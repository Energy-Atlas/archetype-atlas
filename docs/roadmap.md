# Remaining atlas tasks

Updated: 2026-10-21, for the integrated construction foundation/ground publication
candidate, parallel BEMGen v7 testing and the merge of the readable schedule
generator (unreleased).

This is the current roadmap for remaining work. The
[Program JSON completion plan](superpowers/plans/2026-10-11-program-completion.md)
is complete and remains the implementation record. The order and scope below
supersede the earlier proposal to hand off to BEMGen immediately after program
publication. The current execution order below supersedes the earlier requirement
to discuss schedule generators before the BEMGen handoff. Discussion items remain
open design topics, not accepted designs.

## Current execution order

1. **Complete:** above-ground construction was published and tagged
   `construction-delivery-2026-10-16`. Its frozen artifacts remain unchanged.
2. **Implemented locally:** integrated foundation/ground in detailed JSON 3.0.0
   and unified JSON 2.0.0. All 177 suites / 3,320 source-supported contexts are
   complete; release documentation and foundation-aware publication gates are
   prepared. Clean-checkout verification, protected-main PR checks, deployment
   and live verification remain pending. See the
   [foundation release notes](release-notes-construction-foundation-v1.0.0.md).
3. **Handed off locally:** BEMGen packet v7 contains 19 detailed/unified pairs,
   source/method clarifications and [required consumer tests](bemgen-foundation-instantiation-tests.md).
   BEMGen integration testing/acceptance remains a separate consumer gate.
4. Support BEMGen testing and resolve any Atlas contract/data defects it finds.
   Its completion is not required to prepare/publish Atlas independently, but
   consumer acceptance must not be claimed before the tests pass.
5. Restructure release storage and the site per
   [ADR 0036](adr/0036-suite-based-release-storage.md), unblocked on 2026-10-21
   ahead of BEMGen acceptance.

Systems remain deferred. Schedule-generator packaging does not block this
construction milestone; no program/schedule generation changes are included.
The branch, rebased onto `main` after the schedule-generator merge, is integrated
through a protected-main pull request whose required checks gate the merge.
Production foundation deployment and live verification follow that merge and are
not yet recorded. Older plans/review receipts below document historical stages
and do not supersede this current order.

| Order | Task | Status |
| --- | --- | --- |
| 1 | Publish Program JSON v3 | Complete; live verified 2026-10-12 |
| 2 | Publish integrated construction foundation/ground JSON and pages | Implemented and locally validated; publication preparation complete; clean-checkout/PR/main deployment gates pending |
| Deferred | Complete systems JSON and simulation-ready variants | Deferred; not a foundation publication prerequisite |
| Deferred | Package schedule generators | Readable generator merged, unreleased ([ADR 0035](adr/0035-readable-generator-restructure.md)); release deferred; not a construction publication or BEMGen-test prerequisite |
| 3–4 | BEMGen handoff and integration testing | v7 prepared; consumer acceptance pending; resolve reported Atlas defects; use existing schedule contracts |
| 5 | Lighter site and decoupled artifact generation | Decided in [ADR 0036](adr/0036-suite-based-release-storage.md); implementation started on `codex/atlas-storage-restructure` |

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

Current milestone: publish the combined Construction Suite with source-supported
foundation/ground content. [ADR 0027](adr/0027-combined-construction-foundation.md)
and the [embedded contract](construction-foundation-ground-v1-contract.md) extend
the published above-ground delivery prospectively, preserving its frozen data.
GroundFloor, FoundationWall, FloorOverFoundation and RimJoist now reuse existing
component/assignment structures. Detailed 3.0.0 / unified 2.0.0 cover 3,308 contact
and 12 no-contact contexts; native methods remain native where required.
Systems and mechanical outdoor/total-air requirements remain deferred. Fixed
catalogue ACH and the existing shared mass contract remain unchanged.

### Historical above-ground milestone

The first milestone published above-ground construction independently of ground
and systems under [ADR 0020](adr/0020-above-ground-construction-first-release.md).
The accepted source-reference geometry, 2013 climate map, residential annual-average
helper and commercial passive-envelope ACH policy remain applicable.

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
- [x] Publish the above-ground milestone through protected-main checks; preserve
  its `construction-delivery-2026-10-16` marker and frozen artifacts.
- [x] Reopen and implement foundation/ground under the accepted integrated design.
- [ ] Finish clean-checkout verification and publish the combined foundation release
  through protected-main checks, deployment and live verification.
- [ ] Resume systems work only when its deferred scope is reopened.

A unified construction-set v2 schema/exporter and both accepted examples are
now frozen in `data/construction-releases/v2.0.0/`, with all 224 definitions,
4,798 supported contexts and 4,868 assemblies retained and validated. The
[review entry](reviews/construction-set-v2-review.md) records acceptance and
the complete migration. The [local site integration record](superpowers/plans/2026-10-14-construction-site-integration.md)
tracks the historical construction-set delivery sequence. Combined foundation
publication remains pending as recorded above.
BEMGen owns the translator and its current integration tests. The combined step-2 checklist below stays open where systems or
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

Shipping is deferred by the 2026-10-15 user decision: existing schedule contracts
support the first BEMGen integration test, and the generator is not a
prerequisite for publication. The readable [schedule generator](schedule-generator.md)
(`atlas_schedules`, unreleased; [ADR 0035](adr/0035-readable-generator-restructure.md))
is merged. It covers all 1,900 catalogue programmes across 15 ComStock building
types, ResStock dwellings, apartment units and common areas, 186 shared hot-water
services and the 16 DOE reference locations. Native OpenStudio / Ruby answer
keys validate it. The earlier bit-exact v0.1.0–v0.8.0 builds were never
published and are retired.

- [x] Compare a versioned executable generator with a compact parametric recipe
  and the current fixed realization. Identify which schedule families each
  approach can faithfully reproduce.
- [x] Discuss the consumer interface: parameters, seed, calendar, weather,
  runtime/dependencies, units, rule precedence, special days and output schema.
- [x] Define reproducibility and reference-realization checks, including which
  source-fixed schedules should remain fixed.
- [x] Agree on packaging, supported variants and migration behavior; record the
  design in an ADR before implementing it.

The design decisions are recorded in [ADR 0023](adr/0023-generated-constituents-and-physical-mixtures.md)
and [ADR 0035](adr/0035-readable-generator-restructure.md); the invocation guide is
linked above. A release (version, checksum manifest) remains a separate, deferred step.

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
- [ ] Hand over the release 2.0.0 updates in
  [bemgen-handoff-release-2-0-0.md](bemgen-handoff-release-2-0-0.md) (daylighting
  fractions as plain values, and what milestone A adds).
- [ ] Define representative detailed/unified translation tests, confirm valid
  EnergyPlus inputs, resolve Atlas-side issues and record test acceptance.

The handoff must cover geometry/program assignment and consumer sizing as well
as schema changes. Do not invent the missing typology list or the target task.
This replaces the narrower handoff scope in Task 11 of the
[earlier catalogue plan](superpowers/plans/2026-10-07-catalogue-redesign.md).

**Comments / decisions:**

<!-- Write here. -->

## 5. Discuss a lighter site and decoupled generation

No longer deferred: the user unblocked it on 2026-10-21, ahead of BEMGen
acceptance. The decisions are recorded in
[ADR 0036](adr/0036-suite-based-release-storage.md); implementation is on
`codex/atlas-storage-restructure`.

- [x] Measure CI generation/validation/build time separately from deployed
  payload size and browser load/interaction cost.
- [x] Evaluate the user's proposal: keep generated JSON artifacts in Git and
  run generation in an explicitly invoked one-shot workflow; normal site builds
  consume those artifacts without regenerating them.
- [x] Discuss where artifacts live, how schema/source/policy changes invalidate
  them, and how manifests, checksums and reproducibility detect stale outputs.
- [x] Compare alternatives for payload size, including shared resources,
  compression and selective loading, using the measurements.
- [x] Agree on the architecture and record an ADR before implementation.
- [ ] Split CI into parallel jobs, limit Windows to pinned-producer checks and
  drop the duplicate release verification (separate pull request).
- [ ] Implement the suite-based commercial release `data/atlas-releases/v1.0.0`
  and its consumer exports, test-first.
- [x] Replace per-record pages with suite pages, one viewer page and one JSON store
  ([ADR 0043](adr/0043-suite-based-site.md)).
- [ ] Retire the frozen release folders to tags once the new release verifies.

**Comments / decisions:**

Release data stays in Git; site output does not and is cached by input digest.
Programs and construction sets are one file each under
`commercial/<template>/<building-type>/`; schedules get one table per folder;
shared assemblies, materials and HVAC performance records get one library per
template; evidence has its own mirrored tree. Source-backed and filled exports
both ship. Residential storage is deferred.
