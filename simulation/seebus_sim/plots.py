from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from seebus_sim.demand.profile import GroundTruthDemandProfile


def save_convergence_plot(convergence: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(
        convergence["training_days"],
        convergence["mean_absolute_error"],
        marker="o",
        label="MAE",
    )
    ax.set_title("Demand predictor convergence")
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
    station["hour"] = station["minute_of_day"] / 60.0

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(station["hour"], station["true_lambda"], label="Hidden true lambda")
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
