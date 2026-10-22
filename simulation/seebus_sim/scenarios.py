from __future__ import annotations

from dataclasses import dataclass

from seebus_sim.transit.config import RouteConfig, TransitConfig


@dataclass(frozen=True)
class NetworkScenario:
    """Reusable network/fleet definition for one SeeBus experiment scenario.

    The demand and policy layers do not depend on a specific network size. A
    scenario only defines the physical transit network and its shared fleet.
    """

    name: str
    routes: tuple[RouteConfig, ...]
    bus_count: int
    bus_capacity: int = 75
    static_route_headway_minutes: float = 20.0
    hub_id: str = "hub"
    decision_interval_minutes: float = 1.0
    prediction_horizon_minutes: float = 30.0
    destination_decay: float = 0.65
    description: str = ""

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("scenario name must not be empty")
        if not self.routes:
            raise ValueError("scenario must contain at least one route")
        if self.bus_count < 1:
            raise ValueError("bus_count must be >= 1")
        if self.bus_capacity < 1:
            raise ValueError("bus_capacity must be >= 1")
        if self.static_route_headway_minutes <= 0:
            raise ValueError("static_route_headway_minutes must be > 0")

    @property
    def route_count(self) -> int:
        return len(self.routes)

    @property
    def station_count(self) -> int:
        return sum(len(route.stations) for route in self.routes)

    @property
    def station_counts(self) -> tuple[int, ...]:
        return tuple(len(route.stations) for route in self.routes)

    def to_transit_config(self) -> TransitConfig:
        """Build the generic transit configuration consumed by the simulator.

        StaticPolicy dispatches globally in round-robin order. Dividing the
        desired per-route headway by the number of routes therefore preserves
        the configured nominal route headway as the network grows.
        """

        return TransitConfig(
            routes=self.routes,
            bus_count=self.bus_count,
            bus_capacity=self.bus_capacity,
            hub_id=self.hub_id,
            decision_interval_minutes=self.decision_interval_minutes,
            static_dispatch_interval_minutes=(
                self.static_route_headway_minutes / self.route_count
            ),
            prediction_horizon_minutes=self.prediction_horizon_minutes,
            destination_decay=self.destination_decay,
        )


def make_route(
    route_number: int,
    station_count: int,
    *,
    travel_minutes: float = 4.0,
) -> RouteConfig:
    """Generate a route whose stations belong only to that route."""

    if route_number < 1:
        raise ValueError("route_number must be >= 1")
    if station_count < 1:
        raise ValueError("station_count must be >= 1")

    route_id = f"route-{route_number:02d}"
    stations = tuple(
        f"{route_id}-station-{station_number:02d}"
        for station_number in range(1, station_count + 1)
    )
    return RouteConfig(
        id=route_id,
        stations=stations,
        travel_minutes=travel_minutes,
    )


def build_network_scenario(
    *,
    name: str,
    station_counts: tuple[int, ...],
    bus_count: int,
    bus_capacity: int = 75,
    travel_minutes: float = 4.0,
    static_route_headway_minutes: float = 20.0,
    description: str = "",
) -> NetworkScenario:
    """Convenience builder for custom independent-route scenarios.

    Example::

        scenario = build_network_scenario(
            name="custom",
            station_counts=(2, 4, 3, 5),
            bus_count=5,
            static_route_headway_minutes=18,
        )
    """

    if not station_counts:
        raise ValueError("station_counts must contain at least one route")

    routes = tuple(
        make_route(index, count, travel_minutes=travel_minutes)
        for index, count in enumerate(station_counts, start=1)
    )
    return NetworkScenario(
        name=name,
        routes=routes,
        bus_count=bus_count,
        bus_capacity=bus_capacity,
        static_route_headway_minutes=static_route_headway_minutes,
        description=description,
    )


def small_network_scenario() -> NetworkScenario:
    """Original two-route research network retained as a fast control."""

    routes = (
        RouteConfig(
            id="route-a",
            stations=("station-a", "station-b"),
            travel_minutes=5.0,
        ),
        RouteConfig(
            id="route-b",
            stations=("station-c", "station-d"),
            travel_minutes=5.0,
        ),
    )
    return NetworkScenario(
        name="small",
        routes=routes,
        bus_count=3,
        bus_capacity=75,
        static_route_headway_minutes=12.0,
        description="2 routes, 4 stations, 3 shared buses",
    )


def large_network_scenario() -> NetworkScenario:
    """Larger shared-hub scenario for policy scaling experiments.

    Ten routes intentionally have different station counts while every station
    still belongs to exactly one route. Ten buses share the common hub. The default timing keeps the larger network
    challenging without making the static baseline trivially overloaded.
    """

    return build_network_scenario(
        name="large",
        station_counts=(2, 3, 4, 5, 3, 4, 2, 5, 4, 3),
        bus_count=10,
        bus_capacity=75,
        travel_minutes=3.0,
        static_route_headway_minutes=15.0,
        description="10 routes, 35 stations, 10 shared buses",
    )


_SCENARIO_BUILDERS = {
    "small": small_network_scenario,
    "large": large_network_scenario,
}


def scenario_names() -> tuple[str, ...]:
    return tuple(_SCENARIO_BUILDERS)


def get_network_scenario(name: str) -> NetworkScenario:
    try:
        builder = _SCENARIO_BUILDERS[name]
    except KeyError as exc:
        choices = ", ".join(scenario_names())
        raise ValueError(f"unknown scenario {name!r}; choose one of: {choices}") from exc
    return builder()
