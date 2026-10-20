from seebus_sim.experiments import ExperimentResult


def print_experiment_summary(result: ExperimentResult) -> None:
    config = result.config
    demand = result.demand
    transit = config.transit

    print(f"\n=== SeeBus experiment: {config.name} ===")
    print(
        f"Demand: {demand.training_days} training days | "
        f"{demand.benchmark_days} benchmark days | "
        f"{demand.bucket_minutes}-minute buckets"
    )
    print(f"Demand-model benchmark MAE: {demand.mean_absolute_error:.3f} passengers/min")
    route_text = ", ".join(
        f"{route.id} ({' -> '.join(route.stations)}, {route.trip_minutes:g} min)"
        for route in transit.routes
    )
    print(
        f"Transit: shared hub={transit.hub_id} | "
        f"{transit.bus_count} buses x {transit.bus_capacity} capacity"
    )
    print(f"Routes: {route_text}")
    print(
        f"Static control: one dispatch every "
        f"{transit.static_dispatch_interval_minutes:g} min, round-robin | "
        f"{transit.static_route_headway_minutes:g} min/route"
    )

    columns = [
        "policy",
        "service_rate",
        "average_wait_minutes",
        "p95_wait_minutes",
        "max_wait_minutes",
        "max_queue",
        "average_bus_utilization",
        "average_fleet_service_utilization",
        "waiting_at_day_end",
    ]
    printable = result.comparison[columns].copy()
    printable["service_rate"] = printable["service_rate"].map(lambda x: f"{x:.2%}")
    for column in ["average_bus_utilization", "average_fleet_service_utilization"]:
        printable[column] = printable[column].map(lambda x: f"{x:.2%}")
    for column in ["average_wait_minutes", "p95_wait_minutes", "max_wait_minutes"]:
        printable[column] = printable[column].map(lambda x: f"{x:.2f}")
    print("\nPolicy comparison:")
    print(printable.to_string(index=False))
