from __future__ import annotations

import json
import math
from html import escape
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go

from seebus_sim.experiments.sweeps import SweepDefinition, SweepSuiteResult


ROBUSTNESS_SWEEPS = {"sensor-accuracy", "packet-dropout"}


def export_sweep_suite(
    result: SweepSuiteResult,
    output_dir: Path,
    *,
    metadata: dict | None = None,
) -> None:
    """Write compact, report-ready long-form tables for an experiment suite."""

    output_dir.mkdir(parents=True, exist_ok=True)
    result.runs.to_csv(output_dir / "suite_runs.csv", index=False)
    result.summary.to_csv(output_dir / "suite_summary.csv", index=False)
    result.paired_comparison.to_csv(
        output_dir / "suite_paired_comparison.csv", index=False
    )
    result.paired_summary.to_csv(output_dir / "suite_paired_summary.csv", index=False)
    result.day_type_comparison.to_csv(
        output_dir / "suite_day_type_comparison.csv", index=False
    )
    result.event_runs.to_csv(output_dir / "suite_event_runs.csv", index=False)

    benefit_frames: list[pd.DataFrame] = []
    degradation_frames: list[pd.DataFrame] = []
    for definition in result.definitions:
        if definition.name not in ROBUSTNESS_SWEEPS:
            continue
        benefit = build_historical_benefit_summary(result.runs, definition)
        degradation = build_perfect_sensor_degradation_summary(result.runs, definition)
        if not benefit.empty:
            benefit_frames.append(benefit)
        if not degradation.empty:
            degradation_frames.append(degradation)

    if benefit_frames:
        pd.concat(benefit_frames, ignore_index=True).to_csv(
            output_dir / "suite_benefit_vs_historical.csv", index=False
        )
    if degradation_frames:
        pd.concat(degradation_frames, ignore_index=True).to_csv(
            output_dir / "suite_degradation_vs_perfect_sensor.csv", index=False
        )

    manifest = {
        "format_version": 1,
        "baseline_policy": result.baseline_policy,
        "sweeps": [
            {
                "name": definition.name,
                "title": definition.title,
                "parameter": definition.parameter,
                "x_label": definition.x_label,
                "description": definition.description,
                "values": [point.value for point in definition.points],
                "labels": [point.label for point in definition.points],
            }
            for definition in result.definitions
        ],
    }
    if metadata:
        manifest.update(metadata)
    (output_dir / "suite_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _metric_columns(metric: str) -> tuple[str, str, str]:
    return (
        f"{metric}_mean",
        f"{metric}_ci95_low",
        f"{metric}_ci95_high",
    )


def _mean_std_ci(values: pd.Series) -> tuple[float, float, float, float]:
    clean = values.dropna().astype(float)
    if clean.empty:
        return math.nan, math.nan, math.nan, math.nan
    mean = float(clean.mean())
    if len(clean) == 1:
        return mean, 0.0, mean, mean
    std = float(clean.std(ddof=1))
    margin = 1.96 * std / math.sqrt(len(clean))
    return mean, std, mean - margin, mean + margin


def build_historical_benefit_summary(
    runs: pd.DataFrame,
    definition: SweepDefinition,
    *,
    policies: tuple[str, ...] = ("Sensor", "Hybrid"),
) -> pd.DataFrame:
    """Paired minutes saved versus Historical for robustness sweeps.

    Positive values are better: ``Historical wait - policy wait``. The pairing
    is world-by-world, so random demand variation largely cancels out.
    """

    frame = runs[runs["sweep"] == definition.name].copy()
    if frame.empty:
        return pd.DataFrame()

    required = {"run", "parameter_value", "parameter_label", "policy", "average_wait_minutes"}
    if not required <= set(frame.columns):
        return pd.DataFrame()

    pivot = frame.pivot_table(
        index=["run", "parameter_value", "parameter_label"],
        columns="policy",
        values="average_wait_minutes",
        aggfunc="first",
    ).reset_index()
    if "Historical" not in pivot.columns:
        return pd.DataFrame()

    rows: list[dict] = []
    for policy in policies:
        if policy not in pivot.columns:
            continue
        paired = pivot[
            ["run", "parameter_value", "parameter_label", "Historical", policy]
        ].dropna()
        if paired.empty:
            continue
        paired = paired.copy()
        paired["benefit_minutes"] = paired["Historical"] - paired[policy]
        for (value, label), group in paired.groupby(
            ["parameter_value", "parameter_label"], sort=True
        ):
            mean, std, low, high = _mean_std_ci(group["benefit_minutes"])
            rows.append(
                {
                    "sweep": definition.name,
                    "sweep_title": definition.title,
                    "parameter_value": float(value),
                    "parameter_label": str(label),
                    "policy": policy,
                    "runs": int(group["run"].nunique()),
                    "benefit_minutes_mean": mean,
                    "benefit_minutes_std": std,
                    "benefit_minutes_ci95_low": low,
                    "benefit_minutes_ci95_high": high,
                }
            )
    return pd.DataFrame(rows)


def build_perfect_sensor_degradation_summary(
    runs: pd.DataFrame,
    definition: SweepDefinition,
    *,
    policies: tuple[str, ...] = ("Sensor", "Hybrid"),
) -> pd.DataFrame:
    """Paired wait increase relative to the sweep's zero-impairment point.

    Positive values mean the imperfect sensor/network made waiting worse. This
    view intentionally omits Static/Historical because they do not depend on
    sensor quality and would therefore be flat at zero.
    """

    frame = runs[runs["sweep"] == definition.name].copy()
    if frame.empty:
        return pd.DataFrame()
    if not any(abs(float(point.value)) < 1e-12 for point in definition.points):
        return pd.DataFrame()

    rows: list[dict] = []
    labels = (
        frame[["parameter_value", "parameter_label"]]
        .drop_duplicates()
        .set_index("parameter_value")["parameter_label"]
        .to_dict()
    )

    for policy in policies:
        policy_frame = frame[frame["policy"] == policy][
            ["run", "parameter_value", "average_wait_minutes"]
        ]
        if policy_frame.empty:
            continue
        pivot = policy_frame.pivot_table(
            index="run",
            columns="parameter_value",
            values="average_wait_minutes",
            aggfunc="first",
        )
        zero_columns = [column for column in pivot.columns if abs(float(column)) < 1e-12]
        if not zero_columns:
            continue
        baseline = pivot[zero_columns[0]]

        for value in sorted(pivot.columns, key=float):
            paired = pd.concat([baseline, pivot[value]], axis=1).dropna()
            if paired.empty:
                continue
            paired.columns = ["baseline", "current"]
            delta = paired["current"] - paired["baseline"]
            mean, std, low, high = _mean_std_ci(delta)
            rows.append(
                {
                    "sweep": definition.name,
                    "sweep_title": definition.title,
                    "parameter_value": float(value),
                    "parameter_label": str(labels.get(value, value)),
                    "policy": policy,
                    "runs": int(len(paired)),
                    "degradation_minutes_mean": mean,
                    "degradation_minutes_std": std,
                    "degradation_minutes_ci95_low": low,
                    "degradation_minutes_ci95_high": high,
                }
            )
    return pd.DataFrame(rows)


def save_sweep_metric_plot(
    summary: pd.DataFrame,
    definition: SweepDefinition,
    path: Path,
    *,
    metric: str = "average_wait_minutes",
    y_label: str = "Minutes",
    title: str | None = None,
) -> None:
    frame = summary[summary["sweep"] == definition.name].copy()
    if frame.empty:
        return

    mean_col, low_col, high_col = _metric_columns(metric)
    fig, ax = plt.subplots(figsize=(8.5, 5))

    for policy, policy_frame in frame.groupby("policy", sort=False):
        policy_frame = policy_frame.sort_values("parameter_value")
        x = policy_frame["parameter_value"].astype(float).to_numpy()
        y = policy_frame[mean_col].astype(float).to_numpy()
        low = policy_frame[low_col].astype(float).to_numpy()
        high = policy_frame[high_col].astype(float).to_numpy()
        yerr = [y - low, high - y]
        ax.errorbar(x, y, yerr=yerr, marker="o", capsize=3, label=str(policy))

    ax.set_title(title or f"{definition.title} — {metric.replace('_', ' ')}")
    ax.set_xlabel(definition.x_label)
    ax.set_ylabel(y_label)
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def save_sweep_paired_plot(
    paired_summary: pd.DataFrame,
    definition: SweepDefinition,
    path: Path,
    *,
    baseline_policy: str,
) -> None:
    frame = paired_summary[paired_summary["sweep"] == definition.name].copy()
    if frame.empty:
        return

    mean_col = "average_wait_minutes_delta_mean"
    low_col = "average_wait_minutes_delta_ci95_low"
    high_col = "average_wait_minutes_delta_ci95_high"
    fig, ax = plt.subplots(figsize=(8.5, 5))

    for policy, policy_frame in frame.groupby("policy", sort=False):
        policy_frame = policy_frame.sort_values("parameter_value")
        x = policy_frame["parameter_value"].astype(float).to_numpy()
        y = policy_frame[mean_col].astype(float).to_numpy()
        low = policy_frame[low_col].astype(float).to_numpy()
        high = policy_frame[high_col].astype(float).to_numpy()
        yerr = [y - low, high - y]
        ax.errorbar(x, y, yerr=yerr, marker="o", capsize=3, label=str(policy))

    ax.axhline(0.0, linestyle="--", linewidth=1)
    ax.set_title(f"{definition.title} — average-wait improvement vs {baseline_policy}")
    ax.set_xlabel(definition.x_label)
    ax.set_ylabel("Minutes (negative is better)")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def save_sweep_historical_benefit_plot(
    runs: pd.DataFrame,
    definition: SweepDefinition,
    path: Path,
) -> None:
    summary = build_historical_benefit_summary(runs, definition)
    if summary.empty:
        return

    fig, ax = plt.subplots(figsize=(8.5, 5))
    for policy, policy_frame in summary.groupby("policy", sort=False):
        policy_frame = policy_frame.sort_values("parameter_value")
        x = policy_frame["parameter_value"].astype(float).to_numpy()
        y = policy_frame["benefit_minutes_mean"].astype(float).to_numpy()
        low = policy_frame["benefit_minutes_ci95_low"].astype(float).to_numpy()
        high = policy_frame["benefit_minutes_ci95_high"].astype(float).to_numpy()
        ax.errorbar(
            x,
            y,
            yerr=[y - low, high - y],
            marker="o",
            capsize=3,
            label=str(policy),
        )

    ax.axhline(0.0, linestyle="--", linewidth=1)
    ax.set_title(f"{definition.title} — benefit over Historical")
    ax.set_xlabel(definition.x_label)
    ax.set_ylabel("Minutes saved vs Historical (positive is better)")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def save_sweep_perfect_sensor_degradation_plot(
    runs: pd.DataFrame,
    definition: SweepDefinition,
    path: Path,
) -> None:
    summary = build_perfect_sensor_degradation_summary(runs, definition)
    if summary.empty:
        return

    fig, ax = plt.subplots(figsize=(8.5, 5))
    for policy, policy_frame in summary.groupby("policy", sort=False):
        policy_frame = policy_frame.sort_values("parameter_value")
        x = policy_frame["parameter_value"].astype(float).to_numpy()
        y = policy_frame["degradation_minutes_mean"].astype(float).to_numpy()
        low = policy_frame["degradation_minutes_ci95_low"].astype(float).to_numpy()
        high = policy_frame["degradation_minutes_ci95_high"].astype(float).to_numpy()
        ax.errorbar(
            x,
            y,
            yerr=[y - low, high - y],
            marker="o",
            capsize=3,
            label=str(policy),
        )

    ax.axhline(0.0, linestyle="--", linewidth=1)
    ax.set_title(f"{definition.title} — degradation vs perfect sensing")
    ax.set_xlabel(definition.x_label)
    ax.set_ylabel("Additional wait vs 0% impairment (positive is worse)")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _plotly_metric_figure(
    summary: pd.DataFrame,
    definition: SweepDefinition,
    *,
    metric: str,
    title: str,
    y_title: str,
) -> go.Figure:
    frame = summary[summary["sweep"] == definition.name].copy()
    mean_col, low_col, high_col = _metric_columns(metric)
    fig = go.Figure()

    for policy, policy_frame in frame.groupby("policy", sort=False):
        policy_frame = policy_frame.sort_values("parameter_value")
        mean = policy_frame[mean_col].astype(float)
        fig.add_scatter(
            x=policy_frame["parameter_value"],
            y=mean,
            mode="lines+markers",
            name=str(policy),
            error_y=dict(
                type="data",
                symmetric=False,
                array=(policy_frame[high_col].astype(float) - mean).tolist(),
                arrayminus=(mean - policy_frame[low_col].astype(float)).tolist(),
                thickness=1,
                width=3,
            ),
            customdata=policy_frame[["parameter_label"]].to_numpy(),
            hovertemplate=(
                "%{fullData.name}<br>%{customdata[0]}<br>"
                + y_title
                + ": %{y:.2f}<extra></extra>"
            ),
        )

    fig.update_layout(
        title=title,
        xaxis_title=definition.x_label,
        yaxis_title=y_title,
        margin=dict(l=55, r=25, t=55, b=50),
    )
    return fig


def _plotly_paired_figure(
    paired: pd.DataFrame,
    definition: SweepDefinition,
    baseline_policy: str,
) -> go.Figure:
    frame = paired[paired["sweep"] == definition.name].copy()
    fig = go.Figure()

    for policy, policy_frame in frame.groupby("policy", sort=False):
        policy_frame = policy_frame.sort_values("parameter_value")
        mean = policy_frame["average_wait_minutes_delta_mean"].astype(float)
        fig.add_scatter(
            x=policy_frame["parameter_value"],
            y=mean,
            mode="lines+markers",
            name=str(policy),
            error_y=dict(
                type="data",
                symmetric=False,
                array=(
                    policy_frame["average_wait_minutes_delta_ci95_high"].astype(float)
                    - mean
                ).tolist(),
                arrayminus=(
                    mean
                    - policy_frame["average_wait_minutes_delta_ci95_low"].astype(float)
                ).tolist(),
                thickness=1,
                width=3,
            ),
            customdata=policy_frame[["parameter_label"]].to_numpy(),
            hovertemplate=(
                "%{fullData.name}<br>%{customdata[0]}<br>"
                "Δ wait: %{y:.2f} min<extra></extra>"
            ),
        )

    fig.add_hline(y=0.0, line_dash="dash")
    fig.update_layout(
        title=f"Paired average-wait difference vs {baseline_policy}",
        xaxis_title=definition.x_label,
        yaxis_title="Minutes (negative is better)",
        margin=dict(l=55, r=25, t=55, b=50),
    )
    return fig


def _plotly_historical_benefit_figure(
    runs: pd.DataFrame,
    definition: SweepDefinition,
) -> go.Figure:
    summary = build_historical_benefit_summary(runs, definition)
    fig = go.Figure()

    for policy, policy_frame in summary.groupby("policy", sort=False):
        policy_frame = policy_frame.sort_values("parameter_value")
        mean = policy_frame["benefit_minutes_mean"].astype(float)
        fig.add_scatter(
            x=policy_frame["parameter_value"],
            y=mean,
            mode="lines+markers",
            name=str(policy),
            error_y=dict(
                type="data",
                symmetric=False,
                array=(
                    policy_frame["benefit_minutes_ci95_high"].astype(float) - mean
                ).tolist(),
                arrayminus=(
                    mean - policy_frame["benefit_minutes_ci95_low"].astype(float)
                ).tolist(),
                thickness=1,
                width=3,
            ),
            customdata=policy_frame[["parameter_label"]].to_numpy(),
            hovertemplate=(
                "%{fullData.name}<br>%{customdata[0]}<br>"
                "Minutes saved vs Historical: %{y:.2f}<extra></extra>"
            ),
        )

    fig.add_hline(y=0.0, line_dash="dash")
    fig.update_layout(
        title="Benefit over Historical",
        xaxis_title=definition.x_label,
        yaxis_title="Minutes saved (positive is better)",
        margin=dict(l=55, r=25, t=55, b=50),
    )
    return fig


def _plotly_perfect_sensor_degradation_figure(
    runs: pd.DataFrame,
    definition: SweepDefinition,
) -> go.Figure:
    summary = build_perfect_sensor_degradation_summary(runs, definition)
    fig = go.Figure()

    for policy, policy_frame in summary.groupby("policy", sort=False):
        policy_frame = policy_frame.sort_values("parameter_value")
        mean = policy_frame["degradation_minutes_mean"].astype(float)
        fig.add_scatter(
            x=policy_frame["parameter_value"],
            y=mean,
            mode="lines+markers",
            name=str(policy),
            error_y=dict(
                type="data",
                symmetric=False,
                array=(
                    policy_frame["degradation_minutes_ci95_high"].astype(float) - mean
                ).tolist(),
                arrayminus=(
                    mean - policy_frame["degradation_minutes_ci95_low"].astype(float)
                ).tolist(),
                thickness=1,
                width=3,
            ),
            customdata=policy_frame[["parameter_label"]].to_numpy(),
            hovertemplate=(
                "%{fullData.name}<br>%{customdata[0]}<br>"
                "Additional wait vs 0% impairment: %{y:.2f} min<extra></extra>"
            ),
        )

    fig.add_hline(y=0.0, line_dash="dash")
    fig.update_layout(
        title="Degradation vs perfect sensing / communication",
        xaxis_title=definition.x_label,
        yaxis_title="Additional wait vs 0% impairment (minutes; positive is worse)",
        margin=dict(l=55, r=25, t=55, b=50),
    )
    return fig


def _figure_html(fig: go.Figure, include_plotlyjs) -> str:
    return fig.to_html(
        full_html=False,
        include_plotlyjs=include_plotlyjs,
        config={"responsive": True, "displaylogo": False},
    )


def save_sweep_suite_dashboard(result: SweepSuiteResult, path: Path) -> None:
    """Interactive report containing one section per one-factor sweep."""

    sections: list[str] = []
    first_figure = True

    for definition in result.definitions:
        avg_fig = _plotly_metric_figure(
            result.summary,
            definition,
            metric="average_wait_minutes",
            title="Mean average wait",
            y_title="Minutes",
        )
        p95_fig = _plotly_metric_figure(
            result.summary,
            definition,
            metric="p95_wait_minutes",
            title="Mean P95 wait",
            y_title="Minutes",
        )
        paired_fig = _plotly_paired_figure(
            result.paired_summary,
            definition,
            result.baseline_policy,
        )

        base_figures = (avg_fig, p95_fig, paired_fig)
        figures = []
        for fig in base_figures:
            figures.append(_figure_html(fig, "cdn" if first_figure else False))
            first_figure = False

        robustness_html = ""
        if definition.name in ROBUSTNESS_SWEEPS:
            benefit_fig = _plotly_historical_benefit_figure(result.runs, definition)
            degradation_fig = _plotly_perfect_sensor_degradation_figure(
                result.runs,
                definition,
            )
            robustness_figures = []
            for fig in (benefit_fig, degradation_fig):
                robustness_figures.append(
                    _figure_html(fig, "cdn" if first_figure else False)
                )
                first_figure = False
            robustness_html = f"""
              <p class="muted robustness-note">
                Paired robustness views use the same synthetic world at every
                impairment level. Benefit over Historical asks whether imperfect
                sensing is still worth using; degradation shows how much is lost
                relative to the 0% impairment point.
              </p>
              <div class="grid">
                <div class="chart">{robustness_figures[0]}</div>
                <div class="chart">{robustness_figures[1]}</div>
              </div>
            """

        sections.append(
            f"""
            <section>
              <h2>{escape(definition.title)}</h2>
              <p>{escape(definition.description)}</p>
              <div class="grid">
                <div class="chart">{figures[0]}</div>
                <div class="chart">{figures[1]}</div>
                <div class="chart wide">{figures[2]}</div>
              </div>
              {robustness_html}
            </section>
            """
        )

    runs = int(result.runs["run"].nunique()) if not result.runs.empty else 0
    policies = (
        list(dict.fromkeys(result.runs["policy"].tolist())) if not result.runs.empty else []
    )

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SeeBus experiment suite</title>
  <style>
    body {{ margin: 0; font-family: system-ui, -apple-system, Segoe UI, sans-serif; background: #f4f6f8; color: #111827; }}
    main {{ max-width: 1400px; margin: 0 auto; padding: 28px; }}
    h1 {{ margin-bottom: 6px; }}
    h2 {{ margin-top: 0; }}
    .muted {{ color: #5f6b7a; }}
    section {{ background: white; border: 1px solid #d9dee5; border-radius: 14px; padding: 20px; margin-top: 22px; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }}
    .chart {{ min-width: 0; border: 1px solid #e3e7ec; border-radius: 10px; overflow: hidden; }}
    .wide {{ grid-column: 1 / -1; }}
    .robustness-note {{ margin: 18px 2px 10px; }}
    @media (max-width: 850px) {{ .grid {{ grid-template-columns: 1fr; }} .wide {{ grid-column: auto; }} main {{ padding: 14px; }} }}
  </style>
</head>
<body>
<main>
  <h1>SeeBus experiment suite</h1>
  <p class="muted">{runs} paired worlds per sweep point · policies: {escape(', '.join(policies))} · baseline {escape(result.baseline_policy)}</p>
  {''.join(sections)}
</main>
</body>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
