from seebus_sim.config import DemandConfig, ExperimentConfig
from seebus_sim.experiments import (
    PolicySpec,
    build_seeded_batch_configs,
    run_batch,
)
from seebus_sim.transit import (
    HistoricalPolicy,
    RouteConfig,
    StaticPolicy,
    TransitConfig,
)


def _tiny_base() -> ExperimentConfig:
    return ExperimentConfig(
        name="batch-test",
        demand=DemandConfig(
            training_days=2,
            benchmark_days=2,
            bucket_minutes=30,
            daily_noise_std=0.05,
            event_probability=0.15,
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
    )


def test_seeded_batch_configs_are_reproducible_and_prefix_stable():
    base = _tiny_base()
    first = build_seeded_batch_configs(base, 3, base_seed=1234)
    second = build_seeded_batch_configs(base, 5, base_seed=1234)

    assert [c.demand_seed for c in first] == [c.demand_seed for c in second[:3]]
    assert [c.transit_seed for c in first] == [c.transit_seed for c in second[:3]]
    assert [c.sensor_seed for c in first] == [c.sensor_seed for c in second[:3]]
    assert len({c.demand_seed for c in second}) == 5


def test_batch_produces_paired_and_policy_summaries():
    configs = build_seeded_batch_configs(_tiny_base(), 2, base_seed=77)
    result = run_batch(
        configs,
        [
            PolicySpec("Static", StaticPolicy),
            PolicySpec("Historical", HistoricalPolicy),
        ],
        baseline_policy="Static",
    )

    assert len(result.experiments) == 2
    assert len(result.comparison) == 4
    assert set(result.summary["policy"]) == {"Static", "Historical"}
    assert set(result.paired_comparison["policy"]) == {"Historical"}
    assert result.paired_comparison["run"].nunique() == 2
    assert set(result.paired_summary["policy"]) == {"Historical"}
    assert "average_wait_win_rate" in result.paired_summary.columns
    assert set(result.event_runs["run"]) == {1, 2}


def test_batch_day_type_rows_cover_every_policy_world_pair():
    configs = build_seeded_batch_configs(_tiny_base(), 2, base_seed=88)
    result = run_batch(
        configs,
        [PolicySpec("Static", StaticPolicy)],
        baseline_policy="Static",
    )

    # Every world has at least normal days, with optional additional event rows.
    normal = result.day_type_comparison[
        result.day_type_comparison["day_type"] == "normal"
    ]
    assert normal["run"].nunique() == 2
    assert set(normal["policy"]) == {"Static"}
