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

## 7. Status and open items (2026-10-17, after M9)

M1–M5, M8 and M9 are done. M6 is done except the release build, which the user
deferred. M7 built every family, but native answer keys exist only for some of
them (O1).

User decisions on the gap review, 2026-10-17:

| # | Item | Decision |
|---|---|---|
| O1 | Native programme-slot keys for the nine newer families | Done: 534 native cases, 2,834 slots exact (`test_family_programmes_native.py`) |
| O2 | Flat-day zeroing by ComStock's base-to-peak step (data centres, flat weekend days) | Done: documented rule (flat days unchanged), `flat_days="native"` for keys; scan finds 0 zeroed days (was 488 pairs) |
| O3 | Offices and Warehouse still use recipes migrated from the legacy package | Done: all 15 families builder-made; `test_recipes_native.py`; heat fractions restored |
| O4 | Release build and checksum manifest | Not yet (user) |
| O5 | Run the updated CI on GitHub | Not now (user) |
| O6 | Review hygiene: unused `holidays` argument, cross-module test helpers, legacy-key tests that skip silently | Done |
| O7 | Answer-key extraction scripts cannot be rerun (inputs purged) | Accepted (user) |
| O8 | Apartment `residents` capped at 20 per dwelling unit | Done: cap 11, documented |
| O9 | Pre-rewrite objects may persist on GitHub until its garbage collection | Accepted (user) |
| O10 | Local copies of the pre-purge history | Deferred (user), see below |

O1 needs, per family, a native capture with the OpenStudio 3.10 harness
(`scripts/capture/commercial.rb`) running pinned openstudio-standards 0.8.6
and the ComStock measures: occupancy inference, the hours transform, the
occupancy adjustment and base-to-peak. It needs fixed seeds for every
programme slot, compact keys from those captures, and a test like
`tests/schedules/test_commercial_families.py`. The capture also confirms O2
natively.

O2: code reading and the native family keys show that ComStock clears every
equal-valued day after the hours transform. Every sampled Large Office modifies
the weekday plug-load ratio (2,000 of 2,000 draws), so its flat data-centre
equipment schedule becomes zero. No native run of a data-centre schedule has
confirmed this yet.

O3: the migrated office and warehouse recipes carry one configuration per
template (no source/reviewed split) and a single normalised People entry.
Medium Office keeps hot water as a programme slot (the legacy water-pilot
design) rather than a linked shared service. Rebuilding them changes
configuration ids and the water model, so the legacy orchestration keys must
be re-baselined for those owners. The native family keys (926 cases) still
check the schedules.

O8: the cap applies to one dwelling unit, not a building. A building is many
unit instances, and commercial occupancy comes from definitions × floor area,
not `residents`. ResStock samples occupants 0–9 and "10+" (mapped to 11). A
unit with more than 20 residents is rejected with `invalid_request`.

O10 (deferred): the pre-purge history still exists locally in
`refs/backup/stochastic-schedule-extraction-pre-purge`, `refs/original/` (codex
worktree) and the Claude handover branch
`claude/stochastic-schedule-extraction-handover-324832` (dd406bf). Deleting
them and running `git gc` frees the space; do it only when the user asks.

Follow-up decisions, 2026-10-17 (second round): O1 uses one template, both
views and two seeds per family. O2 is deferred here; the user asked for an
independent investigation of five claims, run in a separate session (output
`C:/Users/cl2749/comstock-bpr-investigation/REPORT.md`, outside this repo):
(1) the BPR degenerate-day vulnerability; (2) flat days expanded into equal
points reach it; (3) whether the documented section 4.6.3 data-centre
exemption is implemented; (4) whether the NaN values fail the workflow or
survive into simulation; (5) whether data-centre IT loads are invalid all year.
O3 is approved. O8 aligns the cap with ResStock (0-11, "10+" -> 11), with
documentation. Implementation waits for the user's go-ahead.

O2 investigation result (separate session, `C:/Users/cl2749/comstock-bpr-investigation/REPORT.md`):
- Claims 1, 2 and 5 confirmed by native OpenStudio 3.10 runs of the pinned code.
  A generated ComStock Large Office with a data centre runs hours
  modification, then both BPR measures. Its data-centre equipment (215 and
  484 W/m²) reads 0.0 for all 8,760 hours. Design days stay at 1.0.
- Claim 3 refuted: no data-centre exemption was found in the code read.
  About 55 other upstream measures were not text-searched.
- Claim 4 refuted: the workflow does not fail. OpenStudio rejects each NaN
  value with only a WARN, the measure ignores the return value, and the
  translated IDF has 0. EnergyPlus was not run.
- Correction for this repo: ComStock templates use `OfficeLarge ALWAYS_ON` for
  data centres, while the atlas recipe comes from the plain 90.1-2007
  `DataCenter_EQUIP_SCH`. The mechanism is the same, the source schedule
  differs. Still deferred here.

Upstream report of the O2 bug: deferred (user, 2026-10-17).

Execution decisions, 2026-10-17 (third round). Proceed autonomously with O6,
O8, O3 and O1. O2, O4, O5 and O10 stay out. Commit locally and ask before
pushing.
- O3: legacy-generator comparisons are dropped for the rebuilt office and
  warehouse owners; the native family keys check them instead.
- O1: templates vary per family, with both views and seeds 42 and 51:

| Family | Template |
|---|---|
| Large Office | 90.1-2019 |
| Large Hotel | DOE Ref 1980-2004 |
| Small Hotel | 90.1-2007 |
| Hospital | DOE Ref Pre-1980 |
| Outpatient | 90.1-2019 |
| Primary School | 90.1-2013 |
| Secondary School | DOE Ref 1980-2004 |
| Supermarket | 90.1-2007 |
| Strip Mall | DOE Ref Pre-1980 |

Decisions, 2026-10-18:
- One native template per newer family is sufficient (user).
- Possible zeroing of Medium Office data centres in ComStock is deferred
  (user). The atlas catalogue has no Medium Office data-centre programme.
- Open for discussion: testing the residential-dominant (inverted rule-day)
  path, and retiring the answer-key extraction and migration scripts that can
  no longer run.

Decisions and findings, 2026-10-18 (second round):
- O11 (new): native test of the residential-dominant (inverted rule-day)
  path. The user agreed to this plan:
  1. Natively check the dominance decision for all 150 configurations on
     real prototype geometry.
  2. Capture synthetic residential-dominant cases built from real guest-room,
     patient-room and apartment occupancy.
  3. Stress the default-profile choice: weekends dominant, tied weekday
     profiles, seasonal rules.
  4. Add a compact answer key and test. If our default-day heuristic
     disagrees, port `schedule_ruleset_cleanup_profiles` faithfully.
  Not started.
- O12 (new): retire the answer-key extractors and migration scripts that
  can no longer run. Keep the capture harnesses and the runnable
  `family_programmes.py` pair, and add `tests/answer_keys/README.md` with
  provenance per key and the last commit holding each retired script. The
  user approved this; not started.
- O2 widened. A scan of the packaged catalogue (`build/task-10/bpr_blast_radius.py`;
  all templates and views, seeds 42 and 51) finds the flat-day BPR zeroing
  well beyond data centres. It hits flat weekend profiles: Sunday in Small,
  Medium and Large Office, and Saturday plus Sunday in Primary and Secondary
  School (52 or 104 days a year). 488 programme-slot pairs are affected.
  Measured against the same programme without BPR, the zeroed days hold 2–3 %
  of annual Office lighting, 9–14 % of Small and Medium Office plug loads and
  13–26 % of School lighting and plug loads. Large Office data-centre plug
  loads lose 71–100 %. No other family was affected at these seeds.
  The generator keeps the annual target. Where only some days are zeroed,
  the fitted amplitude raises the remaining days, so weekend load moves onto
  weekdays instead of being lost. Only an all-year zero (data centres)
  raises `zero_generated_integral`. The upstream blast-radius question was
  sent to the separate investigation session. The O2 decision stays deferred.
- O2 upstream result (investigation `REPORT.md` section 8, 3,072 native runs).
  In real ComStock, only data-centre schedules lose whole loads: all
  templates, every sampled data-centre Large and Medium Office. Weekend
  partial-load zeroing appears only under `ComStock 90.1-2004`, which falls
  back to plain 90.1-2004 schedules. Other ComStock templates use non-flat
  15-minute EndUseData schedules. Hospitals, hotels, outpatient and warehouse
  never sample BPR. The atlas catalogue builds from the plain prototype
  schedules, so its weekend exposure (offices, schools) matches the 90.1-2004
  case and overstates real ComStock for DOE Ref and 90.1-2007+. The Sunday
  zeros in published models are explained: inferred hours differ by template.

Decision, 2026-10-18 (third round): O2 is no longer deferred. The generators
fix the flat-day BPR defect by following the documented ComStock/ResStock
method rather than the code. Working reading: a day whose values are all
equal has no defined base-to-peak ratio, so BPR leaves it unchanged, as for
one-value days. Data-centre IT equipment stays constant (reference doc
section 4.6.3). Native-matching behaviour stays available only for
validating against the answer keys. This is recorded as a deliberate
deviation from native ComStock, overriding the ADR 0035 quirk rule for this
case. The investigation session is checking the documented method, the
energy implications and the comparison with published results before
implementation.

O2 method review (investigation `REPORT.md` section 9):
- The documented method is complete only for data centres. Section 4.6.3
  keeps them constant, and the measure leaves one-value days unaltered.
- Leaving flat weekend rules unchanged extends the one-value rule by
  inference; no document states it.
- Upstream `main` still has the defect, and no issue exists. Whether
  ComStock was calibrated around the bug is unresolved: the EULP report
  could not be fetched.
- Recommended rule: in `adjust_day`, a day whose values are all equal (any
  number of points) stays unchanged with sentinel base 1.0. No name-based
  data-centre special case. Keep a native-match mode for the answer keys.
- Deviations to document: data-centre and flat weekend loads are no longer
  zeroed, so energy exceeds native/published ComStock (data-centre Large
  Office about +8 kWh/ft²·yr). Flat weekends are covered by extension, not
  documentation. The atlas data-centre schedule is the plain monthly-step
  `DataCenter_EQUIP_SCH` (mean 0.625), not ComStock's constant 1.0. The
  deviation is against current upstream.

Status, 2026-10-18: O12 done (2ab3861). O2 done (466d796): flat days are
unchanged by base-to-peak, and native mode is kept for the keys. O11 done:
native dominance matches all 150 configurations, and 20 residential-dominant
cases match exactly, including the default-profile stress cases. The
heuristic `_default_days` needed no change.

Residential review decisions, 2026-10-18:
- Seed and stream structure (master seed -> unit seed chain -> seven streams
  per unit; R1 MT19937 replay versus R2 PCG64): reviewed, no change (user).
- O13 (new, approved, later): southern-hemisphere fix for residential
  interior lighting. Keep the astronomical sunset, which already flips
  seasons. Shift the month-indexed empirical terms by six months when the
  latitude is negative: the April-October +1 h offset, the monthly lighting,
  plug-load and appliance multipliers, and the month term of the evening
  width. Document it as a deviation from upstream, which models the US only.
  Not started.
- O14 (new, under discussion): occupancy tables for local models (state or
  multi-state region) derived from ATUS microdata. Upstream ships national
  tables only: 4 occupant-type probabilities, time-inhomogeneous transitions
  (95 steps x 7 states per type and day type, about 32,000 free
  probabilities) and duration tables. Its only regional input is the
  per-state monthly time shift. No derivation tooling is in the pinned
  sources. The user requires local derivation and expects small states (CT,
  RI, even NY) to need regional pooling, e.g. Northeast.
- O14 evaluation (2026-10-18). Option 1, re-weighting the national type mix
  (3 local parameters), is robust to state and county level through
  MRP/shrinkage but misses within-type timing. Option 2, regional chains, is
  higher fidelity only where data are dense and risks noise. Proposed:
  option 1 as the default, option 2 gated by evidence. A
  composition-versus-behaviour decomposition experiment (ATUS 2003-2019,
  census regions, replicate-weight CIs, CT/RI/NY illustration) was delegated
  to a separate session working outside git in
  `D:/atus-composition-behaviour-study` (`REPORT.md`). The O14 method waits
  for its verdict.
- O14 decomposition result (`D:/atus-composition-behaviour-study/REPORT.md`,
  ATUS 2003-2019, 210,586 diaries):
  - The national clustering reproduces ResStock only moderately: profile
    L1 distance about 0.2, and type shares differ by 4-6 points. K-modes
    has many near-equal optima.
  - Composition explains 80-92 % of weekday time at home in the South and
    West, but only about 61 % pooled and 13-44 % at weekends. Within-type
    behaviour, mostly wake and return timing, is above the noise floor in
    the Midwest and Northeast and at weekends, yet small in absolute terms
    (under 0.5 pp of at-home share, about 10 min), against 17-20 pp between
    types.
  - Verdict: option 1 alone is not general; full regional chains are not
    justified. Proposed middle path (inference, untested): option 1 plus a
    few regional timing parameters fitted on region-sized pools, and type
    shares for small states shrunk toward the region (RI about 23-37 %
    direct).
  - Not yet decided by the user.
- O14 scope (user, 2026-10-18): all options stay open: option 1, hybrid-lite
  (option 1 plus re-fitted regional lead table, data only), full hybrid
  (separate morning/evening shifts, new mechanism), and option 2 (regional
  chains). A hybrid-lite test, with every option compared out of sample on
  one metric, was sent to session atus-decomposition.
- O14 hybrid-lite result (`REPORT.md` section 7, profile space, 5x5-fold
  out of sample):
  - Fitted annual leads are tiny (-2 to +3 min); only West fits upstream's
    non-negative convention.
  - Midwest and South: nothing beats option 1 beyond noise.
  - Northeast and West: removed out of sample, share of the behaviour gap:
    annual lead 0.13-0.30, two-shift warp 0.37-0.56, option 2 profile means
    0.72-0.88. Option 2's intervals are wide (+-0.4-0.8) and it is an upper
    bound for real regional chains.
  - Monthly leads overfit, a seasonal pattern that is not regional, and
    rank last. No region shows earlier mornings plus later returns. The
    Midwest's later returns are captured only by regional means.
  - All options remain open; no decision yet.
- O14 DECISION (user, 2026-10-18): option 1. Localize the occupant-type mix
  only; chains, durations and lead shifts stay national. The spatial
  resolution (state, finer or coarser) is under discussion.
- O14 resolution (user, 2026-10-18): the state is the default resolution
  (shrunk toward its census division or region). Grouping ATUS by further
  attributes and user-specified custom mixes are under discussion.
- O14 attribute experiment requested (user, 2026-10-18; only this one run).
  It replaces k-modes with chain-likelihood classification (ResStock chains,
  national prior, optional EM). It ranks person, household and geography
  attributes by out-of-sample log-loss of the type mix, and tests whether
  the state adds information beyond attributes. Primary window 2003-2019,
  sensitivity 2022-2024. Session atus-decomposition, `REPORT.md` section 8.
  Informed by an external Tompkins County case study (chain-likelihood
  classification; age x employment x enrolment cells; ACS PUMS residents
  per dwelling), whose occupancy tilt and time shift were not identifiable
  from group meters.
- O14 attribute result (`REPORT.md` section 8):
  - The chain-likelihood classifier reproduces ResStock's weekday shares
    within 0.8 points (mean top probability 0.88). Weekend diaries are off
    by 7 points and their labels mean something different.
  - Weekday attribute ranking over age x employment x enrolment: full- or
    part-time (+11.9 milli-nats), education (+6.2), children (+3.0),
    partner (+2.6). Tenure, household size, income, sex and metro status
    are negligible; principal city is not in the extract.
  - Attributes explain about 77 % of weekday between-state variance; the
    state adds only about +1 milli-nat.
  - Recommended (inference): national cell probabilities from weekday
    diaries 2003-2019; cells age x employment-4 x enrolment x education x
    partner (256, shrunk hierarchically, pseudo-count about 100); location
    mix = ACS residents x cell probabilities, plus an optional shrunk state
    offset; the same mix applied at weekends. State-specific cells are
    infeasible for small states.
  - Pending user decision.
- O14 decisions (user, 2026-10-19): the ATUS calibration window is
  selectable (pre-COVID 2003-2019, or recent years). Finer-than-state
  resolution comes later. The cell structure leans toward 16 cells (age x
  employed x enrolled); the role of the state with 16 cells is under
  discussion.
- O14 DECISION (user, 2026-10-19): 16 cells (age 15-24/25-44/45-64/65+ x
  employed x enrolled), with national cell probabilities and composition
  only (no state adjustment). A location's mix is its residents across the
  cells. The stray re-serialised `constants_rb.json` (values unchanged,
  written during the ATUS study) was restored. Implementation of O13 and O14
  started.
- O13 done (2026-10-19): southern-hemisphere season shift in `residential/seasons.py`, applied to residential monthly multipliers, fixed-background multipliers, the lighting hour and the evening width; tests in `test_seasons.py`.
- O14 implemented (2026-10-19): `scripts/derive_occupancy_mix.py` (pinned ATUS 2003-2024 and ACS 2024 PUMS, `sources/occupancy-mix-lock.json`) writes `occupancy-mix.json`, with 16 cells x 2 windows and 51 state compositions. `residential/occupancy.py` gives the state mix (children keep national shares). The request option `occupancy` (mix state/national, window 2003-2019/2022-2024) defaults to the state mix, 2003-2019. Native and legacy keys use national. Tests are in `test_occupancy_mix.py`.

Decisions and findings, 2026-10-27 (logged; implement later together with the
remaining decisions):
- O15 DECISION (user, 2026-10-27): commercial power loads (lighting,
  additional lighting, plug loads, gas equipment) and commercial shared
  hot-water services keep their source magnitude (W/m² density, or m³/s peak
  flow) fixed and bind it to the sampled schedule, as ComStock does. Annual
  energy and volume become outputs of each draw. The prototype value ×
  schedule is one candidate draw of what ResStock or ComStock may produce, so
  it is not a target to match. This amends ADR 0021 (annual budgets fixed
  before sampling), ADR 0023 (mixture targets as sums of original targets)
  and ADR 0027 (original per-area volume targets before amplitude binding).
  Not started.
  - Why: the generator holds each load's annual total and refits its
    amplitude (`budgets.fit_amplitude`), so peak power drifts from the
    installed value. A catalogue scan (2026-10-27, seeds 42 and 51, 5,778
    loads) found the peak above the installed value in 53 % of lighting,
    45 % of plug-load, 23 % of gas-equipment and 27 % of shared-water cases
    (up to 1.46× power and 2.11× flow). The annual-energy spread that
    ComStock's hours sampling produces was cancelled.
  - In ComStock, `create_typical_building_from_model` rewrites schedule
    values only; `set_interior_lighting_technology` replaces the density and
    keeps the default schedule; base-to-peak changes schedule values only.
    Nothing rescales power to hold energy.
  - Unchanged: residential dwellings (annual totals by ResStock design),
    fixed programmes, people counts (density × schedule, never fitted),
    apartment plug loads and unit water (untransformed prototype schedules).
- O16 (open): apartment-unit lighting and additional lighting combine a
  prototype density, whose schedule peaks at 0.18, with ResStock timing
  normalised to a peak of 1. A fixed density would give 2.8–3.6× the
  prototype energy (90.1) or about 0.47× (DOE Ref Midrise). The ResStock shape
  carries no installed rating, so these slots stay on the annual binding until
  their budget source is decided (prototype budget, or a ResStock annual
  lighting budget).
- Open findings: ComStock sets lighting density from a sampled lighting
  generation (technology baseline), while the atlas uses each template's code
  density. ComStock's baseline adds no daylighting controls
  (`add_daylighting_controls: nil`); only `upgrade_light_lighting_controls`
  adds them, and it models occupancy sensors as a density reduction. ADR 0044
  records the PNNL prototypes' controls instead.
