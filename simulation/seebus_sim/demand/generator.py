import numpy as np
import pandas as pd

from seebus_sim.demand.profile import GroundTruthDemandProfile, WEEKDAYS


class PoissonDemandGenerator:
    """
    Generate the hidden passenger-arrival process at one-minute resolution.

    The true lambda for a minute is built from multiple hidden components:

        normal time-of-day curve
        x weekday factor
        x day-to-day random factor
        x optional one-off event factor

    Passenger arrivals are then sampled from Poisson(true_lambda).

    The learner only receives the arrival counts; the hidden component columns
    are included in the generated data solely so experiments can inspect and
    evaluate the simulated world.
    """

    def __init__(
        self,
        profile: GroundTruthDemandProfile,
        rng: np.random.Generator,
        daily_noise_std: float = 0.12,
        event_probability: float = 0.07,
        event_multiplier_range: tuple[float, float] = (1.8, 4.5),
        event_duration_range: tuple[int, int] = (45, 180),
    ):
        self.profile = profile
        self.rng = rng
        self.daily_noise_std = daily_noise_std
        self.event_probability = event_probability
        self.event_multiplier_range = event_multiplier_range
        self.event_duration_range = event_duration_range

    def _daily_multiplier(self) -> float:
        # A centered log-normal multiplier keeps the value positive while
        # preserving an expected multiplier close to 1.0.
        sigma = self.daily_noise_std
        return float(self.rng.lognormal(mean=-0.5 * sigma * sigma, sigma=sigma))

    def _maybe_generate_event(self, scenario_day: int, station_id: str) -> dict | None:
        if self.rng.random() >= self.event_probability:
            return None

        # Most one-off transport demand events are more interesting during
        # daytime/evening than at 03:00, so sample from 08:00-22:00.
        start = int(self.rng.integers(8 * 60, 22 * 60))
        duration = int(
            self.rng.integers(
                self.event_duration_range[0],
                self.event_duration_range[1] + 1,
            )
        )
        end = min(24 * 60, start + duration)
        multiplier = float(
            self.rng.uniform(
                self.event_multiplier_range[0],
                self.event_multiplier_range[1],
            )
        )

        return {
            "event_id": f"event-{scenario_day}-{station_id}",
            "start": start,
            "end": end,
            "multiplier": multiplier,
        }

    def generate_day(
        self,
        day: int,
        *,
        scenario_day: int | None = None,
        weekday_index: int | None = None,
    ) -> pd.DataFrame:
        """
        Generate one simulated day.

        `day` is the external day label written to the dataset. `scenario_day`
        controls the benchmark world's internal day index and can therefore be
        kept fixed even if the training period length changes.
        """

        if scenario_day is None:
            scenario_day = day
        if weekday_index is None:
            weekday_index = (scenario_day - 1) % 7

        weekday_name = WEEKDAYS[weekday_index]
        rows: list[dict] = []

        for station_id, lambdas in self.profile.lambda_by_station_bucket.items():
            station_type = self.profile.station_types[station_id]
            weekday_factor = self.profile.get_weekday_factor(station_id, weekday_index)
            daily_factor = self._daily_multiplier()
            event = self._maybe_generate_event(scenario_day, station_id)

            for minute in range(24 * 60):
                bucket = minute // self.profile.bucket_minutes
                base_lambda = float(lambdas[bucket])

                event_active = bool(
                    event is not None
                    and event["start"] <= minute < event["end"]
                )
                event_factor = float(event["multiplier"]) if event_active else 1.0

                true_lambda = (
                    base_lambda
                    * weekday_factor
                    * daily_factor
                    * event_factor
                )
                arrivals = int(self.rng.poisson(true_lambda))

                rows.append(
                    {
                        "day": day,
                        "scenario_day": scenario_day,
                        "weekday": weekday_name,
                        "station_id": station_id,
                        "station_type": station_type,
                        "minute": minute,
                        "bucket": bucket,
                        "base_lambda": base_lambda,
                        "weekday_factor": weekday_factor,
                        "daily_factor": daily_factor,
                        "event_factor": event_factor,
                        "event_id": event["event_id"] if event_active else "",
                        "true_lambda": true_lambda,
                        "arrivals": arrivals,
                    }
                )

        return pd.DataFrame(rows)
