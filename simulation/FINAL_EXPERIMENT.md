# SeeBus final experiment freeze

This repository version is the **final experiment candidate** for the project-course
research run. Avoid changing simulation behavior after starting the final batch.

## Frozen research model

- Network: `large` preset — 10 fixed routes, 35 route-exclusive stations, 10-bus
  central baseline, one shared hub.
- Demand: hidden station archetypes, time-of-day/weekday structure, daily
  variation, Poisson passenger arrivals, and rare one-off local demand events.
- Learning: historical demand is trained only on the training split; policies do
  not see hidden true lambda or event flags.
- Sensors: queue occupancy estimate with Gaussian estimation error, clamp to
  0–100%, 1 percentage-point reporting quantization.
- Communication: each station attempts one update per simulated minute; dropped
  packets leave the backend using its last successfully received reading.
- Policies: Static, Historical, Sensor, Hybrid.
- Transit: fixed routes, no transfers, no route switching, no stop skipping,
  fixed segment travel times.

## Final one-factor sweeps

1. Fleet pressure: `6,8,10,12,14` buses.
2. One-off events: `0,0.1,0.25,0.5,1` expected station-events/network-day.
3. Occupancy-estimation error σ: `0,5,10,20,30,40,50,60,75,100` percentage points.
4. Packet dropout: `0,5,10,20,40,60,80,90,100` percent.
5. Hybrid live-sensor weight: `0,0.25,0.5,0.6,0.75,1`.

## Important interpretation notes

- The fleet sweep keeps the Static timetable fixed while fleet size changes. It
  measures resource pressure on the same nominal service plan; it does not
  retune Static frequency for each fleet size.
- Estimation error is zero-mean Gaussian noise, not a constant bias. Independent
  station errors can partially cancel when route occupancy is averaged.
- Packet dropout is independent packet loss. This is intentionally simpler than
  bursty Wi-Fi outages.
- The network topology stays fixed in the primary study. Random network topology
  is a possible later robustness extension, not part of the main experiment.
- Approximate 95% CIs use mean ± 1.96 standard errors across paired worlds.

## Pre-flight

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest
```

All tests should pass before starting the final run.

## Final confirmatory run

Use a fresh master seed rather than the exploratory `12345` seed so the final
results are evaluated on unseen synthetic worlds. Example:

```powershell
python .\run_suite.py `
  --scenario large `
  --runs 30 `
  --workers 16 `
  --seed 20261023 `
  --output output\final-suite-large-30
```

The default suite contains 39 parameter points, so 30 worlds/point means 1,170
paired synthetic worlds, each replayed under all four policies.

If the process is interrupted, rerun the exact same command. Completed parameter
points are checkpointed and reused.

After the simulations finish, reports can be regenerated without rerunning the
worlds:

```powershell
python .\run_suite.py `
  --scenario large `
  --runs 30 `
  --seed 20261023 `
  --output output\final-suite-large-30 `
  --report-only
```

## Primary outputs to preserve

- `suite_runs.csv`
- `suite_summary.csv`
- `suite_paired_summary.csv`
- `suite_day_type_comparison.csv`
- `suite_benefit_vs_historical.csv`
- `suite_degradation_vs_perfect_sensor.csv`
- `suite_manifest.json`
- `report.html`

The two robustness CSVs/plots answer the engineering questions directly:

- **Benefit over Historical**: is imperfect live sensing still worth using?
- **Degradation vs 0% impairment**: how much performance is lost because the
  sensor/network is imperfect?


## Secondary tuning sanity study

Before interpreting Hybrid as intrinsically superior, run a small paired tuning
study at the default 10-bus operating point:

```powershell
python .\run_tuning.py `
  --scenario large `
  --runs 10 `
  --workers 10 `
  --seed 20261024 `
  --output output\tuning-large-10b-10
```

This crosses Historical target-load thresholds (`0.15,0.25,0.35,0.5,0.7`) with
Hybrid sensor weights (`0.25,0.5,0.6,0.75`). Prefer evidence of a broad region
where Hybrid beats the same-threshold Historical policy over selecting a single
best cell. If an exact tuning is later chosen, validate it on a new seed rather
than reporting the same worlds used to select it.
