# SeeBus Simulation

Lightweight simulation/experimentation module for the SeeBus project.

The current slice focuses on demand generation and learning before buses and
scheduling policies are introduced.

## Current model

1. Generate a hidden time-dependent passenger arrival rate (`lambda`) for each station.
2. Generate passenger arrivals from a Poisson process at one-minute resolution.
3. Aggregate training observations into 15-minute buckets.
4. Learn `lambda_hat` independently for each station/time bucket.
5. Generate a separate replayable benchmark set using an independent random stream.
6. Measure how prediction error changes as more training days are observed.

The predictor never receives the hidden ground-truth lambda values.

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

Generated files:

```text
output/
├── training_demand.csv
├── benchmark_demand.csv
├── training_history.csv
├── prediction_comparison.csv
├── convergence.csv
├── convergence.png
└── station-a-profile.png
```

`benchmark_demand.csv` is the important replay file. Future scheduling policies
will all consume the same benchmark passenger arrivals so comparisons are fair.

## Tests

```powershell
pytest
```

## Next milestone

Add the simulation world:

- station passenger queues
- buses and capacities
- default schedule
- SimPy event loop
- static policy baseline
- waiting-time / P95 / queue metrics

Then add sensor, historical, weighted and other scheduling policies without
changing the benchmark demand.
