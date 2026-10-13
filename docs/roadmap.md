# Remaining atlas tasks

Updated: 2026-10-13, following the user's construction-first boundary decision.

This is the current roadmap for remaining work. The
[Program JSON completion plan](superpowers/plans/2026-10-11-program-completion.md)
is complete and remains the implementation record. The order and scope below
supersede the earlier proposal to hand off to BEMGen immediately after program
publication. Discussion items remain open design topics, not accepted designs.

The [JSON completion discovery and delivery plan](superpowers/plans/2026-10-12-json-completion.md)
details tasks 2-5 on `feature/json-completion`. Its first deliverables are separate
construction and system field reviews with coverage patterns and annotation space.
Those reviews and independent source-recovery pilots are now recorded; final
consumer exports and publication remain open.

| Order | Task | Status |
| --- | --- | --- |
| 1 | Publish Program JSON v3 | Complete; live verified 2026-10-12 |
| 2 | Include constructions and systems, with separate JSON exports and pages | First ship 100% above-ground construction; combined ground/foundation and systems deferred |
| 3 | Discuss shipping schedule generators instead of a single generated schedule | Design discussion |
| 4 | Send BEMGen a handoff for schema updates and missing typology plan generators | Pending the preceding contract work |
| 5 | Discuss a lighter deployed site and decoupled artifact generation | Design discussion |

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
construction and climate zone is selected; reference conditions remain open.
[ADR 0020](adr/0020-above-ground-construction-first-release.md)
supersedes the earlier all-kind publication gate for this first milestone.

The initial above-ground/interior inventory contains 2,982 elements, plus 183
mixed packages and 41 residential enclosures to project. Missing source selectors
for doors/skylights/additional windows require dependency expansion before the
final eligible inventory and 100% receipt are frozen. The original 3,798 rows
remain immutable evidence, including 592 deferred ground-contact elements.

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

- [ ] Compare BEMGen's current schemas and consumers with the published program,
  construction and system contracts and the schedule-generator decision.
- [ ] Inventory missing typologies against BEMGen's actual plan generators;
  identify missing generators and supported atlas assignments explicitly.
- [ ] Prepare a handoff with exact contract versions, example JSONs, published
  artifact identity, defaults/exclusions, required bindings and migration work.
- [ ] Send the handoff to the identified BEMGen task, covering both JSON schema
  updates and the missing typology plan generators.
- [ ] Record the receiving task and acknowledged scope.

The handoff must cover geometry/program assignment and consumer sizing as well
as schema changes. Do not invent the missing typology list or the target task.
This replaces the narrower handoff scope in Task 11 of the
[earlier catalogue plan](superpowers/plans/2026-10-07-catalogue-redesign.md).

**Comments / decisions:**

<!-- Write here. -->

## 5. Discuss a lighter site and decoupled generation

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
