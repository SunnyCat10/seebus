from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class GroundTruthDemandProfile:
    """
    Hidden demand profile known only to the simulator.

    lambda_by_station_bucket stores expected passenger arrivals per minute.
    """

    lambda_by_station_bucket: dict[str, np.ndarray]
    bucket_minutes: int

    @property
    def buckets_per_day(self) -> int:
        return 24 * 60 // self.bucket_minutes

    def get_lambda(self, station_id: str, bucket: int) -> float:
        return float(self.lambda_by_station_bucket[station_id][bucket])


def generate_ground_truth_profile(
    station_ids: list[str],
    bucket_minutes: int,
    rng: np.random.Generator,
) -> GroundTruthDemandProfile:
    """
    Create a hidden daily demand curve for each station.

    Each station gets:
    - a random baseline arrival rate
    - a random morning-rush strength
    - a random evening-rush strength
    - a small station-specific phase variation

    The policy/predictor never sees these true lambdas.
    """

    buckets_per_day = 24 * 60 // bucket_minutes
    minutes = np.arange(buckets_per_day) * bucket_minutes
    hours = minutes / 60.0

    profiles: dict[str, np.ndarray] = {}

    for station_id in station_ids:
        baseline = rng.uniform(0.15, 1.2)
        morning_strength = rng.uniform(1.5, 5.0)
        evening_strength = rng.uniform(1.0, 4.0)

        morning_center = rng.normal(8.0, 0.35)
        evening_center = rng.normal(17.0, 0.5)

        morning = morning_strength * np.exp(
            -0.5 * ((hours - morning_center) / 1.0) ** 2
        )
        evening = evening_strength * np.exp(
            -0.5 * ((hours - evening_center) / 1.35) ** 2
        )

        midday = rng.uniform(0.2, 0.8) * np.exp(
            -0.5 * ((hours - 12.5) / 2.8) ** 2
        )

        profile = baseline + morning + evening + midday
        profiles[station_id] = profile

    return GroundTruthDemandProfile(
        lambda_by_station_bucket=profiles,
        bucket_minutes=bucket_minutes,
    )
