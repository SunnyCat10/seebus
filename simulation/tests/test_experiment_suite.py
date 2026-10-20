from dataclasses import replace

from seebus_sim.config import DemandConfig, ExperimentConfig
from seebus_sim.experiments import PolicySpec, run_batch, run_experiment
from seebus_sim.transit import StaticPolicy, TransitConfig


def _tiny_config(name: str = "tiny", demand_seed: int = 10) -> ExperimentConfig:
    stations = ("a", "b", "c")
    return ExperimentConfig(
        name=name,
        station_ids=stations,
        demand=DemandConfig(
            training_days=2,
            benchmark_days=2,
            bucket_minutes=30,
            daily_noise_std=0.05,
            event_probability=0.0,
        ),
        transit=TransitConfig(
            route=stations,
            bus_count=2,
            bus_capacity=60,
            travel_minutes=5.0,
        ),
        demand_seed=demand_seed,
        transit_seed=99,
    )


def test_experiment_runner_produces_policy_comparison():
    result = run_experiment(
        _tiny_config(),
        [PolicySpec("Static", StaticPolicy)],
    )

    assert list(result.policies) == ["Static"]
    assert result.comparison.loc[0, "policy"] == "Static"
    assert result.comparison.loc[0, "generated_passengers"] > 0


def test_batch_combines_experiment_summaries():
    first = _tiny_config("first", 10)
    second = replace(first, name="second", demand_seed=11)

    result = run_batch(
        [first, second],
        [PolicySpec("Static", StaticPolicy)],
    )

    assert len(result.experiments) == 2
    assert set(result.comparison["experiment"]) == {"first", "second"}
