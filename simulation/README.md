# SeeBus Simulation

Lightweight simulation/experimentation module for the SeeBus project.

The project now has two layers:

1. a richer hidden passenger-demand world plus a deliberately simpler learned
   historical demand model;
2. a static SimPy transit baseline that replays the fixed benchmark through
   station queues and buses, producing passenger waiting-time metrics.

## Layer 1: hidden demand and historical learning

For each station, the simulator generates a normal time-of-day demand curve and
assigns a broad station archetype (`residential`, `office`, `shopping`, or
`mixed`). The hidden passenger-arrival rate changes by day:

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

The historical predictor does **not** receive the hidden factors. It learns only
one average `lambda_hat` for each station and 15-minute time bucket.

Training and benchmark use independent random streams, so changing the amount
of training data does not change the benchmark world.

## Layer 2: static transit baseline

The fixed benchmark passenger arrivals are replayed through a simple circular
route:

```text
station-a -> station-b -> station-c -> station-d -> station-a
```

The baseline contains:

- FIFO station queues;
- passenger destinations along the circular route;
- buses with finite capacity;
- fixed travel times;
- an evenly spaced static timetable;
- passenger boarding and alighting;
- time-weighted station queue lengths;
- time-weighted bus utilization;
- waiting-time metrics.

SimPy owns the simulation clock and event scheduling. Domain state is kept in
ordinary Python objects (`StationQueue`, `BusState`, passenger batches).

### Important simplifications

This is intentionally still a lightweight research model:

- one one-way circular route;
- fixed travel time between neighboring stations;
- no traffic or road network;
- no dwell-time model yet;
- no transfers;
- every passenger chooses a downstream stop on the same loop;
- no adaptive scheduling yet.

Those choices keep the static baseline easy to validate before policies start
changing the schedule.

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

The main demand knobs are near the top of `run.py`:

```python
demand_result = run_demand_experiment(
    station_ids=["station-a", "station-b", "station-c", "station-d"],
    training_days=14,
    benchmark_days=30,
    bucket_minutes=15,
    seed=42,
    daily_noise_std=0.12,
    event_probability=0.07,
)
```

The static transit baseline is configured separately:

```python
transit_config = TransitConfig(
    route=("station-a", "station-b", "station-c", "station-d"),
    bus_count=2,
    bus_capacity=75,
    travel_minutes=5.0,
)
```

For this four-stop loop the scheduled headway is:

```text
loop time / bus count
= (4 stops x 5 min) / 2
= 10 min
```

## Transit metrics

The static baseline reports:

- generated / boarded / completed passengers;
- service rate;
- average passenger wait;
- median passenger wait;
- P95 passenger wait;
- maximum passenger wait;
- average and maximum station queue;
- bus occupancy/utilization;
- passengers still waiting at the end of a benchmark day.

Waiting-time statistics are passenger-weighted even though the simulator stores
passengers in batches for efficiency.

## Outputs

Demand layer:

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

Static transit layer adds:

```text
output/
├── static_timetable.csv
├── static_daily_metrics.csv
├── static_station_metrics.csv
├── static_bus_metrics.csv
├── static_boarding_events.csv
├── static_alighting_events.csv
├── static_stop_events.csv
├── static-daily-wait.png
└── static-station-wait.png
```

`benchmark_demand.csv` remains the fixed demand replay source. Future scheduling
policies should use the same benchmark arrivals and transit random seed so they
are compared against the same passenger population.

Hidden diagnostic columns such as `true_lambda`, weekday/day/event factors are
for research/evaluation only and must not be exposed to scheduling policies.

## Tests

```powershell
python -m pytest
```

## Next milestone

Once the static baseline metrics look sensible, add a scheduling-policy layer
without changing the demand or transit world:

1. static timetable (current baseline)
2. sensor-only priority
3. historical-demand priority
4. hybrid historical + sensor priority
5. weighted / fairness-aware policies

All policies should be benchmarked against the same replayable passenger days.
