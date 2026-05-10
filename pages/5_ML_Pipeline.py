import streamlit as st
import pandas as pd

import sys, os

_PAGES_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_PAGES_DIR)
for _p in (_PROJECT_ROOT, _PAGES_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from styles import inject_css
from ml_pipeline import (
    ensure_ml_artifacts_loaded,
    get_demand_forecast,
    get_grid_demand,
    detect_anomaly,
    detect_anomaly_rule_based,
    detect_anomalies_batch,
    get_model_status,
)

import pickle

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from sklearn.linear_model import LinearRegression
from sklearn.metrics import accuracy_score, confusion_matrix, mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

# ── AeroNet matplotlib palette (EDA expander charts) ─────────────────────────
_MPL_PRIM = "#399DB5"
_MPL_SEC = "#E9819A"
_MPL_ACC = "#411E57"
_MPL_HI = "#E092A7"
_MPL_AXBG = "#FBC8CC"
_MPL_AXBG_ALPHA = 0.15
_MPL_GRID = (80 / 255, 49 / 255, 75 / 255, 0.1)
_MPL_HIST_COLS = [_MPL_PRIM, _MPL_SEC, _MPL_ACC, _MPL_HI]

# Pandas Styler heatmaps — same language as App / Simulation (cream base → pink → mauve → teal → purple).
_ML_GRID_HEATMAP_CMAP = LinearSegmentedColormap.from_list(
    "aeronet_ml_grid",
    [
        "#f4f1ea",
        _MPL_AXBG,
        _MPL_HI,
        _MPL_SEC,
        "#c4dfe8",
        _MPL_PRIM,
        "#5d3a73",
        _MPL_ACC,
    ],
)

# Default label maps for bike-sharing style encodings; falls back to raw codes/values from the frame.
_DEMAND_SEASON_NAMES = {1: "Spring", 2: "Summer", 3: "Fall", 4: "Winter"}
_DEMAND_WEATHER_NAMES = {1: "Clear", 2: "Mist", 3: "Light Rain", 4: "Heavy Rain"}


def _demand_season_ticklabels(values) -> list[str]:
    out = []
    for v in values:
        try:
            iv = int(v)
            out.append(_DEMAND_SEASON_NAMES.get(iv, str(iv)))
        except (TypeError, ValueError):
            out.append(str(v))
    return out


def _demand_weather_ticklabels(values) -> list[str]:
    out = []
    for w in values:
        try:
            iw = int(w)
            out.append(_DEMAND_WEATHER_NAMES.get(iw, f"code {iw}"))
        except (TypeError, ValueError):
            out.append(str(w))
    return out


def _resolve_artifact_pkl_path(filename: str) -> str:
    """Prefer `data/processed/`, then `pages/` (same layout as demand metrics)."""
    for rel in (("data", "processed", filename), ("pages", filename)):
        cand = os.path.join(_PROJECT_ROOT, *rel)
        if os.path.isfile(cand):
            return cand
    return os.path.join(_PAGES_DIR, filename)


def _telemetry_numeric_feature_columns(df: pd.DataFrame) -> list[str]:
    """Numeric telemetry columns for anomaly EDA (exclude the label)."""
    cols: list[str] = []
    for c in df.columns:
        if c == "anomaly_type":
            continue
        if pd.api.types.is_numeric_dtype(df[c]):
            cols.append(str(c))
    return sorted(cols)


def _temp_axis_label_and_title(s: pd.Series) -> tuple[str, str]:
    s = pd.to_numeric(s, errors="coerce").dropna()
    if len(s) == 0:
        return "temp", "Temperature vs demand"
    mx, mn = float(s.max()), float(s.min())
    if mx <= 1.05 and mn >= -0.05:
        return "Temperature (0–1 normalized)", "Temperature vs demand (frame values)"
    return "Temperature", "Temperature vs demand (raw-scale feature in data)"


def _style_mpl_figure_axes(fig):
    fig.patch.set_alpha(0)
    rb, gb, bb = tuple(int(_MPL_AXBG[i : i + 2], 16) / 255.0 for i in (1, 3, 5))
    for ax in fig.axes:
        ax.set_facecolor((rb, gb, bb, _MPL_AXBG_ALPHA))
        ax.grid(True, color=_MPL_GRID, linestyle="-", linewidth=0.8)


def _build_demand_dataset(seed: int = 42):
    """Exact synthetic generator from demand_forecasting.ipynb (used to train demand_model.pkl)."""
    np.random.seed(seed)
    n = 8640  # ~1 year of hourly data (360 days × 24 h)
    hours = np.tile(np.arange(24), n // 24 + 1)[:n]
    seasons = np.random.choice([1, 2, 3, 4], n)
    holiday = np.random.choice([0, 1], n, p=[0.97, 0.03])
    workingday = np.random.choice([0, 1], n, p=[0.3, 0.7])
    weather = np.random.choice([1, 2, 3, 4], n, p=[0.6, 0.25, 0.13, 0.02])
    temp = np.clip(np.random.normal(0.5, 0.2, n), 0.02, 1.0)
    atemp = temp + np.random.normal(0, 0.04, n)
    humidity = np.clip(np.random.normal(0.55, 0.2, n), 0, 1)
    windspeed = np.abs(np.random.normal(0.2, 0.15, n))

    base = 50 + 30 * np.sin(np.pi * hours / 12)
    base += 40 * (weather == 1).astype(int)
    base -= 20 * (weather >= 3).astype(int)
    base += 10 * workingday
    count = np.clip(np.round(base + np.random.normal(0, 15, n)), 0, None)

    df = pd.DataFrame({
        "datetime":   pd.date_range("2023-01-01", periods=n, freq="h"),
        "season":     seasons,
        "holiday":    holiday,
        "workingday": workingday,
        "weather":    weather,
        "temp":       temp,
        "atemp":      atemp,
        "humidity":   humidity,
        "windspeed":  windspeed,
        "count":      count.astype(int),
    })
    df["hour"] = df["datetime"].dt.hour
    return df


def _resolve_bike_sharing_train_csv() -> str | None:
    """Train file may live under bike-sharing/ or at data/raw/ root (common Kaggle unzip layout)."""
    for rel in (
        ("data", "raw", "bike-sharing", "train.csv"),
        ("data", "raw", "train.csv"),
    ):
        p = os.path.join(_PROJECT_ROOT, *rel)
        if os.path.isfile(p):
            return p
    return None


@st.cache_data(show_spinner=False)
def load_demand_dataframe_same_as_metrics():
    """
    Same loading path as demand evaluation (Kaggle CSV if present, else synthetic).
    Returned columns include `feature_cols` + `target_col` after dropna.
    """
    csv_path = _resolve_bike_sharing_train_csv()
    feature_cols = ["hour", "season", "holiday", "workingday", "weather", "temp", "humidity", "windspeed"]
    target_col = "count"
    if csv_path is not None:
        df = pd.read_csv(csv_path)
        if "datetime" in df.columns:
            df["hour"] = pd.to_datetime(df["datetime"]).dt.hour
        source = "kaggle"
    else:
        df = _build_demand_dataset(seed=42)
        source = "synthetic"
    df = df.dropna(subset=feature_cols + [target_col])
    return df, source, feature_cols, target_col


@st.cache_data(show_spinner=False)
def get_demand_metrics():
    """Load demand RF, evaluate RF + train LinearRegression on same 80/20 split.
    Returns: mae_rf, rmse_rf, r2_rf, source, mae_lr, rmse_lr, r2_lr."""
    for rel in (
        ("data", "processed", "demand_model.pkl"),
        ("pages", "demand_model.pkl"),
    ):
        mp = os.path.join(_PROJECT_ROOT, *rel)
        if os.path.isfile(mp):
            model_path = mp
            break
    else:
        raise FileNotFoundError(
            "demand_model.pkl not found under data/processed/ or pages/. Run demand_forecasting.ipynb."
        )

    with open(model_path, "rb") as f:
        model = pickle.load(f)

    df, source, feature_cols, target_col = load_demand_dataframe_same_as_metrics()
    X = df[feature_cols].copy()
    y = df[target_col].to_numpy(dtype=float)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    y_pred_rf = model.predict(X_test)
    mae_rf = round(float(mean_absolute_error(y_test, y_pred_rf)), 2)
    rmse_rf = round(float(np.sqrt(mean_squared_error(y_test, y_pred_rf))), 2)
    r2_rf = round(float(r2_score(y_test, y_pred_rf)), 4)

    lr_model = LinearRegression().fit(X_train, y_train)
    y_pred_lr = lr_model.predict(X_test)
    mae_lr = round(float(mean_absolute_error(y_test, y_pred_lr)), 2)
    rmse_lr = round(float(np.sqrt(mean_squared_error(y_test, y_pred_lr))), 2)
    r2_lr = round(float(r2_score(y_test, y_pred_lr)), 4)

    return mae_rf, rmse_rf, r2_rf, source, mae_lr, rmse_lr, r2_lr


def _build_anomaly_dataset(n_samples: int = 5000, n_drones: int = 10, grid_size: int = 10, seed: int = 42):
    """Exact replica of generate_drone_telemetry() from anomaly_classifier.ipynb.
    Anomalies are sampled from disjoint ranges so the threshold rule has clean separation."""
    np.random.seed(seed)

    records = []
    for i in range(n_samples):
        drone_id = f"D{i % n_drones + 1}"
        step = i // n_drones
        battery_level = np.clip(np.random.normal(75, 15), 5, 100)

        is_battery_anomaly = np.random.rand() < 0.12
        if is_battery_anomaly:
            battery_drop = np.random.uniform(31, 60)
        else:
            battery_drop = np.random.uniform(1, 5)

        altitude = np.clip(np.random.normal(50, 10), 10, 100)
        speed    = np.clip(np.random.normal(8, 2), 1, 20)

        is_sensor_spike = np.random.rand() < 0.10
        if is_sensor_spike:
            altitude_change = np.random.uniform(16, 40)
            speed_change    = np.random.uniform(9, 18)
        else:
            altitude_change = np.random.uniform(0.5, 5)
            speed_change    = np.random.uniform(0.2, 3)

        is_route_anomaly = np.random.rand() < 0.11
        if is_route_anomaly:
            route_deviation = np.random.uniform(6, 15)
        else:
            route_deviation = np.random.uniform(0, 2)

        planned_x = np.random.randint(0, grid_size)
        planned_y = np.random.randint(0, grid_size)
        actual_x  = int(np.clip(planned_x + np.random.choice([-1, 0, 0, 0, 1]) + int(route_deviation * np.random.choice([-1, 1]) * 0.3), 0, grid_size - 1))
        actual_y  = int(np.clip(planned_y + np.random.choice([-1, 0, 0, 0, 1]) + int(route_deviation * np.random.choice([-1, 1]) * 0.3), 0, grid_size - 1))

        if battery_drop > 30:
            label = "Battery Anomaly"
        elif route_deviation > 5:
            label = "Route Anomaly"
        elif altitude_change > 15 or speed_change > 8:
            label = "Sensor Spike"
        else:
            label = "Normal"

        records.append({
            "drone_id": drone_id,
            "step": step,
            "battery_level":   round(battery_level, 1),
            "battery_drop":    round(battery_drop, 2),
            "altitude":        round(altitude, 1),
            "altitude_change": round(altitude_change, 2),
            "speed":           round(speed, 1),
            "speed_change":    round(speed_change, 2),
            "planned_x": planned_x,
            "planned_y": planned_y,
            "actual_x":  actual_x,
            "actual_y":  actual_y,
            "route_deviation": round(route_deviation, 2),
            "anomaly_type":    label,
        })

    return pd.DataFrame(records)


@st.cache_data(show_spinner=False)
def get_anomaly_metrics():
    """Load pickled RF scaler/encoder + same split; train DT / KNN / NB for comparison plots.
    Returns (acc_rf, cm_df_rf, class_names, multi_detail)."""
    from sklearn.preprocessing import StandardScaler
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.naive_bayes import GaussianNB

    base = os.path.dirname(__file__)
    with open(os.path.join(base, "anomaly_model.pkl"), "rb") as f:
        rf_model = pickle.load(f)
    with open(os.path.join(base, "anomaly_label_encoder.pkl"), "rb") as f:
        le = pickle.load(f)

    df = _build_anomaly_dataset(n_samples=5000, seed=42)

    feature_cols = [
        "battery_level",
        "battery_drop",
        "altitude",
        "altitude_change",
        "speed",
        "speed_change",
        "route_deviation",
    ]
    X = df[feature_cols].to_numpy(dtype=float)
    y = le.transform(df["anomaly_type"])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    scaler_mt = StandardScaler().fit(X_train)
    X_train_s = scaler_mt.transform(X_train)
    X_test_s = scaler_mt.transform(X_test)

    y_pred_rf = rf_model.predict(X_test)
    acc = round(float(accuracy_score(y_test, y_pred_rf)), 4)
    cm_rf = confusion_matrix(y_test, y_pred_rf)
    class_names = list(le.classes_)
    cm_df = pd.DataFrame(cm_rf, index=class_names, columns=class_names)

    dt = DecisionTreeClassifier(max_depth=10, min_samples_split=5, random_state=42).fit(
        X_train, y_train
    )
    knn = KNeighborsClassifier(n_neighbors=7, weights="distance").fit(
        X_train_s, y_train
    )
    nb = GaussianNB().fit(X_train_s, y_train)

    model_specs = [
        ("Random Forest", rf_model, X_test, False),
        ("Decision Tree", dt, X_test, False),
        ("KNN", knn, X_test_s, True),
        ("Naive Bayes", nb, X_test_s, True),
    ]

    cms = {}
    accs = {}
    for label, clf, X_ev, _scaled in model_specs:
        pred = clf.predict(X_ev)
        accs[label] = float(accuracy_score(y_test, pred))
        cms[label] = confusion_matrix(y_test, pred)

    multi = {"accuracies": accs, "cms": cms, "class_names": class_names, "df": df.copy()}

    return acc, cm_df, class_names, multi


@st.cache_data(show_spinner=False)
def get_model_comparison():
    """Same numbers as anomaly multi-model metrics (avoid duplicate dataset build)."""
    _acc_rf, _cm_df, _names, multi = get_anomaly_metrics()
    fmt = lambda a: f"{round(float(a) * 100, 2)}%"
    order = ["Random Forest", "Decision Tree", "KNN", "Naive Bayes"]
    notes = {
        "Random Forest": "Selected model — pickled artifact",
        "Decision Tree": "Simpler, more explainable",
        "KNN": "Scaled features — distance weighted",
        "Naive Bayes": "Gaussian — fast probabilistic baseline",
    }
    return pd.DataFrame(
        {
            "Model": order,
            "Accuracy": [fmt(multi["accuracies"][k]) for k in order],
            "Notes": [notes[k] for k in order],
        }
    )


st.set_page_config(page_title="ML Pipeline • AeroNet Lite", page_icon="ML", layout="wide")
inject_css()


ML_SVG = """<svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
<path d="M4 18V6" stroke="#399DB5" stroke-width="2" stroke-linecap="round"/>
<path d="M4 18H20" stroke="#399DB5" stroke-width="2" stroke-linecap="round"/>
<path d="M7 14l3-3 3 2 4-5" stroke="#7C4EBB" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
<circle cx="10" cy="11" r="1.2" fill="#DE5C8F"/>
<circle cx="13" cy="13" r="1.2" fill="#DE5C8F"/>
<circle cx="17" cy="8" r="1.2" fill="#DE5C8F"/>
</svg>"""

ribbon_html = f"""<div class="aeronet-top-ribbon">
<div style="display:flex;align-items:center;justify-content:space-between;gap:14px;">
<div style="display:flex;align-items:center;gap:10px;">
{ML_SVG}
<div>
<div style="font-size:1.75rem;font-weight:850;letter-spacing:-0.02em;color:#50314B;line-height:1.05;">ML Pipeline</div>
<div style="margin-top:0.15rem;color:#405C6F;font-weight:600;">Module 5 — Demand Forecasting and Anomaly Detection</div>
</div>
</div>
</div>
</div>"""
st.markdown(ribbon_html, unsafe_allow_html=True)


def card_open(title: str) -> None:
    st.markdown(
        f"<div style='background:#EDECDB;border-radius:14px;border:1px solid rgba(24,26,30,0.12);padding:14px 14px;box-shadow:0 10px 24px rgba(24,26,30,0.06);'>"
        f"<div style='font-weight:850;color:#50314B;font-size:14px;margin-bottom:10px;'>{title}</div>",
        unsafe_allow_html=True,
    )


def card_close() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def badge(text: str, ok: bool) -> str:
    bg = "rgba(107, 177, 173, 0.22)" if ok else "rgba(222, 92, 143, 0.20)"
    fg = "#2C2C3B" if ok else "#2C2C3B"
    border = "rgba(107, 177, 173, 0.38)" if ok else "rgba(222, 92, 143, 0.35)"
    return (
        f"<span style='display:inline-block;padding:3px 10px;border-radius:999px;"
        f"background:{bg};border:1px solid {border};color:{fg};font-weight:900;font-size:12px;margin-right:8px;'>"
        f"{text}</span>"
    )


st.subheader("Demand Forecasting")

left, right = st.columns(2, gap="large")
with left:
    hour = st.slider("Hour", 0, 23, 12)
    season = st.selectbox("Season", [1, 2, 3, 4], format_func={1: "Spring", 2: "Summer", 3: "Fall", 4: "Winter"}.get)
    weather = st.selectbox(
        "Weather",
        [1, 2, 3, 4],
        format_func={1: "Clear", 2: "Mist", 3: "Light Rain", 4: "Heavy Rain"}.get,
    )
with right:
    temp = st.slider("Temperature (normalized)", 0.0, 1.0, 0.50, 0.01)
    humidity = st.slider("Humidity (normalized)", 0.0, 1.0, 0.50, 0.01)
    windspeed = st.slider("Windspeed (normalized)", 0.0, 1.0, 0.20, 0.01)

holiday = st.checkbox("Holiday", value=False)
workingday = st.checkbox("Working Day", value=True)

if "ml_demand_pred" not in st.session_state:
    st.session_state["ml_demand_pred"] = None
if "ml_grid_demand" not in st.session_state:
    st.session_state["ml_grid_demand"] = None
if "ml_demand_error" not in st.session_state:
    st.session_state["ml_demand_error"] = None

current_inputs = (
    hour,
    season,
    holiday,
    workingday,
    weather,
    round(temp, 2),
    round(humidity, 2),
    round(windspeed, 2),
)
if st.session_state.get("_last_demand_inputs") != current_inputs:
    st.session_state["_last_demand_inputs"] = current_inputs
    if st.session_state.get("ml_demand_pred") is not None:
        st.caption("⟳ Inputs changed — click Run Demand Forecast to update.")

if st.button("Run Demand Forecast", type="primary", use_container_width=True):
    try:
        st.session_state["ml_demand_error"] = None
        pred = get_demand_forecast(
            hour=hour,
            season=season,
            holiday=1 if holiday else 0,
            workingday=1 if workingday else 0,
            weather=weather,
            temp=temp,
            humidity=humidity,
            windspeed=windspeed,
        )
        grid = get_grid_demand(
            hour=hour,
            season=season,
            holiday=1 if holiday else 0,
            workingday=1 if workingday else 0,
            weather=weather,
            base_temp=temp,
            base_humidity=humidity,
            base_wind=windspeed,
            grid_size=10,
            seed=42,
        )
        st.session_state["ml_demand_pred"] = int(pred)
        st.session_state["ml_grid_demand"] = grid
    except FileNotFoundError as e:
        st.session_state["ml_demand_pred"] = None
        st.session_state["ml_grid_demand"] = None
        st.session_state["ml_demand_error"] = str(e)

if st.session_state["ml_demand_error"]:
    st.error(st.session_state["ml_demand_error"])

card_open("Predicted Demand")
if st.session_state["ml_demand_pred"] is None:
    st.markdown("<div style='color:#405C6F;font-weight:700;'>Run the forecast to see a prediction.</div>", unsafe_allow_html=True)
else:
    st.metric("Predicted Demand Count", st.session_state["ml_demand_pred"])
card_close()

st.write("")
card_open("10×10 Demand Heatmap")
grid = st.session_state["ml_grid_demand"]
if grid is None:
    st.markdown("<div style='color:#405C6F;font-weight:700;'>Heatmap will appear after running the forecast.</div>", unsafe_allow_html=True)
else:
    heat = pd.DataFrame(grid)
    st.dataframe(
        heat.style.background_gradient(cmap=_ML_GRID_HEATMAP_CMAP, axis=None),
        use_container_width=True,
        hide_index=True,
    )
card_close()

st.divider()
card_open("Model Performance — Demand Forecasting")
try:
    mae, rmse, r2, _src, _mae_lr, _rmse_lr, _r2_lr = get_demand_metrics()
    c1, c2, c3 = st.columns(3)
    c1.metric("MAE", mae)
    c2.metric("RMSE", rmse)
    c3.metric("R²", r2)
    if _src == "kaggle":
        st.caption("Random Forest Regressor — evaluated on held-out 20% test set (Kaggle bike-sharing data).")
    else:
        st.caption("Random Forest Regressor — evaluated on held-out 20% test set (notebook synthetic fallback).")
        st.info(
            "The pickled `demand_model.pkl` was trained on the Kaggle bike-sharing dataset "
            "(10,886 rows). That CSV is not on disk, so metrics here are computed against the "
            "notebook's synthetic generator instead — the model was not trained on this "
            "distribution, so MAE / RMSE / R² will look worse than the notebook's reported "
            "MAE 47.44 / RMSE 70.27 / R² 0.85.\n\n"
            "To restore the notebook numbers, place the Kaggle Bike Sharing **`train.csv`** at either:\n"
            "`aeronet-lite/data/raw/bike-sharing/train.csv` **or** `aeronet-lite/data/raw/train.csv`"
        )
except Exception as e:
    st.warning(f"Could not compute metrics: {e}")
card_close()


st.divider()
st.subheader("Anomaly Detection")

ac1, ac2 = st.columns(2, gap="large")
with ac1:
    battery_level = st.slider("Battery Level", 0, 100, 75)
    battery_drop = st.slider("Battery Drop", 0, 50, 3)
    altitude = st.slider("Altitude", 0, 120, 50)
    altitude_change = st.slider("Altitude Change", 0, 30, 2)
with ac2:
    speed = st.slider("Speed", 0, 20, 8)
    speed_change = st.slider("Speed Change", 0, 15, 1)
    route_deviation = st.slider("Route Deviation", 0, 15, 1)

current_anomaly_inputs = (
    battery_level,
    battery_drop,
    altitude,
    altitude_change,
    speed,
    speed_change,
    route_deviation,
)
if st.session_state.get("_last_anomaly_inputs") != current_anomaly_inputs:
    st.session_state["_last_anomaly_inputs"] = current_anomaly_inputs
    if st.session_state.get("ml_anomaly_result") is not None:
        st.caption("⟳ Inputs changed — click Run Anomaly Detection to update.")

drone_id = st.selectbox("Drone ID", ["D1", "D2", "D3", "D4"], key="anomaly_drone_id")

if "ml_anomaly_result" not in st.session_state:
    st.session_state["ml_anomaly_result"] = None
if "ml_anomaly_error" not in st.session_state:
    st.session_state["ml_anomaly_error"] = None
if "ml_anomaly_fallback" not in st.session_state:
    st.session_state["ml_anomaly_fallback"] = False

if st.button("Run Anomaly Detection", type="primary", use_container_width=True):
    try:
        st.session_state["ml_anomaly_error"] = None
        st.session_state["ml_anomaly_fallback"] = False
        st.session_state["ml_anomaly_result"] = detect_anomaly(
            battery_level=float(battery_level),
            battery_drop=float(battery_drop),
            altitude=float(altitude),
            altitude_change=float(altitude_change),
            speed=float(speed),
            speed_change=float(speed_change),
            route_deviation=float(route_deviation),
        )
    except FileNotFoundError as e:
        st.session_state["ml_anomaly_error"] = str(e)
        label = detect_anomaly_rule_based(
            battery_drop=float(battery_drop),
            route_deviation=float(route_deviation),
            altitude_change=float(altitude_change),
            speed_change=float(speed_change),
        )
        st.session_state["ml_anomaly_result"] = {
            "label": "Rule-Based Fallback (model not loaded)",
            "confidence": 0.0,
            "probabilities": {"Normal": 0.0, "Battery Anomaly": 0.0, "Route Anomaly": 0.0, "Sensor Spike": 0.0},
            "is_anomaly": label != "Normal",
            "fallback_label": label,
        }
        st.session_state["ml_anomaly_fallback"] = True

if st.session_state["ml_anomaly_error"]:
    st.error(st.session_state["ml_anomaly_error"])

card_open("Anomaly Result")
res = st.session_state["ml_anomaly_result"]
if res is None:
    st.session_state["anomaly_alert"] = None
    st.markdown("<div style='color:#405C6F;font-weight:700;'>Run detection to see results.</div>", unsafe_allow_html=True)
else:
    label = str(res.get("label", "Unknown"))
    conf = float(res.get("confidence", 0.0))
    is_anom = bool(res.get("is_anomaly", False))
    probs = dict(res.get("probabilities", {}))

    card_bg = "rgba(107, 177, 173, 0.16)" if not is_anom else "rgba(222, 92, 143, 0.16)"
    st.markdown(
        f"<div style='background:{card_bg};border-radius:14px;border:1px solid rgba(24,26,30,0.10);padding:12px 12px;margin-bottom:12px;'>"
        f"<div style='display:flex;align-items:center;justify-content:space-between;gap:10px;'>"
        f"<div style='font-weight:900;color:#411E57;'>{label}</div>"
        f"<div style='font-weight:900;color:#2C2C3B;'>Confidence: {int(round(conf*100))}%</div>"
        f"</div>"
        f"<div style='margin-top:8px;color:#2C2C3B;font-weight:700;'>is_anomaly: {str(is_anom)}</div>"
        + (f"<div style='margin-top:6px;color:#2C2C3B;font-weight:700;'>Fallback label: {res.get('fallback_label')}</div>" if st.session_state["ml_anomaly_fallback"] else "")
        + "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div style='font-weight:850;color:#50314B;margin-bottom:8px;'>Class Probabilities</div>", unsafe_allow_html=True)
    for cls in ["Normal", "Battery Anomaly", "Route Anomaly", "Sensor Spike"]:
        p = float(probs.get(cls, 0.0))
        st.markdown(f"<div style='font-weight:700;color:#411E57;margin-bottom:4px;'>{cls}</div>", unsafe_allow_html=True)
        st.progress(min(max(p, 0.0), 1.0))

    if res.get("is_anomaly"):
        st.session_state["anomaly_alert"] = {
            "label": str(res.get("label", "")),
            "confidence": float(res.get("confidence", 0.0)),
            "drone": drone_id,
        }
        st.error(
            "ALERT: Anomaly detected — Disruption Handler will force drone return to hub."
        )
    else:
        st.session_state["anomaly_alert"] = None
card_close()

st.divider()
card_open("Model Performance — Anomaly Classifier")
try:
    acc, cm_df, class_names, _anomaly_multi = get_anomaly_metrics()
    st.metric("Accuracy", f"{round(acc*100, 2)}%")
    st.caption("Random Forest Classifier — evaluated on held-out 20% test set")
    st.markdown("<div style='font-weight:700;color:#50314B;margin:10px 0 6px;'>Confusion Matrix — Rows = Actual, Columns = Predicted</div>", unsafe_allow_html=True)
    st.dataframe(
        cm_df.style.background_gradient(cmap="Blues"),
        use_container_width=True
    )
except Exception as e:
    st.warning(f"Could not compute metrics: {e}")
card_close()

with st.expander("Model Comparison (click to expand)"):
    st.caption("All models trained and evaluated on the same synthetic anomaly dataset (80/20 stratified split, seed=42).")
    try:
        st.table(get_model_comparison())
    except Exception as e:
        st.warning(f"Could not compute model comparison: {e}")


st.divider()
st.subheader("Model Status")

try:
    ensure_ml_artifacts_loaded()
    status = get_model_status()
except FileNotFoundError as e:
    status = None
    st.error(str(e))

card_open("Artifacts & Load State")
if status is None:
    st.markdown("<div style='color:#405C6F;font-weight:700;'>Status unavailable.</div>", unsafe_allow_html=True)
else:
    rows = []
    all_ok = bool(status.get("all_artifacts_available", False))

    for k, v in status.items():
        ok = bool(v) if isinstance(v, bool) else False
        rows.append(f"<div style='margin:6px 0;'>{badge(k, ok)}<span style='font-weight:750;color:#411E57;'>{str(v)}</span></div>")

    st.markdown("".join(rows), unsafe_allow_html=True)
    if not all_ok:
        st.warning(
            "Run demand_forecasting.ipynb and anomaly_classifier.ipynb first to generate model files."
        )
card_close()


_ML_EXPANDER_WARN = "Run a forecast or detection first to load models."

with st.expander("EDA and Model Analysis"):
    tab_eda, tab_cmp, tab_anom, tab_fi = st.tabs(
        ["Demand EDA", "Model Comparison", "Anomaly Analysis", "Feature Importance"]
    )

    # TAB 1 — Demand EDA
    with tab_eda:
        try:
            df_eda, _src_eda, _fc_eda, target_eda = load_demand_dataframe_same_as_metrics()
            fig, axes = plt.subplots(2, 2, figsize=(11, 8.8))
            _style_mpl_figure_axes(fig)

            hour_idx = sorted(df_eda["hour"].dropna().astype(int).unique())
            by_hour = df_eda.groupby("hour")[target_eda].mean().reindex(hour_idx).fillna(0.0)
            axes[0, 0].bar(hour_idx, by_hour.to_numpy(dtype=float), color=_MPL_PRIM, edgecolor="none")
            axes[0, 0].set_title("Mean demand by hour (from loaded data)")
            axes[0, 0].set_xlabel("Hour")
            axes[0, 0].set_ylabel(f"Average `{target_eda}`")

            by_season_grp = df_eda.groupby("season")[target_eda].mean().sort_index()
            season_vals = list(by_season_grp.index.dropna())
            x_se = np.arange(len(season_vals))
            axes[0, 1].bar(x_se, by_season_grp.loc[season_vals].to_numpy(dtype=float), color=_MPL_SEC, edgecolor="none")
            axes[0, 1].set_xticks(x_se)
            axes[0, 1].set_xticklabels(
                _demand_season_ticklabels([int(float(v)) for v in season_vals]), rotation=22, ha="right"
            )
            axes[0, 1].set_title("Mean demand by season (values present in frame)")
            axes[0, 1].set_ylabel(f"Average `{target_eda}`")

            temp_xlbl, temp_title = _temp_axis_label_and_title(df_eda["temp"])
            axes[1, 0].scatter(
                df_eda["temp"],
                df_eda[target_eda],
                s=8,
                alpha=0.3,
                color=_MPL_PRIM,
                edgecolors="none",
            )
            axes[1, 0].set_title(temp_title)
            axes[1, 0].set_xlabel(temp_xlbl)
            axes[1, 0].set_ylabel(target_eda)

            by_weather_grp = df_eda.groupby("weather")[target_eda].mean().sort_index()
            weather_vals = list(by_weather_grp.index.dropna())
            x_wx = np.arange(len(weather_vals))
            axes[1, 1].bar(x_wx, by_weather_grp.loc[weather_vals].to_numpy(dtype=float), color=_MPL_HI, edgecolor="none")
            axes[1, 1].set_xticks(x_wx)
            axes[1, 1].set_xticklabels(
                _demand_weather_ticklabels([int(float(w)) for w in weather_vals]), rotation=20, ha="right"
            )
            axes[1, 1].set_title("Mean demand by weather (categories in frame)")
            axes[1, 1].set_ylabel(f"Average `{target_eda}`")

            fig.suptitle(
                f"Demand EDA — {_src_eda} source, n={len(df_eda):,} rows (same pipeline as RF metrics)",
                color=_MPL_ACC,
                fontweight="800",
            )
            fig.tight_layout()
            st.pyplot(fig, clear_figure=True)
            plt.close(fig)
            st.caption(
                "Aggregates computed live from **`load_demand_dataframe_same_as_metrics()`**: hourly & seasonal averages, "
                "weather strata, and a raw scatter vs temperature (all rows after dropna)."
            )
        except Exception:
            st.warning(_ML_EXPANDER_WARN)

    # TAB 2 — Regression comparison (LR vs pickled RF)
    with tab_cmp:
        try:
            mae_rf, rmse_rf, r2_rf, _src_mc, mae_lr, rmse_lr, r2_lr = get_demand_metrics()
            labels_b = ["Linear Regression", "Random Forest"]
            fig_b, axes_b = plt.subplots(1, 3, figsize=(12.5, 4.2))
            _style_mpl_figure_axes(fig_b)
            comps = [
                ("MAE", [mae_lr, mae_rf]),
                ("RMSE", [rmse_lr, rmse_rf]),
                ("R²", [r2_lr, r2_rf]),
            ]
            for ax_j, (title_j, vals) in zip(axes_b, comps):
                ax_j.bar(np.arange(2), vals, color=[_MPL_PRIM, _MPL_SEC], width=0.55)
                ax_j.set_xticks(np.arange(2))
                ax_j.set_xticklabels(labels_b, rotation=22, ha="right")
                ax_j.set_title(title_j)
                ax_j.axhline(0, color=_MPL_GRID[:3], alpha=0.4, lw=0.8)
            fig_b.suptitle("Linear Regression vs Random Forest — same split", color=_MPL_ACC, fontweight="780")
            fig_b.tight_layout()
            st.pyplot(fig_b, clear_figure=True)
            plt.close(fig_b)
            st.caption(
                "**Linear Regression** is fit on `(X_train, y_train)`; **RF** is the pickled estimator — both evaluated on "
                "the mutually held‑out **`test_size=0.2`** partition (random_state=42)."
            )
        except Exception:
            st.warning(_ML_EXPANDER_WARN)

    # TAB 3 — Anomaly multi-model + telemetry distributions
    with tab_anom:
        try:
            _, _, _, multi = get_anomaly_metrics()
            cols_bar = [_MPL_PRIM, _MPL_SEC, _MPL_ACC, _MPL_HI]
            labels_order = ["Random Forest", "Decision Tree", "KNN", "Naive Bayes"]

            st.markdown("###### Section A — Model accuracy")
            fig_a, ax_a = plt.subplots(figsize=(8.8, 4.2))
            _style_mpl_figure_axes(fig_a)
            acc_pct = [multi["accuracies"][k] * 100.0 for k in labels_order]
            xs = np.arange(len(labels_order))
            ax_a.bar(xs, acc_pct, color=cols_bar, edgecolor="none")
            ax_a.set_xticks(xs)
            ax_a.set_xticklabels(labels_order, rotation=18, ha="right")
            ax_a.set_ylabel("Accuracy (%)")
            ax_a.set_title("Held-out stratified validation (20%)")
            ax_a.set_ylim(0, max(100, max(acc_pct, default=1) * 1.12))
            fig_a.tight_layout()
            st.pyplot(fig_a, clear_figure=True)
            plt.close(fig_a)

            st.markdown("###### Section B — Confusion matrices")
            fig_m, axes_m = plt.subplots(2, 2, figsize=(10.8, 9.8))
            _style_mpl_figure_axes(fig_m)
            for ax_m, lbl in zip(axes_m.ravel(), labels_order):
                cm_i = multi["cms"][lbl]
                im_m = ax_m.imshow(cm_i, cmap="Blues")
                ni, nj = cm_i.shape
                for ii in range(ni):
                    for jj in range(nj):
                        ax_m.text(
                            jj,
                            ii,
                            int(cm_i[ii, jj]),
                            ha="center",
                            va="center",
                            color="#1f1f1f",
                            fontsize=9,
                            fontweight=600,
                        )
                ax_m.set_xticks(np.arange(nj))
                ax_m.set_yticks(np.arange(ni))
                ax_m.set_xticklabels(multi["class_names"], rotation=35, ha="right")
                ax_m.set_yticklabels(multi["class_names"])
                ax_m.set_xlabel("Predicted")
                ax_m.set_ylabel("Actual")
                acc_i = multi["accuracies"][lbl]
                ax_m.set_title(f"{lbl} — accuracy {acc_i * 100:.2f}%")
                fig_m.colorbar(im_m, ax=ax_m, fraction=0.046)
            fig_m.tight_layout()
            st.pyplot(fig_m, clear_figure=True)
            plt.close(fig_m)

            df_tel = multi["df"]
            class_lbl_order = sorted(df_tel["anomaly_type"].unique())
            telemetry_num_cols = _telemetry_numeric_feature_columns(df_tel)

            st.markdown("###### Section C — Telemetry distributions (box)")
            feats_box = telemetry_num_cols[: min(8, len(telemetry_num_cols))]
            if not feats_box:
                st.info("No numeric telemetry columns found in `multi['df']` for boxplots.")
            else:
                fig_cw = max(14.8, 3.5 * len(feats_box))
                fig_c, axes_c = plt.subplots(1, len(feats_box), figsize=(fig_cw, 3.9), squeeze=False)
                axes_c = np.ravel(axes_c)
                _style_mpl_figure_axes(fig_c)
                for ax_c, fcol in zip(axes_c, feats_box):
                    series_list = []
                    lbls_eff = []
                    for grp in class_lbl_order:
                        vals = df_tel.loc[df_tel["anomaly_type"] == grp, fcol].dropna().to_numpy(dtype=float)
                        if vals.size > 0:
                            series_list.append(vals)
                            lbls_eff.append(grp)
                    if not series_list:
                        ax_c.set_visible(False)
                        continue
                    bp = ax_c.boxplot(series_list, patch_artist=True)
                    ax_c.set_xticklabels(lbls_eff, rotation=52, fontsize=7)
                    _hist_cycle = cols_bar + cols_bar + cols_bar + cols_bar
                    for bx, clr in zip(bp["boxes"], _hist_cycle):
                        bx.set_facecolor(clr)
                        bx.set_alpha(0.45)
                        bx.set_edgecolor(_MPL_ACC)
                    ax_c.set_title(fcol)
                    ax_c.axhline(0, color=_MPL_GRID[:3], alpha=0.35)
                fig_c.tight_layout()
                st.pyplot(fig_c, clear_figure=True)
                plt.close(fig_c)

            st.markdown("###### Section D — Feature histograms by anomaly label")
            feat_hist_subset = telemetry_num_cols
            if not feat_hist_subset:
                st.info("No numeric features to histogram.")
            else:
                n_h = len(feat_hist_subset)
                n_hist_cols = 2
                n_hist_rows = int(np.ceil(n_h / n_hist_cols))
                fig_h, axes_h = plt.subplots(
                    n_hist_rows, n_hist_cols, figsize=(10.5, max(3.2, 3.1 * n_hist_rows)), squeeze=False
                )
                axes_flat = np.ravel(axes_h)
                _style_mpl_figure_axes(fig_h)
                for idx, f_hi in enumerate(feat_hist_subset):
                    ax_hi = axes_flat[idx]
                    col_ser = pd.to_numeric(df_tel[f_hi], errors="coerce").dropna()
                    rng = (
                        col_ser.quantile([0.01, 0.99]).tolist()
                        if len(col_ser) >= 10
                        else [col_ser.min(), col_ser.max()]
                    )
                    for li, grp in enumerate(class_lbl_order):
                        sub = df_tel.loc[df_tel["anomaly_type"] == grp, f_hi].dropna()
                        sub = pd.to_numeric(sub, errors="coerce").dropna()
                        if len(sub) < 5:
                            continue
                        clr = cols_bar[li % len(cols_bar)]
                        ax_hi.hist(
                            sub,
                            bins=min(32, max(8, len(sub) // 20)),
                            alpha=0.45,
                            density=True,
                            color=clr,
                            label=str(grp),
                            range=(rng[0], rng[1]) if len(rng) == 2 and rng[1] > rng[0] else None,
                        )
                    ax_hi.set_title(f_hi)
                    ax_hi.legend(fontsize=7, loc="upper right")
                for idx in range(len(feat_hist_subset), len(axes_flat)):
                    axes_flat[idx].set_visible(False)
                fig_h.tight_layout()
                st.pyplot(fig_h, clear_figure=True)
                plt.close(fig_h)

            st.caption(
                "Plots use **live** anomaly telemetry from `multi['df']` (same simulated build as metrics). "
                "Numeric axes are inferred from dataframe dtypes; histogram bin counts adapt to cohort size."
            )
        except Exception:
            st.warning(_ML_EXPANDER_WARN)

    # TAB 4 — RF feature importances
    with tab_fi:
        try:
            demand_feature_names = [
                "hour",
                "season",
                "holiday",
                "workingday",
                "weather",
                "temp",
                "humidity",
                "windspeed",
            ]
            anomaly_feature_names = [
                "battery_level",
                "battery_drop",
                "altitude",
                "altitude_change",
                "speed",
                "speed_change",
                "route_deviation",
            ]
            with open(_resolve_artifact_pkl_path("demand_model.pkl"), "rb") as f_rf_d:
                d_mod = pickle.load(f_rf_d)
            with open(_resolve_artifact_pkl_path("anomaly_model.pkl"), "rb") as f_rf_a:
                a_mod = pickle.load(f_rf_a)

            fi_d = np.asarray(d_mod.feature_importances_, dtype=float)
            fi_a = np.asarray(a_mod.feature_importances_, dtype=float)

            fig_f, (ax_dl, ax_ar) = plt.subplots(1, 2, figsize=(13.8, 5.9))
            _style_mpl_figure_axes(fig_f)

            order_d = np.argsort(fi_d)[::-1]
            md_names = getattr(d_mod, "feature_names_in_", None)
            dn = demand_feature_names
            if md_names is not None and len(md_names) == len(fi_d):
                dn = list(md_names)
            y_pos_d = np.arange(len(order_d))
            ax_dl.barh(y_pos_d, fi_d[order_d][::-1], color=_MPL_SEC, edgecolor="none")
            ax_dl.set_yticks(y_pos_d)
            ax_dl.set_yticklabels([dn[i] for i in order_d][::-1])
            ax_dl.set_xlabel("Importance")
            ax_dl.invert_yaxis()
            ax_dl.set_title("Demand Random Forest")

            order_a = np.argsort(fi_a)[::-1]
            ma_names = getattr(a_mod, "feature_names_in_", None)
            an = anomaly_feature_names
            if ma_names is not None and len(ma_names) == len(fi_a):
                an = list(ma_names)
            y_pos_a = np.arange(len(order_a))
            ax_ar.barh(y_pos_a, fi_a[order_a][::-1], color=_MPL_PRIM, edgecolor="none")
            ax_ar.set_yticks(y_pos_a)
            ax_ar.set_yticklabels([an[i] for i in order_a][::-1])
            ax_ar.set_xlabel("Importance")
            ax_ar.invert_yaxis()
            ax_ar.set_title("Anomaly Random Forest")

            fig_f.tight_layout()
            st.pyplot(fig_f, clear_figure=True)
            plt.close(fig_f)
            st.caption(
                "Importances are **`feature_importances_`** from tree splits (fraction of impurity decrease). "
                "Taller bars mean splits on that predictor reduced error more across the ensemble."
            )
        except Exception:
            st.warning(_ML_EXPANDER_WARN)

