from pathlib import Path

from seebus_sim.experiments import ExperimentResult


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
        policy_result.bus_metrics.to_csv(policy_dir / "bus_metrics.csv", index=False)
        policy_result.boarding_events.to_csv(policy_dir / "boarding_events.csv", index=False)
        policy_result.alighting_events.to_csv(policy_dir / "alighting_events.csv", index=False)
        policy_result.stop_events.to_csv(policy_dir / "stop_events.csv", index=False)
