from dataclasses import dataclass

import numpy as np
import pandas as pd

from seebus_sim.demand.generator import PoissonDemandGenerator
from seebus_sim.demand.history import DemandHistory
from seebus_sim.demand.predictors.average import AveragePoissonPredictor
from seebus_sim.demand.profile import (
    GroundTruthDemandProfile,
    generate_ground_truth_profile,
)


@dataclass
class DemandExperimentResult:
    training_days: int
    benchmark_days: int
    bucket_minutes: int
    profile: GroundTruthDemandProfile
    training_demand: pd.DataFrame
    benchmark_demand: pd.DataFrame
    history: pd.DataFrame
    comparison: pd.DataFrame
    convergence: pd.DataFrame
    event_summary: pd.DataFrame
    mean_absolute_error: float


def _empty_demand_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "day",
            "scenario_day",
            "weekday",
            "station_id",
            "station_type",
            "minute",
            "bucket",
            "base_lambda",
            "weekday_factor",
            "daily_factor",
            "event_factor",
            "event_id",
            "true_lambda",
            "arrivals",
        ]
    )


def _generate_days(
    generator: PoissonDemandGenerator,
    start_day: int,
    day_count: int,
) -> pd.DataFrame:
    if day_count <= 0:
        return _empty_demand_frame()

    frames = []
    for offset in range(day_count):
        frames.append(
            generator.generate_day(
                day=start_day + offset,
                scenario_day=offset + 1,
                weekday_index=offset % 7,
            )
        )

    return pd.concat(frames, ignore_index=True)


def _build_history(
    minute_demand: pd.DataFrame,
    bucket_minutes: int,
) -> pd.DataFrame:
    store = DemandHistory(bucket_minutes=bucket_minutes)

    for _, day_frame in minute_demand.groupby("day", sort=True):
        store.add_day(day_frame)

    return store.to_frame()


def _compare_predictor_to_benchmark(
    predictor: AveragePoissonPredictor,
    benchmark_demand: pd.DataFrame,
    bucket_minutes: int,
) -> pd.DataFrame:
    """
    Evaluate the learned stationary station/time model on unseen benchmark days.

    The hidden world can vary by weekday, daily noise, and one-off events, so
    there is intentionally no single fixed 'true lambda' anymore. We compare
    the predictor with each benchmark day's mean hidden lambda for the bucket.
    """

    truth = (
        benchmark_demand
        .groupby(
            [
                "day",
                "scenario_day",
                "weekday",
                "station_id",
                "station_type",
                "bucket",
            ],
            as_index=False,
        )
        .agg(
            true_lambda=("true_lambda", "mean"),
            actual_arrivals=("arrivals", "sum"),
            event_factor=("event_factor", "max"),
        )
    )
    truth["minute_of_day"] = truth["bucket"] * bucket_minutes
    truth["observed_lambda"] = truth["actual_arrivals"] / bucket_minutes
    truth["predicted_lambda"] = [
        predictor.predict_lambda(row.station_id, int(row.bucket))
        for row in truth.itertuples(index=False)
    ]
    truth["abs_error"] = (
        truth["true_lambda"] - truth["predicted_lambda"]
    ).abs()
    truth["abs_observation_error"] = (
        truth["observed_lambda"] - truth["predicted_lambda"]
    ).abs()

    return truth


def _convergence_points(training_days: int) -> list[int]:
    preferred = [1, 2, 3, 5, 7, 10, 14, 21, 30]
    points = [day for day in preferred if day <= training_days]
    if training_days > 0 and training_days not in points:
        points.append(training_days)
    return sorted(set(points))


def _extract_event_summary(demand: pd.DataFrame, split: str) -> pd.DataFrame:
    active = demand[demand["event_id"] != ""].copy()
    if active.empty:
        return pd.DataFrame(
            columns=[
                "split",
                "event_id",
                "day",
                "scenario_day",
                "weekday",
                "station_id",
                "station_type",
                "start_minute",
                "end_minute",
                "duration_minutes",
                "event_multiplier",
            ]
        )

    summary = (
        active.groupby(
            [
                "event_id",
                "day",
                "scenario_day",
                "weekday",
                "station_id",
                "station_type",
            ],
            as_index=False,
        )
        .agg(
            start_minute=("minute", "min"),
            last_active_minute=("minute", "max"),
            event_multiplier=("event_factor", "max"),
        )
    )
    summary["end_minute"] = summary["last_active_minute"] + 1
    summary["duration_minutes"] = summary["end_minute"] - summary["start_minute"]
    summary.insert(0, "split", split)
    return summary.drop(columns=["last_active_minute"])


def run_demand_experiment(
    station_ids: list[str],
    training_days: int = 14,
    benchmark_days: int = 30,
    bucket_minutes: int = 15,
    seed: int = 42,
    daily_noise_std: float = 0.12,
    event_probability: float = 0.07,
) -> DemandExperimentResult:
    """
    Create a richer hidden world, learn a deliberately simpler model from
    training observations, and evaluate it on a fixed replayable benchmark.

    Hidden world:
      - station-specific time-of-day profile / rush hours
      - station archetype and weekday/weekend behavior
      - random day-to-day multiplicative variation
      - rare one-off demand events
      - Poisson passenger arrivals conditioned on the resulting true lambda

    Learner:
      - still only estimates one lambda per station/time bucket
      - it does not know weekday, station archetype, daily factor, or events

    Separate RNG streams keep the benchmark world unchanged when training
    length changes.
    """

    if training_days < 1:
        raise ValueError("training_days must be >= 1")
    if benchmark_days < 1:
        raise ValueError("benchmark_days must be >= 1")
    if (24 * 60) % bucket_minutes != 0:
        raise ValueError("bucket_minutes must evenly divide one day")
    if not (0.0 <= event_probability <= 1.0):
        raise ValueError("event_probability must be between 0 and 1")

    seed_sequence = np.random.SeedSequence(seed)
    profile_seed, training_seed, benchmark_seed = seed_sequence.spawn(3)

    profile = generate_ground_truth_profile(
        station_ids=station_ids,
        bucket_minutes=bucket_minutes,
        rng=np.random.default_rng(profile_seed),
    )

    generator_options = {
        "daily_noise_std": daily_noise_std,
        "event_probability": event_probability,
    }

    training_generator = PoissonDemandGenerator(
        profile=profile,
        rng=np.random.default_rng(training_seed),
        **generator_options,
    )
    benchmark_generator = PoissonDemandGenerator(
        profile=profile,
        rng=np.random.default_rng(benchmark_seed),
        **generator_options,
    )

    training_demand = _generate_days(
        training_generator,
        start_day=1,
        day_count=training_days,
    )
    benchmark_demand = _generate_days(
        benchmark_generator,
        start_day=training_days + 1,
        day_count=benchmark_days,
    )

    history = _build_history(training_demand, bucket_minutes=bucket_minutes)

    predictor = AveragePoissonPredictor()
    predictor.fit(history)

    comparison = _compare_predictor_to_benchmark(
        predictor=predictor,
        benchmark_demand=benchmark_demand,
        bucket_minutes=bucket_minutes,
    )

    convergence_rows: list[dict] = []
    for days in _convergence_points(training_days):
        prefix = training_demand[training_demand["scenario_day"] <= days]
        prefix_history = _build_history(prefix, bucket_minutes=bucket_minutes)

        prefix_predictor = AveragePoissonPredictor()
        prefix_predictor.fit(prefix_history)

        prefix_comparison = _compare_predictor_to_benchmark(
            predictor=prefix_predictor,
            benchmark_demand=benchmark_demand,
            bucket_minutes=bucket_minutes,
        )

        errors = prefix_comparison["true_lambda"] - prefix_comparison["predicted_lambda"]
        convergence_rows.append(
            {
                "training_days": days,
                "mean_absolute_error": float(errors.abs().mean()),
                "root_mean_squared_error": float(np.sqrt((errors ** 2).mean())),
            }
        )

    convergence = pd.DataFrame(convergence_rows)

    event_frames = [
        frame
        for frame in (
            _extract_event_summary(training_demand, "training"),
            _extract_event_summary(benchmark_demand, "benchmark"),
        )
        if not frame.empty
    ]
    if event_frames:
        event_summary = pd.concat(event_frames, ignore_index=True)
    else:
        event_summary = _extract_event_summary(training_demand, "training")

    return DemandExperimentResult(
        training_days=training_days,
        benchmark_days=benchmark_days,
        bucket_minutes=bucket_minutes,
        profile=profile,
        training_demand=training_demand,
        benchmark_demand=benchmark_demand,
        history=history,
        comparison=comparison,
        convergence=convergence,
        event_summary=event_summary,
        mean_absolute_error=float(comparison["abs_error"].mean()),
    )


# Kept as a compatibility wrapper for the first starter version.
def run_training_experiment(
    station_ids: list[str],
    training_days: int = 7,
    bucket_minutes: int = 15,
    seed: int = 42,
) -> DemandExperimentResult:
    return run_demand_experiment(
        station_ids=station_ids,
        training_days=training_days,
        benchmark_days=1,
        bucket_minutes=bucket_minutes,
        seed=seed,
    )
