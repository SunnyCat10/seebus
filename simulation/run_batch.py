from __future__ import annotations

import argparse
from pathlib import Path

from seebus_sim.config import default_experiment_config
from seebus_sim.experiments import (
    build_seeded_batch_configs,
    default_policy_specs,
    run_batch,
)
from seebus_sim.reporting import (
    export_batch,
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
        help="Output directory. Defaults to output/batch-<runs>.",
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.runs < 1:
        raise SystemExit("--runs must be >= 1")
    if args.workers < 1:
        raise SystemExit("--workers must be >= 1")

    base_config = default_experiment_config()
    policies = default_policy_specs()
    configs = build_seeded_batch_configs(
        base_config,
        args.runs,
        base_seed=args.seed,
    )

    print(
        f"Running {args.runs} worlds x {len(policies)} policies "
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

    output_dir = args.output or Path("output") / f"batch-{args.runs}"
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    export_batch(result, output_dir)
    save_batch_dashboard(result, output_dir / "report.html")
    save_batch_policy_plot(result.comparison, plots_dir / "average-wait-distribution.png")
    save_batch_paired_plot(
        result.paired_comparison,
        plots_dir / "paired-average-wait.png",
        result.baseline_policy,
    )
    print_batch_summary(result)

    print(f"\nInteractive batch report: {output_dir / 'report.html'}")
    print(f"Aggregate CSVs and PNG plots: {output_dir}")


if __name__ == "__main__":
    main()
