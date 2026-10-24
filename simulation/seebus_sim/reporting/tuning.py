from __future__ import annotations

import json
from html import escape
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from seebus_sim.experiments.tuning import (
    TuningGridDefinition,
    build_historical_threshold_summary,
    build_hybrid_grid_summary,
)


def export_tuning_report_data(
    tuning_runs: pd.DataFrame,
    definition: TuningGridDefinition,
    output_dir: Path,
    *,
    metadata: dict | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    output_dir.mkdir(parents=True, exist_ok=True)
    historical = build_historical_threshold_summary(tuning_runs)
    hybrid = build_hybrid_grid_summary(tuning_runs)
    tuning_runs.to_csv(output_dir / "tuning_runs.csv", index=False)
    historical.to_csv(output_dir / "historical_threshold_summary.csv", index=False)
    hybrid.to_csv(output_dir / "hybrid_grid_summary.csv", index=False)
    manifest = {
        "format_version": 1,
        "target_load_fractions": list(definition.target_load_fractions),
        "sensor_weights": list(definition.sensor_weights),
    }
    if metadata:
        manifest.update(metadata)
    (output_dir / "tuning_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    return historical, hybrid


def _heatmap_matrix(frame: pd.DataFrame, value_column: str):
    thresholds = sorted(frame["target_load_fraction"].unique())
    weights = sorted(frame["sensor_weight"].unique())
    pivot = frame.pivot(
        index="target_load_fraction", columns="sensor_weight", values=value_column
    ).reindex(index=thresholds, columns=weights)
    return thresholds, weights, pivot.to_numpy(dtype=float)


def save_tuning_pngs(
    historical: pd.DataFrame,
    hybrid: pd.DataFrame,
    output_dir: Path,
) -> None:
    plots = output_dir / "plots"
    plots.mkdir(parents=True, exist_ok=True)

    if not historical.empty:
        fig, ax = plt.subplots(figsize=(7.5, 4.8))
        x = historical["target_load_fraction"].to_numpy(dtype=float)
        y = historical["average_wait_minutes_mean"].to_numpy(dtype=float)
        low = historical["average_wait_minutes_ci95_low"].to_numpy(dtype=float)
        high = historical["average_wait_minutes_ci95_high"].to_numpy(dtype=float)
        ax.errorbar(x, y, yerr=[y - low, high - y], marker="o", capsize=3)
        ax.set_title("Historical policy — demand threshold")
        ax.set_xlabel("Predicted backlog threshold (fraction of bus capacity)")
        ax.set_ylabel("Mean average wait (minutes)")
        ax.grid(True, alpha=0.25)
        fig.tight_layout()
        fig.savefig(plots / "historical-threshold.png", dpi=160)
        plt.close(fig)

    for value_column, filename, title, label in (
        (
            "average_wait_minutes_mean",
            "hybrid-average-wait-heatmap.png",
            "Hybrid tuning — mean average wait",
            "Minutes (lower is better)",
        ),
        (
            "benefit_vs_historical_minutes_mean",
            "hybrid-benefit-vs-historical-heatmap.png",
            "Hybrid tuning — benefit over same-threshold Historical",
            "Minutes saved (positive is better)",
        ),
        (
            "benefit_vs_sensor_minutes_mean",
            "hybrid-benefit-vs-sensor-heatmap.png",
            "Hybrid tuning — benefit over Sensor",
            "Minutes saved (positive is better)",
        ),
    ):
        if hybrid.empty:
            continue
        thresholds, weights, matrix = _heatmap_matrix(hybrid, value_column)
        fig, ax = plt.subplots(figsize=(8.2, 5.4))
        image = ax.imshow(matrix, aspect="auto", origin="lower")
        ax.set_xticks(np.arange(len(weights)), [f"{w:g}" for w in weights])
        ax.set_yticks(np.arange(len(thresholds)), [f"{t:g}" for t in thresholds])
        ax.set_xlabel("Hybrid sensor weight")
        ax.set_ylabel("Historical target-load fraction")
        ax.set_title(title)
        for row in range(matrix.shape[0]):
            for col in range(matrix.shape[1]):
                value = matrix[row, col]
                if np.isfinite(value):
                    ax.text(col, row, f"{value:.2f}", ha="center", va="center")
        cbar = fig.colorbar(image, ax=ax)
        cbar.set_label(label)
        fig.tight_layout()
        fig.savefig(plots / filename, dpi=160)
        plt.close(fig)


def _historical_figure(historical: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if not historical.empty:
        mean = historical["average_wait_minutes_mean"].astype(float)
        fig.add_scatter(
            x=historical["target_load_fraction"],
            y=mean,
            mode="lines+markers",
            name="Historical",
            error_y=dict(
                type="data",
                symmetric=False,
                array=(historical["average_wait_minutes_ci95_high"] - mean).tolist(),
                arrayminus=(mean - historical["average_wait_minutes_ci95_low"]).tolist(),
            ),
        )
    fig.update_layout(
        title="Historical threshold sensitivity",
        xaxis_title="Predicted backlog threshold (fraction of bus capacity)",
        yaxis_title="Mean average wait (minutes)",
    )
    return fig


def _heatmap_figure(
    hybrid: pd.DataFrame,
    value_column: str,
    *,
    title: str,
    colorbar_title: str,
) -> go.Figure:
    thresholds, weights, matrix = _heatmap_matrix(hybrid, value_column)
    text = [[f"{value:.2f}" if np.isfinite(value) else "" for value in row] for row in matrix]
    fig = go.Figure(
        data=go.Heatmap(
            x=weights,
            y=thresholds,
            z=matrix,
            text=text,
            texttemplate="%{text}",
            colorbar=dict(title=colorbar_title),
            hovertemplate=(
                "Sensor weight: %{x}<br>Historical threshold: %{y}<br>"
                + colorbar_title
                + ": %{z:.2f}<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        title=title,
        xaxis_title="Hybrid sensor weight",
        yaxis_title="Historical target-load fraction",
    )
    return fig


def save_tuning_dashboard(
    historical: pd.DataFrame,
    hybrid: pd.DataFrame,
    path: Path,
    *,
    runs: int,
    scenario: str,
    bus_count: int,
) -> None:
    figures = [
        _historical_figure(historical),
        _heatmap_figure(
            hybrid,
            "average_wait_minutes_mean",
            title="Hybrid mean average wait",
            colorbar_title="Minutes",
        ),
        _heatmap_figure(
            hybrid,
            "benefit_vs_historical_minutes_mean",
            title="Hybrid benefit over same-threshold Historical",
            colorbar_title="Minutes saved",
        ),
        _heatmap_figure(
            hybrid,
            "benefit_vs_sensor_minutes_mean",
            title="Hybrid benefit over Sensor",
            colorbar_title="Minutes saved",
        ),
    ]
    figure_html = []
    for index, fig in enumerate(figures):
        figure_html.append(
            fig.to_html(
                full_html=False,
                include_plotlyjs="cdn" if index == 0 else False,
                config={"responsive": True, "displaylogo": False},
            )
        )

    if not hybrid.empty:
        best = hybrid.loc[hybrid["average_wait_minutes_mean"].idxmin()]
        best_text = (
            f"Best observed Hybrid cell: threshold {best['target_load_fraction']:.2f}, "
            f"sensor weight {best['sensor_weight']:.2f}, "
            f"mean wait {best['average_wait_minutes_mean']:.2f} min."
        )
    else:
        best_text = "No Hybrid results available."

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>SeeBus policy tuning</title><style>
body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:0;background:#f4f6f8;color:#111827}}main{{max-width:1400px;margin:auto;padding:28px}}section{{background:white;border:1px solid #dbe1e8;border-radius:16px;padding:20px;margin:18px 0}}.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}}.chart{{min-width:0}}.muted{{color:#4b5563}}@media(max-width:900px){{.grid{{grid-template-columns:1fr}}}}
</style></head><body><main>
<h1>SeeBus policy tuning study</h1>
<p class=\"muted\">{runs} paired worlds · {escape(scenario)} scenario · {bus_count} shared buses. This is a focused sensitivity study, not part of the main one-factor-at-a-time suite.</p>
<section><h2>Historical threshold</h2><p>Tests whether the standalone Historical result depends strongly on the 35% predicted-load cutoff.</p><div class=\"chart\">{figure_html[0]}</div></section>
<section><h2>Hybrid tuning matrix</h2><p>{escape(best_text)} A broad low-wait region is stronger evidence than a single isolated optimum.</p><div class=\"grid\"><div class=\"chart\">{figure_html[1]}</div><div class=\"chart\">{figure_html[2]}</div><div class=\"chart\">{figure_html[3]}</div></div></section>
</main></body></html>""",
        encoding="utf-8",
    )
