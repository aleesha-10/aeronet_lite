import html as html_module
import os
import re
import sys
import time  # noqa: F401
from dataclasses import dataclass
from typing import Optional, Set

import streamlit as st

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

_PAGES_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_PAGES_DIR)
for _p in (_PROJECT_ROOT, _PAGES_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from astar_planner import plan_delivery_route  # noqa: F401, E402
from csp_validator import run_all_constraints  # noqa: F401, E402
from delivery_simulator import Delivery, DeliverySimulator, Drone  # noqa: E402
from grid_data import GRID, GRID_SIZE, get_all_of_type  # noqa: E402
from grid_render import render_grid_html  # noqa: E402
from styles import inject_css  # noqa: E402


@dataclass
class CellAdapter:
    row: int
    col: int
    no_fly: bool = False
    is_commercial_corridor: bool = False


def build_adapter_grid(grid_dicts, extra_no_fly: Optional[Set] = None):
    extra_no_fly = extra_no_fly or set()
    adapted = []
    for cell in grid_dicts:
        adapted.append(
            CellAdapter(
                row=cell["row"],
                col=cell["col"],
                no_fly=cell["no_fly"] or (cell["row"], cell["col"]) in extra_no_fly,
                is_commercial_corridor=(cell["zone"] == "Commercial"),
            )
        )
    return [adapted[r * 10 : (r + 1) * 10] for r in range(10)]


TEAL = "#399DB5"
PINK = "#E9819A"
PURPLE = "#411E57"
MAUVE = "#E092A7"
BG = "#FBC8CC"

# Home / Fleet heatmaps use sand → rose mauve; Simulation uses the same parchment frame but a
# teal-forward ramp so it reads distinctly while staying on-palette with AeroNet Lite.
_SIM_DEMAND_HEATMAP_CMAP = LinearSegmentedColormap.from_list(
    "aeronet_sim_demand",
    [
        "#f4f1ea",
        "#fce8ec",
        BG,
        MAUVE,
        "#c4dfe8",
        TEAL,
        "#5d3a73",
        PURPLE,
    ],
)

# Matches App.py “Demand Heatmap” expander (paper + axis panel).
_HM_FIG_BG = "#EDE9DB"
_HM_AX_BG = "#f4f2ec"
_HM_INK = "#50314B"
_HM_MUTED = "#405C6F"
_HM_SPINE_EDGE = (36 / 255, 42 / 255, 54 / 255, 0.35)


def _purple_rgb() -> tuple[int, int, int]:
    return int(PURPLE[1:3], 16), int(PURPLE[3:5], 16), int(PURPLE[5:7], 16)


def _hex_rgba(hex_color: str, alpha: float) -> str:
    r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
    return f"rgba({r},{g},{b},{alpha})"


st.set_page_config(page_title="20-Step Simulation • AeroNet Lite", page_icon="📊", layout="wide")
inject_css()

matplotlib.rcParams["figure.facecolor"] = "none"
rp, gp, bp = _purple_rgb()
matplotlib.rcParams["axes.facecolor"] = (rp / 255.0, gp / 255.0, bp / 255.0, 0.08)


SIM_SVG = f"""<svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
<polygon points="8,5 19,12 8,19 8,5" fill="{TEAL}" stroke="{TEAL}" stroke-width="1.2" stroke-linejoin="round"/>
<circle cx="6" cy="12" r="2" fill="{PINK}"/>
</svg>"""

st.markdown(
    f"""<div class="aeronet-top-ribbon">
<div style="display:flex;align-items:center;gap:10px;">
{SIM_SVG}
<div>
<div style="font-size:1.75rem;font-weight:850;letter-spacing:-0.02em;color:{PURPLE};line-height:1.05;">20-Step Simulation</div>
<div style="margin-top:0.15rem;color:{PURPLE};opacity:0.72;font-weight:600;">Module Integration — Full AeroNet Lite Demo</div>
</div>
</div>
</div>""",
    unsafe_allow_html=True,
)

# SECTION 1 — System readiness
st.markdown(
    f"<div style='font-weight:800;color:{PURPLE};margin:8px 0 12px;font-size:15px'>System readiness</div>",
    unsafe_allow_html=True,
)

path_success = bool(st.session_state.get("path_success"))
selected_fleet = st.session_state.get("selected_fleet")
c1, c2, c3, c4, c5 = st.columns(5)
_lbl = 17
_val = "1.5rem"
with c1:
    st.markdown(f"<span style='color:{PURPLE};font-weight:800;font-size:{_lbl}px'>CSP</span>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='font-size:{_val};font-weight:650;color:{PURPLE};margin-top:2px'>"
        f"{html_module.escape(str(st.session_state.get('violations_count', '—')))}</div>",
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(f"<span style='color:{TEAL};font-weight:800;font-size:{_lbl}px'>Fleet</span>", unsafe_allow_html=True)
    if selected_fleet:
        _fv = html_module.escape(f"{selected_fleet['light']}L + {selected_fleet['heavy']}H")
    else:
        _fv = html_module.escape("Not selected")
    st.markdown(f"<div style='font-size:{_val};font-weight:650;color:{PURPLE};margin-top:2px'>{_fv}</div>", unsafe_allow_html=True)
with c3:
    st.markdown(f"<span style='color:{MAUVE};font-weight:800;font-size:{_lbl}px'>Demand</span>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='font-size:{_val};font-weight:650;color:{PURPLE};margin-top:2px'>"
        f"{html_module.escape(str(st.session_state.get('ml_demand_pred', '—')))}</div>",
        unsafe_allow_html=True,
    )
with c4:
    st.markdown(f"<span style='color:{PINK};font-weight:800;font-size:{_lbl}px'>Anomaly</span>", unsafe_allow_html=True)
    _aa = st.session_state.get("anomaly_alert") or {}
    _lab = (
        str(_aa.get("label"))
        if isinstance(_aa, dict) and _aa.get("label")
        else "None"
    )
    _an = html_module.escape(_lab if _lab else "None")
    st.markdown(f"<div style='font-size:{_val};font-weight:650;color:{PURPLE};margin-top:2px'>{_an}</div>", unsafe_allow_html=True)
with c5:
    st.markdown(f"<span style='color:{PURPLE};font-weight:800;font-size:{_lbl}px'>Route</span>", unsafe_allow_html=True)
    _rt = html_module.escape("Planned" if path_success else "Not planned")
    st.markdown(f"<div style='font-size:{_val};font-weight:650;color:{PURPLE};margin-top:2px'>{_rt}</div>", unsafe_allow_html=True)

if not selected_fleet:
    st.warning("Go to Fleet Selector first and select a fleet.")
    st.stop()

# SECTION 2 — Simulation config
st.markdown(
    f"<div style='font-weight:800;color:{PURPLE};margin:16px 0 10px;font-size:15px'>Simulation configuration</div>",
    unsafe_allow_html=True,
)
col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
with col_cfg1:
    no_fly_step = st.slider("No-fly activation step", 8, 15, 11)
    anomaly_step = st.slider("Anomaly detection step", 15, 19, 18)
with col_cfg2:
    no_fly_cell_row = st.number_input("No-fly cell row", 0, 9, 4)
    no_fly_cell_col = st.number_input("No-fly cell col", 0, 9, 7)

with col_cfg3:
    st.write("")
    st.caption("Tune disruption timing alongside the scripted 20-step ledger.")

if "sim_run" not in st.session_state:
    st.session_state["sim_run"] = False


def _log_stripe_rgb(i: int) -> tuple[int, int, int, float]:
    r, g, b = _purple_rgb()
    a = 0.28 if i % 2 == 0 else 0.42
    return r, g, b, a


def _render_event_panel(lines: list) -> None:
    inner_chunks: list[str] = []
    for i, line in enumerate(lines):
        rr, gg, bb, aa = _log_stripe_rgb(i)
        base_style = (
            f"padding:10px 12px;border-radius:10px;line-height:1.45;margin:6px 0;"
            f"background:rgba({rr},{gg},{bb},{aa:.2f});"
        )
        m = re.match(r"^(Step\s+\d+)\s*:\s*(.+)$", line)
        if m:
            hl = html_module.escape(m.group(1))
            bd = html_module.escape(m.group(2).strip())
            inner_chunks.append(
                f"<div style='{base_style}display:flex;gap:14px'>"
                f"<div style=\"color:{TEAL};font-weight:850;width:96px;font-variant-numeric:tabular-nums;\">{hl}</div>"
                f"<div style='color:{BG};opacity:0.96;flex:1'>{bd}</div>"
                "</div>"
            )
        else:
            inner_chunks.append(
                f"<div style='{base_style}color:{BG};'>{html_module.escape(line)}</div>"
            )
    st.markdown(
        f"<div style='border-radius:16px;background:#1a0f24;padding:12px 14px 14px;"
        f"border:1px solid {_hex_rgba(TEAL, 0.22)};'>{''.join(inner_chunks)}</div>",
        unsafe_allow_html=True,
    )


def _heatmap_from_array(mat: np.ndarray, title_txt: str) -> None:
    """Same visual language as App.py demand heatmap (paper, panel, spines, colorbar); custom ramp."""
    lo, hi = float(np.nanmin(mat)), float(np.nanmax(mat))
    if hi <= 1.05 and lo >= 0.0:
        vmin, vmax = 0.0, 1.0
    else:
        vmin, vmax = lo, hi

    fig, ax = plt.subplots(figsize=(6.5, 5.2), dpi=96)
    fig.patch.set_facecolor(_HM_FIG_BG)
    ax.set_facecolor(_HM_AX_BG)
    im = ax.imshow(
        mat,
        cmap=_SIM_DEMAND_HEATMAP_CMAP,
        vmin=vmin,
        vmax=vmax,
        aspect="equal",
        origin="upper",
    )
    ax.set_xticks(range(GRID_SIZE))
    ax.set_yticks(range(GRID_SIZE))
    ax.set_title(title_txt, color=_HM_INK, fontweight="800", fontsize=12)
    ax.set_xlabel("Column", color=_HM_INK, fontweight=600)
    ax.set_ylabel("Row", color=_HM_INK, fontweight=600)
    ax.tick_params(axis="both", colors=_HM_MUTED, labelsize=10)
    for spine in ax.spines.values():
        spine.set_edgecolor(_HM_SPINE_EDGE)
    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Demand weight", color=_HM_INK, fontweight=600)
    cbar.ax.tick_params(colors=_HM_MUTED)
    cbar.outline.set_edgecolor(_HM_SPINE_EDGE)
    fig.tight_layout()
    _hc1, _hc2, _hc3 = st.columns([1, 4, 1])
    with _hc2:
        st.pyplot(fig, clear_figure=True, use_container_width=True)
    plt.close(fig)


# SECTION 3 — Run
if st.button("Run 20-Step Simulation", type="primary", use_container_width=True):
    adapted_grid = build_adapter_grid(GRID)
    fleet = selected_fleet
    hubs_raw = sorted(
        [(c["row"], c["col"]) for c in get_all_of_type("is_hub", True)],
        key=lambda tc: (tc[0], tc[1]),
    )
    nl = int(fleet["light"])
    nh = int(fleet["heavy"])
    drones: list[Drone] = []
    for idx in range(nl + nh):
        hub_cell = hubs_raw[idx % len(hubs_raw)]
        drones.append(
            Drone(
                drone_id=f"D{idx + 1}",
                drone_type="light" if idx < nl else "heavy",
                position=hub_cell,
                home_hub=hub_cell,
            )
        )

    deliveries = [
        Delivery("DEL-1", (0, 2), (3, 8), (8, 5)),
        Delivery("DEL-2", (1, 7), (6, 0), (9, 9)),
        Delivery("DEL-3", (5, 1), (2, 3), (7, 9)),
    ]

    sim = DeliverySimulator(adapted_grid, drones, deliveries, grid_flat=list(GRID))
    anomaly_alert = st.session_state.get("anomaly_alert")
    anomaly_ok = isinstance(anomaly_alert, dict) and bool(anomaly_alert.get("label"))
    anomaly_step_eff = int(anomaly_step) if anomaly_ok else None

    no_fly_events = {int(no_fly_step): (int(no_fly_cell_row), int(no_fly_cell_col))}

    ev = list(
        sim.run(
            total_steps=20,
            no_fly_events=no_fly_events,
            anomaly_step=anomaly_step_eff,
            session_demand_pred=st.session_state.get("ml_demand_pred"),
        )
    )

    demand_val = st.session_state.get("ml_demand_pred", "—")
    ev[14] = f"Step 15: Demand forecast retrieved — {demand_val} units predicted for active corridor."
    ev[15] = f"Step 16: Delivery load adjusted based on forecast — corridor weighting updated."
    ev[16] = f"Step 17: New delivery DEL-4 optionally queued based on demand signal {demand_val}."

    if anomaly_ok and anomaly_step_eff is not None:
        ast = anomaly_step_eff
        pct_val = float(anomaly_alert.get("confidence", 0))
        pct = int(pct_val * 100)
        lbl = str(anomaly_alert.get("label", ""))
        ev[ast - 1] = (
            f"Step {ast:02d}: {lbl} detected (confidence {pct}%) — drone forced to return to hub."
        )

    st.session_state["sim_event_log"] = ev
    st.session_state["sim_completed"] = sim.completed
    st.session_state["sim_delayed"] = sim.delayed
    st.session_state["sim_failed"] = sim.failed
    st.session_state["sim_no_fly_cell"] = (int(no_fly_cell_row), int(no_fly_cell_col))
    st.session_state["sim_no_fly_event_count"] = sim.no_fly_event_count
    st.session_state["sim_run"] = True
    st.rerun()

# SECTIONS 4–8
if st.session_state.get("sim_run"):
    st.subheader("Event Log")
    _render_event_panel(st.session_state.get("sim_event_log") or [])

    st.subheader("Simulation Summary")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Completed Deliveries", str(st.session_state.get("sim_completed")))
    m2.metric("Delayed", str(st.session_state.get("sim_delayed")))
    m3.metric("Failed", str(st.session_state.get("sim_failed")))
    m4.metric("No-fly Events", str(st.session_state.get("sim_no_fly_event_count", "—")))

    st.subheader("Demand Heatmap — Current Simulation")
    hm_title = "Grid Cell Base Demand (run ML Pipeline for live forecast)"
    hm_mat: Optional[np.ndarray] = None
    grid_cached = st.session_state.get("ml_grid_demand")
    if st.session_state.get("ml_demand_pred") is not None and grid_cached is not None:
        hm_mat = np.asarray(grid_cached, dtype=float)
        if hm_mat.size == GRID_SIZE * GRID_SIZE:
            hm_mat = hm_mat.reshape((GRID_SIZE, GRID_SIZE))
        hm_title = "Predicted Delivery Demand per Grid Cell"
    elif st.session_state.get("ml_demand_pred") is not None:
        try:
            from ml_pipeline import get_grid_demand

            hm_mat = np.asarray(
                get_grid_demand(
                    hour=12,
                    season=1,
                    holiday=0,
                    workingday=1,
                    weather=1,
                    base_temp=0.5,
                    base_humidity=0.5,
                    base_wind=0.2,
                    grid_size=GRID_SIZE,
                    seed=42,
                ),
                dtype=float,
            )
            hm_title = "Predicted Delivery Demand per Grid Cell"
        except Exception:
            hm_mat = None
    if hm_mat is None:
        hm_mat = np.array(
            [[GRID[r * GRID_SIZE + c]["demand"] for c in range(GRID_SIZE)] for r in range(GRID_SIZE)],
            dtype=float,
        )
        if st.session_state.get("ml_demand_pred") is not None and grid_cached is None:
            hm_title = "Grid Cell Base Demand (ML grid cache missing — showing GRID priors)"

    _heatmap_from_array(hm_mat, hm_title)

    sim_nf = tuple(st.session_state.get("sim_no_fly_cell") or (no_fly_cell_row, no_fly_cell_col))
    fixed_nf = [(c["row"], c["col"]) for c in get_all_of_type("no_fly", True)]
    nofly_highlights = list(dict.fromkeys([sim_nf, *fixed_nf]))

    st.subheader("Grid — End of Simulation")
    viz = {
        "NOFLY": nofly_highlights,
        "DEL1": [(8, 5)],
        "DEL2": [(9, 9)],
        "DEL3": [(7, 9)],
    }
    viz_styles = {
        "NOFLY": f"outline: 3px solid {PINK}; outline-offset:-3px;",
        "DEL1": f"outline: 3px solid {TEAL}; outline-offset:-3px;",
        "DEL2": f"outline: 3px solid {PURPLE}; outline-offset:-3px;",
        "DEL3": f"outline: 3px solid {MAUVE}; outline-offset:-3px;",
    }
    st.markdown(
        render_grid_html(GRID, highlights=viz, highlight_styles=viz_styles, show_symbols=True, cell_px=54),
        unsafe_allow_html=True,
    )
    legend_bits = [
        ("No-fly (sim + grid)", PINK),
        ("DEL-1 drop-off", TEAL),
        ("DEL-2 drop-off", PURPLE),
        ("DEL-3 drop-off", MAUVE),
    ]
    leg = "".join(
        f"<span style='display:inline-flex;align-items:center;gap:6px;margin-right:16px;color:{PURPLE};font-weight:750;'>"
        f"<span style='width:12px;height:12px;border-radius:2px;box-sizing:border-box;border:3px solid {col};'></span>"
        f"{html_module.escape(lbl)}</span>"
        for lbl, col in legend_bits
    )
    st.markdown(leg, unsafe_allow_html=True)

    st.subheader("Anomaly Events")
    live_alert = st.session_state.get("anomaly_alert")
    if isinstance(live_alert, dict) and live_alert.get("label"):
        pct_i = int(float(live_alert.get("confidence", 0)) * 100)
        ev_tbl = pd.DataFrame(
            [
                {
                    "Step": anomaly_step,
                    "Drone": live_alert.get("drone", "D3"),
                    "Anomaly Type": str(live_alert.get("label", "")),
                    "Confidence": f"{pct_i}%",
                    "Action Taken": "Forced return to hub via A*",
                }
            ]
        )
        sty = ev_tbl.style.set_properties(
            **{
                "background-color": BG,
                "color": PURPLE,
                "font-weight": "600",
                "border": f"1px solid {TEAL}",
            }
        ).set_table_styles(
            [
                {
                    "selector": "th",
                    "props": [
                        ("background-color", PURPLE),
                        ("color", BG),
                        ("font-weight", "700"),
                        ("border", f"1px solid {TEAL}"),
                    ],
                }
            ]
        )
        st.dataframe(sty, use_container_width=True, hide_index=True)
    else:
        st.info("No anomalies detected in this simulation run.")
else:
    st.info("Configure the controls above, then run **Run 20-Step Simulation** to populate the report.")
