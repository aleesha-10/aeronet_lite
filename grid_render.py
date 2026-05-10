from __future__ import annotations

import html as html_module
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, FrozenSet


ZONE_BG: Mapping[str, str] = {
    # Original zone mapping (Coastal/Winter/Berry palette)
    "Residential": "rgba(229, 150, 173, 0.8)",  # #E596AD (Charm Pink)
    "Industrial": "#96A3B4",  # Cadet Grey
    "Commercial": "#FCCF96",  # Peach-Orange
    # Use Deep Space Sparkle for strong contrast vs Residential
    "Hospital": "rgba(64, 92, 111, 0.78)",  # #405C6F (Deep Space Sparkle)
    "School": "rgba(107, 177, 173, 0.7)",  # #6BB1AD (Veranda Blue)
    "Open Field": "rgba(167, 188, 189, 0.5)",  # #A7BCBD (Sky Cloud)
}

# Parchment tile behind legend glyphs (matches typical zone cell lightness).
_LEGEND_GLYPH_BG_DEFAULT = "#EDE9DC"


def legend_letter_glyph(
    ch: str,
    *,
    fg: str,
    bg: str | None = None,
    size_px: int = 22,
) -> str:
    """Single-letter chip for sidebar legends (same letters as grid cell markers)."""
    escaped = html_module.escape(ch)
    bg_css = bg or _LEGEND_GLYPH_BG_DEFAULT
    return (
        f"<span style=\"display:inline-flex;align-items:center;justify-content:center;"
        f"width:{size_px}px;height:{size_px}px;margin-right:8px;border-radius:6px;"
        f"font-weight:900;font-size:13px;line-height:1;color:{fg};background:{bg_css};"
        f"border:1px solid rgba(24,26,30,0.14);vertical-align:middle;box-sizing:border-box;\">"
        f"{escaped}</span>"
    )


def render_grid_html(
    grid: Sequence[dict],
    *,
    size: int = 10,
    cell_px: int = 48,
    highlights: Optional[Dict[str, Iterable[Tuple[int, int]]]] = None,
    highlight_styles: Optional[Dict[str, str]] = None,
    show_symbols: bool = True,
    show_highlight_labels: bool = True,
    highlight_on: str = "td",
    highlight_on_by_rule: Optional[Mapping[str, str]] = None,
    hide_highlight_labels_for: Optional[Iterable[str]] = None,
    highlight_classes: Optional[Mapping[str, str]] = None,
    highlight_label_overrides: Optional[Mapping[str, str]] = None,
) -> str:
    """
    Build an HTML table representation of the grid.

    highlights:
      Mapping of rule_id -> iterable of (row, col) tuples to highlight.
    highlight_styles:
      Mapping of rule_id -> CSS snippet appended to the <td> style.
    show_highlight_labels:
      When True, show small rule-id chips (e.g. R1, F) on highlighted cells.
      Set False for overlays where the legend is explained outside the grid
      (cleaner when only highlight rings/chips carry meaning).
    highlight_on:
      "td" — apply highlight_styles on the cell (needed for CSP full-cell washes).
      "inner" — apply them on `.aeronet-cell-inner` (rounded face). Use for outline
      rings so rectangles do not peek through rounded corners as a teal/blue lattice.
    highlight_on_by_rule:
      Optional override per rule_id -> "td" | "inner" (e.g. path glow on <td>,
      endpoints on `.aeronet-cell-inner`).
    hide_highlight_labels_for:
      Rule ids (e.g. "PATH") to omit from corner chips — keeps the legend while
      decluttering repetitive labels.
    highlight_classes:
      Optional rule_id -> extra CSS class names on `.aeronet-cell-inner` (e.g. path
      corridor glow via scoped styles in the page).
    highlight_label_overrides:
      Optional rule_id -> label text for corner chips (e.g. PATH -> "Path").
    """
    highlights = highlights or {}
    highlight_styles = highlight_styles or {}
    if highlight_on not in {"td", "inner"}:
        highlight_on = "td"

    hon_by_rule = dict(highlight_on_by_rule or {})
    hide_chips_for: FrozenSet[str] = frozenset(hide_highlight_labels_for or [])
    h_classes = dict(highlight_classes or {})
    label_over = dict(highlight_label_overrides or {})

    highlighted_at: Dict[Tuple[int, int], List[str]] = {}
    for rule_id, coords in highlights.items():
        for rc in coords:
            highlighted_at.setdefault(rc, []).append(rule_id)

    def symbol(cell: dict) -> str:
        if not show_symbols:
            return ""
        # Single-letter markers: D hub, C charging, M medical pickup, N no-fly.
        if cell.get("no_fly"):
            return "N"
        if cell.get("is_hub"):
            return "D"
        if cell.get("is_charging"):
            return "C"
        if cell.get("is_medical_pickup"):
            return "M"
        return ""

    rows_html: List[str] = []
    for r in range(size):
        tds: List[str] = []
        for c in range(size):
            cell = grid[r * size + c]
            base_bg = "#F75E74" if cell.get("no_fly") else ZONE_BG.get(cell.get("zone", ""), "#EDECDB")
            text_color = "#EDECDB" if cell.get("no_fly") else "#181A1E"

            title = (
                f"({cell['row']},{cell['col']}) {cell['zone']} | "
                f"density:{cell['density']} | hub:{cell['is_hub']} | no_fly:{cell['no_fly']}"
            )
            tooltip = (
                f"({cell['row']},{cell['col']}) {cell['zone']}"
                "&#10;"
                f"density:{cell['density']} | hub:{cell['is_hub']} | no_fly:{cell['no_fly']}"
            ).replace('"', "&quot;")

            rc = (cell["row"], cell["col"])
            rule_labels = highlighted_at.get(rc, [])
            style_bits = [
                f"width:{cell_px}px;height:{cell_px}px;",
                "text-align:center;vertical-align:middle;",
                "border:1px solid rgba(24,26,30,0.12);",
                f"background-color:{base_bg};",
                "position:relative;",
            ]
            inner_highlight_bits: List[str] = []
            for rid in rule_labels:
                snippet = highlight_styles.get(rid, "")
                if snippet:
                    layer = hon_by_rule.get(rid, highlight_on)
                    if layer not in {"td", "inner"}:
                        layer = highlight_on
                    if layer == "inner":
                        inner_highlight_bits.append(snippet)
                    else:
                        style_bits.append(snippet)

            sym = symbol(cell)
            if sym:
                sym_html = (
                    "<div style='display:flex; justify-content:center; align-items:center;'>"
                    f"<span style='font-weight:900; color:{text_color}; font-size:15px; "
                    "line-height:1; letter-spacing:-0.02em;'>"
                    f"{html_module.escape(sym)}</span>"
                    "</div>"
                )
            else:
                sym_html = ""

            label_html = ""
            chip_rules = [rid for rid in rule_labels if rid not in hide_chips_for]
            if show_highlight_labels and chip_rules:
                label_text = ",".join(label_over.get(rid, rid) for rid in chip_rules)
                label_html = (
                    "<div class='aeronet-highlight-chip' style='position:absolute; right:4px; top:4px;"
                    "font-size:9px; line-height:1.1; padding:2px 5px; border-radius:6px;"
                    "background: rgba(24,26,30,0.72); color:#f4f1ea; font-weight:700;"
                    "pointer-events:none; z-index:2;'>"
                    f"{label_text}"
                    "</div>"
                )

            inner_style = "".join(inner_highlight_bits)
            inner_class_bits = ["aeronet-cell-inner"]
            for rid in rule_labels:
                extra = h_classes.get(rid)
                if extra:
                    inner_class_bits.append(extra)
            inner_open = f"<div class=\"{' '.join(inner_class_bits)}\""
            if inner_style:
                inner_open += f' style="{inner_style}"'
            inner_open += ">"

            tds.append(
                "<td class='aeronet-cell' "
                f'data-tooltip="{tooltip}" '
                f'data-zone="{cell.get("zone","")}" '
                f'style="{"".join(style_bits)}">'
                f"{inner_open}{sym_html}{label_html}</div>"
                "</td>"
            )
        rows_html.append("<tr>" + "".join(tds) + "</tr>")

    return (
        "<div class='aeronet-grid-wrap'>"
        "<div class='aeronet-grid-card'>"
        "<div class='aeronet-grid-stage'>"
        "<table class='aeronet-grid' role='grid' aria-label='AeroNet city grid'>"
        + "".join(rows_html)
        + "</table>"
        "</div>"
        "</div>"
        "</div>"
    )

