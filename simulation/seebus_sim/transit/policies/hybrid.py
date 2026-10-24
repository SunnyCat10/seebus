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
class HybridPolicyConfig:
    """Weights and thresholds for historical + live-sensor dispatching."""

    historical_weight: float = 0.40
    sensor_weight: float = 0.60
    target_load_fraction: float = 0.35
    target_route_occupancy: float = 0.20
    min_headway_factor: float = 0.50
    max_headway_factor: float = 1.50

    def __post_init__(self) -> None:
        if self.historical_weight < 0 or self.sensor_weight < 0:
            raise ValueError("policy weights must be >= 0")
        if self.historical_weight + self.sensor_weight <= 0:
            raise ValueError("at least one policy weight must be > 0")
        if self.target_load_fraction <= 0:
            raise ValueError("target_load_fraction must be > 0")
        if not 0 < self.target_route_occupancy <= 1:
            raise ValueError("target_route_occupancy must be in (0, 1]")
        if self.min_headway_factor < 0:
            raise ValueError("min_headway_factor must be >= 0")
        if self.max_headway_factor <= 0:
            raise ValueError("max_headway_factor must be > 0")
        if self.max_headway_factor < self.min_headway_factor:
            raise ValueError("max_headway_factor must be >= min_headway_factor")

    @property
    def normalized_weights(self) -> tuple[float, float]:
        total = self.historical_weight + self.sensor_weight
        return self.historical_weight / total, self.sensor_weight / total


class HybridPolicy(SchedulingPolicy):
    """Combine predictable historical pressure with noisy live occupancy.

    Historical demand can anticipate regular rush hours; sensors can correct the
    plan when the benchmark world deviates from history, including one-off
    events. Both signals are normalized against the same thresholds used by the
    standalone policies before being combined.
    """

    def __init__(self, config: HybridPolicyConfig | None = None) -> None:
        self.config = config or HybridPolicyConfig()

    @property
    def name(self) -> str:
        return "hybrid"

    @property
    def requires_history(self) -> bool:
        return True

    @property
    def requires_sensor(self) -> bool:
        return True

    def _route_candidate(
        self,
        context: PolicyContext,
        route: RouteObservation,
    ) -> tuple[float, float, float, float] | None:
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

        historical_pressure, predicted_backlog = historical_demand_pressure(
            context,
            route,
            elapsed=elapsed,
            target_load_fraction=self.config.target_load_fraction,
        )
        sensor_pressure = (
            route.sensor_occupancy / self.config.target_route_occupancy
            if route.sensor_occupancy is not None
            else 0.0
        )

        history_weight, sensor_weight = self.config.normalized_weights
        # If a sensor reading is unavailable, fall back to the historical signal
        # rather than artificially shrinking the score because of missing data.
        if route.sensor_occupancy is None:
            combined_pressure = historical_pressure
        else:
            combined_pressure = (
                history_weight * historical_pressure
                + sensor_weight * sensor_pressure
            )

        headway_pressure = elapsed / max_headway
        if combined_pressure + 1e-9 < 1.0 and elapsed + 1e-9 < max_headway:
            return None

        score = combined_pressure + 0.25 * headway_pressure
        return score, predicted_backlog, route.sensor_occupancy or 0.0, elapsed

    def decide_dispatch(self, context: PolicyContext) -> DispatchDecision | None:
        candidates: list[tuple[float, str, float, float, float]] = []
        for route in context.routes:
            candidate = self._route_candidate(context, route)
            if candidate is None:
                continue
            score, backlog, occupancy, elapsed = candidate
            candidates.append((score, route.route_id, backlog, occupancy, elapsed))

        if not candidates:
            return None

        score, route_id, backlog, occupancy, elapsed = max(
            candidates,
            key=lambda item: (item[0], item[1]),
        )
        return DispatchDecision(
            route_id=route_id,
            reason=(
                f"hybrid pressure: ~{backlog:.1f} historical passengers, "
                f"{occupancy:.0%} live occupancy, {elapsed:.1f} min headway"
            ),
            score=score,
        )
