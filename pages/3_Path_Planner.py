import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import pandas as pd

from grid_data import GRID, get_all_of_type, manhattan
from grid_render import render_grid_html, ZONE_BG
from grid_adapter import build_adapter_grid
from styles import inject_css
from astar_planner import astar, plan_delivery_route

st.set_page_config(page_title="Path Planner", layout="wide")
inject_css()


# Header

PATH_SVG = """<svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
<path d="M4 18c0-3 3-3 6-6s3-6 6-6 4 2 4 4" stroke="#399DB5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
<circle cx="4" cy="18" r="2" fill="#411E57"/>
<circle cx="20" cy="10" r="2" fill="#DE5C8F"/>
</svg>"""

ribbon_html = f"""<div class="aeronet-top-ribbon">
<div style="display:flex;align-items:center;justify-content:space-between;gap:14px;">
<div style="display:flex;align-items:center;gap:10px;">
{PATH_SVG}
<div>
<div style="font-size:1.75rem;font-weight:850;letter-spacing:-0.02em;color:#50314B;line-height:1.05;">Delivery Path Planner</div>
<div style="margin-top:0.15rem;color:#405C6F;font-weight:600;">A* Search — Hub to Pickup to Drop-off to Hub</div>
</div>
</div>
</div>
</div>"""
st.markdown(ribbon_html, unsafe_allow_html=True)

fleet = st.session_state.get("selected_fleet")
if fleet:
    total_drones = fleet["light"] + fleet["heavy"]
    st.markdown(
        f"<div style='padding:14px 18px;margin:4px 0 12px;border-radius:14px;"
        f"background:rgba(78,106,118,0.12);border:1px solid rgba(61,92,111,0.22);'>"
        f"<div style='font-weight:800;color:#2d3f4a;font-size:14px;line-height:1.35'>"
        f"Fleet linked from Fleet Selector: <b>{fleet['light']}</b> light + "
        f"<b>{fleet['heavy']}</b> heavy drones "
        f"({total_drones} total capacity for deliveries)."
        f"</div></div>",
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        "<div style='padding:12px 16px;margin:4px 0 12px;border-radius:14px;"
        "background:rgba(120,94,104,0.12);border:1px solid rgba(107,71,92,0.25);'>"
        "<div style='font-weight:770;color:#4a3340;font-size:13px'>"
        "No fleet selected — open <strong>Fleet Selector</strong> and run "
        "<strong>Select Fleet</strong> for live capacity context."
        "</div></div>",
        unsafe_allow_html=True,
    )


def card_open(title: str) -> None:
    st.markdown(
        "<div style='background:linear-gradient(178deg,#f4f2ec 0%,#eae7de 52%,#e3dfd5 100%);"
        "border-radius:18px;border:1px solid rgba(36,42,54,0.11);padding:18px 20px 20px;"
        "box-shadow:0 14px 36px rgba(24,26,30,0.07),inset 0 1px 0 rgba(255,255,255,0.6);'>"
        f"<div style='font-weight:820;color:#3a3142;font-size:15px;margin-bottom:12px;"
        f"letter-spacing:0.02em;padding-bottom:10px;"
        f"border-bottom:1px solid rgba(24,26,30,0.08);'>{title}</div>",
        unsafe_allow_html=True,
    )


def card_close() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


# Cell lookup helper (dict view of GRID)

_CELL_BY_RC = {(c["row"], c["col"]): c for c in GRID}


def _cell_at(rc):
    return _CELL_BY_RC.get(rc)


# Session state defaults

_DEFAULTS = {
    "path_full_path":  [],
    "path_total_cost": 0.0,
    "path_segments":   {},
    "path_success":    False,
    "path_planned":    False,
    "path_hub":        None,
    "path_pickup":     None,
    "path_dropoff":    None,
    "path_extra_nf":   set(),
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# Route configuration constants

HUB_OPTIONS = [(c["row"], c["col"]) for c in get_all_of_type("is_hub", True)]
MEDICAL_PICKUP_OPTIONS = [
    (c["row"], c["col"]) for c in get_all_of_type("is_medical_pickup", True)
]
_mp_list = ", ".join(f"({r},{c})" for r, c in MEDICAL_PICKUP_OPTIONS) or "—"
_hub_list = ", ".join(f"({r},{c})" for r, c in HUB_OPTIONS) or "—"
_SPECIAL_ENDPOINTS_CAPTION = f"Medical pickups: {_mp_list} · Hubs: {_hub_list}"
FIXED_NOFLY = [(c["row"], c["col"]) for c in get_all_of_type("no_fly", True)]

st.markdown(
    """
<style>
  /* Path Planner — denser labelled controls inside elevated cards */
  section[data-testid="stMain"] .path-route-config label { font-size:12px;color:#49444a;font-weight:650;}
</style>
    """,
    unsafe_allow_html=True,
)

st.write("")
st.markdown("<div class='path-route-config'>", unsafe_allow_html=True)
card_open("Route configuration")
_route_left, _route_right = st.columns([1.35, 1], gap="large")

with _route_left:
    hub = st.selectbox(
        "Hub",
        options=HUB_OPTIONS,
        format_func=lambda x: f"Hub ({x[0]},{x[1]})",
    )
    st.markdown(
        "<div style='margin:10px 0 6px;color:#49444a;font-weight:820;font-size:13px'>Pickup coordinates</div>",
        unsafe_allow_html=True,
    )
    pu_r, pu_c = st.columns(2, gap="small")
    with pu_r:
        pickup_row = st.number_input(
            "Pickup row",
            min_value=0,
            max_value=9,
            value=0,
            step=1,
            key="pp_pickup_row",
        )
    with pu_c:
        pickup_col = st.number_input(
            "Pickup column",
            min_value=0,
            max_value=9,
            value=0,
            step=1,
            key="pp_pickup_col",
        )
    pickup = (int(pickup_row), int(pickup_col))
    st.caption(_SPECIAL_ENDPOINTS_CAPTION)
    st.markdown(
        "<div style='margin:14px 0 6px;color:#49444a;font-weight:820;font-size:13px'>Drop-off coordinates</div>",
        unsafe_allow_html=True,
    )
    do_r, do_c = st.columns(2, gap="small")
    with do_r:
        dropoff_row = st.number_input(
            "Drop-off row",
            min_value=0,
            max_value=9,
            value=9,
            step=1,
            key="pp_dropoff_row",
        )
    with do_c:
        dropoff_col = st.number_input(
            "Drop-off column",
            min_value=0,
            max_value=9,
            value=9,
            step=1,
            key="pp_dropoff_col",
        )
    dropoff = (int(dropoff_row), int(dropoff_col))
    st.caption(_SPECIAL_ENDPOINTS_CAPTION)

with _route_right:
    st.markdown(
        "<div style='margin:2px 0 8px;color:#49444a;font-weight:820;font-size:13px'>"
        "Extra no-fly (temporary obstacles)</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Added cells stack with the three fixed grid no-fly zones and affect "
        "the planner immediately."
    )
    enf_r, enf_c = st.columns(2)
    with enf_r:
        extra_nf_row = st.number_input(
            "Blocked row",
            min_value=0,
            max_value=9,
            value=0,
            step=1,
            key="pp_extra_nf_row",
        )
    with enf_c:
        extra_nf_col = st.number_input(
            "Blocked column",
            min_value=0,
            max_value=9,
            value=0,
            step=1,
            key="pp_extra_nf_col",
        )
    _enf_btn1, _enf_btn2 = st.columns(2)
    with _enf_btn1:
        extra_nf_add = st.button("Add blocked cell")
    with _enf_btn2:
        clear_nf = st.button("Clear extras")

    if extra_nf_add:
        if "extra_nf_set" not in st.session_state:
            st.session_state["extra_nf_set"] = set()
        st.session_state["extra_nf_set"].add((int(extra_nf_row), int(extra_nf_col)))

    if clear_nf:
        st.session_state["extra_nf_set"] = set()

    _nf_shown = list(st.session_state.get("extra_nf_set", set()))
    _nf_txt = (
        "<span style='color:#49444a'>" + ", ".join(f"({r},{c})" for r, c in sorted(_nf_shown)) + "</span>"
        if _nf_shown
        else "<span style='opacity:0.7'>none</span>"
    )
    st.markdown(
        "<div style='margin:14px 0 0;padding-top:12px;border-top:1px solid rgba(36,42,54,0.09);'>"
        f"<div style='color:#534c52;font-size:13px;font-weight:750;line-height:1.45'>"
        f"Ad-hoc blocked cells<br/><span style='font-weight:650'>{_nf_txt}</span></div></div>",
        unsafe_allow_html=True,
    )

_reset_col, _ = st.columns([0.42, 0.58])
with _reset_col:
    if st.button("Reset route state", key="path_reset_route", use_container_width=True):
        for _k, _v in _DEFAULTS.items():
            st.session_state[_k] = _v if not isinstance(_v, set) else set()
        st.rerun()

card_close()
st.markdown("</div>", unsafe_allow_html=True)


# Endpoints & Active No-fly (pre-flight)

st.write("")
card_open("Endpoints & Active No-Fly")

ep_l, ep_m, ep_r = st.columns(3, gap="medium")


def _endpoint_block(label: str, rc):
    cell = _cell_at(rc)
    if cell is None:
        return (
            f"<div style='color:#3a3142;font-weight:830;'>{label}</div>"
            f"<div style='color:#6b4f57;font-weight:720;'>Out of grid: {rc}</div>"
        )
    flags = []
    if cell.get("is_hub"):              flags.append("Hub")
    if cell.get("is_charging"):         flags.append("Charging")
    if cell.get("is_medical_pickup"):   flags.append("Medical pickup")
    if cell.get("no_fly"):              flags.append("No-fly")
    flag_str = " · ".join(flags) if flags else "—"
    return (
        f"<div style='color:#3a3142;font-weight:820;font-size:14px;margin-bottom:4px;'>{label}</div>"
        f"<div style='color:#3d3d48;font-weight:690;line-height:1.6;'>"
        f"Cell ({cell['row']},{cell['col']})<br/>"
        f"Zone: {cell['zone']}<br/>"
        f"Density: {cell['density']}<br/>"
        f"Demand: {cell['demand']}<br/>"
        f"Flags: {flag_str}"
        f"</div>"
    )


ep_l.markdown(_endpoint_block("Hub",      hub),     unsafe_allow_html=True)
ep_m.markdown(_endpoint_block("Pickup",   pickup),  unsafe_allow_html=True)
ep_r.markdown(_endpoint_block("Drop-off", dropoff), unsafe_allow_html=True)

active_no_fly_all = sorted(set(FIXED_NOFLY) | st.session_state.get("extra_nf_set", set()))
st.markdown(
    "<div style='font-weight:820;color:#3a3142;margin:14px 0 6px;font-size:14px;"
    "letter-spacing:0.015em'>Active No-Fly Cells</div>",
    unsafe_allow_html=True,
)
if active_no_fly_all:
    chips_html = "".join(
        "<span style='display:inline-block;padding:4px 11px;margin:3px 4px 3px 0;border-radius:999px;"
        "background:rgba(61,92,111,0.09);border:1px solid rgba(61,92,111,0.28);"
        f"color:#2d3740;font-weight:720;font-size:12px;'>({r},{c})</span>"
        for r, c in active_no_fly_all
    )
    st.markdown(
        f"<div style='display:flex;flex-wrap:wrap;'>{chips_html}</div>",
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        "<div style='color:#405C6F;font-weight:700;'>None.</div>",
        unsafe_allow_html=True,
    )

# Pre-flight warnings
warnings_list = []
pickup_cell = _cell_at(pickup)
dropoff_cell = _cell_at(dropoff)
if pickup_cell and (pickup_cell["no_fly"] or pickup in st.session_state.get("extra_nf_set", set())):
    warnings_list.append(f"Pickup {pickup} is on a no-fly cell — A* will refuse.")
if dropoff_cell and (dropoff_cell["no_fly"] or dropoff in st.session_state.get("extra_nf_set", set())):
    warnings_list.append(f"Drop-off {dropoff} is on a no-fly cell — A* will refuse.")
if hub == pickup:
    warnings_list.append("Hub equals Pickup — segment 1 will be a zero-length path.")
if pickup == dropoff:
    warnings_list.append("Pickup equals Drop-off — segment 2 will be a zero-length path.")
if dropoff == hub:
    warnings_list.append("Drop-off equals Hub — segment 3 will be a zero-length path.")
if hub in active_no_fly_all:
    warnings_list.append(f"Hub {hub} sits on an active no-fly cell.")

if warnings_list:
    st.warning("\n\n".join(f"• {w}" for w in warnings_list))
card_close()


# Plan Route

st.write("")
card_open("Run Route")
plan_clicked = st.button("Plan Route", type="primary", use_container_width=True)

if plan_clicked:
    adapted_grid = build_adapter_grid(GRID, extra_no_fly=st.session_state.get("extra_nf_set", set()))
    full_path, total_cost, segments, success = plan_delivery_route(
        hub, pickup, dropoff, adapted_grid
    )
    st.session_state["path_full_path"]  = full_path
    st.session_state["path_total_cost"] = total_cost
    st.session_state["path_segments"]   = segments
    st.session_state["path_success"]    = success
    st.session_state["path_planned"]    = True
    st.session_state["path_hub"]        = hub
    st.session_state["path_pickup"]     = pickup
    st.session_state["path_dropoff"]    = dropoff
    st.session_state["path_extra_nf"]   = st.session_state.get("extra_nf_set", set())

if st.session_state["path_planned"]:
    full_path  = st.session_state["path_full_path"]
    total_cost = st.session_state["path_total_cost"]
    segments   = st.session_state["path_segments"]
    success    = st.session_state["path_success"]

    seg_ok_count = sum(1 for s in segments.values() if s.get("message") == "success")

    r1, r2, r3, r4 = st.columns(4, gap="medium")
    r1.metric("Status", "FOUND" if success else "FAILED")
    r2.metric("Total Steps", len(full_path) if success else 0)
    r3.metric("Total Cost", total_cost)
    r4.metric("Segments OK", f"{seg_ok_count}/3")
else:
    st.markdown(
        "<div style='color:#465a68;font-weight:720;line-height:1.45'>"
        "Set hub, pickup, and drop-off in <b>Route configuration</b> above, then "
        "click <b>Plan Route</b>."
        "</div>",
        unsafe_allow_html=True,
    )
card_close()


# Segment Breakdown

if st.session_state["path_planned"]:
    st.write("")
    card_open("Segment Breakdown")
    segments = st.session_state["path_segments"]
    if segments:
        seg_label_map = {
            "hub_to_pickup":     "Hub → Pickup",
            "pickup_to_dropoff": "Pickup → Drop-off",
            "dropoff_to_hub":    "Drop-off → Hub",
        }
        rows = []
        for key in ["hub_to_pickup", "pickup_to_dropoff", "dropoff_to_hub"]:
            seg = segments.get(key, {})
            rows.append(
                {
                    "Segment": seg_label_map[key],
                    "Steps":   len(seg.get("path", [])),
                    "Cost":    seg.get("cost", 0.0),
                    "Status":  seg.get("message", "—"),
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.markdown(
            "<div style='color:#405C6F;font-weight:700;'>"
            "No segment data yet."
            "</div>",
            unsafe_allow_html=True,
        )
    card_close()


# Failure Diagnosis (only on failure)

if st.session_state["path_planned"] and not st.session_state["path_success"]:
    st.write("")
    card_open("Failure Diagnosis")
    segments = st.session_state["path_segments"] or {}
    failed_any = False
    for key, seg in segments.items():
        msg = seg.get("message", "")
        if msg != "success":
            failed_any = True
            label = {
                "hub_to_pickup":     "Hub → Pickup",
                "pickup_to_dropoff": "Pickup → Drop-off",
                "dropoff_to_hub":    "Drop-off → Hub",
            }.get(key, key)
            st.error(f"{label}: {msg}")
    if not failed_any:
        st.error("Route marked as failed but no segment reported an error message.")
    st.caption(
        "Tip: lift no-fly blockers, move the pickup or drop-off off a no-fly cell, "
        "or pick a hub closer to the goal."
    )
    card_close()


# Path Efficiency (only on success)

if st.session_state["path_planned"] and st.session_state["path_success"]:
    st.write("")
    card_open("Path Efficiency")
    full_path  = st.session_state["path_full_path"]
    total_cost = st.session_state["path_total_cost"]
    hub_e      = st.session_state["path_hub"]
    pickup_e   = st.session_state["path_pickup"]
    dropoff_e  = st.session_state["path_dropoff"]

    ideal_manhattan = (
        manhattan(hub_e, pickup_e)
        + manhattan(pickup_e, dropoff_e)
        + manhattan(dropoff_e, hub_e)
    )

    actual_steps = max(0, len(full_path) - 1) if full_path else 0
    detour_steps = max(0, actual_steps - ideal_manhattan)

    if total_cost > 0:
        cost_ratio = round(ideal_manhattan / total_cost, 3)
    else:
        cost_ratio = 1.0

    e1, e2, e3, e4 = st.columns(4, gap="medium")
    e1.metric(
        "Manhattan Ideal",
        ideal_manhattan,
        help="Sum of Manhattan distances Hub → Pickup → Drop-off → Hub. "
             "Lower bound on the number of moves needed when nothing is blocked.",
    )
    e2.metric("Actual Steps", actual_steps)
    e3.metric(
        "Detour Steps",
        detour_steps,
        help="Extra moves taken vs. the Manhattan ideal — caused by no-fly detours.",
    )
    e4.metric(
        "Cost vs Ideal",
        cost_ratio,
        help="ideal Manhattan moves / actual A* cost. "
             "Above 1.0 means commercial corridors (0.8 cost) saved more than detours added; "
             "below 1.0 means detours dominated.",
    )
    card_close()


# Cost Breakdown by Zone (only on success)

if st.session_state["path_planned"] and st.session_state["path_success"]:
    st.write("")
    card_open("Cost Breakdown")
    full_path = st.session_state["path_full_path"]
    zone_counts = {}
    commercial_steps = 0
    normal_steps = 0
    for rc in full_path:
        cell = _cell_at(rc)
        if cell is None:
            continue
        z = cell["zone"]
        zone_counts[z] = zone_counts.get(z, 0) + 1
        if z == "Commercial":
            commercial_steps += 1
        else:
            normal_steps += 1

    cb1, cb2, cb3 = st.columns(3, gap="medium")
    cb1.metric("Cells Visited", len(full_path))
    cb2.metric(
        "Commercial Corridor Cells",
        commercial_steps,
        help="Each commercial corridor cell costs 0.8 instead of 1.0 to enter.",
    )
    cb3.metric("Other Zone Cells", normal_steps)

    zone_df = pd.DataFrame(
        sorted(
            ({"Zone": z, "Cells": n} for z, n in zone_counts.items()),
            key=lambda r: r["Cells"],
            reverse=True,
        )
    )
    if not zone_df.empty:
        st.dataframe(zone_df, use_container_width=True, hide_index=True)

    savings = round(commercial_steps * (1.0 - 0.8), 2)
    if savings > 0:
        st.caption(
            f"Commercial corridors saved approximately {savings} cost units on this route."
        )
    card_close()


# Grid Visualization

st.write("")
card_open("Grid Visualization")

if st.session_state["path_planned"] and st.session_state["path_success"]:
    full_path = st.session_state["path_full_path"]
    hub_sel       = st.session_state["path_hub"]
    pickup_sel    = st.session_state["path_pickup"]
    dropoff_sel   = st.session_state["path_dropoff"]
    extra_nf_sel  = st.session_state["path_extra_nf"]

    endpoints = {hub_sel, pickup_sel, dropoff_sel}
    path_cells_only = [cell for cell in full_path if cell not in endpoints]

    highlights = {
        "PATH":    path_cells_only,
        "HUB":     [hub_sel],
        "PICKUP":  [pickup_sel],
        "DROPOFF": [dropoff_sel],
        "NOFLY":   FIXED_NOFLY + list(extra_nf_sel),
    }
else:
    highlights = {
        "NOFLY": FIXED_NOFLY + list(st.session_state["path_extra_nf"] or st.session_state.get("extra_nf_set", set())),
    }

highlight_styles = {
    "HUB":     "outline: 3px solid #411E57; outline-offset:-3px;",
    "PICKUP":  "outline: 3px solid #6BB1AD; outline-offset:-3px;",
    "DROPOFF": "outline: 3px solid #DE5C8F; outline-offset:-3px;",
    "NOFLY":   "outline: 3px solid #E9819A; outline-offset:-3px;",
}

st.markdown(
    """
<style>
/* Per-cell corridor: inset glow only (no td filter blobs) */
@keyframes aeronetPathCorridorPulse {
  0%, 100% {
    box-shadow:
      inset 0 0 0 2px rgba(44, 124, 136, 0.78),
      inset 0 0 14px rgba(44, 124, 136, 0.30),
      inset 0 10px 16px rgba(255, 255, 255, 0.20),
      inset 0 -10px 16px rgba(24, 26, 30, 0.06);
  }
  50% {
    box-shadow:
      inset 0 0 0 3px rgba(44, 124, 136, 1),
      inset 0 0 26px rgba(44, 124, 136, 0.48),
      inset 0 10px 16px rgba(255, 255, 255, 0.23),
      inset 0 -10px 16px rgba(24, 26, 30, 0.06);
  }
}
table.aeronet-grid td.aeronet-cell .aeronet-cell-inner.aeronet-path-corridor {
  animation: aeronetPathCorridorPulse 2.1s ease-in-out infinite;
}
</style>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    render_grid_html(
        GRID,
        cell_px=54,
        highlights=highlights,
        highlight_styles=highlight_styles,
        show_symbols=True,
        highlight_on="inner",
        highlight_classes={"PATH": "aeronet-path-corridor"},
        highlight_label_overrides={"PATH": "Path"},
    ),
    unsafe_allow_html=True,
)


def _swatch_svg(color: str) -> str:
    return (
        "<svg width='18' height='18' viewBox='0 0 24 24' "
        "xmlns='http://www.w3.org/2000/svg' aria-hidden='true'>"
        f"<circle cx='12' cy='12' r='9' fill='none' stroke='{color}' stroke-width='3'/>"
        "</svg>"
    )


legend_items = [
    ("Path",         "#2C7C88"),
    ("Hub",          "#411E57"),
    ("Pickup",       "#6BB1AD"),
    ("Drop-off",     "#DE5C8F"),
    ("No-fly",       "#E9819A"),
]
legend_html_parts = []
for label, color in legend_items:
    legend_html_parts.append(
        "<div style='display:inline-flex;align-items:center;gap:6px;"
        "padding:4px 10px;border-radius:999px;background:rgba(24,26,30,0.05);"
        "border:1px solid rgba(24,26,30,0.10);font-weight:700;color:#411E57;"
        "font-size:13px;margin:4px 6px 0 0;'>"
        f"{_swatch_svg(color)}<span>{label}</span>"
        "</div>"
    )
st.markdown(
    "<div style='display:flex;flex-wrap:wrap;align-items:center;margin-top:10px;'>"
    + "".join(legend_html_parts)
    + "</div>",
    unsafe_allow_html=True,
)
st.caption(
    "D = Hub. C = Charging pad. M = Medical pickup. N = No-fly. "
    "Route corridor cells pulse with an inset teal glow and a Path tag; "
    "hub, pickup, and drop-off use ring outlines."
)
card_close()


# Path coordinates (expander)

if st.session_state["path_planned"] and st.session_state["path_success"]:
    st.write("")
    with st.expander("Path Coordinates"):
        full_path = st.session_state["path_full_path"]
        st.caption(
            f"{len(full_path)} cells visited end-to-end "
            f"(joined at hub, pickup, drop-off junctions)."
        )
        rows_out = []
        prev = None
        for i, (r, c) in enumerate(full_path):
            if prev is None:
                move = "Start"
            else:
                dr, dc = r - prev[0], c - prev[1]
                if   dr == -1 and dc == 0: move = "↑ N"
                elif dr ==  1 and dc == 0: move = "↓ S"
                elif dr ==  0 and dc == -1: move = "← W"
                elif dr ==  0 and dc == 1:  move = "→ E"
                elif dr ==  0 and dc == 0:  move = "—"
                else:                       move = f"Δ({dr},{dc})"
            cell = _cell_at((r, c))
            zone = cell["zone"] if cell else ""
            tag = ""
            if (r, c) == st.session_state["path_hub"]:      tag = "Hub"
            elif (r, c) == st.session_state["path_pickup"]: tag = "Pickup"
            elif (r, c) == st.session_state["path_dropoff"]: tag = "Drop-off"
            rows_out.append(
                {"Step": i, "Move": move, "Row": r, "Col": c, "Zone": zone, "Marker": tag}
            )
            prev = (r, c)
        st.dataframe(pd.DataFrame(rows_out), use_container_width=True, hide_index=True)
