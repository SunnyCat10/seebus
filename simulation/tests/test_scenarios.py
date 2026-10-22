import pytest

from seebus_sim.config import default_experiment_config
from seebus_sim.scenarios import (
    build_network_scenario,
    get_network_scenario,
    large_network_scenario,
    scenario_names,
    small_network_scenario,
)


def test_large_network_has_ten_routes_varied_stations_and_ten_buses():
    scenario = large_network_scenario()

    assert scenario.route_count == 10
    assert scenario.station_counts == (2, 3, 4, 5, 3, 4, 2, 5, 4, 3)
    assert scenario.station_count == 35
    assert scenario.bus_count == 10
    assert len(set(scenario.station_counts)) > 1

    config = scenario.to_transit_config()
    assert config.bus_count == 10
    assert config.static_route_headway_minutes == pytest.approx(15.0)
    assert config.static_dispatch_interval_minutes == pytest.approx(1.5)
    assert len(set(config.station_ids)) == 35


def test_small_network_preserves_original_baseline_shape():
    scenario = small_network_scenario()
    config = scenario.to_transit_config()

    assert scenario.route_count == 2
    assert scenario.station_count == 4
    assert scenario.bus_count == 3
    assert config.static_route_headway_minutes == pytest.approx(12.0)
    assert config.static_dispatch_interval_minutes == pytest.approx(6.0)
    assert config.station_ids == (
        "station-a",
        "station-b",
        "station-c",
        "station-d",
    )


def test_custom_network_builder_makes_unique_route_owned_stations():
    scenario = build_network_scenario(
        name="custom",
        station_counts=(1, 3, 2),
        bus_count=4,
        travel_minutes=6.0,
        static_route_headway_minutes=18.0,
    )
    config = scenario.to_transit_config()

    assert scenario.station_counts == (1, 3, 2)
    assert config.bus_count == 4
    assert config.static_dispatch_interval_minutes == pytest.approx(6.0)
    assert len(config.station_ids) == len(set(config.station_ids)) == 6
    assert all(route.travel_minutes == 6.0 for route in config.routes)


def test_experiment_config_can_select_network_preset():
    small = default_experiment_config("small")
    large = default_experiment_config("large")

    assert len(small.transit.routes) == 2
    assert small.transit.bus_count == 3
    assert len(large.transit.routes) == 10
    assert len(large.station_ids) == 35
    assert large.transit.bus_count == 10
    assert set(scenario_names()) == {"small", "large"}
    assert get_network_scenario("large").name == "large"


def test_unknown_scenario_is_rejected():
    with pytest.raises(ValueError):
        get_network_scenario("giant")
