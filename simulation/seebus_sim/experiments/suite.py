from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, replace
import math

import numpy as np
import pandas as pd

from seebus_sim.config import ExperimentConfig
from seebus_sim.demand.predictors.average import AveragePoissonPredictor
from seebus_sim.experiment import DemandExperimentResult, run_demand_experiment
from seebus_sim.transit import SchedulingPolicy, StaticPolicy, TransitExperimentResult
from seebus_sim.transit.experiment import run_transit_experiment


PolicyFactory = Callable[[], SchedulingPolicy]


@dataclass(frozen=True)
class PolicySpec:
    """Named policy factory used by experiment and batch runners."""

    label: str
    factory: PolicyFactory

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("policy label must not be empty")


@dataclass
class ExperimentResult:
    config: ExperimentConfig
    demand: DemandExperimentResult
    policies: dict[str, TransitExperimentResult]
    comparison: pd.DataFrame


@dataclass
class BatchResult:
    """Aggregated result for several independently generated simulation worlds.

    ``comparison`` contains one row per run/policy.
    ``summary`` aggregates each policy across worlds.
    ``paired_comparison`` compares every non-baseline policy with the baseline in
    the *same* world, which is the preferred way to evaluate policy differences.
    ``day_type_comparison`` separates normal benchmark days from days containing
    one-off demand events.
    """

    experiments: list[ExperimentResult]
    comparison: pd.DataFrame
    summary: pd.DataFrame
    paired_comparison: pd.DataFrame
    paired_summary: pd.DataFrame
    day_type_comparison: pd.DataFrame
    event_runs: pd.DataFrame
    baseline_policy: str


@dataclass
class _BatchRunDigest:
    run: int
    comparison: pd.DataFrame
    day_type_comparison: pd.DataFrame
    event_run: dict


class _AverageDemandProvider:
    """Callable historical predictor with fast bucket-aware horizon integration."""

    def __init__(self, demand_result: DemandExperimentResult) -> None:
        self.predictor = AveragePoissonPredictor()
        self.predictor.fit(demand_result.history)
        self.bucket_minutes = demand_result.bucket_minutes
        self.buckets_per_day = 24 * 60 // self.bucket_minutes

    def __call__(self, station_id: str, minute: float) -> float | None:
        bucket = int(max(0.0, minute) // self.bucket_minutes) % self.buckets_per_day
        return self.predictor.predict_lambda(station_id, bucket)

    def predict_arrivals(
        self,
        station_ids: tuple[str, ...],
        start_minute: float,
        horizon_minutes: float,
    ) -> float | None:
        """Integrate learned lambda across bucket boundaries, not minute steps."""
        if horizon_minutes <= 0:
            return 0.0

        total = 0.0
        current = float(start_minute)
        remaining = float(horizon_minutes)

        while remaining > 1e-9:
            minute_in_day = current % (24 * 60)
            bucket = int(minute_in_day // self.bucket_minutes)
            bucket_end = (bucket + 1) * self.bucket_minutes
            step = min(remaining, bucket_end - minute_in_day)
            if step <= 1e-9:
                step = min(remaining, float(self.bucket_minutes))

            for station_id in station_ids:
                predicted_lambda = self.predictor.predict_lambda(station_id, bucket)
                if predicted_lambda is None:
                    return None
                total += predicted_lambda * step

            current += step
            remaining -= step

        return total


def _prediction_provider(
    demand_result: DemandExperimentResult,
) -> _AverageDemandProvider:
    return _AverageDemandProvider(demand_result)


def _comparison_frame(
    experiment_name: str,
    policy_results: dict[str, TransitExperimentResult],
) -> pd.DataFrame:
    rows: list[dict] = []
    for label, result in policy_results.items():
        summary = result.summary
        rows.append(
            {
                "experiment": experiment_name,
                "policy": label,
                "policy_name": result.policy_name,
                "benchmark_days": summary["benchmark_days"],
                "generated_passengers": summary["generated_passengers"],
                "service_rate": summary["service_rate"],
                "average_wait_minutes": summary["average_wait_minutes"],
                "median_wait_minutes": summary["median_wait_minutes"],
                "p95_wait_minutes": summary["p95_wait_minutes"],
                "max_wait_minutes": summary["max_wait_minutes"],
                "average_queue": summary["average_queue"],
                "max_queue": summary["max_queue"],
                "average_bus_utilization": summary["average_bus_utilization"],
                "average_fleet_service_utilization": summary.get(
                    "average_fleet_service_utilization", 0.0
                ),
                "dispatches": summary.get("dispatches", 0),
                "waiting_at_day_end": summary["waiting_at_day_end"],
            }
        )
    return pd.DataFrame(rows)


def run_experiment(
    config: ExperimentConfig,
    policies: Iterable[PolicySpec] | None = None,
) -> ExperimentResult:
    """
    Generate one demand world once, then replay the same benchmark for all policies.

    This is the main research-level entry point. Demand generation is shared across
    policies so policy comparisons are paired and reproducible.
    """

    policy_specs = list(policies or [PolicySpec("Static", StaticPolicy)])
    if not policy_specs:
        raise ValueError("at least one policy is required")
    labels = [spec.label for spec in policy_specs]
    if len(labels) != len(set(labels)):
        raise ValueError("policy labels must be unique")

    demand_result = run_demand_experiment(
        station_ids=list(config.station_ids),
        training_days=config.demand.training_days,
        benchmark_days=config.demand.benchmark_days,
        bucket_minutes=config.demand.bucket_minutes,
        seed=config.demand_seed,
        daily_noise_std=config.demand.daily_noise_std,
        event_probability=config.demand.event_probability,
    )

    prediction_provider = _prediction_provider(demand_result)
    policy_results: dict[str, TransitExperimentResult] = {}

    for spec in policy_specs:
        policy_results[spec.label] = run_transit_experiment(
            benchmark_demand=demand_result.benchmark_demand,
            config=config.transit,
            policy_factory=spec.factory,
            seed=config.transit_seed,
            prediction_provider=prediction_provider,
            sensor_config=config.sensor,
            sensor_seed=config.sensor_seed,
        )

    return ExperimentResult(
        config=config,
        demand=demand_result,
        policies=policy_results,
        comparison=_comparison_frame(config.name, policy_results),
    )


def build_seeded_batch_configs(
    base_config: ExperimentConfig,
    runs: int,
    *,
    base_seed: int = 20261020,
) -> list[ExperimentConfig]:
    """Create independent, reproducible worlds for a batch.

    A NumPy ``SeedSequence`` is used so each run receives independent demand,
    transit, and sensor seeds. Recreating the same ``base_seed`` reproduces the
    same sequence of worlds, and increasing ``runs`` preserves the earlier runs.
    """

    if runs < 1:
        raise ValueError("runs must be >= 1")

    root = np.random.SeedSequence(base_seed)
    configs: list[ExperimentConfig] = []

    for run_index, run_seed in enumerate(root.spawn(runs), start=1):
        demand_seed_seq, transit_seed_seq, sensor_seed_seq = run_seed.spawn(3)

        def _seed(sequence: np.random.SeedSequence) -> int:
            return int(sequence.generate_state(1, dtype=np.uint32)[0])

        configs.append(
            replace(
                base_config,
                name=f"{base_config.name}-run-{run_index:03d}",
                demand_seed=_seed(demand_seed_seq),
                transit_seed=_seed(transit_seed_seq),
                sensor_seed=_seed(sensor_seed_seq),
            )
        )

    return configs


def _run_experiment_worker(
    args: tuple[ExperimentConfig, list[PolicySpec]],
) -> ExperimentResult:
    config, policies = args
    return run_experiment(config, policies)


def _event_metadata(result: ExperimentResult) -> tuple[int, set[int]]:
    events = result.demand.event_summary
    if events.empty:
        return 0, set()
    benchmark = events[events["split"] == "benchmark"]
    if benchmark.empty:
        return 0, set()
    return int(len(benchmark)), set(benchmark["scenario_day"].astype(int).tolist())


def _batch_comparison(experiments: Sequence[ExperimentResult]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for run_index, result in enumerate(experiments, start=1):
        event_count, event_days = _event_metadata(result)
        frame = result.comparison.copy()
        frame.insert(0, "run", run_index)
        frame["demand_seed"] = result.config.demand_seed
        frame["transit_seed"] = result.config.transit_seed
        frame["sensor_seed"] = result.config.sensor_seed
        frame["benchmark_event_count"] = event_count
        frame["benchmark_event_days"] = len(event_days)
        frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


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


def _policy_summary(comparison: pd.DataFrame) -> pd.DataFrame:
    if comparison.empty:
        return pd.DataFrame()

    metrics = [
        "service_rate",
        "average_wait_minutes",
        "median_wait_minutes",
        "p95_wait_minutes",
        "max_wait_minutes",
        "average_queue",
        "max_queue",
        "average_bus_utilization",
        "average_fleet_service_utilization",
        "dispatches",
        "waiting_at_day_end",
    ]
    rows: list[dict] = []

    for policy, frame in comparison.groupby("policy", sort=False):
        row: dict[str, float | int | str] = {
            "policy": policy,
            "runs": int(frame["run"].nunique()),
        }
        for metric in metrics:
            mean, std, ci_low, ci_high = _mean_std_ci(frame[metric])
            row[f"{metric}_mean"] = mean
            row[f"{metric}_std"] = std
            row[f"{metric}_ci95_low"] = ci_low
            row[f"{metric}_ci95_high"] = ci_high
        rows.append(row)

    return pd.DataFrame(rows)


def _paired_comparison(
    comparison: pd.DataFrame,
    baseline_policy: str,
) -> pd.DataFrame:
    if comparison.empty:
        return pd.DataFrame()
    if baseline_policy not in set(comparison["policy"]):
        raise ValueError(f"baseline policy {baseline_policy!r} is not present")

    metrics = [
        "service_rate",
        "average_wait_minutes",
        "median_wait_minutes",
        "p95_wait_minutes",
        "max_wait_minutes",
        "average_queue",
        "max_queue",
        "average_bus_utilization",
        "average_fleet_service_utilization",
        "dispatches",
        "waiting_at_day_end",
    ]

    baseline = comparison[comparison["policy"] == baseline_policy][
        ["run", *metrics]
    ].set_index("run")

    rows: list[dict] = []
    for row in comparison.itertuples(index=False):
        if row.policy == baseline_policy:
            continue
        base = baseline.loc[int(row.run)]
        output: dict[str, float | int | str | bool] = {
            "run": int(row.run),
            "experiment": row.experiment,
            "policy": row.policy,
            "baseline_policy": baseline_policy,
        }
        for metric in metrics:
            value = float(getattr(row, metric))
            baseline_value = float(base[metric])
            delta = value - baseline_value
            output[f"{metric}_delta"] = delta
            output[f"{metric}_baseline"] = baseline_value
            if abs(baseline_value) > 1e-12:
                output[f"{metric}_pct_change"] = delta / baseline_value
            else:
                output[f"{metric}_pct_change"] = math.nan

        # Explicit paired wins make the report easier to interpret. Waiting and
        # queues are lower-is-better; service rate is higher-is-better.
        output["average_wait_win"] = (
            output["average_wait_minutes_delta"] < 0
        )
        output["p95_wait_win"] = output["p95_wait_minutes_delta"] < 0
        output["max_queue_win"] = output["max_queue_delta"] < 0
        output["service_rate_win"] = output["service_rate_delta"] > 0
        rows.append(output)

    return pd.DataFrame(rows)


def _paired_summary(paired: pd.DataFrame) -> pd.DataFrame:
    if paired.empty:
        return pd.DataFrame()

    delta_metrics = [
        "service_rate_delta",
        "average_wait_minutes_delta",
        "median_wait_minutes_delta",
        "p95_wait_minutes_delta",
        "max_wait_minutes_delta",
        "average_queue_delta",
        "max_queue_delta",
        "average_bus_utilization_delta",
        "average_fleet_service_utilization_delta",
        "dispatches_delta",
        "waiting_at_day_end_delta",
    ]
    win_metrics = [
        "average_wait_win",
        "p95_wait_win",
        "max_queue_win",
        "service_rate_win",
    ]
    rows: list[dict] = []

    for policy, frame in paired.groupby("policy", sort=False):
        row: dict[str, float | int | str] = {
            "policy": policy,
            "baseline_policy": str(frame["baseline_policy"].iloc[0]),
            "runs": int(frame["run"].nunique()),
        }
        for metric in delta_metrics:
            mean, std, ci_low, ci_high = _mean_std_ci(frame[metric])
            row[f"{metric}_mean"] = mean
            row[f"{metric}_std"] = std
            row[f"{metric}_ci95_low"] = ci_low
            row[f"{metric}_ci95_high"] = ci_high
        for metric in win_metrics:
            row[f"{metric}_rate"] = float(frame[metric].mean())
        rows.append(row)

    return pd.DataFrame(rows)


def _day_type_frame_for_experiment(
    run_index: int,
    result: ExperimentResult,
) -> pd.DataFrame:
    rows: list[dict] = []
    _, event_days = _event_metadata(result)
    for label, policy_result in result.policies.items():
        daily = policy_result.daily_metrics.copy()
        daily["day_type"] = daily["scenario_day"].astype(int).map(
            lambda day: "event" if day in event_days else "normal"
        )
        for day_type, frame in daily.groupby("day_type", sort=False):
            rows.append(
                {
                    "run": run_index,
                    "experiment": result.config.name,
                    "policy": label,
                    "day_type": day_type,
                    "days": int(len(frame)),
                    "average_wait_minutes": float(frame["average_wait_minutes"].mean()),
                    "p95_wait_minutes": float(frame["p95_wait_minutes"].mean()),
                    "max_wait_minutes": float(frame["max_wait_minutes"].max()),
                    "average_queue": float(frame["average_queue"].mean()),
                    "max_queue": int(frame["max_queue"].max()),
                    "service_rate": float(frame["service_rate"].mean()),
                }
            )
    return pd.DataFrame(rows)


def _event_run_row(run_index: int, result: ExperimentResult) -> dict:
    events = result.demand.event_summary
    benchmark = events[events["split"] == "benchmark"] if not events.empty else events
    return {
        "run": run_index,
        "experiment": result.config.name,
        "demand_seed": result.config.demand_seed,
        "transit_seed": result.config.transit_seed,
        "sensor_seed": result.config.sensor_seed,
        "benchmark_events": int(len(benchmark)),
        "benchmark_event_days": int(benchmark["scenario_day"].nunique())
        if not benchmark.empty
        else 0,
    }


def _digest_experiment(run_index: int, result: ExperimentResult) -> _BatchRunDigest:
    event_count, event_days = _event_metadata(result)
    comparison = result.comparison.copy()
    comparison.insert(0, "run", run_index)
    comparison["demand_seed"] = result.config.demand_seed
    comparison["transit_seed"] = result.config.transit_seed
    comparison["sensor_seed"] = result.config.sensor_seed
    comparison["benchmark_event_count"] = event_count
    comparison["benchmark_event_days"] = len(event_days)
    return _BatchRunDigest(
        run=run_index,
        comparison=comparison,
        day_type_comparison=_day_type_frame_for_experiment(run_index, result),
        event_run=_event_run_row(run_index, result),
    )


def _run_batch_digest_worker(
    args: tuple[int, ExperimentConfig, list[PolicySpec]],
) -> _BatchRunDigest:
    run_index, config, policies = args
    return _digest_experiment(run_index, run_experiment(config, policies))


def run_batch(
    configs: Iterable[ExperimentConfig],
    policies: Iterable[PolicySpec] | None = None,
    *,
    workers: int = 1,
    baseline_policy: str = "Static",
    retain_experiments: bool = True,
    progress: Callable[[int, int], None] | None = None,
) -> BatchResult:
    """Run several independent worlds and aggregate paired policy comparisons.

    Parallelism is intentionally at the *world* level. Individual SimPy worlds
    remain single-process and deterministic. When ``workers > 1``, policy
    factories must be pickleable (top-level policy classes are ideal).

    For large batches, set ``retain_experiments=False``. The runner then keeps
    only compact per-world summaries instead of retaining passenger/stop event
    tables for every world. This is what ``run_batch.py`` uses by default.
    """

    configs_list = list(configs)
    policy_specs = list(policies or [PolicySpec("Static", StaticPolicy)])
    if workers < 1:
        raise ValueError("workers must be >= 1")

    total = len(configs_list)
    experiments: list[ExperimentResult] = []
    digests: list[_BatchRunDigest] = []

    if retain_experiments:
        if workers == 1 or total <= 1:
            for run_index, config in enumerate(configs_list, start=1):
                result = run_experiment(config, policy_specs)
                experiments.append(result)
                digests.append(_digest_experiment(run_index, result))
                if progress is not None:
                    progress(run_index, total)
        else:
            with ProcessPoolExecutor(max_workers=workers) as executor:
                futures = {
                    executor.submit(run_experiment, config, policy_specs): run_index
                    for run_index, config in enumerate(configs_list, start=1)
                }
                indexed_results: list[tuple[int, ExperimentResult]] = []
                completed = 0
                for future in as_completed(futures):
                    run_index = futures[future]
                    indexed_results.append((run_index, future.result()))
                    completed += 1
                    if progress is not None:
                        progress(completed, total)
                indexed_results.sort(key=lambda item: item[0])
                for run_index, result in indexed_results:
                    experiments.append(result)
                    digests.append(_digest_experiment(run_index, result))
    else:
        args = [
            (run_index, config, policy_specs)
            for run_index, config in enumerate(configs_list, start=1)
        ]
        if workers == 1 or total <= 1:
            for completed, item in enumerate(args, start=1):
                digests.append(_run_batch_digest_worker(item))
                if progress is not None:
                    progress(completed, total)
        else:
            with ProcessPoolExecutor(max_workers=workers) as executor:
                futures = {
                    executor.submit(_run_batch_digest_worker, item): item[0]
                    for item in args
                }
                completed = 0
                for future in as_completed(futures):
                    digests.append(future.result())
                    completed += 1
                    if progress is not None:
                        progress(completed, total)

    digests.sort(key=lambda digest: digest.run)
    comparison = (
        pd.concat([digest.comparison for digest in digests], ignore_index=True)
        if digests
        else pd.DataFrame()
    )
    day_type = (
        pd.concat(
            [digest.day_type_comparison for digest in digests if not digest.day_type_comparison.empty],
            ignore_index=True,
        )
        if any(not digest.day_type_comparison.empty for digest in digests)
        else pd.DataFrame()
    )
    event_runs = pd.DataFrame([digest.event_run for digest in digests])
    paired = (
        _paired_comparison(comparison, baseline_policy)
        if not comparison.empty
        else pd.DataFrame()
    )

    return BatchResult(
        experiments=experiments,
        comparison=comparison,
        summary=_policy_summary(comparison),
        paired_comparison=paired,
        paired_summary=_paired_summary(paired),
        day_type_comparison=day_type,
        event_runs=event_runs,
        baseline_policy=baseline_policy,
    )
