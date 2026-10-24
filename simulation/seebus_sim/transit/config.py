from dataclasses import dataclass
from functools import cached_property


@dataclass(frozen=True)
class RouteConfig:
    """One fixed circular service route that starts and ends at the shared hub."""

    id: str
    stations: tuple[str, ...]
    travel_minutes: float = 5.0

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("route id must not be empty")
        if not self.stations:
            raise ValueError("route must contain at least one station")
        if len(set(self.stations)) != len(self.stations):
            raise ValueError(f"route {self.id!r} contains duplicate stations")
        if self.travel_minutes <= 0:
            raise ValueError("travel_minutes must be > 0")

    @property
    def trip_minutes(self) -> float:
        # hub -> first station -> ... -> last station -> hub
        return (len(self.stations) + 1) * self.travel_minutes


@dataclass(frozen=True)
class TransitConfig:
    """
    Shared-hub transit model.

    Buses wait at one common hub. A policy may dispatch an idle bus onto a
    route, but once dispatched the bus must complete the route in order and
    return to the hub before the policy can use it again.
    """

    routes: tuple[RouteConfig, ...]
    bus_count: int = 2
    bus_capacity: int = 75
    hub_id: str = "hub"
    service_start: float = 0.0
    service_end: float = 24 * 60
    decision_interval_minutes: float = 1.0
    static_dispatch_interval_minutes: float = 10.0
    prediction_horizon_minutes: float = 30.0
    destination_decay: float = 0.65

    def __post_init__(self) -> None:
        if not self.routes:
            raise ValueError("at least one route is required")
        route_ids = [route.id for route in self.routes]
        if len(set(route_ids)) != len(route_ids):
            raise ValueError("route ids must be unique")

        all_stations = [station for route in self.routes for station in route.stations]
        if len(set(all_stations)) != len(all_stations):
            raise ValueError("each station must belong to exactly one route")
        if self.hub_id in all_stations:
            raise ValueError("hub_id must not also be a passenger-demand station")
        if self.bus_count < 1:
            raise ValueError("bus_count must be >= 1")
        if self.bus_capacity < 1:
            raise ValueError("bus_capacity must be >= 1")
        if self.service_end <= self.service_start:
            raise ValueError("service_end must be after service_start")
        if self.decision_interval_minutes <= 0:
            raise ValueError("decision_interval_minutes must be > 0")
        if self.static_dispatch_interval_minutes <= 0:
            raise ValueError("static_dispatch_interval_minutes must be > 0")
        if self.prediction_horizon_minutes <= 0:
            raise ValueError("prediction_horizon_minutes must be > 0")
        if self.destination_decay <= 0:
            raise ValueError("destination_decay must be > 0")

    @cached_property
    def station_ids(self) -> tuple[str, ...]:
        return tuple(station for route in self.routes for station in route.stations)

    @cached_property
    def route_ids(self) -> tuple[str, ...]:
        return tuple(route.id for route in self.routes)

    @cached_property
    def _route_by_id(self) -> dict[str, RouteConfig]:
        return {route.id: route for route in self.routes}

    @cached_property
    def _route_by_station(self) -> dict[str, RouteConfig]:
        return {station: route for route in self.routes for station in route.stations}

    @property
    def static_route_headway_minutes(self) -> float:
        """Headway per route for the round-robin static control policy."""
        return self.static_dispatch_interval_minutes * len(self.routes)

    def route(self, route_id: str) -> RouteConfig:
        try:
            return self._route_by_id[route_id]
        except KeyError:
            raise KeyError(route_id) from None

    def route_for_station(self, station_id: str) -> RouteConfig:
        try:
            return self._route_by_station[station_id]
        except KeyError:
            raise KeyError(station_id) from None
