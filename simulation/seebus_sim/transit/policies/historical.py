from dataclasses import dataclass

from seebus_sim.transit.policies.base import (
    DispatchDecision,
    PolicyContext,
    RouteObservation,
    SchedulingPolicy,
)
from seebus_sim.transit.policies.helpers import (
    elapsed_since_dispatch,
    headway_limits,
    historical_demand_pressure,
)


@dataclass(frozen=True)
class HistoricalPolicyConfig:
    """Tuning knobs for the historical-demand dispatch policy.

    ``target_load_fraction`` controls how much historically predicted demand is
    allowed to accumulate before another bus is dispatched. The threshold is a
    fraction of one bus's capacity.

    Headway limits are expressed relative to the static control's nominal
    per-route headway, keeping the defaults meaningful if the baseline timetable
    changes.
    """

    target_load_fraction: float = 0.35
    min_headway_factor: float = 0.50
    max_headway_factor: float = 1.50

    def __post_init__(self) -> None:
        if self.target_load_fraction <= 0:
            raise ValueError("target_load_fraction must be > 0")
        if self.min_headway_factor < 0:
            raise ValueError("min_headway_factor must be >= 0")
        if self.max_headway_factor <= 0:
            raise ValueError("max_headway_factor must be > 0")
        if self.max_headway_factor < self.min_headway_factor:
            raise ValueError("max_headway_factor must be >= min_headway_factor")


class HistoricalPolicy(SchedulingPolicy):
    """Dispatch buses using only the learned historical demand profile.

    The policy estimates how many passengers are likely to have accumulated on
    each route since its previous dispatch:

        predicted backlog ~= predicted arrival rate * minutes since dispatch

    A route becomes eligible when either:
    - the predicted backlog reaches a configurable fraction of bus capacity, or
    - its maximum allowed headway has been reached.

    The minimum headway prevents sending multiple buses almost on top of each
    other. The maximum headway is a starvation guard for quiet routes.

    No live queue length, hidden lambda, one-off-event flag, or sensor reading is
    used by this policy.
    """

    def __init__(self, config: HistoricalPolicyConfig | None = None) -> None:
        self.config = config or HistoricalPolicyConfig()

    @property
    def name(self) -> str:
        return "historical"

    @property
    def requires_history(self) -> bool:
        return True

    def _route_candidate(
        self,
        context: PolicyContext,
        route: RouteObservation,
    ) -> tuple[float, float, float] | None:
        if not route.can_complete_before_service_end:
            return None

        min_headway, max_headway = headway_limits(
            context,
            self.config.min_headway_factor,
            self.config.max_headway_factor,
        )
        elapsed = elapsed_since_dispatch(route, max_headway)
        if elapsed + 1e-9 < min_headway:
            return None

        demand_pressure, predicted_backlog = historical_demand_pressure(
            context,
            route,
            elapsed=elapsed,
            target_load_fraction=self.config.target_load_fraction,
        )
        headway_pressure = elapsed / max_headway

        if demand_pressure + 1e-9 < 1.0 and elapsed + 1e-9 < max_headway:
            return None

        score = demand_pressure + 0.25 * headway_pressure
        return score, predicted_backlog, elapsed

    def decide_dispatch(self, context: PolicyContext) -> DispatchDecision | None:
        candidates: list[tuple[float, str, float, float]] = []

        for route in context.routes:
            candidate = self._route_candidate(context, route)
            if candidate is None:
                continue
            score, predicted_backlog, elapsed = candidate
            candidates.append(
                (score, route.route_id, predicted_backlog, elapsed)
            )

        if not candidates:
            return None

        # Stable route-id tie-break makes runs deterministic.
        score, route_id, predicted_backlog, elapsed = max(
            candidates,
            key=lambda item: (item[0], item[1]),
        )
        return DispatchDecision(
            route_id=route_id,
            reason=(
                f"historical pressure: ~{predicted_backlog:.1f} predicted "
                f"arrivals since last dispatch ({elapsed:.1f} min)"
            ),
            score=score,
        )
