from seebus_sim.transit.policies.base import (
    PolicyContext,
    SchedulingPolicy,
    StopDecision,
)


class StaticPolicy(SchedulingPolicy):
    """Control policy: follow the original fixed timetable exactly."""

    @property
    def name(self) -> str:
        return "static"

    def decide_next_stop(self, context: PolicyContext) -> StopDecision:
        return StopDecision(
            station_id=context.planned_stop.station_id,
            target_time=context.planned_stop.arrival_time,
            reason="fixed timetable",
        )
