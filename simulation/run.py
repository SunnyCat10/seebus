from pathlib import Path

from seebus_sim.experiment import run_demand_experiment
from seebus_sim.plots import (
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
    )

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    result.training_demand.to_csv(output_dir / "training_demand.csv", index=False)
    result.benchmark_demand.to_csv(output_dir / "benchmark_demand.csv", index=False)
    result.history.to_csv(output_dir / "training_history.csv", index=False)
    result.comparison.to_csv(output_dir / "prediction_comparison.csv", index=False)
    result.convergence.to_csv(output_dir / "convergence.csv", index=False)

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

    print("\n=== SeeBus demand-learning experiment ===")
    print(f"Training days:  {result.training_days}")
    print(f"Benchmark days: {result.benchmark_days}")
    print(f"Bucket size:    {result.bucket_minutes} minutes")
    print(
        "Final lambda MAE: "
        f"{result.mean_absolute_error:.3f} passengers/min"
    )

    print("\nConvergence:")
    print(result.convergence.to_string(index=False))

    sample = result.comparison[
        result.comparison["bucket"].isin([28, 32, 36, 68, 72])
    ]

    print("\nSample learned demand:")
    print(
        sample[
            [
                "station_id",
                "bucket",
                "true_lambda",
                "predicted_lambda",
                "abs_error",
            ]
        ]
        .head(16)
        .to_string(index=False)
    )

    print("\nReplayable benchmark rows:", len(result.benchmark_demand))
    print("\nWrote files to output/:")
    for path in sorted(output_dir.iterdir()):
        print(f"  {path.name}")
