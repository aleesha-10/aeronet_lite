"""
ml_pipeline.py — AeroNet Lite ML Pipeline
==========================================
Provides two primary callable functions for the simulation:

    get_demand_forecast(...)  -> predicted delivery demand (regression)
    detect_anomaly(...)       -> predicted flight anomaly label (classification)

Also provides helper:
    get_grid_demand(...)      -> demand predictions for entire 10x10 grid

This module has ZERO notebook dependencies. It only requires the
trained .pkl files saved by demand_forecasting.ipynb and anomaly_classifier.ipynb.

Usage in other modules:
    from ml_pipeline import get_demand_forecast, detect_anomaly, get_grid_demand
"""

import os
import pickle
import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

# PATH RESOLUTION
# Works whether this file is run from src/ or from the project root.
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_CURRENT_DIR)  # aeronet_lite/

PROCESSED_DIR = os.path.join(_PROJECT_ROOT, 'data', 'processed')

# Artifact file names (must match what the notebooks save)
_DEMAND_MODEL_FILE   = 'demand_model.pkl'
_DEMAND_SCALER_FILE  = 'demand_scaler.pkl'
_ANOMALY_MODEL_FILE  = 'anomaly_model.pkl'
_ANOMALY_SCALER_FILE = 'anomaly_scaler.pkl'
_ANOMALY_ENCODER_FILE = 'anomaly_label_encoder.pkl'

# LAZY-LOAD SINGLETONS
# Models are loaded once on first call, then cached in module-level dicts.
# This avoids reloading the .pkl on every simulation step.

_demand_model   = None
_demand_scaler  = None
_anomaly_model  = None
_anomaly_scaler = None
_anomaly_encoder = None


def _load_pickle(filepath: str):
    """Load a pickle file with a helpful error if it doesn't exist."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"Required artifact not found: {filepath}\n"
            f"Please run the corresponding notebook first to generate it:\n"
            f"  - demand_forecasting.ipynb  -> demand_model.pkl, demand_scaler.pkl\n"
            f"  - anomaly_classifier.ipynb  -> anomaly_model.pkl, anomaly_scaler.pkl, anomaly_label_encoder.pkl"
        )
    with open(filepath, 'rb') as f:
        return pickle.load(f)


def _ensure_demand_model():
    """Lazy-load demand model and scaler on first call."""
    global _demand_model, _demand_scaler
    if _demand_model is None:
        _demand_model  = _load_pickle(os.path.join(PROCESSED_DIR, _DEMAND_MODEL_FILE))
        _demand_scaler = _load_pickle(os.path.join(PROCESSED_DIR, _DEMAND_SCALER_FILE))
        print("[ML Pipeline] Demand forecasting model loaded.")


def _ensure_anomaly_model():
    """Lazy-load anomaly model, scaler, and label encoder on first call."""
    global _anomaly_model, _anomaly_scaler, _anomaly_encoder
    if _anomaly_model is None:
        _anomaly_model   = _load_pickle(os.path.join(PROCESSED_DIR, _ANOMALY_MODEL_FILE))
        _anomaly_scaler  = _load_pickle(os.path.join(PROCESSED_DIR, _ANOMALY_SCALER_FILE))
        _anomaly_encoder = _load_pickle(os.path.join(PROCESSED_DIR, _ANOMALY_ENCODER_FILE))
        print("[ML Pipeline] Anomaly classification model loaded.")


# FUNCTION 1: DEMAND FORECASTING (REGRESSION)

def get_demand_forecast(
    hour: int = 12,
    season: int = 1,
    holiday: int = 0,
    workingday: int = 1,
    weather: int = 1,
    temp: float = 0.5,
    humidity: float = 0.5,
    windspeed: float = 0.2,
    round_output: bool = True
) -> float:
    """
    Predict hourly delivery demand using the trained Random Forest regressor.

    Parameters
    ----------
    hour        : int   -- Hour of day (0-23). Default 12.
    season      : int   -- 1=Spring, 2=Summer, 3=Fall, 4=Winter. Default 1.
    holiday     : int   -- 0 or 1. Default 0.
    workingday  : int   -- 0 or 1. Default 1.
    weather     : int   -- 1=Clear, 2=Mist, 3=Light Rain, 4=Heavy Rain. Default 1.
    temp        : float -- Normalized temperature (0-1). Default 0.5.
    humidity    : float -- Normalized humidity (0-1). Default 0.5.
    windspeed   : float -- Normalized windspeed (0-1). Default 0.2.
    round_output: bool  -- Round to nearest integer. Default True.

    Returns
    -------
    float -- Predicted demand count (e.g., 157 deliveries/hour).
    """
    _ensure_demand_model()

    x = pd.DataFrame([{
        'hour': hour,
        'season': season,
        'holiday': holiday,
        'workingday': workingday,
        'weather': weather,
        'temp': np.clip(temp, 0, 1),
        'humidity': np.clip(humidity, 0, 1),
        'windspeed': abs(windspeed)
    }])

    prediction = _demand_model.predict(x)[0]

    if round_output:
        prediction = max(0, round(prediction))

    return prediction


def get_grid_demand(
    hour: int = 12,
    season: int = 1,
    holiday: int = 0,
    workingday: int = 1,
    weather: int = 1,
    base_temp: float = 0.5,
    base_humidity: float = 0.5,
    base_wind: float = 0.2,
    grid_size: int = 10,
    spatial_noise_std: float = 5.0,
    seed: int = None
) -> np.ndarray:
    """
    Predict demand for EVERY cell in the 10x10 simulation grid.

    Micro-climate variation is simulated by adding small Gaussian noise
    to temperature, humidity, and windspeed for each cell.

    Parameters
    ----------
    hour             : int   -- Hour of day.
    season           : int   -- Season code.
    holiday          : int   -- Is holiday?
    workingday       : int   -- Is working day?
    weather          : int   -- Weather code.
    base_temp        : float -- Base normalized temperature.
    base_humidity    : float -- Base normalized humidity.
    base_wind        : float -- Base normalized windspeed.
    grid_size        : int   -- Grid dimension (default 10).
    spatial_noise_std: float -- Std of demand noise per cell.
    seed             : int   -- Optional seed for reproducibility.

    Returns
    -------
    np.ndarray -- Shape (grid_size, grid_size), each entry = predicted demand.
    """
    _ensure_demand_model()

    if seed is not None:
        np.random.seed(seed)

    grid_demand = np.zeros((grid_size, grid_size))

    for r in range(grid_size):
        for c in range(grid_size):
            temp_var = np.clip(base_temp + np.random.normal(0, 0.03), 0, 1)
            hum_var  = np.clip(base_humidity + np.random.normal(0, 0.03), 0, 1)
            wind_var = abs(base_wind + np.random.normal(0, 0.02))

            x = pd.DataFrame([{
                'hour': hour, 'season': season, 'holiday': holiday,
                'workingday': workingday, 'weather': weather,
                'temp': temp_var, 'humidity': hum_var, 'windspeed': wind_var
            }])

            pred = _demand_model.predict(x)[0]
            pred += np.random.normal(0, spatial_noise_std * 0.3)
            grid_demand[r][c] = max(0, round(pred))

    return grid_demand


# FUNCTION 2: ANOMALY DETECTION (CLASSIFICATION)

# Valid label names (for validation in detect_anomaly)
VALID_ANOMALY_LABELS = {'Normal', 'Battery Anomaly', 'Route Anomaly', 'Sensor Spike'}


def detect_anomaly(
    battery_level: float = 75.0,
    battery_drop: float = 2.5,
    altitude: float = 50.0,
    altitude_change: float = 1.0,
    speed: float = 8.0,
    speed_change: float = 0.5,
    route_deviation: float = 0.5
) -> dict:
    """
    Classify a single drone telemetry reading using the trained
    Random Forest anomaly classifier.

    Parameters
    ----------
    battery_level  : float -- Current battery percentage (0-100).
    battery_drop   : float -- Battery drop in last step (%).
    altitude       : float -- Current altitude (m).
    altitude_change: float -- Altitude change in last step (m).
    speed          : float -- Current speed (m/s).
    speed_change   : float -- Speed change in last step (m/s).
    route_deviation: float -- Deviation from planned route (grid cells).

    Returns
    -------
    dict with keys:
        'label'      : str   -- 'Normal', 'Battery Anomaly',
                               'Route Anomaly', or 'Sensor Spike'
        'confidence' : float -- Model confidence for predicted class (0-1)
        'probabilities': dict -- Probability for each class
        'is_anomaly' : bool  -- True if label != 'Normal'
    """
    _ensure_anomaly_model()

    x = pd.DataFrame([{
        'battery_level': battery_level,
        'battery_drop': battery_drop,
        'altitude': altitude,
        'altitude_change': altitude_change,
        'speed': speed,
        'speed_change': speed_change,
        'route_deviation': route_deviation
    }])

    pred_encoded = _anomaly_model.predict(x)[0]
    label = _anomaly_encoder.inverse_transform([pred_encoded])[0]

    proba = _anomaly_model.predict_proba(x)[0]
    confidence = round(float(proba[pred_encoded]), 4)

    probabilities = {}
    for i, class_name in enumerate(_anomaly_encoder.classes_):
        probabilities[class_name] = round(float(proba[i]), 4)

    return {
        'label': label,
        'confidence': confidence,
        'probabilities': probabilities,
        'is_anomaly': label != 'Normal'
    }


# CONVENIENCE: BATCH DETECTION FOR ALL ACTIVE DRONES

def detect_anomalies_batch(telemetry_list: list) -> list:
    """
    Run anomaly detection for a list of drone telemetry dicts.
    Useful for the simulation step where multiple drones are checked at once.

    Parameters
    ----------
    telemetry_list : list of dict -- Each dict must have the same keys as
                      detect_anomaly() parameters.

    Returns
    -------
    list of dict -- Same order as input, each entry is the result dict
                   from detect_anomaly(), with an added 'drone_id' key.
    """
    results = []
    for reading in telemetry_list:
        drone_id = reading.pop('drone_id', 'Unknown')
        result = detect_anomaly(**reading)
        result['drone_id'] = drone_id
        reading['drone_id'] = drone_id
        results.append(result)
    return results



# RULE-BASED FALLBACK (if .pkl files don't exist yet)

def detect_anomaly_rule_based(
    battery_drop: float = 0.0,
    route_deviation: float = 0.0,
    altitude_change: float = 0.0,
    speed_change: float = 0.0
) -> str:
    """
    Rule-based anomaly detection -- used as a fallback if the trained
    model .pkl is not available, or for verification / comparison.

    These are the SAME threshold rules used to generate synthetic labels
    in the notebook:

        battery_drop   > 30  -> Battery Anomaly
        route_deviation > 5  -> Route Anomaly
        altitude_change > 15 OR speed_change > 8 -> Sensor Spike
        otherwise            -> Normal

    Priority: Battery > Route > Sensor > Normal
    """
    if battery_drop > 30:
        return 'Battery Anomaly'
    elif route_deviation > 5:
        return 'Route Anomaly'
    elif altitude_change > 15 or speed_change > 8:
        return 'Sensor Spike'
    else:
        return 'Normal'

# MODEL STATUS / DIAGNOSTICS

def get_model_status() -> dict:
    """
    Check which models are loaded and ready. Useful for debugging
    and for printing a status message at simulation start.
    """
    status = {
        'demand_model_loaded': _demand_model is not None,
        'demand_scaler_loaded': _demand_scaler is not None,
        'anomaly_model_loaded': _anomaly_model is not None,
        'anomaly_scaler_loaded': _anomaly_scaler is not None,
        'anomaly_encoder_loaded': _anomaly_encoder is not None,
    }

    status['demand_model_on_disk'] = os.path.exists(
        os.path.join(PROCESSED_DIR, _DEMAND_MODEL_FILE))
    status['anomaly_model_on_disk'] = os.path.exists(
        os.path.join(PROCESSED_DIR, _ANOMALY_MODEL_FILE))

    all_ready = all([
        status['demand_model_on_disk'],
        status['anomaly_model_on_disk']
    ])
    status['all_artifacts_available'] = all_ready

    return status


def print_model_status():
    """Print a human-readable model status report."""
    s = get_model_status()
    print("-" * 55)
    print("  ML PIPELINE -- MODEL STATUS")
    print("-" * 55)
    print(f"  Demand model on disk  : {'Yes' if s['demand_model_on_disk'] else 'No'}")
    print(f"  Demand model loaded   : {'Yes' if s['demand_model_loaded'] else 'Pending (will load on first call)'}")
    print(f"  Anomaly model on disk : {'Yes' if s['anomaly_model_on_disk'] else 'No'}")
    print(f"  Anomaly model loaded  : {'Yes' if s['anomaly_model_loaded'] else 'Pending (will load on first call)'}")
    print(f"  All artifacts ready   : {'Yes' if s['all_artifacts_available'] else 'No (Run notebooks first!)'}")
    print("-" * 55)



# DEMAND -> GRID CELL ASSIGNMENT (for fleet selector integration)


def assign_demand_to_grid(grid: list, hour: int = 12, season: int = 1,
                          holiday: int = 0, workingday: int = 1,
                          weather: int = 1, seed: int = None) -> list:
    """
    Take the shared 10x10 grid model (list of list of dicts) and
    populate the 'demand' field in each cell using the forecasting model.

    Parameters
    ----------
    grid       : list of list of dict -- The shared 10x10 grid model.
    hour       : int -- Simulation hour.
    season     : int -- Season code.
    holiday    : int -- Holiday flag.
    workingday : int -- Working day flag.
    weather    : int -- Weather code.
    seed       : int -- Optional seed for reproducibility.

    Returns
    -------
    list -- The same grid object with 'demand' field updated in each cell.
    """
    demand_array = get_grid_demand(
        hour=hour, season=season, holiday=holiday,
        workingday=workingday, weather=weather,
        grid_size=len(grid), seed=seed
    )

    for r, row in enumerate(grid):
        for c, cell in enumerate(row):
            cell['demand'] = int(demand_array[r][c])

    return grid



# STANDALONE TEST / DEMO

if __name__ == '__main__':
    print("\n" + "-" * 60)
    print("  AERONET LITE -- ML Pipeline Self-Test")
    print("-" * 60 + "\n")

    # 1. Check model status
    print_model_status()
    print()

    # 2. Test demand forecasting
    print("-" * 60)
    print("  DEMAND FORECASTING TESTS")
    print("-" * 60)

    test_scenarios = [
        {"hour": 8,  "season": 2, "workingday": 1, "weather": 1, "temp": 0.7, "label": "Summer weekday morning rush"},
        {"hour": 14, "season": 1, "workingday": 1, "weather": 1, "temp": 0.5, "label": "Spring weekday afternoon"},
        {"hour": 22, "season": 3, "workingday": 0, "weather": 2, "temp": 0.4, "label": "Fall weekend night"},
        {"hour": 6,  "season": 4, "workingday": 1, "weather": 3, "temp": 0.2, "label": "Winter weekday rainy morning"},
    ]

    for scenario in test_scenarios:
        label = scenario.pop('label')
        demand = get_demand_forecast(**scenario)
        print(f"  {label:40s} -> Demand: {demand}")

    # 3. Test grid demand
    print(f"\n  Grid demand (5x5 corner, hour=14):")
    grid = get_grid_demand(hour=14, season=2, workingday=1, grid_size=10, seed=42)
    for r in range(5):
        row_str = "    " + "  ".join(f"{grid[r][c]:4.0f}" for c in range(5))
        print(row_str)

    # 4. Test anomaly detection
    print("\n" + "-" * 60)
    print("  ANOMALY DETECTION TESTS")
    print("-" * 60)

    anomaly_tests = [
        {"battery_level": 80, "battery_drop": 2.5, "altitude": 50,
         "altitude_change": 1.2, "speed": 8, "speed_change": 0.5,
         "route_deviation": 0.3, "label": "Normal flight"},

        {"battery_level": 45, "battery_drop": 38.0, "altitude": 50,
         "altitude_change": 2.1, "speed": 8, "speed_change": 1.0,
         "route_deviation": 1.2, "label": "Battery anomaly"},

        {"battery_level": 70, "battery_drop": 3.0, "altitude": 52,
         "altitude_change": 1.5, "speed": 6, "speed_change": 0.5,
         "route_deviation": 8.7, "label": "Route anomaly"},

        {"battery_level": 75, "battery_drop": 2.0, "altitude": 55,
         "altitude_change": 22.0, "speed": 14, "speed_change": 11.0,
         "route_deviation": 0.8, "label": "Sensor spike"},

        {"battery_level": 40, "battery_drop": 45.0, "altitude": 55,
         "altitude_change": 18.0, "speed": 14, "speed_change": 10.0,
         "route_deviation": 9.0, "label": "Multiple anomalies (priority test)"},
    ]

    for test in anomaly_tests:
        label = test.pop('label')
        result = detect_anomaly(**test)
        print(f"  {label:40s} -> {result['label']:20s} "
              f"(confidence: {result['confidence']:.2f}, "
              f"is_anomaly: {result['is_anomaly']})")

    # 5. Test batch detection
    print("\n  Batch detection test:")
    batch = [
        {"drone_id": "D1", "battery_level": 80, "battery_drop": 2,
         "altitude": 50, "altitude_change": 1, "speed": 8,
         "speed_change": 0.5, "route_deviation": 0.3},
        {"drone_id": "D2", "battery_level": 45, "battery_drop": 38,
         "altitude": 50, "altitude_change": 2, "speed": 8,
         "speed_change": 1, "route_deviation": 1.0},
        {"drone_id": "D3", "battery_level": 70, "battery_drop": 3,
         "altitude": 52, "altitude_change": 1.5, "speed": 6,
         "speed_change": 0.5, "route_deviation": 8.7},
    ]
    batch_results = detect_anomalies_batch(batch)
    for r in batch_results:
        print(f"    {r['drone_id']}: {r['label']} (confidence: {r['confidence']:.2f})")

    # 6. Test rule-based fallback
    print("\n  Rule-based fallback test:")
    print(f"    battery_drop=35  -> {detect_anomaly_rule_based(battery_drop=35)}")
    print(f"    route_dev=8      -> {detect_anomaly_rule_based(route_deviation=8)}")
    print(f"    alt_change=20    -> {detect_anomaly_rule_based(altitude_change=20)}")
    print(f"    all normal       -> {detect_anomaly_rule_based()}")

    # 7. Test assign_demand_to_grid
    print("\n  Grid assignment test (3x3 mini-grid):")
    mini_grid = [[{"row": r, "col": c, "demand": 0} for c in range(3)] for r in range(3)]
    assign_demand_to_grid(mini_grid, hour=14, season=2, seed=42)

    for r in range(3):
        demands = [str(mini_grid[r][c]['demand']) for c in range(3)]
        print(f"    Row {r}: [{', '.join(demands)}]")

    print("\n" + "-" * 60)
    print("  ML Pipeline self-test complete.")
    print("-" * 60 + "\n")