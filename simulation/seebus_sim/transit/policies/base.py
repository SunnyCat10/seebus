from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import cached_property


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
    sensor_occupancy: float | None  # mean noisy station occupancy on the route
    last_dispatch_time: float | None
    minutes_since_dispatch: float | None
    buses_in_service: int
    can_complete_before_service_end: bool
    prediction_window_minutes: float | None = None


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

    @cached_property
    def _station_lookup(self) -> dict[str, StationObservation]:
        return {observation.station_id: observation for observation in self.stations}

    @cached_property
    def _route_lookup(self) -> dict[str, RouteObservation]:
        return {observation.route_id: observation for observation in self.routes}

    def station(self, station_id: str) -> StationObservation:
        try:
            return self._station_lookup[station_id]
        except KeyError:
            raise KeyError(station_id) from None

    def route(self, route_id: str) -> RouteObservation:
        try:
            return self._route_lookup[route_id]
        except KeyError:
            raise KeyError(route_id) from None


@dataclass(frozen=True)
class DispatchDecision:
    """
    Dispatch this idle bus onto one complete route immediately.

    Returning ``None`` from ``decide_dispatch`` means keep the bus idle at the
    hub until a later decision opportunity.
    """

    route_id: str
    reason: str = ""
    score: float | None = None


class SchedulingPolicy(ABC):
    """Interface implemented by all SeeBus route-allocation policies.

    Policies declare which observation channels they require. The simulator can
    then avoid computing historical forecasts or sensor readings for policies
    that never use them, which keeps large policy-comparison batches fast.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @property
    def requires_history(self) -> bool:
        return False

    @property
    def requires_sensor(self) -> bool:
        return False

    @abstractmethod
    def decide_dispatch(self, context: PolicyContext) -> DispatchDecision | None:
        raise NotImplementedError
