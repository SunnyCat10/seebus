# SeeBus Simulation

Lightweight research simulator for evaluating bus **route-allocation / dispatch** policies under repeatable synthetic passenger demand.

The current model has four layers:

1. **Hidden demand world** — station-specific rush hours, weekday behavior, daily variation, rare events, and Poisson passenger arrivals.
2. **Demand learner** — learns a deliberately simpler historical arrival-rate model from training days.
3. **Transit world** — a shared hub, independent fixed routes, station queues, a common bus pool, bus capacity, destinations, and SimPy event timing.
4. **Policy + reporting** — a policy decides which complete route receives an idle bus and when; results are exported as CSV, PNG, and an interactive HTML report.

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
│   └── static/
│       ├── timetable.csv          # planned static route dispatches
│       ├── daily_metrics.csv
│       ├── station_metrics.csv
│       ├── route_metrics.csv
│       ├── bus_metrics.csv
│       ├── dispatch_events.csv    # actual policy allocations
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

## Experiments and batches

`run_experiment()` generates the demand world once and replays the exact same benchmark passenger arrivals for every policy.

`run_batch()` already supports several experiment configurations, so later we can run multiple policies over multiple random seeds, fleet sizes, event probabilities, and policy parameters without changing the simulator.

## Tests

```powershell
python -m pytest
```

Tests cover demand reproducibility, passenger conservation, FIFO queues, unique station ownership, static dispatch sequencing, whole-route commitment, route-policy timing, and experiment/batch orchestration.

## Intentional simplifications

For now there is one shared hub, no transfers, no shared stations between routes, no road traffic, no route switching, no stop skipping, fixed segment travel times, and no passenger route choice. These constraints are intentional so the research stays focused on **how to allocate a limited shared bus fleet between routes over time**.
