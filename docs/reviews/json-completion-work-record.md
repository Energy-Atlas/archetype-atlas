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

## Adopted construction fixed-ACH implementation (2026-10-14)

The user explicitly accepted F1, F2, F3 and G1: one pinned 2013 climate reference
map across vintages, residential source annual-average helper, commercial
system-off passive-envelope reference at 22°C, and the whole-SmallHotel leakage
benchmark for its uninstantiated generic GuestRoom construction set. ADR 0020
and the field review now record those answers. All H/X system work and ground
delivery remain deferred; blank annotations there remain unanswered.

Implemented a focused Python derivation builder and native commercial geometry
supplement, retaining source default airtightness/pressure, native area
normalization, terrain, source multipliers and whole enclosed volume. Commercial
constants average clipped hourly reference volume flow after centroid-height
wind/temperature corrections. The source enclosed volume includes interior and
plenum spaces and is not labelled conditioned volume. Preserve all reference
forms and source coefficient/surrogate fallbacks, not an average across forms.

The Medium Office / 90.1-2019 / 4A pilot yields 0.1396961316 ACH;
`source_building_101526` / 5A yields 0.671608067 ACH; the 15-storey-building
apartment fixture / 4C yields 0.1049942718 ACH using its dwelling-scale source
pressure boundary. Residential source labels 7AK/8AK retain their identity and
record both identical source-map forcing aliases, without inventing a moisture
class or new assembly applicability.

Independent review found missing runtime EPW checksum enforcement and a missing
Python dependency in the native supplement. Both were repaired and regression
tests observed failing first and then passing. A full native pass exposed two
LargeOffice basement inferred-volume replay differences of 0.00113%. Their
precise cause is unverified. The accepted geometry-v1 reference operands remain
unchanged, with a 0.002% replay tolerance that rejects larger disagreements.
The complete raw surface census has no nonhorizontal 5+ vertex surfaces;
future such inputs fail pending translated-engine centroid recovery.

This implementation does not deliver or publish the final above-ground
construction consumer contract. Residential assembly translation, omitted
door/skylight/window selector dependencies, the exporter/schema and the complete
readiness receipt remain. Program, ground, systems, frozen releases and site/CI
generation remain outside this focused work.

Validation completed: 19 focused unit tests; full 129-case native recovery;
four commercial native replays; all 41 residential direct-helper comparisons;
deterministic `python -m scripts.derive_construction_ach --check`; independent
review of final census/units/physical consistency and unchanged original inputs.
The output contains 41 residential constants, 2,709 commercial reference/climate
benchmarks and 183 resolved package mappings. Original geometry/climate candidate
receipts and frozen construction definitions remain unchanged.

## Complete above-ground construction consumer export (2026-10-14)

Recovered all 183 pinned commercial source sets and all 41 residential fixtures
using construction-only native execution. Commercial closure retains 2,982 old
elements and adds 1,456 omitted dependencies. Residential recovery yields 430
recipes (283 opaque, 147 simple glazing), retaining 839 native occurrences and
857 source assignments. Its 210 foundation/ground elements remain deferred; no
systems or ground solver phases were run.

The independent construction v1.0.0 schema/exporter freezes 4,868 assemblies,
183 packages and 41 enclosures: 5,092/5,092 ready IDs with all 3,206 eligible
baseline IDs preserved. Central tables contain 858 material and 7,972 evidence
resources. Medium Office and residential standalone examples validate before
the full catalogue; all 4,751 declared package/climate/reference contexts
resolve. The 592 frozen ground IDs and all commercial ground selectors are
explicitly deferred. Older DOE source thermal rows do not cover 0A/0B in 56
packages; unsupported contexts stay explicit instead of receiving guessed data.

Independent review identified incomplete readiness-reference checks and empty
misleading default labels. Seven malformed-pilot mutation cases were observed
failing their rejection tests, then fixed through census/order/context/evidence
validation. Default labels were removed; per-property source null/default
evidence remains. Follow-up review found no remaining actionable issues.

Both fresh native recovery checks passed; 52 focused unit tests and exact-byte
export reproducibility checks pass. The release contains schema, two examples,
completeness receipt, checksum manifest and upstream license notices. ADR 0021
and the contract document source-native target/setter limitations, roof pitch,
internal-mass scaling and constant curtain incident-solar multipliers. This
freezes ready inputs on the feature branch; it does not claim full simulation
result parity or site publication. Program, frozen definitions, ground, systems
and site/CI generation remain unchanged.

## Unified construction-set migration for review (2026-10-14)

The user accepted one source/context-selected construction set containing all
component types, with Program-compatible header/source metadata. Catalogue
selection resolves climate/reference; BEMGen owns BEM assignment and IDF
translation. Generic required_bindings and deferred_scope fields are removed
from the consumer contract. Component targets, assignment scopes, source
conditions and geometry conventions are schema controlled.

Implemented the v2 schema, selected exporter, compact 224-definition context
index and complete Medium Office/residential examples. Source-selected Plenum
overrides are embedded in the building set; compatibility-only Office lookups
remain evidence. Residential parent-wall adjacency, pitch, internal-mass/
interstory scaling and shading variants survive. Frozen v1 source physics,
material/assembly IDs and selected fixed ACH remain unchanged.

Fresh review found a legitimate Attic floor using a legacy roof role and missing
guards against dropped geometry conventions. Regression tests were observed
failing and repaired. Scoped-condition/root consistency was also strengthened
because mislabeling affects BEMGen assignment. The review gate remains pending
human comments; all-context release validation, source/program regeneration,
site/CI, publication, translator, ground and systems remain outside this phase.
See [the review entry](construction-set-v2-review.md).

Focused final checks: 26 tests pass; all four review artifact bytes reproduce;
review manifest verifies three artifact and eighteen input hashes. Frozen v1
and program files have no changes. Artifacts are committed locally for review,
with no site integration, CI, push or publication in this phase.

## Accepted construction v2 migration and freeze (2026-10-14)

The user accepted both unified examples and authorized acceptance recording,
complete migration validation and the v2.0.0 freeze. Site integration/publication
remains the next phase. The existing `feature/json-completion` checkout is used;
frozen v1, program artifacts, native recovery, ground and systems are unchanged.

The normalized release preserves 224 source definitions, all 4,751 commercial
and 47 residential supported climate/reference contexts, 4,868 assemblies and
858 materials. Evidence contains all 7,972 original records plus one pinned SDK
inheritance proof and 41 explicit residential adjacency-context proofs. All
17,564 distinct source-definition/selector/assembly candidate choices are checked.
Space and all 15 recovered story override queries are preserved; original story
IDs and source order remain explicit. The source hierarchy uses checksum-pinned
OpenStudio 3.10 primary documentation rather than a guessed precedence.

The completeness denominator is 5,092 source identities (definitions plus
assemblies). Of the assemblies, 3,429 are context-supported candidates/recipes;
1,439 independent source-table recipes are retained without invented prototype
mapping. They receive physical, layer/material, provenance and schema checks as
well as exact source equality. Their ready status describes complete assembly
physics, not unreported building applicability.

Fresh independent technical review found three important issues. Regression
tests first reproduced receipt/assignment contradictions, direct and repeated-
story variant hydration differences, and the missing v1 catalogue checksum gate.
Repairs enforce correspondence, replace variants in source order, retain direct
selector semantics, and verify immutable v1 bytes before choosing the baseline.
Resource-graph checks now explicitly cover independent source-table recipes.

Focused export/release tests, including the original v1 exporter checks: 37 pass.
Full validation and exact-byte reproduction are recorded in the frozen
[completeness receipt](../../data/construction-releases/v2.0.0/completeness.json)
and [manifest](../../data/construction-releases/v2.0.0/manifest.json).
The release includes shared tables, both schemas, index, complete examples,
README, locked source retrieval and upstream license notices. Frozen v2 hydration
reproduces each default standalone consumer document. No native/program/site/CI
generation or production deployment is part of this freeze.

The final reproduction input guard caught a working-tree schema reset to the
exact older HEAD version. Staged/frozen schema bytes remained intact. Preserved
the reset in the ignored build folder, restored the validated schema and repeated
reproduction before committing. No stale schema was accepted into the freeze.
The repeated full `--check` passed with stable inputs and exact-byte equality of
all release artifacts. The frozen Medium Office CLI export/check also passed.
Staged outputs and generation inputs match the manifest, and all upstream notices
match v1 bytes. Staged diff inspection and the security audit pass before the
local freeze commit. Site integration and protected-main publication remain open.

## Construction v2 local site integration — 2026-10-14

At the user's instruction, integrated the frozen v2 release into the existing
site on `feature/json-completion`, based on `23c5f1d`. The construction finder now
contains 224 source sets and 4,798 supported climate/reference contexts. Pages
copy self-contained selected JSON v2 and preserve raw source JSON separately.
All 4,868 assembly, 858 material and 8,014 evidence resources have linked pages;
the 1,439 source-table-only recipes retain explicit unreported prototype mapping.
Contract, schemas, examples, source lock and license notices accompany delivery.
BEMGen translation, ground and system completion remain deferred.

The existing local generated tree contained Program JSON v2. Refreshed its program
presentation from unchanged v3 inputs, without native/research recovery or program
artifact generation. Local reuse now fingerprints every exporter operand and
shared semantic dependency. Independent review exposed missing cache operands
and inadequate page/evidence binding checks; failing regressions preceded repairs.
Delivery verification compares complete packet closures with the locked freeze
and binds actual page JSON/context controls and resource routes to the report.
Verification avoids retaining all repeated profile packets in memory.

Validation: 30 focused Python presentation/delivery tests, seven existing object
browser tests and two Node selection tests pass. All generated construction
packets/resources match the freeze. The strict local MkDocs build and full site
checker pass links, fragments, assets, size limits, retirement, program exports
and frozen construction delivery. Eight real-browser construction checks cover
exact Medium Office/residential copies, explicit selection errors, corrupted and
missing resources, clipboard fallback, mobile light/dark and no-JavaScript lists.
Screenshots were inspected; receipts and output stay under ignored `build/`.

The source JSON, frozen releases and schemas remain unchanged. Staged inspection
and security audit precede a reversible local commit. No push, GitHub workflow,
PR, Pages deployment or production publication is part of this task. See the
[local integration plan](../superpowers/plans/2026-10-14-construction-site-integration.md).
