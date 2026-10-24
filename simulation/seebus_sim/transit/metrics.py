import math
from collections import defaultdict

import numpy as np
import pandas as pd


class WaitAccumulator:
    """Compact exact passenger-weighted wait-time statistics.

    Boarding event logs are useful for debugging, but batch experiments only
    need aggregate wait metrics.  Keeping a count per observed wait value gives
    us exact passenger-weighted mean/median/P95/max without retaining one large
    dictionary row for every boarding batch.
    """

    def __init__(self) -> None:
        self._counts: dict[float, int] = defaultdict(int)
        self.total_count = 0
        self.total_wait = 0.0
        self.max_wait = math.nan

    def add(self, wait_minutes: float, count: int) -> None:
        if count <= 0:
            return
        wait = float(wait_minutes)
        passenger_count = int(count)
        self._counts[wait] += passenger_count
        self.total_count += passenger_count
        self.total_wait += wait * passenger_count
        if math.isnan(self.max_wait) or wait > self.max_wait:
            self.max_wait = wait

    def merge(self, other: "WaitAccumulator") -> None:
        for wait, count in other._counts.items():
            self._counts[wait] += count
        self.total_count += other.total_count
        self.total_wait += other.total_wait
        if not math.isnan(other.max_wait):
            if math.isnan(self.max_wait) or other.max_wait > self.max_wait:
                self.max_wait = other.max_wait

    def to_dict(self) -> dict[float, int]:
        return dict(self._counts)

    @classmethod
    def from_dict(cls, counts: dict[float, int]) -> "WaitAccumulator":
        accumulator = cls()
        for wait, count in counts.items():
            accumulator.add(float(wait), int(count))
        return accumulator

    def _quantile(self, quantile: float) -> float:
        if not 0.0 <= quantile <= 1.0:
            raise ValueError("quantile must be between 0 and 1")
        if self.total_count <= 0:
            return math.nan

        target = quantile * self.total_count
        cumulative = 0
        for wait in sorted(self._counts):
            cumulative += self._counts[wait]
            if cumulative >= target:
                return float(wait)
        return float(max(self._counts))

    def summary(self) -> dict[str, float]:
        if self.total_count <= 0:
            return {
                "average_wait_minutes": math.nan,
                "median_wait_minutes": math.nan,
                "p95_wait_minutes": math.nan,
                "max_wait_minutes": math.nan,
            }
        return {
            "average_wait_minutes": self.total_wait / self.total_count,
            "median_wait_minutes": self._quantile(0.50),
            "p95_wait_minutes": self._quantile(0.95),
            "max_wait_minutes": float(self.max_wait),
        }


def weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    total_weight = float(weights.sum())
    if total_weight <= 0:
        return math.nan
    return float(np.average(values.to_numpy(dtype=float), weights=weights.to_numpy(dtype=float)))


def weighted_quantile(
    values: pd.Series,
    weights: pd.Series,
    quantile: float,
) -> float:
    if not 0.0 <= quantile <= 1.0:
        raise ValueError("quantile must be between 0 and 1")
    if len(values) == 0 or float(weights.sum()) <= 0:
        return math.nan

    order = np.argsort(values.to_numpy(dtype=float), kind="stable")
    sorted_values = values.to_numpy(dtype=float)[order]
    sorted_weights = weights.to_numpy(dtype=float)[order]
    cumulative = np.cumsum(sorted_weights)
    target = quantile * cumulative[-1]
    index = int(np.searchsorted(cumulative, target, side="left"))
    index = min(index, len(sorted_values) - 1)
    return float(sorted_values[index])


def wait_summary(boarding_events: pd.DataFrame) -> dict[str, float]:
    if boarding_events.empty:
        return {
            "average_wait_minutes": math.nan,
            "median_wait_minutes": math.nan,
            "p95_wait_minutes": math.nan,
            "max_wait_minutes": math.nan,
        }

    values = boarding_events["wait_minutes"]
    weights = boarding_events["count"]
    return {
        "average_wait_minutes": weighted_mean(values, weights),
        "median_wait_minutes": weighted_quantile(values, weights, 0.50),
        "p95_wait_minutes": weighted_quantile(values, weights, 0.95),
        "max_wait_minutes": float(values.max()),
    }
