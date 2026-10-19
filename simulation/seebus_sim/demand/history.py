import pandas as pd


class DemandHistory:
    """Stores observations available to the learning system."""

    def __init__(self, bucket_minutes: int):
        self.bucket_minutes = bucket_minutes
        self._frames: list[pd.DataFrame] = []

    def add_day(self, minute_observations: pd.DataFrame) -> None:
        required = {"day", "station_id", "minute", "arrivals"}
        missing = required - set(minute_observations.columns)
        if missing:
            raise ValueError(f"Missing observation columns: {sorted(missing)}")

        observations = minute_observations.copy()
        observations["bucket"] = observations["minute"] // self.bucket_minutes

        aggregated = (
            observations
            .groupby(["day", "station_id", "bucket"], as_index=False)
            .agg(arrivals=("arrivals", "sum"))
        )
        aggregated["bucket_minutes"] = self.bucket_minutes

        self._frames.append(aggregated)

    def to_frame(self) -> pd.DataFrame:
        if not self._frames:
            return pd.DataFrame(
                columns=[
                    "day",
                    "station_id",
                    "bucket",
                    "arrivals",
                    "bucket_minutes",
                ]
            )

        return pd.concat(self._frames, ignore_index=True)
