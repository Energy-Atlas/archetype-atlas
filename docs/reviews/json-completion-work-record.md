# Construction and system JSON work record

Plan: `docs/superpowers/plans/2026-10-12-json-completion.md`.
Branch: `feature/json-completion`. Started: 2026-10-12.

## Accepted execution scope

Implement the field reviews and source recovery, with Medium Office and
residential pilot validation. Construction, system and program contracts remain
independent; cross-contract mixing/assignment is a consumer concern and is not
implemented here. Systems include HVAC and DHW equipment, heater losses and solar.
That describes the completed recovery pass; the latest delivery scope and
all-variant readiness requirement are recorded below in ADR 0019.

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

## All-variant readiness and final system scope (2026-10-12)

The user requires "Every variant must be simulation-ready" and states "no need
of detailed dhw." [ADR 0019](../adr/0019-all-variant-readiness-and-hvac-delivery-scope.md)
records the revised acceptance gate: all 3,798 construction and 1,046 HVAC
variants need ready consumer exports. Ready pilots are intermediate gates;
blocked/raw variants cannot satisfy the completed release. No variants may be
dropped or unknown physics silently defaulted to claim completion.

Detailed DHW/solar evidence is retained, but ready detailed DHW models are no
longer a step 2 deliverable. Simplified draw-only energy remains in Program v4.
The prior counts of 196 blocked detailed DHW/solar source translations are
historical evidence coverage, not remaining step 2 release blockers. Construction
and HVAC readiness has not changed through this scope clarification; all source
and consumer-contract work identified above remains open. No implementation,
simulation, catalogue regeneration or site/CI run accompanies this documentation
update.

## Gap descriptions and annotation proposals (2026-10-12)

[The grouped gap review](construction-system-gap-proposals.md) provides detailed
descriptions, reasons, proposed fixes, closure checks and a comment area per gap
type. Per the user's instruction, no comment means agreement with that entry's
written proposal. It does not report fixes as implemented. Closer inspection
shows all 59 ground-target blockers are `Adiabatic GroundContactFloor` rows, and
133 packages contain 3,081 unknown scoped air-entry occurrences requiring
applicability/source review. These findings refine the proposals without changing
the frozen data or existing recovery disposition counts.

## Construction annotations and deferred systems (2026-10-13)

The user narrows the current phase to constructions. H and X entries have not
been reviewed; blank responses on those entries do not mean agreement. All
system work is deferred. This changes current execution order, not the ultimate
all-variant readiness target. The grouped review and plan now record that scope.

C04 permits simple/detailed glazing alternatives for one construction. C05 sets
ASHRAE climate-zone/group resolution without EPW-location records. C07 targets
delivered ACH while preserving pressure-test evidence and source conversion.
C08 requests discussion of an independent ground/basement axis; that architectural
choice remains open. No construction schema, physics or system implementation
is changed by recording these annotations.

## Above-ground construction milestone (2026-10-13)

The user chooses the second axis boundary: above-ground construction is separate
from combined ground/foundation/basement, including below-grade and
foundation-dependent interface assemblies. Ship above-ground construction at
100% first; ground and all systems are deferred. Infiltration stays in this
construction scope; mechanical outdoor/total-air requirements are deferred.
Constant ACH is selected, with reference conditions still under discussion.
See [ADR 0020](../adr/0020-above-ground-construction-first-release.md).

The narrowed baseline has 2,982 source-resolved above-ground/interior elements,
183 mixed packages and 41 residential enclosures to project; 592 explicitly
ground-contact elements are deferred. Source package selectors reveal missing
door, skylight and additional window dependencies in the existing exporter.
Therefore 3,206 projected existing identities are only a preliminary population,
not the full ready-release denominator. Expand and reconcile source dependency
closure before claiming 100% coverage. The commercial package infiltration
population is 906 unknown occurrences; its 3,624 mechanical-air occurrences are
outside this milestone. No physics/exporter changes or catalogue/site generation
were performed in this scope/coverage audit.

## Fixed catalogue ACH decision (2026-10-13)

The user selects fixed catalogue ACH per construction and climate zone. The
consumer does not recalculate it from actual building geometry. Store leakage
at package/enclosure level and reuse the selected value across geometry/zoning
variants. ADR 0020 records a proposed common reference enclosure separately from
this accepted decision; its geometry and climate factors are not approved yet.
Residential source fixtures retain different floor counts and
source CFA defaults, so using their geometry would incorporate building-form
differences into the catalogue constants. Source leakage bases, attached-unit
exterior fractions and commercial conversion still need recovery. No numeric
ACH, JSON change, source regeneration or site/CI build accompanies this record.

## Source archetype ACH reference geometry (2026-10-13)

The user chooses source archetype reference geometry, superseding the proposed
common one-storey reference enclosure. The catalogue constant remains fixed for
the consumer's geometry/zoning variants. Reference geometry and source defaults
are derivation evidence, not a dependency on program JSON or consumer geometry.

The existing residential recovery provides source CFA defaults, ceiling height,
floor count and aspect ratio for all 41 fixtures. Ceiling height is uniformly
8.0 ft; the preceding entry's original suggestion of varying ceiling heights was
incorrect and is corrected above. Infiltration height/volume and exposure still
require source-rule recovery. Ten `Any` and five `Office` commercial packages
require tracing reference-model mappings rather than choosing an arbitrary form.
Preserve distinct reference variants when their derived constants differ.
Climate factors and conversion details remain open. No scalar ACH generation,
JSON regeneration, system/ground implementation or site/CI build was performed.

## Source geometry/exposure recovery and climate proposals (2026-10-13)

Executed pinned source argument, geometry and leakage methods for all 41
residential fixtures. Recovered pressure-boundary height/volume, compartment
areas, exterior fraction, terrain/shielding and neighbor-distance evidence.
Sixteen attached fixtures have fractions 0.1818–0.89567; the 15-storey apartment
fixture retains one dwelling storey and an 8 ft infiltration height. Ground
adjacency dimensions were used only for the source pressure boundary; no ground
heat-transfer contract/model was delivered.

Executed geometry-only recovery for 129 commercial reference cases, with Medium
Office first. Retained space scopes, exterior areas, vertical extent, multipliers,
terrain/default flags and source lookup contexts. All 15 generic Any/Office sets
have reference matches. The 183-package receipt contains 182 source matches and
one evidence-backed uninstantiated SmallHotel 2019 GuestRoom scope; its whole-
building candidate remains unassigned. All-space volume is not asserted to be a
conditioned-volume denominator. No loads/HVAC/ground solver phases were run.

Added separate versioned geometry and proposal-only climate evidence under
`data/construction-inputs`. Executed 42 candidate source weather/shielding factors
from the pinned 2006 and 2013 climate maps. The grouped reference review provides
numeric factor alternatives, scientific interpretation, proposals and comment
areas. No proposed climate factor, annual-average convention or surrogate room
reference is treated as accepted by a blank comment.

Independent review found missing residential SmallHotel story overrides, lost
commercial terrain evidence and inadequate unmatched-package validation. All
three were fixed; their regression tests were observed failing first and then
passed. Eight focused tests pass, including a regression for floating-point
geometry-sum noise. Derived runtime geometry is canonicalized to nine significant
digits; literal source-table parameters remain unchanged. Focused replays cover
all 41 residential cases, five commercial pilots and all 42 climate candidates.
Frozen program, construction and system
releases remain unchanged; no catalogue/site generation or full CI was run.
