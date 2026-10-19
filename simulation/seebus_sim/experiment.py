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
    mean_absolute_error: float


def _generate_days(
    generator: PoissonDemandGenerator,
    start_day: int,
    day_count: int,
) -> pd.DataFrame:
    if day_count <= 0:
        return pd.DataFrame(
            columns=["day", "station_id", "minute", "bucket", "arrivals"]
        )

    return pd.concat(
        [
            generator.generate_day(day)
            for day in range(start_day, start_day + day_count)
        ],
        ignore_index=True,
    )


def _build_history(
    minute_demand: pd.DataFrame,
    bucket_minutes: int,
) -> pd.DataFrame:
    store = DemandHistory(bucket_minutes=bucket_minutes)

    for _, day_frame in minute_demand.groupby("day", sort=True):
        store.add_day(day_frame)

    return store.to_frame()


def _compare_predictor_to_truth(
    predictor: AveragePoissonPredictor,
    profile: GroundTruthDemandProfile,
    station_ids: list[str],
) -> pd.DataFrame:
    rows: list[dict] = []

    for station_id in station_ids:
        for bucket in range(profile.buckets_per_day):
            true_lambda = profile.get_lambda(station_id, bucket)
            predicted_lambda = predictor.predict_lambda(station_id, bucket)

            rows.append(
                {
                    "station_id": station_id,
                    "bucket": bucket,
                    "minute_of_day": bucket * profile.bucket_minutes,
                    "true_lambda": true_lambda,
                    "predicted_lambda": predicted_lambda,
                    "abs_error": abs(true_lambda - predicted_lambda),
                }
            )

    return pd.DataFrame(rows)


def _convergence_points(training_days: int) -> list[int]:
    preferred = [1, 2, 3, 5, 7, 10, 14, 21, 30]
    points = [day for day in preferred if day <= training_days]
    if training_days > 0 and training_days not in points:
        points.append(training_days)
    return sorted(set(points))


def run_demand_experiment(
    station_ids: list[str],
    training_days: int = 14,
    benchmark_days: int = 30,
    bucket_minutes: int = 15,
    seed: int = 42,
) -> DemandExperimentResult:
    """
    Create one hidden world, learn it from training days, and generate a
    separate replayable benchmark set.

    Separate random-number streams are used for:
      1. hidden ground truth,
      2. training observations,
      3. benchmark observations.

    This means changing the amount of training data does not silently alter
    the future benchmark days.
    """

    if training_days < 1:
        raise ValueError("training_days must be >= 1")
    if benchmark_days < 1:
        raise ValueError("benchmark_days must be >= 1")
    if (24 * 60) % bucket_minutes != 0:
        raise ValueError("bucket_minutes must evenly divide one day")

    seed_sequence = np.random.SeedSequence(seed)
    profile_seed, training_seed, benchmark_seed = seed_sequence.spawn(3)

    profile = generate_ground_truth_profile(
        station_ids=station_ids,
        bucket_minutes=bucket_minutes,
        rng=np.random.default_rng(profile_seed),
    )

    training_generator = PoissonDemandGenerator(
        profile=profile,
        rng=np.random.default_rng(training_seed),
    )
    benchmark_generator = PoissonDemandGenerator(
        profile=profile,
        rng=np.random.default_rng(benchmark_seed),
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

    comparison = _compare_predictor_to_truth(
        predictor=predictor,
        profile=profile,
        station_ids=station_ids,
    )

    convergence_rows: list[dict] = []
    for days in _convergence_points(training_days):
        prefix = training_demand[training_demand["day"] <= days]
        prefix_history = _build_history(prefix, bucket_minutes=bucket_minutes)

        prefix_predictor = AveragePoissonPredictor()
        prefix_predictor.fit(prefix_history)

        prefix_comparison = _compare_predictor_to_truth(
            predictor=prefix_predictor,
            profile=profile,
            station_ids=station_ids,
        )

        convergence_rows.append(
            {
                "training_days": days,
                "mean_absolute_error": float(prefix_comparison["abs_error"].mean()),
                "root_mean_squared_error": float(
                    np.sqrt((prefix_comparison["abs_error"] ** 2).mean())
                ),
            }
        )

    convergence = pd.DataFrame(convergence_rows)

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
