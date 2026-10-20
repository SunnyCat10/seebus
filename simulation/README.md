# SeeBus Simulation

Lightweight simulation/experimentation module for the SeeBus project.

The current slice generates a deliberately richer hidden passenger-demand world,
learns a simpler historical demand model from it, and creates a fixed benchmark
that future scheduling policies can replay fairly.

## Hidden world

For each station, the simulator generates a normal time-of-day demand curve and
assigns a broad station archetype (`residential`, `office`, `shopping`, or
`mixed`). The hidden passenger-arrival rate then changes by day:

```text
true_lambda
  = normal time-of-day lambda
  x weekday factor
  x day-to-day random factor
  x one-off event factor
```

Passenger arrivals are sampled every minute:

```text
arrivals ~ Poisson(true_lambda)
```

This gives the hidden world:

- station-specific baseline demand
- smooth morning / midday / evening peaks
- weekday and weekend behavior
- random day-to-day variation
- rare one-off demand events
- Poisson sampling noise

The predictor does **not** receive any of these hidden factors. It still learns
only one average `lambda_hat` for each station and 15-minute time bucket from
historical passenger counts.

That mismatch is intentional: the learned model is an imperfect approximation
of a more complicated real world.

## Training and benchmark

1. Generate training days and observe only passenger counts.
2. Aggregate them into 15-minute historical buckets.
3. Learn `lambda_hat` for each station/time bucket.
4. Generate a separate benchmark using an independent random stream.
5. Evaluate the learned model against each unseen benchmark day's hidden
   `true_lambda`.
6. Save the benchmark passenger arrivals for future scheduling-policy replay.

Changing the number of training days does not change the underlying benchmark
world.

## Setup

```powershell
cd simulation
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run

```powershell
python run.py
```

The main experiment knobs are in `run.py`:

```python
result = run_demand_experiment(
    station_ids=["station-a", "station-b", "station-c", "station-d"],
    training_days=14,
    benchmark_days=30,
    bucket_minutes=15,
    seed=42,
    daily_noise_std=0.12,
    event_probability=0.07,
)
```

## Outputs

```text
output/
├── training_demand.csv
├── benchmark_demand.csv
├── training_history.csv
├── prediction_comparison.csv
├── events.csv
├── convergence.csv
├── convergence.png
├── station-a-profile.png
└── station-a-benchmark-variation.png
```

`benchmark_demand.csv` is the important future replay file. All scheduling
policies should consume the same passenger arrivals.

The demand CSVs also contain hidden diagnostic columns (`true_lambda`, weekday,
daily and event factors). Those are for research/evaluation only and should not
be exposed to scheduling policies.

## Tests

```powershell
python -m pytest
```

## Next milestone

Add the transport world on top of the fixed benchmark:

- station passenger queues
- buses and capacities
- default schedule
- SimPy event loop
- static policy baseline
- waiting-time / P95 / queue metrics

Then compare sensor-only, historical-only, hybrid, weighted, fairness, and other
scheduling policies without changing the benchmark demand.
