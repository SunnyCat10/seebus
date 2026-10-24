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



## Network scenarios

The physical transit network is now a reusable configuration layer. Policies,
demand generation, batching, and reporting do not depend on a fixed number of
routes or stations.

Two presets are included:

- `small`: the original 2-route / 4-station / 3-bus control network.
- `large`: 10 independent routes, 35 total stations with route sizes
  `(2, 3, 4, 5, 3, 4, 2, 5, 4, 3)`, and 10 shared buses.

The large preset uses 3 minutes per segment and a nominal 15-minute static
headway per route. Because StaticPolicy dispatches routes round-robin, this is a
global dispatch interval of 1.5 minutes.

Create new scenarios in one place with `build_network_scenario()`:

```python
from seebus_sim.scenarios import build_network_scenario

scenario = build_network_scenario(
    name="custom",
    station_counts=(2, 4, 3, 5),
    bus_count=5,
    bus_capacity=75,
    travel_minutes=4.5,
    static_route_headway_minutes=18,
)
```

Every generated station belongs to exactly one route and every route starts and
ends at the same hub, so increasing network size does not introduce transfers
or passenger route-choice logic.

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
- 1 percentage-point reporting precision (`precision=0.01`);
- no dropout by default.

So a true 50% occupancy might be reported as 45%, 50%, 55%, etc. Roughly 95% of the raw Gaussian error lies within about ±10 percentage points before clipping/rounding. The noise is seeded deterministically so experiments are reproducible.

This model is configured through `SensorConfig`, which also includes a dropout
probability for robustness experiments. Every station attempts one sensor update
per decision interval (one minute by default), even while every bus is busy. A
lost packet leaves the backend's last successfully received reading unchanged,
so packet loss creates stale information rather than erasing sensor state.

## Current policies

### Static

The control policy dispatches routes in a fixed round-robin timetable. The exact
global dispatch interval depends on the selected scenario and is chosen from its
configured nominal per-route headway.

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
# Fast original network
python run.py --scenario small

# 10-route / 35-station / 10-bus network
python run.py --scenario large
```

Both presets use the same demand-learning, policies, sensor model, metrics, and
reporting pipeline. The network size/fleet is the only scenario-level transit
configuration that changes.

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
- live sensor estimates when a sensor provider is enabled;
- time since each station was served;
- time since each route was dispatched;
- buses already active on each route;
- number of currently available buses;
- fixed route duration and station membership.

The policy does **not** receive hidden true lambda, event multipliers, or the simulator's exact queue length.

## Static control

`StaticPolicy` dispatches one bus at fixed intervals and rotates routes
round-robin. For example, the small two-route scenario uses:

```text
00:00 -> Route A
00:06 -> Route B
00:12 -> Route A
00:18 -> Route B
...
```

The shared bus pool still constrains the timetable: a route can only be
dispatched when an actual bus is idle at the hub. The fleet-pressure sweep keeps
the nominal Static timetable fixed while changing the available bus pool; this
is a deliberate experimental assumption rather than automatically retuning the
Static schedule for every fleet size.

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
python run_batch.py --scenario small --runs 10
python run_batch.py --scenario large --runs 10
python run_batch.py --scenario large --runs 30 --workers 4
python run_batch.py --scenario large --runs 100 --workers 4 --seed 12345
```

Each batch run creates a new independently generated world, while **all policies inside that run see the same world**. This makes policy differences paired rather than comparing unrelated random demand.

A master seed makes the sequence reproducible:

```powershell
python run_batch.py --scenario large --runs 30 --seed 12345
```

Worlds can be parallelized across CPU processes:

```powershell
python run_batch.py --scenario large --runs 30 --workers 4
python run_batch.py --scenario large --runs 100 --workers 4

# Rebuild plots/report from a completed large-network checkpoint
python run_batch.py --scenario large --runs 100 --report-only
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


## Experiment suites / parameter sweeps

`run_suite.py` is the **batch-of-batches** layer used for robustness studies.
Each sweep point is an ordinary paired multi-world batch, so all policies still
see exactly the same synthetic world inside a run. The same master seed is also
reused across parameter values, which means run 17 in the 6-bus experiment uses
the same hidden demand world as run 17 in the 8-, 10-, 12-, and 14-bus
experiments. Demand randomness is split into stable station/day substreams so
changing event frequency does not perturb unrelated later stations or days;
common events keep the same timing and strength across nested event-rate points.

The default research suite uses the `large` network and a central baseline of:

- 10 shared buses;
- 1 expected one-off station-event per **network-day**;
- 5 percentage points of Gaussian sensor measurement error;
- 1 percentage-point sensor quantization precision;
- 0% packet dropout outside the dedicated dropout sweep.

It then varies one factor at a time:

```text
Fleet pressure:
6, 8, 9, 10, 12, 14, 16, 18, 20 buses

Event frequency:
0, 0.1, 0.25, 0.5, 1 expected station-events / network-day

Occupancy estimation accuracy:
0%, 5%, 10%, 20%, 30%, 40%, 50%, 60%, 75%, 100% measurement-error sigma

Packet dropout:
0%, 5%, 10%, 20%, 40%, 60%, 80%, 90%, 100% lost sensor packets

Hybrid sensor/history weight:
0, 0.25, 0.5, 0.6, 0.75, 1.0 sensor weight
(history weight = 1 - sensor weight)
```

Sensor accuracy varies `noise_std`; reporting precision remains fixed at 1
percentage point so quantization contributes very little additional error. A
`0%` noise point therefore approximates an ideal occupancy estimator. The
packet-dropout sweep is separate: lost packets do not erase server state; the
backend keeps using the last successfully received occupancy until a newer
reading arrives. Stations attempt updates every minute regardless of fleet
availability. At 100% dropout no sensor packet ever reaches the backend, so the
Sensor policy falls back to its headway guard and Hybrid falls back to its
historical signal.

Hybrid combines the two normalized pressure signals as
`history_weight * historical_pressure + sensor_weight * sensor_pressure`. The
hybrid-weight sweep uses complementary weights summing to one: 0 sensor weight
is history-only, 1 is sensor-only, and the default 0.6 point reproduces the
normal 40% history / 60% sensor Hybrid configuration.

The underlying demand generator still represents events as independent
station/day Bernoulli opportunities. For the suite, the human-facing network
rate is converted with:

```text
per-station event probability
    = expected events per network-day / number of stations
```

so `1 event/day` on the 35-station network uses probability `1/35` per station
per day. This keeps the existing hidden-world generator compatible while making
the experimental parameter easy to explain.

### Run one sweep

During development, start with 5-10 worlds per point:

```powershell
python .\run_suite.py --scenario large --sweep fleet-pressure --runs 5 --workers 4 --seed 12345
python .\run_suite.py --scenario large --sweep event-frequency --runs 10 --workers 4 --seed 12345
python .\run_suite.py --scenario large --sweep sensor-accuracy --runs 10 --workers 4 --seed 12345
python .\run_suite.py --scenario large --sweep packet-dropout --runs 10 --workers 4 --seed 12345
python .\run_suite.py --scenario large --sweep hybrid-weight --runs 10 --workers 4 --seed 12345
```

### Run the full core suite

```powershell
python .\run_suite.py --scenario large --runs 30 --workers 8 --seed 12345
```

With the current defaults this is 39 separate batch points (9 fleet + 5 event +
10 sensor-accuracy + 9 dropout + 6 hybrid-weight), so `--runs 30` means 1,170
independently simulated worlds in total (each replayed by all registered policies). Use a small `--runs` value while iterating and reserve
30-100 worlds per point for final analysis.

Values are configurable from the command line:

```powershell
python .\run_suite.py `
  --scenario large `
  --runs 30 `
  --workers 8 `
  --fleet-values 6,8,9,10,12,14,16,18,20 `
  --event-values 0,0.1,0.25,0.5,1 `
  --sensor-error-values 0,5,10,20,30,40,50,60,75,100 `
  --packet-dropout-values 0,5,10,20,40,60,80,90,100 `
  --hybrid-sensor-weight-values 0,0.25,0.5,0.6,0.75,1
```

The central values used by the *other* sweeps can also be changed with
`--base-buses`, `--base-events-per-day`, and `--base-sensor-error`.

### Checkpoints and resume

Every parameter value is checkpointed as soon as its batch completes:

```text
output/suite-large-30/
├── fleet-pressure/
│   ├── buses-06/
│   ├── buses-08/
│   ├── buses-10/
│   ├── buses-12/
│   └── buses-14/
├── event-frequency/
│   └── ...
├── sensor-accuracy/
│   └── ...
├── packet-dropout/
│   └── ...
├── hybrid-weight/
│   └── ...
├── suite_runs.csv
├── suite_summary.csv
├── suite_paired_comparison.csv
├── suite_paired_summary.csv
├── suite_day_type_comparison.csv
├── suite_event_runs.csv
├── suite_benefit_vs_historical.csv
├── suite_degradation_vs_perfect_sensor.csv
├── suite_manifest.json
├── report.html
└── plots/
```

Rerunning the same command reuses compatible completed point checkpoints and
continues with missing points. Checkpoint metadata includes the seed, run count,
scenario, sweep, and parameter value so results from a different experiment are
not silently reused.

To regenerate only the aggregate CSVs/plots/report from completed checkpoints:

```powershell
python .\run_suite.py --scenario large --runs 30 --seed 12345 --report-only
```

Use `--force` to intentionally recompute every selected point.

### Suite graphs

For every sweep the report generates:

1. mean average passenger wait vs the swept parameter, with 95% confidence
   intervals for every policy;
2. mean P95 passenger wait vs the parameter;
3. paired average-wait difference versus Static, where negative values are
   better.

For the occupancy-estimation and packet-dropout sweeps it also generates two
paired robustness views:

4. **benefit over Historical** = Historical wait − policy wait, where positive
   values mean imperfect sensing still provides value over history alone;
5. **degradation vs perfect sensing / communication** = current wait − wait at
   the 0% impairment point in the same synthetic world, where positive values
   show the cost of an imperfect engineering solution.

These extra views preserve the 100% failure endpoints as useful sanity checks
without letting those outliers hide the smaller but meaningful degradation at
lower impairment levels.

The same long-form data are exported to CSV, so further plots or statistical
analysis can be produced without rerunning the simulation.

For the fleet sweep the nominal Static timetable/headway is intentionally held
constant while the available fleet changes. This tests **resource pressure on
the same service plan**: small fleets may miss dispatch opportunities, while
adaptive policies may exploit additional idle buses differently as the fleet
grows.

## Tests

```powershell
python -m pytest
```

Tests cover demand reproducibility, passenger conservation, FIFO queues, unique station ownership, static dispatch sequencing, whole-route commitment, policy timing/selection, sensor behavior, reproducible batch seeds, paired comparisons, and experiment/batch orchestration.

## Intentional simplifications

For now there is one shared hub, no transfers, no shared stations between routes, no road traffic, no route switching, no stop skipping, fixed segment travel times, and no passenger route choice. These constraints are intentional so the research stays focused on **how to allocate a limited shared bus fleet between routes over time**.

## Performance notes

The large network (10 routes / 35 stations / 10 buses) exercises the same
simulation code as the small network, but v12 removes several costs that scaled
poorly with network size:

- **One policy snapshot per decision tick.** Historical forecasts and sensor
  readings are computed once for the simulated minute and reused for every idle
  bus. Bus-specific fields such as available-bus count, route dispatch age, and
  buses already in service are updated cheaply between decisions.
- **Pre-generated sensor error.** Each station/day now gets one seeded NumPy
  noise/dropout stream that is generated as arrays up front. A sensor read is
  then an O(1) lookup rather than constructing a fresh NumPy RNG for every
  station/minute.
- **Cached topology lookups.** Route IDs, station-to-route ownership, and policy
  context lookups use cached dictionaries rather than repeatedly scanning all
  routes.
- **Single-pass pandas grouping.** Benchmark days and per-station demand are
  grouped once instead of repeatedly boolean-filtering the full DataFrame.
  Metric aggregation similarly groups boarding/dispatch events once before
  computing per-station/per-route summaries.
- **Cached passenger destination choices.** The fixed downstream destination
  probabilities for each station are built once per simulated day rather than
  recalculated by each passenger process.

These changes do not alter Static or Historical policy semantics. The optimized
sensor implementation preserves the configured noise distribution and paired
reproducibility, but it uses a new deterministic random stream, so exact
Sensor/Hybrid numbers from v11 should not be expected to match bit-for-bit.

For a quick runtime check on your own machine, compare scenarios with the same
small batch and one worker:

```powershell
Measure-Command { python .\run_batch.py --scenario small --runs 2 --workers 1 --seed 12345 }
Measure-Command { python .\run_batch.py --scenario large --runs 2 --workers 1 --seed 12345 }
```

Use the same seed when comparing code versions so the generated worlds remain
reproducible within each version.

## Performance modes

The simulator keeps the research dataset minute-dense for inspection/export, but
transit replay is now sparse: before policies are evaluated, benchmark rows with
`arrivals == 0` are removed once per generated world and the smaller arrival
table is shared by every policy. Station passenger processes therefore jump
from one real passenger-arrival minute to the next instead of looping over all
1,440 minutes.

Single-world runs keep **full event logging** so detailed boarding, alighting,
stop, route, station, and bus CSVs are available for debugging and plots.

Large batch runs automatically use **compact event logging**. Compact mode does
not build the heavyweight per-boarding/per-stop DataFrames. Instead it keeps an
exact passenger-weighted wait histogram internally, so average, median, P95,
and maximum wait are unchanged. Daily queue, service, fleet-utilization, and
passenger-conservation metrics are also still calculated exactly.

In other words:

```text
python run.py --scenario large
    -> full detailed logs

python run_batch.py --scenario large --runs 100 --workers 4
    -> sparse arrivals + compact logs
    -> compact checkpoint/report tables only
```

Any interesting batch world can still be reproduced from the demand/transit/
sensor seeds recorded in `runs.csv` and rerun as a detailed single experiment.

For programmatic use, the transit layer accepts:

```python
run_transit_experiment(..., event_logging="full")
run_transit_experiment(..., event_logging="compact")
```

Batch mode selects `compact` automatically when `retain_experiments=False`.


## Focused policy-tuning matrix

`run_tuning.py` is a deliberately separate secondary experiment. It keeps the
large network at 10 buses and replays each generated world across a Cartesian
grid of Historical predicted-load thresholds and Hybrid sensor/history weights.
This checks whether the default 35% / 60%-sensor Hybrid result is part of a broad
good region rather than a lucky single parameter choice.

Default grid:

- Historical target-load fraction: `0.15, 0.25, 0.35, 0.50, 0.70`
- Hybrid sensor weight: `0.25, 0.50, 0.60, 0.75`

The standalone Sensor policy and every Historical threshold are run in the same
paired worlds. Hybrid is compared against Historical **at the same threshold**
and against Sensor. All variants share the same generated demand world, so the
grid is considerably cheaper and statistically cleaner than running independent
batches for every cell.

```powershell
python .\run_tuning.py --scenario large --runs 10 --workers 10 --seed 20261024
```

Outputs include `historical_threshold_summary.csv`, `hybrid_grid_summary.csv`,
three heatmaps, and an interactive `report.html`. Use this as a sensitivity /
tuning study; do not replace the main one-factor-at-a-time suite with it.
