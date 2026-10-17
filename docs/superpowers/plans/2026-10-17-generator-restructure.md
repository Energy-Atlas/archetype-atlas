# Schedule generator restructure (ADR 0035)

Date: 2026-10-17. Decisions by the user: nothing is released, so delete freely
with no backward compatibility; bit-level precision is never needed; ComStock is
a faithful readable port (option 1); residential ships R1 (Ruby MT replay) and
R2 (numpy PCG64), retiring R1 if they are statistically equivalent; numpy is
allowed; branch history is rewritten before publication. Implementation runs
unsupervised; pushes and the history force-push need the user.

## 1. Semantics to preserve

These carry over from ADR 0005 and 0017–0032. Everything not listed is
machinery and is deleted.

1. `generate(request) -> bundle`: variable-count 8,760-hour schedules for a
   calendar year 2007 (non-leap, local standard time, no DST, hour `[h,h+1)`).
   Operating hours are sampled, never supplied. Master seed: unsigned 64-bit.
2. Annual budgets: captured from the original source shape before sampling and
   transforms; the effective amplitude is fitted to the emitted integral.
   Fractions are never clipped. Counts, temperatures and activity are not
   energy-normalised. A positive target over a zero realisation is an error.
3. Null means unknown, never zero. Missing operands fail; no fallback schedules.
   Source versus reviewed views, and code-era versus DOE templates, stay
   separate and labelled. No population-equivalence claim.
4. Rule calendars: last matching rule wins, Default row is the fallback,
   holidays select the default day, design days are excluded from integrals.
5. Commercial: ten conditional draws per operating group (one uniform each, in
   fixed order; first cumulative probability strictly greater than the draw;
   a draw beyond a sub-unit CDF errors); group seed
   `sha256([policy, master, group])`; coordinated rooms share draws;
   `peak_occ_frac = 0.231`; base-to-peak ratios with NA meaning "disabled";
   hours inferred from the named occupancy carrier (People-weighted, per family).
6. Residential: cumulative unit seeds (`seed *= position`), streams main,
   hygiene, dishwasher, clothes_washer, clothes_dryer, ev (reserved), cooking;
   stream sharing as in ADR 0020; zero residents skip before any draw;
   annual rotation, daily/month lead, hourly sum, normalise.
7. Mixtures: `q[h] = sum(weight * extent * multiplicity * amplitude * shape[h]) / denominator`;
   bases floor_area (m2), dwelling_unit, person, absolute; heat fractions
   weighted by annual energy; people heat per member; setpoints averaged over
   active members.
8. Source compositions: expand a parent into its real members, generate each,
   area ratio `A_i / A`; original weights validated, never reapplied.
9. Physical services: identity `physical_id` + `source_service_id`, whole mode
   only, extent x multiplicity applied once; booster absolute; water volume
   separate from heater energy; programmes link to required services.
10. Apartments: ResStock single-unit timing with explicit integer N (separate
    from prototype density rho*A); N = 0 keeps fixed rules; caller-unit water is
    1 load + 3 controls and draws no random numbers; common rooms need no N or
    location. The location domain is open (any supported state/coordinates).

## 2. Package layout

```
atlas_schedules/
  __init__.py        generate(), compose()
  __main__.py        CLI: python -m atlas_schedules request.json -o bundle.json
  request.py         JSON Schema (v2) validation -> plain dataclasses
  bundle.py          output assembly
  calendar.py        rule set -> 8760
  budgets.py         annual targets and amplitude fitting
  seeds.py           master/unit/group seed derivation
  resources.py       load packaged data (one manifest, checked at build/test)
  programmes.py      recipe resolution, companions
  mixtures.py
  compositions.py
  services.py        physical service owners and links
  commercial/
    sampler.py       ten-draw conditional sampler
    occupancy.py     People-weighted occupancy fraction (one or many groups)
    hours.py         daily hours-of-operation inference
    parametric.py    to_relative() / apply()
    base_peak.py     base-to-peak ratio adjustment
    design_days.py
    transform.py     pipeline over slots
    families/*.json  slots, modes, People groups, family quirks as data
  residential/
    rng.py           Stream protocol; RubyStream (R1), Pcg64Stream (R2)
    tables.py        source tables
    activity.py      Markov occupant states
    shapes.py        occupancy, plug, TV, fan
    lighting.py      solar lighting model
    events.py        sinks, baths/showers, water, appliance power
    shift.py         rotate, lead, hourly sum, normalise
    generate.py
  apartment/
    recipes.py  unit.py  water.py
  data/              packaged resources
tests/
  answer_keys/       compact native fixtures (.npz + small JSON)
scripts/
  build_resources.py   answer_keys/*.py   capture/*.rb   release.py
```

Style: one statement per line, descriptive names, functions under ~40 lines,
docstrings that cite the upstream file and method, no inline receipts.

## 3. Request v2 (sketch, finalised in M1)

```json
{"schema_version": "2.0.0", "seed": 42, "calendar": {"year": 2007},
 "residential_rng": "pcg64",
 "instances": [{"key": "office-1", "program_id": "...", "inputs": {},
                "extents": {"floor_area": {"value": 500, "unit": "m2", "evidence": "..."}},
                "multiplicity": 1, "operating_group": null, "services": []}],
 "mixture": null}
```

The bundle keeps schedules (8760 values, unit), bindings (annual target,
effective amplitude), constituents and a small metadata/generation block
(package version, seeds, sampled operating parameters, RNG mode).

## 4. Validation

- Answer keys: re-extract compact fixtures from the existing native captures
  (commercial vectors and family natives, retail/restaurant/stripmall natives,
  residential/event vectors and family natives, apartment natives). Keep only
  inputs, discrete outcomes and hourly channels; store arrays as `.npz`.
- Acceptance (ADR 0035): fractions 1e-6 abs, magnitudes 1e-6 rel, annual
  0.01 %, discrete outcomes identical with flips reported.
- Quirk rule: start from the plain algorithm; add an upstream quirk only when an
  answer key fails without it, and name the answer key in its docstring.
- R1/R2 equivalence: 500 seeds on representative configurations (1, 2 and 4
  residents; 3 climates). Two one-sided tests with margins: hourly mean profile
  within 1 % of peak, annual totals within 1 %, daily-total distributions and
  event count/duration/start distributions within a KS-distance margin of 0.03.
  Pass: retire R1 and record the evidence. Fail: ship both and report.
- New families: one offline OpenStudio 3.10.0 answer-key run per configuration
  using the local runtime, run one at a time under the memory watchdog.

## 5. Deletions

Authority locks and transitions (`sources/schedule-generator-*-lock.json`,
`scripts/schedule_generator_runtime_cut*.py`), `data/schedule-generator/apartment/`
proofs, authority, evidence and qualification copies, `apartment_authority*.py`,
`authority_types.py`, `physical_sets.py` proof logic, `contract.py` schema
re-implementation, `canonical.py` hashing, `reproduction.py`, `comparison.py`,
case-matrix and layout-3 scripts, `data/generator-releases/`, schema 1.0–1.2,
`ruby_float_sum` and other sub-tolerance emulation, receipts in outputs, and
tests that only check the above. Large native captures are replaced by compact
answer keys.

## 6. Milestones (fresh ETA per step)

| # | Milestone | ETA |
|---|---|---|
| M1 | Core: request v2, calendar, budgets, seeds, resources, bundle, CLI | 8–12 h |
| M2 | Commercial kernel; six existing families pass answer keys | 15–25 h |
| M3 | Residential rewrite with R1; passes residential and event keys | 8–12 h |
| M4 | R2 mode and the R1/R2 equivalence study | 6–10 h |
| M5 | Apartments, services, compositions, mixtures | 10–16 h |
| M6 | Delete legacy, rewrite docs, new release build | 6–10 h |
| M7 | Remaining families (Stripmall templates, Large Office, hotels, schools, supermarket, hospital, outpatient) with answer keys | 36–72 h |
| M8 | Weather expansion | 6–12 h |
| M9 | Whole-branch review, history rewrite; ask the user to force-push | 4–6 h |

Total about 100–175 h. Work stops only for repeated resource failures (about
three of one kind), destructive or outward steps, or a finding that contradicts
a user decision.
