from __future__ import annotations

from dataclasses import dataclass, replace
from functools import partial
from typing import Iterable

import pandas as pd

from seebus_sim.config import ExperimentConfig, default_experiment_config
from seebus_sim.experiments.suite import BatchResult, PolicySpec
from seebus_sim.transit import HistoricalPolicy, HybridPolicy, SensorPolicy, StaticPolicy
from seebus_sim.transit.policies.hybrid import HybridPolicyConfig


@dataclass(frozen=True)
class SweepPoint:
    """One parameter value in an experiment sweep."""

    value: float
    label: str
    slug: str
    config: ExperimentConfig
    policies: tuple[PolicySpec, ...] | None = None


@dataclass(frozen=True)
class SweepDefinition:
    """A one-factor-at-a-time sweep over otherwise identical experiments."""

    name: str
    title: str
    parameter: str
    x_label: str
    description: str
    points: tuple[SweepPoint, ...]

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("sweep name must not be empty")
        if not self.points:
            raise ValueError("sweep must contain at least one point")
        values = [point.value for point in self.points]
        if len(values) != len(set(values)):
            raise ValueError(f"sweep {self.name!r} contains duplicate values")


@dataclass
class SweepSuiteResult:
    """Long-form aggregate tables for several batches-of-batches."""

    definitions: tuple[SweepDefinition, ...]
    runs: pd.DataFrame
    summary: pd.DataFrame
    paired_comparison: pd.DataFrame
    paired_summary: pd.DataFrame
    day_type_comparison: pd.DataFrame
    event_runs: pd.DataFrame
    baseline_policy: str


def event_probability_for_expected_network_rate(
    events_per_network_day: float,
    station_count: int,
) -> float:
    """Convert an intuitive network event rate to the existing station/day Bernoulli model.

    The current hidden-world generator independently gives each station one
    chance to receive a one-off event per simulated day. Setting
    ``p = expected_events / station_count`` therefore produces exactly the
    requested *expected* number of station-events per network-day while keeping
    the generator backwards compatible.
    """

    if station_count < 1:
        raise ValueError("station_count must be >= 1")
    if events_per_network_day < 0:
        raise ValueError("events_per_network_day must be >= 0")
    if events_per_network_day > station_count:
        raise ValueError(
            "events_per_network_day cannot exceed station_count with the current "
            "one-event-per-station/day generator"
        )
    return float(events_per_network_day / station_count)


def research_suite_base_config(
    scenario: str = "large",
    *,
    events_per_network_day: float = 1.0,
    sensor_noise_std: float = 0.05,
) -> ExperimentConfig:
    """Central baseline used by one-factor-at-a-time robustness sweeps.

    Existing ``run.py`` and ``run_batch.py`` defaults are deliberately not
    changed. The suite uses an explicit, easier-to-explain baseline of one
    expected station-event per network-day and 5 percentage points of sensor
    measurement noise.
    """

    config = default_experiment_config(scenario)
    probability = event_probability_for_expected_network_rate(
        events_per_network_day,
        len(config.station_ids),
    )
    return replace(
        config,
        name=f"{scenario}-suite-base",
        demand=replace(config.demand, event_probability=probability),
        sensor=replace(config.sensor, noise_std=sensor_noise_std),
    )


def _slug_number(value: float) -> str:
    text = f"{value:g}".replace("-", "minus-").replace(".", "p")
    return text


def build_fleet_pressure_sweep(
    base_config: ExperimentConfig,
    values: Iterable[int] = (6, 8, 9, 10, 12, 14, 16, 18, 20),
) -> SweepDefinition:
    points: list[SweepPoint] = []
    for buses in values:
        buses = int(buses)
        if buses < 1:
            raise ValueError("fleet sizes must be >= 1")
        config = replace(
            base_config,
            name=f"{base_config.name}-fleet-{buses}",
            transit=replace(base_config.transit, bus_count=buses),
        )
        points.append(
            SweepPoint(
                value=float(buses),
                label=f"{buses} buses",
                slug=f"buses-{buses:02d}",
                config=config,
            )
        )
    return SweepDefinition(
        name="fleet-pressure",
        title="Fleet pressure",
        parameter="bus_count",
        x_label="Shared buses",
        description=(
            "Vary the size of the shared bus pool while keeping demand, routes, "
            "sensor quality, and the nominal static timetable unchanged."
        ),
        points=tuple(points),
    )


def build_event_frequency_sweep(
    base_config: ExperimentConfig,
    values: Iterable[float] = (0.0, 0.1, 0.25, 0.5, 1.0),
) -> SweepDefinition:
    station_count = len(base_config.station_ids)
    points: list[SweepPoint] = []
    for events_per_day in values:
        events_per_day = float(events_per_day)
        probability = event_probability_for_expected_network_rate(
            events_per_day,
            station_count,
        )
        config = replace(
            base_config,
            name=f"{base_config.name}-events-{_slug_number(events_per_day)}",
            demand=replace(base_config.demand, event_probability=probability),
        )
        points.append(
            SweepPoint(
                value=events_per_day,
                label=f"{events_per_day:g} events/day",
                slug=f"events-{_slug_number(events_per_day)}",
                config=config,
            )
        )
    return SweepDefinition(
        name="event-frequency",
        title="One-off event frequency",
        parameter="expected_events_per_network_day",
        x_label="Expected station-events per network-day",
        description=(
            "Vary the expected number of unexpected station demand spikes per "
            "network-day. Internally this is converted to the equivalent "
            "per-station/day event probability."
        ),
        points=tuple(points),
    )


def build_sensor_accuracy_sweep(
    base_config: ExperimentConfig,
    error_percent_values: Iterable[float] = (0.0, 5.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 75.0, 100.0),
) -> SweepDefinition:
    points: list[SweepPoint] = []
    for error_percent in error_percent_values:
        error_percent = float(error_percent)
        if error_percent < 0:
            raise ValueError("sensor error values must be >= 0")
        config = replace(
            base_config,
            name=f"{base_config.name}-sensor-error-{_slug_number(error_percent)}",
            sensor=replace(base_config.sensor, noise_std=error_percent / 100.0),
        )
        points.append(
            SweepPoint(
                value=error_percent,
                label=f"{error_percent:g}% error σ",
                slug=f"error-{_slug_number(error_percent)}pct",
                config=config,
            )
        )
    return SweepDefinition(
        name="sensor-accuracy",
        title="Occupancy estimation accuracy",
        parameter="sensor_noise_std_percent",
        x_label="Occupancy estimation error σ (%)",
        description=(
            "Vary Gaussian occupancy-estimation error while keeping reporting "
            "quantization fixed at 1 percentage point. Lower values mean more "
            "accurate station occupancy estimates."
        ),
        points=tuple(points),
    )


def build_packet_dropout_sweep(
    base_config: ExperimentConfig,
    dropout_percent_values: Iterable[float] = (0.0, 5.0, 10.0, 20.0, 40.0, 60.0, 80.0, 90.0, 100.0),
) -> SweepDefinition:
    points: list[SweepPoint] = []
    for dropout_percent in dropout_percent_values:
        dropout_percent = float(dropout_percent)
        if not 0.0 <= dropout_percent <= 100.0:
            raise ValueError("packet dropout values must be between 0 and 100")
        config = replace(
            base_config,
            name=f"{base_config.name}-packet-dropout-{_slug_number(dropout_percent)}",
            sensor=replace(
                base_config.sensor,
                dropout_probability=dropout_percent / 100.0,
            ),
        )
        points.append(
            SweepPoint(
                value=dropout_percent,
                label=f"{dropout_percent:g}% dropout",
                slug=f"dropout-{_slug_number(dropout_percent)}pct",
                config=config,
            )
        )
    return SweepDefinition(
        name="packet-dropout",
        title="Packet dropout",
        parameter="sensor_packet_dropout_percent",
        x_label="Sensor packet dropout (%)",
        description=(
            "Vary independent sensor-packet loss. When a packet is lost, the "
            "server continues using the last successfully received occupancy "
            "reading until a newer packet arrives."
        ),
        points=tuple(points),
    )



def build_hybrid_weight_sweep(
    base_config: ExperimentConfig,
    sensor_weight_values: Iterable[float] = (0.0, 0.25, 0.5, 0.6, 0.75, 1.0),
) -> SweepDefinition:
    """Vary how strongly Hybrid trusts live sensors versus history.

    ``sensor_weight`` is normalized together with ``historical_weight``.  This
    sweep fixes them to complementary values that sum to one, making the x-axis
    directly interpretable: 0 is pure historical pressure and 1 is pure sensor
    pressure.  With zero packet dropout those endpoints are useful sanity checks
    against the standalone Historical and Sensor policies.
    """

    points: list[SweepPoint] = []
    for sensor_weight in sensor_weight_values:
        sensor_weight = float(sensor_weight)
        if not 0.0 <= sensor_weight <= 1.0:
            raise ValueError("hybrid sensor weights must be between 0 and 1")
        history_weight = 1.0 - sensor_weight
        hybrid_factory = partial(
            HybridPolicy,
            HybridPolicyConfig(
                historical_weight=history_weight,
                sensor_weight=sensor_weight,
            ),
        )
        policies = (
            PolicySpec("Static", StaticPolicy),
            PolicySpec("Historical", HistoricalPolicy),
            PolicySpec("Sensor", SensorPolicy),
            PolicySpec("Hybrid", hybrid_factory),
        )
        points.append(
            SweepPoint(
                value=sensor_weight,
                label=(
                    f"{sensor_weight:.2f} sensor / {history_weight:.2f} history"
                ),
                slug=f"sensor-weight-{_slug_number(sensor_weight)}",
                config=replace(
                    base_config,
                    name=f"{base_config.name}-hybrid-weight-{_slug_number(sensor_weight)}",
                ),
                policies=policies,
            )
        )

    return SweepDefinition(
        name="hybrid-weight",
        title="Hybrid sensor/history weight",
        parameter="hybrid_sensor_weight",
        x_label="Hybrid sensor weight (history weight = 1 − sensor weight)",
        description=(
            "Vary how Hybrid combines normalized historical-demand pressure and "
            "live sensor pressure. A sensor weight of 0 is history-only; 1 is "
            "sensor-only; intermediate values blend the two signals."
        ),
        points=tuple(points),
    )

def build_core_sweeps(
    base_config: ExperimentConfig,
    *,
    fleet_values: Iterable[int] = (6, 8, 9, 10, 12, 14, 16, 18, 20),
    event_values: Iterable[float] = (0.0, 0.1, 0.25, 0.5, 1.0),
    sensor_error_values: Iterable[float] = (0.0, 5.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 75.0, 100.0),
    packet_dropout_values: Iterable[float] = (0.0, 5.0, 10.0, 20.0, 40.0, 60.0, 80.0, 90.0, 100.0),
    hybrid_sensor_weight_values: Iterable[float] = (0.0, 0.25, 0.5, 0.6, 0.75, 1.0),
) -> tuple[SweepDefinition, ...]:
    return (
        build_fleet_pressure_sweep(base_config, fleet_values),
        build_event_frequency_sweep(base_config, event_values),
        build_sensor_accuracy_sweep(base_config, sensor_error_values),
        build_packet_dropout_sweep(base_config, packet_dropout_values),
        build_hybrid_weight_sweep(base_config, hybrid_sensor_weight_values),
    )


def _with_sweep_metadata(
    frame: pd.DataFrame,
    definition: SweepDefinition,
    point: SweepPoint,
) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    output = frame.copy()
    output.insert(0, "sweep", definition.name)
    output.insert(1, "sweep_title", definition.title)
    output.insert(2, "parameter", definition.parameter)
    output.insert(3, "parameter_value", point.value)
    output.insert(4, "parameter_label", point.label)
    return output


def combine_sweep_batches(
    results: Iterable[tuple[SweepDefinition, SweepPoint, BatchResult]],
    *,
    baseline_policy: str = "Static",
) -> SweepSuiteResult:
    definitions: list[SweepDefinition] = []
    seen_definition_names: set[str] = set()
    runs: list[pd.DataFrame] = []
    summary: list[pd.DataFrame] = []
    paired_comparison: list[pd.DataFrame] = []
    paired_summary: list[pd.DataFrame] = []
    day_type: list[pd.DataFrame] = []
    event_runs: list[pd.DataFrame] = []

    for definition, point, batch in results:
        if batch.baseline_policy != baseline_policy:
            raise ValueError(
                f"batch baseline {batch.baseline_policy!r} does not match "
                f"suite baseline {baseline_policy!r}"
            )
        if definition.name not in seen_definition_names:
            definitions.append(definition)
            seen_definition_names.add(definition.name)

        runs.append(_with_sweep_metadata(batch.comparison, definition, point))
        summary.append(_with_sweep_metadata(batch.summary, definition, point))
        paired_comparison.append(
            _with_sweep_metadata(batch.paired_comparison, definition, point)
        )
        paired_summary.append(
            _with_sweep_metadata(batch.paired_summary, definition, point)
        )
        day_type.append(
            _with_sweep_metadata(batch.day_type_comparison, definition, point)
        )
        event_runs.append(_with_sweep_metadata(batch.event_runs, definition, point))

    def _concat(frames: list[pd.DataFrame]) -> pd.DataFrame:
        nonempty = [frame for frame in frames if not frame.empty]
        return pd.concat(nonempty, ignore_index=True) if nonempty else pd.DataFrame()

    return SweepSuiteResult(
        definitions=tuple(definitions),
        runs=_concat(runs),
        summary=_concat(summary),
        paired_comparison=_concat(paired_comparison),
        paired_summary=_concat(paired_summary),
        day_type_comparison=_concat(day_type),
        event_runs=_concat(event_runs),
        baseline_policy=baseline_policy,
    )
