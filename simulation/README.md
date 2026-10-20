# SeeBus Simulation

Lightweight research simulator for evaluating adaptive bus-scheduling policies under repeatable synthetic passenger demand.

The current version has four layers:

1. **Demand world** — generates station-specific rush hours, weekday behavior, day-to-day variation, rare events, and Poisson arrivals.
2. **Demand learner** — learns a deliberately simpler historical arrival-rate model from training days.
3. **Transit world** — replays unseen benchmark days through station queues, buses, capacity constraints, destinations, and a fixed loop route using SimPy.
4. **Policy + reporting** — scheduling policies receive only allowed observations; results are exported as CSV, PNG, and an interactive HTML report.

## Setup

```powershell
cd simulation
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run the default experiment

```powershell
python run.py
```

The default experiment uses:

- 4 stations
- 14 demand-training days
- 30 unseen benchmark days
- 15-minute historical demand buckets
- 2 buses
- 75-passenger bus capacity
- 5 minutes between neighboring stations
- 10-minute static headway

## Output

```text
output/
├── report.html                 # interactive research dashboard
├── policy_comparison.csv       # one row per policy
├── demand/
│   ├── training_demand.csv
│   ├── benchmark_demand.csv
│   ├── training_history.csv
│   ├── prediction_comparison.csv
│   ├── convergence.csv
│   └── events.csv
├── policies/
│   └── static/
│       ├── timetable.csv
│       ├── daily_metrics.csv
│       ├── station_metrics.csv
│       ├── bus_metrics.csv
│       ├── boarding_events.csv
│       ├── alighting_events.csv
│       └── stop_events.csv
└── plots/
    ├── demand-convergence.png
    ├── demand-profile.png
    ├── demand-variation.png
    ├── policy-comparison.png
    ├── static-daily-wait.png
    └── static-station-wait.png
```

`report.html` uses Plotly for interactive charts. It loads Plotly JavaScript from the CDN when opened; the PNG and CSV outputs remain fully local.

## Architecture

```text
ExperimentConfig
      │
      ├── Demand generator ──> training + benchmark demand
      │                           │
      │                           └──> historical predictor
      │
      └── same benchmark demand replayed for every policy
                                  │
                                  v
                        Transit simulation (SimPy)
                                  │
                                  v
                         SchedulingPolicy
                                  │
                                  v
                           metrics + events
                                  │
                     ┌────────────┴────────────┐
                     v                         v
                   CSV/PNG               report.html
```

The policy does **not** receive hidden simulator state such as the true lambda, event multiplier, or exact passenger queue. Policy-visible information is defined in `seebus_sim/transit/policies/base.py`.

## Main modules

```text
seebus_sim/
├── config.py                    # experiment configuration
├── demand/                      # hidden demand world + predictor
├── transit/                     # queues, buses, timetable, SimPy engine
│   └── policies/                # policy interface + implementations
├── experiments/                 # single-run and batch orchestration
└── reporting/                   # exports, plots, dashboard, console summary
```

`run.py` is intentionally thin: configure an experiment, choose policies, run it, and report the results.

## Add another policy

Implement `SchedulingPolicy`:

```python
from seebus_sim.transit import PolicyContext, SchedulingPolicy, StopDecision


class MyPolicy(SchedulingPolicy):
    @property
    def name(self) -> str:
        return "my-policy"

    def decide_next_stop(self, context: PolicyContext) -> StopDecision:
        return StopDecision(
            station_id=context.planned_stop.station_id,
            target_time=context.planned_stop.arrival_time,
            reason="example",
        )
```

Then add it to `run.py`:

```python
policies = [
    PolicySpec("Static", StaticPolicy),
    PolicySpec("My policy", MyPolicy),
]
```

Both policies receive the **same benchmark passenger demand**, making the comparison paired and reproducible.

Policies that need constructor arguments can use a factory:

```python
PolicySpec("Weighted", lambda: WeightedPolicy(sensor_weight=0.7))
```

## Run batches later

The experiment layer already supports multiple configurations:

```python
from dataclasses import replace

from seebus_sim.config import default_experiment_config
from seebus_sim.experiments import PolicySpec, run_batch
from seebus_sim.transit import StaticPolicy

base = default_experiment_config()

configs = [
    replace(base, name=f"seed-{seed}", demand_seed=seed)
    for seed in range(10)
]

batch = run_batch(
    configs,
    [PolicySpec("Static", StaticPolicy)],
)

print(batch.comparison)
```

This is intended for future experiments such as:

- several random seeds
- different fleet sizes/capacities
- different event rates
- different demand noise levels
- multiple policies over the exact same scenarios
- parameter sweeps for weighted policies

## Tests

```powershell
python -m pytest
```

The tests cover demand reproducibility, passenger conservation, FIFO queues, policy routing constraints, static-policy regression, and the experiment/batch orchestration layer.

## Current intentional simplifications

The simulator currently models a single one-way loop route with fixed segment travel time. It does not yet model road traffic, transfers, multiple routes, variable dwell time, or correlated city-wide disruptions. Those can be added later if they become useful to the research question.
