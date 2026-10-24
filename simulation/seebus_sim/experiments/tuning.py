from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import Iterable
import math

import pandas as pd

from seebus_sim.experiments.suite import BatchResult, PolicySpec
from seebus_sim.transit import (
    HistoricalPolicy,
    HistoricalPolicyConfig,
    HybridPolicy,
    HybridPolicyConfig,
    SensorPolicy,
    StaticPolicy,
)


@dataclass(frozen=True)
class TuningGridDefinition:
    """Focused 2-D policy-tuning study for the default 10-bus regime."""

    target_load_fractions: tuple[float, ...]
    sensor_weights: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.target_load_fractions:
            raise ValueError("at least one historical threshold is required")
        if not self.sensor_weights:
            raise ValueError("at least one hybrid sensor weight is required")
        if any(value <= 0 for value in self.target_load_fractions):
            raise ValueError("historical target-load fractions must be > 0")
        if any(not 0 <= value <= 1 for value in self.sensor_weights):
            raise ValueError("hybrid sensor weights must be between 0 and 1")
        if len(set(self.target_load_fractions)) != len(self.target_load_fractions):
            raise ValueError("historical threshold values must be unique")
        if len(set(self.sensor_weights)) != len(self.sensor_weights):
            raise ValueError("hybrid sensor weights must be unique")


def _fmt(value: float) -> str:
    return f"{float(value):g}"


def historical_policy_label(target_load_fraction: float) -> str:
    return f"Historical[t={_fmt(target_load_fraction)}]"


def hybrid_policy_label(target_load_fraction: float, sensor_weight: float) -> str:
    return (
        f"Hybrid[t={_fmt(target_load_fraction)},w={_fmt(sensor_weight)}]"
    )


def build_tuning_policy_specs(
    definition: TuningGridDefinition,
) -> tuple[list[PolicySpec], pd.DataFrame]:
    """Build all tuning policies so every variant replays the same demand world.

    Historical thresholds are evaluated once each. Hybrid variants then cross
    those thresholds with sensor/history weights. Pure 0/1 endpoints are not
    required for this focused grid because the standalone Historical/Sensor
    policies already act as those sanity-check endpoints.
    """

    specs: list[PolicySpec] = [
        PolicySpec("Static", StaticPolicy),
        PolicySpec("Sensor", SensorPolicy),
    ]
    metadata_rows: list[dict] = [
        {"policy": "Static", "family": "Static", "target_load_fraction": math.nan, "sensor_weight": math.nan},
        {"policy": "Sensor", "family": "Sensor", "target_load_fraction": math.nan, "sensor_weight": 1.0},
    ]

    for threshold in definition.target_load_fractions:
        label = historical_policy_label(threshold)
        specs.append(
            PolicySpec(
                label,
                partial(
                    HistoricalPolicy,
                    HistoricalPolicyConfig(target_load_fraction=float(threshold)),
                ),
            )
        )
        metadata_rows.append(
            {
                "policy": label,
                "family": "Historical",
                "target_load_fraction": float(threshold),
                "sensor_weight": 0.0,
            }
        )

    for threshold in definition.target_load_fractions:
        for sensor_weight in definition.sensor_weights:
            history_weight = 1.0 - float(sensor_weight)
            label = hybrid_policy_label(threshold, sensor_weight)
            specs.append(
                PolicySpec(
                    label,
                    partial(
                        HybridPolicy,
                        HybridPolicyConfig(
                            target_load_fraction=float(threshold),
                            historical_weight=history_weight,
                            sensor_weight=float(sensor_weight),
                        ),
                    ),
                )
            )
            metadata_rows.append(
                {
                    "policy": label,
                    "family": "Hybrid",
                    "target_load_fraction": float(threshold),
                    "sensor_weight": float(sensor_weight),
                }
            )

    return specs, pd.DataFrame(metadata_rows)


def annotate_tuning_runs(
    batch: BatchResult,
    metadata: pd.DataFrame,
) -> pd.DataFrame:
    if batch.comparison.empty:
        return pd.DataFrame()
    return batch.comparison.merge(metadata, on="policy", how="left", validate="many_to_one")


def _mean_ci(values: pd.Series) -> tuple[float, float, float]:
    clean = values.dropna().astype(float)
    if clean.empty:
        return math.nan, math.nan, math.nan
    mean = float(clean.mean())
    if len(clean) == 1:
        return mean, mean, mean
    margin = 1.96 * float(clean.std(ddof=1)) / math.sqrt(len(clean))
    return mean, mean - margin, mean + margin


def build_historical_threshold_summary(tuning_runs: pd.DataFrame) -> pd.DataFrame:
    frame = tuning_runs[tuning_runs["family"] == "Historical"].copy()
    rows: list[dict] = []
    for threshold, group in frame.groupby("target_load_fraction", sort=True):
        mean, low, high = _mean_ci(group["average_wait_minutes"])
        p95_mean, p95_low, p95_high = _mean_ci(group["p95_wait_minutes"])
        rows.append(
            {
                "target_load_fraction": float(threshold),
                "runs": int(group["run"].nunique()),
                "average_wait_minutes_mean": mean,
                "average_wait_minutes_ci95_low": low,
                "average_wait_minutes_ci95_high": high,
                "p95_wait_minutes_mean": p95_mean,
                "p95_wait_minutes_ci95_low": p95_low,
                "p95_wait_minutes_ci95_high": p95_high,
            }
        )
    return pd.DataFrame(rows)


def build_hybrid_grid_summary(tuning_runs: pd.DataFrame) -> pd.DataFrame:
    frame = tuning_runs[tuning_runs["family"] == "Hybrid"].copy()
    if frame.empty:
        return pd.DataFrame()

    historical = tuning_runs[tuning_runs["family"] == "Historical"][
        ["run", "target_load_fraction", "average_wait_minutes"]
    ].rename(columns={"average_wait_minutes": "historical_wait"})
    sensor = tuning_runs[tuning_runs["family"] == "Sensor"][
        ["run", "average_wait_minutes"]
    ].rename(columns={"average_wait_minutes": "sensor_wait"})

    frame = frame.merge(
        historical,
        on=["run", "target_load_fraction"],
        how="left",
        validate="many_to_one",
    ).merge(sensor, on="run", how="left", validate="many_to_one")
    frame["benefit_vs_historical_minutes"] = (
        frame["historical_wait"] - frame["average_wait_minutes"]
    )
    frame["benefit_vs_sensor_minutes"] = (
        frame["sensor_wait"] - frame["average_wait_minutes"]
    )

    rows: list[dict] = []
    for (threshold, weight), group in frame.groupby(
        ["target_load_fraction", "sensor_weight"], sort=True
    ):
        avg_mean, avg_low, avg_high = _mean_ci(group["average_wait_minutes"])
        p95_mean, p95_low, p95_high = _mean_ci(group["p95_wait_minutes"])
        hist_mean, hist_low, hist_high = _mean_ci(
            group["benefit_vs_historical_minutes"]
        )
        sensor_mean, sensor_low, sensor_high = _mean_ci(
            group["benefit_vs_sensor_minutes"]
        )
        rows.append(
            {
                "target_load_fraction": float(threshold),
                "sensor_weight": float(weight),
                "history_weight": 1.0 - float(weight),
                "runs": int(group["run"].nunique()),
                "average_wait_minutes_mean": avg_mean,
                "average_wait_minutes_ci95_low": avg_low,
                "average_wait_minutes_ci95_high": avg_high,
                "p95_wait_minutes_mean": p95_mean,
                "p95_wait_minutes_ci95_low": p95_low,
                "p95_wait_minutes_ci95_high": p95_high,
                "benefit_vs_historical_minutes_mean": hist_mean,
                "benefit_vs_historical_minutes_ci95_low": hist_low,
                "benefit_vs_historical_minutes_ci95_high": hist_high,
                "benefit_vs_sensor_minutes_mean": sensor_mean,
                "benefit_vs_sensor_minutes_ci95_low": sensor_low,
                "benefit_vs_sensor_minutes_ci95_high": sensor_high,
            }
        )
    return pd.DataFrame(rows)
