# Remaining atlas tasks

Updated: 2026-10-15, following the user's construction closure and BEMGen-test priority decision.

This is the current roadmap for remaining work. The
[Program JSON completion plan](superpowers/plans/2026-10-11-program-completion.md)
is complete and remains the implementation record. The order and scope below
supersede the earlier proposal to hand off to BEMGen immediately after program
publication. The current execution order below supersedes the earlier requirement
to discuss schedule generators before the BEMGen handoff. Discussion items remain
open design topics, not accepted designs.

## Current execution order

1. **Complete:** review and close the above-ground construction implementation,
   with fresh coverage, reproducibility and consumer-boundary evidence. See the
   [milestone closure record](reviews/construction-milestone-closure.md).
2. Prepare the construction site and release for protected-main publication.
   Publication and its required checks are a separate gate from implementation
   closure; closing construction does not claim production deployment.
3. Prepare the BEMGen test handoff using existing schedule contracts. Include
   both construction representations, program/schema integration, component
   assignment, geometry responsibilities, infiltration and mass accounting.
4. Support BEMGen integration testing and resolve Atlas contract/data issues;
   record the acceptance results and remaining limitations.
5. Revisit lighter artifact delivery only after the BEMGen test is accepted.

Schedule-generator packaging does not block publication or BEMGen testing.
Ground/foundation and systems remain deferred. Only item 1 is authorized for
the current execution turn; subsequent items are planned, not started.

The [JSON completion discovery and delivery plan](superpowers/plans/2026-10-12-json-completion.md)
details tasks 2-5 on `feature/json-completion`. Its first deliverables are separate
construction and system field reviews with coverage patterns and annotation space.
The independent above-ground construction consumer export is frozen at 100%
source coverage. Its detailed/unified implementation and local integration are
reviewed and closed in the [closure record](reviews/construction-milestone-closure.md).
Production publication remains open. Ground and systems are deferred.

| Order | Task | Status |
| --- | --- | --- |
| 1 | Publish Program JSON v3 | Complete; live verified 2026-10-12 |
| 2 | Include constructions and systems, with separate JSON exports and pages | Above-ground JSON frozen at 100%; publication pending; ground/foundation and systems deferred |
| Deferred | Discuss shipping schedule generators instead of a single generated schedule | Deferred; not a publication or BEMGen-test prerequisite |
| 3–4 | Prepare BEMGen schema/typology handoff and support integration testing | Next after publication preparation; use existing schedule contracts |
| 5 | Discuss a lighter deployed site and decoupled artifact generation | Deferred until BEMGen testing is accepted |

## 1. Publish Program JSON v3

- [x] Review and integrate `fix/program-consistency` into the publication path.
- [x] Replace workflow path filters with required checks for every PR/main push,
  including the v3 exporter, schema, recovery inputs, policy and examples.
- [x] Build the full catalogue, validate its resources and links, and verify
  representative raw/ready copying and schedules before deployment.
- [x] Publish and verify live Medium Office and residential v3 exports,
  contract documentation, source/default distinctions and required bindings.
- [x] Record the deployed commit and verification evidence.

Starting point: program implementation `15be6bb`, source recovery `6038df7`,
and the [completeness receipt](reviews/program-json-completeness.json).
There are 1,900 completed program exports within the agreed scope. Protected
[PR #4](https://github.com/Energy-Atlas/archetype-atlas/pull/4) integrated them into
`main`. Commit `d3c1b3bca09aae9e185b17dc4c61f8e50bb19bf4` was successfully
published by [main run 38214474243](https://github.com/Energy-Atlas/archetype-atlas/actions/runs/38214474243).
The [publication record](reviews/program-v3-publication.md) and
[live verification receipt](reviews/program-v3-live.json) confirm v3 schema,
resource checksums, exact reviewed examples and required bindings on the deployed
Medium Office and residential pages. The program-consistency branch was retired.

**Comments / decisions:**

<!-- Write here. -->

## 2. Constructions and systems: separate JSONs and pages

Current milestone: publish above-ground construction at 100% coverage, independently
of deferred ground/foundation and systems. Foundation/basement owns its below-grade
and foundation-dependent interface assemblies. Construction includes infiltration;
mechanical outdoor/total-air requirements are deferred. Fixed catalogue ACH per
construction and climate zone is selected, derived using source archetype
reference geometry. The 2013 climate map, residential source annual-average
helper and commercial passive-envelope reference are accepted.
[ADR 0020](adr/0020-above-ground-construction-first-release.md)
supersedes the earlier all-kind publication gate for this first milestone.

Source reference geometry/exposure is recovered for 41 residential and 129
commercial cases. All 15 generic packages have reference matches; the full
original package receipt has 182 matches and one explicitly uninstantiated
SmallHotel space scope. The accepted overlay uses the whole SmallHotel benchmark
for that scope, keeping its distinct ID and absent-room flag. The
[climate/reference review](reviews/construction-ach-reference-proposals.md)
records the accepted conditions and pilot constants. The independent
[construction contract](construction-json-v1-contract.md) now integrates them
with recovered assemblies and complete selector dependencies.

The final consumer inventory contains 4,868 assemblies, 183 packages and 41
residential enclosures: 5,092/5,092 ready identities, including all 3,206 eligible
baseline IDs, 1,456 recovered selector dependencies and 430 residential assembly
children. Schema, examples, licenses, checksum manifest and completeness receipt
are frozen in `data/construction-releases/v1.0.0`. The original 3,798 rows remain
immutable evidence, including 592 deferred ground-contact elements.

- [x] Recover all above-ground native source assemblies and selector closure.
- [x] Freeze the independent above-ground schema, JSON, examples and 100% receipt.
- [x] Integrate the construction v2 contract into local site pages, filters,
  complete JSON copying and linked resource pages.
- [ ] Publish through protected-main checks after review. The current task
  authorizes local building only; no push, GitHub workflow or Pages deployment.
- [ ] Resume ground/system work only when its deferred scope is reopened.

A unified construction-set v2 schema/exporter and both accepted examples are
now frozen in `data/construction-releases/v2.0.0/`, with all 224 definitions,
4,798 supported contexts and 4,868 assemblies retained and validated. The
[review entry](reviews/construction-set-v2-review.md) records acceptance and
the complete migration. The [local site integration record](superpowers/plans/2026-10-14-construction-site-integration.md)
tracks step 4 of the construction-set delivery sequence; production publication
remains pending.
BEMGen owns the future translator. The combined step-2 checklist below stays open where systems or
publication are still required.

- [x] Inventory current construction/material and system/component exports,
  their physical inputs, applicability, source gaps and model bindings.
- [ ] Define separate versioned construction and system export contracts;
  keep their objects and pages separate from program JSON.
- [ ] Establish the completeness requirements for each kind. Recover source
  values first and discuss material unresolved assumptions with the user.
- [ ] Verify ready exports for every construction and HVAC variant; pilots or
  published blocked/raw variants do not satisfy the completion gate.
- [ ] Provide representative construction and system examples that identify
  source values, accepted defaults, dependencies and simulation inputs.
- [ ] Validate the contracts and publish the corresponding JSONs, pages and
  documentation.

Starting point: the catalogue already has separate construction and HVAC-system
pages, linked materials/components, and raw JSON. The remaining work concerns
the export contracts and completeness, rather than creating those kinds from
scratch. Program defaults do not implicitly apply to construction or system
unknowns. Geometry, assignment and sizing remain consumer responsibilities.

Updated user decisions on 2026-10-12: every construction and HVAC variant must
be simulation-ready before step 2 closes. Detailed DHW consumer models are not
required; retain heater/loss/solar source evidence separately. Simplified draw-only
water-heating energy remains in program JSON with its accepted exclusions and
solar skip. The skip does not exempt the fixture's construction/HVAC variants.
See [ADR 0019](adr/0019-all-variant-readiness-and-hvac-delivery-scope.md).
This supersedes the earlier requirement for ready detailed DHW delivery. The
water-use room gains and distribution-waste draws remain outside program scope.

**Comments / decisions:**

<!-- Write here. -->

## 3. Discuss shipping schedule generators

Deferred by the 2026-10-15 user decision. Retain the questions below for later;
existing schedule contracts support the first BEMGen integration test.

- [ ] Compare a versioned executable generator with a compact parametric recipe
  and the current fixed realization. Identify which schedule families each
  approach can faithfully reproduce.
- [ ] Discuss the consumer interface: parameters, seed, calendar, weather,
  runtime/dependencies, units, rule precedence, special days and output schema.
- [ ] Define reproducibility and reference-realization checks, including which
  source-fixed schedules should remain fixed.
- [ ] Agree on packaging, supported variants and migration behavior; record the
  design in an ADR before implementing it.

Retain deterministic reference cases for comparison. Shipping a generator must
not silently transplant the recorded annual calendar or discard source holiday,
design-day, date-selector or ordering semantics. This task revisits the earlier
deferral of schedule generators; it does not assume a particular package or
runtime has already been selected.

**Comments / decisions:**

<!-- Write here. -->

## 4. BEMGen schema and missing-typology handoff

- [ ] Compare BEMGen's current schemas and consumers with the program,
  detailed/unified construction and existing schedule contracts. Systems remain
  deferred and a schedule-generator decision is not a prerequisite.
- [ ] Inventory missing typologies against BEMGen's actual plan generators;
  identify missing generators and supported atlas assignments explicitly.
- [ ] Prepare a handoff with exact contract versions, example JSONs, published
  artifact identity, defaults/exclusions, required bindings and migration work.
- [ ] Send the handoff to the identified BEMGen task, covering both JSON schema
  updates and the missing typology plan generators.
- [ ] Record the receiving task and acknowledged scope.
- [ ] Define representative detailed/unified translation tests, confirm valid
  EnergyPlus inputs, resolve Atlas-side issues and record test acceptance.

The handoff must cover geometry/program assignment and consumer sizing as well
as schema changes. Do not invent the missing typology list or the target task.
This replaces the narrower handoff scope in Task 11 of the
[earlier catalogue plan](superpowers/plans/2026-10-07-catalogue-redesign.md).

**Comments / decisions:**

<!-- Write here. -->

## 5. Discuss a lighter site and decoupled generation

Deferred until the BEMGen integration test is accepted, per the 2026-10-15 decision.

- [ ] Measure CI generation/validation/build time separately from deployed
  payload size and browser load/interaction cost.
- [ ] Evaluate the user's proposal: keep generated JSON artifacts in Git and
  run generation in an explicitly invoked one-shot workflow; normal site builds
  consume those artifacts without regenerating them.
- [ ] Discuss where artifacts live, how schema/source/policy changes invalidate
  them, and how manifests, checksums and reproducibility detect stale outputs.
- [ ] Compare alternatives for payload size, including shared resources,
  compression and selective loading, using the measurements.
- [ ] Agree on the architecture and record an ADR before implementation.

Separating generation from CI can reduce build work; deployed payload and
browser performance need their own measurements. A lightweight publication path
must still reject missing, stale or incompatible artifacts and retain source
provenance and license notices. Committing generated JSON is a proposal for this
discussion, not an already adopted repository policy.

**Comments / decisions:**

<!-- Write here. -->
