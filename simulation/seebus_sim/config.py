from dataclasses import dataclass

from seebus_sim.scenarios import NetworkScenario, get_network_scenario
from seebus_sim.transit.config import TransitConfig
from seebus_sim.transit.sensors import SensorConfig


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
    sensor: SensorConfig = SensorConfig()
    demand_seed: int = 42
    transit_seed: int = 2026
    sensor_seed: int = 31415

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("experiment name must not be empty")

    @property
    def station_ids(self) -> tuple[str, ...]:
        return self.transit.station_ids


def experiment_config_for_scenario(
    scenario: str | NetworkScenario,
    *,
    name: str | None = None,
) -> ExperimentConfig:
    """Create the standard research experiment on a chosen network scenario."""

    network = get_network_scenario(scenario) if isinstance(scenario, str) else scenario
    return ExperimentConfig(
        name=name or network.name,
        demand=DemandConfig(),
        transit=network.to_transit_config(),
        sensor=SensorConfig(
            reference_queue_size=50,
            noise_std=0.05,
            precision=0.05,
        ),
        demand_seed=42,
        transit_seed=2026,
        sensor_seed=31415,
    )


def default_experiment_config(
    scenario: str | NetworkScenario = "small",
) -> ExperimentConfig:
    """Standard experiment; choose ``small`` or ``large`` network preset."""

    return experiment_config_for_scenario(scenario)
