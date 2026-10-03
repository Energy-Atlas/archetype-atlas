# Executed residential schedules

The dedicated runner executes ResStock's pinned `ScheduleGenerator` and its
thermostat translation routines using the official OpenStudio 3.10.0 portable
Windows runtime. It supplies the inputs used by these routines, rather than
claiming to execute the entire HPXML building-generation and EnergyPlus workflow.
Original fixture records, nulls and runtime gaps in v0.2.0 remain unchanged.

```powershell
.venv/Scripts/python.exe -m scripts.residential_profiles
.venv/Scripts/python.exe -m scripts.residential_profiles --destination build/residential-repeat
```

Run on Windows with Python 3.11.8 or newer and enough disk space for approximately
1 GB of locked runtime/source archives and extraction. Other operating systems can
validate and publish the frozen supplement without executing the Windows runtime.
Execution is opt-in; ordinary source fetch/build never invokes downloaded code.
Each invocation first records a running attempt, then fetches/executes into a
fresh `attempts/<id>/` directory. `latest-run.json` records running, failed or
completed status and the expected record IDs/index hash. Failures never reuse
an old index; earlier successful files remain intact. Freezing with
`python -m scripts.resolve --profiles build/residential --target <new-directory>`
requires the latest attempt to be completed. Raw output directories and failed
or interrupted attempts are rejected. The immutable v0.1.0 supplement preserves
the runner snapshot originally used to generate its independently verified data.
Runtime reuse verifies every extracted file against its extraction inventory.
The source archive is SHA-256 locked; independently verified Git blob hashes
confirmed the selected 1,021 source files. Upstream export attributes change CRLF
line endings in 619 files; executable archive bytes have their own hashes.

## Fixed inputs and interpretation

- The 41 public model-fixture IDs become deterministic random seeds. These are
  modeled configurations, not identified households or population weights.
- Source occupants, bedrooms, state and exact selected options are retained.
  Exact lookup lines/arguments establish appliance and ceiling-fan presence.
  No dishwasher schedule is generated when the selected dishwasher is `None`.
- Calendar 2007 and hourly intervals come from the pinned national baseline.
  Values apply to `[hour,hour+1)` in local standard time, without DST or holiday
  substitutions. Exported fractions are normalized shapes, not load magnitudes;
  selected usage multipliers remain separate inputs.
- The source FIPS county-weather archive returned HTTP 403 on 2026-10-03.
  The pinned HPXML ZIP-to-weather mapping selects 37 TMY3 stations for the 41
  configurations from the working [official station archive](https://data.nlr.gov/submissions/128).
  ZIP latitude/longitude/timezone and actual EPW hashes are retained. These are
  explicitly **station-proxy variants**, not exact county-weather reproductions.
- Three source configurations explicitly contain zero occupants. The upstream
  measure skips their stochastic generation. We honor that skip, supply only a
  zero occupancy fraction as an explicit resolution, and leave their other
  stochastic profiles unresolved. Occupancy zero does not imply lights or
  appliances are always off.
- All 41 nominal thermostat profiles execute upstream offset translation,
  Fahrenheit-to-Celsius conversion and overlap correction in `HVAC.apply_setpoints`.
  Both seasons are Jan 1–Dec 31 in the selected source bindings. The temporary
  OpenStudio model evaluates schedules only; it supplies no research geometry.
  Unavailable-day counts remain reported inputs: their placement/overrides are
  **not executed**, so these are not effective equipment availability profiles.
- EV, refrigerator/freezer, exterior lighting and other non-exported end uses
  remain explicitly unresolved. Appliance installation, load magnitudes and
  complete HPXML/model feasibility must be resolved separately.

## Validation and licensing

CSV outputs are checked for the declared columns, 8,760 hourly rows, finite
values, fraction bounds and heating ≤ cooling. Canonical compact JSON retains
SI values, execution metadata, original inputs, bindings and provenance. Each
artifact and CSV has a SHA-256 digest. Independent reruns compare both digests.

Runtime/source/weather archive URLs, sizes, revisions and hashes are in
`sources/runtime-lock.json` and `sources/weather-lock.json`. Downloaded archives
remain immutable under ignored `build/`; the supplement includes licenses and
locked retrieval metadata. Credit DOE/NREL/ALLIANCE for weather inputs, as required
by the [dataset notice](https://data.nlr.gov/node/128/license); no endorsement is
implied. ResStock and bundled HPXML retain their upstream notices. Original
runner and documentation remain unlicensed by the user's choice.
