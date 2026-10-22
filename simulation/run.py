from __future__ import annotations

import argparse
from pathlib import Path

from seebus_sim.config import default_experiment_config
from seebus_sim.experiments import default_policy_specs, run_experiment
from seebus_sim.reporting import (
    export_experiment,
    print_experiment_summary,
    save_benchmark_variation_plot,
    save_convergence_plot,
    save_daily_wait_plot,
    save_dashboard,
    save_policy_comparison_plot,
    save_profile_comparison_plot,
    save_station_wait_plot,
)
from seebus_sim.scenarios import scenario_names


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one SeeBus simulation world.")
    parser.add_argument(
        "--scenario",
        choices=scenario_names(),
        default="small",
        help="Network preset to use (default: small).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output directory. Defaults to output for small, output/<scenario> otherwise.",
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    config = default_experiment_config(args.scenario)
    policies = default_policy_specs()

    result = run_experiment(config, policies)

    output_dir = args.output or (
        Path("output") if args.scenario == "small" else Path("output") / args.scenario
    )
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    export_experiment(result, output_dir)
    save_dashboard(result, output_dir / "report.html")

    save_convergence_plot(result.demand.convergence, plots_dir / "demand-convergence.png")
    save_profile_comparison_plot(
        comparison=result.demand.comparison,
        station_id=config.station_ids[0],
        bucket_minutes=config.demand.bucket_minutes,
        path=plots_dir / "demand-profile.png",
    )
    save_benchmark_variation_plot(
        benchmark_demand=result.demand.benchmark_demand,
        station_id=config.station_ids[0],
        bucket_minutes=config.demand.bucket_minutes,
        path=plots_dir / "demand-variation.png",
    )
    save_policy_comparison_plot(result.comparison, plots_dir / "policy-comparison.png")

    for label, policy_result in result.policies.items():
        safe_label = label.lower().replace(" ", "-")
        save_daily_wait_plot(
            policy_result.daily_metrics,
            plots_dir / f"{safe_label}-daily-wait.png",
            title=f"{label} — waiting time by benchmark day",
        )
        save_station_wait_plot(
            policy_result.station_metrics,
            plots_dir / f"{safe_label}-station-wait.png",
            title=f"{label} — waiting time by station",
        )

    print_experiment_summary(result)
    print(f"\nInteractive report: {output_dir / 'report.html'}")
    print(f"Raw CSVs and PNG plots: {output_dir}")


if __name__ == "__main__":
    main()
