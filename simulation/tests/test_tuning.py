import pandas as pd

from seebus_sim.experiments.tuning import (
    TuningGridDefinition,
    annotate_tuning_runs,
    build_historical_threshold_summary,
    build_hybrid_grid_summary,
    build_tuning_policy_specs,
)
from seebus_sim.experiments.suite import BatchResult


def test_tuning_policy_grid_has_expected_configs():
    definition = TuningGridDefinition(
        target_load_fractions=(0.25, 0.35),
        sensor_weights=(0.5, 0.75),
    )
    specs, metadata = build_tuning_policy_specs(definition)
    assert len(specs) == 2 + 2 + 4
    assert set(metadata["family"]) == {"Static", "Sensor", "Historical", "Hybrid"}

    hybrid = next(spec for spec in specs if spec.label == "Hybrid[t=0.35,w=0.75]")
    config = hybrid.factory().config
    assert config.target_load_fraction == 0.35
    assert config.normalized_weights == (0.25, 0.75)


def test_tuning_summary_uses_same_threshold_historical_pairing():
    definition = TuningGridDefinition((0.25, 0.35), (0.5,))
    _, metadata = build_tuning_policy_specs(definition)
    rows = []
    for run in (1, 2):
        rows.extend([
            {"run": run, "policy": "Static", "average_wait_minutes": 15.0, "p95_wait_minutes": 50.0},
            {"run": run, "policy": "Sensor", "average_wait_minutes": 9.5, "p95_wait_minutes": 21.0},
            {"run": run, "policy": "Historical[t=0.25]", "average_wait_minutes": 11.0, "p95_wait_minutes": 31.0},
            {"run": run, "policy": "Historical[t=0.35]", "average_wait_minutes": 10.5, "p95_wait_minutes": 30.0},
            {"run": run, "policy": "Hybrid[t=0.25,w=0.5]", "average_wait_minutes": 9.0, "p95_wait_minutes": 20.0},
            {"run": run, "policy": "Hybrid[t=0.35,w=0.5]", "average_wait_minutes": 8.8, "p95_wait_minutes": 19.5},
        ])
    batch = BatchResult([], pd.DataFrame(rows), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), "Static")
    annotated = annotate_tuning_runs(batch, metadata)
    historical = build_historical_threshold_summary(annotated)
    hybrid = build_hybrid_grid_summary(annotated)

    assert len(historical) == 2
    cell = hybrid[(hybrid["target_load_fraction"] == 0.35) & (hybrid["sensor_weight"] == 0.5)].iloc[0]
    assert abs(cell["benefit_vs_historical_minutes_mean"] - 1.7) < 1e-12
    assert abs(cell["benefit_vs_sensor_minutes_mean"] - 0.7) < 1e-12
