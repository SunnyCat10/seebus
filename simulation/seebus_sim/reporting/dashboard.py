from html import escape
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from seebus_sim.experiments import ExperimentResult


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
<p class="sub">Experiment: {escape(config.name)} · {config.demand.training_days} training days · {config.demand.benchmark_days} benchmark days · {len(config.transit.routes)} routes · {len(config.station_ids)} stations</p>
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
