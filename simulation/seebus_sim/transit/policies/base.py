from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class BusObservation:
    """State of one idle bus currently available at the shared hub."""

    bus_id: str
    capacity: int
    available_bus_count: int


@dataclass(frozen=True)
class StationObservation:
    """
    Policy-visible information for one station.

    Exact simulator queue length and hidden true lambda are deliberately not
    exposed. Historical prediction and future sensor estimates enter through
    the corresponding providers.
    """

    station_id: str
    route_id: str
    predicted_lambda: float | None
    sensor_occupancy: float | None
    last_served_time: float | None
    minutes_since_service: float | None


@dataclass(frozen=True)
class RouteObservation:
    """Policy-visible summary for one fixed route."""

    route_id: str
    station_ids: tuple[str, ...]
    trip_minutes: float
    predicted_arrivals_next_horizon: float | None
    sensor_occupancy: float | None
    last_dispatch_time: float | None
    minutes_since_dispatch: float | None
    buses_in_service: int
    can_complete_before_service_end: bool


@dataclass(frozen=True)
class PolicyContext:
    """Snapshot supplied when an idle bus may be dispatched from the hub."""

    now: float
    scenario_day: int
    weekday: str
    bus: BusObservation
    stations: tuple[StationObservation, ...]
    routes: tuple[RouteObservation, ...]
    service_start: float
    service_end: float
    static_dispatch_interval_minutes: float
    prediction_horizon_minutes: float

    def station(self, station_id: str) -> StationObservation:
        for observation in self.stations:
            if observation.station_id == station_id:
                return observation
        raise KeyError(station_id)

    def route(self, route_id: str) -> RouteObservation:
        for observation in self.routes:
            if observation.route_id == route_id:
                return observation
        raise KeyError(route_id)


@dataclass(frozen=True)
class DispatchDecision:
    """
    Dispatch this idle bus onto one complete route immediately.

    Returning ``None`` from ``decide_dispatch`` means keep the bus idle at the
    hub until a later decision opportunity.
    """

    route_id: str
    reason: str = ""


class SchedulingPolicy(ABC):
    """Interface implemented by all SeeBus route-allocation policies."""

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def decide_dispatch(self, context: PolicyContext) -> DispatchDecision | None:
        raise NotImplementedError
