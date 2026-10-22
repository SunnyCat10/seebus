from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SensorConfig:
    """Configuration for the simulated station occupancy sensor.

    The real SeeBus sensor reports an approximate occupancy fraction rather than
    an exact passenger count. The simulator therefore converts the true queue
    length to a normalized occupancy, adds measurement noise, and quantizes the
    result to finite precision before exposing it to policies.

    ``reference_queue_size`` is the number of waiting passengers represented by
    100% occupancy. Larger queues saturate at 100%.

    ``noise_std`` is an absolute occupancy standard deviation. For example,
    ``0.05`` means roughly 5 percentage points of one-sigma measurement error.

    ``precision`` controls quantization. ``0.05`` produces readings in 5%
    increments: 0%, 5%, 10%, ..., 100%.
    """

    reference_queue_size: int = 50
    noise_std: float = 0.05
    precision: float = 0.05
    dropout_probability: float = 0.0

    def __post_init__(self) -> None:
        if self.reference_queue_size < 1:
            raise ValueError("reference_queue_size must be >= 1")
        if self.noise_std < 0:
            raise ValueError("noise_std must be >= 0")
        if not 0 < self.precision <= 1:
            raise ValueError("precision must be in (0, 1]")
        if not 0.0 <= self.dropout_probability <= 1.0:
            raise ValueError("dropout_probability must be between 0 and 1")


class NoisyOccupancySensor:
    """Deterministic noisy occupancy readings for reproducible experiments.

    Noise is generated from ``seed + scenario day + station + decision minute``
    rather than from call order. Therefore two policies that happen to observe
    the same queue at the same simulated time receive the same measurement
    error, which keeps policy comparisons paired and reproducible.
    """

    def __init__(
        self,
        config: SensorConfig,
        *,
        station_ids: tuple[str, ...],
        scenario_day: int,
        seed: int,
    ) -> None:
        self.config = config
        self.scenario_day = scenario_day
        self.seed = seed
        self._station_index = {
            station_id: index for index, station_id in enumerate(station_ids)
        }
        self._cache: dict[tuple[str, int], float | None] = {}

    def _rng(self, station_id: str, minute: float) -> np.random.Generator:
        try:
            station_index = self._station_index[station_id]
        except KeyError as exc:
            raise KeyError(f"unknown sensor station {station_id!r}") from exc

        # Policy decisions currently happen on integer-minute ticks. Flooring
        # keeps repeated reads inside the same minute stable as well.
        minute_index = int(np.floor(max(0.0, minute) + 1e-9))
        sequence = np.random.SeedSequence(
            [self.seed, self.scenario_day, station_index, minute_index]
        )
        return np.random.default_rng(sequence)

    def read(self, station_id: str, minute: float, waiting_count: int) -> float | None:
        if waiting_count < 0:
            raise ValueError("waiting_count must be >= 0")

        minute_index = int(np.floor(max(0.0, minute) + 1e-9))
        cache_key = (station_id, minute_index)
        if cache_key in self._cache:
            return self._cache[cache_key]

        rng = self._rng(station_id, minute)
        if rng.random() < self.config.dropout_probability:
            self._cache[cache_key] = None
            return None

        true_occupancy = min(
            1.0,
            waiting_count / self.config.reference_queue_size,
        )
        measured = true_occupancy + float(rng.normal(0.0, self.config.noise_std))
        measured = float(np.clip(measured, 0.0, 1.0))

        steps = round(measured / self.config.precision)
        quantized = float(np.clip(steps * self.config.precision, 0.0, 1.0))
        self._cache[cache_key] = quantized
        return quantized
