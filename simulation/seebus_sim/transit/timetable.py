from dataclasses import dataclass

import pandas as pd

from seebus_sim.transit.config import TransitConfig


@dataclass(frozen=True)
class ScheduledDispatch:
    route_id: str
    departure_time: float
    sequence: int


def build_static_dispatch_timetable(config: TransitConfig) -> pd.DataFrame:
    """
    Planned round-robin dispatches for the static control policy.

    This table is a reference schedule rather than a bus-specific stop list.
    The shared bus pool supplies whichever idle bus is available when a
    dispatch is due.
    """

    rows: list[dict] = []
    departure_time = config.service_start
    sequence = 0

    while departure_time < config.service_end:
        route = config.routes[sequence % len(config.routes)]
        # Do not plan a trip that cannot return to the hub before service end.
        if departure_time + route.trip_minutes <= config.service_end:
            rows.append(
                {
                    "route_id": route.id,
                    "departure_time": float(departure_time),
                    "sequence": sequence,
                }
            )
        departure_time += config.static_dispatch_interval_minutes
        sequence += 1

    return pd.DataFrame(rows)


# Old name kept as a small compatibility alias for external notebooks/scripts.
def build_loop_timetable(config: TransitConfig) -> pd.DataFrame:
    return build_static_dispatch_timetable(config)
