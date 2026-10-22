from __future__ import annotations

import argparse
from pathlib import Path

from seebus_sim.config import default_experiment_config
from seebus_sim.experiments import (
    build_seeded_batch_configs,
    default_policy_specs,
    run_batch,
)
from seebus_sim.scenarios import scenario_names
from seebus_sim.reporting import (
    export_batch,
    load_batch_checkpoint,
    print_batch_summary,
    save_batch_dashboard,
    save_batch_paired_plot,
    save_batch_policy_plot,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run Static/Historical/Sensor/Hybrid on several independently "
            "generated but paired SeeBus simulation worlds."
        )
    )
    parser.add_argument(
        "--scenario",
        choices=scenario_names(),
        default="small",
        help="Network preset to use (default: small).",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=10,
        help="Number of independent worlds to simulate (default: 10).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help=(
            "Number of worker processes. Parallelism is by world, not inside "
            "SimPy (default: 1)."
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20261020,
        help="Master seed used to derive reproducible per-world seeds.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=("Output directory. Defaults to output/batch-<runs> for small "
              "or output/batch-<scenario>-<runs> otherwise."),
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help=(
            "Regenerate plots/HTML/console summary from an existing batch "
            "checkpoint without rerunning any simulations."
        ),
    )
    return parser


def _render_reports(result, output_dir: Path) -> list[str]:
    """Best-effort reporting. A broken chart must not invalidate the batch."""
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []

    artifacts = [
        (
            "interactive HTML report",
            lambda: save_batch_dashboard(result, output_dir / "report.html"),
        ),
        (
            "average-wait boxplot",
            lambda: save_batch_policy_plot(
                result.comparison,
                plots_dir / "average-wait-distribution.png",
            ),
        ),
        (
            "paired average-wait boxplot",
            lambda: save_batch_paired_plot(
                result.paired_comparison,
                plots_dir / "paired-average-wait.png",
                result.baseline_policy,
            ),
        ),
    ]

    for label, action in artifacts:
        try:
            action()
        except Exception as exc:  # reporting must never erase/re-run simulation work
            failures.append(f"{label}: {type(exc).__name__}: {exc}")

    return failures


def main() -> None:
    args = _parser().parse_args()
    if args.runs < 1:
        raise SystemExit("--runs must be >= 1")
    if args.workers < 1:
        raise SystemExit("--workers must be >= 1")

    output_dir = args.output or (
        Path("output") / f"batch-{args.runs}"
        if args.scenario == "small"
        else Path("output") / f"batch-{args.scenario}-{args.runs}"
    )

    if args.report_only:
        try:
            result = load_batch_checkpoint(output_dir)
        except FileNotFoundError as exc:
            raise SystemExit(str(exc)) from exc
        print(f"Loaded batch checkpoint from {output_dir}; no simulations will run.")
    else:
        base_config = default_experiment_config(args.scenario)
        policies = default_policy_specs()
        configs = build_seeded_batch_configs(
            base_config,
            args.runs,
            base_seed=args.seed,
        )

        print(
            f"Running {args.runs} {args.scenario} worlds x {len(policies)} policies "
            f"with {args.workers} worker(s)..."
        )

        result = run_batch(
            configs,
            policies,
            workers=args.workers,
            baseline_policy="Static",
            retain_experiments=False,
            progress=lambda completed, total: print(
                f"  completed {completed}/{total} worlds", flush=True
            ),
        )

        # Durable checkpoint FIRST. Everything below this point is disposable
        # reporting and can be regenerated later with --report-only.
        export_batch(
            result,
            output_dir,
            metadata={
                "master_seed": args.seed,
                "requested_runs": args.runs,
                "scenario": args.scenario,
                "routes": len(base_config.transit.routes),
                "stations": len(base_config.transit.station_ids),
                "buses": base_config.transit.bus_count,
            },
        )
        print(f"\nBatch checkpoint saved: {output_dir}")
        print(
            "Simulation results are safe. Reports can be regenerated with: "
            f"python .\\run_batch.py --runs {args.runs} --report-only"
        )

    failures = _render_reports(result, output_dir)
    print_batch_summary(result)

    print(f"\nBatch checkpoint: {output_dir}")
    if (output_dir / "report.html").exists():
        print(f"Interactive batch report: {output_dir / 'report.html'}")

    if failures:
        print("\nReporting completed with warnings; simulation/checkpoint data is intact:")
        for failure in failures:
            print(f"  - {failure}")
        print(
            "Fix the reporting issue and rerun with --report-only; the worlds "
            "do not need to be simulated again."
        )
    else:
        print(f"Aggregate CSVs and PNG plots: {output_dir}")


if __name__ == "__main__":
    main()
