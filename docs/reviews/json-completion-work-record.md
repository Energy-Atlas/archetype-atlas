# Construction and system JSON work record

Plan: `docs/superpowers/plans/2026-10-12-json-completion.md`.
Branch: `feature/json-completion`. Started: 2026-10-12.

## Accepted execution scope

Implement the field reviews and source recovery, with Medium Office and
residential pilot validation. Construction, system and program contracts remain
independent; cross-contract mixing/assignment is a consumer concern and is not
implemented here. Systems include HVAC and DHW equipment, heater losses and solar.

Use source-defined defaults and previously approved assumptions only. Remaining
physical unknowns stay explicit and block readiness. Do not stop for human
supervision. Skip full site builds, GitHub CI and lengthy local CI, especially
unchanged program generation/validation. Use focused checks of changed behavior.

## Execution decisions

- Ruling: implement source recovery as independently versioned construction and
  system input sidecars; leave frozen definitions and published program exports
  unchanged. This permits review and pilot validation before publication. Cost
  if wrong: migration of the new sidecars, rather than changes to released data.
- Ruling: source recipes and nominal option properties are evidence, not proof
  of executable physics. Missing curves, assemblies or source bindings block
  readiness; geometry, sizing and serving assignment are distinct consumer
  bindings. Cost if wrong: fewer ready exports until additional source recovery.
- Ruling: use focused tests and checksum/schema/physical/provenance checks for
  this pass. Full publication checks remain required for a later release. Cost
  if wrong: integration failures may first surface in the publication phase.

## Progress

- Field review tooling: complete; separate construction/system field documents
  retain annotation blocks, applicability denominators, patterns and affected IDs.
- Source recovery: complete for this evidence pass; 3,798 construction and 1,046
  HVAC dispositions, 76 residential HVAC equipment records, 195 water-heater
  records and one solar record. Unknown physics remains explicitly blocked.
- Pilot validation: four independent source-input examples pass schema, physical,
  inventory and provenance checks. They are not final ready consumer exports.
- Focused regression: 33 tests passed, including
  existing construction/HVAC checks. Source reexecution, review regeneration and
  pilot/receipt comparison each passed their `--check` command.
- Independent whole-change review: complete. Two Important findings were fixed
  and rechecked: recovered layer physics now receives model-specific range and
  finite-value checks; six secondary residential heaters retain their actual
  producing source method. Regression tests reproduce and reject both defects.
- Publication/site/CI: outside this pass.

## Recovery outcomes and limits

- Twelve glazing selector collisions resolve to identical physical recipes;
  source IDs/candidates remain distinct.
- Sixty-four ground rows recover their actual U-based model; 40 zero source
  targets remove insulation, rather than implying zero physical U.
- 166 material instances recover executed source/runtime surface defaults,
  preserving raw nulls and rejected setter behavior.
- All 41 residential fixtures have option/equipment recovery. Full enclosure
  layers, HVAC distribution, control/curve translation and engine performance
  remain incomplete.
- Construction dispositions: 2,982 source-resolved, 716 requiring consumer
  operands, 100 blocked (41 residential enclosures and 59 ground targets).
- All 1,046 HVAC and 196 DHW/solar records retain source translation blockers;
  nominal equipment/rating values do not certify simulation readiness.

The [ADR](../adr/0017-independent-energy-source-recovery.md) records concrete
remaining source actions. No new scientific fallback assumption was adopted.
