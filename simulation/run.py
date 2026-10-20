from pathlib import Path

from seebus_sim.experiment import run_demand_experiment
from seebus_sim.plots import (
    save_benchmark_variation_plot,
    save_convergence_plot,
    save_profile_comparison_plot,
)


if __name__ == "__main__":
    station_ids = ["station-a", "station-b", "station-c", "station-d"]

    result = run_demand_experiment(
        station_ids=station_ids,
        training_days=14,
        benchmark_days=30,
        bucket_minutes=15,
        seed=42,
        daily_noise_std=0.12,
        event_probability=0.07,
    )

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    result.training_demand.to_csv(output_dir / "training_demand.csv", index=False)
    result.benchmark_demand.to_csv(output_dir / "benchmark_demand.csv", index=False)
    result.history.to_csv(output_dir / "training_history.csv", index=False)
    result.comparison.to_csv(output_dir / "prediction_comparison.csv", index=False)
    result.convergence.to_csv(output_dir / "convergence.csv", index=False)
    result.event_summary.to_csv(output_dir / "events.csv", index=False)

    save_convergence_plot(
        result.convergence,
        output_dir / "convergence.png",
    )
    save_profile_comparison_plot(
        comparison=result.comparison,
        station_id=station_ids[0],
        bucket_minutes=result.bucket_minutes,
        path=output_dir / "station-a-profile.png",
    )
    save_benchmark_variation_plot(
        benchmark_demand=result.benchmark_demand,
        station_id=station_ids[0],
        bucket_minutes=result.bucket_minutes,
        path=output_dir / "station-a-benchmark-variation.png",
    )

    print("\n=== SeeBus richer demand-learning experiment ===")
    print(f"Training days:  {result.training_days}")
    print(f"Benchmark days: {result.benchmark_days}")
    print(f"Bucket size:    {result.bucket_minutes} minutes")
    print(
        "Benchmark lambda MAE: "
        f"{result.mean_absolute_error:.3f} passengers/min"
    )

    print("\nHidden station archetypes:")
    for station_id in station_ids:
        print(f"  {station_id}: {result.profile.station_types[station_id]}")

    print("\nConvergence on fixed unseen benchmark:")
    print(result.convergence.to_string(index=False))

    benchmark_events = result.event_summary[
        result.event_summary["split"] == "benchmark"
    ]
    print(f"\nOne-off benchmark events: {len(benchmark_events)}")
    if not benchmark_events.empty:
        print(
            benchmark_events[
                [
                    "scenario_day",
                    "weekday",
                    "station_id",
                    "start_minute",
                    "duration_minutes",
                    "event_multiplier",
                ]
            ]
            .head(10)
            .to_string(index=False)
        )

    print("\nReplayable benchmark rows:", len(result.benchmark_demand))
    print("\nWrote files to output/:")
    for path in sorted(output_dir.iterdir()):
        print(f"  {path.name}")
