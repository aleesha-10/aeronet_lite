import streamlit as st
import pandas as pd

from grid_data import GRID
from grid_render import ZONE_BG, legend_letter_glyph, render_grid_html
from styles import inject_css
from csp_validator import run_all_constraints


st.set_page_config(page_title="CSP Validator • AeroNet Lite", page_icon="✅", layout="wide")
inject_css()
st.markdown(
    """
<style>
/* Equal-height R1–R4 cards: stretch paired columns + flex layout inside */
div[data-testid="stHorizontalBlock"]:has(.aeronet-rule-card--constraint) {
    display: flex;
    align-items: stretch !important;
    gap: 12px;
    margin-bottom: 12px;
}
div[data-testid="column"]:has(.aeronet-rule-card--constraint) {
    display: flex;
    flex-direction: column;
    min-width: 0;
}
div[data-testid="column"]:has(.aeronet-rule-card--constraint) > div {
    flex: 1 1 auto !important;
    display: flex !important;
    flex-direction: column !important;
    min-height: 0;
}
div[data-testid="column"]:has(.aeronet-rule-card--constraint)
    div[data-testid="element-container"],
div[data-testid="column"]:has(.aeronet-rule-card--constraint)
    div[data-testid="stMarkdownContainer"] {
    flex: 1 1 auto !important;
    display: flex !important;
    flex-direction: column !important;
    min-height: 0;
}
div[data-testid="column"]:has(.aeronet-rule-card--constraint)
    div[data-testid="stMarkdownContainer"]
    > div {
    flex: 1 1 auto;
    display: flex;
    flex-direction: column;
    min-height: 0;
}
.aeronet-rule-card--constraint {
    flex: 1 1 auto;
    display: flex;
    flex-direction: column;
    min-height: 188px;
    height: 100%;
    margin-bottom: 0 !important;
    box-sizing: border-box;
}
.aeronet-rule-card--constraint .aeronet-rule-card__footer {
    margin-top: auto;
    flex-shrink: 0;
}
</style>
    """,
    unsafe_allow_html=True,
)
CSP_SVG = """
<svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true"
     xmlns="http://www.w3.org/2000/svg">
  <path d="M4 7h16" stroke="#405C6F" stroke-width="2" stroke-linecap="round"/>
  <path d="M4 12h10" stroke="#50314B" stroke-width="2" stroke-linecap="round"/>
  <path d="M4 17h16" stroke="#405C6F" stroke-width="2" stroke-linecap="round"/>
  <circle cx="18" cy="12" r="2" fill="#6BB1AD"/>
  <path d="M18 10.6v2.8" stroke="#181A1E" stroke-width="1.6" stroke-linecap="round"/>
</svg>
"""

ribbon_html = f"""<div class="aeronet-top-ribbon">
<div style="display:flex;align-items:center;justify-content:space-between;gap:14px;">
<div style="display:flex;align-items:center;gap:10px;">
{CSP_SVG}
<div>
<div style="font-size:1.75rem;font-weight:850;letter-spacing:-0.02em;color:#50314B;line-height:1.05;">CSP Validator</div>
<div style="margin-top:0.15rem;color:#405C6F;font-weight:600;">Module 1 — Constraint Satisfaction Problem (CSP) validator for the city grid.</div>
</div>
</div>
</div>
</div>"""
st.markdown(ribbon_html, unsafe_allow_html=True)

if "rule_results" not in st.session_state:
    st.session_state["rule_results"] = {
        "R1": {"status": "PENDING", "violations": []},
        "R2": {"status": "PENDING", "violations": []},
        "R3": {"status": "PENDING", "violations": []},
        "R4": {"status": "PENDING", "violations": []},
    }
if "violations_count" not in st.session_state:
    st.session_state["violations_count"] = 0
if "validation_run" not in st.session_state:
    st.session_state["validation_run"] = False

def _run_validator() -> None:
    import time

    with st.spinner("Running CSP checks..."):
        time.sleep(0.6)
        raw = run_all_constraints(GRID)

    results = {}
    total = 0
    for rid, info in raw.items():
        v = list(info["violations"])
        if rid == "R4":
            satisfied = bool(info.get("satisfied"))
            results[rid] = {
                "status": "PASS" if satisfied else "FAIL",
                "violations": v,
                "satisfied": satisfied,
                "hospital_count": int(info.get("hospital_count", 0)),
            }
            if not satisfied:
                total += 1
        else:
            total += len(v)
            results[rid] = {
                "status": "PASS" if len(v) == 0 else "FAIL",
                "violations": v,
            }

    st.session_state["rule_results"] = results
    st.session_state["violations_count"] = total
    st.session_state["validation_run"] = True
    st.session_state["_suppress_home_csp_hydrate"] = False

RULE_META = {
    "R1": {
        "name": "Industrial Safety",
        "color": "#8C3352",
        "desc": "Industrial cells must not be directly adjacent (up/down/left/right) to Schools or Hospitals.",
        "hint": "Check 4-directional neighbors for each Industrial cell.",
    },
    "R2": {
        "name": "Residential Coverage",
        "color": "#399DB5",
        "desc": "Every Residential cell must be within Manhattan distance 3 of a Hub.",
        "hint": "Compute Manhattan distance to all hubs; require min ≤ 3.",
    },
    "R3": {
        "name": "Hub Charging Access",
        "color": "#7C4EBB",
        "desc": "Every Hub must have a Charging Pad within Manhattan distance 2.",
        "hint": "Compute Manhattan distance to all charging pads; require min ≤ 2.",
    },
    "R4": {
        "name": "Medical Emergency Access",
        "color": "#DE5C8F",
        "desc": "At least one Hospital must have a Medical Pickup within Manhattan distance 1.",
        "hint": "For each hospital, check any medical pickup at distance 1.",
    },
}


def _status_badge(status: str) -> str:
    if status == "PASS":
        return "<span style='color:#181A1E; background: rgba(107, 177, 173, 0.35); padding:3px 8px; border-radius:999px; font-weight:700;'>PASS</span>"
    if status == "FAIL":
        return "<span style='color:#181A1E; background: rgba(247, 94, 116, 0.45); padding:3px 8px; border-radius:999px; font-weight:700;'>FAIL</span>"
    return "<span style='color:#181A1E; background: rgba(154, 171, 186, 0.35); padding:3px 8px; border-radius:999px; font-weight:700;'>PENDING</span>"


def _rule_card(rule_id: str) -> None:
    meta = RULE_META[rule_id]
    result = st.session_state["rule_results"].get(rule_id, {"status": "PENDING", "violations": []})
    status = result.get("status", "PENDING")
    vcount = len(result.get("violations", []))
    icon = (
        "<svg width='16' height='16' viewBox='0 0 24 24' fill='none' aria-hidden='true' "
        "xmlns='http://www.w3.org/2000/svg'>"
        f"<path d='M12 3l9 4.5v9L12 21l-9-4.5v-9L12 3z' stroke='{meta['color']}' stroke-width='2'/>"
        f"<path d='M8 12h8' stroke='{meta['color']}' stroke-width='2' stroke-linecap='round'/>"
        "</svg>"
    )
    pill = f"<span style='background:{meta['color']}; color:#EDECDB; padding:3px 10px; border-radius:999px; font-weight:800; font-size:12px;'>{rule_id}</span>"
    desc = meta["desc"]
    if len(desc) > 92:
        desc = desc[:90].rstrip() + "…"

    st.markdown(
        f"""
<div class="aeronet-rule-card aeronet-rule-card--constraint"
     style="background:#EDECDB; border-radius: 14px; border: 1px solid rgba(24,26,30,0.12); border-left: 4px solid {meta['color']}; padding: 14px; box-shadow: 0 10px 24px rgba(24,26,30,0.06);">
  <div style="display:flex; align-items:center; justify-content:space-between; gap:10px;">
    <div style="display:flex; align-items:center; gap:10px;">
      {pill}
      <div style="display:flex; align-items:center; gap:8px;">
        {icon}
        <div style="font-weight:850; color:#181A1E; line-height:1.1;">{meta['name']}</div>
      </div>
    </div>
    <div>{_status_badge(status)}</div>
  </div>
  <div style="margin-top:8px; color:#181A1E; opacity:0.92; font-size:13px; line-height:1.35; flex-shrink: 0;">{desc}</div>
  <div class="aeronet-rule-card__footer" style="margin-top:10px; display:flex; align-items:center; justify-content:space-between; gap:10px;">
    <div style="color:#905F9E; font-size:12px;"><b>Rule:</b> {meta['hint']}</div>
    <div style="color:#50314B; font-weight:850;">{vcount} issue(s)</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


st.markdown('<div class="aeronet-ribbon-cta">', unsafe_allow_html=True)
st.button("Run CSP Validator", type="primary", use_container_width=True, on_click=_run_validator)
st.markdown("</div>", unsafe_allow_html=True)
if st.session_state["validation_run"]:
    n = int(st.session_state.get("violations_count", 0))
    if n == 0:
        st.success("All constraints satisfied!")
    else:
        st.error(f"{n} constraint(s) violated.")

st.subheader("Constraints (R1–R4)")
c1, c2 = st.columns(2)
with c1:
    _rule_card("R1")
with c2:
    _rule_card("R2")
c3, c4 = st.columns(2)
with c3:
    _rule_card("R3")
with c4:
    _rule_card("R4")


st.divider()
st.subheader("Violations Report")

SUGGESTED_FIX = {
    "R1": "Move Industrial cell away from School/Hospital, or rezone neighbor",
    "R2": "Add a Hub near ({row},{col}) or rezone cell to Open Field",
    "R3": "Add a Charging Pad within 2 cells of Hub at ({row},{col})",
    "R4": "Add Medical Pickup adjacent to Hospital at ({row},{col})",
}

report_rows = []
rule_results = st.session_state["rule_results"]
for rid in ["R1", "R2", "R3", "R4"]:
    meta = RULE_META[rid]
    violations = rule_results.get(rid, {}).get("violations", [])
    if not st.session_state["validation_run"]:
        report_rows.append(
            {
                "Rule": rid,
                "Cell (row, col)": "-",
                "Constraint": meta["name"],
                "Suggested Fix": "Run the validator to compute violations.",
            }
        )
        continue

    if rid == "R4" and st.session_state["validation_run"]:
        satisfied = bool(rule_results.get("R4", {}).get("satisfied"))
        hospital_count = int(rule_results.get("R4", {}).get("hospital_count", 0))
        if satisfied:
            report_rows.append(
                {
                    "Rule": rid,
                    "Cell (row, col)": "PASS",
                    "Constraint": meta["name"],
                    "Suggested Fix": "Rule satisfied (at least one hospital has medical pickup access).",
                }
            )
        else:
            if hospital_count == 0:
                report_rows.append(
                    {
                        "Rule": rid,
                        "Cell (row, col)": "FAIL",
                        "Constraint": meta["name"],
                        "Suggested Fix": "Add at least one Hospital cell to the grid.",
                    }
                )
            else:
                for (r, c) in violations:
                    report_rows.append(
                        {
                            "Rule": rid,
                            "Cell (row, col)": f"({r}, {c})",
                            "Constraint": meta["name"],
                            "Suggested Fix": SUGGESTED_FIX[rid].format(row=r, col=c),
                        }
                    )
        continue

    if not violations:
        report_rows.append(
            {
                "Rule": rid,
                "Cell (row, col)": "PASS",
                "Constraint": meta["name"],
                "Suggested Fix": "No action needed.",
            }
        )
    else:
        for (r, c) in violations:
            report_rows.append(
                {
                    "Rule": rid,
                    "Cell (row, col)": f"({r}, {c})",
                    "Constraint": meta["name"],
                    "Suggested Fix": SUGGESTED_FIX[rid].format(row=r, col=c),
                }
            )

df = pd.DataFrame(report_rows, columns=["Rule", "Cell (row, col)", "Constraint", "Suggested Fix"])

def _status_from_row(row: pd.Series) -> str:
    cell = str(row.get("Cell (row, col)", ""))
    if cell in {"PASS"}:
        return "PASS"
    if cell in {"FAIL"}:
        return "FAIL"
    if cell == "-" or cell.strip() == "":
        return "PENDING"
    return "FAIL"


df.insert(1, "Status", df.apply(_status_from_row, axis=1))

RULE_TINT = {
    "R1": "rgba(159, 70, 88, 0.10)",   # english-red
    "R2": "rgba(107, 177, 173, 0.12)", # veranda-blue
    "R3": "rgba(64, 92, 111, 0.10)",   # deep-space
    "R4": "rgba(247, 94, 116, 0.10)",  # brink-pink
}

def _style_rows(row: pd.Series):
    rid = str(row.get("Rule", ""))
    status = str(row.get("Status", "PENDING"))
    base = RULE_TINT.get(rid, "rgba(24, 26, 30, 0.04)")

    rule_color = RULE_META.get(rid, {}).get("color", "#7C4EBB")

    if status == "PASS":
        bg = "rgba(107, 177, 173, 0.10)"
        status_bg = "rgba(107, 177, 173, 0.26)"
        status_fg = "#2C2C3B"
    elif status == "FAIL":
        bg = base
        status_bg = "rgba(247, 94, 116, 0.26)"
        status_fg = "#2C2C3B"
    else:
        bg = "rgba(154, 171, 186, 0.14)"
        status_bg = "rgba(154, 171, 186, 0.28)"
        status_fg = "#2C2C3B"

    # Columns: Rule | Status | Cell (row, col) | Constraint | Suggested Fix
    return [
        f"background-color:{bg}; box-shadow: inset 4px 0 0 0 {rule_color}; font-weight:800;",
        f"background-color:{status_bg}; color:{status_fg}; font-weight:900; text-transform:uppercase; border-radius:999px;",
        f"background-color:{bg};",
        f"background-color:{bg}; font-weight:800; color:#411E57;",
        f"background-color:{bg};",
    ]


styled = (
    df.style
    .apply(_style_rows, axis=1)
    .set_table_styles(
        [
            {"selector": "table", "props": [("font-family", '"Space Grotesk", system-ui, Segoe UI, Arial, sans-serif')]},
            {"selector": "th", "props": [("font-weight", "750")]},
            {"selector": "td", "props": [("font-size", "14px"), ("line-height", "1.25")]},
            {"selector": "thead th", "props": [("background-color", "#411E57"), ("color", "#FBC8CC")]},
            {"selector": "tbody td", "props": [("border-bottom", "1px solid rgba(44,44,59,0.08)")]},
        ]
    )
    .set_properties(**{"font-weight": "650"}, subset=["Rule", "Status"])
    .set_properties(**{"font-weight": "850", "color": "#411E57"}, subset=["Constraint"])
    .set_properties(**{"color": "#181A1E"}, subset=["Suggested Fix"])
)

st.dataframe(styled, use_container_width=True, hide_index=True)


st.write("")
st.subheader("Constraint Graph Visualization")

gcol, lcol = st.columns([8, 4], gap="large")
with gcol:
    highlights = {}
    if st.session_state["validation_run"]:
        for rid in ["R1", "R2", "R3", "R4"]:
            coords = rule_results.get(rid, {}).get("violations", [])
            if coords:
                highlights[rid] = coords

    highlight_styles = {
        "R1": "box-shadow: inset 0 0 0 3px #9F4658;",
        "R2": "background-image: linear-gradient(rgba(252, 207, 150, 0.45), rgba(252, 207, 150, 0.45));",
        "R3": "background-image: linear-gradient(rgba(64, 92, 111, 0.28), rgba(64, 92, 111, 0.28));",
        "R4": "background-image: linear-gradient(rgba(229, 150, 173, 0.35), rgba(229, 150, 173, 0.35));",
    }

    grid_html = render_grid_html(GRID, cell_px=58, highlights=highlights, highlight_styles=highlight_styles, show_symbols=True)
    st.markdown(grid_html, unsafe_allow_html=True)

with lcol:
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
        f"<div style='display:flex;align-items:center;margin:6px 0' title='Medical pickup point'>"
        f"{legend_letter_glyph('M', fg='#181A1E')}Medical pickup</div>"
        f"<div style='display:flex;align-items:center;margin:6px 0' title='No-fly zone'>"
        f"{legend_letter_glyph('N', fg='#EDECDB', bg='#F75E74')}No-fly</div>"
        "</div>",
        "<div style='margin-top:10px; color:#405C6F; font-size:12px;'>Tip: hover a cell to see details.</div>",
    ]
    st.markdown("<br/>".join(legend_lines), unsafe_allow_html=True)


st.write("")
st.subheader("Constraint Summary")
sum_cols = st.columns(4)
for i, rid in enumerate(["R1", "R2", "R3", "R4"]):
    res = rule_results.get(rid, {"status": "PENDING", "violations": []})
    vcount = len(res.get("violations", []))
    status = res.get("status", "PENDING")
    with sum_cols[i]:
        shown_status = "PENDING" if not st.session_state["validation_run"] else status
        if rid == "R4" and st.session_state["validation_run"]:
            shown_status = "PASS" if bool(res.get("satisfied")) else "FAIL"
            if shown_status == "PASS":
                vcount = 0

        color = "#9AABBA"
        if shown_status == "PASS":
            color = "#6BB1AD"
        elif shown_status == "FAIL":
            color = "#F75E74"

        st.markdown(
            f"<div style='font-weight:850; color:#50314B; font-size:12px;'>{rid}</div>"
            f"<div style='font-size:24px; font-weight:900; color:#181A1E; line-height:1.1;'>{vcount}</div>"
            f"<div style='display:inline-block; margin-top:6px; padding:3px 10px; border-radius:999px; "
            f"background: rgba(24,26,30,0.06); border:1px solid rgba(24,26,30,0.10); "
            f"color:{color}; font-weight:900; font-size:12px;'>{shown_status}</div>",
            unsafe_allow_html=True,
        )

