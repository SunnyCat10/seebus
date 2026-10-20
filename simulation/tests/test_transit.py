import pandas as pd

from seebus_sim.transit import TransitConfig
from seebus_sim.transit.models import PassengerBatch, StationQueue
from seebus_sim.transit.simulation import simulate_static_day
from seebus_sim.transit.timetable import build_loop_timetable


def _small_day(route: tuple[str, ...], arrivals_per_station: int = 12) -> pd.DataFrame:
    rows = []
    for station_id in route:
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
    queue.add(PassengerBatch(2.5, "c", 5), now=2.5)

    boarded = queue.board(capacity=7, now=5.0)

    assert [(batch.destination_id, batch.count) for batch in boarded] == [
        ("b", 5),
        ("c", 2),
    ]
    assert queue.waiting_count == 3
    assert queue.boarded_count == 7


def test_loop_timetable_has_expected_headway():
    config = TransitConfig(
        route=("a", "b", "c", "d"),
        bus_count=2,
        bus_capacity=40,
        travel_minutes=5.0,
    )
    timetable = build_loop_timetable(config)
    station_a = timetable[timetable["station_id"] == "a"].sort_values("arrival_time")

    gaps = station_a["arrival_time"].diff().dropna()

    assert config.scheduled_headway == 10.0
    assert (gaps.round(6) == 10.0).all()


def test_static_day_conserves_passengers_and_respects_capacity():
    config = TransitConfig(
        route=("a", "b", "c", "d"),
        bus_count=2,
        bus_capacity=30,
        travel_minutes=5.0,
    )
    result = simulate_static_day(_small_day(config.route), config, seed=17)
    metrics = result.daily_metrics

    assert metrics["generated_passengers"] == (
        metrics["completed_passengers"]
        + metrics["waiting_at_end"]
        + metrics["onboard_at_end"]
    )
    assert result.stop_events["occupancy_after"].max() <= config.bus_capacity
    assert result.bus_metrics["max_occupancy"].max() <= config.bus_capacity


def test_transit_destination_generation_is_reproducible():
    config = TransitConfig(
        route=("a", "b", "c", "d"),
        bus_count=2,
        bus_capacity=30,
        travel_minutes=5.0,
    )
    demand = _small_day(config.route, arrivals_per_station=20)

    first = simulate_static_day(demand, config, seed=91)
    second = simulate_static_day(demand, config, seed=91)

    pd.testing.assert_frame_equal(first.boarding_events, second.boarding_events)
    pd.testing.assert_frame_equal(first.alighting_events, second.alighting_events)
