from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path

from seebus_sim import SIMULATION_SCHEMA_VERSION
from seebus_sim.experiments import (
    TuningGridDefinition,
    annotate_tuning_runs,
    build_seeded_batch_configs,
    build_tuning_policy_specs,
    research_suite_base_config,
    run_batch,
)
from seebus_sim.reporting import (
    export_batch,
    export_tuning_report_data,
    load_batch_checkpoint,
    save_tuning_dashboard,
    save_tuning_pngs,
)
from seebus_sim.scenarios import scenario_names


def _csv_numbers(text: str) -> tuple[float, ...]:
    values = tuple(float(raw.strip()) for raw in text.split(",") if raw.strip())
    if not values:
        raise argparse.ArgumentTypeError("expected a comma-separated non-empty list")
    return values


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the focused 10-bus Historical-threshold × Hybrid-weight tuning study. "
            "All variants replay the same paired synthetic worlds."
        )
    )
    parser.add_argument("--scenario", choices=scenario_names(), default="large")
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--seed", type=int, default=20261024)
    parser.add_argument("--buses", type=int, default=10)
    parser.add_argument(
        "--threshold-values",
        default="0.15,0.25,0.35,0.5,0.7",
        help="Historical predicted-load thresholds as fractions of bus capacity.",
    )
    parser.add_argument(
        "--sensor-weight-values",
        default="0.25,0.5,0.6,0.75",
        help="Hybrid sensor weights; history weight is 1 minus the value.",
    )
    parser.add_argument("--base-events-per-day", type=float, default=1.0)
    parser.add_argument("--base-sensor-error", type=float, default=5.0)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    return parser


def _checkpoint_matches(path: Path, args, definition: TuningGridDefinition) -> bool:
    manifest_path = path / "batch_manifest.json"
    if not (path / "runs.csv").exists() or not manifest_path.exists():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return (
        manifest.get("experiment_type") == "policy-tuning-grid"
        and int(manifest.get("simulation_schema_version", -1)) == SIMULATION_SCHEMA_VERSION
        and int(manifest.get("master_seed", -1)) == args.seed
        and int(manifest.get("requested_runs", -1)) == args.runs
        and str(manifest.get("scenario", "")) == args.scenario
        and int(manifest.get("bus_count", -1)) == args.buses
        and abs(float(manifest.get("base_events_per_network_day", -1.0)) - args.base_events_per_day) < 1e-12
        and abs(float(manifest.get("base_sensor_error_percent", -1.0)) - args.base_sensor_error) < 1e-12
        and list(manifest.get("target_load_fractions", [])) == list(definition.target_load_fractions)
        and list(manifest.get("sensor_weights", [])) == list(definition.sensor_weights)
    )


def main() -> None:
    args = _parser().parse_args()
    if args.runs < 1 or args.workers < 1 or args.buses < 1:
        raise SystemExit("--runs, --workers, and --buses must be >= 1")
    if args.force and args.report_only:
        raise SystemExit("--force and --report-only cannot be used together")

    definition = TuningGridDefinition(
        target_load_fractions=_csv_numbers(args.threshold_values),
        sensor_weights=_csv_numbers(args.sensor_weight_values),
    )
    base = research_suite_base_config(
        args.scenario,
        events_per_network_day=args.base_events_per_day,
        sensor_noise_std=args.base_sensor_error / 100.0,
    )
    base = replace(base, transit=replace(base.transit, bus_count=args.buses))
    policies, policy_metadata = build_tuning_policy_specs(definition)

    output_dir = args.output or Path("output") / f"tuning-{args.scenario}-{args.buses}b-{args.runs}"
    checkpoint_ok = _checkpoint_matches(output_dir, args, definition)
    if checkpoint_ok and not args.force:
        batch = load_batch_checkpoint(output_dir)
        print(f"Reused tuning checkpoint: {output_dir}")
    elif args.report_only:
        raise SystemExit("Missing or incompatible tuning checkpoint.")
    else:
        configs = build_seeded_batch_configs(base, args.runs, base_seed=args.seed)
        print(
            f"Running {len(policies)} policy variants across {args.runs} paired worlds "
            f"at {args.buses} buses..."
        )
        batch = run_batch(
            configs,
            policies,
            workers=args.workers,
            baseline_policy="Static",
            retain_experiments=False,
            progress=lambda completed, total: print(
                f"  {completed}/{total} worlds", flush=True
            ),
        )
        export_batch(
            batch,
            output_dir,
            metadata={
                "experiment_type": "policy-tuning-grid",
                "simulation_schema_version": SIMULATION_SCHEMA_VERSION,
                "master_seed": args.seed,
                "requested_runs": args.runs,
                "scenario": args.scenario,
                "bus_count": args.buses,
                "target_load_fractions": list(definition.target_load_fractions),
                "sensor_weights": list(definition.sensor_weights),
                "base_events_per_network_day": args.base_events_per_day,
                "base_sensor_error_percent": args.base_sensor_error,
            },
        )
        print(f"Checkpoint saved: {output_dir}")

    tuning_runs = annotate_tuning_runs(batch, policy_metadata)
    historical, hybrid = export_tuning_report_data(
        tuning_runs,
        definition,
        output_dir,
        metadata={
            "simulation_schema_version": SIMULATION_SCHEMA_VERSION,
            "scenario": args.scenario,
            "bus_count": args.buses,
            "runs": args.runs,
            "master_seed": args.seed,
        },
    )
    save_tuning_pngs(historical, hybrid, output_dir)
    save_tuning_dashboard(
        historical,
        hybrid,
        output_dir / "report.html",
        runs=args.runs,
        scenario=args.scenario,
        bus_count=args.buses,
    )

    print("\n=== Tuning summary ===")
    if not historical.empty:
        best_h = historical.loc[historical["average_wait_minutes_mean"].idxmin()]
        print(
            f"Best Historical threshold: {best_h['target_load_fraction']:.2f} "
            f"→ {best_h['average_wait_minutes_mean']:.2f} min mean wait"
        )
    if not hybrid.empty:
        best = hybrid.loc[hybrid["average_wait_minutes_mean"].idxmin()]
        print(
            f"Best Hybrid cell: threshold={best['target_load_fraction']:.2f}, "
            f"sensor weight={best['sensor_weight']:.2f} "
            f"→ {best['average_wait_minutes_mean']:.2f} min mean wait"
        )
    print(f"Report: {output_dir / 'report.html'}")


if __name__ == "__main__":
    main()
