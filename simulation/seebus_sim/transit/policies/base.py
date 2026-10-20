from abc import ABC, abstractmethod
from dataclasses import dataclass

from seebus_sim.transit.timetable import ScheduledStop


@dataclass(frozen=True)
class BusObservation:
    """Operational bus state that a scheduling policy is allowed to observe."""

    bus_id: str
    capacity: int
    occupancy: int
    current_station_id: str | None

    @property
    def free_capacity(self) -> int:
        return self.capacity - self.occupancy


@dataclass(frozen=True)
class StationObservation:
    """
    Policy-visible information for one station.

    Deliberately excludes the simulator's exact queue length and hidden true
    lambda. A future sensor provider can expose a noisy/approximate occupancy,
    while a prediction provider can expose learned historical demand.
    """

    station_id: str
    predicted_lambda: float | None
    sensor_occupancy: float | None
    last_served_time: float | None
    minutes_since_service: float | None


@dataclass(frozen=True)
class PolicyContext:
    """Snapshot supplied to a policy whenever a bus needs its next stop."""

    now: float
    scenario_day: int
    weekday: str
    bus: BusObservation
    stations: tuple[StationObservation, ...]
    planned_stop: ScheduledStop
    route: tuple[str, ...]
    travel_minutes: float

    def station(self, station_id: str) -> StationObservation:
        for observation in self.stations:
            if observation.station_id == station_id:
                return observation
        raise KeyError(station_id)


@dataclass(frozen=True)
class StopDecision:
    """
    A policy's choice for one service opportunity.

    `target_time` is the earliest time the policy wants the bus to serve the
    chosen station. The simulator still enforces one-way route travel time, so
    an infeasible target is automatically delayed to the earliest reachable
    time.
    """

    station_id: str
    target_time: float
    reason: str = ""


class SchedulingPolicy(ABC):
    """Interface implemented by all SeeBus scheduling policies."""

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def decide_next_stop(self, context: PolicyContext) -> StopDecision:
        raise NotImplementedError
