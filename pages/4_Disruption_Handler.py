import sys, os

# Pages dir (matches spec); project root ensures `astar_planner` / `grid_data` resolve
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from astar_planner import astar, plan_delivery_route  # noqa: F401
from grid_data import GRID, get_all_of_type  # noqa: F401
from grid_adapter import build_adapter_grid
from grid_render import render_grid_html
from styles import inject_css


st.set_page_config(page_title="Disruption Handler • AeroNet Lite", page_icon="⚠️", layout="wide")
inject_css()

DISRUPT_SVG = """<svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
<path d="M12 3l9 17H3L12 3z" stroke="#b06d5a" stroke-width="1.6" stroke-linejoin="round" fill="rgba(245,228,218,0.35)"/>
<path d="M12 9v5" stroke="#50314B" stroke-width="2" stroke-linecap="round"/>
<circle cx="12" cy="16.5" r="1.1" fill="#50314B"/>
</svg>"""

ribbon_html = f"""<div class="aeronet-top-ribbon">
<div style="display:flex;align-items:center;justify-content:space-between;gap:14px;">
<div style="display:flex;align-items:center;gap:10px;">
{DISRUPT_SVG}
<div>
<div style="font-size:1.75rem;font-weight:850;letter-spacing:-0.02em;color:#50314B;line-height:1.05;">Disruption Handler</div>
<div style="margin-top:0.15rem;color:#405C6F;font-weight:600;">Module 4 — Real-Time No-Fly Activation and A* Rerouting</div>
</div>
</div>
</div>
</div>"""
st.markdown(ribbon_html, unsafe_allow_html=True)

# SECTION 1 — Anomaly Alert Banner
alert = st.session_state.get("anomaly_alert")
if alert:
    label = str(alert.get("label", ""))
    conf = float(alert.get("confidence", 0.0))
    drone = str(alert.get("drone", ""))
    st.error(
        f"Anomaly alert — {label} (confidence {int(round(conf * 100))}%) · Drone {drone}."
    )
    st.caption("Activate a no-fly cell below to simulate forced rerouting.")
else:
    st.caption("No active anomaly from ML Pipeline. You can still simulate no-fly disruptions below.")

st.write("")

# SECTION 2 — Route Context
path_hub = st.session_state.get("path_hub")
path_pickup = st.session_state.get("path_pickup")
path_dropoff = st.session_state.get("path_dropoff")
path_full_path = st.session_state.get("path_full_path", [])
path_success = st.session_state.get("path_success", False)
fleet = st.session_state.get("selected_fleet")

if path_hub is None or not path_success:
    st.warning("No planned route found. Go to Path Planner first and plan a route.")
    st.stop()

st.markdown(
    "<div style='font-weight:820;color:#3a3142;font-size:14px;margin:0 0 10px;'>Route context</div>",
    unsafe_allow_html=True,
)
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"**Hub**  \n{path_hub}")
with c2:
    st.markdown(f"**Pickup**  \n{path_pickup}")
with c3:
    st.markdown(f"**Drop-off**  \n{path_dropoff}")

if fleet:
    st.info(
        f"Fleet: {fleet['light']} light, {fleet['heavy']} heavy drones from Fleet Selector."
    )

st.write("")
st.markdown("---")

# SECTION 3 — Activate No-Fly Cell
st.subheader("Activate No-Fly Disruption")

nf_r, nf_c = st.columns(2)
with nf_r:
    nf_row = st.number_input("No-Fly Row", min_value=0, max_value=9, value=0, step=1, key="dh_nf_row")
with nf_c:
    nf_col = st.number_input("No-Fly Col", min_value=0, max_value=9, value=0, step=1, key="dh_nf_col")

b1, b2 = st.columns([1, 1])
with b1:
    activate = st.button("Activate No-Fly Cell", type="primary", use_container_width=True)
with b2:
    reset_disrupt = st.button("Reset Disruptions", use_container_width=True)

if reset_disrupt:
    st.session_state["dh_active_nf"] = set()
    st.session_state["dh_event_log"] = []
    st.session_state["dh_rerouted_path"] = []
    if "dh_rerouted_ok" in st.session_state:
        del st.session_state["dh_rerouted_ok"]
    st.rerun()

if activate:
    new_nf = (int(nf_row), int(nf_col))
    if new_nf in st.session_state.get("dh_active_nf", set()):
        st.warning(f"Cell {new_nf} is already a no-fly zone.")
        st.stop()

    crosses = new_nf in path_full_path

    st.session_state.setdefault("dh_active_nf", set())
    merged_nf = (
        st.session_state.get("extra_nf_set", set())
        | st.session_state["dh_active_nf"]
        | {new_nf}
    )
    adapted_grid = build_adapter_grid(GRID, extra_no_fly=merged_nf)

    st.session_state["dh_active_nf"].add(new_nf)

    log_entries = list(st.session_state.get("dh_event_log", []))
    log_entries.append(f"No-fly cell activated at {new_nf}")

    if crosses:
        log_entries.append(f"Route crosses newly blocked cell {new_nf} — rerouting with A*...")
        new_path, new_cost, _new_segments, new_ok = plan_delivery_route(
            path_hub, path_pickup, path_dropoff, adapted_grid
        )
        if new_ok:
            st.session_state["dh_rerouted_path"] = new_path
            st.session_state["dh_rerouted_cost"] = new_cost
            st.session_state["dh_rerouted_ok"] = True
            log_entries.append(
                f"Drone rerouted successfully using A* — new cost: {new_cost}, steps: {len(new_path)}"
            )
        else:
            st.session_state["dh_rerouted_ok"] = False
            st.session_state["dh_rerouted_path"] = []
            log_entries.append(
                "FAILED: No safe path exists after disruption. Delivery marked as DELAYED."
            )
    else:
        log_entries.append(f"Cell {new_nf} blocked — original route is unaffected.")
        st.session_state["dh_rerouted_path"] = list(path_full_path)
        st.session_state["dh_rerouted_cost"] = st.session_state.get("path_total_cost", 0)
        st.session_state["dh_rerouted_ok"] = True

    st.session_state["dh_event_log"] = log_entries
    st.rerun()

st.write("")

# SECTION 4 — Event Log
st.subheader("Event Log")
log = st.session_state.get("dh_event_log", [])
if not log:
    st.info("No disruptions triggered yet.")
else:
    st.markdown(
        """
<style>
/* Event log: Streamlit syntax-highlighting uses dark token colors; force one readable palette. */
section[data-testid="stMain"] [data-testid="stCode"] {
  background: #EDE9DF !important;
  border-radius: 10px !important;
}
section[data-testid="stMain"] [data-testid="stCode"] pre {
  background: #EDE9DF !important;
  color: #261e2e !important;
  border: 1px solid rgba(36, 26, 48, 0.22) !important;
  border-radius: 10px !important;
  padding: 12px 14px !important;
  font-family: ui-monospace, monospace !important;
}
section[data-testid="stMain"] [data-testid="stCode"] pre code,
section[data-testid="stMain"] [data-testid="stCode"] pre span,
section[data-testid="stMain"] [data-testid="stCode"] pre * {
  color: #261e2e !important;
  background: transparent !important;
  background-color: transparent !important;
}
</style>
        """,
        unsafe_allow_html=True,
    )
    for i, entry in enumerate(log, start=1):
        st.code(f"Step {i}\n{entry}", language=None)

st.write("")

# SECTION 5 — Grid Visualization
st.subheader("Grid Visualization")

active_nf = list(st.session_state.get("dh_active_nf", set()))
rerouted_path = st.session_state.get("dh_rerouted_path", [])
original_path = path_full_path
endpoints = {path_hub, path_pickup, path_dropoff}

highlights = {
    "ORIGINAL": [c for c in original_path if c not in endpoints],
    "REROUTED": [
        c
        for c in rerouted_path
        if c not in endpoints and c not in original_path
    ],
    "HUB": [path_hub],
    "PICKUP": [path_pickup],
    "DROPOFF": [path_dropoff],
    "NEWNOFLY": active_nf,
}
highlight_styles = {
    "ORIGINAL": "outline: 2px dashed #9AABBA; outline-offset:-2px;",
    "REROUTED": "outline: 3px solid #6BB1AD; outline-offset:-3px;",
    "HUB": "outline: 3px solid #411E57; outline-offset:-3px;",
    "PICKUP": "outline: 3px solid #6BB1AD; outline-offset:-3px;",
    "DROPOFF": "outline: 3px solid #DE5C8F; outline-offset:-3px;",
    "NEWNOFLY": "outline: 3px solid #F75E74; outline-offset:-3px;",
}

st.markdown(
    render_grid_html(
        GRID,
        cell_px=54,
        highlights=highlights,
        highlight_styles=highlight_styles,
        show_symbols=True,
        highlight_on="inner",
    ),
    unsafe_allow_html=True,
)

legend_parts = [
    ("Original corridor (dashed)", "#9AABBA", "dashed"),
    ("Rerouted segment (new)", "#6BB1AD", "solid"),
    ("Hub", "#411E57", "solid"),
    ("Pickup / Drop-off rings", "#6BB1AD / #DE5C8F", "solid"),
    ("Activated no-fly", "#F75E74", "solid"),
]
legend_html = "<div style='display:flex;flex-wrap:wrap;gap:8px 14px;margin-top:12px;'>"
for label, color, _style in legend_parts:
    legend_html += (
        f"<div style='display:inline-flex;align-items:center;gap:6px;font-weight:700;"
        f"font-size:12px;color:#3a3142;'><span style='display:inline-block;width:14px;height:14px;"
        f"border-radius:4px;border:2px solid {color};background:transparent;'></span>{label}</div>"
    )
legend_html += "</div>"
st.markdown(legend_html, unsafe_allow_html=True)

st.write("")

# SECTION 6 — Route Comparison
if st.session_state.get("dh_rerouted_ok") is not None:
    st.subheader("Route Comparison")
    old_cost = float(st.session_state.get("path_total_cost", 0))
    new_cost = float(st.session_state.get("dh_rerouted_cost", 0))
    rp = st.session_state.get("dh_rerouted_path", [])
    steps_delta = len(rp) - len(original_path)
    ok = bool(st.session_state.get("dh_rerouted_ok"))

    m1, m2, m3 = st.columns(3)
    m1.metric("Original cost", f"{old_cost}")
    m2.metric("New cost", f"{new_cost}" if ok else "—")
    m3.metric("Steps change", f"{steps_delta:+d}" if ok else "N/A")

    if not ok:
        st.error("Delivery DELAYED — no safe path exists after disruption.")
    elif new_cost > old_cost:
        st.warning(f"Detour added {round(new_cost - old_cost, 2)} cost units.")
    else:
        st.success("Reroute found with equal or lower cost.")
