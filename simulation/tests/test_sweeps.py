from dataclasses import replace

import pandas as pd

from seebus_sim.experiments import (
    BatchResult,
    build_core_sweeps,
    build_seeded_batch_configs,
    combine_sweep_batches,
    event_probability_for_expected_network_rate,
    research_suite_base_config,
)
from seebus_sim.reporting import (
    build_historical_benefit_summary,
    build_perfect_sensor_degradation_summary,
)


def test_event_rate_conversion_is_network_scale_aware():
    assert event_probability_for_expected_network_rate(0.0, 35) == 0.0
    assert event_probability_for_expected_network_rate(1.0, 35) == 1.0 / 35.0
    assert event_probability_for_expected_network_rate(4.0, 35) == 4.0 / 35.0


def test_core_sweeps_change_one_factor_at_a_time():
    base = research_suite_base_config("large")
    fleet, events, sensor, dropout, hybrid = build_core_sweeps(base)

    assert [point.value for point in fleet.points] == [6.0, 8.0, 9.0, 10.0, 12.0, 14.0, 16.0, 18.0, 20.0]
    assert [point.config.transit.bus_count for point in fleet.points] == [6, 8, 9, 10, 12, 14, 16, 18, 20]
    assert all(point.config.sensor == base.sensor for point in fleet.points)

    assert [point.value for point in events.points] == [0.0, 0.1, 0.25, 0.5, 1.0]
    assert events.points[-1].config.demand.event_probability == 1.0 / len(base.station_ids)
    assert all(point.config.transit.bus_count == base.transit.bus_count for point in events.points)

    assert [point.value for point in sensor.points] == [0.0, 5.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 75.0, 100.0]
    assert sensor.points[1].config.sensor.noise_std == 0.05
    assert all(point.config.sensor.precision == 0.01 for point in sensor.points)
    assert all(point.config.demand == base.demand for point in sensor.points)

    assert [point.value for point in dropout.points] == [0.0, 5.0, 10.0, 20.0, 40.0, 60.0, 80.0, 90.0, 100.0]
    assert dropout.points[3].config.sensor.dropout_probability == 0.20
    assert dropout.points[-1].config.sensor.dropout_probability == 1.0
    assert all(point.config.sensor.noise_std == base.sensor.noise_std for point in dropout.points)

    assert [point.value for point in hybrid.points] == [0.0, 0.25, 0.5, 0.6, 0.75, 1.0]
    assert all(point.config == base or point.config.transit == base.transit for point in hybrid.points)
    first_hybrid = next(spec for spec in hybrid.points[0].policies if spec.label == "Hybrid")
    last_hybrid = next(spec for spec in hybrid.points[-1].policies if spec.label == "Hybrid")
    assert first_hybrid.factory().config.normalized_weights == (1.0, 0.0)
    assert last_hybrid.factory().config.normalized_weights == (0.0, 1.0)


def test_sweep_points_reuse_same_world_seed_sequence():
    base = research_suite_base_config("large")
    fleet = build_core_sweeps(base)[0]

    first = build_seeded_batch_configs(fleet.points[0].config, 4, base_seed=9876)
    second = build_seeded_batch_configs(fleet.points[1].config, 4, base_seed=9876)

    assert [config.demand_seed for config in first] == [config.demand_seed for config in second]
    assert [config.transit_seed for config in first] == [config.transit_seed for config in second]
    assert [config.sensor_seed for config in first] == [config.sensor_seed for config in second]


def _fake_batch(value: float) -> BatchResult:
    comparison = pd.DataFrame(
        {
            "run": [1, 1],
            "policy": ["Static", "Hybrid"],
            "average_wait_minutes": [10.0, 8.0 - value * 0.01],
        }
    )
    summary = pd.DataFrame(
        {
            "policy": ["Static", "Hybrid"],
            "average_wait_minutes_mean": [10.0, 8.0 - value * 0.01],
            "average_wait_minutes_ci95_low": [9.9, 7.9 - value * 0.01],
            "average_wait_minutes_ci95_high": [10.1, 8.1 - value * 0.01],
            "p95_wait_minutes_mean": [20.0, 15.0],
            "p95_wait_minutes_ci95_low": [19.0, 14.0],
            "p95_wait_minutes_ci95_high": [21.0, 16.0],
        }
    )
    paired = pd.DataFrame(
        {"run": [1], "policy": ["Hybrid"], "baseline_policy": ["Static"]}
    )
    paired_summary = pd.DataFrame(
        {
            "policy": ["Hybrid"],
            "baseline_policy": ["Static"],
            "average_wait_minutes_delta_mean": [-2.0],
            "average_wait_minutes_delta_ci95_low": [-2.2],
            "average_wait_minutes_delta_ci95_high": [-1.8],
        }
    )
    return BatchResult(
        experiments=[],
        comparison=comparison,
        summary=summary,
        paired_comparison=paired,
        paired_summary=paired_summary,
        day_type_comparison=pd.DataFrame(),
        event_runs=pd.DataFrame(),
        baseline_policy="Static",
    )


def test_suite_aggregation_adds_long_form_sweep_metadata():
    base = research_suite_base_config("large")
    fleet = build_core_sweeps(base)[0]
    result = combine_sweep_batches(
        [
            (fleet, fleet.points[0], _fake_batch(fleet.points[0].value)),
            (fleet, fleet.points[1], _fake_batch(fleet.points[1].value)),
        ]
    )

    assert set(result.summary["sweep"]) == {"fleet-pressure"}
    assert set(result.summary["parameter_value"]) == {6.0, 8.0}
    assert set(result.summary["policy"]) == {"Static", "Hybrid"}


def test_event_frequency_sweep_keeps_non_event_hidden_components_paired():
    from seebus_sim.experiment import run_demand_experiment

    stations = ["a", "b", "c", "d"]
    low = run_demand_experiment(
        stations,
        training_days=2,
        benchmark_days=3,
        seed=2026,
        event_probability=0.25,
    )
    high = run_demand_experiment(
        stations,
        training_days=2,
        benchmark_days=3,
        seed=2026,
        event_probability=0.75,
    )

    for column in ("base_lambda", "weekday_factor", "daily_factor"):
        pd.testing.assert_series_equal(
            low.benchmark_demand[column],
            high.benchmark_demand[column],
            check_names=False,
        )

    low_events = low.event_summary[low.event_summary["split"] == "benchmark"]
    high_events = high.event_summary[high.event_summary["split"] == "benchmark"]
    low_keys = set(zip(low_events["scenario_day"], low_events["station_id"]))
    high_keys = set(zip(high_events["scenario_day"], high_events["station_id"]))
    assert low_keys <= high_keys

    common = low_events.merge(
        high_events,
        on=["scenario_day", "station_id"],
        suffixes=("_low", "_high"),
    )
    if not common.empty:
        assert (common["start_minute_low"] == common["start_minute_high"]).all()
        assert (common["duration_minutes_low"] == common["duration_minutes_high"]).all()
        assert (common["event_multiplier_low"] == common["event_multiplier_high"]).all()


def test_robustness_summaries_use_paired_world_differences():
    base = research_suite_base_config("large")
    sensor_sweep = build_core_sweeps(base)[2]

    rows = []
    for run, historical, sensor_0, hybrid_0, sensor_100, hybrid_100 in (
        (1, 10.0, 8.0, 7.5, 11.0, 9.0),
        (2, 12.0, 9.0, 8.5, 13.0, 10.5),
    ):
        for value, label, sensor, hybrid in (
            (0.0, "0% error σ", sensor_0, hybrid_0),
            (100.0, "100% error σ", sensor_100, hybrid_100),
        ):
            for policy, wait in (
                ("Historical", historical),
                ("Sensor", sensor),
                ("Hybrid", hybrid),
            ):
                rows.append(
                    {
                        "sweep": sensor_sweep.name,
                        "run": run,
                        "parameter_value": value,
                        "parameter_label": label,
                        "policy": policy,
                        "average_wait_minutes": wait,
                    }
                )

    runs = pd.DataFrame(rows)
    benefit = build_historical_benefit_summary(runs, sensor_sweep)
    degradation = build_perfect_sensor_degradation_summary(runs, sensor_sweep)

    sensor_benefit_0 = benefit[
        (benefit["policy"] == "Sensor") & (benefit["parameter_value"] == 0.0)
    ].iloc[0]
    sensor_benefit_100 = benefit[
        (benefit["policy"] == "Sensor") & (benefit["parameter_value"] == 100.0)
    ].iloc[0]
    assert sensor_benefit_0["benefit_minutes_mean"] == 2.5
    assert sensor_benefit_100["benefit_minutes_mean"] == -1.0

    sensor_degradation_100 = degradation[
        (degradation["policy"] == "Sensor")
        & (degradation["parameter_value"] == 100.0)
    ].iloc[0]
    hybrid_degradation_100 = degradation[
        (degradation["policy"] == "Hybrid")
        & (degradation["parameter_value"] == 100.0)
    ].iloc[0]
    assert sensor_degradation_100["degradation_minutes_mean"] == 3.5
    assert hybrid_degradation_100["degradation_minutes_mean"] == 1.75
