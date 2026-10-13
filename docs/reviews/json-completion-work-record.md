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

## Initial draw-only program DHW follow-up (2026-10-12)

The user's authorized follow-up implements [ADR 0018](../adr/0018-draw-only-program-water-heating-energy.md)
as opt-in [Program JSON 4](../program-json-v4-contract.md). It does not make the
detailed equipment/system contracts ready or complete remaining task 2 work.

- All 154 commercial main/booster/laundry channels recover numeric conversion
  efficiency by executing pinned source factory/lookup methods. All 41 existing
  residential heater conversions remain available; 40 fixtures enter the new
  representation after the explicit solar skip.
- Four complete program pilots validate local, residential, shared-service and
  mixture demand migration. The source census verifies all heater joins and
  source water targets without rebuilding the full v3 program library.
- Three SmallHotel source targets exceed main supply temperature and remain
  blocked at this initial checkpoint, including their dependent mixtures. The contract contains an annotated
  proposal to cap actual delivery while preserving the requested target and unmet
  temperature. No such policy is applied pending the user's decision.
- The coverage artifact separately lists 59 independent source services without
  an existing program attachment. Their conversion data is recovered; allocation
  is not guessed or copied to every program.
- The final reviewer reproduced an Important ownership gap. Three failing
  regressions established that invented duplicate shared demands, unrelated
  service reassignment and omitted water demands were accepted. Validation now
  verifies the complete original v3 water inventory, ownership, assignments and
  schedules. Those regressions pass after the fix.
- Final verification: 31 focused/regression tests passed, source conversion
  reexecution passed `--check`, and four-pilot/coverage reproduction passed
  `--check`. No unexpected unresolved source join was found.
- Standby losses, heater auxiliaries and pilot consumption stay excluded. No
  density, specific heat, fuel or efficiency default is introduced. Full release,
  site generation and lengthy CI remain outside this pass.

## Approved SmallHotel delivery cap (2026-10-12)

The user accepted the source outlet cap and unmet-target reporting. The three
main-loop laundry draws preserve their 82.222°C requested schedules, original
volume and source fuel/conversion; simplified supply uses the 60°C main outlet.
An explicit policy with pinned EnergyPlus evidence follows each demand into
its 12 dependent mixtures. Unmet thermal demand is reported separately and adds
no fuel consumption. Standby, auxiliaries, pilot consumption and solar stay
outside scope. No source-loop reassignment or independent laundry-demand copying.

Focused coverage now checks all 217 commercial service recipes, all 15 affected
complete exports and six tracked pilots. The 59 unattached independent source
services still require consumer assignment. Detailed construction/HVAC readiness
and catalogue publication remain separate work.

Verification: 34 focused water/aggregation/completeness tests passed. Six-pilot
and 15-affected-export reproduction passed `validate_program_water_heating
--check`; the local pinned WaterUse source SHA-256 matches the evidence lock.
No full catalogue/site build, EnergyPlus simulation or lengthy CI was run.
Independent read-only review found no remaining issues; it reproduced the focused
artifacts, verified all 10 locked source files and checked 48 physical edge cases.
