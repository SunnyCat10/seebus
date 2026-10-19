import numpy as np
import pandas as pd

from seebus_sim.demand.profile import GroundTruthDemandProfile


class PoissonDemandGenerator:
    """
    Generates the hidden passenger-arrival process.

    The ground-truth lambda is piecewise constant inside each configured
    time bucket, but observations are generated at one-minute resolution.
    That gives the future queue simulation realistic timing while letting
    the predictor learn a coarser demand profile.
    """

    def __init__(
        self,
        profile: GroundTruthDemandProfile,
        rng: np.random.Generator,
        daily_noise_std: float = 0.08,
    ):
        self.profile = profile
        self.rng = rng
        self.daily_noise_std = daily_noise_std

    def generate_day(self, day: int) -> pd.DataFrame:
        rows: list[dict] = []

        for station_id, lambdas in self.profile.lambda_by_station_bucket.items():
            daily_multiplier = max(
                0.05,
                self.rng.normal(1.0, self.daily_noise_std),
            )

            for minute in range(24 * 60):
                bucket = minute // self.profile.bucket_minutes
                base_lambda = float(lambdas[bucket])
                effective_lambda = base_lambda * daily_multiplier
                arrivals = int(self.rng.poisson(effective_lambda))

                rows.append(
                    {
                        "day": day,
                        "station_id": station_id,
                        "minute": minute,
                        "bucket": bucket,
                        "arrivals": arrivals,
                    }
                )

        return pd.DataFrame(rows)
