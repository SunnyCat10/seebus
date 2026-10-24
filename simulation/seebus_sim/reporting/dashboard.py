from html import escape
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from seebus_sim.experiments import BatchResult, ExperimentResult


def _figure_html(fig: go.Figure, include_plotlyjs: bool | str) -> str:
    return fig.to_html(
        full_html=False,
        include_plotlyjs=include_plotlyjs,
        config={"displaylogo": False, "responsive": True},
    )


def _summary_cards(result: ExperimentResult) -> str:
    comparison = result.comparison
    cards = []
    for row in comparison.itertuples(index=False):
        cards.append(
            f"""
            <div class="card">
              <div class="eyebrow">{escape(str(row.policy))}</div>
              <div class="metric">{row.average_wait_minutes:.2f} min</div>
              <div class="label">Average wait</div>
              <div class="small">P95 {row.p95_wait_minutes:.2f} min · Service {row.service_rate:.2%}</div>
            </div>
            """
        )
    return "".join(cards)


def _policy_wait_figure(result: ExperimentResult) -> go.Figure:
    frame = result.comparison
    fig = go.Figure()
    fig.add_bar(x=frame["policy"], y=frame["average_wait_minutes"], name="Average wait")
    fig.add_bar(x=frame["policy"], y=frame["p95_wait_minutes"], name="P95 wait")
    fig.update_layout(
        title="Passenger waiting time by policy",
        barmode="group",
        yaxis_title="Minutes",
        margin=dict(l=50, r=20, t=55, b=45),
    )
    return fig


def _daily_wait_figure(result: ExperimentResult) -> go.Figure:
    fig = go.Figure()
    for label, policy in result.policies.items():
        frame = policy.daily_metrics
        fig.add_scatter(
            x=frame["scenario_day"],
            y=frame["average_wait_minutes"],
            mode="lines+markers",
            name=f"{label} average",
        )
        fig.add_scatter(
            x=frame["scenario_day"],
            y=frame["p95_wait_minutes"],
            mode="lines",
            name=f"{label} P95",
        )
    fig.update_layout(
        title="Waiting time across benchmark days",
        xaxis_title="Benchmark day",
        yaxis_title="Minutes",
        margin=dict(l=50, r=20, t=55, b=45),
    )
    return fig


def _station_figure(result: ExperimentResult) -> go.Figure:
    fig = go.Figure()
    for label, policy in result.policies.items():
        summary = (
            policy.station_metrics.groupby("station_id", as_index=False)
            .agg(average_wait_minutes=("average_wait_minutes", "mean"))
        )
        fig.add_bar(
            x=summary["station_id"],
            y=summary["average_wait_minutes"],
            name=label,
        )
    fig.update_layout(
        title="Average wait by station",
        barmode="group",
        xaxis_title="Station",
        yaxis_title="Minutes",
        margin=dict(l=50, r=20, t=55, b=45),
    )
    return fig




def _route_dispatch_figure(result: ExperimentResult) -> go.Figure:
    fig = go.Figure()
    for label, policy in result.policies.items():
        if policy.dispatch_events.empty:
            continue
        summary = (
            policy.dispatch_events.groupby("route_id", as_index=False)
            .size()
            .rename(columns={"size": "dispatches"})
        )
        fig.add_bar(
            x=summary["route_id"],
            y=summary["dispatches"],
            name=label,
        )
    fig.update_layout(
        title="Bus dispatches by route",
        barmode="group",
        xaxis_title="Route",
        yaxis_title="Dispatches",
        margin=dict(l=50, r=20, t=55, b=45),
    )
    return fig

def _convergence_figure(result: ExperimentResult) -> go.Figure:
    frame = result.demand.convergence
    fig = go.Figure()
    fig.add_scatter(
        x=frame["training_days"],
        y=frame["mean_absolute_error"],
        mode="lines+markers",
        name="MAE",
    )
    fig.add_scatter(
        x=frame["training_days"],
        y=frame["root_mean_squared_error"],
        mode="lines+markers",
        name="RMSE",
    )
    fig.update_layout(
        title="Demand-model convergence",
        xaxis_title="Training days",
        yaxis_title="Passengers/min error",
        margin=dict(l=50, r=20, t=55, b=45),
    )
    return fig


def _queue_utilization_figure(result: ExperimentResult) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    for label, policy in result.policies.items():
        daily = policy.daily_metrics
        fig.add_trace(
            go.Scatter(
                x=daily["scenario_day"],
                y=daily["max_queue"],
                mode="lines+markers",
                name=f"{label} max queue",
            ),
            secondary_y=False,
        )
        daily_bus = (
            policy.bus_metrics.groupby("scenario_day", as_index=False)
            .agg(utilization=("utilization", "mean"))
        )
        fig.add_trace(
            go.Scatter(
                x=daily_bus["scenario_day"],
                y=daily_bus["utilization"] * 100,
                mode="lines",
                name=f"{label} utilization",
            ),
            secondary_y=True,
        )
    fig.update_layout(
        title="Peak queues and bus utilization",
        xaxis_title="Benchmark day",
        margin=dict(l=50, r=50, t=55, b=45),
    )
    fig.update_yaxes(title_text="Maximum queue", secondary_y=False)
    fig.update_yaxes(title_text="Utilization (%)", secondary_y=True)
    return fig


def _event_table(result: ExperimentResult) -> str:
    events = result.demand.event_summary
    events = events[events["split"] == "benchmark"].copy()
    if events.empty:
        return "<p class='muted'>No one-off benchmark events were generated.</p>"

    wanted = [
        "scenario_day",
        "weekday",
        "station_id",
        "start_minute",
        "duration_minutes",
        "event_multiplier",
    ]
    table = events[wanted].copy()
    table["event_multiplier"] = table["event_multiplier"].map(lambda value: f"{value:.2f}×")
    return table.to_html(index=False, border=0, classes="events")


def save_dashboard(result: ExperimentResult, path: Path) -> None:
    """Create one lightweight interactive HTML research dashboard.

    Plotly JavaScript is loaded from its CDN when the report is opened.
    """

    figures = [
        _policy_wait_figure(result),
        _daily_wait_figure(result),
        _station_figure(result),
        _convergence_figure(result),
        _queue_utilization_figure(result),
        _route_dispatch_figure(result),
    ]
    figure_html = []
    for index, figure in enumerate(figures):
        figure_html.append(_figure_html(figure, "cdn" if index == 0 else False))

    config = result.config
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SeeBus simulation report — {escape(config.name)}</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 0; background: #f6f7f9; color: #171717; }}
main {{ max-width: 1180px; margin: 0 auto; padding: 28px; }}
h1 {{ margin-bottom: 6px; }}
.sub {{ color: #666; margin-top: 0; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(210px,1fr)); gap: 14px; margin: 24px 0; }}
.card, .panel {{ background: white; border: 1px solid #ddd; border-radius: 12px; padding: 16px; }}
.metric {{ font-size: 1.8rem; font-weight: 700; margin: 4px 0; }}
.eyebrow {{ font-weight: 650; }}
.label, .small, .muted {{ color: #666; }}
.small {{ margin-top: 8px; font-size: .9rem; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(440px,1fr)); gap: 16px; }}
.panel {{ min-width: 0; overflow-x: auto; }}
table.events {{ border-collapse: collapse; width: 100%; }}
table.events th, table.events td {{ border-bottom: 1px solid #ddd; padding: 8px; text-align: left; white-space: nowrap; }}
@media (max-width: 640px) {{ main {{ padding: 16px; }} .grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<main>
<h1>SeeBus simulation report</h1>
<p class="sub">Experiment: {escape(config.name)} · {config.demand.training_days} training days · {config.demand.benchmark_days} benchmark days · {len(config.transit.routes)} routes · {len(config.station_ids)} stations · sensor noise σ={config.sensor.noise_std:.0%}, precision={config.sensor.precision:.0%}</p>
<div class="cards">{_summary_cards(result)}</div>
<div class="grid">
  <section class="panel">{figure_html[0]}</section>
  <section class="panel">{figure_html[3]}</section>
  <section class="panel">{figure_html[1]}</section>
  <section class="panel">{figure_html[2]}</section>
  <section class="panel">{figure_html[4]}</section>
  <section class="panel">{figure_html[5]}</section>
  <section class="panel"><h2>One-off benchmark events</h2>{_event_table(result)}</section>
</div>
</main>
</body>
</html>"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def _batch_wait_distribution(result: BatchResult) -> go.Figure:
    fig = go.Figure()
    for policy, frame in result.comparison.groupby("policy", sort=False):
        fig.add_box(
            y=frame["average_wait_minutes"],
            name=str(policy),
            boxmean=True,
            boxpoints="all" if len(frame) <= 30 else "outliers",
        )
    fig.update_layout(
        title="Average wait across simulated worlds",
        yaxis_title="Minutes",
        margin=dict(l=50, r=20, t=55, b=45),
    )
    return fig


def _batch_paired_figure(result: BatchResult) -> go.Figure:
    fig = go.Figure()
    paired = result.paired_comparison
    if not paired.empty:
        for policy, frame in paired.groupby("policy", sort=False):
            fig.add_box(
                y=frame["average_wait_minutes_delta"],
                name=str(policy),
                boxmean=True,
                boxpoints="all" if len(frame) <= 30 else "outliers",
            )
        fig.add_hline(y=0.0, line_dash="dash")
    fig.update_layout(
        title=f"Paired average-wait difference vs {result.baseline_policy}",
        yaxis_title="Minutes (negative is better)",
        margin=dict(l=50, r=20, t=55, b=45),
    )
    return fig


def _batch_p95_distribution(result: BatchResult) -> go.Figure:
    fig = go.Figure()
    for policy, frame in result.comparison.groupby("policy", sort=False):
        fig.add_box(
            y=frame["p95_wait_minutes"],
            name=str(policy),
            boxmean=True,
            boxpoints=False,
        )
    fig.update_layout(
        title="P95 wait across simulated worlds",
        yaxis_title="Minutes",
        margin=dict(l=50, r=20, t=55, b=45),
    )
    return fig


def _batch_win_rate_figure(result: BatchResult) -> go.Figure:
    fig = go.Figure()
    frame = result.paired_summary
    if not frame.empty:
        fig.add_bar(
            x=frame["policy"],
            y=frame["average_wait_win_rate"] * 100,
            name="Average wait",
        )
        fig.add_bar(
            x=frame["policy"],
            y=frame["p95_wait_win_rate"] * 100,
            name="P95 wait",
        )
        fig.add_bar(
            x=frame["policy"],
            y=frame["max_queue_win_rate"] * 100,
            name="Max queue",
        )
    fig.update_layout(
        title=f"Win rate vs {result.baseline_policy}",
        barmode="group",
        yaxis_title="Runs won (%)",
        yaxis_range=[0, 100],
        margin=dict(l=50, r=20, t=55, b=45),
    )
    return fig


def _batch_day_type_figure(result: BatchResult) -> go.Figure:
    fig = go.Figure()
    frame = result.day_type_comparison
    if frame.empty:
        return fig

    summary = (
        frame.groupby(["policy", "day_type"], as_index=False)
        .agg(average_wait_minutes=("average_wait_minutes", "mean"))
    )
    day_types = [day for day in ("normal", "event") if day in set(summary["day_type"])]
    for day_type in day_types:
        subset = summary[summary["day_type"] == day_type]
        fig.add_bar(
            x=subset["policy"],
            y=subset["average_wait_minutes"],
            name=day_type.title(),
        )
    fig.update_layout(
        title="Average wait on normal vs one-off-event days",
        barmode="group",
        yaxis_title="Minutes",
        margin=dict(l=50, r=20, t=55, b=45),
    )
    return fig


def _batch_summary_cards(result: BatchResult) -> str:
    cards: list[str] = []
    for row in result.summary.itertuples(index=False):
        cards.append(
            f"""
            <div class="card">
              <div class="eyebrow">{escape(str(row.policy))}</div>
              <div class="metric">{row.average_wait_minutes_mean:.2f} min</div>
              <div class="label">Mean average wait</div>
              <div class="small">95% CI {row.average_wait_minutes_ci95_low:.2f}–{row.average_wait_minutes_ci95_high:.2f} · Service {row.service_rate_mean:.2%}</div>
            </div>
            """
        )
    return "".join(cards)


def save_batch_dashboard(result: BatchResult, path: Path) -> None:
    """Create an interactive aggregate report for a multi-world policy batch."""

    figures = [
        _batch_wait_distribution(result),
        _batch_paired_figure(result),
        _batch_p95_distribution(result),
        _batch_win_rate_figure(result),
        _batch_day_type_figure(result),
    ]
    figure_html = [
        _figure_html(figure, "cdn" if index == 0 else False)
        for index, figure in enumerate(figures)
    ]

    runs = int(result.comparison["run"].nunique()) if not result.comparison.empty else 0
    events = int(result.event_runs["benchmark_events"].sum()) if not result.event_runs.empty else 0
    event_worlds = int((result.event_runs["benchmark_events"] > 0).sum()) if not result.event_runs.empty else 0
    if not result.comparison.empty and {"route_count", "station_count", "bus_count"}.issubset(result.comparison.columns):
        first = result.comparison.iloc[0]
        network_text = (
            f"{int(first['route_count'])} routes · "
            f"{int(first['station_count'])} stations · "
            f"{int(first['bus_count'])} buses"
        )
    else:
        network_text = "network configuration unavailable"

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SeeBus batch report</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 0; background: #f6f7f9; color: #171717; }}
main {{ max-width: 1180px; margin: 0 auto; padding: 28px; }}
h1 {{ margin-bottom: 6px; }}
.sub {{ color: #666; margin-top: 0; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(210px,1fr)); gap: 14px; margin: 24px 0; }}
.card, .panel {{ background: white; border: 1px solid #ddd; border-radius: 12px; padding: 16px; }}
.metric {{ font-size: 1.8rem; font-weight: 700; margin: 4px 0; }}
.eyebrow {{ font-weight: 650; }}
.label, .small, .muted {{ color: #666; }}
.small {{ margin-top: 8px; font-size: .9rem; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(440px,1fr)); gap: 16px; }}
.panel {{ min-width: 0; overflow-x: auto; }}
@media (max-width: 640px) {{ main {{ padding: 16px; }} .grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<main>
<h1>SeeBus batch report</h1>
<p class="sub">{runs} independently generated worlds · baseline {escape(result.baseline_policy)} · {network_text} · {events} benchmark events across {event_worlds} worlds</p>
<div class="cards">{_batch_summary_cards(result)}</div>
<div class="grid">
  <section class="panel">{figure_html[0]}</section>
  <section class="panel">{figure_html[1]}</section>
  <section class="panel">{figure_html[2]}</section>
  <section class="panel">{figure_html[3]}</section>
  <section class="panel">{figure_html[4]}</section>
</div>
</main>
</body>
</html>"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
