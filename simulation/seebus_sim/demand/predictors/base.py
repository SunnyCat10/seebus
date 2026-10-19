from abc import ABC, abstractmethod

import pandas as pd


class DemandPredictor(ABC):
    @abstractmethod
    def fit(self, history: pd.DataFrame) -> None:
        pass

    @abstractmethod
    def predict_lambda(self, station_id: str, bucket: int) -> float:
        pass
