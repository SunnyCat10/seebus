from pathlib import Path

from seebus_sim.experiment import run_demand_experiment
from seebus_sim.plots import (
    save_benchmark_variation_plot,
    save_convergence_plot,
    save_profile_comparison_plot,
    save_transit_daily_wait_plot,
    save_transit_station_wait_plot,
)
from seebus_sim.transit import StaticPolicy, TransitConfig, run_transit_experiment


if __name__ == "__main__":
    station_ids = ["station-a", "station-b", "station-c", "station-d"]

    demand_result = run_demand_experiment(
        station_ids=station_ids,
        training_days=14,
        benchmark_days=30,
        bucket_minutes=15,
        seed=42,
        daily_noise_std=0.12,
        event_probability=0.07,
    )

    transit_config = TransitConfig(
        route=tuple(station_ids),
        bus_count=2,
        bus_capacity=75,
        travel_minutes=5.0,
    )
    transit_result = run_transit_experiment(
        benchmark_demand=demand_result.benchmark_demand,
        config=transit_config,
        policy_factory=StaticPolicy,
        seed=2026,
    )

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    # Demand-learning outputs.
    demand_result.training_demand.to_csv(output_dir / "training_demand.csv", index=False)
    demand_result.benchmark_demand.to_csv(output_dir / "benchmark_demand.csv", index=False)
    demand_result.history.to_csv(output_dir / "training_history.csv", index=False)
    demand_result.comparison.to_csv(output_dir / "prediction_comparison.csv", index=False)
    demand_result.convergence.to_csv(output_dir / "convergence.csv", index=False)
    demand_result.event_summary.to_csv(output_dir / "events.csv", index=False)

    save_convergence_plot(
        demand_result.convergence,
        output_dir / "convergence.png",
    )
    save_profile_comparison_plot(
        comparison=demand_result.comparison,
        station_id=station_ids[0],
        bucket_minutes=demand_result.bucket_minutes,
        path=output_dir / "station-a-profile.png",
    )
    save_benchmark_variation_plot(
        benchmark_demand=demand_result.benchmark_demand,
        station_id=station_ids[0],
        bucket_minutes=demand_result.bucket_minutes,
        path=output_dir / "station-a-benchmark-variation.png",
    )

    # Static transit baseline outputs.
    transit_result.timetable.to_csv(output_dir / "static_timetable.csv", index=False)
    transit_result.daily_metrics.to_csv(output_dir / "static_daily_metrics.csv", index=False)
    transit_result.station_metrics.to_csv(output_dir / "static_station_metrics.csv", index=False)
    transit_result.bus_metrics.to_csv(output_dir / "static_bus_metrics.csv", index=False)
    transit_result.boarding_events.to_csv(output_dir / "static_boarding_events.csv", index=False)
    transit_result.alighting_events.to_csv(output_dir / "static_alighting_events.csv", index=False)
    transit_result.stop_events.to_csv(output_dir / "static_stop_events.csv", index=False)

    save_transit_daily_wait_plot(
        transit_result.daily_metrics,
        output_dir / "static-daily-wait.png",
    )
    save_transit_station_wait_plot(
        transit_result.station_metrics,
        output_dir / "static-station-wait.png",
    )

    print("\n=== SeeBus richer demand-learning experiment ===")
    print(f"Training days:  {demand_result.training_days}")
    print(f"Benchmark days: {demand_result.benchmark_days}")
    print(f"Bucket size:    {demand_result.bucket_minutes} minutes")
    print(
        "Benchmark lambda MAE: "
        f"{demand_result.mean_absolute_error:.3f} passengers/min"
    )

    print("\nHidden station archetypes:")
    for station_id in station_ids:
        print(f"  {station_id}: {demand_result.profile.station_types[station_id]}")

    print("\nConvergence on fixed unseen benchmark:")
    print(demand_result.convergence.to_string(index=False))

    benchmark_events = demand_result.event_summary[
        demand_result.event_summary["split"] == "benchmark"
    ]
    print(f"\nOne-off benchmark events: {len(benchmark_events)}")
    if not benchmark_events.empty:
        print(
            benchmark_events[
                [
                    "scenario_day",
                    "weekday",
                    "station_id",
                    "start_minute",
                    "duration_minutes",
                    "event_multiplier",
                ]
            ]
            .head(10)
            .to_string(index=False)
        )

    print("\n=== Static transit baseline ===")
    print(
        f"Route: {' -> '.join(transit_config.route)} -> {transit_config.route[0]}"
    )
    print(
        f"Buses: {transit_config.bus_count} x {transit_config.bus_capacity} capacity | "
        f"travel: {transit_config.travel_minutes:g} min/segment | "
        f"headway: {transit_config.scheduled_headway:.2f} min"
    )

    summary = transit_result.summary
    print(f"Benchmark days simulated: {summary['benchmark_days']}")
    print(f"Passengers generated:     {summary['generated_passengers']:,}")
    print(f"Passengers boarded:       {summary['boarded_passengers']:,}")
    print(f"Service rate:             {summary['service_rate']:.2%}")
    print(f"Average wait:             {summary['average_wait_minutes']:.2f} min")
    print(f"Median wait:              {summary['median_wait_minutes']:.2f} min")
    print(f"P95 wait:                 {summary['p95_wait_minutes']:.2f} min")
    print(f"Maximum wait:             {summary['max_wait_minutes']:.2f} min")
    print(f"Average station queue:    {summary['average_queue']:.2f}")
    print(f"Maximum station queue:    {summary['max_queue']}")
    print(f"Average bus utilization:  {summary['average_bus_utilization']:.2%}")
    print(f"Waiting at day ends:      {summary['waiting_at_day_end']:,}")

    print("\nWrote files to output/:")
    for path in sorted(output_dir.iterdir()):
        print(f"  {path.name}")
