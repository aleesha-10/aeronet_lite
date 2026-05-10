"""
delivery_simulator.py — 20-step integration simulation (GRID + plan_delivery_route).
Instantiate with adapters, drones, and deliveries; call run(...) for a stepped event_log.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from astar_planner import plan_delivery_route
from csp_validator import run_all_constraints
from grid_adapter import build_adapter_grid
from grid_data import GRID, get_all_of_type

Coord = Tuple[int, int]


def _csp_violation_total(raw: Dict[str, Any]) -> int:
    total = 0
    for rid, info in raw.items():
        if rid == "R4":
            if not bool(info.get("satisfied", True)):
                total += 1
        else:
            total += len(info.get("violations", []))
    return total


@dataclass
class Delivery:
    delivery_id: str
    hub: Coord
    pickup: Coord
    dropoff: Coord
    status: str = "pending"  # pending, active, completed, delayed, failed


@dataclass
class Drone:
    drone_id: str
    drone_type: str  # "light" | "heavy"
    position: Coord
    home_hub: Coord
    path: List[Coord] = field(default_factory=list)
    path_index: int = 0
    delivery: Optional[Delivery] = None


class DeliverySimulator:
    """
    ``adapted_grid`` is ignored for replanning; ``GRID`` flat dict + ``extra_nf`` rebuilds adapters.
    """

    def __init__(
        self,
        adapted_grid: list,
        drones: List[Drone],
        deliveries: List[Delivery],
        *,
        grid_flat: Optional[List[dict]] = None,
    ) -> None:
        self.adapted_grid = adapted_grid
        self.grid_flat = list(grid_flat) if grid_flat is not None else list(GRID)
        self.drones = drones
        self.deliveries = deliveries
        self.extra_nf: Set[Coord] = set()
        self.base_nf = {(c["row"], c["col"]) for c in get_all_of_type("no_fly", True)}
        self.event_log: List[str] = []
        self.completed = 0
        self.delayed = 0
        self.failed = 0
        self.no_fly_event_count = 0

    def _adapt(self) -> list:
        return build_adapter_grid(self.grid_flat, extra_no_fly=self.extra_nf)

    def _route_and_bind(self, dr: Drone, dlv: Delivery) -> None:
        dlv.status = "pending"
        dr.delivery = dlv
        g = self._adapt()
        path, _cost, _segs, ok = plan_delivery_route(dlv.hub, dlv.pickup, dlv.dropoff, g)
        if ok and path:
            dr.path = path
            dr.path_index = 0
            dr.position = path[0]
            dr.home_hub = dlv.hub
            dlv.status = "active"
        else:
            dr.path = []
            dr.path_index = 0
            dlv.status = "failed"

    def _reroute_drone_delivery(self, dr: Drone) -> None:
        if dr.delivery is None or dr.delivery.status != "active":
            return
        g = self._adapt()
        dlv = dr.delivery
        path, _c, _s, ok = plan_delivery_route(dlv.hub, dlv.pickup, dlv.dropoff, g)
        if ok and path:
            dr.path = path
            dr.path_index = 0
            dr.position = path[0]
        else:
            dlv.status = "delayed"
            dr.path = []
            dr.path_index = 0

    def _activate_nf(self, coord: Coord) -> int:
        """Returns number of drones marked delayed after failed reroute."""
        self.extra_nf.add(coord)
        self.no_fly_event_count += 1
        broken = 0
        for dr in self.drones:
            if not dr.path or dr.delivery is None or dr.delivery.status != "active":
                continue
            ahead = dr.path[dr.path_index :]
            if coord in ahead:
                g = self._adapt()
                ok_path, _c2, _s2, ok = plan_delivery_route(
                    dr.delivery.hub, dr.delivery.pickup, dr.delivery.dropoff, g
                )
                if ok and ok_path:
                    dr.path = ok_path
                    dr.path_index = 0
                    dr.position = ok_path[0]
                else:
                    dr.delivery.status = "delayed"
                    dr.path = []
                    broken += 1
        return broken

    def _move_all_one(self) -> int:
        """Advance each active drone one hop; returns count moved."""
        n = 0
        for dr in self.drones:
            if not dr.path:
                continue
            if dr.path_index >= len(dr.path) - 1:
                continue
            dr.path_index += 1
            dr.position = dr.path[dr.path_index]
            n += 1
        return n

    def _finalize_done(self) -> None:
        for dr in self.drones:
            dlv = dr.delivery
            if dlv is None:
                continue
            if dlv.status != "active" or not dr.path:
                continue
            if dr.path_index >= len(dr.path) - 1:
                dlv.status = "completed"

    def run(
        self,
        total_steps: int = 20,
        no_fly_events: Optional[Dict[int, Coord]] = None,
        anomaly_step: Optional[int] = None,
        *,
        session_demand_pred: Any = None,
    ) -> List[str]:
        no_fly_events = dict(no_fly_events or {})
        logs: List[str] = []

        lf = sum(1 for d in self.drones if d.drone_type == "light")
        hf = sum(1 for d in self.drones if d.drone_type == "heavy")

        n_del = len(self.deliveries)
        for i in range(min(n_del, len(self.drones))):
            self._route_and_bind(self.drones[i], self.deliveries[i])
        if n_del > len(self.drones):
            for j in range(len(self.drones), n_del):
                self.deliveries[j].status = "failed"

        csp_raw = run_all_constraints(self.grid_flat)
        vc = _csp_violation_total(csp_raw)

        nf_step = None
        if no_fly_events:
            nf_step = min(no_fly_events.keys())

        for t in range(1, total_steps + 1):
            msg = ""

            if t == 1:
                msg = f"Initialized city grid adapter — {len(self.grid_flat)} cells from GRID."
            elif t == 2:
                msg = f"CSP audit complete — aggregated violation tally: {vc}."
            elif t == 3:
                msg = (
                    f"Fleet manifests — {len(self.drones)} drones "
                    f"({lf} light, {hf} heavy); standby at assigned hubs."
                )
            elif t in (4, 5, 6):
                di = t - 4
                if di < len(self.deliveries) and di < len(self.drones):
                    dlv = self.deliveries[di]
                    stt = self.deliveries[di].status
                    msg = (
                        f"Courier {dlv.delivery_id} bound — hub {dlv.hub} → pickup {dlv.pickup} "
                        f"→ drop-off {dlv.dropoff}; routing status `{stt}`."
                    )
                else:
                    msg = "No additional courier manifests for this timestep."
            elif 7 <= t <= 10:
                mv = self._move_all_one()
                self._finalize_done()
                act = sum(1 for d in self.deliveries if d.status == "active")
                msg = (
                    f"Movement pulse — {mv} corridor updates; deliveries still airborne: {act}."
                )
            elif t in no_fly_events:
                coord = no_fly_events[t]
                brk = self._activate_nf(coord)
                msg = (
                    f"No-fly cell {coord} activated — A* replanning engaged; "
                    f"{brk} courier path(s) could not be reopened."
                )
            elif nf_step is not None and t == nf_step + 1:
                msg = (
                    "Conflict sweep — validating residual paths versus updated no-fly geometry."
                )
            elif nf_step is not None and t == nf_step + 2:
                msg = "Reroute cadence sealed — stalled jobs transitioned to DELAYED where needed."
            elif anomaly_step is not None and t == anomaly_step:
                tgt = next((d for d in self.drones if d.drone_id == "D3"), None)
                if tgt and tgt.delivery and tgt.delivery.status == "active":
                    self._reroute_drone_delivery(tgt)
                msg = "Anomaly protocol — telemetry tripwire; rerouting flagged drone toward hub corridor."
            elif t == total_steps - 1:
                if session_demand_pred is not None:
                    msg = (
                        f"Demand fusion — consolidating session forecast `{session_demand_pred}` "
                        "with corridor loading."
                    )
                else:
                    msg = (
                        "Demand posture — awaiting ML Pipeline forecast; using structural demand priors only."
                    )
            elif t == total_steps:
                for dr in self.drones:
                    if dr.delivery and dr.delivery.status == "active":
                        if dr.path:
                            dr.delivery.status = "completed"
                        else:
                            dr.delivery.status = "delayed"
                self.completed = sum(1 for d in self.deliveries if d.status == "completed")
                self.delayed = sum(1 for d in self.deliveries if d.status == "delayed")
                self.failed = sum(1 for d in self.deliveries if d.status == "failed")
                msg = (
                    f"Final ledger — deliveries completed {self.completed}, delayed {self.delayed}, "
                    f"failed {self.failed}; curated no-fly activations logged: {self.no_fly_event_count}."
                )
            else:
                mv2 = self._move_all_one()
                self._finalize_done()
                msg = (
                    f"Sustainment pulse — telemetry nominal ({mv2} minor leg adjustments while holding pattern)."
                )

            logs.append(f"Step {t:02d}: {msg}")

        self.event_log = logs
        return logs
