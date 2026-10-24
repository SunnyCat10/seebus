"""Compatibility wrappers. New code should use :mod:`seebus_sim.reporting`."""

from pathlib import Path

import pandas as pd

from seebus_sim.reporting.plots import (
    save_benchmark_variation_plot,
    save_convergence_plot,
    save_daily_wait_plot,
    save_profile_comparison_plot,
    save_station_wait_plot,
)


def save_transit_daily_wait_plot(daily_metrics: pd.DataFrame, path: Path) -> None:
    save_daily_wait_plot(
        daily_metrics,
        path,
        title="Static timetable passenger waiting time",
    )


def save_transit_station_wait_plot(station_metrics: pd.DataFrame, path: Path) -> None:
    save_station_wait_plot(
        station_metrics,
        path,
        title="Static timetable waiting time by station",
    )


__all__ = [
    "save_benchmark_variation_plot",
    "save_convergence_plot",
    "save_profile_comparison_plot",
    "save_transit_daily_wait_plot",
    "save_transit_station_wait_plot",
]
