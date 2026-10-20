from dataclasses import dataclass

from seebus_sim.transit import TransitConfig


@dataclass(frozen=True)
class DemandConfig:
    """Configuration for generating and learning passenger demand."""

    training_days: int = 14
    benchmark_days: int = 30
    bucket_minutes: int = 15
    daily_noise_std: float = 0.12
    event_probability: float = 0.07

    def __post_init__(self) -> None:
        if self.training_days < 1:
            raise ValueError("training_days must be >= 1")
        if self.benchmark_days < 1:
            raise ValueError("benchmark_days must be >= 1")
        if (24 * 60) % self.bucket_minutes != 0:
            raise ValueError("bucket_minutes must evenly divide one day")
        if self.daily_noise_std < 0:
            raise ValueError("daily_noise_std must be >= 0")
        if not 0.0 <= self.event_probability <= 1.0:
            raise ValueError("event_probability must be between 0 and 1")


@dataclass(frozen=True)
class ExperimentConfig:
    """One reproducible SeeBus simulation experiment."""

    name: str
    station_ids: tuple[str, ...]
    demand: DemandConfig
    transit: TransitConfig
    demand_seed: int = 42
    transit_seed: int = 2026

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("experiment name must not be empty")
        if len(self.station_ids) < 2:
            raise ValueError("station_ids must contain at least two stations")
        if len(set(self.station_ids)) != len(self.station_ids):
            raise ValueError("station_ids must be unique")
        if tuple(self.transit.route) != tuple(self.station_ids):
            raise ValueError("transit route must match station_ids for the current loop model")


def default_experiment_config() -> ExperimentConfig:
    """The baseline configuration used throughout the current research setup."""

    stations = ("station-a", "station-b", "station-c", "station-d")
    return ExperimentConfig(
        name="baseline",
        station_ids=stations,
        demand=DemandConfig(),
        transit=TransitConfig(
            route=stations,
            bus_count=2,
            bus_capacity=75,
            travel_minutes=5.0,
        ),
        demand_seed=42,
        transit_seed=2026,
    )
