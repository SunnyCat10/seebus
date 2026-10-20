from dataclasses import dataclass

import numpy as np
import pandas as pd
import simpy

from seebus_sim.transit.config import TransitConfig
from seebus_sim.transit.metrics import wait_summary
from seebus_sim.transit.models import BusState, PassengerBatch, StationQueue
from seebus_sim.transit.timetable import build_loop_timetable


@dataclass
class TransitDayResult:
    scenario_day: int
    weekday: str
    daily_metrics: dict
    station_metrics: pd.DataFrame
    bus_metrics: pd.DataFrame
    boarding_events: pd.DataFrame
    alighting_events: pd.DataFrame
    stop_events: pd.DataFrame


def _destination_probabilities(config: TransitConfig) -> np.ndarray:
    distances = np.arange(1, len(config.route), dtype=float)
    weights = np.exp(-config.destination_decay * (distances - 1.0))
    return weights / weights.sum()


def _destination_ids(config: TransitConfig, station_id: str) -> list[str]:
    origin_index = config.route.index(station_id)
    return [
        config.route[(origin_index + distance) % len(config.route)]
        for distance in range(1, len(config.route))
    ]


def _make_station_rngs(
    config: TransitConfig,
    scenario_day: int,
    seed: int,
) -> dict[str, np.random.Generator]:
    return {
        station_id: np.random.default_rng(
            np.random.SeedSequence([seed, scenario_day, station_index])
        )
        for station_index, station_id in enumerate(config.route)
    }


def simulate_static_day(
    day_demand: pd.DataFrame,
    config: TransitConfig,
    *,
    seed: int = 2026,
) -> TransitDayResult:
    """
    Replay one benchmark day through a fixed circular bus timetable.

    Demand rows provide passenger counts per station/minute. Passengers are
    deterministically split into downstream destinations from a dedicated
    transit RNG stream, so rerunning another scheduling policy with the same
    seed can use the exact same passenger population.
    """

    if day_demand.empty:
        raise ValueError("day_demand must not be empty")

    scenario_days = day_demand["scenario_day"].unique()
    if len(scenario_days) != 1:
        raise ValueError("day_demand must contain exactly one scenario_day")

    scenario_day = int(scenario_days[0])
    weekday = str(day_demand["weekday"].iloc[0])
    demand_stations = set(day_demand["station_id"].unique())
    if demand_stations != set(config.route):
        raise ValueError("transit route must contain exactly the benchmark stations")

    env = simpy.Environment()
    duration = config.service_end - config.service_start
    stations = {station_id: StationQueue(station_id) for station_id in config.route}
    buses = {
        f"bus-{index + 1}": BusState(f"bus-{index + 1}", config.bus_capacity)
        for index in range(config.bus_count)
    }

    station_rngs = _make_station_rngs(config, scenario_day, seed)
    destination_probabilities = _destination_probabilities(config)

    boarding_rows: list[dict] = []
    alighting_rows: list[dict] = []
    stop_rows: list[dict] = []

    timetable = build_loop_timetable(config)

    def passenger_process(station_id: str, station_demand: pd.DataFrame):
        station = stations[station_id]
        rng = station_rngs[station_id]
        destination_ids = _destination_ids(config, station_id)

        for row in station_demand.sort_values("minute").itertuples(index=False):
            count = int(row.arrivals)
            if count <= 0:
                continue

            # Benchmark rows represent a minute bucket. Put those passengers at
            # the bucket midpoint so simultaneous bus/arrival ordering is
            # explicit and deterministic.
            arrival_time = float(row.minute) + 0.5
            if arrival_time < config.service_start or arrival_time >= config.service_end:
                continue

            delay = arrival_time - env.now
            if delay > 0:
                yield env.timeout(delay)

            split = rng.multinomial(count, destination_probabilities)
            batches = [
                PassengerBatch(arrival_time, destination_id, int(destination_count))
                for destination_id, destination_count in zip(destination_ids, split)
                if destination_count > 0
            ]
            rng.shuffle(batches)

            for batch in batches:
                station.add(batch, env.now)

    def bus_process(bus_id: str, bus_schedule: pd.DataFrame):
        bus = buses[bus_id]

        for stop in bus_schedule.sort_values("arrival_time").itertuples(index=False):
            delay = float(stop.arrival_time) - env.now
            if delay > 0:
                yield env.timeout(delay)

            station = stations[stop.station_id]
            occupancy_before = bus.occupancy

            alighted = bus.alight(stop.station_id, env.now)
            alighted_count = sum(batch.count for batch in alighted)
            for batch in alighted:
                alighting_rows.append(
                    {
                        "scenario_day": scenario_day,
                        "weekday": weekday,
                        "bus_id": bus_id,
                        "station_id": stop.station_id,
                        "destination_id": batch.destination_id,
                        "arrival_time": batch.arrival_time,
                        "boarding_time": batch.boarding_time,
                        "alighting_time": env.now,
                        "ride_minutes": env.now - batch.boarding_time,
                        "count": batch.count,
                    }
                )

            boarded = station.board(bus.free_capacity, env.now)
            for batch in boarded:
                boarding_rows.append(
                    {
                        "scenario_day": scenario_day,
                        "weekday": weekday,
                        "bus_id": bus_id,
                        "station_id": stop.station_id,
                        "destination_id": batch.destination_id,
                        "passenger_arrival_time": batch.arrival_time,
                        "boarding_time": env.now,
                        "wait_minutes": env.now - batch.arrival_time,
                        "count": batch.count,
                    }
                )
            bus.board(boarded, env.now)
            boarded_count = sum(batch.count for batch in boarded)

            stop_rows.append(
                {
                    "scenario_day": scenario_day,
                    "weekday": weekday,
                    "bus_id": bus_id,
                    "station_id": stop.station_id,
                    "scheduled_time": float(stop.arrival_time),
                    "actual_time": env.now,
                    "occupancy_before": occupancy_before,
                    "alighted": alighted_count,
                    "boarded": boarded_count,
                    "occupancy_after": bus.occupancy,
                    "queue_after": station.waiting_count,
                }
            )

    # Passenger processes are registered first. Mid-minute arrival times remove
    # ambiguity at integer timetable times regardless of process ordering.
    for station_id in config.route:
        station_demand = day_demand[day_demand["station_id"] == station_id]
        env.process(passenger_process(station_id, station_demand))

    for bus_id in buses:
        bus_schedule = timetable[timetable["bus_id"] == bus_id]
        env.process(bus_process(bus_id, bus_schedule))

    env.run(until=config.service_end)

    for station in stations.values():
        station.finalize(config.service_end)
    for bus in buses.values():
        bus.finalize(config.service_end)

    boarding_events = pd.DataFrame(boarding_rows)
    alighting_events = pd.DataFrame(alighting_rows)
    stop_events = pd.DataFrame(stop_rows)

    wait = wait_summary(boarding_events)
    generated = int(day_demand["arrivals"].sum())
    waiting_end = sum(station.waiting_count for station in stations.values())
    onboard_end = sum(bus.occupancy for bus in buses.values())
    completed = sum(bus.completed_count for bus in buses.values())
    boarded = sum(bus.boarded_count for bus in buses.values())

    if generated != waiting_end + onboard_end + completed:
        raise AssertionError(
            "passenger conservation failed: "
            f"generated={generated}, waiting={waiting_end}, "
            f"onboard={onboard_end}, completed={completed}"
        )

    station_metric_rows: list[dict] = []
    for station_id, station in stations.items():
        station_boarding = (
            boarding_events[boarding_events["station_id"] == station_id]
            if not boarding_events.empty
            else boarding_events
        )
        station_wait = wait_summary(station_boarding)
        station_metric_rows.append(
            {
                "scenario_day": scenario_day,
                "weekday": weekday,
                "station_id": station_id,
                "generated_passengers": station.generated_count,
                "boarded_passengers": station.boarded_count,
                "waiting_at_end": station.waiting_count,
                "average_queue": station.average_queue(duration),
                "max_queue": station.max_queue,
                **station_wait,
            }
        )

    bus_metric_rows: list[dict] = []
    for bus_id, bus in buses.items():
        bus_metric_rows.append(
            {
                "scenario_day": scenario_day,
                "weekday": weekday,
                "bus_id": bus_id,
                "capacity": bus.capacity,
                "boarded_passengers": bus.boarded_count,
                "completed_passengers": bus.completed_count,
                "onboard_at_end": bus.occupancy,
                "max_occupancy": bus.max_occupancy,
                "utilization": bus.utilization(duration),
            }
        )

    average_queue = float(
        np.mean([station.average_queue(duration) for station in stations.values()])
    )
    max_queue = max(station.max_queue for station in stations.values())
    avg_utilization = float(
        np.mean([bus.utilization(duration) for bus in buses.values()])
    )

    daily_metrics = {
        "scenario_day": scenario_day,
        "weekday": weekday,
        "generated_passengers": generated,
        "boarded_passengers": boarded,
        "completed_passengers": completed,
        "waiting_at_end": waiting_end,
        "onboard_at_end": onboard_end,
        "service_rate": boarded / generated if generated else 1.0,
        **wait,
        "average_queue": average_queue,
        "max_queue": max_queue,
        "average_bus_utilization": avg_utilization,
    }

    return TransitDayResult(
        scenario_day=scenario_day,
        weekday=weekday,
        daily_metrics=daily_metrics,
        station_metrics=pd.DataFrame(station_metric_rows),
        bus_metrics=pd.DataFrame(bus_metric_rows),
        boarding_events=boarding_events,
        alighting_events=alighting_events,
        stop_events=stop_events,
    )
