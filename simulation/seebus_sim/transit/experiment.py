from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from seebus_sim.transit.config import TransitConfig
from seebus_sim.transit.metrics import wait_summary
from seebus_sim.transit.policies import SchedulingPolicy, StaticPolicy
from seebus_sim.transit.sensors import NoisyOccupancySensor, SensorConfig
from seebus_sim.transit.simulation import (
    PredictionProvider,
    SensorProvider,
    simulate_day,
)
from seebus_sim.transit.timetable import build_static_dispatch_timetable


PolicyFactory = Callable[[], SchedulingPolicy]


@dataclass
class TransitExperimentResult:
    config: TransitConfig
    policy_name: str
    timetable: pd.DataFrame
    daily_metrics: pd.DataFrame
    station_metrics: pd.DataFrame
    route_metrics: pd.DataFrame
    bus_metrics: pd.DataFrame
    boarding_events: pd.DataFrame
    alighting_events: pd.DataFrame
    stop_events: pd.DataFrame
    dispatch_events: pd.DataFrame
    summary: dict


def _concat(frames: list[pd.DataFrame]) -> pd.DataFrame:
    nonempty = [frame for frame in frames if not frame.empty]
    return pd.concat(nonempty, ignore_index=True) if nonempty else pd.DataFrame()


def run_transit_experiment(
    benchmark_demand: pd.DataFrame,
    config: TransitConfig,
    *,
    policy_factory: PolicyFactory = StaticPolicy,
    seed: int = 2026,
    prediction_provider: PredictionProvider | None = None,
    sensor_provider: SensorProvider | None = None,
    sensor_config: SensorConfig | None = None,
    sensor_seed: int = 31415,
) -> TransitExperimentResult:
    """Replay every benchmark day with a fresh policy instance per day."""

    day_results = []
    for scenario_day in sorted(benchmark_demand["scenario_day"].unique()):
        day_demand = benchmark_demand[
            benchmark_demand["scenario_day"] == scenario_day
        ]
        day_sensor_provider = sensor_provider
        if day_sensor_provider is None and sensor_config is not None:
            day_sensor_provider = NoisyOccupancySensor(
                sensor_config,
                station_ids=config.station_ids,
                scenario_day=int(scenario_day),
                seed=sensor_seed,
            ).read

        day_results.append(
            simulate_day(
                day_demand,
                config,
                policy_factory(),
                seed=seed,
                prediction_provider=prediction_provider,
                sensor_provider=day_sensor_provider,
            )
        )

    daily_metrics = pd.DataFrame([result.daily_metrics for result in day_results])
    station_metrics = _concat([result.station_metrics for result in day_results])
    route_metrics = _concat([result.route_metrics for result in day_results])
    bus_metrics = _concat([result.bus_metrics for result in day_results])
    boarding_events = _concat([result.boarding_events for result in day_results])
    alighting_events = _concat([result.alighting_events for result in day_results])
    stop_events = _concat([result.stop_events for result in day_results])
    dispatch_events = _concat([result.dispatch_events for result in day_results])

    policy_names = set(daily_metrics["policy_name"].unique())
    if len(policy_names) != 1:
        raise AssertionError(f"experiment mixed policy names: {policy_names}")
    policy_name = str(next(iter(policy_names)))

    total_generated = int(daily_metrics["generated_passengers"].sum())
    total_boarded = int(daily_metrics["boarded_passengers"].sum())
    total_completed = int(daily_metrics["completed_passengers"].sum())
    total_waiting = int(daily_metrics["waiting_at_end"].sum())
    total_onboard = int(daily_metrics["onboard_at_end"].sum())

    waits = wait_summary(boarding_events)
    average_bus_utilization = (
        float(bus_metrics["utilization"].mean()) if not bus_metrics.empty else 0.0
    )
    average_fleet_service_utilization = (
        float(bus_metrics["service_utilization"].mean())
        if not bus_metrics.empty
        else 0.0
    )
    average_queue = (
        float(station_metrics["average_queue"].mean())
        if not station_metrics.empty
        else 0.0
    )

    summary = {
        "policy_name": policy_name,
        "benchmark_days": int(daily_metrics["scenario_day"].nunique()),
        "generated_passengers": total_generated,
        "boarded_passengers": total_boarded,
        "completed_passengers": total_completed,
        "waiting_at_day_end": total_waiting,
        "onboard_at_day_end": total_onboard,
        "service_rate": total_boarded / total_generated if total_generated else 1.0,
        "dispatches": int(daily_metrics["dispatches"].sum()),
        **waits,
        "average_queue": average_queue,
        "max_queue": int(station_metrics["max_queue"].max()) if not station_metrics.empty else 0,
        "average_bus_utilization": average_bus_utilization,
        "average_fleet_service_utilization": average_fleet_service_utilization,
    }

    return TransitExperimentResult(
        config=config,
        policy_name=policy_name,
        timetable=build_static_dispatch_timetable(config),
        daily_metrics=daily_metrics,
        station_metrics=station_metrics,
        route_metrics=route_metrics,
        bus_metrics=bus_metrics,
        boarding_events=boarding_events,
        alighting_events=alighting_events,
        stop_events=stop_events,
        dispatch_events=dispatch_events,
        summary=summary,
    )


def run_static_transit_experiment(
    benchmark_demand: pd.DataFrame,
    config: TransitConfig,
    *,
    seed: int = 2026,
) -> TransitExperimentResult:
    return run_transit_experiment(
        benchmark_demand,
        config,
        policy_factory=StaticPolicy,
        seed=seed,
    )
