from __future__ import annotations

from typing import Any, Dict, List, Tuple


GRID_SIZE = 10

# A realistic 10x10 city grid (100 cells). We keep the definition deterministic
# to make CSP demos repeatable.
#
# Required intentional violations for demo:
# - At least 1 Industrial cell adjacent to a School
# - At least 1 Residential cell >3 Manhattan distance from any hub


_ZONE_MAP: List[List[str]] = [
    # 0
    ["Industrial", "Industrial", "Commercial", "Commercial", "Open Field", "Residential", "Residential", "Commercial", "Commercial", "Residential"],
    # 1
    ["Industrial", "Commercial", "Commercial", "Residential", "Residential", "Residential", "Commercial", "Commercial", "Residential", "Residential"],
    # 2
    ["Commercial", "Commercial", "Residential", "Residential", "Residential", "Commercial", "Residential", "Hospital", "Commercial", "Residential"],
    # 3
    ["Commercial", "Residential", "Residential", "Residential", "Commercial", "Commercial", "Commercial", "Residential", "Residential", "Open Field"],
    # 4
    ["Residential", "Residential", "Commercial", "Commercial", "Industrial", "Industrial", "Commercial", "Residential", "Residential", "Commercial"],
    # 5
    ["Residential", "Commercial", "Commercial", "Commercial", "Industrial", "Open Field", "Commercial", "Residential", "Commercial", "Commercial"],
    # 6
    ["Open Field", "Industrial", "Industrial", "School", "Residential", "Commercial", "Commercial", "Residential", "Residential", "Commercial"],
    # 7
    ["Industrial", "Industrial", "Commercial", "Residential", "Residential", "Commercial", "Open Field", "Commercial", "Residential", "Residential"],
    # 8
    ["Commercial", "Commercial", "Residential", "Residential", "Commercial", "Commercial", "Residential", "Residential", "Commercial", "Commercial"],
    # 9
    ["Commercial", "Residential", "Open Field", "Residential", "Commercial", "Commercial", "Residential", "Commercial", "Commercial", "Residential"],
]


def _density_for_zone(zone: str, row: int, col: int) -> int:
    if zone == "Residential":
        # slightly denser near center
        base = 5200 + (1000 - 80 * abs(4 - row) - 80 * abs(4 - col))
        return int(max(4200, min(7900, base)))
    if zone == "Commercial":
        base = 3800 + (700 - 60 * abs(4 - row) - 60 * abs(4 - col))
        return int(max(2500, min(5200, base)))
    if zone == "Industrial":
        base = 1800 + (300 - 40 * abs(5 - row) - 40 * abs(5 - col))
        return int(max(900, min(2400, base)))
    if zone in {"Hospital", "School"}:
        return 4200 if zone == "Hospital" else 3600
    # Open Field
    return 700 + (30 * ((row + col) % 6))


def _demand_for_zone(zone: str, row: int, col: int) -> float:
    if zone == "Residential":
        return round(0.55 + 0.05 * ((row + col) % 5), 2)
    if zone == "Commercial":
        return round(0.65 + 0.05 * ((row * 2 + col) % 5), 2)
    if zone == "Industrial":
        return round(0.35 + 0.05 * ((row + 2 * col) % 4), 2)
    if zone == "Hospital":
        return 0.95
    if zone == "School":
        return 0.6
    return round(0.15 + 0.03 * ((row + col) % 5), 2)


# Hubs spread to cover most residential areas (keep a few intentional R2 violations).
_HUBS = {(0, 2), (1, 7), (5, 1), (7, 6)}  # >= 3 hubs

# Charging pads placed so every hub satisfies R3 (within distance 2).
_CHARGING = {(0, 1), (1, 6), (1, 7), (5, 2), (6, 6)}  # >= 4 charging pads
_NO_FLY = {(0, 4), (5, 5), (9, 2)}  # >= 3 no-fly cells

_HOSPITAL = (2, 7)
_MEDICAL_PICKUP = (2, 6)  # within 1 Manhattan distance of hospital


GRID: List[Dict[str, Any]] = []
for r in range(GRID_SIZE):
    for c in range(GRID_SIZE):
        zone = _ZONE_MAP[r][c]
        cell = {
            "row": r,
            "col": c,
            "zone": zone,
            "density": _density_for_zone(zone, r, c),
            "is_hub": (r, c) in _HUBS,
            "is_charging": (r, c) in _CHARGING,
            "is_medical_pickup": (r, c) == _MEDICAL_PICKUP,
            "no_fly": (r, c) in _NO_FLY,
            "demand": _demand_for_zone(zone, r, c),
        }
        GRID.append(cell)


def get_cell(row: int, col: int) -> Dict[str, Any]:
    if not (0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE):
        raise IndexError(f"Cell out of bounds: ({row}, {col})")
    return GRID[row * GRID_SIZE + col]


def get_neighbors(row: int, col: int) -> List[Dict[str, Any]]:
    neighbors: List[Dict[str, Any]] = []
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        rr, cc = row + dr, col + dc
        if 0 <= rr < GRID_SIZE and 0 <= cc < GRID_SIZE:
            neighbors.append(get_cell(rr, cc))
    return neighbors


def manhattan(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def get_all_of_type(field: str, value: Any) -> List[Dict[str, Any]]:
    return [cell for cell in GRID if cell.get(field) == value]

