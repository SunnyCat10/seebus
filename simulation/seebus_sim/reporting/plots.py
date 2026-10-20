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
    station = (
        station.groupby("bucket", as_index=False)
        .agg(
            true_lambda=("true_lambda", "mean"),
            predicted_lambda=("predicted_lambda", "mean"),
        )
    )
    station["hour"] = station["bucket"] * bucket_minutes / 60.0

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(station["hour"], station["true_lambda"], label="Average hidden benchmark lambda")
    ax.plot(station["hour"], station["predicted_lambda"], label="Learned lambda", linestyle="--")
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


def save_policy_comparison_plot(comparison: pd.DataFrame, path: Path) -> None:
    x = range(len(comparison))
    width = 0.36
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(
        [value - width / 2 for value in x],
        comparison["average_wait_minutes"],
        width=width,
        label="Average wait",
    )
    ax.bar(
        [value + width / 2 for value in x],
        comparison["p95_wait_minutes"],
        width=width,
        label="P95 wait",
    )
    ax.set_xticks(list(x), comparison["policy"])
    ax.set_title("Passenger waiting time by policy")
    ax.set_ylabel("Minutes")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def save_daily_wait_plot(
    daily_metrics: pd.DataFrame,
    path: Path,
    title: str,
) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(
        daily_metrics["scenario_day"],
        daily_metrics["average_wait_minutes"],
        marker="o",
        label="Average wait",
    )
    ax.plot(
        daily_metrics["scenario_day"],
        daily_metrics["p95_wait_minutes"],
        marker="o",
        label="P95 wait",
    )
    ax.set_title(title)
    ax.set_xlabel("Benchmark day")
    ax.set_ylabel("Minutes")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def save_station_wait_plot(
    station_metrics: pd.DataFrame,
    path: Path,
    title: str,
) -> None:
    summary = (
        station_metrics.groupby("station_id", as_index=False)
        .agg(
            average_wait_minutes=("average_wait_minutes", "mean"),
            p95_wait_minutes=("p95_wait_minutes", "mean"),
        )
    )
    x = range(len(summary))
    width = 0.36
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(
        [value - width / 2 for value in x],
        summary["average_wait_minutes"],
        width=width,
        label="Average wait",
    )
    ax.bar(
        [value + width / 2 for value in x],
        summary["p95_wait_minutes"],
        width=width,
        label="P95 wait",
    )
    ax.set_xticks(list(x), summary["station_id"])
    ax.set_title(title)
    ax.set_ylabel("Minutes")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
