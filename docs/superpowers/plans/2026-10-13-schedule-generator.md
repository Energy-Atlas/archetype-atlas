# Pure Python schedule generator implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or superpowers:subagent-driven-development to implement this plan task by task. Steps use checkbox syntax for tracking. Execution method remains subject to the user's choice; do not dispatch agents during plan review.

**Goal:** Ship a pure Python generator and referenced program contract covering applicable catalogue programs, with seeded temporal variation and conserved annual residential and commercial load totals.

**Architecture:** Extract immutable source mechanisms, probability tables and reference definitions into a local resource package. Generate complete related channel sets per constituent or commercial operating group, bind annual budgets to the actual emitted schedules, then compute mixtures. Preserve fixed channels, controls, source rules, provenance and frozen reference releases separately from generated realizations.

**Tech stack:** Python 3.11 and 3.14, standard-library runtime, JSON, SHA-256, unittest, and the repository's existing JSON Schema tooling for build/test validation. Ruby/OpenStudio is confined to opt-in development reference capture. Ship an independent ZIP distribution; no new runtime service or dependency is required.

**Spec:** [Approved design](../specs/2026-10-13-schedule-generator-design.md), approved 2026-10-13 after removing the commercial annual-consumption exception.

## Global constraints

- Work exclusively in `codex/stochastic-schedule-extraction` and its attached worktree; preserve other ongoing developments.
- Generation runs entirely in Python. Ruby, OpenStudio, EnergyPlus, external services and network access are not required to generate a packaged realization.
- The generator returns a variable number of schedules, each with exactly 8,760 hourly samples.
- Use an explicit non-leap Gregorian year; the initial default remains 2007 to match the atlas references. Reject leap years rather than dropping February 29.
- Hourly values describe `[hour, hour+1)` in local standard time. Apply no implicit DST, timezone conversion or holiday calendar.
- Require an explicit unsigned 64-bit master seed; reject booleans and invalid numeric values.
- Commercial operating hours are sampled from the supplied seed, rather than required as caller-selected hours.
- Apply annual-total conservation to both residential and commercial loads, including commercial definitions originally expressed as design power or power density with a reference schedule.
- Conservation refers to the load-weighted annual integral: the product of effective magnitude and schedule sum. Non-energy controls and resident counts retain their defined semantics.
- Keep fractional schedules in their valid range by changing effective magnitudes rather than multiplying fractions above one.
- Generate constituent schedules before computing mixture schedules; retain separate residential instance streams and shared commercial operating groups.
- Preserve actual source/template identity, SI units, physical hosts, fuels, scaling bases, shared-service identity and source rule/design-day semantics.
- Retain the existing exclusions of residential EV and HVAC equipment-unavailability overlays, plus existing program-scope exclusions.
- Freeze source revisions and SHA-256 locks, keep raw artifacts immutable, retain upstream notices and do not invent missing inputs or appliance shares.
- Frozen releases and existing Program JSON v3 remain immutable reference cases; do not regenerate them into a new meaning.
- Before every commit inspect the staged diff and run `python -m scripts.audit --staged`; use neutral automated authorship and an `Agent-Model` trailer recording unavailable details as unavailable.
- Production integration requires a protected `main` PR, required checks and resolved review conversations. This plan does not authorize a separate production deployment or changes in another chat.

## Review focus

1. A new seed or longer commercial operating day must not change any included load's annual target; test emitted values and effective magnitudes together (Tasks 2, 6, 8).
2. Adding/reordering repeated apartments must not synchronize or change existing unit streams; an explicit commercial group must remain coordinated (Tasks 3, 8).
3. Missing source inputs, aggregate appliance shares or positive-budget zero-integral channels must fail explicitly, while declared absences remain zeros (Tasks 2, 7, 8).
4. Overnight/zero/full-day commercial hours and calendar/holiday/design-day selectors must survive transformations without source-order loss (Tasks 3, 6).
5. The shipped ZIP must work outside the repository without network, Ruby, OpenStudio or untracked caches, and reject tampered resources (Tasks 1, 10).

## Boundaries and files

Keep runtime modules independent of `scripts.*`, which imports repository paths and build dependencies. Build scripts may reuse existing fetch, definition, export and release helpers. Runtime data is a generated inspection of locked sources, not a hand-written substitute for calibration data.

| Files | Responsibility |
| --- | --- |
| `atlas_schedules/contract.py`, `canonical.py`, `errors.py` | Strict JSON, runtime validation, canonical identities and typed error context |
| `atlas_schedules/resources.py`, `atlas_schedules/data/` | Verified packaged source tables, recipes, references and weather features |
| `atlas_schedules/budgets.py` | Reference targets, emitted-value integrals and effective intensity/flow |
| `atlas_schedules/seeds.py`, `calendar.py`, `ruby_random.py` | Stable stream derivation, rule evaluation and source-compatible random draws |
| `atlas_schedules/residential/activity.py`, `events.py`, `shapes.py` | ResStock activity chains, dependent events and occupancy/location-dependent shapes |
| `atlas_schedules/commercial/sampling.py`, `parametric.py` | ComStock conditional operating samples and source schedule transformations |
| `atlas_schedules/companions.py`, `programs.py` | Source-fixed/default/control channels and generated program slot bindings |
| `atlas_schedules/mixtures.py`, `generator.py` | Constituent orchestration, conserved compositions and public API |
| `atlas_schedules/__init__.py`, `__main__.py` | Public import and offline JSON CLI |
| `scripts/schedule_generator_sources.py`, `schedule_generator_build.py` | Locked extraction and resource/catalogue compilation |
| `scripts/schedule_generator_reference.py`, `reference_schedule_generator.rb` | Opt-in upstream development fixture capture |
| `scripts/schedule_generator_coverage.py`, `schedule_generator_release.py` | Applicability/coverage evidence and reproducible independent distribution |
| `schemas/schedule-generator-{request,bundle,program}-v1.schema.json` | Separate versioned request, output and program-reference contracts |
| `sources/schedule-generator-{lock,policy}.json`, `docs/adr/0017-python-schedule-generators.md` | Mechanism bindings, interpretation policy and approved architecture |

Create package `__init__.py` files only with the task that supplies the package's functionality. New tests use `tests/test_schedule_generator_*.py`; keep fixtures under `tests/fixtures/schedule-generator/`. New research artifacts use `data/schedule-generator/` and a new `data/generator-releases/v0.1.0/`, leaving historical bundles untouched.

## Shared interface decisions

`generate(params: dict, seed: int) -> dict` is the public API. The CLI reads `{schema_version: "1.0.0", params: {...}, seed: ...}` and produces the same bundle. Input JSON rejects duplicate keys, NaN, infinity and unknown operand fields. Validation errors use `GeneratorError(code: str, path: str, message: str)` with instance/channel context.

`params` contains `resource_set_id`, `calendar`, `instances`, and optional `mixture`. `calendar` contains `year`, `clock: "local_standard_time"` and explicit `holidays` (default empty). Each instance contains `key`, `program_id`, `inputs`, `basis_bindings`, and nullable `operating_group`. Household inputs carry residents, bedrooms, installed end uses and required location/weather keys. The source recipe enumerates its required inputs; missing values cannot inherit unrelated fixture values.

`mixture` contains `program_id`, nullable `composition_id`, and members `{instance_key, weight}`. Weights are finite, nonnegative and sum to one for normalized area mixtures; non-area multiplicity is explicit in `basis_bindings`, never disguised as a weight. Known catalogue compositions supply their recorded weights; repeated instances need an explicit allocation of those weights. Without a mixture, return the requested individual program bindings.

Bundle keys are `schema_version`, `algorithm_version`, `schedules`, `bindings`, `constituents`, `generation`, and `metadata`. Each schedule has `id`, `unit`, `year`, `clock`, `timestep_minutes: 60`, and `values` of length 8,760. A binding identifies `instance_key`, `program_id`, `demand_id`, `slot`, `schedule_id`, `value`, `unit`, `basis`, `fuel`, `host`, `budget_method`, and a scaling receipt for energy/volume loads. Control bindings omit inapplicable magnitude/fuel fields rather than carrying fake zeros.

Source kernels return `GeneratedChannels = {channels: {slot: list[float]}, source_context: dict}`. Program resolution returns `{recipe_id, inputs, slots, demands, controls, shared_services, evidence}`. A bound constituent contains these resolved objects, emitted schedules, magnitude bindings and seed/parameter receipts. Tasks below own each producer; later tasks consume these interfaces rather than reconstructing reference magnitudes from generated outputs.

Use canonical UTF-8 JSON with sorted keys, compact separators, LF, finite numbers and no administrative timestamp in identity. `canonical(value: object) -> bytes` and `content_id(kind: str, payload: dict) -> str` live in `atlas_schedules/canonical.py`. IDs are the kind prefix plus the complete SHA-256 of their canonical physical payload. Administrative extraction dates stay in source metadata. `finalize_channels(generated: dict) -> dict` in `contract.py` rounds emitted kernel samples to nine decimal places before budget binding; raw source comparisons occur before this boundary. Mixture arithmetic uses those finalized constituent samples and retains its computed precision, with no post-composition clipping or independent rounding that would break conservation.

## Execution checklist

### Task 1: Lock mechanisms and compile inspectable source resources

**Files:** Create `scripts/schedule_generator_sources.py`, `scripts/schedule_generator_build.py`, `sources/schedule-generator-lock.json`, `sources/schedule-generator-policy.json`, `atlas_schedules/{resources,errors,canonical}.py`, `atlas_schedules/data/manifest.json`, and `docs/adr/0017-python-schedule-generators.md`. Test `tests/test_schedule_generator_resources.py`.

**Consumes:** Existing source/runtime/weather locks, approved spec, frozen v0.1.1 definitions, v0.4.0 resolutions, residential recovered inputs, and new inspection lock.

**Produces:** `GeneratorError(code: str, path: str, message: str)`; `canonical(value: object) -> bytes`; `content_id(kind: str, payload: dict) -> str`; `extract_sources(lock: dict, cache_root: Path, destination: Path) -> dict`; `build_resources(destination: Path, scope: str) -> dict`; `ResourceSet(root: Path, expected_id: str)` for validated resource directories; `ResourceSet.load(resource_set_id: str) -> ResourceSet` for packaged resources; `ResourceSet.get(kind: str, key: str) -> dict`. Resource kinds are `residential`, `commercial`, `weather`, `program`, `composition`, and `reference`. Source CLI accepts `--lock`, `--cache-root`, `--destination` and `--verify-only`; build CLI accepts `--scope` and `--destination`.

- [ ] Write `test_resource_hash_and_inventory_rejection` (changed/deleted/extra members raise `resource_integrity`), `test_unsafe_archive_member_rejection`, `test_probability_resource_is_required`, and `test_resource_identity_ignores_destination` (two extractions have identical ordered tables, provenance and manifest identity).
- [ ] Run `python -m unittest tests.test_schedule_generator_resources -v`; confirm the specific missing implementation or integrity assertion fails.
- [ ] Trace the pinned ComStock configuration to an explicit public TSV archive version and the required Standards 0.8.6 schedule methods. Record rationale, public URL, revision, bytes, SHA-256, extracted-member hashes and upstream notices. Extract ResStock's complete activity/event/default resource dependency closure from its already locked archive. Lock exact DOE 16-location EPWs, preserving the two 3B cases, and extract the weather features needed by the schedule kernels. Do not relabel station-proxy fixtures.
- [ ] Implement the interfaces above. Reject incomplete conditional-distribution rows, malformed probabilities, unsupported dependency cycles and unsafe resource paths. Compile compact canonical resources with per-field provenance and an ordered numerical-table representation. Never execute downloaded sampler code during extraction.
- [ ] Run the resource tests and `python -m scripts.schedule_generator_build --scope pilot --destination build/generator-pilot-resources`; require verified hashes and an explicit dependency inventory. Any unavailable material source becomes a named blocked extraction family, not guessed data or a completed family.
- [ ] Inspect/audit and commit `data(schedules): lock generator mechanisms and compile pilot resources`.

### Task 2: Define contracts and conserved magnitude bindings

**Files:** Create `atlas_schedules/{contract,budgets}.py`, the three v1 schemas, and request/binding fixtures. Test `tests/test_schedule_generator_contract.py` and `test_schedule_generator_budgets.py`.

**Consumes:** Shared interface decisions and Task 1 resources, canonical encoding, identities and typed errors.

**Produces:** `validate_request(params: dict, seed: int) -> None`; `validate_bundle(bundle: dict) -> None`; `finalize_channels(generated: dict) -> dict`; `reference_budget(demand: dict, reference_values: list[float]) -> dict`; `bind_budget(target: dict, values: list[float]) -> dict`. Budget targets contain `quantity`, `total`, `unit`, `basis`, `method`, and original evidence; binding output contains effective `value`, unit/basis and its scaling receipt.

- [ ] Write `test_res_and_com_reference_budget_conservation`: for each source family, 10 W/m2 × 2,000 reference hours yields 20,000 Wh/m2; 1,600 generated hours gives 12.5 W/m2, and 2,400 hours gives 8.333333333333334 W/m2 while preserving that total. Add `test_direct_annual_definition_precedes_rounded_power`, `test_volume_seconds_conversion`, `test_zero_unknown_and_unrealized_targets`, `test_strict_8760_contract`, and `test_controls_are_not_energy_scaled` with the outcomes below.

```python
target = reference_budget(demand_10_W_m2, reference_2000_hours)
assert target['total'] == 20000
bound = bind_budget(target, emitted_1600_hours)
assert bound['value'] == 12.5
assert math.fsum(emitted_1600_hours) * bound['value'] == 20000
# Positive targets with all-zero samples raise GeneratorError with
# code='zero_generated_integral'; unknown targets raise unresolved_annual_target.
```
- [ ] Run `python -m unittest tests.test_schedule_generator_contract tests.test_schedule_generator_budgets -v`; observe the intended failures.
- [ ] Implement strict request/bundle validation and canonical IDs. Use `math.fsum` of emitted values. Direct annual targets take precedence; otherwise use the original reference magnitude and calendar-compatible reference schedule. Keep fractional outputs bounded by adjusting magnitude. Positive target with zero integral raises `zero_generated_integral`; unknown target raises `unresolved_annual_target`; no retry, clipping or seed substitution.
- [ ] Validate energy/volume conservation with `math.isclose(..., rel_tol=1e-10, abs_tol=1e-12)` in the stated integral unit. Scaling bases and fuels remain distinct. Physical nameplate conflicts raise `infeasible_intensity` when a real limit is provided. Validate schemas against their example objects with the existing JSON Schema tooling.
- [ ] Rerun both modules; require all tests passing and per-demand provenance, input immutability, fraction bounds and rounding-integral consistency.
- [ ] Inspect/audit and commit `feat(schedules): add referenced contracts and annual budget binding`.

### Task 3: Establish stable streams and calendar evaluation

**Files:** Create `atlas_schedules/{seeds,calendar,ruby_random}.py`, `scripts/schedule_generator_reference.py`, and `scripts/reference_schedule_generator.rb`; extend the resource build with golden draw capture. Test `tests/test_schedule_generator_seeds.py`, `test_schedule_generator_calendar.py`, and `test_schedule_generator_random.py`.

**Consumes:** Task 1 canonical encoding/errors and source resources, plus Task 2 contract validation.

**Produces:** `derive_seed(master: int, purpose: str, key: str) -> int`; `SourceRandom(seed: int)` with `random() -> float`, `randbelow(limit: int) -> int`, `getstate() -> dict` and `setstate(state: dict) -> None`; `evaluate_rules(schedule: dict, year: int, holidays: list[str]) -> dict` returning annual `values` and retained `special_profiles`.

- [ ] Write `test_seed_domain_and_duplicate_keys`, `test_streams_survive_insertion_and_reordering`, `test_source_random_matches_golden_draws`, and `test_random_state_roundtrip`. Assert valid seeds `0`/`2**64-1`, rejected booleans/negative/overflow seeds, duplicate-key rejection, unchanged named streams, exact golden Ruby draws at limits including `2**32`, and identical subsequent draws after state restoration. Add `test_non_leap_hourly_calendar` (8,760 in 2007; error in 2008) and `test_special_rules_preserve_precedence_and_wrapping` (holiday/design selectors and later matching rules retain their fixture values).
- [ ] Run `python -m unittest tests.test_schedule_generator_seeds tests.test_schedule_generator_calendar tests.test_schedule_generator_random -v`; verify failures.
- [ ] Derive a 64-bit seed from the first eight big-endian bytes of SHA-256 over canonical `['atlas-seed-v1', master, purpose, key]`. Document this adaptation; use purpose labels `residential-unit` and `commercial-group`. Detect collisions for the request. Port Ruby random initialization/draw behavior needed by ResStock; do not use Python `random.Random(seed)` as an assumed replacement. Trace and preserve upstream random draw order.
- [ ] Port the existing rule semantics into a standalone runtime evaluator, preserving selectors/order and producing separately retained design profiles. Validate holiday dates against the requested non-leap year. Keep special-day profiles out of annual integrals unless an explicit holiday date selects one.
- [ ] Rerun all three modules against independently captured, checksum-identified draw/rule vectors; require exact random draw matches and disclosed numerical tolerance for schedule values.
- [ ] Inspect/audit and commit `feat(schedules): add stable seed streams and source calendar semantics`.

### Task 4: Port ResStock occupant activities and dependent shapes

**Files:** Create `atlas_schedules/residential/{activity,shapes}.py`; extend `scripts/schedule_generator_reference.py` and `scripts/reference_schedule_generator.rb`. Test `tests/test_schedule_generator_residential_activity.py` and `test_schedule_generator_residential_shapes.py`.

**Consumes:** Pinned ResStock resources from Task 1, source-compatible draws and calendar from Task 3. Development capture reuses locked runtime verification and existing `scripts/run_residential_profiles.rb`; ordinary tests read local golden JSON only.

**Produces:** `simulate_activities(inputs: dict, unit_seed: int, resources: ResourceSet) -> dict`; `occupancy_shapes(activities: dict, inputs: dict, resources: ResourceSet) -> GeneratedChannels`. Activity output carries per-occupant state traces, main-stream state, unit offset and end-use seeds for Task 5.

- [ ] Write `test_activity_trace_matches_source_fixture`, `test_multiple_residents_and_offset`, and `test_weather_changes_only_dependent_shapes`. Assert exact state/duration/offset golden traces and draw order for weekday/weekend/state cases, occupancy within `[0,1]`, separate one/multiple-resident cases, and unchanged core transitions when only weather changes. Lighting and fan channels must match their location/weather fixture results.
- [ ] Run `python -m unittest tests.test_schedule_generator_residential_activity tests.test_schedule_generator_residential_shapes -v`; observe failing kernel/reference assertions.
- [ ] Implement the internal 15-minute activity mechanism and the source minute-level shift/aggregation sequence before hourly emission. Generate occupancy, interior/garage lighting, applicable plug/TV and fan shapes together. Preserve appliance/garage presence, main/end-use stream relationships and the source's zero-resident skip boundary.
- [ ] Capture checked upstream intermediate traces and emitted channels using an explicit `python -m scripts.schedule_generator_reference --family residential --destination build/generator-reference-residential` development command. Include source/runtime/resource/input hashes; execute no sizing or EnergyPlus. Compare raw numerical components at `abs_tol=1e-12` and require exact numeric equality after the upstream three-significant-digit CSV export formatting where applicable; report any deliberate adaptation separately.
- [ ] Rerun activity/shape tests offline; independently vary location/state/weather and assert only source-dependent channels change. Confirm no actual resident-count or activity-W/person scaling occurs.
- [ ] Inspect/audit and commit `feat(schedules): port residential activities and coordinated shapes`.

### Task 5: Port residential appliance and water events

**Files:** Create `atlas_schedules/residential/events.py` and its public `__init__.py`; extend reference capture and resource compilation. Test `tests/test_schedule_generator_residential_events.py`.

**Consumes:** Task 4 activity traces/stream state and Task 1 duration, consumption, event cluster, draw and monthly data.

**Produces:** `generate_events(activities: dict, inputs: dict, resources: ResourceSet) -> GeneratedChannels`; `generate_residential(inputs: dict, unit_seed: int, resources: ResourceSet) -> GeneratedChannels` in `residential/__init__.py`, composing Tasks 4–5.

- [ ] Write `test_activity_events_match_source_fixture`, `test_absent_appliances_and_zero_use`, `test_removing_one_end_use_preserves_other_streams`, and `test_water_normalization_after_shift`. Assert cooking/washer/dryer/dishwasher and all included water channels match their source fixture, absent channels carry absence receipts, unrelated event traces remain identical, and output sums/bounds match the source's normalization stage.
- [ ] Run `python -m unittest tests.test_schedule_generator_residential_events -v`; observe intended failures.
- [ ] Port source event ordering, correlations, durations and power/water draws; retain internal normalization semantics. These shape samples never replace definition-derived annual energy/volume. Emit only applicable channels and explicit absence receipts; EV remains excluded.
- [ ] Extend development captures to full related channel sets for occupied single-unit/multifamily cases and the existing frozen fixture inputs. Verify per-channel component parity before budget binding, then use Task 2 to check annual totals from original recovered definitions. Include a positive-budget/no-event seed that fails explicitly instead of returning zero or drawing another seed.
- [ ] Rerun the event, activity, shape and budget modules offline; require correct per-unit occupancy/end-use correlations and unchanged unrelated streams.
- [ ] Inspect/audit and commit `feat(schedules): port residential appliance and water events`.

### Task 6: Port commercial sampling and source transformations

**Files:** Create `atlas_schedules/commercial/{sampling,parametric}.py`; extend reference capture and source build. Test `tests/test_schedule_generator_commercial_sampling.py` and `test_schedule_generator_commercial_parametric.py`.

**Consumes:** Task 1 selected conditional TSV resources and actual Standards runtime methods, Task 3 random/calendar primitives, Task 2 budgets.

**Produces:** `sample_operating_parameters(inputs: dict, group_seed: int, resources: ResourceSet) -> dict`; `transform_commercial(channels: dict, operating: dict, source_context: dict) -> GeneratedChannels`. Sampling returns both effective values and source distribution-row/option/draw receipts.

- [ ] Write `test_operating_sample_matches_conditional_row`, `test_cumulative_probability_boundaries`, `test_na_flags_and_missing_dependencies`, `test_overnight_zero_and_full_day_transforms`, and `test_constants_ramps_and_design_days_match_source`. Assert exact expected options for stored draw/row pairs, `NA` flag behavior, errors for unknown selectors, and fixture-equivalent values/rules for 0/24-hour and overnight cases. No request supplies operating hours; unrelated group draw receipts differ.
- [ ] Run `python -m unittest tests.test_schedule_generator_commercial_sampling tests.test_schedule_generator_commercial_parametric -v`; observe intended failures.
- [ ] Port source conditional selection and the actual operating-hour inference/formula/transformation dependency closure. Retain occupancy adjustment and lighting/equipment base-to-peak logic where the selected source configuration applies them. Sample only source-required schedule parameters; do not resample intensity, geometry or stock attributes. Reject missing dependency bindings rather than selecting a guessed national/California or building-type substitute.
- [ ] Capture a Medium Office reference matrix with native, short, long, overnight, zero/full-day and weekday/weekend cases. Compare pre-normalization transforms to the pinned upstream methods and store source inference context. Then bind the unchanged pre-sampling reference budgets: short and long schedules must have different effective magnitudes and identical annual totals. Compare declared constant and design-day behavior separately.
- [ ] Rerun the sampling/parametric/calendar/budget modules. Require numerical kernel parity at `abs_tol=1e-12` unless an upstream export precision is explicitly recorded, and budget conservation at Task 2 tolerances.
- [ ] Inspect/audit and commit `feat(schedules): port seeded commercial operating distributions`.

### Task 7: Compile program recipes and companion schedules

**Files:** Create `atlas_schedules/{programs,companions}.py`, `data/schedule-generator/programs.json`, `compositions.json`, and `coverage.json`; extend `scripts/schedule_generator_build.py` and policy. Test `tests/test_schedule_generator_programs.py` and `test_schedule_generator_companions.py`.

**Consumes:** Frozen definitions through `scripts.definition_release.read_bundle`, ready v3 exports through `scripts.program_json_v3.ProgramExporter`, original recovered annual magnitudes through `scripts/recover_program_inputs.py`, and the kernels/resources from Tasks 1–6.

**Produces:** `resolve_program(program_id: str, inputs: dict, resources: ResourceSet) -> dict`; `generate_companions(resolved: dict, resources: ResourceSet) -> GeneratedChannels`. Program records contain schedule slots, required inputs, original/reference budgets, source method and applicability.

- [ ] Write `test_original_budgets_precede_reference_fitted_magnitudes`, `test_reference_commercial_budget_is_pre_sampling`, `test_companion_controls_and_backgrounds`, `test_zero_resident_preserves_installed_refrigeration`, and `test_missing_appliance_shares_are_unsupported`. Assert original annual-kWh precedence, stable commercial targets across samples, correct nominal/fixed channels, retained background demand, distinct fuel/host identities and explicit unsupported aggregate mappings. Program exports must expose resolvable schedule slots.
- [ ] Run `python -m unittest tests.test_schedule_generator_programs tests.test_schedule_generator_companions -v`; observe failures.
- [ ] Compile source/reviewed views separately, preserving accepted v3 defaults and their receipts. Map apartment units to ResStock time allocation with actual definition-derived annual targets; leave apartment common spaces and hotel guestrooms on applicable source methods. Require explicit household presence/location parameters. Recover source-backed aggregate end-use mappings; absent decomposition is `unsupported_binding`, never guessed appliance shares or borrowed unrelated-fixture magnitudes.
- [ ] Implement thermostat translation/correction and each included source-fixed/default companion recipe as Python or explicit compiled source rule tables. Match the definition's selected fixed-versus-conditional default. Temperature-dependent channels require their actual bound temperature input; retain existing explicit fixed-background variants where those are the selected definitions. Include shared services once with their physical identities.
- [ ] Build `--scope pilot` recipes for Medium Office and occupied/vacant repeated apartment cases. Rerun program/companion/kernel/budget modules and validate their reference closure, no unknown active operands, same-source fixed values and unchanged frozen definitions.
- [ ] Inspect/audit and commit `feat(programs): compile generator recipes and companion channels`.

### Task 8: Orchestrate constituent generation and compute mixtures

**Files:** Create `atlas_schedules/{generator,mixtures}.py` and public `__init__.py`; add complete pilot request/bundle examples under `docs/examples/schedule-generator-v1/`. Test `tests/test_schedule_generator_pilot.py` and `test_schedule_generator_mixtures.py`.

**Consumes:** Task 7 resolved programs, Tasks 4–6 kernels, Task 3 stable streams and Task 2 annual binding.

**Produces:** Public `generate(params: dict, seed: int) -> dict`; `compose_constituents(constituents: list[dict], mixture: dict, calendar: dict) -> dict`.

- [ ] Write `test_medium_office_and_two_apartment_pilots`, `test_stable_independent_units_and_coordinated_commercial_group`, `test_mixed_families_and_29_members`, and `test_group_conflict_and_shared_service_identity`. Assert 8,760 values per returned channel, stable canonical bytes, independent unit stream receipts, identical group operating receipts and explicit `operating_group_conflict`. Per-hour mixed trajectories must equal the sum of generated/bound constituents; annual totals equal weighted original budgets.
- [ ] Run `python -m unittest tests.test_schedule_generator_pilot tests.test_schedule_generator_mixtures -v`; observe failures.
- [ ] Resolve all inputs first; precompute reference budgets; derive unit/group streams; generate each full related channel set; create emitted schedule IDs; bind magnitudes; compose only afterward. Return constituent and mixed slots, all used schedules and complete receipts. Cache shared operating samples by stable group identity, not room index. Request a fresh realization without touching source definitions.
- [ ] For compatible energy/volume demands compute `q_mix[h] = sum(w_i * D_i * s_i[h])` and normalize by `sum(w_i * D_i)`. Keep basis/fuel/host separation, explicit non-area scaling and singletons. Preserve per-load occupancy activity; adapt the approved active-member thermostat averaging, recording its representative-control interpretation. Weight constant heat fractions by conserved annual component energy.
- [ ] Rerun pilots and constituent modules. Check every hour, annual target, mixed total, reference closure, zero group, incompatible scale and singleton identity. Verify a mixture uses individually generated constituent objects rather than averaging stored source schedules. Neither unsupported members nor mixed annual/ruleset adapters may silently disappear.
- [ ] Record successful pilot evidence before permitting Task 9 expansion; inspect/audit and commit `feat(schedules): generate constituent bundles and conserved mixtures`.

### Task 9: Expand all applicable programs and dependency families

**Files:** Create `scripts/schedule_generator_coverage.py`, `docs/validation/schedule-generator-coverage.json`, and full `data/schedule-generator/` inventories; extend recipe/source resources. Test `tests/test_schedule_generator_coverage_full.py`.

**Consumes:** Passing Task 8 pilot evidence, all current 1,900 definitions/378 compositions, and exact source/weather dependencies.

**Produces:** `build_coverage(resources: ResourceSet) -> dict` and CLI `python -m scripts.schedule_generator_coverage --check`. Each channel/family has `generated`, `source_fixed`, `absent`, `requires_binding`, or `unsupported` status with explicit climate/vintage/region dependencies and reasons.

- [ ] Write `test_every_current_record_has_channel_coverage`, `test_dependency_normalization_preserves_template_and_region`, `test_two_3b_locations_remain_distinct`, and `test_unsupported_and_excluded_are_not_complete`. Assert enumeration of 1,900 definitions and 378 compositions, five commercial templates, all residential fixture identities, valid mixture-member coverage, and distinct unknown/shared/absent/unsupported/excluded states. Shared source recipes must not create fabricated climate-specific records.
- [ ] Run `python -m unittest tests.test_schedule_generator_coverage_full -v`; observe failures.
- [ ] Extend source-backed mappings across all programs, common spaces, support spaces and mixtures. Compare schedule recipes by actual selectors/data instead of multiplying identical rows across climate/vintage labels. Inventory genuine differentiated families; exercise each with its bound location/weather and template inputs, retaining original stock/prototype identity. Add kernel regression cases when a new branch is exercised.
- [ ] Resolve recoverable mappings and required resource gaps; record any remaining material source or architecture ambiguity with exact affected programs and a concrete proposal. Required caller inputs are allowed when explicitly enumerated; fabricated inputs and silent fixed-schedule fallback are not. Do not declare full extraction complete while applicable active channels remain unsupported.
- [ ] Run full family coverage plus multiple seed realizations per family; compare target invariance and shape variation, all included references and unchanged fixed methods. Generate the channel/parameter matrix and resource size/runtime measurements. Persist the checked report only after its denominators and exclusions are validated.
- [ ] Inspect/audit and commit `data(schedules): cover applicable program and climate template families`.

### Task 10: Package independent generation and verify release reproduction

**Files:** Create `atlas_schedules/__main__.py`, `scripts/schedule_generator_release.py`, `docs/schedule-generator.md`, and new generator release files; modify `.github/workflows/validate.yml`, `README.md`, and `docs/roadmap.md`. Test `tests/test_schedule_generator_cli.py`, `test_schedule_generator_release.py`, and `test_schedule_generator_reproducibility.py`.

**Consumes:** Task 9 complete resources/coverage, Task 8 public API and Task 2 schemas.

**Produces:** `freeze_generator(target: Path, version: str) -> dict`; `verify_generator(target: Path) -> list[str]`; CLI `python -m atlas_schedules --request REQUEST.json --output BUNDLE.json`. Release CLI accepts `--target`, `--freeze`, `--verify` and `--reproduce`.

- [ ] Write `test_standalone_zip_generates_offline`, `test_api_cli_canonical_parity`, `test_tampered_resource_and_duplicate_json_rejected`, and `test_immutable_reproducible_release`. Assert generation from an empty checkout-independent directory with repository imports/network/subprocess forbidden, identical API/CLI bundle bytes, expected integrity/JSON errors, immutable-target rejection, retained notices and identical regenerated payload/ZIP hashes from two distinct paths.
- [ ] Run `python -m unittest tests.test_schedule_generator_cli tests.test_schedule_generator_release tests.test_schedule_generator_reproducibility -v`; observe failures.
- [ ] Package Python runtime modules, data, schemas, program references, examples, source manifest and applicable upstream notices. Use canonical LF bytes, sorted ZIP paths, `ZIP_STORED` and fixed ZIP timestamps/attributes so ZIP reproduction does not depend on the host zlib version. Include no large raw sources, development runtime, credentials, PII or internal cache paths. The CLI verifies local resource identities and produces the identical API bundle without imports from repository build scripts.
- [ ] Document parameter/seed-to-slot mapping, pure Python invocation, annual normalization for both families, magnitude binding requirements, units, mixtures, fixed/control channels, scope, hybrid interpretation and coverage. Link the independent artifact and referenced contract from the repository README; mark the generator roadmap item complete only when the actual delivery gates pass. Website UI changes and production publishing remain separate work.
- [ ] Add source verification, coverage check, release verification/reproduction and ordinary generator tests to the existing Linux/Python 3.11 and Windows/Python 3.14 research matrix. Retain all existing required checks. The shipped generator remains offline; CI extraction may retrieve locked public sources through explicit Python steps.
- [ ] Run both local ZIP reproduction and the full existing validation commands listed below; require identical payload/ZIP manifests, no legacy changes and zero release errors. Inspect/audit and commit `feat(schedules): ship reproducible standalone Python generator`.

## Verification commands and evidence

During each task run its focused tests through observed failure and success, then retain that result in task evidence. Do not repeatedly run the slow whole suite without new implementation changes or failures. At the final delivery run:

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
python -m scripts.schedule_generator_coverage --check
python -m scripts.schedule_generator_release --target data/generator-releases/v0.1.0 --verify
python -m scripts.schedule_generator_release --target data/generator-releases/v0.1.0 --reproduce
python -m scripts.audit
```

Record the actual command/result, fixture/resource/request hashes, covered branches, numerical tolerance and adaptation boundaries. Reproduction must regenerate source-derived resources and reference targets, not merely compare a copied ZIP. A new release is frozen only after covered active binding completeness and pilot/family gates pass.

Before any commit use explicit logical file staging, `git diff --cached --check`, inspect `git diff --cached`, and run `python -m scripts.audit --staged`. Neutral commit example: `Research Agent <agent@example.invalid>` with `Agent-Model: unavailable (exact runtime model identifier not exposed)` when that identifier remains unavailable.

## Plan review and integration

All implementation checkboxes remain unchecked. The current clean-cache baseline completed 267 existing tests with one skip; this is a baseline, not validation of code that has not been written.

Review this plan and select native execution or subagent-driven execution before implementation. Native execution is recommended here because the source ports, stream behavior, magnitude contracts and composition gates depend tightly on one another. Source golden comparisons provide per-task checks; request an independent final branch review and resolve findings before integration. Delegation is permitted only through the user's selected method or an applicable skill instruction.

Complete an independent review of the resulting branch and its scientific/source receipts before creating a PR. If a PR is created, attach it to this chat. Do not change `main` directly or publish from this branch. Keep the worktree available for review and do not merge or archive it merely because the implementation plan has been written.
