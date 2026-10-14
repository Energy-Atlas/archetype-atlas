# Pure Python schedule generator implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or superpowers:subagent-driven-development to implement this plan task by task. Steps use checkbox syntax for tracking. The user has accepted this revised plan for implementation. Execute natively in the isolated worktree; use the required independent final review, without dispatching implementation agents.

**Goal:** Progressively ship a source-faithful pure Python generator and referenced program contract, with seeded temporal variation and conserved known annual residential/commercial targets.

**Architecture:** Extract immutable source mechanisms, probability tables and reference definitions into a local resource package. Generate complete related channel sets per constituent or commercial operating group, bind annual budgets to the actual emitted schedules, then compute mixtures. Preserve fixed channels, controls, source rules, provenance and frozen reference releases separately from generated realizations.

**Tech stack:** Python 3.11 and 3.14, standard-library runtime, JSON, SHA-256, unittest, and the repository's existing JSON Schema tooling for build/test validation. Ruby/OpenStudio is confined to opt-in development reference capture. Ship an independent ZIP distribution; no new runtime service or dependency is required.

**Spec:** [Generator design](../specs/2026-10-13-schedule-generator-design.md), revised 2026-10-14 to incorporate the user's five plan-review comments and two final adjustments. [Review response](../../reviews/schedule-generator-plan-comments-2026-10-14.md) records the source checks and resulting changes.

## Global constraints

- Work exclusively in `codex/stochastic-schedule-extraction` and its attached worktree; preserve other ongoing developments.
- Generation runs entirely in Python. Ruby, OpenStudio, EnergyPlus, external services and network access are not required to generate a packaged realization.
- The generator returns a variable number of schedules, each with exactly 8,760 hourly samples.
- Use an explicit non-leap Gregorian year; the initial default remains 2007 to match the atlas references. Reject leap years rather than dropping February 29.
- Hourly values describe `[hour, hour+1)` in local standard time. Apply no implicit DST, timezone conversion or holiday calendar.
- Require an explicit unsigned 64-bit master seed; reject booleans and invalid numeric values.
- Commercial operating hours are sampled from the supplied seed, rather than required as caller-selected hours. Complete the ComStock per-parameter sampling/context audit before its kernel implementation; disclose the standalone seeded adaptation and never claim population-realization equivalence without validating full upstream context.
- Apply annual-total conservation to both residential and commercial loads, including commercial definitions originally expressed as design power or power density with a reference schedule.
- Conservation refers to the load-weighted annual integral. Distinguish the known aggregate/reference target from the schedule-conditioned effective magnitude, which is a normalization amplitude and not necessarily installed/nameplate capacity. Non-energy controls and resident counts retain their defined semantics.
- Keep fractional schedules in their valid range by changing effective magnitudes rather than multiplying fractions above one.
- Generate constituent schedules before computing mixtures; preserve upstream residential RNG order/coupling and coordinated commercial operating groups. Source fidelity takes precedence over insertion/removal invariance.
- Preserve actual source/template identity, SI units, physical hosts, fuels, scaling bases, shared-service identity and only the rule/special-profile semantics required by the selected source. Do not introduce a generalized scheduling language.
- Retain the existing exclusions of residential EV and HVAC equipment-unavailability overlays, plus existing program-scope exclusions.
- Freeze source revisions and SHA-256 locks, keep raw artifacts immutable, retain upstream notices and do not invent missing inputs or appliance shares.
- Frozen releases and existing Program JSON v3 remain immutable reference cases; do not regenerate them into a new meaning.
- Before every commit inspect the staged diff and run `python -m scripts.audit --staged`; use neutral automated authorship and an `Agent-Model` trailer recording unavailable details as unavailable.
- Production integration requires a protected `main` PR, required checks and resolved review conversations. This plan does not authorize a separate production deployment or changes in another chat.

## Review focus

1. A new seed or longer commercial operating day must not change any included load's annual target; test emitted values and effective magnitudes together (Tasks 2, 6, 8).
2. Preserve native unit/end-use initialization, ordering and coupling even when insertion/removal changes output. Test independence only where upstream provides it; keep commercial groups coordinated (Tasks 3, 5, 8).
3. Missing source inputs, aggregate appliance shares or positive-budget zero-integral channels must fail explicitly, while declared absences remain zeros (Tasks 2, 7, 8).
4. Overnight/zero/full-day commercial hours and source-required selectors must survive transformations. Do not invent ResStock special-day behavior (Tasks 3, 6).
5. The first family milestone must work offline outside the repository; numerical equivalence must pass despite harmless serialization changes, while frozen-resource tampering must fail (Tasks 1, 2, 9).

## Delivery milestones

M1 is exactly the ten cases in [`sources/schedule-generator-m1-scope.json`](../../../sources/schedule-generator-m1-scope.json): six frozen `MultiFamily5PlusLowRise` household configurations with their individually bound station-proxy weather, and four Medium Office 90.1-2013 Office/Plenum source/reviewed views. Each case identifies its exact program, configuration reference, weather, template/vintage and calendar. The manifest is authoritative for the target set and currently says `planned_not_shipped`; it makes no implementation/support claim. M1 uses year 2007; seed, explicit physical scaling, repetition and compatible mixture assembly remain variable. Additional household configurations, weather substitutions, templates and calendar years are later scope additions, not an implicit cross product.

Task 1 must resolve the one named commercial sampling configuration in the audit, including exact external dependency selectors and probability rows, before commercial kernel implementation. A discovered weather dependency requires a versioned explicit case binding. The audit and scope gate remain closed until resolved; no guessed selector/default can complete them. The existing six residential proxy contexts retain their full source labels and hashes.

Complete M1 coverage means complete evidence for **every listed case and every included active/default/fixed/control slot**, plus repeated units, conservation, compatible mixtures and standalone operation. Copy the exact scope manifest/version/hash into the shipped milestone manifest, with its resolved configuration/resource references and per-case evidence. Do not shrink the denominator to successful cases or silently drop a blocked case; changing the set requires an explicit versioned scope revision. Ship after Task 9. Broader catalogue and DOE-location coverage remain later objectives.

M2 and later add families, templates and weather/location domains through Task 10. Each addition repeats source parity, conservation, binding/mixture and standalone checks, then ships a new immutable version. Full catalogue coverage remains the eventual objective. Every milestone reports generated, source-fixed, absent, requires-binding, unsupported and excluded scope explicitly; coverage outside the declared milestone may remain unsupported without invalidating M1.

## Boundaries and files

Keep runtime modules independent of `scripts.*`, which imports repository paths and build dependencies. Build scripts may reuse existing fetch, definition, export and release helpers. Runtime data is a generated inspection of locked sources, not a hand-written substitute for calibration data.

| Files | Responsibility |
| --- | --- |
| `atlas_schedules/contract.py`, `canonical.py`, `errors.py`, `comparison.py` | Strict JSON, scoped references, source/resource encoding, errors and numerical comparison |
| `atlas_schedules/resources.py`, `atlas_schedules/data/` | Verified packaged source tables, recipes, references and weather features |
| `atlas_schedules/budgets.py` | Reference targets, emitted-value integrals and effective intensity/flow |
| `atlas_schedules/seeds.py`, `calendar.py`, `ruby_random.py` | Source seed allocation/draws and calendar evaluation limited to upstream semantics |
| `atlas_schedules/residential/activity.py`, `events.py`, `shapes.py` | ResStock activity chains, dependent events and occupancy/location-dependent shapes |
| `atlas_schedules/commercial/sampling.py`, `parametric.py` | ComStock conditional operating samples and source schedule transformations |
| `atlas_schedules/companions.py`, `programs.py` | Source-fixed/default/control channels and generated program slot bindings |
| `atlas_schedules/mixtures.py`, `generator.py` | Constituent orchestration, conserved compositions and public API |
| `atlas_schedules/__init__.py`, `__main__.py` | Public import and offline JSON CLI |
| `scripts/schedule_generator_sources.py`, `schedule_generator_build.py` | Locked extraction and resource/catalogue compilation |
| `scripts/schedule_generator_reference.py`, `reference_schedule_generator.rb` | Opt-in upstream development fixture capture |
| `scripts/schedule_generator_coverage.py`, `schedule_generator_release.py` | Applicability/coverage evidence and reproducible independent distribution |
| `schemas/schedule-generator-{request,bundle,program}-v1.schema.json` | Separate versioned request, output and program-reference contracts |
| `sources/schedule-generator-{lock,policy}.json`, `sources/schedule-generator-m1-scope.json`, `data/schedule-generator/comstock-sampling-audit.json`, `docs/adr/0017-python-schedule-generators.md` | Mechanism bindings, interpretation policy, exact milestone scope, sampling preflight and approved architecture |

Create package `__init__.py` files only with the task that supplies the package's functionality. New tests use `tests/test_schedule_generator_*.py`; keep fixtures under `tests/fixtures/schedule-generator/`. New research artifacts use `data/schedule-generator/` and a new `data/generator-releases/v0.1.0/`, leaving historical bundles untouched.

## Shared interface decisions

`generate(params: dict, seed: int) -> dict` is the public API. The CLI reads `{schema_version: "1.0.0", params: {...}, seed: ...}` and produces the same bundle. Input JSON rejects duplicate keys, NaN, infinity and unknown operand fields. Validation errors use `GeneratorError(code: str, path: str, message: str)` with instance/channel context.

`params` contains `resource_set_id`, `calendar`, `instances`, and optional `mixture`. `calendar` contains `year`, `clock: "local_standard_time"` and explicit `holidays` (default empty). Each instance contains `key`, `program_id`, `inputs`, `basis_bindings`, and nullable `operating_group`. Household inputs carry residents, bedrooms, installed end uses and required location/weather keys. The source recipe enumerates its required inputs; missing values cannot inherit unrelated fixture values.

`mixture` contains `program_id`, nullable `composition_id`, and members `{instance_key, weight}`. Weights are finite, nonnegative and sum to one for normalized area mixtures; non-area multiplicity is explicit in `basis_bindings`, never disguised as a weight. Known catalogue compositions supply their recorded weights; repeated instances need an explicit allocation of those weights. Without a mixture, return the requested individual program bindings.

Bundle keys are `schema_version`, `algorithm_version`, `schedules`, `bindings`, `constituents`, `generation`, and `metadata`. Each schedule has `id`, `unit`, `year`, `clock`, `timestep_minutes: 60`, and `values` of length 8,760. A load binding identifies `instance_key`, `program_id`, `demand_id`, `slot`, `schedule_id`, `fuel`, `host`, `budget_method`, and a scaling receipt. It carries separate `reference_target` and `effective_magnitude` objects: the former contains known quantity/total/unit/basis/evidence, and the latter contains realization-conditioned value/unit/basis. Control bindings omit inapplicable magnitude/fuel fields rather than carrying fake zeros.

Source kernels return `GeneratedChannels = {channels: {slot: list[float]}, source_context: dict}`. Program resolution returns `{recipe_id, inputs, slots, demands, controls, shared_services, evidence}`. A bound constituent contains these resolved objects, emitted schedules, magnitude bindings and seed/parameter receipts. Tasks below own each producer; later tasks consume these interfaces rather than reconstructing reference magnitudes from generated outputs.

Use strict finite JSON; canonical UTF-8/LF encoding is a convenient format for source/resource tables, not scientific equality of generated bundles. `canonical(value: object) -> bytes` lives in `canonical.py` for those artifacts. `schedule_id(instance_key: str, slot: str) -> str` supplies unambiguous, percent-escaped scoped references without hashing floating-point output. Record algorithm/source/resource versions, actual seeds, source-significant order and parameters independently of these IDs.

`finalize_channels(generated: dict) -> dict` validates finite values and applies only a recorded upstream export precision when that representation is selected. It does not round to nine decimals for portability. Budget binding uses the actual emitted values; no post-mixture clipping/rounding may break conservation.

`compare_bundles(actual: dict, expected: dict, policy: dict) -> list[str]` in `comparison.py` resolves schedules through constituent/demand/slot references rather than opaque IDs or JSON byte order. Compare units, calendar, included channels, annual targets, source-significant parameters and discrete decisions exactly where appropriate. Ignore irrelevant formatting, key order and administrative paths/timestamps. Continuous tolerances are named in `sources/schedule-generator-policy.json` and recorded with each comparison:

- Dimensionless fractions: `rel_tol=1e-6`, `abs_tol=1e-8` against raw reference values.
- Temperatures in degrees C: `rel_tol=0`, `abs_tol=1e-4`.
- Activity in W/person: `rel_tol=1e-6`, `abs_tol=1e-6`.
- Annual energy/reference-load integrals: `rel_tol=1e-8`, `abs_tol=1e-8` in the declared integral unit; annual volume: `rel_tol=1e-8`, `abs_tol=1e-12` m3.
- If the only source reference is an exported three-significant-digit CSV, compare within its quantization interval plus the raw-value tolerance; do not demand full-precision equality to rounded exports. Record that precision explicitly.

Exact discrete decisions and compatible RNG draw vectors remain required where upstream permits them. A changed event/selected option is not excused by a continuous tolerance. Generated arrays are accepted by numerical/source equivalence across supported/common environments, not equal SHA-256 hashes. Immutable archives, resources, packaged manifests and frozen artifact bytes retain checksum/integrity verification.

## Execution checklist

### Task 1: Lock mechanisms and compile inspectable source resources

**Files:** Complete `sources/schedule-generator-m1-scope.json` and create `data/schedule-generator/comstock-sampling-audit.json`; create `scripts/schedule_generator_sources.py`, `scripts/schedule_generator_build.py`, `sources/schedule-generator-lock.json`, `sources/schedule-generator-policy.json`, `atlas_schedules/{resources,errors,canonical}.py`, `atlas_schedules/data/manifest.json`, and `docs/adr/0017-python-schedule-generators.md`. Test `tests/test_schedule_generator_resources.py`.

**Consumes:** Existing source/runtime/weather locks, approved spec, authoritative planned M1 scope manifest, [sampling preflight](../../reviews/comstock-sampling-semantics-2026-10-14.md), frozen v0.1.1 definitions, v0.4.0 resolutions, residential recovered inputs, and new inspection lock.

**Produces:** `GeneratorError(code: str, path: str, message: str)`; `canonical(value: object) -> bytes`; `schedule_id(instance_key: str, slot: str) -> str`; `extract_sources(lock: dict, cache_root: Path, destination: Path) -> dict`; `build_resources(destination: Path, scope: str) -> dict`; `ResourceSet(root: Path, expected_id: str)` for validated resource directories; `ResourceSet.load(resource_set_id: str) -> ResourceSet` for packaged resources; `ResourceSet.get(kind: str, key: str) -> dict`. Resource kinds are `residential`, `commercial`, `weather`, `program`, `composition`, and `reference`. Source CLI accepts `--lock`, `--cache-root`, `--destination` and `--verify-only`; build CLI accepts `--scope` and `--destination`.

- [ ] Before any commercial kernel implementation, complete a per-selected-parameter audit against the pinned sampler and actual TSV archive: source configuration/version/stock year, ordered dependency closure, exact conditioning inputs, row/option order, allocated group dimensions/vector positions, sample index/count, bucket layout, precomputed allocation and sampler mode. Determine which values are locally selectable after conditioning and what full upstream context is needed to reproduce a population row. The inspected pseudorandom path uses NumPy global matrices; Sobol additionally uses Python random shifts and a pandas shuffle. Neither has a seed argument in this file. Record any external initialization evidence rather than inventing it.
- [ ] Resolve the named `medium_office_90_1_2013` configuration and freeze its exact selector/resource bindings in `comstock-sampling-audit.json`. Set `gate_status: passed` only after every selected field has a decision. Use the explicitly labeled `atlas_conditional_seeded_v1` adaptation for the standalone interface, with `population_realization_equivalent: false`; record RNG algorithm/seed derivation/draw order and comparison boundaries. Preserve conditional/source-transform parity without asserting identical population matrices or Sobol behavior. Missing tables/selectors block this gate and the commercial port.
- [ ] Validate all ten M1 cases against their frozen program/configuration/weather/template references and checksums; keep source/reviewed views distinct. Bind every commercial conditioning selector explicitly and certify the declared weather independence before passing the scope gate. No wildcard domain, proxy substitution or unsupported-only denominator is allowed. Add meaningful resource/scope tests `test_m1_exact_case_set`, `test_m1_wrong_configuration_weather_or_template_rejected`, and `test_commercial_sampling_gate_blocks_unresolved_port`.
- [ ] Write `test_resource_hash_and_inventory_rejection` (changed/deleted/extra members raise `resource_integrity`), `test_unsafe_archive_member_rejection`, `test_probability_resource_is_required`, and `test_resource_identity_ignores_destination` (two extractions have identical ordered tables, provenance and manifest identity).
- [ ] Run `python -m unittest tests.test_schedule_generator_resources -v`; confirm the specific missing implementation or integrity assertion fails.
- [ ] Trace the pinned ComStock configuration to an explicit public TSV archive version and the required Standards 0.8.6 schedule methods. Record rationale, public URL, revision, bytes, SHA-256, extracted-member hashes and upstream notices. Extract the complete ResStock activity/event resource dependency closure needed by M1 from its already locked archive. Bind the exact weather inputs required for the declared pilot contexts and retain their variant labels. Acquire further DOE locations, templates and companion defaults with later families rather than gating M1 on all 16 cases.
- [ ] Implement the interfaces above. Reject incomplete conditional-distribution rows, malformed probabilities, unsupported dependency cycles and unsafe resource paths. Compile compact canonical resources with per-field provenance and an ordered numerical-table representation. Never execute downloaded sampler code during extraction.
- [ ] Run the resource tests and `python -m scripts.schedule_generator_build --scope pilot --destination build/generator-pilot-resources`; require verified hashes and an explicit dependency inventory. Any unavailable material source becomes a named blocked extraction family, not guessed data or a completed family.
- [ ] Inspect/audit and commit `data(schedules): lock generator mechanisms and compile pilot resources`.

### Task 2: Define contracts and conserved magnitude bindings

**Files:** Create `atlas_schedules/{contract,budgets,comparison}.py`, the three v1 schemas, and request/binding fixtures. Test `tests/test_schedule_generator_contract.py` and `test_schedule_generator_budgets.py`.

**Consumes:** Shared interface decisions and Task 1 resources, canonical encoding, identities and typed errors.

**Produces:** `validate_request(params: dict, seed: int) -> None`; `validate_bundle(bundle: dict) -> None`; `finalize_channels(generated: dict) -> dict`; `reference_budget(demand: dict, reference_values: list[float]) -> dict`; `bind_budget(target: dict, values: list[float]) -> dict`. Budget targets contain `quantity`, `total`, `unit`, `basis`, `method`, and original evidence; binding output contains separate `reference_target` and `effective_magnitude` objects plus its scaling receipt. Also produce `compare_bundles(actual: dict, expected: dict, policy: dict) -> list[str]`.

- [ ] Write `test_res_and_com_reference_budget_conservation`: for each source family, 10 W/m2 × 2,000 reference hours yields 20,000 Wh/m2; 1,600 generated hours gives 12.5 W/m2, and 2,400 hours gives 8.333333333333334 W/m2 while preserving that total. Add `test_direct_annual_definition_precedes_rounded_power`, `test_volume_seconds_conversion`, `test_zero_unknown_and_unrealized_targets`, `test_strict_8760_contract`, and `test_controls_are_not_energy_scaled` with the outcomes below.

```python
target = reference_budget(demand_10_W_m2, reference_2000_hours)
assert target['total'] == 20000
bound = bind_budget(target, emitted_1600_hours)
assert bound['effective_magnitude']['value'] == 12.5
assert math.fsum(emitted_1600_hours) * bound['effective_magnitude']['value'] == 20000
# Positive targets with all-zero samples raise GeneratorError with
# code='zero_generated_integral'; unknown targets raise unresolved_annual_target.
```
- [ ] Run `python -m unittest tests.test_schedule_generator_contract tests.test_schedule_generator_budgets -v`; observe the intended failures.
- [ ] Implement strict request/bundle validation, scoped references and the numerical comparator. Add `test_equivalent_values_ignore_serialization_and_ids` and `test_discrete_decision_and_large_numeric_changes_fail`; rearranged JSON keys/formatting and harmless numeric representation changes pass, while changed event decisions or out-of-tolerance values fail. Use `math.fsum` of emitted values. Direct annual targets take precedence; otherwise use the original reference magnitude and calendar-compatible reference schedule. Keep fractional outputs bounded by adjusting magnitude. Positive target with zero integral raises `zero_generated_integral`; unknown target raises `unresolved_annual_target`; no retry, clipping or seed substitution.
- [ ] Validate energy/volume conservation with the named tolerance policy above. Scaling bases and fuels remain distinct. Add `test_normalization_amplitude_is_not_nameplate`: a schedule-conditioned amplitude is not automatically capped/rejected by a reported installed rating. A separately requested physical capacity constraint raises `infeasible_intensity` if incompatible and is reported as an additional model condition. Validate schemas against their example objects with the existing JSON Schema tooling.
- [ ] Rerun both modules; require all tests passing and per-demand provenance, input immutability, fraction bounds and rounding-integral consistency.
- [ ] Inspect/audit and commit `feat(schedules): add referenced contracts and annual budget binding`.

### Task 3: Preserve source RNG allocation and necessary calendar semantics

**Files:** Create `atlas_schedules/{seeds,calendar,ruby_random}.py`, `scripts/schedule_generator_reference.py`, and `scripts/reference_schedule_generator.rb`; extend the resource build with golden draw capture. Test `tests/test_schedule_generator_seeds.py`, `test_schedule_generator_calendar.py`, and `test_schedule_generator_random.py`.

**Consumes:** Task 1 canonical encoding/errors and source resources, plus Task 2 contract validation.

**Produces:** `assign_unit_seeds(master: int, ordered_keys: list[str]) -> dict[str, int]`; `SourceRandom(seed: int)` with `random() -> float`, `randbelow(limit: int) -> int`, `getstate() -> dict` and `setstate(state: dict) -> None`; `evaluate_rules(schedule: dict, year: int, holidays: list[str]) -> dict` returning annual `values` and optional source-required `special_profiles`. This is an adapter for actual source rule objects, not a new public rule language.

- [ ] Write `test_master_seed_domain_and_unique_keys`, `test_native_multifamily_seed_sequence`, `test_source_random_matches_golden_draws`, and `test_random_state_roundtrip`. Master seed 42 yields native ordered unit seeds `[42, 84, 252]`; seed 0 remains 0 for all units as upstream does. Reject boolean/negative/overflow master inputs and duplicate keys; permit native derived integers larger than 64 bits. Compare golden draws/state restoration exactly where upstream permits. Add `test_non_leap_hourly_calendar` and `test_only_source_required_special_profiles`: 8,760 in 2007, rejection of 2008, actual source selectors/precedence preserved, and no invented ResStock holiday/design profile.
- [ ] Run `python -m unittest tests.test_schedule_generator_seeds tests.test_schedule_generator_calendar tests.test_schedule_generator_random -v`; verify failures.
- [ ] Inspect/capture upstream initialization, ordered stream allocation and draw call sites before porting. Implement native cumulative unit-position multiplication and preserve source-significant request order; do not promise insertion/removal/reordering invariance. Port the required Ruby initialization/draw behavior, including source-native larger derived seeds. Retain the original six end-use seed slots and actual shared/coupled calls; do not create per-appliance streams beyond upstream. Record any necessary batch/group adaptation explicitly rather than silently changing the source mechanism.
- [ ] Port only the rule/calendar semantics required by inspected commercial or companion source objects into a runtime adapter. Retain their selectors/order and source-provided profiles; do not apply that adapter as a new ResStock activity rule layer. Validate holiday dates against the requested non-leap year. Keep special-day profiles out of annual integrals unless an explicit holiday date selects one.
- [ ] Rerun all three modules against independently captured, checksum-identified draw/rule vectors; require exact random draw matches and disclosed numerical tolerance for schedule values.
- [ ] Inspect/audit and commit `feat(schedules): preserve source RNG and calendar behavior`.

### Task 4: Port ResStock occupant activities and dependent shapes

**Files:** Create `atlas_schedules/residential/{activity,shapes}.py`; extend `scripts/schedule_generator_reference.py` and `scripts/reference_schedule_generator.rb`. Test `tests/test_schedule_generator_residential_activity.py` and `test_schedule_generator_residential_shapes.py`.

**Consumes:** Pinned ResStock resources from Task 1, source-compatible draws and calendar from Task 3. Development capture reuses locked runtime verification and existing `scripts/run_residential_profiles.rb`; ordinary tests read local golden JSON only.

**Produces:** `simulate_activities(inputs: dict, unit_seed: int, resources: ResourceSet) -> dict`; `occupancy_shapes(activities: dict, inputs: dict, resources: ResourceSet) -> GeneratedChannels`. Activity output carries per-occupant state traces, main-stream state, unit offset and end-use seeds for Task 5.

- [ ] Write `test_activity_trace_matches_source_fixture`, `test_multiple_residents_and_offset`, and `test_weather_changes_only_dependent_shapes`. Assert exact state/duration/offset golden traces and draw order for weekday/weekend/state cases, occupancy within `[0,1]`, separate one/multiple-resident cases, and unchanged core transitions when only weather changes. Lighting and fan channels must match their location/weather fixture results.
- [ ] Run `python -m unittest tests.test_schedule_generator_residential_activity tests.test_schedule_generator_residential_shapes -v`; observe failing kernel/reference assertions.
- [ ] Implement the internal 15-minute activity mechanism and the source minute-level shift/aggregation sequence before hourly emission. Generate occupancy, interior/garage lighting, applicable plug/TV and fan shapes together. Preserve appliance/garage presence, main/end-use stream relationships and the source's zero-resident skip boundary.
- [ ] Capture checked upstream intermediate traces and emitted channels using an explicit `python -m scripts.schedule_generator_reference --family residential --destination build/generator-reference-residential` development command. Include source/runtime/resource/input hashes; execute no sizing or EnergyPlus. Require exact supported discrete traces/draws and numerical equivalence of continuous channels under the named tolerance/export-precision policy. Record deliberate adaptations separately; do not force byte or full-precision equality to rounded CSV.
- [ ] Rerun activity/shape tests offline; independently vary location/state/weather and assert only source-dependent channels change. Confirm no actual resident-count or activity-W/person scaling occurs.
- [ ] Inspect/audit and commit `feat(schedules): port residential activities and coordinated shapes`.

### Task 5: Port residential appliance and water events

**Files:** Create `atlas_schedules/residential/events.py` and its public `__init__.py`; extend reference capture and resource compilation. Test `tests/test_schedule_generator_residential_events.py`.

**Consumes:** Task 4 activity traces/stream state and Task 1 duration, consumption, event cluster, draw and monthly data.

**Produces:** `generate_events(activities: dict, inputs: dict, resources: ResourceSet) -> GeneratedChannels`; `generate_residential(inputs: dict, unit_seed: int, resources: ResourceSet) -> GeneratedChannels` in `residential/__init__.py`, composing Tasks 4–5.

- [ ] Write `test_activity_events_match_source_fixture`, `test_absent_appliances_and_zero_use`, `test_end_use_change_matches_upstream_coupling`, and `test_water_normalization_after_shift`. Assert cooking/washer/dryer/dishwasher and all included water channels match their source fixture, absent channels carry absence receipts, changed-present/absent end uses reproduce upstream's actual shared-draw consequences, and output sums/bounds match its normalization stage. Add `test_excluded_ev_output_retains_seed_slot` so omitting EV output does not remove its upstream seed draw or shift cooking's seed.
- [ ] Run `python -m unittest tests.test_schedule_generator_residential_events -v`; observe intended failures.
- [ ] Port source event ordering, correlations, durations and power/water draws; retain internal normalization semantics. These shape samples never replace definition-derived annual energy/volume. Emit only applicable channels and explicit absence receipts; EV remains excluded.
- [ ] Extend development captures to full related channel sets for occupied single-unit/multifamily cases and the existing frozen fixture inputs. Verify per-channel component parity before budget binding, then use Task 2 to check annual totals from original recovered definitions. Include a positive-budget/no-event seed that fails explicitly instead of returning zero or drawing another seed.
- [ ] Rerun the event, activity, shape and budget modules offline; require source-correct correlations and coupling. Assert unchanged streams only for branches proven independent by upstream capture; never change the RNG layout just to satisfy invariance.
- [ ] Inspect/audit and commit `feat(schedules): port residential appliance and water events`.

### Task 6: Port commercial sampling and source transformations

**Files:** Create `atlas_schedules/commercial/{sampling,parametric}.py`; extend reference capture and source build. Test `tests/test_schedule_generator_commercial_sampling.py` and `test_schedule_generator_commercial_parametric.py`.

**Consumes:** Task 1 passed commercial sampling audit, resolved exact M1 configuration, selected conditional TSV resources and actual Standards runtime methods, Task 3 source-calendar adapter, and Task 2 budgets/comparison policy. Refuse to begin the commercial kernel with unresolved audit fields; follow the recorded standalone adaptation rather than implying equivalence to population-matrix draws.

**Produces:** `sample_operating_parameters(inputs: dict, group_seed: int, resources: ResourceSet) -> dict`; `transform_commercial(channels: dict, operating: dict, source_context: dict) -> GeneratedChannels`. Sampling returns both effective values and source distribution-row/option/draw receipts, plus explicit sampler policy, RNG/version, conditioning inputs, adaptation and `population_realization_equivalent: false`.

- [ ] Write `test_standalone_sampling_policy_and_context_are_explicit`, `test_wrapper_seed_reproducibility`, `test_no_population_equivalence_claim`, `test_operating_sample_matches_conditional_row`, `test_cumulative_probability_boundaries`, `test_na_flags_and_missing_dependencies`, `test_overnight_zero_and_full_day_transforms`, and `test_constants_ramps_and_design_days_match_source`. Compare conditional selection with identical stored uniform draws and resolved rows; test the wrapper's seed-to-draw reproducibility separately. Do not compare an arbitrary population row and local wrapper by seed alone. Assert exact expected options for stored draw/row pairs, `NA` flag behavior, errors for unknown selectors, and fixture-equivalent values/rules for 0/24-hour and overnight cases. No request supplies operating hours; unrelated group draw receipts differ.
- [ ] Run `python -m unittest tests.test_schedule_generator_commercial_sampling tests.test_schedule_generator_commercial_parametric -v`; observe intended failures.
- [ ] Port source conditional selection and the actual operating-hour inference/formula/transformation dependency closure. Retain occupancy adjustment and lighting/equipment base-to-peak logic where the selected source configuration applies them. Sample only source-required schedule parameters; do not resample intensity, geometry or stock attributes. Reject missing dependency bindings rather than selecting a guessed national/California or building-type substitute.
- [ ] Capture a Medium Office reference matrix with native, short, long, overnight, zero/full-day and weekday/weekend cases. Compare pre-normalization transforms to the pinned upstream methods and store source inference context. Then bind the unchanged pre-sampling reference budgets: short and long schedules must have different effective magnitudes and identical annual totals. Compare declared constant and design-day behavior separately.
- [ ] Rerun the sampling/parametric/calendar/budget modules. Require exact selected options/discrete decisions where the source draw method permits, continuous kernel equivalence under the named tolerance/export-precision policy, and unchanged known annual targets. Record any seeded standalone wrapper adaptation to upstream batch sampling.
- [ ] Inspect/audit and commit `feat(schedules): port seeded commercial operating distributions`.

### Task 7: Compile program recipes and companion schedules

**Files:** Create `atlas_schedules/{programs,companions}.py`, `data/schedule-generator/programs.json`, `compositions.json`, `catalogue-index.json`, and `coverage.json`; extend `scripts/schedule_generator_build.py` and policy. Test `tests/test_schedule_generator_programs.py` and `test_schedule_generator_companions.py`.

**Consumes:** Frozen definitions through `scripts.definition_release.read_bundle`, ready v3 exports through `scripts.program_json_v3.ProgramExporter`, original recovered annual magnitudes through `scripts/recover_program_inputs.py`, and the kernels/resources from Tasks 1–6.

**Produces:** `resolve_program(program_id: str, inputs: dict, resources: ResourceSet) -> dict`; `generate_companions(resolved: dict, resources: ResourceSet) -> GeneratedChannels`. Program records contain schedule slots, required inputs, original/reference budgets, source method and applicability.

- [ ] Write `test_original_budgets_precede_reference_fitted_magnitudes`, `test_reference_commercial_budget_is_pre_sampling`, `test_companion_controls_and_backgrounds`, `test_zero_resident_preserves_installed_refrigeration`, and `test_missing_appliance_shares_are_unsupported`. Assert original annual-kWh precedence, stable commercial targets across samples, correct nominal/fixed channels, retained background demand, distinct fuel/host identities and explicit unsupported aggregate mappings. Program exports must expose resolvable schedule slots.
- [ ] Run `python -m unittest tests.test_schedule_generator_programs tests.test_schedule_generator_companions -v`; observe failures.
- [ ] Compile M1 source/reviewed views separately, preserving accepted v3 defaults and receipts. Include a compact full-catalogue ID/status index so unsupported families are visible without extracting all their physical resources. Map apartment units to ResStock time allocation with actual definition-derived annual targets; leave apartment common spaces and hotel guestrooms on applicable source methods. Require explicit household presence/location parameters. Recover source-backed aggregate end-use mappings; absent decomposition is `unsupported_binding`, never guessed appliance shares or borrowed unrelated-fixture magnitudes.
- [ ] Implement thermostat translation/correction and each included source-fixed/default companion recipe as Python or explicit compiled source rule tables. Match the definition's selected fixed-versus-conditional default. Temperature-dependent channels require their actual bound temperature input; retain existing explicit fixed-background variants where those are the selected definitions. Include shared services once with their physical identities.
- [ ] Build `--scope pilot` recipes for Medium Office and occupied/vacant repeated apartment cases. Rerun program/companion/kernel/budget modules and validate their reference closure, no unknown active operands, same-source fixed values and unchanged frozen definitions.
- [ ] Inspect/audit and commit `feat(programs): compile generator recipes and companion channels`.

### Task 8: Complete end-to-end family generation and mixtures

**Files:** Create `atlas_schedules/{generator,mixtures}.py` and public `__init__.py`; add complete pilot request/bundle examples under `docs/examples/schedule-generator-v1/`. Test `tests/test_schedule_generator_pilot.py` and `test_schedule_generator_mixtures.py`.

**Consumes:** Task 7 resolved programs, Tasks 4–6 kernels, Task 3 source-native RNG allocation and Task 2 annual binding.

**Produces:** Public `generate(params: dict, seed: int) -> dict`; `compose_constituents(constituents: list[dict], mixture: dict, calendar: dict) -> dict`.

- [ ] Write `test_medium_office_and_two_apartment_pilots`, `test_source_unit_order_and_coordinated_commercial_group`, `test_mixed_families_and_29_members`, and `test_group_conflict_and_shared_service_identity`. Assert 8,760 values per channel, same-request discrete/numerical equivalence, native unit-order/stream receipts, identical within-group operating samples and explicit `operating_group_conflict`. Reordering units is allowed to change their source-assigned seeds. Do not compare generated JSON hashes. Per-hour mixed trajectories must equal the sum of generated/bound constituents; annual totals equal weighted original budgets.
- [ ] Run `python -m unittest tests.test_schedule_generator_pilot tests.test_schedule_generator_mixtures -v`; observe failures.
- [ ] Resolve all inputs first; precompute reference budgets; assign source-native unit seeds and source-documented group sampling; generate each full related channel set; create scoped schedule references; bind magnitudes; compose only afterward. Return constituent and mixed slots, all used schedules and complete receipts. Cache shared operating samples by stable group identity, not room index. Request a fresh realization without touching source definitions.
- [ ] For compatible energy/volume demands compute `q_mix[h] = sum(w_i * D_i * s_i[h])` and normalize by `sum(w_i * D_i)`. Keep basis/fuel/host separation, explicit non-area scaling and singletons. Preserve per-load occupancy activity; adapt the approved active-member thermostat averaging, recording its representative-control interpretation. Weight constant heat fractions by conserved annual component energy.
- [ ] Rerun pilots and constituent modules. Check every hour, annual target, mixed total, reference closure, zero group, incompatible scale and singleton identity. Verify a mixture uses individually generated constituent objects rather than averaging stored source schedules. Neither unsupported members nor mixed annual/ruleset adapters may silently disappear.
- [ ] Record complete declared-family end-to-end evidence before Task 9 shipment; inspect/audit and commit `feat(schedules): generate constituent bundles and conserved mixtures`.

### Task 9: Ship the first standalone family milestone

**Files:** Create `atlas_schedules/__main__.py`, `scripts/schedule_generator_release.py`, `docs/schedule-generator.md`, `scripts/schedule_generator_coverage.py`, `docs/validation/schedule-generator-coverage.json`, and `data/generator-releases/v0.1.0/`; modify `.github/workflows/validate.yml`, `README.md`, and `docs/roadmap.md`. Test `tests/test_schedule_generator_cli.py`, `test_schedule_generator_release.py`, and `test_schedule_generator_reproducibility.py`.

**Consumes:** Task 8 complete evidence for every case in the authoritative M1 scope, Task 1 passed sampling/configuration gates, local resources, public API and Task 2 schemas/comparator; unresolved catalogue families outside the manifest are outside M1's advertised support.

**Produces:** `build_coverage(resources: ResourceSet) -> dict`; `freeze_generator(target: Path, version: str) -> dict`; `verify_generator(target: Path) -> list[str]`; CLI `python -m atlas_schedules --request REQUEST.json --output BUNDLE.json`. Release CLI accepts `--target`, `--freeze`, `--verify` and `--reproduce`; coverage CLI supports `--check` and `--scope`. The shipped milestone manifest embeds the exact case set from `sources/schedule-generator-m1-scope.json`, its version/hash, resolved configuration/resource references and per-case channel evidence; `--reproduce` compares fresh generated results numerically and source decisions discretely, not generated hashes.

- [ ] Write `test_standalone_zip_generates_offline`, `test_api_cli_numerical_equivalence`, `test_tampered_resource_and_duplicate_json_rejected`, `test_frozen_integrity_and_numerical_reproduction`, `test_partial_scope_can_ship`, `test_m1_missing_case_or_channel_blocks_shipment`, `test_m1_scope_manifest_cannot_silently_shrink`, and `test_unsupported_outside_scope_is_visible`. Assert generation from an empty checkout-independent directory with repository imports/network/subprocess forbidden, API/CLI scientific equivalence under the named policy, expected integrity/JSON errors, immutable-target rejection, retained notices, valid frozen artifact/member hashes, and equivalent regenerated numerical results from distinct paths. Assert exact manifest equality, no extra configuration/weather/template combinations, and release rejection when any one listed case or included channel is unresolved, missing or failed. M1 must pass with all listed cases and included channels complete while other catalogue families remain explicitly unsupported/requires-binding; requesting an unsupported family fails clearly.
- [ ] Run `python -m unittest tests.test_schedule_generator_cli tests.test_schedule_generator_release tests.test_schedule_generator_reproducibility -v`; observe failures.
- [ ] Package Python runtime modules, data, schemas, program references, examples, source manifest, authoritative M1 scope and completed commercial sampling audit, and applicable upstream notices. Freeze and checksum the actual packaged resources/manifests. Use an ordinary independent ZIP; matching freshly generated numerical JSON/ZIP bytes across machines is not a scientific gate. Include no large raw sources, development runtime, credentials, PII or internal cache paths. The CLI verifies local resource identities and produces a numerically/source-equivalent API bundle without imports from repository build scripts.
- [ ] Document parameter/seed-to-slot mapping, pure Python invocation, annual normalization for both families, magnitude binding requirements, units, mixtures, fixed/control channels, scope, hybrid interpretation and coverage. Link the independent artifact and referenced contract from the repository README; record M1 as delivered with its exact scope while keeping broad/full coverage work open. Website UI changes and production publishing remain separate work.
- [ ] Add source verification, coverage check, release verification/reproduction and ordinary generator tests to the existing Linux/Python 3.11 and Windows/Python 3.14 research matrix. Retain all existing required checks. The shipped generator remains offline; CI extraction may retrieve locked public sources through explicit Python steps.
- [ ] Run standalone generation, numerical/source reproduction, frozen resource integrity and the full existing validation commands below. Require complete advertised scope, no legacy changes and zero release errors, not equal hashes of regenerated schedules. Inspect/audit and commit `feat(schedules): ship source-validated residential and office milestone`.

### Task 10: Expand and ship additional families progressively

**Files:** Extend `scripts/schedule_generator_coverage.py`, `docs/validation/schedule-generator-coverage.json`, and `data/schedule-generator/` inventories; extend recipe/source resources. Test `tests/test_schedule_generator_coverage_full.py`.

**Consumes:** Delivered Task 9 M1, all current 1,900 definitions/378 compositions as the eventual inventory, and exact new family/template/weather dependencies.

**Produces:** `build_coverage(resources: ResourceSet) -> dict` and CLI `python -m scripts.schedule_generator_coverage --check`; use Task 9 freezing/verification for each newly completed family milestone. Each channel/family has `generated`, `source_fixed`, `absent`, `requires_binding`, or `unsupported` status with explicit climate/vintage/region dependencies and reasons.

- [ ] Write `test_every_current_record_has_channel_coverage`, `test_dependency_normalization_preserves_template_and_region`, `test_two_3b_locations_remain_distinct`, and `test_unsupported_and_excluded_are_not_complete`. Assert enumeration of 1,900 definitions and 378 compositions, five commercial templates, all residential fixture identities, valid mixture-member coverage, and distinct unknown/shared/absent/unsupported/excluded states. Shared source recipes must not create fabricated climate-specific records.
- [ ] Run `python -m unittest tests.test_schedule_generator_coverage_full -v`; observe failures.
- [ ] Extend source-backed mappings across all programs, common spaces, support spaces and mixtures. Compare schedule recipes by actual selectors/data instead of multiplying identical rows across climate/vintage labels. Inventory genuine differentiated families; exercise each with its bound location/weather and template inputs, retaining original stock/prototype identity. Add kernel regression cases when a new branch is exercised.
- [ ] Resolve recoverable mappings and required resource gaps; record any remaining material source or architecture ambiguity with exact affected programs and a concrete proposal. Required caller inputs are allowed when explicitly enumerated; fabricated inputs and silent fixed-schedule fallback are not. Unsupported channels outside a declared milestone do not block that shipment; unsupported channels inside it do. Keep eventual full extraction open until applicable active channels are covered.
- [ ] Run full family coverage plus multiple seed realizations per family; compare target invariance and shape variation, all included references and unchanged fixed methods. Generate the channel/parameter matrix and resource size/runtime measurements. Validate coverage denominators/exclusions and ship each complete added family as the next immutable release before proceeding to another. Expand the DOE reference weather set with the families that require it, preserving both 3B cases; do not hold already usable families for all remaining locations.
- [ ] Inspect/audit and commit `data(schedules): cover applicable program and climate template families`.

## Verification commands and evidence

During each task run its focused tests through observed failure and success, then retain that result in task evidence. Do not repeatedly run the slow whole suite without new implementation changes or failures. At each shipment run (use the declared milestone scope and its release target):

```powershell
python -m scripts.fetch
python -m scripts.fetch --lock sources/schedule-evidence-lock.json
python -m scripts.fetch --lock sources/water-evidence-lock.json
python -m scripts.fetch --lock sources/completion-evidence-lock.json
python -m scripts.fetch --lock sources/definition-evidence-lock.json
python -m scripts.schedule_generator_sources --verify-only
python -m unittest discover -s tests -v
python -m scripts.validate
python -m scripts.reproduce
python -m scripts.compare --report build/source-comparison.json
python -m scripts.coverage --report build/coverage.json
python -m scripts.release --verify
python -m scripts.release --verify --target data/releases/v0.1.0
python -m scripts.resolve --verify
python -m scripts.resolve --verify --target data/resolution-releases/v0.1.0
python -m scripts.resolve --verify --target data/resolution-releases/v0.2.0
python -m scripts.resolve --verify --target data/resolution-releases/v0.3.0
python -m scripts.commercial_completion --verify
python -m scripts.water_equivalent --verify
python -m scripts.water_reporting --verify
python -m scripts.definition_release --verify
python -m scripts.definition_release --reproduce
python -m scripts.program_completeness --check
python -m scripts.schedule_coverage --report build/schedule-coverage.json
python -m scripts.schedule_generator_coverage --check --scope m1
python -m scripts.schedule_generator_release --target data/generator-releases/v0.1.0 --verify
python -m scripts.schedule_generator_release --target data/generator-releases/v0.1.0 --reproduce
python -m scripts.audit
```

Record commands/results, source/resource hashes, actual seeds/order, discrete decisions, continuous tolerances and declared adaptations. Verify frozen resources/manifests exactly; reproduce fresh schedules and reference targets through source/discrete and numerical comparison, never generated SHA equality. Each release requires active binding completeness inside its declared family scope, explicit remaining coverage, and passing standalone/source/conservation checks. Full catalogue coverage remains a progressive objective, not the first-release prerequisite.

Before any commit use explicit logical file staging, `git diff --cached --check`, inspect `git diff --cached`, and run `python -m scripts.audit --staged`. Neutral commit example: `Research Agent <agent@example.invalid>` with `Agent-Model: unavailable (exact runtime model identifier not exposed)` when that identifier remains unavailable.

## Plan review and integration

All implementation checkboxes remain unchecked. The current clean-cache baseline completed 267 existing tests with one skip; this is a baseline, not validation of code that has not been written.

Review this plan and select native execution or subagent-driven execution before implementation. Native execution is recommended here because the source ports, RNG behavior, target/amplitude bindings and family gates depend tightly on one another. Source golden/numerical comparisons provide per-task checks; request an independent final branch review and resolve findings before integration. Delegation is permitted only through the user's selected method or an applicable skill instruction.

Complete an independent review of the resulting branch and its scientific/source receipts before creating a PR. If a PR is created, attach it to this chat. Do not change `main` directly or publish from this branch. Keep the worktree available for review and do not merge or archive it merely because the implementation plan has been written.
