from pathlib import Path

from seebus_sim.config import default_experiment_config
from seebus_sim.experiments import PolicySpec, run_experiment
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
from seebus_sim.transit import StaticPolicy


def main() -> None:
    config = default_experiment_config()

    # Add future policies here. Every policy replays the same benchmark demand.
    policies = [
        PolicySpec("Static", StaticPolicy),
    ]

    result = run_experiment(config, policies)

    output_dir = Path("output")
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
