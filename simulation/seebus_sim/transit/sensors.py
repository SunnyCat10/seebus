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

    ``precision`` controls quantization. ``0.01`` produces readings in 1%
    increments: 0%, 1%, 2%, ..., 100%.
    """

    reference_queue_size: int = 50
    noise_std: float = 0.05
    precision: float = 0.01
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
    """Fast deterministic noisy occupancy readings for reproducible experiments.

    Earlier versions constructed a fresh NumPy RNG for every station/minute
    reading. That is statistically fine but expensive in large networks. This
    implementation pre-generates the *measurement error* and dropout mask for
    every station/minute using one RNG stream per station/day, then performs an
    O(1) array lookup during the simulation.

    Two policies using the same seed/day/station/minute therefore still receive
    the same measurement error. The actual occupancy is computed from each
    policy's own queue state, so paired comparisons remain fair.
    """

    # Policy decisions happen on minute-scale ticks today. 1441 also covers a
    # potential read exactly at 24:00 without reallocating.
    _MINUTES_PER_DAY = 24 * 60 + 1

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
        # The backend keeps the most recent successfully received reading.
        # A dropped packet therefore makes the observation stale rather than
        # magically erasing previously known occupancy.
        self._last_successful_reading: dict[str, float] = {}

        station_count = len(station_ids)
        self._noise = np.empty((station_count, self._MINUTES_PER_DAY), dtype=float)
        self._dropout = np.empty((station_count, self._MINUTES_PER_DAY), dtype=bool)

        for station_id, station_index in self._station_index.items():
            # One reproducible stream per station/day. This is dramatically
            # cheaper than creating a new Generator for every read.
            rng = np.random.default_rng(
                np.random.SeedSequence([seed, scenario_day, station_index])
            )
            self._dropout[station_index] = (
                rng.random(self._MINUTES_PER_DAY) < config.dropout_probability
            )
            if config.noise_std == 0:
                self._noise[station_index].fill(0.0)
            else:
                self._noise[station_index] = rng.normal(
                    0.0,
                    config.noise_std,
                    self._MINUTES_PER_DAY,
                )

    def sample(self, station_id: str, minute: float, waiting_count: int) -> float | None:
        """Attempt one station-to-server sensor update.

        A dropped packet leaves the server-side cached value untouched. A
        successful packet replaces that cached value with the newly measured
        occupancy. The simulation calls this independently of policy dispatch
        opportunities so packet dropout models communication reliability, not
        scheduler polling frequency.
        """
        if waiting_count < 0:
            raise ValueError("waiting_count must be >= 0")

        try:
            station_index = self._station_index[station_id]
        except KeyError as exc:
            raise KeyError(f"unknown sensor station {station_id!r}") from exc

        minute_index = int(np.floor(max(0.0, minute) + 1e-9))
        minute_index = min(minute_index, self._MINUTES_PER_DAY - 1)

        if self._dropout[station_index, minute_index]:
            return self._last_successful_reading.get(station_id)

        true_occupancy = min(
            1.0,
            waiting_count / self.config.reference_queue_size,
        )
        measured = true_occupancy + float(self._noise[station_index, minute_index])
        measured = min(1.0, max(0.0, measured))

        steps = round(measured / self.config.precision)
        reading = min(1.0, max(0.0, steps * self.config.precision))
        self._last_successful_reading[station_id] = reading
        return reading

    def latest_reading(
        self,
        station_id: str,
        minute: float | None = None,
        waiting_count: int | None = None,
    ) -> float | None:
        """Return the most recent reading received by the simulated backend.

        ``minute`` and ``waiting_count`` are accepted so this method can be
        passed directly as the simulator's normal sensor-provider callback.
        They intentionally do not trigger a new sensor transmission.
        """

        if station_id not in self._station_index:
            raise KeyError(f"unknown sensor station {station_id!r}")
        return self._last_successful_reading.get(station_id)

    def read(self, station_id: str, minute: float, waiting_count: int) -> float | None:
        """Backward-compatible sample-and-read helper for focused unit tests."""

        return self.sample(station_id, minute, waiting_count)
