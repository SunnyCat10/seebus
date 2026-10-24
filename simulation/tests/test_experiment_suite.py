from dataclasses import replace

from seebus_sim.config import DemandConfig, ExperimentConfig
from seebus_sim.experiments import PolicySpec, run_batch, run_experiment
from seebus_sim.transit import (
    HistoricalPolicy,
    HybridPolicy,
    RouteConfig,
    SensorPolicy,
    StaticPolicy,
    TransitConfig,
)


def _tiny_config(name: str = "tiny", demand_seed: int = 10) -> ExperimentConfig:
    return ExperimentConfig(
        name=name,
        demand=DemandConfig(
            training_days=2,
            benchmark_days=2,
            bucket_minutes=30,
            daily_noise_std=0.05,
            event_probability=0.0,
        ),
        transit=TransitConfig(
            routes=(
                RouteConfig("route-a", ("a1", "a2"), travel_minutes=5.0),
                RouteConfig("route-b", ("b1", "b2"), travel_minutes=5.0),
            ),
            bus_count=2,
            bus_capacity=60,
            static_dispatch_interval_minutes=10.0,
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
    assert not result.policies["Static"].route_metrics.empty
    assert not result.policies["Static"].dispatch_events.empty


def test_batch_combines_experiment_summaries():
    first = _tiny_config("first", 10)
    second = replace(first, name="second", demand_seed=11)

    result = run_batch(
        [first, second],
        [PolicySpec("Static", StaticPolicy)],
    )

    assert len(result.experiments) == 2
    assert set(result.comparison["experiment"]) == {"first", "second"}


def test_experiment_runner_compares_policies_on_same_generated_world():
    result = run_experiment(
        _tiny_config(),
        [
            PolicySpec("Static", StaticPolicy),
            PolicySpec("Historical", HistoricalPolicy),
        ],
    )

    assert list(result.policies) == ["Static", "Historical"]
    assert set(result.comparison["policy"]) == {"Static", "Historical"}
    assert result.comparison["generated_passengers"].nunique() == 1
    assert result.policies["Historical"].policy_name == "historical"
    assert "policy_score" in result.policies["Historical"].dispatch_events.columns


def test_experiment_runner_supports_sensor_and_hybrid_policies():
    result = run_experiment(
        _tiny_config(),
        [
            PolicySpec("Static", StaticPolicy),
            PolicySpec("Sensor", SensorPolicy),
            PolicySpec("Hybrid", HybridPolicy),
        ],
    )

    assert set(result.comparison["policy"]) == {"Static", "Sensor", "Hybrid"}
    assert result.comparison["generated_passengers"].nunique() == 1
    assert result.policies["Sensor"].policy_name == "sensor"
    assert result.policies["Hybrid"].policy_name == "hybrid"
