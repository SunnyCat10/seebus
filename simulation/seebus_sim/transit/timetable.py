from dataclasses import dataclass

import pandas as pd

from seebus_sim.transit.config import TransitConfig


@dataclass(frozen=True)
class ScheduledStop:
    bus_id: str
    station_id: str
    arrival_time: float
    sequence: int


def build_loop_timetable(config: TransitConfig) -> pd.DataFrame:
    """
    Build an evenly-spaced fixed timetable for a one-way circular route.

    Buses are phased around the loop before the simulated day begins, which
    avoids placing every bus at the first station at midnight. We only emit
    stops that occur inside the configured service window.
    """

    rows: list[dict] = []
    loop_minutes = config.loop_minutes
    headway = config.scheduled_headway

    for bus_index in range(config.bus_count):
        bus_id = f"bus-{bus_index + 1}"
        phase = bus_index * headway

        # The previous pass through route[0] may be before service_start. This
        # lets a bus's first in-window stop naturally be B/C/D rather than A.
        first_route_start = config.service_start + phase - loop_minutes
        sequence = 0

        while True:
            station_index = sequence % len(config.route)
            cycle = sequence // len(config.route)
            arrival_time = (
                first_route_start
                + cycle * loop_minutes
                + station_index * config.travel_minutes
            )

            if arrival_time >= config.service_end:
                break

            if arrival_time >= config.service_start:
                rows.append(
                    {
                        "bus_id": bus_id,
                        "station_id": config.route[station_index],
                        "arrival_time": float(arrival_time),
                        "sequence": sequence,
                    }
                )

            sequence += 1

    return (
        pd.DataFrame(rows)
        .sort_values(["arrival_time", "bus_id", "sequence"])
        .reset_index(drop=True)
    )
