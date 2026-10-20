import pandas as pd

from seebus_sim.demand.predictors.average import AveragePoissonPredictor
from seebus_sim.experiment import run_demand_experiment


def test_average_predictor_uses_total_observed_time():
    history = pd.DataFrame(
        [
            {
                "day": 1,
                "station_id": "a",
                "bucket": 0,
                "arrivals": 30,
                "bucket_minutes": 15,
            },
            {
                "day": 2,
                "station_id": "a",
                "bucket": 0,
                "arrivals": 45,
                "bucket_minutes": 15,
            },
        ]
    )

    predictor = AveragePoissonPredictor()
    predictor.fit(history)

    assert predictor.predict_lambda("a", 0) == 2.5


def test_benchmark_is_reproducible():
    first = run_demand_experiment(
        ["a", "b"], training_days=3, benchmark_days=2, seed=123
    )
    second = run_demand_experiment(
        ["a", "b"], training_days=3, benchmark_days=2, seed=123
    )

    pd.testing.assert_frame_equal(first.benchmark_demand, second.benchmark_demand)


def test_benchmark_random_stream_is_independent_of_training_length():
    short = run_demand_experiment(
        ["a", "b"], training_days=3, benchmark_days=2, seed=123
    )
    long = run_demand_experiment(
        ["a", "b"], training_days=7, benchmark_days=2, seed=123
    )

    short_reindexed = short.benchmark_demand.copy()
    long_reindexed = long.benchmark_demand.copy()

    short_reindexed["day"] -= short.training_days
    long_reindexed["day"] -= long.training_days

    pd.testing.assert_frame_equal(short_reindexed, long_reindexed)


def test_training_and_benchmark_days_do_not_overlap():
    result = run_demand_experiment(
        ["a"], training_days=4, benchmark_days=3, seed=9
    )

    training_days = set(result.training_demand["day"].unique())
    benchmark_days = set(result.benchmark_demand["day"].unique())

    assert training_days.isdisjoint(benchmark_days)


def test_hidden_world_has_weekday_and_daily_variation():
    result = run_demand_experiment(
        ["a"], training_days=7, benchmark_days=7, seed=77,
        event_probability=0.0,
    )

    demand = result.benchmark_demand
    assert set(demand["weekday"].unique()) == {
        "Monday", "Tuesday", "Wednesday", "Thursday",
        "Friday", "Saturday", "Sunday"
    }
    assert demand["daily_factor"].nunique() > 1
    assert demand["weekday_factor"].nunique() > 1


def test_one_off_events_can_be_forced_for_testing():
    result = run_demand_experiment(
        ["a", "b"], training_days=2, benchmark_days=2, seed=5,
        event_probability=1.0,
    )

    benchmark_events = result.event_summary[
        result.event_summary["split"] == "benchmark"
    ]

    # One event per station/day when probability is forced to 1.
    assert len(benchmark_events) == 4
    assert (benchmark_events["event_multiplier"] > 1.0).all()
    assert (result.benchmark_demand["true_lambda"] > 0).all()
