from dataclasses import dataclass


@dataclass(frozen=True)
class TransitConfig:
    """Configuration for the first static circular-route transit model."""

    route: tuple[str, ...]
    bus_count: int = 3
    bus_capacity: int = 80
    travel_minutes: float = 5.0
    service_start: float = 0.0
    service_end: float = 24 * 60
    destination_decay: float = 0.65

    def __post_init__(self) -> None:
        if len(self.route) < 2:
            raise ValueError("route must contain at least two stations")
        if len(set(self.route)) != len(self.route):
            raise ValueError("route station IDs must be unique")
        if self.bus_count < 1:
            raise ValueError("bus_count must be >= 1")
        if self.bus_capacity < 1:
            raise ValueError("bus_capacity must be >= 1")
        if self.travel_minutes <= 0:
            raise ValueError("travel_minutes must be > 0")
        if self.service_end <= self.service_start:
            raise ValueError("service_end must be after service_start")
        if self.destination_decay <= 0:
            raise ValueError("destination_decay must be > 0")

    @property
    def loop_minutes(self) -> float:
        return len(self.route) * self.travel_minutes

    @property
    def scheduled_headway(self) -> float:
        return self.loop_minutes / self.bus_count
