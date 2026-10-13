# JSON completion discovery and delivery plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan inline, task by task. Steps use checkboxes for tracking. Complete the field reviews before fixing new contract interfaces; material scientific or architectural decisions remain discussion items.

**Goal:** Complete construction and system JSON delivery, then resolve schedule-generator packaging, hand off to BEMGen, and decide how to lighten publication.

**Current milestone (2026-10-13):** First ship above-ground construction at 100%
coverage. Combined ground/foundation/basement, its below-grade/interface assemblies,
and all systems are deferred. Construction includes infiltration only; fixed
catalogue ACH per construction and climate zone is selected, derived using source
archetype reference geometry. Climate factors and conversion details remain open.
Follow [ADR 0020](../../adr/0020-above-ground-construction-first-release.md)
for the revised publication gate and source selector/dependency audit.

**Architecture:** Extend the existing separate catalogue objects and pages with versioned consumer contracts. Recover source semantics before applying reviewed defaults; distinguish unknown physics from geometry, assignment and sizing supplied by the simulation consumer. Keep the later generator and publication choices open until their evidence and alternatives have been reviewed.

**Gap proposals and user annotations:** [Construction/HVAC gap review](../../reviews/construction-system-gap-proposals.md). Current phase: above-ground construction only. Ground-dependent C work and all H work are deferred; H and X entries remain unreviewed and their blanks do not signify agreement. The user selected the second axis boundary under ADR 0020. Apply C annotations and audit C09's omitted source selectors; retain comment areas.

**Tech stack:** Python, JSON Schema, pinned upstream source/runtime calculations where necessary, unittest, MkDocs and the existing content-addressed JSON delivery.

**Spec:** [Current roadmap](../../roadmap.md), [research brief](../../AGENT_RESEARCH_BRIEF.md), [element definitions ADR](../../adr/0013-element-definition-catalogue.md), [program completion ADR](../../adr/0016-program-completion-policy.md), [all-variant readiness ADR](../../adr/0019-all-variant-readiness-and-hvac-delivery-scope.md), and [schedule mechanisms ADR](../../adr/0005-parametric-schedule-generators.md).

## Starting state and agreed scope

- Planning branch: `feature/json-completion`, created from `main` at `c2dd1fd53481f50f0853fa81f9f3cee1155b3cd1`.
- Program JSON v3 is published and live verified. Its [publication record](../../reviews/program-v3-publication.md) closes roadmap task 1.
- Construction and HVAC objects already have separate pages and raw JSON. They need consumer contracts and a completeness review, not replacement of the catalogue.
- Initial source-recovery scope covered HVAC and domestic hot-water equipment together, including heater losses and solar equipment. Latest delivery decision: **no ready detailed DHW models are required**; retain their source evidence separately and keep simplified draw-only heating in program JSON.
- Latest readiness decision: **every construction and HVAC variant must be simulation-ready** before the completed step 2 release. Ready pilots and raw/blocked variants do not satisfy that gate. ADR 0019 records both decisions.
- Signed water-use room gains and distribution-waste water draws remain outside the agreed program contract. Equipment scope does not silently reintroduce them as program loads; discuss any proposed extension to their treatment explicitly.
- Roadmap order remains constructions/systems, schedule-generator discussion, BEMGen handoff, then lighter-site discussion. Record performance measurements along the way without prematurely adopting a new publication architecture.

The read-only census on 2026-10-12 used `data/definition-releases/v0.1.1`, whose manifest SHA-256 is `5787c554fd7ee554b45742b6a3bb7df04ea25219f7903d14f43603793e6fcd4e`:

| Table | Records | Initial review focus |
| --- | ---: | --- |
| Constructions | 3,798 | 3,574 elements, 183 packages, 41 residential enclosures |
| Materials | 6,210 | Different requirements for massive, massless, gas and glazing models |
| HVAC systems | 1,046 | Source roles/descriptors; no populated connection graphs |
| Components | 4,217 | Rating predicates, equipment roles, curves and source bindings |
| Services | 217 | Supporting demand records; this is not a count of physical water heaters |
| Schedules | 4,410 | Preserve rule semantics and embed required dependencies |

These counts describe the existing bundle, not a completed consumer contract or a count of missing simulation inputs.

## Global constraints

- Canonical JSON uses SI units and explicit schema versions; null means unknown or not reported, never implicit zero.
- Preserve source revision/checksum, locator, original value/unit, transformation, extraction date and interpretation for every recovered field.
- Preserve existing-stock versus code/prototype contexts, climate/vintage variants and source identities. Similar names are not evidence of physical identity.
- Preserve ordered layers, thermal mass, film conventions, source adjustments, schedule selectors/dates/design days and rule order.
- Geometry, spatial assignment and sizing remain consumer responsibilities. Missing source physics must not be disguised as a routine consumer binding.
- Full eligible inventory is the baseline 3,798 constructions and 1,046 HVAC variants. Preserve IDs; do not reduce the denominator or introduce unapproved defaults to claim readiness. Detailed DHW source evidence is outside this ready-export inventory.
- For the current construction milestone, ADR 0020 explicitly partitions that baseline: defer 592 ground-contact elements, project the 183 mixed packages and 41 residential enclosures, and retain all eligible above-ground identities. Recover missing source-defined above-ground dependencies before freezing the final denominator. Earlier ground/HVAC tasks and all-kind gates below are future-phase requirements, not prerequisites for this publication.
- Program defaults do not apply to constructions or systems. Existing generic construction assumptions remain limited to their reviewed internal/ground-contact scope.
- Keep frozen releases and raw downloads immutable. New inputs require locked retrieval, retained notices and a new release when canonical definitions change.
- Validate a Medium Office pilot before catalogue expansion. Release checks cover schema, physical, referential, schedule, provenance and reproducibility behavior.
- Before every commit inspect the staged diff and run `python -m scripts.audit --staged`; use neutral automated authorship, Conventional Commits and the required `Agent-Model` trailer.
- Working branches validate manually; PRs target protected `main`. Production deployment remains `main` only, with all three required checks. Follow `design/ui-design-spec.md` for any page styling changes.

## Review focus

| Failure mode | Expected behavior | Owning task |
| --- | --- | --- |
| Inapplicable material properties counted as missing | Model-specific requirements; no opaque SHGC or massless density invented | 2A / 2C |
| Duplicate glazing names or U-only assembly identity | Resolve through source context; retain layers/mass, reject ambiguous selection | 2A / 2C |
| Descriptor labels presented as executable HVAC physics | Recover source recipes, controls and performance; expose actual unresolved inputs | 2B / 2D |
| Conditional efficiency collapsed to a guessed COP | Preserve rating metric, capacity/date predicates, curves and operating conditions | 2B / 2D |
| DHW demand or losses counted more than once | Keep simplified energy in program JSON and detailed evidence separate; preserve service ownership | 2B / 2E |

## 2A. Construction field review

**Files:** Read `scripts/construction_definitions.py`, `scripts/residential_definitions.py`, `scripts/definition_contract.py`, `sources/definition-policy.json` and the frozen bundle. Create `docs/reviews/construction-json-field-review.md` and a machine-readable census alongside it.

- [x] Build an applicability matrix by representation, construction role and material model. Use applicable-record denominators instead of treating every absent parameter as missing.
- [x] Write one review entry per JSON field/property, summarizing affected counts, common source/model types, patterns, representative IDs, recovery options and remaining uncertainty. Include a **User comments / decision** area in every entry; do not write one entry per catalogue record.
- [x] Classify each affected case as source-recoverable, unresolved source data, already assumed, not applicable, or a consumer geometry/boundary input. Trace existing assumptions to their policy and evidence.
- [x] Investigate the 12 ambiguous glazing rows, the 41 residential enclosures without resolved assemblies, and the four existing assumed construction rows. Resolve duplicate physical definitions through source selectors rather than first/last-match selection.
- [x] Audit F/C ground models and their area/perimeter/height requirements separately from U-value constructions. Review source film resistance, adjusted layers, glazing optical properties and infiltration basis.
- [x] Identify recoverable residential layers and selected source options. Preserve ACH50/reference pressure; do not reinterpret pressure-test leakage as natural infiltration.
- [x] Reconcile census totals with the frozen manifest and record source/code identities. Present genuine missing inputs and concrete proposals for any new assumptions.

**Exit:** Every applicable construction field has a documented disposition and annotation space. Unresolved physical data and required consumer operands are separately enumerable.

**Comments / decisions:**

<!-- Write here. -->

## 2B. HVAC and hot-water equipment field review

**Files:** Read `scripts/hvac_definitions.py`, `scripts/residential_definitions.py`, the service/component tables, and the pinned residential recovery inputs under `data/program-inputs/`. Create `docs/reviews/system-json-field-review.md` and its machine-readable census.

- [x] Review equipment family, fuel, heating/cooling components, fans, terminals, ventilation, controls, schedules, efficiency/rating metrics, performance curves and source topology/recipes.
- [x] Use the same field-based review format as 2A, with affected counts/types, evidence, proposed recovery and a user annotation area. Apply comments to all equivalent source/model cases, including unannotated ones.
- [x] Investigate all 1,046 empty connection lists and the 94 systems with empty component lists. Distinguish nominal recipes, deliberately absent equipment and extraction gaps; do not infer absence of equipment from an empty list alone.
- [x] Inspect the 707 conditional performance-rule components and 726 curve components. Identify source equipment assignments, capacity bands, rating dates, metrics, domains and controls instead of selecting an arbitrary efficiency.
- [x] Recover residential equipment selections through pinned source routines where required. Reuse retrieval/runtime locks where valid and extend them explicitly for additional source resources.
- [x] Inventory commercial and residential DHW heaters, storage, fuels, efficiency models, standby losses, recirculation and solar equipment where reported. Identify missing source fields and geometry/weather/temperature/assignment operands by equipment type.
- [x] Map physical DHW equipment to existing local/shared water demands without duplicating demand. Preserve instantiate-once service ownership and distinguish heater losses from fixture-related room gains.
- [x] Present unresolved source physics with concrete options; do not invent COP, fan pressure, plant configuration, heater efficiency or solar performance to make an export pass.

**Exit:** HVAC and DHW have model-specific field requirements, source recovery paths and explicit remaining scientific/architectural questions.

**Comments / decisions:**

<!-- Write here. -->

## 2C. Construction contract and Medium Office pilot

**Planned files:** `schemas/construction-json-v1.schema.json`, `scripts/construction_json.py`, `tests/test_construction_json.py`, `docs/construction-json-contract.md`, and examples under `docs/examples/construction-json-v1/`. Record contract decisions in a new ADR; these names are proposed destinations, not existing interfaces.

- [ ] Settle the construction choices in the decision table below using 2A evidence, then specify the schema and exporter interface before implementation.
- [ ] Define distinct element and package representations, explicit field status/provenance, ordered materials, scoped air requirements and required consumer bindings. Define raw versus ready behavior and which unresolved physics blocks ready export.
- [ ] Select a Medium Office pilot with matching source family, template and climate context. Prefer a 90.1-2019 case if its source bindings support the full pilot; never combine a legacy package and modern system silently.
- [ ] Pin focused tests before implementing recovery/export behavior: massive versus massless material operands, gas/simple/detailed glazing applicability, ambiguous names, layer order/mass, source films/adjustments, F/C geometry and leakage reference pressure.
- [ ] Export and inspect the complete pilot dependency closure. Show source values, existing accepted assumptions and inputs still required by the simulation consumer.
- [ ] Compare normalized pilot values against the pinned source construction calculations. Record exactly which comparisons were executed; schema validation is not simulation validation.

**Exit:** A documented construction pilot validates without hidden substitutions; every required physical operand is recovered, explicitly assumed under an accepted rule, or blocks readiness. Consumer bindings remain visible.

**Comments / decisions:**

<!-- Write here. -->

## 2D. System contract and HVAC pilots

**Planned files:** `schemas/system-json-v1.schema.json`, `scripts/system_json.py`, `tests/test_system_json.py`, `docs/system-json-contract.md`, and examples under `docs/examples/system-json-v1/`. Extend source recovery scripts/inputs only where needed; document catalogue-kind changes in an ADR.

- [ ] Settle HVAC system representation and readiness semantics from 2B evidence. Specify the schema/exporter interface and migration behavior before coding; detailed DHW is source evidence only under ADR 0019.
- [ ] Describe HVAC families in the system contract, preserving existing HVAC IDs and source context. Keep water demand and simplified draw-only energy in the independent program/service contract.
- [ ] Recover the Medium Office HVAC source recipes and supporting components. Validate compatible source bindings; identify any absent source equipment definition rather than supplying an assumed plant.
- [ ] Add a residential HVAC pilot and targeted HVAC heat-pump cases where supported. Preserve every fixture/variant, including the HVAC of the fixture skipped for simplified solar DHW.
- [ ] Pin tests for conditional rating selection boundaries/dates, efficiency metric units, component/curve assignments and domains, controls/schedules, and explicit serving/sizing operands. Seasonal ratings must not become instantaneous COP values.
- [ ] Pin tests that reject unresolved active HVAC physics and duplicate serving/component instantiation. Verify HVAC consumer exports do not add simplified DHW energy or detailed heater/loss/solar models as required dependencies.
- [ ] Compare available source calculations or translated model inputs, preserving provenance and runtime hashes. Distinguish executed model translation from an actual energy simulation.

**Exit:** HVAC pilot exports satisfy the system contract, with no guessed topology/performance and explicit consumer assignments/sizing. Pilots are intermediate gates; all-variant readiness remains required in 2E.

**Comments / decisions:**

<!-- Write here. -->

### Contract choices to resolve after the field reviews

| Choice | Concrete starting proposal | Evidence/decision needed |
| --- | --- | --- |
| Construction identity | Separate element/package forms; ordered source materials and mass, with U/F/C as model-specific properties | Source assembly recovery and treatment of residential enclosure packages |
| HVAC topology | Export the recoverable source recipe/components/controls, with consumer serving and sizing bindings | Which source relations can be recovered; whether a recipe is sufficient or a fuller graph is needed |
| DHW delivery boundary | Decided: simplified draw-only energy in program JSON; detailed equipment/solar retained as source evidence | ADRs 0018/0019; no ready detailed DHW export or new primary catalogue kind required |
| Copyable dependencies | Self-contained single-object exports, including required materials/components/curves/schedules | Closure size, cycles, reference semantics and consistency with bulk delivery |
| Remaining defaults | Recover first; propose narrow type/source-specific rules with evidence and scope | User decisions on material unresolved assumptions; no general fallback efficiencies/layers |

The DHW boundary and all-variant readiness gate are accepted decisions. Other rows remain consumer-interface proposals; no new default values are approved.

**Comments / decisions:**

<!-- Write here. -->

## 2E. Catalogue expansion, pages and publication

**Files:** Extend the new exporters/tests and recovery inputs from 2C/2D; integrate with `scripts/object_site.py`, `scripts/active_site.py` and their tests. Add reproducible completeness receipts under `docs/reviews/`; retain historical bundles/schemas.

- [ ] Apply validated recovery/export logic to every construction and HVAC source variant, preserving source identities. Resolve every eligible blocked variant; a raw/blocked disposition does not satisfy the release gate.
- [ ] Produce receipts with input/source/policy/code identities, export hashes, model-specific coverage and remaining bindings. Require ready counts to equal the complete eligible construction/HVAC inventory, zero failed exports and zero unresolved source-physics blockers. Detailed DHW evidence is outside that denominator.
- [ ] Provide construction and system pages with schema links, raw/ready copying as defined by the contracts, and Medium Office/residential examples. Keep program, construction and system payloads distinct.
- [ ] Test schema, physical constraints, dependency closure/orphans/cycles, schedule semantics, provenance and reproducibility. Verify deterministic bytes on the supported Python/platform matrix and run relevant existing definition/site tests.
- [ ] If canonical definitions change, freeze a new version and document migration instead of editing `v0.1.1`. Validate source license notices and locked retrieval for any new inputs.
- [ ] Build and inspect the full site, representative object copying and required simulation bindings. Open a protected-main PR after staged review/security audit; require build and both research matrix checks before integration.
- [ ] After publication, verify live schema versions, payload identities/checksums, example content and consumer bindings; record the deployed commit and receipt.

**Exit:** Roadmap task 2 is complete only when every eligible construction and HVAC variant is ready, separate exports/pages are published and live verified, and required release checks pass. Any eligible blocked export keeps this step open. Detailed DHW model translation is not a release requirement.

**Comments / decisions:**

<!-- Write here. -->

## 3. Schedule-generator design discussion

**Files:** Use `docs/adr/0005-parametric-schedule-generators.md` and `docs/schedule-source-review.md`; save the resulting design and subsequent implementation plan separately.

- [ ] Compare a pinned upstream wrapper, a compact executable recipe and reimplementation, using the actual ResStock and ComStock mechanisms. Identify source-fixed schedules that remain fixed.
- [ ] Demonstrate reproducible reference cases and list required seeds/streams, calendar, weather/location, unavailable periods, special/design days, time resolution, source resources, runtime and license notices.
- [ ] Verify actual commercial runtime dependency bindings; the atlas Standards evidence revision is not automatically ComStock's runtime version. Preserve household activity generation versus commercial operating-hour transformations.
- [ ] Propose an API/package and schedule-schema migration with parity fixtures, deterministic output hashes and explicit consumer operands. Retain the agreed 2007/no-holiday aggregation reference independently of simulation calendar rules.
- [ ] Discuss tradeoffs and record the selected architecture in an ADR before implementation; then write the executable implementation plan and acceptance tests.

**Exit:** A selected generator contract and packaging plan, with supported families and parity requirements. This discussion alone does not deliver a generator.

**Comments / decisions:**

<!-- Write here. -->

## 4. BEMGen handoff

**Deliverable:** A versioned handoff document, actual receiving task, and recorded acknowledgment.

- [ ] Inspect BEMGen's current schemas, atlas consumers and plan-generator inventory. Build a mapping of atlas typologies to supported/missing generators; do not infer missing typologies from names alone.
- [ ] Prepare exact contract/schema versions, published artifact hashes, representative JSON, migration examples, source/default distinctions and exclusions.
- [ ] Specify consumer responsibilities for geometry, program/system assignment, sizing, weather/calendar, service ownership and schedule generation. Include cross-repository acceptance examples for Medium Office and residential cases.
- [ ] Send the authorized handoff to the identified BEMGen task, covering schema updates and missing typology plan generators. Record receiving task identity, acknowledged scope and follow-up ownership.

**Exit:** BEMGen has the concrete contracts and generator-gap inventory needed to implement its changes; completion of those consumer changes is tracked in the receiving task.

**Comments / decisions:**

<!-- Write here. -->

## 5. Lighter publication and deployed site discussion

**Files:** Inspect `.github/workflows/validate.yml`, `.github/workflows/catalogue-site.yml`, artifact delivery and site generation. Save measurements and the accepted architecture in a new ADR before changing workflows.

- [ ] Measure extraction/generation, validation, site build and deployment time separately. Measure compressed/uncompressed payloads and browser load/interaction separately from CI cost.
- [ ] Evaluate the user's proposal: generated JSON artifacts in Git, produced by a manually invoked one-shot workflow; ordinary CI/site builds validate and consume those artifacts.
- [ ] Compare current regeneration and other artifact-storage options against repository growth, payload reuse, reviewability, reproducibility, licensing and operational cost.
- [ ] Specify source/schema/policy/generator invalidation, atomic artifact+manifest updates, stale/missing artifact rejection and locked retrieval. Propose which checks still regenerate samples or verify full reproduction.
- [ ] Evaluate compression, resource reuse, caching and selective browser loading using measurements. Keep payload performance distinct from the cost of generating it.
- [ ] Discuss and record the selected design before implementation. Preserve protected-main deployment and required checks unless an explicit policy change is agreed.

**Exit:** A measured architecture decision and implementation plan. Generated artifacts in Git and one-shot generation remain proposals until this discussion resolves them.

**Comments / decisions:**

<!-- Write here. -->

## Current execution status

Tasks 2A and 2B are complete: the field-review documents and reproducible census are recorded. Source recovery and four independent Medium Office/residential input pilots are available under `docs/examples/energy-recovery/`; see `docs/reviews/json-completion-work-record.md`. Remaining physics stays blocked under the accepted source-only assumption policy. Final consumer contracts/exporters, expansion to ready JSON and site publication (2C-2E) remain open; these source pilots do not complete those tasks.

The user subsequently selected simplified program-level water-heating energy,
covering draw heating only and explicitly excluding standby losses. See
[ADR 0018](../../adr/0018-draw-only-program-water-heating-energy.md). Its consumer
schema, conversion recovery and implementation are available as opt-in
[Program JSON 4](../../program-json-v4-contract.md); detailed DHW
equipment/loss data stays available as independent source evidence.
Heater auxiliaries are also explicitly excluded. The solar-equipped fixture
`source_building_402849` is skipped for the new simplified DHW representation;
its existing program, water draw and detailed solar data remain available.

Latest user decisions are captured in ADR 0019: all construction/HVAC variants
must be ready, and ready detailed DHW models are not needed. The current blocked
construction/HVAC counts still require source recovery and final consumer export
work. The 196 detailed DHW/solar translation blockers no longer block step 2.
