import html as html_module
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import streamlit as st

from grid_data import GRID, GRID_SIZE, get_all_of_type

# Same palette as Fleet Selector “Fitness Landscape” (warm cream → sand → rose mauve).
_DEMAND_HEATMAP_CMAP = LinearSegmentedColormap.from_list(
    "aeronet_demand",
    ["#f4f1ea", "#e8d8be", "#d9b88a", "#c48a7a", "#8b4a5c", "#5a2d40"],
)
from grid_render import ZONE_BG, legend_letter_glyph, render_grid_html
from styles import inject_css
from csp_validator import run_all_constraints


st.set_page_config(
    page_title="AeroNet Lite",
    page_icon="🛰️",
    layout="wide",
)

# Session state
if "violations_count" not in st.session_state:
    st.session_state["violations_count"] = 0
if "validation_run" not in st.session_state:
    st.session_state["validation_run"] = False

inject_css()

if not st.session_state.get("validation_run", False):
    # After Reset Everything, `_suppress_home_csp_hydrate` keeps violations at 0 until the user runs
    # CSP Validator (otherwise we'd immediately recomputed the static GRID tally and undo the reset).
    if st.session_state.get("_suppress_home_csp_hydrate", False):
        if "violations_count" not in st.session_state:
            st.session_state["violations_count"] = 0
    else:
        raw = run_all_constraints(GRID)
        total = 0
        for rid, info in raw.items():
            if rid == "R4":
                if not bool(info.get("satisfied", True)):
                    total += 1
            else:
                total += len(info.get("violations", []))
        st.session_state["violations_count"] = total

DRONE_SVG = """
<svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true"
     xmlns="http://www.w3.org/2000/svg">
  <path d="M7 7h10" stroke="#405C6F" stroke-width="2" stroke-linecap="round"/>
  <path d="M7 17h10" stroke="#405C6F" stroke-width="2" stroke-linecap="round"/>
  <path d="M9 12h6" stroke="#50314B" stroke-width="2" stroke-linecap="round"/>
  <path d="M8 10.5l-3-3" stroke="#96A3B4" stroke-width="2" stroke-linecap="round"/>
  <path d="M16 10.5l3-3" stroke="#96A3B4" stroke-width="2" stroke-linecap="round"/>
  <path d="M8 13.5l-3 3" stroke="#96A3B4" stroke-width="2" stroke-linecap="round"/>
  <path d="M16 13.5l3 3" stroke="#96A3B4" stroke-width="2" stroke-linecap="round"/>
  <circle cx="5" cy="7.5" r="1.5" fill="#6BB1AD"/>
  <circle cx="19" cy="7.5" r="1.5" fill="#6BB1AD"/>
  <circle cx="5" cy="16.5" r="1.5" fill="#6BB1AD"/>
  <circle cx="19" cy="16.5" r="1.5" fill="#6BB1AD"/>
</svg>
"""

st.markdown(
    f"""
<div style="display:flex; align-items:center; gap:10px; margin-top: 0.25rem;">
  {DRONE_SVG}
  <div>
    <div style="font-size:2.1rem; font-weight:800; letter-spacing:-0.02em; color:#50314B; line-height:1.05;">
      AeroNet Lite
    </div>
    <div style="margin-top:0.2rem; color:#405C6F; font-weight:600;">
      Autonomous Drone Delivery Simulation
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)
st.divider()

# Match Simulation “System readiness” scale (slightly larger than default st.metric).
_HOME_MLBL = "#405C6F"
_HOME_MVAL = "#411E57"
_HOME_LBL_PX = 17
_HOME_VAL_PX = "1.5rem"

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(
        f"<span style='color:{_HOME_MLBL};font-weight:800;font-size:{_HOME_LBL_PX}px'>Grid Cells</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='font-size:{_HOME_VAL_PX};font-weight:750;color:{_HOME_MVAL};margin-top:2px'>"
        f"{html_module.escape('100')}</div>",
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        f"<span style='color:{_HOME_MLBL};font-weight:800;font-size:{_HOME_LBL_PX}px'>Active Drones</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='font-size:{_HOME_VAL_PX};font-weight:750;color:{_HOME_MVAL};margin-top:2px'>"
        f"{html_module.escape('8')}</div>",
        unsafe_allow_html=True,
    )
with col3:
    _nfz = len(get_all_of_type("no_fly", True))
    st.markdown(
        f"<span style='color:{_HOME_MLBL};font-weight:800;font-size:{_HOME_LBL_PX}px'>No-Fly Zones</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='font-size:{_HOME_VAL_PX};font-weight:750;color:{_HOME_MVAL};margin-top:2px'>"
        f"{html_module.escape(str(_nfz))}</div>",
        unsafe_allow_html=True,
    )
with col4:
    _vc = st.session_state["violations_count"]
    st.markdown(
        f"<span style='color:{_HOME_MLBL};font-weight:800;font-size:{_HOME_LBL_PX}px'>CSP Violations</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='font-size:{_HOME_VAL_PX};font-weight:750;color:{_HOME_MVAL};margin-top:2px'>"
        f"{html_module.escape(str(_vc))}</div>",
        unsafe_allow_html=True,
    )

with st.expander("Reset System"):
    st.markdown(
        "<div style='background:#EDECDB;border-radius:14px;border:1px solid rgba(24,26,30,0.12);padding:14px 14px;box-shadow:0 10px 24px rgba(24,26,30,0.06);'>"
        "<div style='color:#405C6F;font-weight:650;font-size:13px;line-height:1.45'>"
        "Clears all session state across all pages. Use this to start a fresh simulation run."
        "</div></div>",
        unsafe_allow_html=True,
    )
    if st.button("Reset Everything", type="primary", use_container_width=True):
        keys_to_clear = [
            "violations_count",
            "validation_run",
            "rule_results",
            "selected_fleet",
            "fleet_score",
            "fleet_budget",
            "fleet_method",
            "fleet_ga_cache_fleet",
            "fleet_ga_cache_score",
            "fleet_ga_cache_budget",
            "path_full_path",
            "path_total_cost",
            "path_segments",
            "path_success",
            "path_planned",
            "path_hub",
            "path_pickup",
            "path_dropoff",
            "path_extra_nf",
            "extra_nf_set",
            "dh_active_nf",
            "dh_event_log",
            "dh_rerouted_path",
            "dh_rerouted_cost",
            "dh_rerouted_ok",
            "ml_demand_pred",
            "ml_grid_demand",
            "ml_demand_error",
            "ml_anomaly_result",
            "ml_anomaly_error",
            "ml_anomaly_fallback",
            "anomaly_alert",
            "_last_demand_inputs",
            "_last_anomaly_inputs",
            "sim_run",
            "sim_event_log",
            "sim_completed",
            "sim_delayed",
            "sim_failed",
            "sim_no_fly_cell",
            "sim_no_fly_event_count",
        ]
        for k in keys_to_clear:
            if k in st.session_state:
                del st.session_state[k]
        st.session_state["_suppress_home_csp_hydrate"] = True
        st.success("System reset. All pages cleared.")
        st.rerun()

grid_col, legend_col = st.columns([8, 4], gap="large")

with grid_col:
    st.markdown(render_grid_html(GRID, cell_px=58, show_symbols=True), unsafe_allow_html=True)

with legend_col:
    st.markdown(
        "<div style='font-weight:900; font-size:22px; color:#181A1E; margin-top:6px; margin-bottom:6px;'>Legend</div>",
        unsafe_allow_html=True,
    )

    def swatch(zone: str) -> str:
        color = ZONE_BG[zone]
        return f"<span class='zone-swatch' data-zone='{zone}' style='background:{color};'></span>"

    legend_lines = [
        "<div style='font-weight:800; color:#50314B; margin-bottom:6px;'>Zone Colors</div>",
        f"{swatch('Residential')}Residential",
        f"{swatch('Industrial')}Industrial",
        f"{swatch('Commercial')}Commercial",
        f"{swatch('Hospital')}Hospital",
        f"{swatch('School')}School",
        f"{swatch('Open Field')}Open Field",
        "<hr style='border:none;border-top:1px solid rgba(24,26,30,0.15); margin:12px 0;'/>",
        "<div style='font-weight:800; color:#50314B; margin-bottom:6px;'>Cell markers</div>",
        "<div style='line-height:1.9'>"
        f"<div style='display:flex;align-items:center;margin:6px 0' title='Hub (Drone base)'>{legend_letter_glyph('D', fg='#181A1E')}Hub</div>"
        f"<div style='display:flex;align-items:center;margin:6px 0' title='Charging pad'>{legend_letter_glyph('C', fg='#181A1E')}Charging</div>"
        f"<div style='display:flex;align-items:center;margin:6px 0' title='Medical pickup point'>{legend_letter_glyph('M', fg='#181A1E')}Medical pickup</div>"
        f"<div style='display:flex;align-items:center;margin:6px 0' title='No-fly zone'>"
        f"{legend_letter_glyph('N', fg='#EDECDB', bg='#F75E74')}No-fly</div>"
        "</div>",
        "<div style='margin-top:10px; color:#405C6F; font-size:12px;'>Tip: hover a cell to see details.</div>",
    ]
    st.markdown("<br/>".join(legend_lines), unsafe_allow_html=True)

st.markdown(
    "<div aria-hidden='true' style='height:2rem;margin-top:0.5rem;'></div>",
    unsafe_allow_html=True,
)
with st.expander("Demand Heatmap"):
    st.caption(
        "Live values from each cell’s **`demand`** field in `grid_data.GRID` (typically ~0.15–0.95 by zone). "
        "Colormap matches **Fleet Selector → Fitness Landscape** (cream → sand → mauve)."
    )
    demand_arr = np.array(
        [[GRID[r * GRID_SIZE + c]["demand"] for c in range(GRID_SIZE)] for r in range(GRID_SIZE)],
        dtype=float,
    )
    _bg = "#EDE9DB"
    _panel = "#f4f2ec"
    _ink = "#50314B"
    _muted = "#405C6F"

    fig, ax = plt.subplots(figsize=(6.5, 5.2))
    fig.patch.set_facecolor(_bg)
    ax.set_facecolor(_panel)
    im = ax.imshow(
        demand_arr,
        cmap=_DEMAND_HEATMAP_CMAP,
        vmin=0.0,
        vmax=1.0,
        aspect="equal",
        origin="upper",
    )
    ax.set_xticks(range(GRID_SIZE))
    ax.set_yticks(range(GRID_SIZE))
    ax.set_xlabel("Column", color=_ink, fontweight=600)
    ax.set_ylabel("Row", color=_ink, fontweight=600)
    ax.tick_params(axis="both", colors=_muted, labelsize=10)
    _edge = (36 / 255, 42 / 255, 54 / 255, 0.35)
    for spine in ax.spines.values():
        spine.set_edgecolor(_edge)
    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Demand weight", color=_ink, fontweight=600)
    cbar.ax.tick_params(colors=_muted)
    cbar.outline.set_edgecolor(_edge)
    fig.tight_layout()
    st.pyplot(fig, clear_figure=True)
    plt.close(fig)

