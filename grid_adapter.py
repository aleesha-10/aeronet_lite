"""Shared dict → A* grid adapter (Path Planner, Disruption Handler, simulator)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Set


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
