from collections import deque
from dataclasses import dataclass


@dataclass
class PassengerBatch:
    arrival_time: float
    destination_id: str
    count: int


@dataclass
class OnboardBatch:
    arrival_time: float
    boarding_time: float
    destination_id: str
    count: int


class StationQueue:
    """FIFO passenger queue with time-weighted queue-length accounting."""

    def __init__(self, station_id: str):
        self.station_id = station_id
        self._queue: deque[PassengerBatch] = deque()
        self.waiting_count = 0
        self.max_queue = 0
        self.queue_area = 0.0
        self._last_change_time = 0.0
        self.generated_count = 0
        self.boarded_count = 0

    def _advance(self, now: float) -> None:
        if now < self._last_change_time:
            raise ValueError("queue time cannot move backwards")
        self.queue_area += self.waiting_count * (now - self._last_change_time)
        self._last_change_time = now

    def add(self, batch: PassengerBatch, now: float) -> None:
        if batch.count <= 0:
            return
        self._advance(now)
        self._queue.append(batch)
        self.waiting_count += batch.count
        self.generated_count += batch.count
        self.max_queue = max(self.max_queue, self.waiting_count)

    def board(self, capacity: int, now: float) -> list[PassengerBatch]:
        """Remove up to capacity passengers in FIFO order."""
        if capacity <= 0 or self.waiting_count == 0:
            return []

        self._advance(now)
        boarded: list[PassengerBatch] = []
        remaining_capacity = capacity

        while remaining_capacity > 0 and self._queue:
            batch = self._queue[0]
            take = min(batch.count, remaining_capacity)

            boarded.append(
                PassengerBatch(
                    arrival_time=batch.arrival_time,
                    destination_id=batch.destination_id,
                    count=take,
                )
            )

            batch.count -= take
            self.waiting_count -= take
            self.boarded_count += take
            remaining_capacity -= take

            if batch.count == 0:
                self._queue.popleft()

        return boarded

    def finalize(self, now: float) -> None:
        self._advance(now)

    def average_queue(self, duration: float) -> float:
        return self.queue_area / duration if duration > 0 else 0.0


class BusState:
    """Bus occupancy state with time-weighted utilization accounting."""

    def __init__(self, bus_id: str, capacity: int):
        self.bus_id = bus_id
        self.capacity = capacity
        self.onboard: list[OnboardBatch] = []
        self.occupancy = 0
        self.max_occupancy = 0
        self.occupancy_area = 0.0
        self._last_change_time = 0.0
        self.boarded_count = 0
        self.completed_count = 0

    @property
    def free_capacity(self) -> int:
        return self.capacity - self.occupancy

    def _advance(self, now: float) -> None:
        if now < self._last_change_time:
            raise ValueError("bus time cannot move backwards")
        self.occupancy_area += self.occupancy * (now - self._last_change_time)
        self._last_change_time = now

    def alight(self, station_id: str, now: float) -> list[OnboardBatch]:
        self._advance(now)
        alighted: list[OnboardBatch] = []
        remaining: list[OnboardBatch] = []

        for batch in self.onboard:
            if batch.destination_id == station_id:
                alighted.append(batch)
                self.occupancy -= batch.count
                self.completed_count += batch.count
            else:
                remaining.append(batch)

        self.onboard = remaining
        return alighted

    def board(self, batches: list[PassengerBatch], now: float) -> None:
        self._advance(now)
        for batch in batches:
            if batch.count > self.free_capacity:
                raise ValueError("boarding would exceed bus capacity")
            self.onboard.append(
                OnboardBatch(
                    arrival_time=batch.arrival_time,
                    boarding_time=now,
                    destination_id=batch.destination_id,
                    count=batch.count,
                )
            )
            self.occupancy += batch.count
            self.boarded_count += batch.count
            self.max_occupancy = max(self.max_occupancy, self.occupancy)

    def finalize(self, now: float) -> None:
        self._advance(now)

    def utilization(self, duration: float) -> float:
        denominator = self.capacity * duration
        return self.occupancy_area / denominator if denominator > 0 else 0.0
