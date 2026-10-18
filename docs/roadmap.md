# Remaining atlas tasks

Updated: 2026-10-14, following delivery of the schedule generator's M1 scope.

This is the current roadmap for remaining work. The
[Program JSON completion plan](superpowers/plans/2026-10-11-program-completion.md)
is complete and remains the implementation record. The order and scope below
supersede the earlier proposal to hand off to BEMGen immediately after program
publication. Discussion items remain open design topics, not accepted designs.

| Order | Task | Status |
| --- | --- | --- |
| 1 | Publish Program JSON v3 | Complete; live verified 2026-10-12 |
| 2 | Include constructions and systems, with separate JSON exports and pages | Pending contract/completeness work |
| 3 | Schedule generators: exact M1 milestone shipped; broad catalogue coverage open | M1 delivered |
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

- [ ] Inventory current construction/material and system/component exports,
  their physical inputs, applicability, source gaps and model bindings.
- [ ] Define separate versioned construction and system export contracts;
  keep their objects and pages separate from program JSON.
- [ ] Establish the completeness requirements for each kind. Recover source
  values first and discuss material unresolved assumptions with the user.
- [ ] Provide representative construction and system examples that identify
  source values, accepted defaults, dependencies and simulation inputs.
- [ ] Validate the contracts and publish the corresponding JSONs, pages and
  documentation.

Starting point: the catalogue already has separate construction and HVAC-system
pages, linked materials/components, and raw JSON. The remaining work concerns
the export contracts and completeness, rather than creating those kinds from
scratch. Program defaults do not implicitly apply to construction or system
unknowns. Geometry, assignment and sizing remain consumer responsibilities.

**Comments / decisions:**

<!-- Write here. -->

## 3. Discuss shipping schedule generators

The readable [schedule generator](schedule-generator.md) (`atlas_schedules`,
unreleased; [ADR 0035](adr/0035-readable-generator-restructure.md)) covers all
1,900 catalogue programmes across 15 ComStock building types, ResStock dwellings,
apartment units and common areas, 186 shared hot-water services and the 16 DOE
reference locations. Native OpenStudio / Ruby answer keys validate it. The
earlier bit-exact v0.1.0–v0.8.0 builds were never published and are retired. Site
design and production publication remain separate work.

- [x] Compare a versioned executable generator with a compact parametric recipe
  and the current fixed realization. Identify which schedule families each
  approach can faithfully reproduce.
- [x] Discuss the consumer interface: parameters, seed, calendar, weather,
  runtime/dependencies, units, rule precedence, special days and output schema.
- [x] Define reproducibility and reference-realization checks, including which
  source-fixed schedules should remain fixed.
- [x] Agree on packaging, supported variants and migration behavior; record the
  design in an ADR before implementing it.

The frozen M1 ZIP retains its exact calendar, source rule/date-selector/design-day
semantics, source order and complete deterministic reference examples. The
decisions are recorded in [ADR 0023](adr/0023-generated-constituents-and-physical-mixtures.md)
and the shipment contract linked above. Later catalogue families need separate
source bindings and versioned releases.

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
