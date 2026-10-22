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
)


@dataclass(frozen=True)
class SensorPolicyConfig:
    """Tuning knobs for the live-sensor-only dispatch policy.

    ``target_route_occupancy`` is the mean station occupancy at which a route is
    considered pressured enough for a dispatch. Occupancy is normalized to
    0..1 by the sensor model, so 0.20 means an average 20% reading across the
    stations of a route.
    """

    target_route_occupancy: float = 0.20
    min_headway_factor: float = 0.50
    max_headway_factor: float = 1.50

    def __post_init__(self) -> None:
        if not 0 < self.target_route_occupancy <= 1:
            raise ValueError("target_route_occupancy must be in (0, 1]")
        if self.min_headway_factor < 0:
            raise ValueError("min_headway_factor must be >= 0")
        if self.max_headway_factor <= 0:
            raise ValueError("max_headway_factor must be > 0")
        if self.max_headway_factor < self.min_headway_factor:
            raise ValueError("max_headway_factor must be >= min_headway_factor")


class SensorPolicy(SchedulingPolicy):
    """Dispatch using only noisy live station occupancy readings.

    Historical predictions are deliberately ignored. A route becomes eligible
    when its mean sensor occupancy crosses the configured threshold or its
    maximum headway is reached. The maximum-headway guard keeps a quiet route
    from starving if sensors remain low or temporarily unavailable.
    """

    def __init__(self, config: SensorPolicyConfig | None = None) -> None:
        self.config = config or SensorPolicyConfig()

    @property
    def name(self) -> str:
        return "sensor"

    @property
    def requires_sensor(self) -> bool:
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

        headway_pressure = elapsed / max_headway

        # Missing sensors do not cause immediate service; the headway guard is
        # the fallback that guarantees eventual dispatch.
        if route.sensor_occupancy is None:
            if elapsed + 1e-9 < max_headway:
                return None
            return headway_pressure, 0.0, elapsed

        occupancy_pressure = (
            route.sensor_occupancy / self.config.target_route_occupancy
        )
        if occupancy_pressure + 1e-9 < 1.0 and elapsed + 1e-9 < max_headway:
            return None

        score = occupancy_pressure + 0.25 * headway_pressure
        return score, route.sensor_occupancy, elapsed

    def decide_dispatch(self, context: PolicyContext) -> DispatchDecision | None:
        candidates: list[tuple[float, str, float, float]] = []

        for route in context.routes:
            candidate = self._route_candidate(context, route)
            if candidate is None:
                continue
            score, occupancy, elapsed = candidate
            candidates.append((score, route.route_id, occupancy, elapsed))

        if not candidates:
            return None

        score, route_id, occupancy, elapsed = max(
            candidates,
            key=lambda item: (item[0], item[1]),
        )
        return DispatchDecision(
            route_id=route_id,
            reason=(
                f"sensor pressure: route occupancy {occupancy:.0%} "
                f"after {elapsed:.1f} min"
            ),
            score=score,
        )
