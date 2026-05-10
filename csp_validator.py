from __future__ import annotations

from typing import Any, Dict, List, Tuple

from grid_data import get_neighbors, manhattan

Coord = Tuple[int, int]


def check_R1_industrial_safety(grid: List[Dict[str, Any]]) -> List[Coord]:
    """
    R1: No Industrial cell can be directly adjacent (4-directional) to a School or Hospital.
    For each Industrial cell, call get_neighbors(row, col).
    If any neighbor has zone == 'School' or zone == 'Hospital', it's a violation.
    Returns: list of violating Industrial cell (row, col) tuples
    """
    violations: List[Coord] = []
    industrial = [c for c in grid if c.get("zone") == "Industrial"]
    for cell in industrial:
        r, c = cell["row"], cell["col"]
        for n in get_neighbors(r, c):
            if n.get("zone") in {"School", "Hospital"}:
                violations.append((r, c))
                break
    return violations


def check_R2_residential_coverage(grid: List[Dict[str, Any]]) -> List[Coord]:
    """
    R2: Every Residential cell must be within Manhattan distance 3 of at least one Hub.
    Get all Residential cells. Get all Hub cells (is_hub=True).
    For each Residential cell, compute manhattan distance to every hub.
    If minimum distance > 3, it's a violation.
    Returns: list of violating Residential cell (row, col) tuples
    """
    hubs = [(c["row"], c["col"]) for c in grid if c.get("is_hub")]
    res = [c for c in grid if c.get("zone") == "Residential"]
    violations: List[Coord] = []
    for cell in res:
        rc = (cell["row"], cell["col"])
        if not hubs:
            violations.append(rc)
            continue
        if min(manhattan(rc, h) for h in hubs) > 3:
            violations.append(rc)
    return violations


def check_R3_hub_charging(grid: List[Dict[str, Any]]) -> List[Coord]:
    """
    R3: Every Hub must have at least one Charging Pad within Manhattan distance 2.
    Get all Hub cells. Get all Charging cells (is_charging=True).
    For each hub, compute manhattan distance to every charging pad.
    If minimum distance > 2, it's a violation.
    Returns: list of violating Hub cell (row, col) tuples
    """
    hubs = [(c["row"], c["col"]) for c in grid if c.get("is_hub")]
    charging = [(c["row"], c["col"]) for c in grid if c.get("is_charging")]
    violations: List[Coord] = []
    for hub in hubs:
        if not charging or min(manhattan(hub, ch) for ch in charging) > 2:
            violations.append(hub)
    return violations


def check_R4_medical_access(grid: List[Dict[str, Any]]) -> List[Coord]:
    """
    R4: At least one Hospital must have a Medical Pickup within Manhattan distance 1.
    Get all Hospital cells. Get all Medical Pickup cells (is_medical_pickup=True).
    For each hospital, check if any medical pickup has manhattan distance == 1.
    Returns: list of Hospital cells that do NOT have a nearby medical pickup (distance 1).

    Note: This list is for visualization/reporting. The rule is considered satisfied
    if at least one hospital has medical access.
    """
    hospitals = [(c["row"], c["col"]) for c in grid if c.get("zone") == "Hospital"]
    pickups = [(c["row"], c["col"]) for c in grid if c.get("is_medical_pickup")]

    uncovered: List[Coord] = []
    for h in hospitals:
        if not any(manhattan(h, p) == 1 for p in pickups):
            uncovered.append(h)
    return uncovered


def run_all_constraints(grid: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Run all 4 checks and return a combined results dict."""
    r4_uncovered = check_R4_medical_access(grid)
    hospitals = [(c["row"], c["col"]) for c in grid if c.get("zone") == "Hospital"]
    r4_satisfied = len(hospitals) > 0 and len(r4_uncovered) < len(hospitals)
    return {
        "R1": {"name": "Industrial Safety", "violations": check_R1_industrial_safety(grid)},
        "R2": {"name": "Residential Coverage", "violations": check_R2_residential_coverage(grid)},
        "R3": {"name": "Hub Charging Access", "violations": check_R3_hub_charging(grid)},
        "R4": {
            "name": "Medical Emergency Access",
            "violations": r4_uncovered,
            "satisfied": r4_satisfied,
            "hospital_count": len(hospitals),
        },
    }


# Backwards-compatible entrypoint (unused for now).
def validate_constraints(grid: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    results = run_all_constraints(grid)
    out: List[Dict[str, Any]] = []
    for rid, info in results.items():
        for (r, c) in info["violations"]:
            out.append({"rule": rid, "row": r, "col": c})
    return out

