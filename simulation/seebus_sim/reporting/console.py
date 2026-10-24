from seebus_sim.experiments import BatchResult, ExperimentResult


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
    print(
        f"Transit: shared hub={transit.hub_id} | "
        f"{len(transit.routes)} routes | {len(transit.station_ids)} stations | "
        f"{transit.bus_count} buses x {transit.bus_capacity} capacity"
    )
    if len(transit.routes) <= 4:
        route_text = ", ".join(
            f"{route.id} ({' -> '.join(route.stations)}, {route.trip_minutes:g} min)"
            for route in transit.routes
        )
        print(f"Routes: {route_text}")
    else:
        station_counts = ", ".join(str(len(route.stations)) for route in transit.routes)
        trip_lengths = [route.trip_minutes for route in transit.routes]
        print(f"Stations per route: [{station_counts}]")
        print(
            f"Route trip duration range: {min(trip_lengths):g}-{max(trip_lengths):g} min"
        )
    print(
        f"Static control: one dispatch every "
        f"{transit.static_dispatch_interval_minutes:g} min, round-robin | "
        f"{transit.static_route_headway_minutes:g} min/route"
    )
    sensor = config.sensor
    print(
        f"Sensor: {sensor.reference_queue_size} waiting passengers = 100% | "
        f"noise sigma={sensor.noise_std:.0%} | precision={sensor.precision:.0%}"
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


def print_batch_summary(result: BatchResult) -> None:
    runs = int(result.comparison["run"].nunique()) if not result.comparison.empty else 0
    print(f"\n=== SeeBus batch: {runs} worlds ===")
    print(f"Baseline policy: {result.baseline_policy}")
    if not result.comparison.empty and {"route_count", "station_count", "bus_count"}.issubset(result.comparison.columns):
        first = result.comparison.iloc[0]
        print(
            f"Network: {int(first['route_count'])} routes | "
            f"{int(first['station_count'])} stations | {int(first['bus_count'])} buses"
        )

    if result.summary.empty:
        print("No batch results.")
        return

    columns = [
        "policy",
        "average_wait_minutes_mean",
        "average_wait_minutes_ci95_low",
        "average_wait_minutes_ci95_high",
        "p95_wait_minutes_mean",
        "max_queue_mean",
        "service_rate_mean",
    ]
    printable = result.summary[columns].copy()
    printable["average_wait_minutes_mean"] = printable["average_wait_minutes_mean"].map(
        lambda x: f"{x:.3f}"
    )
    printable["average_wait_minutes_ci95_low"] = printable[
        "average_wait_minutes_ci95_low"
    ].map(lambda x: f"{x:.3f}")
    printable["average_wait_minutes_ci95_high"] = printable[
        "average_wait_minutes_ci95_high"
    ].map(lambda x: f"{x:.3f}")
    printable["p95_wait_minutes_mean"] = printable["p95_wait_minutes_mean"].map(
        lambda x: f"{x:.3f}"
    )
    printable["max_queue_mean"] = printable["max_queue_mean"].map(lambda x: f"{x:.1f}")
    printable["service_rate_mean"] = printable["service_rate_mean"].map(
        lambda x: f"{x:.2%}"
    )
    print("\nAcross-world policy summary:")
    print(printable.to_string(index=False))

    if not result.paired_summary.empty:
        columns = [
            "policy",
            "average_wait_minutes_delta_mean",
            "average_wait_minutes_delta_ci95_low",
            "average_wait_minutes_delta_ci95_high",
            "average_wait_win_rate",
            "p95_wait_win_rate",
            "max_queue_win_rate",
        ]
        paired = result.paired_summary[columns].copy()
        for column in [
            "average_wait_minutes_delta_mean",
            "average_wait_minutes_delta_ci95_low",
            "average_wait_minutes_delta_ci95_high",
        ]:
            paired[column] = paired[column].map(lambda x: f"{x:+.3f}")
        for column in ["average_wait_win_rate", "p95_wait_win_rate", "max_queue_win_rate"]:
            paired[column] = paired[column].map(lambda x: f"{x:.0%}")
        print(f"\nPaired comparison vs {result.baseline_policy}:")
        print(paired.to_string(index=False))
