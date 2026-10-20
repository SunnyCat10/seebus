import math

import numpy as np
import pandas as pd


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
