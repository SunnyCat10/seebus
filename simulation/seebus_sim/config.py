from dataclasses import dataclass

from seebus_sim.transit import RouteConfig, TransitConfig


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
    demand: DemandConfig
    transit: TransitConfig
    demand_seed: int = 42
    transit_seed: int = 2026

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("experiment name must not be empty")

    @property
    def station_ids(self) -> tuple[str, ...]:
        return self.transit.station_ids


def default_experiment_config() -> ExperimentConfig:
    """Baseline shared-hub experiment used by the research runner."""

    routes = (
        RouteConfig(
            id="route-a",
            stations=("station-a", "station-b"),
            travel_minutes=5.0,
        ),
        RouteConfig(
            id="route-b",
            stations=("station-c", "station-d"),
            travel_minutes=5.0,
        ),
    )
    return ExperimentConfig(
        name="baseline",
        demand=DemandConfig(),
        transit=TransitConfig(
            routes=routes,
            bus_count=3,
            bus_capacity=75,
            static_dispatch_interval_minutes=6.0,
        ),
        demand_seed=42,
        transit_seed=2026,
    )
