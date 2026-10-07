# Catalogue Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> to implement this plan task by task in the current chat. Steps use checkboxes.
> Execute routine research, implementation, validation and reversible release
> work autonomously; do not introduce recurring approval checkpoints.

**Goal:** Deliver the Residential / Non Residential catalogue with Programs,
Constructions and HVAC systems, approved program mixtures, element-level energy
definitions and a reproducible selective public JSON contract.

**Architecture:** Add an independently versioned definition bundle derived from
the frozen atlas and pinned source evidence. Publish its three primary kinds
through static delivery v2, with schedules, components and provenance loaded on
demand, while retaining delivery v1. Validate a Medium Office vertical slice
before expanding the same pipeline across the approved families and residential
fixtures; build the catalogue from the verified bundle.

**Tech stack:** Python 3.11+, unittest, JSON Schema, existing pinned MkDocs and
Playwright dependencies, browser JavaScript and Node's test runner. No backend.

**Spec:** [Agreed design](../specs/2026-10-07-catalogue-redesign-design.md),
[ADR 0012](../../adr/0012-program-composition-simplification.md),
[family matrix](../../reviews/program-aggregation-matrix.md) and
[repository research brief](../../AGENT_RESEARCH_BRIEF.md).

## Global constraints

- Work on `feature/query-dto`; do not merge main or modify BEMGen here.
- Exactly three first-class kinds: Programs, Constructions and HVAC systems.
- Default to 90.1-2019 where supported and the finest supported source programs.
- Canonical JSON uses SI units, explicit bases and schema versions; CSV is export.
- Existing stock, code/prototype, source/reviewed, derived and assumed remain distinct.
- Null means unknown or not reported, never implicitly zero.
- Use determined schedules; generator runtimes and arguments remain deferred.
- HVAC performance definitions are fixed library records. Model application,
  capacity sizing and experiment sizing modes are downstream responsibilities.
- Generic assumptions are permitted only for unresolved internal and ground-contact
  constructions. Other unresolved parameters remain explicit.
- Preserve immutable releases, v1 URLs, upstream notices and locked retrieval.
- Every commit requires staged-diff inspection and the staged security audit.

## Review focus

1. Alternate units for one hot-water demand must not become duplicate demand;
   true additions retain physical quantity, scaling basis and ownership (Task 2).
2. Mixtures spanning date rules, design days or unknown members must conserve
   known trajectories and propagate required unknowns, including leap day (Task 6).
3. Duplicate construction names and insulation adjustments must retain the
   correct assembly and heat capacity rather than matching only U-value (Task 3).
4. Capacity/date-dependent HVAC rules must not become an invented fixed COP or
   drift with the current machine date (Task 4).
5. Stale filters and missing resource packets must produce explicit empty/error
   states, never substitute a different template or download the whole library
   (Tasks 5 and 9).

## Clarifications settled before execution

- A whole-dwelling residential program is valid without a room-area mixture.
  Per-area loads still declare their downstream area dependency; per-unit loads
  do not require room-area weights. :codex-annotation{index="1"}
- Building-serving equipment may be hosted once in a suitable mechanical/core
  zone. Separate electrical demand, heat release and service ownership.
  :codex-annotation{index="2"}
- Addition is for approved mixtures or an isolated building-serving device added
  to a zone; alternate representations of one demand do not add.
  :codex-annotation{index="3"}
- Air-change settings are reached through Constructions, with infiltration,
  outdoor ventilation and total supply distinct and source space requirements
  preserved. Building packages remain convenient assignments of element
  definitions. :codex-annotation{index="4"}
- The user's answers settle fixed library HVAC performance and prohibit further
  generic defaults. No unresolved initial question blocks this plan.

## Feasibility and bounded research

The current release contains 768 commercial source programs, 41 residential
fixtures, 2,451 envelope rows, 1,145 system descriptors and 707 efficiency rules.
Those counts describe the baseline, not a promise that every row is ready for
simulation. All current commercial program infiltration values are null;
48 source program rows have positive minimum total-air-change requirements.
Residential profile availability does not establish complete load magnitudes.

The pinned OpenStudio Standards archive includes material, construction and
construction-set tables absent from the current normalized envelope rows.
All 87 construction names referenced by those rows occur in the common table,
but some names have competing definitions. SimpleGlazing names can be generated
by source code rather than appear as material-table rows. HVAC descriptors need
component/rule extraction; efficiency lookup can depend on capacity and date.
These are feasible extraction tasks, with explicit readiness limits rather than
permission to fill gaps by guesswork.

For each gap, inspect the existing locked source, its cited upstream routines and
official primary documentation. Add a pinned source only when it directly resolves
the gap and redistribution is supportable. Record exhausted evidence paths and
continue with explicit missing fields when resolution requires unavailable model
inputs, unsupported stock substitutions or new scientific assumptions. No broad
stock ingestion or end-to-end prototype reconstruction is required for this plan.

## Files and interfaces

New focused modules, each with matching `tests/test_<module>.py`:

| File | Responsibility |
| --- | --- |
| `scripts/definition_contract.py` | Typed bundle, status/basis vocabulary, IDs and source-context validation. |
| `scripts/program_definitions.py` | Normalize program loads, determined schedule references and shared services. |
| `scripts/construction_definitions.py` | Resolve ordered assemblies, targets, packages and air-exchange requirements. |
| `scripts/hvac_definitions.py` | Extract component graphs and fixed performance/rating definitions. |
| `scripts/definition_compare.py` | Compare corresponding construction/HVAC elements and report known matches, differences and missing evidence. |
| `scripts/program_composition.py` | Approved memberships, represented-area weights and conserved mixed schedules. |
| `scripts/residential_definitions.py` | Whole-dwelling fixtures and source-supported magnitudes. |
| `scripts/definitions.py` | Locked-input orchestration, pilot/full scope and deterministic build CLI. |
| `scripts/definition_validate.py` | Cross-table schema, physical, provenance, readiness and conservation checks. |
| `scripts/definition_release.py` | Freeze, verify and reproduce immutable definition releases. |
| `scripts/query_v2.py` | Static v2 export and client adapter using shared bounded transport. |
| `scripts/definition_site.py` | Generate the new catalogue routes and definition detail pages. |

Schema and policy files: `schemas/definitions.schema.json`,
`schemas/query-v2.schema.json`, `sources/definition-evidence-lock.json`,
`sources/definition-policy.json`, `sources/program-composition-policy.json`.
Document the schema in `docs/adr/0013-element-definition-catalogue.md`.

The bundle comprises `programs`, `constructions`, `hvac_systems` and supporting
`materials`, `components`, `services`, `compositions`, `schedules`, `provenance`,
`source_files`, `policies` and `coverage`. Freeze under
`data/definition-releases/v0.1.0/`; build intermediates stay ignored in `build/`.
All public IDs are deterministic, namespaced and independent of display labels.

`definition_contract.py` defines `DefinitionBundle` (typed tables above),
`BuildContext` (locked sources, extraction date, policy and pilot/full scope),
`ValidationReport` (errors, warnings and coverage), and `DefinitionError`.
Records expose required consumer inputs and per-field evidence; readiness is
capability-specific, not a misleading whole-record complete/incomplete flag.
Use separate axes `evidence_view=source|reviewed` and
`derivation=reported|normalized|composed|assumed`. Missing fields additionally
distinguish unknown, not_reported, not_applicable and requires_input.
Loads carry `quantity`, `value`, `unit`, `basis`, `schedule_id`, `service_id`
when applicable, and a `demand_id` linking alternate representations of one
physical demand. Scope and thermal-effect fields remain distinct from magnitude.
Missing fields carry a reason and any required operand names, not an assumed zero.

## Execution and commit protocol

Tasks 1–5 are the Medium Office pilot. Do not run full-scope extraction until its
checks pass. Tasks 6–8 expand verified semantics; Tasks 9–11 publish and hand off.
Follow each task's test cycle and update its checkboxes with evidence.

For every implementation commit: stage only its logical files, inspect the full
`git diff --cached`, run `git diff --cached --check` and
`.venv/Scripts/python.exe -m scripts.audit --staged`, then commit using neutral
`Research Agent <agent@example.invalid>` authorship, Conventional Commits and
`Agent-Model: unavailable (exact runtime model identifier not exposed)` unless
the environment exposes an exact identifier. Never stage the entire workspace
without inspecting unrelated changes. Commands below run from the repo root.

### Task 1: Establish the definition contract and source locks

**Files:** Create the contract, schema, three policy/lock files and ADR listed
above; create `tests/test_definition_contract.py`.

**Interfaces:** Produce `load_context(root: Path, scope: str) -> BuildContext`,
`validate_record(kind: str, record: dict) -> None` and
`stable_id(namespace: str, payload: dict) -> str` in `definition_contract.py`.

- [ ] Write schema tests: only three primary kinds; null cannot mean zero;
  evidence view is independent of derivation; every non-null physical field
  requires locator, original value/unit, transformation, extraction date and note.
- [ ] Run `python -m unittest tests.test_definition_contract -v`; confirm new
  contract assertions fail before implementation.
- [ ] Implement the types, schema and locks. Pin material/assembly/set files,
  source routines, rating date and policy revision. Verify retrieved bytes against
  SHA-256, including archives already in ignored caches; no implicit cache trust.
- [ ] Record current release manifests, counts and public v1 snapshot as the
  compatibility baseline. Define library performance identity separately from
  applicability, display name, package membership and downstream instance size.
  Pin the extraction date in the build context and reuse it for reproduction;
  fresh wall-clock timestamps must not change a reproduced release.
- [ ] Re-run the contract tests; expect all pass, including hash mismatch and
  duplicate-ID rejection. Commit `feat(definitions): establish versioned contract`.

### Task 2: Normalize Medium Office programs and load ownership

**Files:** Create `scripts/program_definitions.py`,
`tests/test_program_definitions.py`; extend schema only through Task 1 interfaces.

**Interfaces:** Consume `BuildContext`; produce
`build_programs(context: BuildContext) -> DefinitionBundle` in
`program_definitions.py`. It returns programs, services, schedule references and
evidence, scoped to Medium Office until the pilot gate passes.

- [ ] Write fixtures asserting a source-supported 10 W/m² load with fractional
  schedule 0.5 evaluates to 5 W/m², while null magnitude stays unknown. A single
  water demand expressed in two equivalent bases remains one demand; units such
  as m³/(s·m²), m³/s, W/m² and W retain quantity and normalization semantics.
- [ ] Add a shared-service fixture: two references to one 500 W device contribute
  500 W once, with separately sourced zone heat fraction. Reporting allocation
  is not another physical device. Add a fixture whose area-based density requires
  downstream area rather than receiving a made-up floor area.
- [ ] Run `python -m unittest tests.test_program_definitions -v`; confirm failures.
- [ ] Implement source/reviewed load normalization and evidence, schedule/setpoint
  references, occupancy and explicit physical effects. Resolve the original
  per-area/absolute hot-water branch before selecting or converting a basis;
  require temperature/efficiency inputs for water-volume-to-power conversion.
- [ ] Preserve original program air requirements as evidence/constraints for
  Task 3 without exposing a competing infiltration setting in Programs.
- [ ] Re-run tests; expect pass and no generator arguments in delivered Programs.
  Commit `feat(programs): normalize deterministic loads and shared services`.

### Task 3: Resolve Medium Office construction elements and air exchange

**Files:** Create `scripts/construction_definitions.py`,
`tests/test_construction_definitions.py`, `scripts/definition_compare.py`,
`tests/test_definition_compare.py`; add documented internal/ground fallback
policy in `sources/definition-policy.json`.

**Interfaces:** Produce `build_constructions(context: BuildContext,
programs: DefinitionBundle) -> DefinitionBundle` in `construction_definitions.py`.
Output assemblies/materials, package references, scoped air requirements and
required consumer geometry, with all identities based on actual parameters.
`definition_compare.compare_elements(kind: str, left: dict, right: dict,
tolerances: dict | None = None) -> dict` returns `identity`, `matches`,
`differences`, `unknowns` and the comparison's property/tolerance basis.

- [ ] Write fixtures for duplicate names with different layers, equal-U assemblies
  with different mass, ordered layers and IP-to-SI conversions. Assert ambiguous
  joins fail explicitly; no last-row-wins dictionary or U-only identity.
- [ ] Test element comparison reports differing mass at equal U, missing fields
  as insufficient evidence, and caller-specified tolerances as qualified
  similarity rather than identity. Default to exact normalized-property comparison;
  do not invent a universal scientific similarity score or tolerance.
- [ ] Test insulation adjustment against the source routine, generated
  SimpleGlazing, invalid source targets, and F/C-factor definitions requiring
  geometry. Test 6 ACH total supply stays total supply, with infiltration null.
- [ ] Run `python -m unittest tests.test_construction_definitions tests.test_definition_compare -v`;
  confirm failures.
- [ ] Extract source construction sets and resolve exact context/conditioning
  rules; retain U targets, films, layer adjustments and material properties.
  Model generated glazing faithfully and label source-code defaults as such.
- [ ] Resolve internal/ground definitions first. When impossible, choose and cite
  defensible generic assumptions with stable IDs, SI values or a declared physical
  model, applicability and geometry dependencies. Keep source and fallback views
  distinct. Do not supply generic infiltration or other unauthorized defaults.
- [ ] Re-run tests; expect pass, with unsupported values still explicit. Commit
  `feat(constructions): resolve assemblies and scoped air requirements`.

### Task 4: Extract fixed Medium Office HVAC performance definitions

**Files:** Create `scripts/hvac_definitions.py`, `tests/test_hvac_definitions.py`.
Extend `scripts/definition_compare.py` and its tests for component/performance
roles, rating bases and complete curve definitions.

**Interfaces:** Produce `build_hvac(context: BuildContext) -> DefinitionBundle`
in `hvac_definitions.py`: HVAC packages, components, connection/serving roles,
performance definitions, curves, control references and applicability evidence.

- [ ] Write fixtures: same system label with different fan/COP/curve values has
  different performance identity; identical parameters with different package
  names can share identity; missing values prevent a full-identity claim.
  Compare corresponding component roles explicitly; package-level labels or
  whole-building aggregate performance cannot stand in for element comparison.
- [ ] Test a capacity-band/date-dependent rule stays conditional unless its rating
  context is source-supported. Alter the machine date and assert identical output.
  Reject an arbitrary capacity used to manufacture COP; preserve metric and fan
  inclusion distinctions, curve domains and source-supported rating conversions.
- [ ] Run `python -m unittest tests.test_hvac_definitions tests.test_definition_compare -v`;
  confirm failures.
- [ ] Extract component/performance rules from locked source tables and routines.
  Expose fixed resolved variants only where supported; otherwise return the
  original conditional performance definition and explicit unresolved inputs.
  Do not infer fuel from a display name, autosize, simulate a consumer model or
  introduce reference-model/LOD experiment modes into the atlas.
- [ ] Re-run tests; expect pass and no unexplained scalar efficiency. Commit
  `feat(hvac): expose fixed component performance definitions`.

### Task 5: Validate and deliver the complete Medium Office pilot

**Files:** Create orchestration, validation, release and v2 modules and tests;
create `schemas/query-v2.schema.json`; minimally modify
`scripts/query_client.py` and `scripts/query_delivery.py` to share bounded
transport without changing their default v1 contract.

**Interfaces:** `definitions.build(context: BuildContext) -> DefinitionBundle`;
`definition_validate.validate(bundle: DefinitionBundle) -> ValidationReport`;
`definition_release.freeze(bundle: DefinitionBundle, target: Path) -> dict`;
`definition_release.verify(target: Path) -> ValidationReport`;
`query_v2.generate_delivery(bundle: DefinitionBundle, target: Path) -> dict`;
`query_v2.QueryClient(root: str, manifest_ref: str | None = None)` with
`query(kind: str, filters: dict, fields: list[str], view: str = 'source') -> dict` and
`resource(resource_id: str) -> dict`. V2 selects its own schema explicitly.

- [ ] Write pilot integration tests exercising programs, constructions and HVAC,
  referential integrity, evidence and lazy schedules. Assert invalid basis,
  missing evidence, orphan IDs and impossible physical values block freezing.
- [ ] Add v2 tests for exact scalar AND filters, projection and unknown fields;
  zero/multiple matches; corrupted/missing packets; bounded decompression; stable
  manifest pins. Assert v1 DTO/schema, packet identities and client defaults are
  unchanged. Primary query kinds exclude all supporting resource types.
- [ ] Run `python -m unittest tests.test_definition_contract tests.test_program_definitions tests.test_construction_definitions tests.test_definition_compare tests.test_hvac_definitions tests.test_definitions tests.test_definition_validate tests.test_definition_release tests.test_query_v2 tests.test_query_client tests.test_query_delivery -v`;
  confirm failures are limited to new functionality.
- [ ] Implement deterministic sorting/serialization and the CLIs:
  `python -m scripts.definitions --scope pilot --output build/definitions-pilot`,
  `python -m scripts.definition_validate --input build/definitions-pilot`, and
  `python -m scripts.query_v2 --input build/definitions-pilot --output build/delivery-v2-pilot`.
- [ ] Retain natural-context gzip packets at most 131,072 decoded bytes, hashed
  before bounded decoding. Fetch indexes/selected packets only; evidence and
  profiles remain lazy. Pin `latest` once per session; no backend/full-library fetch.
- [ ] Rebuild the pilot twice from locked inputs and compare canonical bytes;
  verify a source-backed Medium Office field from each primary kind. Run schema,
  physical, referential, schedules, provenance and reproducibility checks.
  Expected: zero validation errors and byte-identical outputs. Record the pilot
  report and commit `feat(delivery): validate Medium Office definition pilot`.
  Cross-runtime gzip checks compare the full decoded graph as in ADR 0011;
  encoded-byte reproducibility requires the pinned Python/zlib runtime.

### Task 6: Implement every approved commercial program composition

**Files:** Create `scripts/program_composition.py`,
`tests/test_program_composition.py`; populate
`sources/program-composition-policy.json`; refactor reusable area extraction from
`docs/reviews/tools/extract_program_area_evidence.py` into the production module,
retaining the existing review wrapper and its evidence format.

**Interfaces:** `program_composition.extract_areas(context: BuildContext) -> dict`;
`program_composition.compose(context: BuildContext,
programs: DefinitionBundle) -> DefinitionBundle`. Consume exact source/reviewed
leaf definitions; output immutable leaf references, recipes, mixed fields and
derived schedules. Do not import a review script with fetch/write side effects.

- [ ] Write a conservation fixture: weights 0.25/0.75 and densities 10/20 yield
  mixed density 17.5 and trajectory `2.5*s1(t)+15*s2(t)`, not a separately averaged
  shape. Test pointwise setpoints, per-person/absolute conversion dependencies,
  load-weighted thermal effects and unknown-member propagation.
- [ ] Test seasonal/overlapping source rules, source order, weekday/weekend,
  holidays, design days and leap day. Require explicit compatibility for annual
  realizations; never transplant an 8760 array silently to another year.
- [ ] Write matrix-driven assertions for all 17 families/83 exact contexts:
  basement/attic variants excluded from every denominator; school auditorium
  inclusion; hospital/outpatient department memberships and broad exclusions;
  SmallHotel vertical inclusion/corridor separation; StripMall 25/25/50; separate
  restaurant dining/kitchen; apartment top-floor optional; unsupported modes absent.
- [ ] Run `python -m unittest tests.test_program_composition -v`; confirm failures.
- [ ] Implement unrounded represented-area extraction, applying multipliers once;
  explicit group policy must match the approved matrix rather than name heuristics.
  Derive aligned schedules conserving `sum(w_i*d_i*s_i(t))`; preserve originals
  and derivation provenance. Resolve weights against locked geometry evidence.
- [ ] Re-run tests and compare every recipe/member/weight with the approved
  evidence. Expected: exact memberships, weights sum to one within documented
  numeric tolerance and no known-only averaging. Commit
  `feat(programs): implement approved family compositions`.

### Task 7: Add whole-dwelling residential definitions

**Files:** Create `scripts/residential_definitions.py`,
`tests/test_residential_definitions.py`; extend locked evidence only as needed.

**Interfaces:** `residential_definitions.build_residential(context: BuildContext)
-> DefinitionBundle`; distinguish Standards apartment source lineage from
ResStock fixture lineage and preserve determined profile references. Return
source-supported residential constructions and HVAC definitions through the
same element contracts, not a separate fourth residential object kind.

- [ ] Write fixtures asserting an available aggregate apartment is selectable
  without room areas; per-dwelling loads require unit count, area-based loads
  declare represented-area input, and missing magnitude remains unknown despite
  a complete profile. Hotel/hospital source residential flags do not move their
  building families into the Residential gate.
- [ ] Test unmatched selected options stay unresolved, original annual metadata
  is retained, stock variants are never averaged and no generator API is exposed.
  Test ACH50 retains its reference pressure and is not presented as natural
  infiltration; an AFUE or SEER2 rating retains its metric rather than being
  silently converted to COP. Missing assembly layers remain missing even if an
  insulation option supplies a nominal R-value.
- [ ] Run `python -m unittest tests.test_residential_definitions -v`; confirm failures.
- [ ] Extract source-supported magnitudes and required operands from exact fixture
  options/routines. Do not replace unmatched options from a different snapshot,
  assume floor area from a bin, or reconstruct arbitrary houses to fill gaps.
  Extract available envelope, pressure-test infiltration and HVAC rating evidence
  into Tasks 3–4 contracts, retaining unresolved transformations and controls.
  Record fixture-specific readiness and explicit missing-input reasons.
- [ ] Re-run tests and check all 41 fixtures for evidence/profile referential
  integrity. Expected: whole-dwelling support without invented complete loads.
  Commit `feat(residential): expose whole-dwelling program definitions`.

### Task 8: Expand and freeze the validated definition library

**Files:** Extend Task 2–5 modules/tests for full scope; create
`data/definition-releases/v0.1.0/` and
`docs/reviews/catalogue-definition-coverage.md`.

**Interfaces:** Existing `definitions.build`, `definition_validate.validate`,
`definition_release.freeze/verify`; CLI adds `--scope full`,
`--verify --target PATH`, and `--reproduce --target PATH` in the release module.

- [ ] Add regression cases outside Medium Office: hospital total-air requirements,
  hotel PTAC, restaurant shared water, apartment conditioning categories and
  ground/internal roles. Test every source row is either represented or carries
  an explicit exclusion/unsupported reason in coverage.
- [ ] Run expanded definition tests before implementation; confirm new cases fail.
- [ ] Expand exact construction-set and HVAC applicability joins across supported
  families/templates/climates without Cartesian duplication. Distinguish ancillary
  source equipment such as refrigeration/exhaust from a complete HVAC package;
  retain supporting records rather than presenting misleading complete systems.
- [ ] Generate full scope only after the recorded pilot gate. Freeze the canonical
  bundle, schema, locks, notices, manifest, coverage and generated CSV inspection
  exports. Coverage separately reports known parameters, required consumer inputs,
  unresolved source gaps, assumptions, supported composition modes and resources.
- [ ] Verify/reproduce the frozen release from locked sources. Expected: identical
  canonical hashes, all required checks pass; unresolved research inputs are
  allowed only when correctly labelled and cannot masquerade as ready capabilities.
  Commit `data(definitions): freeze element definition library`.

### Task 9: Build the two-gate catalogue and find-an-entry views

**Files:** Create `scripts/definition_site.py` and tests; modify
`scripts/site.py`, `website/assets/core.js`, `website/assets/site.js`,
`website/assets/site.css`, `mkdocs.yml`, `tests/site_core.test.js`,
`tests/site_parity.test.js`, `scripts/site_smoke.py` and site tests.

**Interfaces:** `definition_site.generate(bundle: DefinitionBundle,
target: Path) -> None`; `site.generate_site` consumes a verified definition-release
path through an explicit optional argument, preserving legacy fixture builds.
Browser filtering consumes generated result/facet metadata, not hard-coded options.

- [ ] Write route/filter tests: exactly Residential and Non Residential at entry;
  exactly three kinds within each; reset dependent filters when context changes;
  hide climate for climate-independent programs; unsupported combinations show an
  explicit empty state and never fall back to another vintage. Test shared IDs.
- [ ] Run Python site tests and `node --test tests/site_core.test.js tests/site_parity.test.js`;
  confirm the new gate/filter assertions fail before implementation.
- [ ] Implement Programs search/building type/detail/vintage/conditional climate;
  HVAC search/conditional building type/vintage/climate/system type; Constructions
  search/building type/vintage/climate. Detail labels map to SourcePrograms,
  DepartmentMixes and GeneralMix; only actual modes appear. Vintage appears once.
- [ ] Detail pages expose element roles/parameters, load basis and scope,
  assumptions/gaps, source/reviewed and composition lineage, required consumer
  inputs and lazy evidence/schedules. Keep historical URLs reachable without
  promoting old raw record kinds to the new first-class catalogue.
- [ ] Test keyboard access, mobile layout, no-JavaScript navigation, deep links,
  copyable IDs, stale filters and lazy-resource errors using Playwright. Run
  `python -m scripts.site`, `python -m mkdocs build --strict`,
  `python -m scripts.site_check` and `python -m scripts.site_smoke --screenshots build/screenshots`.
  Expected: valid links and usable routes with bounded selective delivery. Commit
  `feat(catalogue): add residential and nonresidential selection gates`.

### Task 10: Document, reproduce and publish the new contract

**Files:** Modify `README.md`, `docs/site-build.md`, delivery guide generators,
`.github/workflows/validate.yml`, `.github/workflows/catalogue-site.yml`,
`scripts/query_history.py` and retention tests; add release/migration notes.

**Interfaces:** CI consumes frozen v0.1.0 definitions and v2 exporter. History
retention restores and republishes each delivery major independently, maintaining
all previously advertised immutable manifests/resources and v1 client behavior.

- [ ] Add tests for v1/v2 coexistence, retained historical snapshots, missing
  established history failing publication, first-v2 bootstrap only, and storage
  budgets. Fail oversized artifacts before deployment; never delete referenced
  snapshots to make the build fit.
- [ ] Run history/query tests; confirm the new retention assertions fail.
- [ ] Extend retention and CI path filters/locked retrieval. Publish complete
  request/response schemas, units/bases, statuses, IDs, fixed HVAC performance
  semantics, applicability, required inputs, composition rules and examples.
  Include field-projection/lazy-fetch examples sufficient for independent clients.
- [ ] Run `python -m unittest discover -s tests`, both Node suites, all frozen
  release verifiers/reproducers, strict MkDocs/link/browser checks and security
  audit. Run CI's existing Ubuntu/Windows matrix; inspect generated coverage and
  actual page screenshots. Expect all required checks pass before publication.
- [ ] Commit `feat(release): publish versioned catalogue definitions and delivery`;
  push `feature/query-dto` and use the existing authorized deployment workflow
  with its supported explicit dispatch. Do not merge main, weaken environment
  protection, create credentials or mutate old snapshots.
- [ ] Verify live gate, representative filters/detail pages, guides and both
  delivery majors. Retrieve representative v2 responses with manifest hashes
  checked; pin the public snapshot in the completion report. Roll back a failed
  deployment to the prior verified artifact while preserving immutable history.

### Task 11: Dispatch the downstream BEMGen stage after publication

**Files:** No BEMGen edits in this checkout. The handoff is the user-requested
new BEMGen chat, using the published documentation and pinned snapshot.

**Interfaces:** Use the app's project inventory to identify BEMGen, then create
the previously requested task with an actionable prompt. No local handover
document is necessary; do not use stale ignored build notes as the contract.

- [ ] Check the public contract covers every primary kind, all approved family
  modes, whole-dwelling programs and explicit availability constraints. Re-run a
  small live selective-fetch example before dispatch.
- [ ] Send the BEMGen agent the public guides, exact v2 snapshot, family matrix,
  defaults and exclusions. Request plan generators, preset/schema definitions
  and a manifest-pinned selective fetcher; identify geometric assignment and
  sizing as consumer responsibilities. No schedule generators in this stage.
- [ ] Return the new chat link plus the atlas release, validation evidence and
  unresolved source gaps. If BEMGen cannot be located or dispatched, complete the
  atlas work and report that specific handoff blocker without guessing a target.

## Autonomous operating decisions and completion criteria

Use the existing branch and pinned dependencies; change implementation details
reversibly within these interfaces. Research routine source ambiguities, document
the evidence and continue. A gap in one family must not stop independent supported
definitions. Record exceptional science/licensing/public-release/architecture
blockers precisely; do not resolve them through invented values or silent policy
changes. Internal and ground generic policies need cited, versioned values, not a
future approval checkpoint. Keep meaningful progress updates during active work.

Complete means the verified canonical library is frozen and reproducible; the
published catalogue has the two gates and three kinds; approved compositions,
whole-dwelling semantics, element identities, air requirements and fixed HVAC
performance are accessible; v1 remains usable; v2 is documented and manifest
pinned; live checks pass; and the authorized BEMGen handoff is dispatched or its
external blocker is explicitly reported. Missing source data remain visible in
coverage and consumer requirements. Do not claim that every library row supplies
a complete ready-to-simulate model.

## Plan self-review

Spec coverage: entry/find views → Task 9; programs/ownership → Tasks 2, 6, 7;
constructions/air/generic roles → Tasks 3, 8; fixed HVAC → Tasks 4, 8;
schedules/deferred generators → Tasks 2, 6, 7; selective delivery → Tasks 5, 10;
pilot/release → Tasks 5, 8, 10; downstream stage → Task 11.
All five review-focus cases have owning tests. Interfaces are defined once and
consumed consistently. The two initial material questions are settled above.
