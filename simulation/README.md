# SeeBus Simulation

Lightweight research simulator for evaluating bus **route-allocation / dispatch** policies under repeatable synthetic passenger demand.

The current model has four layers:

1. **Hidden demand world** — station-specific rush hours, weekday behavior, daily variation, rare events, and Poisson passenger arrivals.
2. **Demand learner** — learns a deliberately simpler historical arrival-rate model from training days.
3. **Transit world** — a shared hub, independent fixed routes, station queues, a common bus pool, bus capacity, destinations, and SimPy event timing.
4. **Policy + reporting** — interchangeable policies decide which complete route receives an idle bus and when; every policy replays the same benchmark world and results are exported as CSV, PNG, and an interactive HTML report.

## Transit model

All buses share one hub. Stations belong to exactly one route.

```text
                 Shared hub
                /          \
               /            \
   hub -> A1 -> A2 -> hub   hub -> B1 -> B2 -> hub
          Route A                  Route B
```

A bus can only be controlled while idle at the hub:

```text
IDLE AT HUB
    |
    | policy dispatches Route A
    v
hub -> A1 -> A2 -> hub
                    |
                    v
               IDLE AT HUB
```

Once dispatched, the bus **must**:

- visit every station on that route in order;
- stay on the same route;
- return to the common hub;
- become available to the policy only after the trip is complete.

The policy cannot skip a station, reverse direction, switch routes mid-trip, or teleport a bus.

Passengers also stay simple: each station belongs to one route and passengers travel only to a downstream station on that route or to the hub. Transfers and route choice are intentionally excluded.


## Sensor model

Live sensing is deliberately **imperfect**. Policies never receive the exact simulator queue length. Each station sensor converts the real queue to an approximate 0–100% occupancy reading:

```text
true occupancy = min(waiting passengers / reference queue size, 100%)
       + Gaussian measurement noise
       -> clamp to 0..100%
       -> round to sensor precision
```

The default configuration uses:

- 50 waiting passengers = 100% occupancy;
- 5 percentage-point standard deviation (`noise_std=0.05`);
- 5 percentage-point reporting precision (`precision=0.05`);
- no dropout by default.

So a true 50% occupancy might be reported as 45%, 50%, 55%, etc. Roughly 95% of the raw Gaussian error lies within about ±10 percentage points before clipping/rounding. The noise is seeded deterministically so experiments are reproducible.

This model is configured through `SensorConfig`, which also includes a dropout probability for later robustness experiments.

## Current policies

### Static

The control policy dispatches routes in a fixed round-robin timetable. With the default configuration, one bus is dispatched globally every 6 minutes, so each of the two routes receives a nominal 12-minute headway.

### Historical

`HistoricalPolicy` uses only the demand profile learned from the training days. It does **not** see exact queues, hidden true lambda values, event flags, or sensor readings.

For every route it estimates the passenger demand accumulated since the previous dispatch:

```text
predicted backlog ~= learned arrival rate x minutes since last dispatch
```

A route becomes eligible when the predicted backlog reaches a fraction of one bus's capacity, or when a maximum headway is reached. A minimum headway prevents buses from being dispatched almost on top of each other. The default thresholds are deliberately simple and interpretable; they can be tuned with `HistoricalPolicyConfig`.

The route forecast integrates the learned demand profile over the future prediction horizon, so an approaching learned rush-hour bucket can influence a dispatch before it begins.

### Sensor

`SensorPolicy` ignores the historical predictor and uses only the noisy live occupancy readings. It dispatches when the mean occupancy of a route crosses a configurable threshold, subject to the same minimum- and maximum-headway safeguards used to prevent bunching/starvation.

### Hybrid

`HybridPolicy` combines normalized historical pressure and live sensor pressure. The defaults give 40% weight to the historical signal and 60% to the live sensor signal. Historical demand helps anticipate regular rush hours, while sensors can react to one-off deviations that the learned profile cannot predict.

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

The default experiment uses:

- 2 independent routes
- 2 stations per route
- one shared hub
- 14 demand-training days
- 30 unseen benchmark days
- 15-minute historical demand buckets
- 3 buses in one shared pool
- 75-passenger capacity
- 5 minutes per route segment
- one static dispatch opportunity every 6 minutes
- round-robin static control, giving each route a 12-minute nominal headway

## Output

```text
output/
├── report.html
├── policy_comparison.csv
├── demand/
│   ├── training_demand.csv
│   ├── benchmark_demand.csv
│   ├── training_history.csv
│   ├── prediction_comparison.csv
│   ├── convergence.csv
│   └── events.csv
├── policies/
│   ├── static/
│   │   └── ...
│   ├── historical/
│   ├── sensor/
│   └── hybrid/
│       ├── timetable.csv
│       ├── daily_metrics.csv
│       ├── station_metrics.csv
│       ├── route_metrics.csv
│       ├── bus_metrics.csv
│       ├── dispatch_events.csv    # route choice, reason, and policy score
│       ├── boarding_events.csv
│       ├── alighting_events.csv
│       └── stop_events.csv
└── plots/
    └── ...
```

`report.html` includes policy waiting-time comparisons, daily performance, station results, demand-model convergence, queue/utilization behavior, and bus allocations by route.

## Policy interface

Policies are now **dispatch policies**, not stop-routing policies.

```python
from seebus_sim.transit import DispatchDecision, PolicyContext, SchedulingPolicy


class MyPolicy(SchedulingPolicy):
    @property
    def name(self) -> str:
        return "my-policy"

    def decide_dispatch(self, context: PolicyContext) -> DispatchDecision | None:
        # None means: leave this bus idle at the hub for now.
        if context.now < 7 * 60:
            return None

        return DispatchDecision(
            route_id="route-a",
            reason="example",
        )
```

The engine gives each idle bus a decision opportunity once per simulated minute by default. This means a policy decides **when** to dispatch by returning `None` until it wants to send the bus, and decides **where** by returning a route ID.

Policy-visible state includes:

- learned historical demand per station;
- future sensor estimates when a sensor provider is enabled;
- time since each station was served;
- time since each route was dispatched;
- buses already active on each route;
- number of currently available buses;
- fixed route duration and station membership.

The policy does **not** receive hidden true lambda, event multipliers, or the simulator's exact queue length.

## Static control

`StaticPolicy` dispatches one bus at fixed intervals and rotates routes round-robin:

```text
00:00 -> Route A
00:06 -> Route B
00:12 -> Route A
00:18 -> Route B
...
```

The shared bus pool still constrains the timetable: a route can only be dispatched when an actual bus is idle at the hub.

## Architecture

```text
Hidden world
    |
    +--> training days --> historical predictor
    |
    +--> fixed unseen benchmark days
                         |
                         v
                    station queues
                         |
                +--------+--------+
                | shared bus pool |
                +--------+--------+
                         |
                    dispatch policy
                    /            \
                   v              v
               Route A          Route B
                   |              |
              full route      full route
                   \              /
                    +---- hub ----+
                         |
                         v
                       metrics
```


## Adding another policy

Policies live under `seebus_sim/transit/policies/` and implement one method:

```python
class MyPolicy(SchedulingPolicy):
    @property
    def name(self) -> str:
        return "my-policy"

    def decide_dispatch(self, context: PolicyContext) -> DispatchDecision | None:
        ...
```

Then add it to `default_policy_specs()` in `seebus_sim/experiments/presets.py`:

```python
def default_policy_specs():
    return [
        PolicySpec("Static", StaticPolicy),
        PolicySpec("Historical", HistoricalPolicy),
        PolicySpec("Sensor", SensorPolicy),
        PolicySpec("Hybrid", HybridPolicy),
        PolicySpec("My policy", MyPolicy),
    ]
```

Both the single-run and batch workflows use this same policy registry. All registered policies automatically receive the same generated benchmark demand within a world and appear in the comparison reports.

Parameterized policies can use a factory without changing the runner:

```python
PolicySpec(
    "Historical tuned",
    lambda: HistoricalPolicy(
        HistoricalPolicyConfig(target_load_fraction=0.30)
    ),
)
```

## Experiments and batches

`run_experiment()` generates one demand world and replays the exact same benchmark passenger arrivals for every policy.

For statistical policy comparisons, use the dedicated batch CLI:

```powershell
python run_batch.py --runs 5
python run_batch.py --runs 10
python run_batch.py --runs 30
python run_batch.py --runs 100
```

Each batch run creates a new independently generated world, while **all policies inside that run see the same world**. This makes policy differences paired rather than comparing unrelated random demand.

A master seed makes the sequence reproducible:

```powershell
python run_batch.py --runs 30 --seed 12345
```

Worlds can be parallelized across CPU processes:

```powershell
python run_batch.py --runs 30 --workers 4
python run_batch.py --runs 100 --workers 8
```

Parallelism is only across independent worlds. Each individual SimPy world remains deterministic and single-process. Top-level policy classes are pickleable and work with multiprocessing; if a future `PolicySpec` uses a lambda factory, use one worker or replace the lambda with a top-level factory.

By default a batch writes to `output/batch-<runs>/`:

```text
output/batch-30/
├── report.html
├── runs.csv                 # one row per world x policy, including seeds
├── summary.csv              # policy means/std/approx. 95% CIs
├── paired_comparison.csv    # per-world deltas vs Static
├── paired_summary.csv       # mean paired deltas + policy win rates
├── day_type_comparison.csv  # normal vs one-off-event day performance
├── event_runs.csv           # world seeds and generated event counts
└── plots/
    ├── average-wait-distribution.png
    └── paired-average-wait.png
```

The batch runner intentionally does **not** retain or export every boarding/stop event for every world. That would become very large for 30–100 runs. `runs.csv` stores the exact demand/transit/sensor seeds needed to reproduce an interesting world separately.

The paired summary is usually the most useful research output. For example, it reports the mean difference in average wait versus Static, an approximate 95% confidence interval, and the fraction of worlds in which each policy wins on average wait, P95 wait, and maximum queue. The HTML report also separates normal days from days containing generated one-off demand events.

Programmatically, `build_seeded_batch_configs()` + `run_batch()` can also be used for future sweeps over fleet size, event probability, sensor noise, or policy parameters without changing the simulator.

## Tests

```powershell
python -m pytest
```

Tests cover demand reproducibility, passenger conservation, FIFO queues, unique station ownership, static dispatch sequencing, whole-route commitment, policy timing/selection, sensor behavior, reproducible batch seeds, paired comparisons, and experiment/batch orchestration.

## Intentional simplifications

For now there is one shared hub, no transfers, no shared stations between routes, no road traffic, no route switching, no stop skipping, fixed segment travel times, and no passenger route choice. These constraints are intentional so the research stays focused on **how to allocate a limited shared bus fleet between routes over time**.
