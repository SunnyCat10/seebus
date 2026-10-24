from seebus_sim.transit.policies.base import (
    DispatchDecision,
    PolicyContext,
    SchedulingPolicy,
)


class StaticPolicy(SchedulingPolicy):
    """
    Control policy: round-robin fixed dispatch timetable.

    One route is due every ``static_dispatch_interval_minutes``. Returning None
    between slots is how the policy chooses *when* not to send a bus.
    """

    def __init__(self) -> None:
        self._next_dispatch_time: float | None = None
        self._next_route_index = 0

    @property
    def name(self) -> str:
        return "static"

    def decide_dispatch(self, context: PolicyContext) -> DispatchDecision | None:
        if self._next_dispatch_time is None:
            self._next_dispatch_time = context.service_start

        if context.now + 1e-9 < self._next_dispatch_time:
            return None

        # Advance past infeasible end-of-day slots rather than requesting a
        # route that cannot return to the hub before service end.
        attempts = 0
        while attempts < max(1, len(context.routes) * 2):
            route = context.routes[self._next_route_index % len(context.routes)]
            self._next_route_index += 1
            self._next_dispatch_time += context.static_dispatch_interval_minutes
            attempts += 1

            if route.can_complete_before_service_end:
                return DispatchDecision(
                    route_id=route.route_id,
                    reason="fixed round-robin timetable",
                )

        return None
