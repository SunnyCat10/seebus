from collections.abc import Callable, Iterable
from dataclasses import dataclass

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
    experiments: list[ExperimentResult]
    comparison: pd.DataFrame


def _prediction_provider(
    demand_result: DemandExperimentResult,
) -> Callable[[str, float], float | None]:
    predictor = AveragePoissonPredictor()
    predictor.fit(demand_result.history)
    bucket_minutes = demand_result.bucket_minutes
    buckets_per_day = 24 * 60 // bucket_minutes

    def predict(station_id: str, minute: float) -> float | None:
        bucket = int(max(0.0, minute) // bucket_minutes) % buckets_per_day
        return predictor.predict_lambda(station_id, bucket)

    return predict


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
        )

    return ExperimentResult(
        config=config,
        demand=demand_result,
        policies=policy_results,
        comparison=_comparison_frame(config.name, policy_results),
    )


def run_batch(
    configs: Iterable[ExperimentConfig],
    policies: Iterable[PolicySpec] | None = None,
) -> BatchResult:
    """Run several experiment configurations and combine their policy summaries."""

    policy_specs = list(policies or [PolicySpec("Static", StaticPolicy)])
    results = [run_experiment(config, policy_specs) for config in configs]
    comparison = (
        pd.concat([result.comparison for result in results], ignore_index=True)
        if results
        else pd.DataFrame()
    )
    return BatchResult(experiments=results, comparison=comparison)
