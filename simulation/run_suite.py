from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path

from seebus_sim import SIMULATION_SCHEMA_VERSION
from seebus_sim.experiments import (
    build_core_sweeps,
    build_seeded_batch_configs,
    combine_sweep_batches,
    default_policy_specs,
    research_suite_base_config,
    run_batch,
)
from seebus_sim.reporting import (
    export_batch,
    export_sweep_suite,
    load_batch_checkpoint,
    save_sweep_historical_benefit_plot,
    save_sweep_metric_plot,
    save_sweep_paired_plot,
    save_sweep_perfect_sensor_degradation_plot,
    save_sweep_suite_dashboard,
)
from seebus_sim.scenarios import scenario_names


SWEEP_NAMES = (
    "fleet-pressure",
    "event-frequency",
    "sensor-accuracy",
    "packet-dropout",
    "hybrid-weight",
)
ROBUSTNESS_SWEEP_NAMES = {"sensor-accuracy", "packet-dropout"}


def _csv_numbers(text: str, *, integer: bool = False) -> tuple:
    values = []
    for raw in text.split(","):
        raw = raw.strip()
        if not raw:
            continue
        value = int(raw) if integer else float(raw)
        values.append(value)
    if not values:
        raise argparse.ArgumentTypeError("expected a comma-separated non-empty list")
    return tuple(values)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run one-factor-at-a-time SeeBus robustness sweeps. Every sweep point "
            "is a normal paired multi-world batch and is checkpointed separately."
        )
    )
    parser.add_argument(
        "--scenario",
        choices=scenario_names(),
        default="large",
        help="Network preset used by every sweep point (default: large).",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=30,
        help="Independent paired worlds per sweep point (default: 30).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Worker processes used inside each sweep-point batch (default: 1).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20261020,
        help="Master seed. The same run seeds are reused at every sweep point.",
    )
    parser.add_argument(
        "--sweep",
        action="append",
        choices=SWEEP_NAMES,
        help="Run only this sweep. Repeat to select several. Omit to run all five.",
    )
    parser.add_argument(
        "--fleet-values",
        default=None,
        help="Comma-separated shared-bus counts (default large: 6,8,9,10,12,14,16,18,20).",
    )
    parser.add_argument(
        "--event-values",
        default="0,0.1,0.25,0.5,1",
        help="Expected one-off station-events per network-day.",
    )
    parser.add_argument(
        "--sensor-error-values",
        default="0,5,10,20,30,40,50,60,75,100",
        help="Occupancy-estimation Gaussian error sigma in percentage points.",
    )
    parser.add_argument(
        "--packet-dropout-values",
        default="0,5,10,20,40,60,80,90,100",
        help="Sensor packet-dropout probabilities in percent.",
    )
    parser.add_argument(
        "--hybrid-sensor-weight-values",
        default="0,0.25,0.5,0.6,0.75,1",
        help=(
            "Hybrid live-sensor weights between 0 and 1. History weight is "
            "1 minus this value."
        ),
    )
    parser.add_argument(
        "--base-events-per-day",
        type=float,
        default=1.0,
        help="Central event rate used by non-event sweeps (default: 1/network-day).",
    )
    parser.add_argument(
        "--base-sensor-error",
        type=float,
        default=5.0,
        help="Central sensor error sigma in percentage points (default: 5).",
    )
    parser.add_argument(
        "--base-buses",
        type=int,
        default=None,
        help="Central fleet size for non-fleet sweeps (default: scenario fleet).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Suite output directory. Defaults to output/suite-<scenario>-<runs>.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rerun sweep points even if a valid batch checkpoint already exists.",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Regenerate suite CSV/plots/HTML from existing point checkpoints only.",
    )
    return parser


def _selected_definitions(args, base_config):
    if args.fleet_values is None:
        fleet_values = (6, 8, 9, 10, 12, 14, 16, 18, 20) if args.scenario == "large" else (2, 3, 4, 5)
    else:
        fleet_values = _csv_numbers(args.fleet_values, integer=True)

    definitions = build_core_sweeps(
        base_config,
        fleet_values=fleet_values,
        event_values=_csv_numbers(args.event_values),
        sensor_error_values=_csv_numbers(args.sensor_error_values),
        packet_dropout_values=_csv_numbers(args.packet_dropout_values),
        hybrid_sensor_weight_values=_csv_numbers(args.hybrid_sensor_weight_values),
    )
    selected = set(args.sweep or SWEEP_NAMES)
    return tuple(definition for definition in definitions if definition.name in selected)


def _checkpoint_matches(
    point_dir: Path,
    *,
    seed: int,
    runs: int,
    scenario: str,
    sweep_name: str,
    parameter_value: float,
) -> bool:
    manifest_path = point_dir / "batch_manifest.json"
    if not (point_dir / "runs.csv").exists() or not manifest_path.exists():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return (
        int(manifest.get("master_seed", -1)) == seed
        and int(manifest.get("requested_runs", -1)) == runs
        and str(manifest.get("scenario", "")) == scenario
        and str(manifest.get("sweep", "")) == sweep_name
        and int(manifest.get("simulation_schema_version", -1)) == SIMULATION_SCHEMA_VERSION
        and abs(float(manifest.get("parameter_value", float("nan"))) - parameter_value) < 1e-12
    )


def _print_suite_summary(result) -> None:
    print("\n=== SeeBus experiment suite ===")
    for definition in result.definitions:
        print(f"\n{definition.title}")
        frame = result.summary[result.summary["sweep"] == definition.name]
        if frame.empty:
            print("  no results")
            continue
        columns = [
            "parameter_label",
            "policy",
            "average_wait_minutes_mean",
            "p95_wait_minutes_mean",
            "service_rate_mean",
        ]
        display = frame[columns].copy()
        display["average_wait_minutes_mean"] = display["average_wait_minutes_mean"].map(
            lambda value: f"{value:.2f}"
        )
        display["p95_wait_minutes_mean"] = display["p95_wait_minutes_mean"].map(
            lambda value: f"{value:.2f}"
        )
        display["service_rate_mean"] = display["service_rate_mean"].map(
            lambda value: f"{value:.2%}"
        )
        print(display.to_string(index=False))


def main() -> None:
    args = _parser().parse_args()
    if args.runs < 1:
        raise SystemExit("--runs must be >= 1")
    if args.workers < 1:
        raise SystemExit("--workers must be >= 1")
    if args.base_sensor_error < 0:
        raise SystemExit("--base-sensor-error must be >= 0")
    if args.base_buses is not None and args.base_buses < 1:
        raise SystemExit("--base-buses must be >= 1")
    if args.force and args.report_only:
        raise SystemExit("--force and --report-only cannot be used together")

    base_config = research_suite_base_config(
        args.scenario,
        events_per_network_day=args.base_events_per_day,
        sensor_noise_std=args.base_sensor_error / 100.0,
    )
    if args.base_buses is not None:
        base_config = replace(
            base_config,
            transit=replace(base_config.transit, bus_count=args.base_buses),
        )

    definitions = _selected_definitions(args, base_config)
    if not definitions:
        raise SystemExit("no sweeps selected")

    output_dir = args.output or Path("output") / f"suite-{args.scenario}-{args.runs}"
    policies = default_policy_specs()
    collected = []

    total_points = sum(len(definition.points) for definition in definitions)
    point_number = 0

    for definition in definitions:
        print(f"\n=== {definition.title} ===")
        print(definition.description)
        for point in definition.points:
            point_number += 1
            point_dir = output_dir / definition.name / point.slug
            checkpoint = point_dir / "runs.csv"

            print(
                f"\n[{point_number}/{total_points}] {definition.name}: {point.label}"
            )

            checkpoint_matches = _checkpoint_matches(
                point_dir,
                seed=args.seed,
                runs=args.runs,
                scenario=args.scenario,
                sweep_name=definition.name,
                parameter_value=point.value,
            )

            if checkpoint_matches and not args.force:
                batch = load_batch_checkpoint(point_dir)
                print(f"  reused checkpoint: {point_dir}")
            elif args.report_only:
                raise SystemExit(
                    "Missing or incompatible checkpoint for "
                    f"{definition.name}/{point.slug}: {checkpoint}. "
                    "Use the same --runs/--seed/value arguments used to create it."
                )
            else:
                if checkpoint.exists() and not args.force:
                    print("  existing checkpoint metadata differs; rerunning this point")
                configs = build_seeded_batch_configs(
                    point.config,
                    args.runs,
                    base_seed=args.seed,
                )
                point_policies = list(point.policies) if point.policies is not None else policies
                batch = run_batch(
                    configs,
                    point_policies,
                    workers=args.workers,
                    baseline_policy="Static",
                    retain_experiments=False,
                    progress=lambda completed, total, prefix=f"  {point.label}": print(
                        f"{prefix}: {completed}/{total} worlds", flush=True
                    ),
                )
                export_batch(
                    batch,
                    point_dir,
                    metadata={
                        "master_seed": args.seed,
                        "requested_runs": args.runs,
                        "scenario": args.scenario,
                        "sweep": definition.name,
                        "sweep_parameter": definition.parameter,
                        "parameter_value": point.value,
                        "parameter_label": point.label,
                        "simulation_schema_version": SIMULATION_SCHEMA_VERSION,
                        "base_events_per_network_day": args.base_events_per_day,
                        "base_sensor_error_percent": args.base_sensor_error,
                        "base_bus_count": base_config.transit.bus_count,
                    },
                )
                print(f"  checkpoint saved: {point_dir}")

            collected.append((definition, point, batch))

    result = combine_sweep_batches(collected, baseline_policy="Static")

    # Durable suite-level aggregate checkpoint before any plotting.
    export_sweep_suite(
        result,
        output_dir,
        metadata={
            "scenario": args.scenario,
            "runs_per_point": args.runs,
            "master_seed": args.seed,
            "simulation_schema_version": SIMULATION_SCHEMA_VERSION,
            "base_bus_count": base_config.transit.bus_count,
            "base_events_per_network_day": args.base_events_per_day,
            "base_sensor_error_percent": args.base_sensor_error,
        },
    )
    print(f"\nSuite checkpoint saved: {output_dir}")

    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []

    for definition in definitions:
        plot_actions = [
            (
                f"{definition.name} average-wait plot",
                lambda d=definition: save_sweep_metric_plot(
                    result.summary,
                    d,
                    plots_dir / f"{d.name}-average-wait.png",
                    metric="average_wait_minutes",
                    y_label="Minutes",
                    title=f"{d.title} — mean average wait",
                ),
            ),
            (
                f"{definition.name} P95 plot",
                lambda d=definition: save_sweep_metric_plot(
                    result.summary,
                    d,
                    plots_dir / f"{d.name}-p95-wait.png",
                    metric="p95_wait_minutes",
                    y_label="Minutes",
                    title=f"{d.title} — mean P95 wait",
                ),
            ),
            (
                f"{definition.name} paired plot",
                lambda d=definition: save_sweep_paired_plot(
                    result.paired_summary,
                    d,
                    plots_dir / f"{d.name}-paired-wait.png",
                    baseline_policy=result.baseline_policy,
                ),
            ),
        ]
        if definition.name in ROBUSTNESS_SWEEP_NAMES:
            plot_actions.extend(
                [
                    (
                        f"{definition.name} benefit-vs-history plot",
                        lambda d=definition: save_sweep_historical_benefit_plot(
                            result.runs,
                            d,
                            plots_dir / f"{d.name}-benefit-vs-historical.png",
                        ),
                    ),
                    (
                        f"{definition.name} degradation-vs-perfect plot",
                        lambda d=definition: save_sweep_perfect_sensor_degradation_plot(
                            result.runs,
                            d,
                            plots_dir / f"{d.name}-degradation-vs-perfect.png",
                        ),
                    ),
                ]
            )

        for label, action in plot_actions:
            try:
                action()
            except Exception as exc:
                failures.append(f"{label}: {type(exc).__name__}: {exc}")

    try:
        save_sweep_suite_dashboard(result, output_dir / "report.html")
    except Exception as exc:
        failures.append(f"interactive suite report: {type(exc).__name__}: {exc}")

    _print_suite_summary(result)
    print(f"\nSuite output: {output_dir}")
    if (output_dir / "report.html").exists():
        print(f"Interactive report: {output_dir / 'report.html'}")

    if failures:
        print("\nReporting completed with warnings; all batch checkpoints are safe:")
        for failure in failures:
            print(f"  - {failure}")
        print("Rerun with --report-only after fixing reporting; simulations are reusable.")


if __name__ == "__main__":
    main()
