from dataclasses import dataclass

import pandas as pd

from seebus_sim.transit.config import TransitConfig
from seebus_sim.transit.metrics import wait_summary
from seebus_sim.transit.simulation import simulate_static_day
from seebus_sim.transit.timetable import build_loop_timetable


@dataclass
class TransitExperimentResult:
    config: TransitConfig
    timetable: pd.DataFrame
    daily_metrics: pd.DataFrame
    station_metrics: pd.DataFrame
    bus_metrics: pd.DataFrame
    boarding_events: pd.DataFrame
    alighting_events: pd.DataFrame
    stop_events: pd.DataFrame
    summary: dict


def _concat(frames: list[pd.DataFrame]) -> pd.DataFrame:
    nonempty = [frame for frame in frames if not frame.empty]
    return pd.concat(nonempty, ignore_index=True) if nonempty else pd.DataFrame()


def run_static_transit_experiment(
    benchmark_demand: pd.DataFrame,
    config: TransitConfig,
    *,
    seed: int = 2026,
) -> TransitExperimentResult:
    """Replay every benchmark day through the same fixed timetable."""

    day_results = []
    for scenario_day in sorted(benchmark_demand["scenario_day"].unique()):
        day_demand = benchmark_demand[
            benchmark_demand["scenario_day"] == scenario_day
        ]
        day_results.append(
            simulate_static_day(
                day_demand,
                config,
                seed=seed,
            )
        )

    daily_metrics = pd.DataFrame([result.daily_metrics for result in day_results])
    station_metrics = _concat([result.station_metrics for result in day_results])
    bus_metrics = _concat([result.bus_metrics for result in day_results])
    boarding_events = _concat([result.boarding_events for result in day_results])
    alighting_events = _concat([result.alighting_events for result in day_results])
    stop_events = _concat([result.stop_events for result in day_results])

    total_generated = int(daily_metrics["generated_passengers"].sum())
    total_boarded = int(daily_metrics["boarded_passengers"].sum())
    total_completed = int(daily_metrics["completed_passengers"].sum())
    total_waiting = int(daily_metrics["waiting_at_end"].sum())
    total_onboard = int(daily_metrics["onboard_at_end"].sum())

    waits = wait_summary(boarding_events)

    if bus_metrics.empty:
        average_bus_utilization = 0.0
    else:
        average_bus_utilization = float(bus_metrics["utilization"].mean())

    # Average queue is already time-weighted within each station/day. Equal
    # weighting here gives the mean queue length for a randomly chosen station
    # and benchmark minute.
    average_queue = (
        float(station_metrics["average_queue"].mean())
        if not station_metrics.empty
        else 0.0
    )

    summary = {
        "benchmark_days": int(daily_metrics["scenario_day"].nunique()),
        "generated_passengers": total_generated,
        "boarded_passengers": total_boarded,
        "completed_passengers": total_completed,
        "waiting_at_day_end": total_waiting,
        "onboard_at_day_end": total_onboard,
        "service_rate": total_boarded / total_generated if total_generated else 1.0,
        **waits,
        "average_queue": average_queue,
        "max_queue": int(station_metrics["max_queue"].max()) if not station_metrics.empty else 0,
        "average_bus_utilization": average_bus_utilization,
    }

    return TransitExperimentResult(
        config=config,
        timetable=build_loop_timetable(config),
        daily_metrics=daily_metrics,
        station_metrics=station_metrics,
        bus_metrics=bus_metrics,
        boarding_events=boarding_events,
        alighting_events=alighting_events,
        stop_events=stop_events,
        summary=summary,
    )
