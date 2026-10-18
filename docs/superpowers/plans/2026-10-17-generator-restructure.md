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
