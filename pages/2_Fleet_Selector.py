import streamlit as st
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

import sys, os

sys.path.insert(0, os.path.dirname(__file__))
from fleet_selector import select_fleet, calculate_fitness, DRONE_TYPES

from styles import inject_css
from grid_data import GRID, GRID_SIZE, manhattan, get_all_of_type
from grid_render import render_grid_html

# Valid cells — warm cream → sand → mauve (only NaN/over-budget cells use grey overlay below)
_FITNESS_HEATMAP_CMAP = LinearSegmentedColormap.from_list(
    "aeronet_fitness",
    ["#f4f1ea", "#e8d8be", "#d9b88a", "#c48a7a", "#8b4a5c", "#5a2d40"],
)


st.set_page_config(page_title="Fleet Selector • AeroNet Lite", page_icon="🚁", layout="wide")
inject_css()

st.markdown(
    """
<style>
/* Fitness pill — teal → cream → rose, still restrained vs neon pastels */
.fleet-fitness-pill {
    display: block;
    width: fit-content;
    max-width: 100%;
    margin: 14px auto 0 auto;
    padding: 12px 24px;
    border-radius: 999px;
    font-weight: 700;
    font-size: 0.92rem;
    line-height: 1.4;
    text-align: center;
    color: #3a1f42;
    background: linear-gradient(90deg, #a8d8e4 0%, #efe6cb 44%, #e2aebf 100%);
    border: 1px solid rgba(80, 49, 75, 0.38);
    box-shadow: 0 4px 16px rgba(45, 72, 86, 0.12);
}
/*
 * Bordered report panel only: exclude nested stVerticalBlockBorderWrapper
 * (e.g. inside expanders) so padding/border doesn’t break expander chevrons.
 */
section[data-testid="stMain"]
    [data-testid="stVerticalBlockBorderWrapper"]:not(
        [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlockBorderWrapper"]
    ) {
    background: #f0ece4 !important;
    border: 2px solid rgba(65, 30, 87, 0.22) !important;
    border-radius: 18px !important;
    padding: 16px 14px 18px 14px !important;
    box-shadow: 0 10px 24px rgba(24, 26, 30, 0.08);
}
section[data-testid="stMain"]
    [data-testid="stVerticalBlockBorderWrapper"]:not(
        [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlockBorderWrapper"]
    )
    [data-baseweb="progress-bar"]
    [role="progressbar"]
    > div {
    background-image: linear-gradient(90deg, #4a93a8, #6d6f98, #b06d84) !important;
    background-color: transparent !important;
}
</style>
    """,
    unsafe_allow_html=True,
)


FLEET_SVG = """<svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
<path d="M4 12h6l2-3 2 3h6" stroke="#2a7f96" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
<circle cx="6" cy="12" r="1.6" fill="#4c5a91"/>
<circle cx="12" cy="9" r="1.6" fill="#ab4a62"/>
<circle cx="18" cy="12" r="1.6" fill="#38786b"/>
<path d="M5 17h14" stroke="#50314B" stroke-width="2" stroke-linecap="round"/>
</svg>"""


LIGHT_DRONE_SVG = """<svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
<circle cx="6" cy="6" r="2" stroke="#2a7f96" stroke-width="1.6" fill="none"/>
<circle cx="18" cy="6" r="2" stroke="#2a7f96" stroke-width="1.6" fill="none"/>
<circle cx="6" cy="18" r="2" stroke="#2a7f96" stroke-width="1.6" fill="none"/>
<circle cx="18" cy="18" r="2" stroke="#2a7f96" stroke-width="1.6" fill="none"/>
<path d="M8 8L16 16M16 8L8 16" stroke="#4c5a91" stroke-width="1.4" stroke-linecap="round"/>
<circle cx="12" cy="12" r="2.4" fill="#ab4a62"/>
</svg>"""


HEAVY_DRONE_SVG = """<svg width="26" height="26" viewBox="0 0 24 24" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
<circle cx="5" cy="5" r="2.6" stroke="#411E57" stroke-width="2" fill="none"/>
<circle cx="19" cy="5" r="2.6" stroke="#411E57" stroke-width="2" fill="none"/>
<circle cx="5" cy="19" r="2.6" stroke="#411E57" stroke-width="2" fill="none"/>
<circle cx="19" cy="19" r="2.6" stroke="#411E57" stroke-width="2" fill="none"/>
<path d="M7 7L17 17M17 7L7 17" stroke="#50314B" stroke-width="2" stroke-linecap="round"/>
<rect x="9" y="9" width="6" height="6" rx="1.2" fill="#8c3a52"/>
</svg>"""

ribbon_html = f"""<div class="aeronet-top-ribbon">
<div style="display:flex;align-items:center;justify-content:space-between;gap:14px;">
<div style="display:flex;align-items:center;gap:10px;">
{FLEET_SVG}
<div>
<div style="font-size:1.75rem;font-weight:850;letter-spacing:-0.02em;color:#50314B;line-height:1.05;">Fleet Selector</div>
<div style="margin-top:0.15rem;color:#405C6F;font-weight:600;">Module 2 — Pick the best mix of light and heavy drones for the city grid.</div>
</div>
</div>
</div>
</div>"""
st.markdown(ribbon_html, unsafe_allow_html=True)


def card_open(title: str) -> None:
    st.markdown(
        f"<div style='background:#EDECDB;border-radius:14px;border:1px solid rgba(24,26,30,0.12);padding:12px 14px;box-shadow:0 6px 16px rgba(24,26,30,0.05);'>"
        f"<div style='font-weight:850;color:#50314B;font-size:14px;margin-bottom:6px;'>{title}</div>",
        unsafe_allow_html=True,
    )


def card_close() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


GRID_TOTAL_CELLS = GRID_SIZE * GRID_SIZE
HUBS = [(c["row"], c["col"]) for c in get_all_of_type("is_hub", True)]
NO_FLY = {(c["row"], c["col"]) for c in get_all_of_type("no_fly", True)}


def _effective_range(light_count: int, heavy_count: int) -> float:
    """Fleet-weighted average Manhattan range per drone (cells)."""
    light_range = DRONE_TYPES["light"]["range"]
    heavy_range = DRONE_TYPES["heavy"]["range"]
    total = light_count + heavy_count
    if total == 0:
        return 0.0
    elif heavy_count == 0:
        return float(light_range)
    elif light_count == 0:
        return float(heavy_range)
    return round((light_count * light_range + heavy_count * heavy_range) / total, 1)


def _geographic_coverage(light_count: int, heavy_count: int):
    """Set of (row, col) cells reachable from any hub within effective range,
    excluding no-fly cells. Returns (covered_set, effective_range)."""
    eff = _effective_range(light_count, heavy_count)
    covered = set()

    def _cells_within_range(max_dist: int) -> set:
        cells = set()
        if max_dist <= 0 or not HUBS:
            return cells
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if (r, c) in NO_FLY:
                    continue
                for hr, hc in HUBS:
                    if manhattan((r, c), (hr, hc)) <= max_dist:
                        cells.add((r, c))
                        break
        return cells

    if light_count > 0:
        covered |= _cells_within_range(DRONE_TYPES["light"]["range"])
    if heavy_count > 0:
        covered |= _cells_within_range(DRONE_TYPES["heavy"]["range"])
    return covered, eff


card_open("Drone Specifications")
spec_rows = []
for kind, spec in DRONE_TYPES.items():
    spec_rows.append(
        {
            "Type":          kind.capitalize(),
            "Cost":          spec["cost"],
            "Payload (kg)":  spec["payload"],
            "Range (cells)": spec["range"],
        }
    )
spec_df = pd.DataFrame(spec_rows)


def _style_spec_type_rows(row):
    tint = ""
    if row["Type"] == "Light":
        tint = "background-color: #b8dce6; color: #134456;"
    elif row["Type"] == "Heavy":
        tint = "background-color: #e5b9c9; color: #4a1a2e;"
    return [tint] * len(row)


_numeric_cols = ["Cost", "Payload (kg)", "Range (cells)"]
_spec_styled = (
    spec_df.style.apply(_style_spec_type_rows, axis=1)
    .set_properties(**{"border": "1px solid #c9c2b8", "padding": "9px 10px"})
    .set_properties(subset=_numeric_cols, **{"text-align": "right", "font-variant-numeric": "tabular-nums"})
    .set_properties(subset=["Type"], **{"text-align": "left", "font-weight": "600"})
    .set_table_styles(
        [
            {
                "selector": "table",
                "props": [
                    ("border-collapse", "collapse"),
                    ("background-color", "#fcfaf5"),
                    ("border-radius", "10px"),
                    ("overflow", "hidden"),
                    ("box-shadow", "none"),
                ],
            },
            {
                "selector": "thead th",
                "props": [
                    ("background", "linear-gradient(180deg, #356a7a 0%, #2d5462 100%)"),
                    ("color", "#f4f0e4"),
                    ("font-weight", "750"),
                    ("letter-spacing", "0.02em"),
                    ("padding", "10px 8px"),
                    ("border-bottom", "1px solid rgba(255,255,255,0.12)"),
                ],
            },
        ]
    )
)
st.dataframe(_spec_styled, use_container_width=True, hide_index=True)
st.markdown(
    "<div class='fleet-fitness-pill'>Fitness = 0.75 × coverage% − 0.25 × budget-used%. "
    "Over-budget fleets are rejected.</div>",
    unsafe_allow_html=True,
)
card_close()


st.write("")
card_open("City Grid")
st.markdown(
    render_grid_html(GRID, size=GRID_SIZE, cell_px=54),
    unsafe_allow_html=True,
)
st.write("")
g1, g2, g3, g4, g5 = st.columns(5)
g1.metric("Grid", f"{GRID_SIZE} × {GRID_SIZE}")
g2.metric("Total Cells", GRID_TOTAL_CELLS)
g3.metric("Hubs (D)", len(HUBS))
g4.metric("Charging (C)", len(get_all_of_type("is_charging", True)))
g5.metric("No-fly (N)", len(NO_FLY))
st.caption(
    "D = Hub (drone launch point). C = Charging pad. N = No-fly. "
    "Drones reach cells within their Manhattan range from any hub."
)
card_close()


st.write("")
card_open("Configuration")
demand_estimate = st.session_state.get("ml_demand_pred")
if demand_estimate is not None:
    st.info(
        f"ML Demand Forecast: {demand_estimate} units predicted. "
        "Fleet will be optimized for this demand."
    )
else:
    st.caption(
        "Run the ML Pipeline page first to get a demand estimate. "
        "Using default budget optimization."
    )
demand_target = int(demand_estimate) if demand_estimate is not None else 100

cfg_left, cfg_right = st.columns([3, 2], gap="large")
with cfg_left:
    budget = st.slider("Total Budget", 5000, 30000, 10000, step=500)
with cfg_right:
    method = st.radio(
        "Selection Method",
        ["ga", "brute"],
        format_func=lambda x: "Genetic Algorithm" if x == "ga" else "Brute Force",
        horizontal=True,
    )

light_cost = DRONE_TYPES["light"]["cost"]
heavy_cost = DRONE_TYPES["heavy"]["cost"]
st.markdown(
    f"<div style='color:#405C6F;font-weight:700;margin-top:6px;'>"
    f"At this budget you could afford up to <b>{budget // light_cost}</b> light drones "
    f"or up to <b>{budget // heavy_cost}</b> heavy drones."
    f"</div>",
    unsafe_allow_html=True,
)

if st.button("Select Fleet", type="primary", use_container_width=True):
    with st.spinner("Optimizing fleet..."):
        ga_fleet_cached, ga_score_cached = select_fleet(
            budget, method="ga", demand_cap=demand_target
        )
        st.session_state["fleet_ga_cache_fleet"] = ga_fleet_cached
        st.session_state["fleet_ga_cache_score"] = ga_score_cached
        st.session_state["fleet_ga_cache_budget"] = budget

        if method == "ga":
            fleet, score = ga_fleet_cached, ga_score_cached
        else:
            fleet, score = select_fleet(
                budget, method="brute", demand_cap=demand_target
            )
    st.session_state["selected_fleet"] = fleet
    st.session_state["fleet_score"] = score
    st.session_state["fleet_budget"] = budget
    st.session_state["fleet_method"] = method
card_close()


st.write("")
card_open("Selected Fleet")
if "selected_fleet" not in st.session_state:
    st.markdown(
        "<div style='color:#405C6F;font-weight:700;'>"
        "Pick a budget and method above, then click <b>Select Fleet</b> to see results."
        "</div>",
        unsafe_allow_html=True,
    )
else:
    with st.container(border=True):
        fleet = st.session_state["selected_fleet"]
        budget_sel = st.session_state["fleet_budget"]
        method_sel = st.session_state.get("fleet_method", "ga")
        score = st.session_state["fleet_score"]

        light = fleet["light"]
        heavy = fleet["heavy"]

        total_cost = (
            light * DRONE_TYPES["light"]["cost"]
            + heavy * DRONE_TYPES["heavy"]["cost"]
        )
        abstract_coverage = min(
            light * DRONE_TYPES["light"]["range"]
            + heavy * DRONE_TYPES["heavy"]["range"],
            GRID_TOTAL_CELLS,
        )
        budget_remaining = budget_sel - total_cost
        total_drones = light + heavy
        light_payload_capacity = light * DRONE_TYPES["light"]["payload"]
        heavy_payload_capacity = heavy * DRONE_TYPES["heavy"]["payload"]

        covered_cells, eff_range = _geographic_coverage(light, heavy)
        geo_coverage = len(covered_cells)
        flyable_cells = GRID_TOTAL_CELLS - len(NO_FLY)

        badge_method = "Genetic Algorithm" if method_sel == "ga" else "Brute Force"
        st.markdown(
            f"<div style='background:rgba(89,78,96,0.10);border-radius:10px;"
            f"border:1px solid rgba(65,30,87,0.16);padding:8px 12px;"
            f"color:#50314B;font-weight:800;margin-bottom:10px;'>"
            f"Method: {badge_method} &nbsp;•&nbsp; Budget: {budget_sel}</div>",
            unsafe_allow_html=True,
        )

        m1, m2, m3 = st.columns(3, gap="medium")
        m1.metric("Light Drones", light)
        m2.metric("Heavy Drones", heavy)
        m3.metric("Fitness Score", score)

        st.write("")
        m4, m5, m6 = st.columns(3, gap="medium")
        m4.metric("Total Cost", total_cost)
        m5.metric(
            "Optimizer Coverage",
            f"{abstract_coverage}/{GRID_TOTAL_CELLS}",
            help="Aggregate cell coverage as scored by the optimizer "
                 "(sum of drone ranges, capped at grid size).",
        )
        m6.metric("Budget Remaining", budget_remaining)

        st.write("")
        m7, m8, m9 = st.columns(3, gap="medium")
        m7.metric("Total Drones", total_drones)
        m8.metric("Light Payload", f"{light_payload_capacity} kg")
        m9.metric("Heavy Payload", f"{heavy_payload_capacity} kg")

        st.write("")
        m10, m11, m12 = st.columns(3, gap="medium")
        m10.metric(
            "Grid Coverage",
            f"{geo_coverage}/{flyable_cells}",
            help="Cells reachable on the actual city grid: any cell within "
                 "Manhattan range of a hub, excluding no-fly cells.",
        )
        m11.metric(
            "Avg Effective Range",
            f"{eff_range} cells",
            help="Fleet-weighted average range per drone (Manhattan cells).",
        )
        m12.metric(
            "Hubs Available",
            f"{len(HUBS)}",
            help="Drone launch points defined in the city grid.",
        )

        st.markdown(
            "<div style='font-weight:850;font-size:15px;color:#405C6F;margin:14px 0 6px;'>"
            "Fleet Coverage on the City Grid</div>",
            unsafe_allow_html=True,
        )
        if eff_range == 0 or not HUBS:
            st.markdown(
                "<div style='color:#405C6F;font-weight:700;'>"
                "No drones owned (or no hubs defined) — nothing to overlay."
                "</div>",
                unsafe_allow_html=True,
            )
        fleet_highlights = {
            "F": list(covered_cells),
            "H": HUBS,
        }
        # Do not outline every reachable cell: full coverage paints teal on almost every tile (“blue everywhere”).
        # Match the baseline city grid look: zone colors only; show reachability with small F chips + rose hub rings.
        fleet_styles = {
            "H": "outline: 2.5px solid rgba(122, 58, 76, 0.88); outline-offset: -2px;",
        }
        st.markdown(
            render_grid_html(
                GRID,
                size=GRID_SIZE,
                cell_px=54,
                highlights=fleet_highlights,
                highlight_styles=fleet_styles,
                show_highlight_labels=True,
                highlight_on="inner",
                highlight_label_overrides={"H": "D"},
            ),
            unsafe_allow_html=True,
        )
        st.caption(
            "F or F,D chip: cell is within fleet range from a hub. "
            "Rose ring / D chip: hub marker (same letter as hub cells). "
            "Zone colors match the grid above — no teal tint on reachable cells."
        )

        st.markdown(
            "<div style='font-weight:850;font-size:15px;color:#594662;margin:14px 0 6px;'>Coverage</div>",
            unsafe_allow_html=True,
        )
        cov_pct = geo_coverage / flyable_cells if flyable_cells > 0 else 0.0
        st.progress(min(max(cov_pct, 0.0), 1.0))
        st.caption(
            f"{geo_coverage} / {flyable_cells} flyable cells reached "
            f"({round(cov_pct * 100, 1)}%) — no-fly cells excluded."
        )

        st.markdown(
            "<div style='font-weight:850;font-size:15px;color:#6c4e5b;margin:14px 0 6px;'>"
            "Budget Utilization</div>",
            unsafe_allow_html=True,
        )
        used_pct = total_cost / budget_sel if budget_sel > 0 else 0.0
        st.progress(min(max(used_pct, 0.0), 1.0))
        st.caption(
            f"{total_cost} / {budget_sel} spent "
            f"({round(used_pct * 100, 1)}% — {budget_remaining} remaining)"
        )

        st.markdown(
            "<div style='font-weight:850;font-size:15px;color:#4d5d59;margin:14px 0 6px;'>"
            "Cost Breakdown</div>",
            unsafe_allow_html=True,
        )
        breakdown = pd.DataFrame(
            [
                {
                    "Type":          "Light",
                    "Count":         light,
                    "Unit Cost":     DRONE_TYPES["light"]["cost"],
                    "Subtotal":      light * DRONE_TYPES["light"]["cost"],
                    "Range":         DRONE_TYPES["light"]["range"],
                    "Payload (kg)":  light * DRONE_TYPES["light"]["payload"],
                },
                {
                    "Type":          "Heavy",
                    "Count":         heavy,
                    "Unit Cost":     DRONE_TYPES["heavy"]["cost"],
                    "Subtotal":      heavy * DRONE_TYPES["heavy"]["cost"],
                    "Range":         DRONE_TYPES["heavy"]["range"],
                    "Payload (kg)":  heavy * DRONE_TYPES["heavy"]["payload"],
                },
            ]
        )
        styled_breakdown = breakdown.style.apply(
            lambda row: (
                ["background-color: #b8dce6; color: #134456; font-weight: 600;"] * len(row)
                if row["Type"] == "Light"
                else ["background-color: #e5b9c9; color: #4a1a2e; font-weight: 600;"] * len(row)
            ),
            axis=1,
        )
        st.dataframe(styled_breakdown, use_container_width=True, hide_index=True)

        st.markdown(
            "<div style='font-weight:850;font-size:15px;color:#57424d;margin:18px 0 8px;'>"
            "Fleet at a Glance</div>",
            unsafe_allow_html=True,
        )
        if total_drones == 0:
            st.markdown(
                "<div style='color:#405C6F;font-weight:700;'>No drones in this fleet.</div>",
                unsafe_allow_html=True,
            )
        else:
            light_row = "".join(
                f"<span style='display:inline-flex;align-items:center;justify-content:center;"
                f"width:34px;height:34px;margin:2px;border-radius:8px;"
                f"background:rgba(32,110,130,0.14);border:1px solid rgba(32,110,130,0.35);'>"
                f"{LIGHT_DRONE_SVG}</span>"
                for _ in range(light)
            )
            heavy_row = "".join(
                f"<span style='display:inline-flex;align-items:center;justify-content:center;"
                f"width:38px;height:38px;margin:2px;border-radius:8px;"
                f"background:rgba(130,45,70,0.12);border:1px solid rgba(130,45,70,0.32);'>"
                f"{HEAVY_DRONE_SVG}</span>"
                for _ in range(heavy)
            )
            st.markdown(
                f"<div style='display:flex;flex-direction:column;gap:8px;'>"
                f"<div style='display:flex;align-items:center;gap:10px;flex-wrap:wrap;'>"
                f"<span style='font-weight:800;color:#134456;min-width:80px;'>Light × {light}</span>"
                f"<span style='display:flex;flex-wrap:wrap;'>{light_row}</span>"
                f"</div>"
                f"<div style='display:flex;align-items:center;gap:10px;flex-wrap:wrap;'>"
                f"<span style='font-weight:800;color:#4a1a2e;min-width:80px;'>Heavy × {heavy}</span>"
                f"<span style='display:flex;flex-wrap:wrap;'>{heavy_row}</span>"
                f"</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

        if total_drones == 0:
            recommendation = (
                "No fleet was selected — try increasing the budget or switching method."
            )
        elif geo_coverage >= flyable_cells:
            recommendation = (
                f"This fleet of {total_drones} drones reaches every flyable cell "
                f"({flyable_cells}) on your grid using {round(used_pct * 100, 1)}% of the budget."
            )
        else:
            gap = flyable_cells - geo_coverage
            recommendation = (
                f"This fleet reaches {geo_coverage}/{flyable_cells} flyable cells "
                f"({round(cov_pct * 100, 1)}%); {gap} cells are still unreached on your grid. "
                f"{budget_remaining} of budget remains."
            )
        st.markdown(
            f"<div style='background:#e4e1db;border-radius:12px;"
            f"border:1px solid rgba(65,30,87,0.18);padding:12px 14px;margin-top:14px;"
            f"color:#2c2c3b;font-weight:750;'>{recommendation}</div>",
            unsafe_allow_html=True,
        )
card_close()


if "selected_fleet" in st.session_state:
    budget_sel = st.session_state["fleet_budget"]
    selected_light = st.session_state["selected_fleet"]["light"]
    selected_heavy = st.session_state["selected_fleet"]["heavy"]
    selected_score = st.session_state["fleet_score"]

    st.write("")
    with st.container(border=True):
        with st.expander("Method Comparison — Genetic Algorithm vs Brute Force"):
            st.caption(
                "GA matches the Genetic Algorithm solution from your last Select Fleet "
                f"run at budget {budget_sel}; brute force is recomputed below (deterministic)."
            )
            if (
                st.session_state.get("fleet_ga_cache_budget") == budget_sel
                and "fleet_ga_cache_fleet" in st.session_state
            ):
                ga_fleet = st.session_state["fleet_ga_cache_fleet"]
                ga_score = st.session_state["fleet_ga_cache_score"]
            else:
                with st.spinner("Refreshing GA snapshot for comparison..."):
                    ga_fleet, ga_score = select_fleet(
                        budget_sel, method="ga", demand_cap=demand_target
                    )
            with st.spinner("Computing brute-force optimum..."):
                bf_fleet, bf_score = select_fleet(
                    budget_sel, method="brute", demand_cap=demand_target
                )

            def _fleet_summary(f, s):
                l = f["light"]
                h = f["heavy"]
                cost = (
                    l * DRONE_TYPES["light"]["cost"]
                    + h * DRONE_TYPES["heavy"]["cost"]
                )
                cov = min(
                    l * DRONE_TYPES["light"]["range"]
                    + h * DRONE_TYPES["heavy"]["range"],
                    GRID_TOTAL_CELLS,
                )
                geo, _ = _geographic_coverage(l, h)
                return {
                    "Light":          l,
                    "Heavy":          h,
                    "Total Cost":     cost,
                    "Optimizer Coverage": f"{cov}/{GRID_TOTAL_CELLS}",
                    "Grid Coverage":  f"{len(geo)}/{flyable_cells}",
                    "Fitness Score":  s,
                }

            cmp_df = pd.DataFrame(
                [
                    {"Method": "Genetic Algorithm", **_fleet_summary(ga_fleet, ga_score)},
                    {"Method": "Brute Force",       **_fleet_summary(bf_fleet, bf_score)},
                ]
            )
            st.dataframe(cmp_df, use_container_width=True, hide_index=True)

            if ga_score == bf_score:
                st.success("GA matched the brute-force optimum at this budget.")
            elif ga_score > bf_score:
                st.info(
                    "GA reported a higher score than brute force — this can happen if "
                    "brute force was constrained, but normally brute force is the ceiling."
                )
            else:
                gap = round(bf_score - ga_score, 4)
                st.warning(
                    f"GA was {gap} points below the brute-force optimum. "
                    "Try re-running — GA is stochastic — or increase generations / population."
                )

        st.write("")
        with st.expander("Top Alternative Fleets"):
            max_light_alt = budget_sel // DRONE_TYPES["light"]["cost"]
            max_heavy_alt = budget_sel // DRONE_TYPES["heavy"]["cost"]
            candidates = []
            for l_alt in range(max_light_alt + 1):
                for h_alt in range(max_heavy_alt + 1):
                    s_alt = calculate_fitness(
                        l_alt, h_alt, budget_sel, demand_cap=demand_target
                    )
                    if s_alt == float("-inf"):
                        continue
                    cost_alt = (
                        l_alt * DRONE_TYPES["light"]["cost"]
                        + h_alt * DRONE_TYPES["heavy"]["cost"]
                    )
                    cov_alt = min(
                        l_alt * DRONE_TYPES["light"]["range"]
                        + h_alt * DRONE_TYPES["heavy"]["range"],
                        GRID_TOTAL_CELLS,
                    )
                    geo_alt, _ = _geographic_coverage(l_alt, h_alt)
                    candidates.append(
                        {
                            "Light":               l_alt,
                            "Heavy":               h_alt,
                            "Total Cost":          cost_alt,
                            "Optimizer Coverage":  cov_alt,
                            "Grid Coverage":       len(geo_alt),
                            "Fitness Score":       s_alt,
                            "Selected":            "✓" if (l_alt == selected_light and h_alt == selected_heavy) else "",
                        }
                    )
            candidates.sort(key=lambda r: r["Fitness Score"], reverse=True)
            top_n = candidates[: min(10, len(candidates))]
            st.caption(
                f"Showing top {len(top_n)} of {len(candidates)} valid fleets at budget {budget_sel}. "
                f"Grid Coverage is measured against your {GRID_SIZE}×{GRID_SIZE} city grid "
                f"(≤ {flyable_cells} flyable cells)."
            )
            st.dataframe(pd.DataFrame(top_n), use_container_width=True, hide_index=True)

        st.write("")
        with st.expander("Manual Fitness Check"):
            st.caption(
                "Try your own combination and compare its fitness — and grid coverage — "
                "to the selected fleet."
            )
            max_light_in = int(budget_sel // DRONE_TYPES["light"]["cost"])
            max_heavy_in = int(budget_sel // DRONE_TYPES["heavy"]["cost"])
            mf1, mf2 = st.columns(2)
            with mf1:
                user_light = st.number_input(
                    "Light drones", min_value=0, max_value=max_light_in, value=min(selected_light, max_light_in), step=1
                )
            with mf2:
                user_heavy = st.number_input(
                    "Heavy drones", min_value=0, max_value=max_heavy_in, value=min(selected_heavy, max_heavy_in), step=1
                )

            user_cost = (
                user_light * DRONE_TYPES["light"]["cost"]
                + user_heavy * DRONE_TYPES["heavy"]["cost"]
            )
            user_score = calculate_fitness(
                int(user_light), int(user_heavy), budget_sel, demand_cap=demand_target
            )
            user_geo, user_eff = _geographic_coverage(int(user_light), int(user_heavy))

            if user_score == float("-inf"):
                st.error(
                    f"Over budget by {user_cost - budget_sel} — fleet cost is "
                    f"{user_cost} vs budget {budget_sel}."
                )
            else:
                mc1, mc2, mc3 = st.columns(3)
                mc1.metric("Your Fitness", user_score)
                mc2.metric("Your Total Cost", user_cost)
                mc3.metric("Your Grid Coverage", f"{len(user_geo)}/{flyable_cells}")

                delta = round(user_score - selected_score, 4)
                if delta > 0:
                    st.success(
                        f"Your combo scores {delta} higher than the selected fleet — "
                        "consider re-running the optimizer."
                    )
                elif delta == 0:
                    st.info("Your combo ties the selected fleet's score.")
                else:
                    st.warning(
                        f"Your combo scores {-delta} lower than the selected fleet."
                    )

        st.write("")
        with st.expander("Fitness Landscape (all valid combinations)"):
            st.caption(
                "Each cell shows the fitness for that (light × heavy) combination "
                "(warmer hues = higher fitness). Grey cells labeled None are over budget."
            )
            max_light_grid = budget_sel // DRONE_TYPES["light"]["cost"]
            max_heavy_grid = budget_sel // DRONE_TYPES["heavy"]["cost"]
            landscape = pd.DataFrame(
                index=pd.RangeIndex(max_light_grid + 1, name="light"),
                columns=pd.RangeIndex(max_heavy_grid + 1, name="heavy"),
                dtype=float,
            )
            for l_g in range(max_light_grid + 1):
                for h_g in range(max_heavy_grid + 1):
                    s_g = calculate_fitness(
                        l_g, h_g, budget_sel, demand_cap=demand_target
                    )
                    landscape.loc[l_g, h_g] = (
                        np.nan if s_g == float("-inf") else round(s_g, 2)
                    )

            finite = landscape.to_numpy(dtype=float, na_value=np.nan)
            finite_mask = np.isfinite(finite)
            vmin = float(np.nanmin(finite)) if finite_mask.any() else None
            vmax = float(np.nanmax(finite)) if finite_mask.any() else None

            def _invalid_cell_overlay(df):
                """NaN / over-budget cells only: mid-grey slab; valid cells keep warm gradient."""
                return pd.DataFrame(
                    np.where(
                        df.isna(),
                        "background-color:#9a9c99!important;color:#121212!important;"
                        "font-weight:600!important;border:1px solid rgba(24,26,30,0.14)!important;",
                        "",
                    ),
                    index=df.index,
                    columns=df.columns,
                )

            heatmap_style = (
                landscape.style.background_gradient(
                    cmap=_FITNESS_HEATMAP_CMAP,
                    axis=None,
                    vmin=vmin,
                    vmax=vmax,
                )
                .apply(_invalid_cell_overlay, axis=None)
                .format(precision=2, na_rep="None")
            )
            st.dataframe(heatmap_style, use_container_width=True)
