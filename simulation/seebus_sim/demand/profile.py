from dataclasses import dataclass

import numpy as np


WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


@dataclass(frozen=True)
class GroundTruthDemandProfile:
    """
    Hidden demand profile known only to the simulator.

    `lambda_by_station_bucket` is the station's normal time-of-day demand curve
    before day-of-week, day-to-day noise, and one-off events are applied.
    Values are expected passenger arrivals per minute.
    """

    lambda_by_station_bucket: dict[str, np.ndarray]
    station_types: dict[str, str]
    weekday_factors: dict[str, np.ndarray]
    bucket_minutes: int

    @property
    def buckets_per_day(self) -> int:
        return 24 * 60 // self.bucket_minutes

    def get_lambda(self, station_id: str, bucket: int) -> float:
        """Return the station's normal time-of-day lambda for a bucket."""
        return float(self.lambda_by_station_bucket[station_id][bucket])

    def get_weekday_factor(self, station_id: str, weekday_index: int) -> float:
        return float(self.weekday_factors[station_id][weekday_index])


def _station_weekday_factors(station_type: str) -> np.ndarray:
    """Multipliers for Monday ... Sunday."""
    factors = {
        "residential": [1.00, 1.00, 1.00, 1.02, 1.05, 0.72, 0.62],
        "office": [1.00, 1.02, 1.02, 1.00, 0.90, 0.28, 0.22],
        "shopping": [0.90, 0.92, 0.95, 1.00, 1.18, 1.35, 0.88],
        "mixed": [0.96, 0.98, 1.00, 1.02, 1.08, 0.92, 0.82],
    }
    return np.asarray(factors[station_type], dtype=float)


def _generate_station_curve(
    station_type: str,
    hours: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """Create one smooth normal-day demand curve for a station."""

    baseline = rng.uniform(0.15, 0.9)

    if station_type == "residential":
        morning_strength = rng.uniform(2.8, 5.5)
        evening_strength = rng.uniform(1.2, 3.0)
        midday_strength = rng.uniform(0.15, 0.65)
        morning_center = rng.normal(7.8, 0.35)
        evening_center = rng.normal(17.8, 0.55)
        midday_center = rng.normal(12.5, 0.5)
    elif station_type == "office":
        morning_strength = rng.uniform(3.2, 6.0)
        evening_strength = rng.uniform(2.5, 5.0)
        midday_strength = rng.uniform(0.5, 1.2)
        morning_center = rng.normal(8.4, 0.3)
        evening_center = rng.normal(17.2, 0.45)
        midday_center = rng.normal(12.6, 0.4)
    elif station_type == "shopping":
        morning_strength = rng.uniform(0.4, 1.4)
        evening_strength = rng.uniform(1.8, 3.8)
        midday_strength = rng.uniform(1.4, 3.3)
        morning_center = rng.normal(9.0, 0.45)
        evening_center = rng.normal(18.4, 0.55)
        midday_center = rng.normal(13.4, 0.55)
    else:  # mixed
        morning_strength = rng.uniform(1.8, 4.0)
        evening_strength = rng.uniform(1.5, 3.5)
        midday_strength = rng.uniform(0.6, 1.5)
        morning_center = rng.normal(8.2, 0.4)
        evening_center = rng.normal(17.5, 0.55)
        midday_center = rng.normal(13.0, 0.5)

    morning_width = rng.uniform(0.75, 1.15)
    evening_width = rng.uniform(1.0, 1.55)
    midday_width = rng.uniform(2.0, 3.0)

    morning = morning_strength * np.exp(
        -0.5 * ((hours - morning_center) / morning_width) ** 2
    )
    evening = evening_strength * np.exp(
        -0.5 * ((hours - evening_center) / evening_width) ** 2
    )
    midday = midday_strength * np.exp(
        -0.5 * ((hours - midday_center) / midday_width) ** 2
    )

    return baseline + morning + midday + evening


def generate_ground_truth_profile(
    station_ids: list[str],
    bucket_minutes: int,
    rng: np.random.Generator,
) -> GroundTruthDemandProfile:
    """
    Create a hidden normal-demand pattern for every station.

    Every station is assigned a broad archetype. The archetype influences its
    rush-hour shape and weekday/weekend pattern. The predictor never receives
    the archetype or these hidden factors.
    """

    buckets_per_day = 24 * 60 // bucket_minutes
    minutes = np.arange(buckets_per_day) * bucket_minutes
    hours = minutes / 60.0

    station_type_choices = ["residential", "office", "shopping", "mixed"]

    # Keep small experiments diverse while retaining randomness. For four
    # stations this guarantees one of each archetype; for larger networks the
    # archetypes are repeated and shuffled.
    repeated_types = (
        station_type_choices
        * ((len(station_ids) + len(station_type_choices) - 1) // len(station_type_choices))
    )[:len(station_ids)]
    rng.shuffle(repeated_types)

    profiles: dict[str, np.ndarray] = {}
    station_types: dict[str, str] = {}
    weekday_factors: dict[str, np.ndarray] = {}

    for station_id, station_type in zip(station_ids, repeated_types):
        station_types[station_id] = station_type
        profiles[station_id] = _generate_station_curve(station_type, hours, rng)
        weekday_factors[station_id] = _station_weekday_factors(station_type)

    return GroundTruthDemandProfile(
        lambda_by_station_bucket=profiles,
        station_types=station_types,
        weekday_factors=weekday_factors,
        bucket_minutes=bucket_minutes,
    )
