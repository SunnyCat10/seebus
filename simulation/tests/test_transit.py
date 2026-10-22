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


def _policy_context_for_history(*, now: float, a_prediction: float, b_prediction: float):
    from seebus_sim.transit.policies import (
        BusObservation,
        HistoricalPolicy,
        PolicyContext,
        RouteObservation,
        StationObservation,
    )

    stations = (
        StationObservation("a1", "route-a", a_prediction / 2, None, None, None),
        StationObservation("a2", "route-a", a_prediction / 2, None, None, None),
        StationObservation("b1", "route-b", b_prediction / 2, None, None, None),
        StationObservation("b2", "route-b", b_prediction / 2, None, None, None),
    )
    routes = (
        RouteObservation(
            "route-a", ("a1", "a2"), 15.0, a_prediction * 30, None,
            0.0, now, 0, True,
        ),
        RouteObservation(
            "route-b", ("b1", "b2"), 15.0, b_prediction * 30, None,
            0.0, now, 0, True,
        ),
    )
    return PolicyContext(
        now=now,
        scenario_day=1,
        weekday="Monday",
        bus=BusObservation("bus-1", 75, 1),
        stations=stations,
        routes=routes,
        service_start=0.0,
        service_end=1440.0,
        static_dispatch_interval_minutes=6.0,
        prediction_horizon_minutes=30.0,
    ), HistoricalPolicy


def test_historical_policy_prefers_route_with_more_predicted_pressure():
    context, HistoricalPolicy = _policy_context_for_history(
        now=12.0,
        a_prediction=3.0,
        b_prediction=1.0,
    )
    decision = HistoricalPolicy().decide_dispatch(context)

    assert decision is not None
    assert decision.route_id == "route-a"
    assert decision.score is not None
    assert "historical pressure" in decision.reason


def test_historical_policy_can_keep_bus_idle_when_routes_are_not_due():
    from seebus_sim.transit.policies import (
        BusObservation,
        HistoricalPolicy,
        PolicyContext,
        RouteObservation,
        StationObservation,
    )

    context = PolicyContext(
        now=2.0,
        scenario_day=1,
        weekday="Monday",
        bus=BusObservation("bus-1", 75, 1),
        stations=(
            StationObservation("a1", "route-a", 0.2, None, 0.0, 2.0),
            StationObservation("a2", "route-a", 0.2, None, 0.0, 2.0),
            StationObservation("b1", "route-b", 0.2, None, 0.0, 2.0),
            StationObservation("b2", "route-b", 0.2, None, 0.0, 2.0),
        ),
        routes=(
            RouteObservation("route-a", ("a1", "a2"), 15.0, 12.0, None, 0.0, 2.0, 0, True),
            RouteObservation("route-b", ("b1", "b2"), 15.0, 12.0, None, 0.0, 2.0, 0, True),
        ),
        service_start=0.0,
        service_end=1440.0,
        static_dispatch_interval_minutes=6.0,
        prediction_horizon_minutes=30.0,
    )

    assert HistoricalPolicy().decide_dispatch(context) is None


def test_noisy_sensor_is_bounded_quantized_and_reproducible():
    from seebus_sim.transit import NoisyOccupancySensor, SensorConfig

    config = SensorConfig(
        reference_queue_size=50,
        noise_std=0.05,
        precision=0.05,
    )
    sensor = NoisyOccupancySensor(
        config,
        station_ids=("a1",),
        scenario_day=3,
        seed=123,
    )

    first = sensor.read("a1", 100.0, 25)
    second = sensor.read("a1", 100.0, 25)

    assert first == second
    assert first is not None
    assert 0.0 <= first <= 1.0
    assert abs((first / config.precision) - round(first / config.precision)) < 1e-9


def _policy_context_for_sensor(*, now: float, a_sensor: float, b_sensor: float):
    from seebus_sim.transit.policies import (
        BusObservation,
        PolicyContext,
        RouteObservation,
        StationObservation,
    )

    stations = (
        StationObservation("a1", "route-a", None, a_sensor, None, None),
        StationObservation("a2", "route-a", None, a_sensor, None, None),
        StationObservation("b1", "route-b", None, b_sensor, None, None),
        StationObservation("b2", "route-b", None, b_sensor, None, None),
    )
    routes = (
        RouteObservation(
            "route-a", ("a1", "a2"), 15.0, None, a_sensor,
            0.0, now, 0, True,
        ),
        RouteObservation(
            "route-b", ("b1", "b2"), 15.0, None, b_sensor,
            0.0, now, 0, True,
        ),
    )
    return PolicyContext(
        now=now,
        scenario_day=1,
        weekday="Monday",
        bus=BusObservation("bus-1", 75, 1),
        stations=stations,
        routes=routes,
        service_start=0.0,
        service_end=1440.0,
        static_dispatch_interval_minutes=6.0,
        prediction_horizon_minutes=30.0,
    )


def test_sensor_policy_prefers_route_with_higher_live_occupancy():
    from seebus_sim.transit import SensorPolicy

    context = _policy_context_for_sensor(
        now=12.0,
        a_sensor=0.45,
        b_sensor=0.20,
    )
    decision = SensorPolicy().decide_dispatch(context)

    assert decision is not None
    assert decision.route_id == "route-a"
    assert "sensor pressure" in decision.reason


def test_hybrid_policy_can_use_sensor_to_override_historical_preference():
    from seebus_sim.transit.policies import (
        BusObservation,
        HybridPolicy,
        PolicyContext,
        RouteObservation,
        StationObservation,
    )

    # Route A is historically busier, but route B currently has a large live
    # occupancy reading. With the default 60% live-sensor weight, B should win.
    context = PolicyContext(
        now=12.0,
        scenario_day=1,
        weekday="Monday",
        bus=BusObservation("bus-1", 75, 1),
        stations=(
            StationObservation("a1", "route-a", 1.5, 0.10, None, None),
            StationObservation("a2", "route-a", 1.5, 0.10, None, None),
            StationObservation("b1", "route-b", 0.5, 0.80, None, None),
            StationObservation("b2", "route-b", 0.5, 0.80, None, None),
        ),
        routes=(
            RouteObservation(
                "route-a", ("a1", "a2"), 15.0, 3.0 * 30, 0.10,
                0.0, 12.0, 0, True, 30.0,
            ),
            RouteObservation(
                "route-b", ("b1", "b2"), 15.0, 1.0 * 30, 0.80,
                0.0, 12.0, 0, True, 30.0,
            ),
        ),
        service_start=0.0,
        service_end=1440.0,
        static_dispatch_interval_minutes=6.0,
        prediction_horizon_minutes=30.0,
    )

    decision = HybridPolicy().decide_dispatch(context)
    assert decision is not None
    assert decision.route_id == "route-b"
    assert "hybrid pressure" in decision.reason
