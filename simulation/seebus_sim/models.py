from dataclasses import dataclass


@dataclass(frozen=True)
class DemandObservation:
    day: int
    station_id: str
    bucket: int
    bucket_minutes: int
    arrivals: int

    @property
    def observed_lambda(self) -> float:
        return self.arrivals / self.bucket_minutes
