from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def save_convergence_plot(convergence: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(
        convergence["training_days"],
        convergence["mean_absolute_error"],
        marker="o",
        label="Benchmark MAE",
    )
    ax.set_title("Demand predictor convergence on unseen benchmark days")
    ax.set_xlabel("Training days")
    ax.set_ylabel("Lambda prediction error (passengers/min)")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def save_profile_comparison_plot(
    comparison: pd.DataFrame,
    station_id: str,
    bucket_minutes: int,
    path: Path,
) -> None:
    station = comparison[comparison["station_id"] == station_id].copy()

    # The hidden lambda now changes from day to day. Plot its average benchmark
    # value and the stationary learned model to show the model's approximation.
    station = (
        station.groupby("bucket", as_index=False)
        .agg(
            true_lambda=("true_lambda", "mean"),
            predicted_lambda=("predicted_lambda", "mean"),
        )
    )
    station["minute_of_day"] = station["bucket"] * bucket_minutes
    station["hour"] = station["minute_of_day"] / 60.0

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(
        station["hour"],
        station["true_lambda"],
        label="Average hidden benchmark lambda",
    )
    ax.plot(
        station["hour"],
        station["predicted_lambda"],
        label="Learned lambda",
        linestyle="--",
    )
    ax.set_title(f"Learned demand profile — {station_id}")
    ax.set_xlabel("Hour of day")
    ax.set_ylabel("Passengers/min")
    ax.set_xlim(0, 24)
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def save_benchmark_variation_plot(
    benchmark_demand: pd.DataFrame,
    station_id: str,
    bucket_minutes: int,
    path: Path,
    days_to_plot: int = 7,
) -> None:
    station = benchmark_demand[
        (benchmark_demand["station_id"] == station_id)
        & (benchmark_demand["scenario_day"] <= days_to_plot)
    ].copy()

    bucketed = (
        station.groupby(["scenario_day", "weekday", "bucket"], as_index=False)
        .agg(true_lambda=("true_lambda", "mean"))
    )
    bucketed["hour"] = bucketed["bucket"] * bucket_minutes / 60.0

    fig, ax = plt.subplots(figsize=(9, 4.5))
    for (scenario_day, weekday), day_frame in bucketed.groupby(
        ["scenario_day", "weekday"], sort=True
    ):
        ax.plot(
            day_frame["hour"],
            day_frame["true_lambda"],
            alpha=0.75,
            label=f"Day {scenario_day} ({weekday[:3]})",
        )

    ax.set_title(f"Hidden day-to-day demand variation — {station_id}")
    ax.set_xlabel("Hour of day")
    ax.set_ylabel("True lambda (passengers/min)")
    ax.set_xlim(0, 24)
    ax.grid(True, alpha=0.25)
    ax.legend(ncol=2, fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
