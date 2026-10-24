import pandas as pd

from seebus_sim.demand.predictors.base import DemandPredictor


class AveragePoissonPredictor(DemandPredictor):
    """
    Maximum-likelihood estimate of the Poisson arrival rate for each
    station/time bucket:

        lambda_hat = total arrivals / total observed minutes
    """

    def __init__(self):
        self._lookup: dict[tuple[str, int], float] = {}

    def fit(self, history: pd.DataFrame) -> None:
        if history.empty:
            self._lookup = {}
            return

        grouped = (
            history.groupby(["station_id", "bucket"], as_index=False)
            .agg(
                total_arrivals=("arrivals", "sum"),
                total_minutes=("bucket_minutes", "sum"),
            )
        )

        grouped["predicted_lambda"] = (
            grouped["total_arrivals"] / grouped["total_minutes"]
        )

        self._lookup = {
            (row.station_id, int(row.bucket)): float(row.predicted_lambda)
            for row in grouped.itertuples(index=False)
        }

    def predict_lambda(self, station_id: str, bucket: int) -> float:
        return self._lookup.get((station_id, bucket), 0.0)
