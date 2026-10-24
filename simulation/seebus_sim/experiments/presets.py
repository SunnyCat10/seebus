from seebus_sim.experiments.suite import PolicySpec
from seebus_sim.transit import HistoricalPolicy, HybridPolicy, SensorPolicy, StaticPolicy


def default_policy_specs() -> list[PolicySpec]:
    """Policies used by the default single-run and batch research workflows."""

    return [
        PolicySpec("Static", StaticPolicy),
        PolicySpec("Historical", HistoricalPolicy),
        PolicySpec("Sensor", SensorPolicy),
        PolicySpec("Hybrid", HybridPolicy),
    ]
