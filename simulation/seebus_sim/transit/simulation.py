from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
import simpy

from seebus_sim.transit.config import RouteConfig, TransitConfig
from seebus_sim.transit.metrics import WaitAccumulator
from seebus_sim.transit.models import BusState, PassengerBatch, StationQueue
from seebus_sim.transit.policies import (
    BusObservation,
    DispatchDecision,
    PolicyContext,
    RouteObservation,
    SchedulingPolicy,
    StationObservation,
    StaticPolicy,
)


PredictionProvider = Callable[[str, float], float | None]
SensorProvider = Callable[[str, float, int], float | None]
SensorUpdater = Callable[[str, float, int], float | None]
EventLoggingMode = Literal["full", "compact"]


@dataclass
class TransitDayResult:
    scenario_day: int
    weekday: str
    policy_name: str
    daily_metrics: dict
    station_metrics: pd.DataFrame
    route_metrics: pd.DataFrame
    bus_metrics: pd.DataFrame
    boarding_events: pd.DataFrame
    alighting_events: pd.DataFrame
    stop_events: pd.DataFrame
    dispatch_events: pd.DataFrame
    wait_histogram: dict[float, int]


def _destination_options(
    config: TransitConfig,
    station_id: str,
) -> tuple[list[str], np.ndarray]:
    """Downstream stations on the same route, followed by the shared hub."""
    route = config.route_for_station(station_id)
    origin_index = route.stations.index(station_id)
    destination_ids = list(route.stations[origin_index + 1 :]) + [config.hub_id]
    distances = np.arange(1, len(destination_ids) + 1, dtype=float)
    weights = np.exp(-config.destination_decay * (distances - 1.0))
    return destination_ids, weights / weights.sum()


def _make_station_rngs(
    config: TransitConfig,
    scenario_day: int,
    seed: int,
) -> dict[str, np.random.Generator]:
    return {
        station_id: np.random.default_rng(
            np.random.SeedSequence([seed, scenario_day, station_index])
        )
        for station_index, station_id in enumerate(config.station_ids)
    }


def simulate_day(
    day_demand: pd.DataFrame,
    config: TransitConfig,
    policy: SchedulingPolicy,
    *,
    seed: int = 2026,
    prediction_provider: PredictionProvider | None = None,
    sensor_provider: SensorProvider | None = None,
    sensor_updater: SensorUpdater | None = None,
    event_logging: EventLoggingMode = "full",
) -> TransitDayResult:
    """
    Replay one benchmark day through the shared-hub route-allocation world.

    Policies may only dispatch idle buses from the common hub. Once dispatched,
    the simulator owns the bus until it visits every station on that route in
    order and returns to the hub. Policies cannot skip stops, switch routes, or
    redirect a bus mid-trip.
    """

    if day_demand.empty:
        raise ValueError("day_demand must not be empty")
    if event_logging not in ("full", "compact"):
        raise ValueError("event_logging must be 'full' or 'compact'")
    full_logging = event_logging == "full"

    scenario_days = day_demand["scenario_day"].unique()
    if len(scenario_days) != 1:
        raise ValueError("day_demand must contain exactly one scenario_day")

    scenario_day = int(scenario_days[0])
    weekday = str(day_demand["weekday"].iloc[0])
    demand_stations = set(day_demand["station_id"].unique())
    unknown_stations = demand_stations - set(config.station_ids)
    if unknown_stations:
        raise ValueError(
            "benchmark demand contains stations outside the transit network: "
            f"{sorted(unknown_stations)}"
        )

    env = simpy.Environment()
    duration = config.service_end - config.service_start
    stations = {
        station_id: StationQueue(station_id) for station_id in config.station_ids
    }
    buses = {
        f"bus-{index + 1}": BusState(
            f"bus-{index + 1}", config.bus_capacity, config.hub_id
        )
        for index in range(config.bus_count)
    }

    # Topology is immutable during a day. Resolve these once instead of
    # repeatedly scanning all routes for every observation/passenger process.
    route_by_station = {
        station_id: config.route_for_station(station_id)
        for station_id in config.station_ids
    }
    destination_options_by_station = {
        station_id: _destination_options(config, station_id)
        for station_id in config.station_ids
    }

    station_rngs = _make_station_rngs(config, scenario_day, seed)
    last_served: dict[str, float | None] = {
        station_id: None for station_id in config.station_ids
    }
    last_dispatch: dict[str, float | None] = {
        route.id: None for route in config.routes
    }

    boarding_rows: list[dict] = []
    alighting_rows: list[dict] = []
    stop_rows: list[dict] = []
    dispatch_rows: list[dict] = []

    # Exact compact wait statistics.  These are always collected, while the
    # heavyweight event dictionaries below are only retained in full mode.
    wait_all = WaitAccumulator()
    wait_by_station = (
        {station_id: WaitAccumulator() for station_id in config.station_ids}
        if full_logging
        else {}
    )
    wait_by_route = (
        {route.id: WaitAccumulator() for route in config.routes}
        if full_logging
        else {}
    )
    dispatch_counts = {route.id: 0 for route in config.routes} if full_logging else {}
    dispatch_count_total = 0

    def passenger_process(station_id: str, station_demand: pd.DataFrame):
        station = stations[station_id]
        rng = station_rngs[station_id]
        destination_ids, destination_probabilities = (
            destination_options_by_station[station_id]
        )

        # Demand generated by SeeBus is already minute-ordered inside each
        # station group. Avoid sorting 35 tiny frames again for every policy/day.
        for row in station_demand.itertuples(index=False):
            count = int(row.arrivals)
            if count <= 0:
                continue

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

    def build_tick_snapshot() -> tuple[
        tuple[StationObservation, ...],
        dict[str, tuple[float | None, float | None, float]],
    ]:
        """Build expensive policy-visible observations once per decision tick.

        Multiple idle buses may ask the policy for a decision at the same
        simulated minute. Historical forecasts and sensor readings are identical
        for all of them, so recomputing all stations/routes per bus is wasted
        work. Dynamic fields (last dispatch, buses already in service) are added
        later for each bus decision.
        """

        observations: list[StationObservation] = []
        for station_id in config.station_ids:
            route = route_by_station[station_id]
            served_at = last_served[station_id]
            predicted_lambda = (
                prediction_provider(station_id, env.now)
                if policy.requires_history and prediction_provider is not None
                else None
            )
            sensor_occupancy = (
                sensor_provider(
                    station_id,
                    env.now,
                    stations[station_id].waiting_count,
                )
                if policy.requires_sensor and sensor_provider is not None
                else None
            )
            observations.append(
                StationObservation(
                    station_id=station_id,
                    route_id=route.id,
                    predicted_lambda=predicted_lambda,
                    sensor_occupancy=sensor_occupancy,
                    last_served_time=served_at,
                    minutes_since_service=(
                        env.now - served_at if served_at is not None else None
                    ),
                )
            )

        station_lookup = {obs.station_id: obs for obs in observations}
        prediction_window = min(
            config.prediction_horizon_minutes,
            max(0.0, config.service_end - env.now),
        )
        route_static: dict[str, tuple[float | None, float | None, float]] = {}

        for route in config.routes:
            predicted_arrivals: float | None = None
            if (
                policy.requires_history
                and prediction_provider is not None
                and prediction_window > 0
            ):
                fast_forecast = getattr(prediction_provider, "predict_arrivals", None)
                if callable(fast_forecast):
                    predicted_arrivals = fast_forecast(
                        route.stations, env.now, prediction_window
                    )
                else:
                    predicted_arrivals = 0.0
                    for station_id in route.stations:
                        offset = 0.0
                        while offset < prediction_window - 1e-9:
                            step = min(1.0, prediction_window - offset)
                            sample_time = env.now + offset + step / 2.0
                            predicted_lambda = prediction_provider(
                                station_id, sample_time
                            )
                            if predicted_lambda is None:
                                predicted_arrivals = None
                                break
                            predicted_arrivals += predicted_lambda * step
                            offset += step
                        if predicted_arrivals is None:
                            break

            sensor_values = [
                station_lookup[station_id].sensor_occupancy
                for station_id in route.stations
            ]
            route_sensor = None
            if sensor_values and all(value is not None for value in sensor_values):
                route_sensor = float(sum(sensor_values) / len(sensor_values))

            route_static[route.id] = (
                predicted_arrivals,
                route_sensor,
                prediction_window,
            )

        return tuple(observations), route_static

    def make_policy_context(
        bus_id: str,
        observations: tuple[StationObservation, ...],
        route_static: dict[str, tuple[float | None, float | None, float]],
        route_in_service: dict[str, int],
        available_count: int,
    ) -> PolicyContext:
        route_observations: list[RouteObservation] = []
        for route in config.routes:
            predicted_arrivals, route_sensor, prediction_window = route_static[route.id]
            dispatched_at = last_dispatch[route.id]
            route_observations.append(
                RouteObservation(
                    route_id=route.id,
                    station_ids=route.stations,
                    trip_minutes=route.trip_minutes,
                    predicted_arrivals_next_horizon=predicted_arrivals,
                    sensor_occupancy=route_sensor,
                    last_dispatch_time=dispatched_at,
                    minutes_since_dispatch=(
                        env.now - dispatched_at if dispatched_at is not None else None
                    ),
                    buses_in_service=route_in_service[route.id],
                    can_complete_before_service_end=(
                        env.now + route.trip_minutes <= config.service_end + 1e-9
                    ),
                    prediction_window_minutes=prediction_window,
                )
            )

        return PolicyContext(
            now=env.now,
            scenario_day=scenario_day,
            weekday=weekday,
            bus=BusObservation(
                bus_id=bus_id,
                capacity=buses[bus_id].capacity,
                available_bus_count=available_count,
            ),
            stations=observations,
            routes=tuple(route_observations),
            service_start=config.service_start,
            service_end=config.service_end,
            static_dispatch_interval_minutes=config.static_dispatch_interval_minutes,
            prediction_horizon_minutes=config.prediction_horizon_minutes,
        )

    def log_alighting(bus: BusState, route: RouteConfig, station_id: str) -> int:
        alighted = bus.alight(station_id, env.now)
        if full_logging:
            for batch in alighted:
                alighting_rows.append(
                    {
                        "scenario_day": scenario_day,
                        "weekday": weekday,
                        "policy_name": policy.name,
                        "bus_id": bus.bus_id,
                        "route_id": route.id,
                        "station_id": station_id,
                        "destination_id": batch.destination_id,
                        "arrival_time": batch.arrival_time,
                        "boarding_time": batch.boarding_time,
                        "alighting_time": env.now,
                        "ride_minutes": env.now - batch.boarding_time,
                        "count": batch.count,
                    }
                )
        return sum(batch.count for batch in alighted)

    def route_process(bus_id: str, route: RouteConfig, dispatch_time: float):
        bus = buses[bus_id]
        previous_location = config.hub_id
        for stop_index, station_id in enumerate(route.stations):
            yield env.timeout(route.travel_minutes)
            bus.current_location_id = station_id
            station = stations[station_id]
            occupancy_before = bus.occupancy
            alighted_count = log_alighting(bus, route, station_id)

            boarded = station.board(bus.free_capacity, env.now)
            for batch in boarded:
                wait_minutes = env.now - batch.arrival_time
                wait_all.add(wait_minutes, batch.count)
                if full_logging:
                    wait_by_station[station_id].add(wait_minutes, batch.count)
                    wait_by_route[route.id].add(wait_minutes, batch.count)
                    boarding_rows.append(
                        {
                            "scenario_day": scenario_day,
                            "weekday": weekday,
                            "policy_name": policy.name,
                            "bus_id": bus_id,
                            "route_id": route.id,
                            "station_id": station_id,
                            "destination_id": batch.destination_id,
                            "passenger_arrival_time": batch.arrival_time,
                            "boarding_time": env.now,
                            "wait_minutes": wait_minutes,
                            "count": batch.count,
                        }
                    )
            bus.board(boarded, env.now)
            boarded_count = sum(batch.count for batch in boarded)
            last_served[station_id] = env.now

            if full_logging:
                stop_rows.append(
                    {
                        "scenario_day": scenario_day,
                        "weekday": weekday,
                        "policy_name": policy.name,
                        "bus_id": bus_id,
                        "route_id": route.id,
                        "stop_index": stop_index,
                        "previous_location_id": previous_location,
                        "station_id": station_id,
                        "actual_time": env.now,
                        "dispatch_time": dispatch_time,
                        "minutes_since_dispatch": env.now - dispatch_time,
                        "occupancy_before": occupancy_before,
                        "alighted": alighted_count,
                        "boarded": boarded_count,
                        "occupancy_after": bus.occupancy,
                        "queue_after": station.waiting_count,
                    }
                )
            previous_location = station_id

        # Complete the fixed route and return to the shared hub.
        yield env.timeout(route.travel_minutes)
        bus.current_location_id = config.hub_id
        hub_alighted = log_alighting(bus, route, config.hub_id)
        if bus.occupancy != 0:
            raise AssertionError(
                f"bus {bus_id} returned to hub with {bus.occupancy} passengers"
            )
        bus.finish_route(env.now)

        if full_logging:
            stop_rows.append(
                {
                    "scenario_day": scenario_day,
                    "weekday": weekday,
                    "policy_name": policy.name,
                    "bus_id": bus_id,
                    "route_id": route.id,
                    "stop_index": len(route.stations),
                    "previous_location_id": previous_location,
                    "station_id": config.hub_id,
                    "actual_time": env.now,
                    "dispatch_time": dispatch_time,
                    "minutes_since_dispatch": env.now - dispatch_time,
                    "occupancy_before": hub_alighted,
                    "alighted": hub_alighted,
                    "boarded": 0,
                    "occupancy_after": 0,
                    "queue_after": 0,
                }
            )

    def dispatch_process():
        nonlocal dispatch_count_total
        if config.service_start > 0:
            yield env.timeout(config.service_start)

        while env.now < config.service_end:
            idle_bus_ids = sorted(
                bus_id for bus_id, bus in buses.items() if not bus.in_service
            )
            if idle_bus_ids:
                observations, route_static = build_tick_snapshot()
                route_in_service = {route.id: 0 for route in config.routes}
                for bus in buses.values():
                    if bus.in_service and bus.current_route_id is not None:
                        route_in_service[bus.current_route_id] += 1
                available_count = len(idle_bus_ids)
            else:
                observations = ()
                route_static = {}
                route_in_service = {}
                available_count = 0

            for bus_id in idle_bus_ids:
                context = make_policy_context(
                    bus_id,
                    observations,
                    route_static,
                    route_in_service,
                    available_count,
                )
                decision = policy.decide_dispatch(context)
                if decision is None:
                    continue

                try:
                    route = config.route(decision.route_id)
                except KeyError as exc:
                    raise ValueError(
                        f"policy {policy.name!r} chose unknown route {decision.route_id!r}"
                    ) from exc

                if env.now + route.trip_minutes > config.service_end + 1e-9:
                    raise ValueError(
                        f"policy {policy.name!r} dispatched {route.id!r} at {env.now:.2f}, "
                        "but the route cannot return before service end"
                    )

                # Commit synchronously: later idle-bus decisions in this same
                # tick immediately see the updated fleet/route state.
                bus = buses[bus_id]
                bus.start_route(route.id, env.now)
                last_dispatch[route.id] = env.now
                route_in_service[route.id] += 1
                available_count -= 1
                dispatch_count_total += 1
                if full_logging:
                    dispatch_counts[route.id] += 1
                    dispatch_rows.append(
                        {
                            "scenario_day": scenario_day,
                            "weekday": weekday,
                            "policy_name": policy.name,
                            "bus_id": bus_id,
                            "route_id": route.id,
                            "dispatch_time": env.now,
                            "route_trip_minutes": route.trip_minutes,
                            "expected_return_time": env.now + route.trip_minutes,
                            "policy_reason": decision.reason,
                            "policy_score": decision.score,
                        }
                    )
                env.process(route_process(bus_id, route, env.now))

            next_time = env.now + config.decision_interval_minutes
            if next_time >= config.service_end:
                break
            yield env.timeout(config.decision_interval_minutes)

    def sensor_update_process():
        """Continuously update the backend's cached sensor state.

        Sensor packets are generated independently of whether an idle bus is
        available. This matters for packet-dropout experiments: the server may
        receive useful readings while the entire fleet is busy, and those
        readings should still be available when the next dispatch decision is
        possible.
        """

        if sensor_updater is None:
            return
        if config.service_start > 0:
            yield env.timeout(config.service_start)

        while env.now < config.service_end:
            for station_id in config.station_ids:
                sensor_updater(
                    station_id,
                    env.now,
                    stations[station_id].waiting_count,
                )

            next_time = env.now + config.decision_interval_minutes
            if next_time >= config.service_end:
                break
            yield env.timeout(config.decision_interval_minutes)

    # The generated benchmark is minute-dense for analysis/replay, but the
    # event engine only needs actual arrivals.  Strip zero-arrival rows before
    # creating station processes so a quiet station can jump directly from one
    # real arrival event to the next.
    active_demand = day_demand.loc[day_demand["arrivals"] > 0]
    demand_by_station = {
        str(station_id): frame
        for station_id, frame in active_demand.groupby("station_id", sort=False)
    }
    for station_id, station_demand in demand_by_station.items():
        env.process(passenger_process(station_id, station_demand))
    if sensor_updater is not None:
        # Start the sensor process before dispatch_process so a packet scheduled
        # for a decision minute is visible to that minute's policy decision.
        env.process(sensor_update_process())
    env.process(dispatch_process())

    # Run just beyond the boundary so route-return events scheduled exactly at
    # service_end are processed before end-of-day accounting.
    env.run(until=config.service_end + 1e-6)

    for station in stations.values():
        station.finalize(config.service_end)
    for bus in buses.values():
        bus.finalize(config.service_end)

    boarding_events = pd.DataFrame(boarding_rows) if full_logging else pd.DataFrame()
    alighting_events = pd.DataFrame(alighting_rows) if full_logging else pd.DataFrame()
    stop_events = pd.DataFrame(stop_rows) if full_logging else pd.DataFrame()
    dispatch_events = pd.DataFrame(dispatch_rows) if full_logging else pd.DataFrame()

    wait = wait_all.summary()

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
    route_metric_rows: list[dict] = []
    bus_metric_rows: list[dict] = []

    if full_logging:
        for station_id, station in stations.items():
            station_metric_rows.append(
                {
                    "scenario_day": scenario_day,
                    "weekday": weekday,
                    "policy_name": policy.name,
                    "route_id": route_by_station[station_id].id,
                    "station_id": station_id,
                    "generated_passengers": station.generated_count,
                    "boarded_passengers": station.boarded_count,
                    "waiting_at_end": station.waiting_count,
                    "average_queue": station.average_queue(duration),
                    "max_queue": station.max_queue,
                    **wait_by_station[station_id].summary(),
                }
            )

        for route in config.routes:
            route_stations = route.stations
            route_metric_rows.append(
                {
                    "scenario_day": scenario_day,
                    "weekday": weekday,
                    "policy_name": policy.name,
                    "route_id": route.id,
                    "dispatches": int(dispatch_counts[route.id]),
                    "generated_passengers": sum(
                        stations[station_id].generated_count for station_id in route_stations
                    ),
                    "boarded_passengers": sum(
                        stations[station_id].boarded_count for station_id in route_stations
                    ),
                    "waiting_at_end": sum(
                        stations[station_id].waiting_count for station_id in route_stations
                    ),
                    "average_queue": float(
                        np.mean(
                            [
                                stations[station_id].average_queue(duration)
                                for station_id in route_stations
                            ]
                        )
                    ),
                    "max_queue": max(
                        stations[station_id].max_queue for station_id in route_stations
                    ),
                    **wait_by_route[route.id].summary(),
                }
            )

        for bus_id, bus in buses.items():
            bus_metric_rows.append(
                {
                    "scenario_day": scenario_day,
                    "weekday": weekday,
                    "policy_name": policy.name,
                    "bus_id": bus_id,
                    "capacity": bus.capacity,
                    "trips_completed": bus.trips_completed,
                    "boarded_passengers": bus.boarded_count,
                    "completed_passengers": bus.completed_count,
                    "onboard_at_end": bus.occupancy,
                    "max_occupancy": bus.max_occupancy,
                    "utilization": bus.utilization(duration),
                    "service_utilization": bus.service_utilization(duration),
                }
            )

    average_queue = float(
        np.mean([station.average_queue(duration) for station in stations.values()])
    )
    max_queue = max(station.max_queue for station in stations.values())
    avg_utilization = float(np.mean([bus.utilization(duration) for bus in buses.values()]))
    avg_service_utilization = float(
        np.mean([bus.service_utilization(duration) for bus in buses.values()])
    )

    daily_metrics = {
        "scenario_day": scenario_day,
        "weekday": weekday,
        "policy_name": policy.name,
        "generated_passengers": generated,
        "boarded_passengers": boarded,
        "completed_passengers": completed,
        "waiting_at_end": waiting_end,
        "onboard_at_end": onboard_end,
        "service_rate": boarded / generated if generated else 1.0,
        "dispatches": dispatch_count_total,
        **wait,
        "average_queue": average_queue,
        "max_queue": max_queue,
        "average_bus_utilization": avg_utilization,
        "average_fleet_service_utilization": avg_service_utilization,
    }

    return TransitDayResult(
        scenario_day=scenario_day,
        weekday=weekday,
        policy_name=policy.name,
        daily_metrics=daily_metrics,
        station_metrics=pd.DataFrame(station_metric_rows),
        route_metrics=pd.DataFrame(route_metric_rows),
        bus_metrics=pd.DataFrame(bus_metric_rows),
        boarding_events=boarding_events,
        alighting_events=alighting_events,
        stop_events=stop_events,
        dispatch_events=dispatch_events,
        wait_histogram=wait_all.to_dict(),
    )


def simulate_static_day(
    day_demand: pd.DataFrame,
    config: TransitConfig,
    *,
    seed: int = 2026,
    event_logging: EventLoggingMode = "full",
) -> TransitDayResult:
    return simulate_day(
        day_demand,
        config,
        StaticPolicy(),
        seed=seed,
        event_logging=event_logging,
    )
