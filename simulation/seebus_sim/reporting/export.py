from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError

from seebus_sim.experiments import BatchResult, ExperimentResult


def export_experiment(result: ExperimentResult, output_dir: Path) -> None:
    """Write raw experiment tables into a predictable directory structure."""

    demand_dir = output_dir / "demand"
    policies_dir = output_dir / "policies"
    demand_dir.mkdir(parents=True, exist_ok=True)
    policies_dir.mkdir(parents=True, exist_ok=True)

    demand = result.demand
    demand.training_demand.to_csv(demand_dir / "training_demand.csv", index=False)
    demand.benchmark_demand.to_csv(demand_dir / "benchmark_demand.csv", index=False)
    demand.history.to_csv(demand_dir / "training_history.csv", index=False)
    demand.comparison.to_csv(demand_dir / "prediction_comparison.csv", index=False)
    demand.convergence.to_csv(demand_dir / "convergence.csv", index=False)
    demand.event_summary.to_csv(demand_dir / "events.csv", index=False)

    result.comparison.to_csv(output_dir / "policy_comparison.csv", index=False)

    for label, policy_result in result.policies.items():
        safe_label = label.lower().replace(" ", "-")
        policy_dir = policies_dir / safe_label
        policy_dir.mkdir(parents=True, exist_ok=True)
        policy_result.timetable.to_csv(policy_dir / "timetable.csv", index=False)
        policy_result.daily_metrics.to_csv(policy_dir / "daily_metrics.csv", index=False)
        policy_result.station_metrics.to_csv(policy_dir / "station_metrics.csv", index=False)
        policy_result.route_metrics.to_csv(policy_dir / "route_metrics.csv", index=False)
        policy_result.bus_metrics.to_csv(policy_dir / "bus_metrics.csv", index=False)
        policy_result.boarding_events.to_csv(policy_dir / "boarding_events.csv", index=False)
        policy_result.alighting_events.to_csv(policy_dir / "alighting_events.csv", index=False)
        policy_result.stop_events.to_csv(policy_dir / "stop_events.csv", index=False)
        policy_result.dispatch_events.to_csv(policy_dir / "dispatch_events.csv", index=False)


def export_batch(
    result: BatchResult,
    output_dir: Path,
    *,
    metadata: dict | None = None,
) -> None:
    """Export a durable checkpoint for a multi-world batch.

    This function intentionally writes the compact aggregate tables needed to
    rebuild reports.  Call it *before* plotting/dashboard generation so a
    reporting failure never destroys an expensive completed batch.

    Full per-passenger/per-stop event logs are intentionally not duplicated for
    every world; ``runs.csv`` records the seeds needed to reproduce any run.
    """

    output_dir.mkdir(parents=True, exist_ok=True)
    result.comparison.to_csv(output_dir / "runs.csv", index=False)
    result.summary.to_csv(output_dir / "summary.csv", index=False)
    result.paired_comparison.to_csv(
        output_dir / "paired_comparison.csv", index=False
    )
    result.paired_summary.to_csv(output_dir / "paired_summary.csv", index=False)
    result.day_type_comparison.to_csv(
        output_dir / "day_type_comparison.csv", index=False
    )
    result.event_runs.to_csv(output_dir / "event_runs.csv", index=False)

    manifest = {
        "format_version": 1,
        "baseline_policy": result.baseline_policy,
        "runs": int(result.comparison["run"].nunique())
        if not result.comparison.empty
        else 0,
        "policies": list(dict.fromkeys(result.comparison.get("policy", pd.Series(dtype=str)).tolist())),
    }
    if metadata:
        manifest.update(metadata)
    (output_dir / "batch_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _read_csv_or_empty(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except EmptyDataError:
        return pd.DataFrame()


def load_batch_checkpoint(
    output_dir: Path,
    *,
    baseline_policy: str | None = None,
) -> BatchResult:
    """Reload a compact batch checkpoint without rerunning simulations.

    The resulting ``BatchResult`` has an empty ``experiments`` list by design;
    batch reports use only the aggregate tables saved by :func:`export_batch`.
    """

    runs_path = output_dir / "runs.csv"
    if not runs_path.exists():
        raise FileNotFoundError(
            f"No batch checkpoint found at {runs_path}. Run the batch first."
        )

    manifest_path = output_dir / "batch_manifest.json"
    manifest: dict = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    baseline = baseline_policy or manifest.get("baseline_policy", "Static")
    return BatchResult(
        experiments=[],
        comparison=_read_csv_or_empty(runs_path),
        summary=_read_csv_or_empty(output_dir / "summary.csv"),
        paired_comparison=_read_csv_or_empty(output_dir / "paired_comparison.csv"),
        paired_summary=_read_csv_or_empty(output_dir / "paired_summary.csv"),
        day_type_comparison=_read_csv_or_empty(output_dir / "day_type_comparison.csv"),
        event_runs=_read_csv_or_empty(output_dir / "event_runs.csv"),
        baseline_policy=str(baseline),
    )
