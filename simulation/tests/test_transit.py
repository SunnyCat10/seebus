import pandas as pd
import pytest

from seebus_sim.transit import RouteConfig, TransitConfig
from seebus_sim.transit.models import PassengerBatch, StationQueue
from seebus_sim.transit.policies import DispatchDecision, SchedulingPolicy
from seebus_sim.transit.simulation import simulate_day, simulate_static_day
from seebus_sim.transit.timetable import build_static_dispatch_timetable


def _config() -> TransitConfig:
    return TransitConfig(
        routes=(
            RouteConfig("route-a", ("a1", "a2"), travel_minutes=5.0),
            RouteConfig("route-b", ("b1", "b2"), travel_minutes=5.0),
        ),
        bus_count=2,
        bus_capacity=40,
        static_dispatch_interval_minutes=10.0,
    )


def _small_day(config: TransitConfig, arrivals_per_station: int = 12) -> pd.DataFrame:
    rows = []
    for station_id in config.station_ids:
        rows.append(
            {
                "day": 15,
                "scenario_day": 1,
                "weekday": "Monday",
                "station_id": station_id,
                "minute": 1,
                "arrivals": arrivals_per_station,
            }
        )
    return pd.DataFrame(rows)


def test_station_queue_boards_fifo_and_tracks_wait():
    queue = StationQueue("a")
    queue.add(PassengerBatch(1.5, "b", 5), now=1.5)
    queue.add(PassengerBatch(2.5, "hub", 5), now=2.5)

    boarded = queue.board(capacity=7, now=5.0)

    assert [(batch.destination_id, batch.count) for batch in boarded] == [
        ("b", 5),
        ("hub", 2),
    ]
    assert queue.waiting_count == 3
    assert queue.boarded_count == 7


def test_stations_must_be_unique_across_routes():
    with pytest.raises(ValueError, match="exactly one route"):
        TransitConfig(
            routes=(
                RouteConfig("a", ("shared", "a2")),
                RouteConfig("b", ("shared", "b2")),
            )
        )


def test_static_dispatch_timetable_round_robins_routes():
    config = _config()
    timetable = build_static_dispatch_timetable(config)

    first = timetable.head(4)
    assert first["route_id"].tolist() == [
        "route-a",
        "route-b",
        "route-a",
        "route-b",
    ]
    assert first["departure_time"].tolist() == [0.0, 10.0, 20.0, 30.0]
    assert config.static_route_headway_minutes == 20.0


def test_static_day_conserves_passengers_and_respects_capacity():
    config = _config()
    result = simulate_static_day(_small_day(config), config, seed=17)
    metrics = result.daily_metrics

    assert metrics["generated_passengers"] == (
        metrics["completed_passengers"]
        + metrics["waiting_at_end"]
        + metrics["onboard_at_end"]
    )
    assert result.stop_events["occupancy_after"].max() <= config.bus_capacity
    assert result.bus_metrics["max_occupancy"].max() <= config.bus_capacity


def test_bus_completes_whole_route_before_becoming_available():
    config = _config()
    result = simulate_static_day(_small_day(config, 4), config, seed=22)

    first_dispatch = result.dispatch_events.iloc[0]
    bus_id = first_dispatch["bus_id"]
    route_id = first_dispatch["route_id"]
    dispatch_time = first_dispatch["dispatch_time"]
    route = config.route(route_id)

    stops = result.stop_events[
        (result.stop_events["bus_id"] == bus_id)
        & (result.stop_events["dispatch_time"] == dispatch_time)
    ].sort_values("stop_index")

    assert stops["station_id"].tolist() == [*route.stations, config.hub_id]
    assert stops["route_id"].nunique() == 1
    assert stops.iloc[-1]["actual_time"] - dispatch_time == route.trip_minutes


def test_transit_destination_generation_is_reproducible():
    config = _config()
    demand = _small_day(config, arrivals_per_station=20)

    first = simulate_static_day(demand, config, seed=91)
    second = simulate_static_day(demand, config, seed=91)

    pd.testing.assert_frame_equal(first.boarding_events, second.boarding_events)
    pd.testing.assert_frame_equal(first.alighting_events, second.alighting_events)


def test_policy_controls_route_and_when_but_not_mid_route():
    class WaitThenRouteB(SchedulingPolicy):
        @property
        def name(self) -> str:
            return "wait-then-b"

        def decide_dispatch(self, context):
            if context.now < 5:
                return None
            route = context.route("route-b")
            if route.buses_in_service == 0 and route.can_complete_before_service_end:
                return DispatchDecision("route-b", "test")
            return None

    config = _config()
    result = simulate_day(
        _small_day(config, arrivals_per_station=2),
        config,
        WaitThenRouteB(),
        seed=22,
    )

    assert not result.dispatch_events.empty
    assert result.dispatch_events.iloc[0]["dispatch_time"] == 5.0
    assert set(result.dispatch_events["route_id"]) == {"route-b"}

    route_stops = result.stop_events[result.stop_events["route_id"] == "route-b"]
    for _, group in route_stops.groupby(["bus_id", "dispatch_time"]):
        assert group.sort_values("stop_index")["station_id"].tolist() == [
            "b1",
            "b2",
            config.hub_id,
        ]
