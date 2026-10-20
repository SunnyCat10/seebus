from seebus_sim.experiments import ExperimentResult


def print_experiment_summary(result: ExperimentResult) -> None:
    config = result.config
    demand = result.demand

    print(f"\n=== SeeBus experiment: {config.name} ===")
    print(
        f"Demand: {demand.training_days} training days | "
        f"{demand.benchmark_days} benchmark days | "
        f"{demand.bucket_minutes}-minute buckets"
    )
    print(f"Demand-model benchmark MAE: {demand.mean_absolute_error:.3f} passengers/min")
    print(
        f"Transit: {config.transit.bus_count} buses x {config.transit.bus_capacity} capacity | "
        f"{config.transit.travel_minutes:g} min/segment | "
        f"{config.transit.scheduled_headway:.2f} min headway"
    )

    columns = [
        "policy",
        "service_rate",
        "average_wait_minutes",
        "p95_wait_minutes",
        "max_wait_minutes",
        "max_queue",
        "average_bus_utilization",
        "waiting_at_day_end",
    ]
    printable = result.comparison[columns].copy()
    printable["service_rate"] = printable["service_rate"].map(lambda x: f"{x:.2%}")
    printable["average_bus_utilization"] = printable["average_bus_utilization"].map(
        lambda x: f"{x:.2%}"
    )
    for column in ["average_wait_minutes", "p95_wait_minutes", "max_wait_minutes"]:
        printable[column] = printable[column].map(lambda x: f"{x:.2f}")
    print("\nPolicy comparison:")
    print(printable.to_string(index=False))
