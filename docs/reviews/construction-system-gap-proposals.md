# Construction and HVAC gaps: descriptions and proposals

Date: 2026-10-12. Review scope updated: 2026-10-13. Branch: `feature/json-completion`.
Evidence snapshot: commit `b131a20`, frozen definitions `v0.1.1`, and the
construction/system recovery inputs. This document proposes fixes; it does not
claim they have been implemented.

## How to review

There is one entry per gap type, grouping fields that need the same recovery or
translation. Each entry states the gap, its reason, a concrete proposal and the
check that would close it. The affected-ID inventories remain in the linked
machine-readable census; this is not a separate entry for every catalogue row.

**Current phase: above-ground constructions only.** The combined foundation,
ground and basement axis (including its assemblies) is deferred. Foundation-
dependent floor-over-foundation and rim-joist assemblies are deferred with it.
Infiltration stays in construction; mechanical outdoor/total-air requirements
are deferred. Constant ACH is selected, but its reference conditions remain open.
See [ADR 0020](../adr/0020-above-ground-construction-first-release.md).
The user has not reviewed
H or X entries; all system work is deferred and blank H/X comments do not mean
agreement. For the original reviewed C proposals, the earlier blank-comment
agreement rule remains applicable unless a comment raises a question or changes
the proposal. C02/C08 ground work is now deferred and the user selected the second
boundary: below-grade assemblies belong to combined foundation/ground. New architecture
proposals are discussion items until decided, not accepted through an empty box.
Write corrections, alternatives or constraints in the relevant **Your comments**
area. Comments override the proposal for that entry and equivalent cases. Empty
areas never authorize unwritten numerical fallbacks or scope changes. Preserve
the user's comment text when updating this document.

Construction annotations received on 2026-10-13:

- C04: both simple and detailed glazing representations may be supplied for one
  construction if needed; they are alternatives, not two additive assignments.
- C05: ASHRAE climate zones/groups are the intended catalogue resolution. Do not
  distinguish or record EPW locations in construction applicability. Simulation
  weather inputs remain external to the catalogue.
- C07: the ultimate delivered infiltration output should be constant ACH.
  Retain ACH50 and its pressure reference as source evidence; the reference
  conditions for conversion are still being discussed.
- C08: the second boundary is selected. Above-ground construction is separate
  from combined foundation/ground/basement, which owns below-grade and
  foundation-dependent interface assemblies. Ground work is deferred.

Existing decisions remain binding: every construction and HVAC variant must be
simulation-ready before step 2 closes; detailed DHW models are not required;
program, construction and system JSON remain separate. Geometry, weather,
calendar, serving assignment and sizing are consumer inputs. Missing source
physics cannot be renamed as a consumer input to claim readiness. The solar
DHW skip does not exempt its construction or HVAC variant.

## Coverage and interpretation

| Population | Recorded recovery status | What it establishes |
| --- | --- | --- |
| 3,798 constructions | 2,982 resolved; 716 require bindings; 100 blocked | Source-recovery dispositions, not complete consumer exports |
| 100 blocked constructions | 41 residential enclosure translations; 59 ground classification/target cases | The explicit blockers currently detected by the recovery script |
| 1,046 HVAC systems | All blocked: 993 general commercial recipes, 12 Medium Office PVAV recipes, 41 residential fixtures | Each system retains at least one source/translation gap |
| Construction package air entries | 3,081 unknown entries in 133 of 183 packages | Applicability and source absence must be checked; not 3,081 proven missing physical demands |
| Detailed DHW evidence | 195 heaters and one solar record retained | Outside the ready system delivery requirement |

Counts from different entries overlap. Component/field occurrences are not
additional system records. The recovery script's 100 construction blockers are
not an exhaustive readiness certificate: scoped air entries and final contract
translation still need review. Package air counts below were inspected directly
in the frozen construction table, rather than inferred from the older field
census.

Sources: [construction recovery](../../data/construction-inputs/source-v1.json),
[system recovery](../../data/system-inputs/source-v1.json),
[frozen construction table](../../data/definition-releases/v0.1.1/constructions.json),
[field census](energy-json-field-coverage.json),
[validation receipt](energy-source-recovery-validation.json),
[construction field review](construction-json-field-review.md),
[system field review](system-json-field-review.md), and
[accepted scope](../adr/0019-all-variant-readiness-and-hvac-delivery-scope.md).
The older system census includes detailed DHW gaps that are no longer release
blockers; commercial DHW conversion recovery also supersedes its efficiency gap.

## C01 — Residential ordered assemblies and thermal mass

**Gap description and pattern:** All 41 residential enclosure records have
selected source options, including nominal insulation, glazing and leakage,
but no complete translation into ordered wall/roof/floor materials. The fixtures
include 22 detached homes, five attached homes, three manufactured homes, six
low-rise multifamily, three 2–4-unit multifamily, one midrise and one high-rise.
Affected fields include `layers`, `assembly_layers_and_thermal_mass` and
`geometry_dependent_enclosure_translation`.

**Narrowed milestone:** Recover their above-ground walls, roofs/ceilings, doors,
windows and ordinary floor/partition assemblies. Foundation walls, slabs,
floor-over-foundation and rim-joist details are deferred with the ground axis.

**Reason:** An insulation R-value or assembly U-value does not determine layer
order, framing paths, thickness, density or heat capacity. ResStock expands
selected options first and translates them into engine constructions later,
using surface type and geometry. Recovery currently stops before that translation.

**Proposal to fix:** Trace the pinned HPXML-to-OpenStudio enclosure construction
routines for each selected source option. Recover ordered layers and any
parallel-path/effective-layer calculation, with material operands and source
default evidence. Export geometry-dependent construction recipes with explicit
surface type, dimensions, adjacency and framing operands where the upstream
calculation actually needs them. Preserve separate stock fixtures; do not replace
them with a generic wall having the same R-value. Use a minimal geometry harness
only to compare source calculations, not as delivered building geometry.

**Closure check:** Reproduce source U/R and thermal-mass calculations for the
residential pilot, then each distinct option/assembly branch; validate layer
order, units, finite physical values and every required geometry operand. All
41 variants must export with complete source physics.

**Your comments (blank = agreement):**

<!-- comments:C01:begin -->

<!-- comments:C01:end -->

## C02 — The 59 misclassified or unresolved ground cases

**Current status:** Deferred with all ground/foundation work. These cases do not
block the above-ground construction milestone.

**Gap description and pattern:** Every one of the 59 `ground_factor_target`
cases is named **`Adiabatic GroundContactFloor`**. Their frozen rows are labeled
`C-factor underground wall`, although their role is floor and the source F/C/U
targets are null. They already retain an `Adiabatic Material` layer with a
reported resistance of 9,999 h·ft²·°F/Btu. This is a specific shared pattern,
not 59 unrelated missing ground properties.

**Reason:** `construction_definitions.py` chooses F-factor when an F target is
present and otherwise labels the row C-factor. That fallback misclassifies
targetless ground-floor rows. The upstream constructor also has different
branches with and without a surface argument; the name alone does not prove
that a consuming surface has an adiabatic boundary.

**Proposal to fix:** Follow the pinned `Standard.model_add_construction` caller
and constructor branches for these source packages. Recover the actual object
type, layer recipe and boundary instruction. Correct the model classification
when the executed source establishes a regular layered construction or explicit
adiabatic boundary; then mark F/C operands inapplicable for that model. Preserve
the finite reported material resistance. Do not invent C/F values, turn a null
target into zero U, or infer zero heat flow solely from the word "Adiabatic".
Compare both relevant constructor call forms where package and surface calls
differ, and document which is the supported source recipe.

**Closure check:** A regression must reject a floor labeled as a C-factor wall
without supporting source physics. Execute the relevant source branches, retain
all 59 identities, and verify each corrected model has complete applicable
operands. Keep the original frozen labels as historical evidence.

Evidence: frozen `conditioning_category`, material/target provenance;
[`construction_definitions.py`](../../scripts/construction_definitions.py)
and the locked `Standards.Model.rb#Standard.model_add_construction` source.

**Your comments (blank = agreement):**

<!-- comments:C02:begin -->

<!-- comments:C02:end -->

## C03 — Applying commercial layer adjustments and film conventions

**Gap description and pattern:** Layered commercial constructions may have a
target U-value, a source base assembly and an insulation adjustment. The final
consumer export must combine them correctly. The older field census lists 818
U summaries for source recovery/derivation; that is not 818 unresolved source
records. The 64 recovered U-based ground cases and 166 material-default cases
already have additional evidence to apply.

**Reason:** Source target values are distinct from achieved assembly values.
Film coefficients depend on the source convention and surface role. A zero
source target can remove insulation; it does not mean zero heat transfer.
Defaults retained or rejected by the SDK can differ from the input setter value.

**Proposal to fix:** Reuse the recovered source adjustments/defaults, then
calculate achieved U from the adjusted layers with the exact source film
convention. Keep target and achieved values separately labeled. Preserve
massless and air-gap resistance models without fabricated density or heat
capacity. Retain the four existing generic construction assumptions within
their previously accepted scope; do not extend them to exterior assemblies.

**Closure check:** Compare the Medium Office element closure with pinned source
calculations; test source films, layer mass/order, insulation removal and SDK
setter outcomes. Reject missing operands required by the declared material model.

**Your comments (blank = agreement):**

<!-- comments:C03:begin -->

<!-- comments:C03:end -->

## C04 — Glazing summaries, optical layers and selector ambiguity

**Gap description and pattern:** The census records 106 absent SHGC summaries
and 256 absent visible-transmittance summaries among 504 applicable glazing
occurrences. Detailed optical layers can already be complete even when a scalar
assembly summary is absent. Twelve selector collisions have been resolved as
identical physical recipes while retaining their distinct source contexts.

**Reason:** Simple glazing uses aggregate U/SHGC/VT operands; detailed glazing
uses pane/gas optical and thermal properties. Applying one requirement list to
both models creates false gaps. Matching names alone can also select the wrong
source construction.

**Proposal to fix:** Define separate simple and detailed glazing requirements.
For simple glazing, recover source aggregate values and documented constructor
defaults. For detailed glazing, export the complete ordered optical/gas layers;
derive a scalar summary only through a pinned calculation with explicit rating
conditions, and make that summary optional for execution when layers suffice.
Resolve selectors by source context, retaining all candidate IDs and rejecting
different physical recipes with ambiguous selection.

**Closure check:** Both glazing models pass their own requirements; missing
optional summaries do not block valid detailed-layer exports. Test ambiguous
physical matches, distinct source contexts and gas/optical property applicability.

**Your comments (blank = agreement):**

<!-- comments:C04:begin -->
yes and we may have both glazing versions for 1 construction if needed
<!-- comments:C04:end -->

## C05 — Construction packages and climate/element selection

**Gap description and pattern:** All 183 packages need explicit selection by
climate and element role. A package is not itself a homogeneous material, and
source climate groups are not necessarily individual EPW locations.

**Reason:** Packages reference alternative exterior, interior, ground and glazing
elements, sometimes with program-scoped air requirements. Existing raw objects
do not provide a completed ready consumer contract for those selections.

**Proposal to fix:** Keep separate element and package representations. Export
the package's source selectors and complete referenced element dependencies.
Require the consumer to supply surface roles and compatible climate context;
resolve source selectors deterministically or fail on ambiguity. Preserve stock
versus code/template distinctions. Do not add cross-contract mixing/matching or
silently substitute the closest climate/template.

**Closure check:** Validate every package selector against its source table and
dependency closure. Test boundary climates, unsupported context, ambiguous
matches and interior/ground roles. All 183 packages must have an executable
selection rule with no missing referenced source physics.

**Your comments (blank = agreement):**

<!-- comments:C05:begin -->
we can think climate group (if represeneted as ashrae cz) is the resolution we aim to get. epw locations are understood as proxies of these climates. if we see e.g. 2 epw locations within the same climate, we regard both being the same climate zone and pay no attention to the epw locations. in fact, we should not pay attention to or record epw locations.
<!-- comments:C05:end -->

## C06 — Unknown scoped infiltration and air-exchange entries

**Narrowed milestone:** Keep infiltration only: 906 unknown commercial package
occurrences. The 3,624 outdoor/total-air occurrences are deferred with systems,
with their original evidence retained and no zero assumption.

**Gap description and pattern:** The frozen package table contains 4,530 air
entries; 3,081 are `unknown`, across 133 packages and 768 distinct source program
IDs. Unknown occurrences comprise 906 infiltration-per-area entries, 864 outdoor
air ACH entries, 858 minimum-total-ACH entries, 115 outdoor-air-per-area entries
and 338 outdoor-air-per-person entries. These are repeated field occurrences;
the same program can appear in several packages.

**Reason:** Alternate air-rate bases are stored together, and null values may
mean an unused basis, a source absence or an actual extraction gap. The existing
recovery readiness classifier does not resolve these package air entries.
Program JSON's exclusion of air requirements does not establish zero airflow.

**Proposal to fix:** Inspect every unique source program's active airflow helper
and applicability before assigning status. Recover active infiltration and
outdoor/total-air rates, basis, schedule and source combination rule. For a
demonstrably unused basis, record inapplicability/absence with source evidence
rather than an executable null or guessed zero. Preserve scoped requirements
within construction packages; HVAC supplies the associated ventilation control
semantics. Keep indoor total supply separate from outdoor air, and specify one
consumer accounting path so rates are not added twice. Use source rules for
combining area/person/ACH minima; do not assume every basis should simply be summed.

**Closure check:** Reconcile all 3,081 unknown occurrences to recoveries or
source-proven applicability dispositions. Test occupied/support spaces, multiple
rate bases, schedule availability, area/person/volume scaling and duplicate
instantiation. Active air requirements must be complete before package readiness.

**Your comments (blank = agreement):**

<!-- comments:C06:begin -->

<!-- comments:C06:end -->

## C07 — Residential pressure-test leakage to natural infiltration

**Current decision:** Constant natural ACH is required, not ACH(t). Reference
geometry and climate-factor conditions remain open. The pinned source's
annual-average scalar helper is a candidate conversion; this entry's earlier
weather-dependent model proposal does not constitute acceptance of hourly output.

**Gap description and pattern:** All 41 residential enclosure records preserve
their pressure-test leakage, including the 50 Pa reference. A usable infiltration
model also needs the source pressure/weather/geometry transformation.

**Reason:** ACH50 describes a pressure test, not natural air changes under the
simulation weather. A fixed ACH50-to-ACH divisor would introduce a new physical
assumption and can hide differences in height, shielding and leakage distribution.

**Proposal to fix:** Preserve leakage value, SI rate units and test pressure;
recover the pinned residential airflow algorithm and source default operands.
Expose actual weather, height, volume, shielding and leakage-distribution operands
required by that algorithm, with documented source defaults where they exist.
Keep mechanical ventilation separate. Do not generate household geometry or
substitute a common natural-infiltration rate.

**Closure check:** Verify the pilot's pressure normalization and source airflow
calculation under explicit test weather/geometry. Test units, reference pressure
and required inputs; apply the complete source model to all 41 fixtures.

**Your comments (blank = agreement):**

<!-- comments:C07:begin -->
ok. the ultimate goal is to ship ach
<!-- comments:C07:end -->

## C08 — Ground and surface geometry bindings

**Current status:** Ground bindings and foundation-dependent interface assemblies
are deferred. Above-ground construction must ship independently at 100% coverage.

**Gap description and pattern:** 716 construction records currently require
consumer operands without an identified source blocker. The field census lists
415 area/perimeter occurrences and 113 wall-height occurrences, as well as
package selectors and ordinary ground-boundary/geometry requirements. These
counts overlap and may change when C02's model classification is corrected.

**Reason:** F-factor floors, C-factor walls and ordinary layered ground surfaces
use different physical models. Assemblies cannot determine the building's soil
boundary, slab perimeter, surface dimensions or adjacency.

**Proposal to fix:** Define model-specific bindings: F-factor floor geometry,
C-factor wall geometry, and ordinary surface/ground boundary operands separately.
Require only the inputs used by the selected model. Retain source units and
formula meanings in metadata; reject contradictory role/model combinations.
Source soil/ground-temperature algorithms must be specified rather than treating
an unknown algorithm as a consumer numerical input. The consumer supplies actual
geometry and weather without the Atlas choosing a reference building.

**Closure check:** Test dimensional consistency and missing/invalid operands for
each model. Confirm irrelevant F/C bindings disappear only with source-supported
reclassification. Explicit consumer geometry must not count as missing Atlas data.

**Your comments (blank = agreement):**

<!-- comments:C08:begin -->
question - what value / clarity would it bring if we think of ground / basement as a separate axes from construction, systems, programs (loads & schedules)?
<!-- comments:C08:end -->

### C08 discussion — Separating foundation and ground conditions

Status: historical discussion. The user subsequently selected the second
boundary: construction covers above-ground fabric and combined foundation/ground
owns below-grade assemblies. See ADR 0020. Ground and systems are deferred.

**Recommendation:** Treat foundation/ground conditions as a separately selectable
axis, while keeping the compatible assembly and calculation method explicit.
Start with a supporting ground/foundation profile referenced alongside the
construction. A new primary catalogue kind/page is not needed to discuss or
establish this separation.

| Part | Owns | What remains external |
| --- | --- | --- |
| Construction assembly | Ordered slab/wall materials, insulation, thermal mass; source F/C performance where applicable | Actual surface assignment |
| Foundation configuration | Slab-on-grade, basement or crawlspace arrangement; applicable contact/insulation-placement rules | Actual area, perimeter, burial depth, exposed wall portions and adjacency from geometry |
| Ground boundary profile | Heat-transfer method, soil operands where the method uses them, ground-temperature/deep-boundary policy | Required simulation forcing and actual geometry |
| Basement zone conditioning | Whether a modeled basement is heated/cooled and its zone controls | Program and eventual system assignment; outside this ground-profile discussion |

**Value:** We can distinguish a change in insulation/materials from a change in
soil coupling or foundation layout. Ground defaults no longer hide inside each
construction, and the same compatible assembly can be reused without duplicating
its materials for every soil profile. The 59 misleading C-factor labels become
three separately checked questions: what is the assembly, which surface role
applies, and what is the actual boundary/calculation method?

**Basement caution:** An unconditioned basement is a thermal space, not a soil
property. A floor over that basement has an interzone connection; the basement
slab and relevant walls have ground connections. Omitting the basement and
applying a direct ground boundary to the floor above changes the model. Any such
simplification needs its own declared assumption.

**Limits:** The axes are separable for selection, but not freely interchangeable.
F-factor is perimeter-based floor performance; C-factor is wall conductance that
excludes soil and air films. Their source method/geometry must remain attached.
Kiva instead couples surface constructions with a foundation/soil model. We must
not add independent soil effects to an F/C approximation as if those methods were
equivalent, or combine a factor-defined surface with arbitrary detailed layers.
See the EnergyPlus 25.1
[F/C construction reference](https://bigladdersoftware.com/epx/docs/25-1/input-output-reference/group-surface-construction-elements.html#constructions---modeling-underground-walls-and-ground-floors-defined-with-c-and-f-factors-for-building-energy-code-compliance)
and [Kiva foundation reference](https://bigladdersoftware.com/epx/docs/25-1/input-output-reference/group-advanced-surface-concepts.html#foundationkiva).

**Climate treatment:** Use ASHRAE climate zones/groups as agreed and do not record
EPW locations. Climate-zone membership does not by itself supply soil thermal
properties or a unique ground-temperature history. Keep the required source
algorithm or simulation forcing explicit instead of inventing a zone-wide constant.

**Open architectural choice:** Adopt the separate supporting profile while
preserving source-specific layered-ground/F/C/Kiva methods, or retain all these
fields within each construction. The separate-profile approach is recommended;
a universal ground solver is not proposed or assumed here.

## C09 — Missing above-ground source selector dependencies

**Gap description and pattern:** The 183 frozen packages retain additional source
selectors that the existing package exporter does not link into `elements`:
exterior doors and overhead doors (161 package occurrences each), glass doors
(143), skylights (109), operable windows (161), and interior doors/fixed/operable
windows (161 each). These counts overlap and are not new element totals.

**Reason:** The current `build_constructions` package loop covers walls, roofs,
floors, fixed exterior windows and ground-contact roles, plus interior walls,
floors and ceilings. The other source selectors survive in `source_set` but do
not have a completed dependency closure. The old 2,982 above-ground/interior
element count therefore cannot by itself establish complete source coverage.

**Proposal to fix:** Trace every populated above-ground selector to its exact
source construction/property row and ordered materials. Recover supporting
elements with stable source-derived IDs, climate/template applicability and full
evidence; distinguish applicability/absence from missing extraction. Expand the
above-ground package closure and validate every selector. Reconcile additional
IDs before freezing the first release denominator, without merging stock variants.

**Closure check:** Every populated above-ground source selector has a valid ready
dependency or a source-proven inapplicability disposition. Tests reproduce omitted
door/skylight/operable-window branches and reject dangling/ambiguous selections.
The final completeness receipt includes all newly recovered eligible elements.

**Your comments:**

<!-- comments:C09:begin -->

<!-- comments:C09:end -->

## H01 — Commercial component recipes and internal topology

**Gap description and pattern:** 993 general commercial systems retain
`source_component_recipe` blockers. They include PSZ-AC, PTAC, UnitHeater, VAV,
SAC, PVAV, DC, CAV and DOAS Cold Supply. Every one of the 1,046 frozen HVAC rows
has an empty connection list; 94 also have an empty component list. Empty
extracted lists do not prove that the source has no equipment.

**Reason:** The initial extraction retained system descriptors and role/rating
resources, not the full executed source factory and caller relationships.
Auxiliary roles can describe dependencies or ancillary behavior rather than
separate heating/cooling devices.

**Proposal to fix:** Trace each pinned building/template caller into its actual
HVAC factory, equipment helpers and loop/terminal branches. Export an explicit
component graph with conditional source construction rules for zone-dependent
instantiation. Define internal air/plant connections, fuels and terminal roles;
leave only the external zone serving assignment to the consumer. Give the 94
empty-component rows a source-proven disposition. Do not replace descriptors
with ideal loads or treat ancillary labels as complete executable equipment.

**Closure check:** Compare instantiated pilot components/connections with the
pinned source model and expand by distinct factory branch. Test absent equipment,
multiple serving zones, duplicate branches and orphan connections. Preserve all
source system IDs rather than merging equivalent-looking stock variants.

**Your comments (unreviewed; blank does not mean agreement):**

<!-- comments:H01:begin -->

<!-- comments:H01:end -->

## H02 — Medium Office PVAV helper and template adjustments

**Gap description and pattern:** Twelve Medium Office PVAV rows have a recovered
recipe: VAV-default fan helper, gas main heating, two-speed DX cooling and electric
reheat terminals. Factory performance, template adjustments and curve assignments
remain unresolved. This group is distinct from the 30 PVAV rows in H01.

**Reason:** Knowing the helper names does not expose their setter values or
subsequent standards adjustments. The actual caller skips hot-water-loop creation
and does not forward its heating-type label; unrelated `vav_*` fields cannot
therefore be imported as PVAV settings.

**Proposal to fix:** Make this the first HVAC pilot. Pin and execute the exact
fan, gas-coil, two-speed DX and terminal helpers, then the applicable template
adjustments in source order. Record constructor defaults, rejected setters,
capacity predicates, resulting curves and controls. Retain gas/DX/electric-reheat
topology unless the executed source establishes a different branch.

**Closure check:** Compare the complete pilot graph and performance operands to
the source factory output, then verify all 12 rows. Do not claim readiness from
the already recovered helper-name recipe alone.

**Your comments (unreviewed; blank does not mean agreement):**

<!-- comments:H02:begin -->

<!-- comments:H02:end -->

## H03 — Performance selection, rating metrics and fuel identity

**Gap description and pattern:** The frozen field census has 911 heating and
794 cooling performance occurrences, plus 707 conditional rating-rule components
requiring subtype/rating-condition resolution. Top-level heating fuel is unknown
for 1,005 commercial rows. These are overlapping field populations, not extra
system counts.

**Reason:** Standards tables depend on equipment subtype, capacity band, date,
template and rating conditions. A generic `efficiency_or_cop` field cannot safely
represent burner efficiency, instantaneous COP and seasonal/integrated ratings.
Descriptor heating labels do not necessarily equal the executed coil fuel.

**Proposal to fix:** Recover equipment subtype and actual fuel from the source
factory, then preserve the full rating-selection rule with explicit predicates,
units, metric and transformation. Execute the upstream rating-to-model conversion
where required, including supporting fan/curve assumptions. Keep capacity and
rating date as explicit consumer operands when the source rule depends on them;
do not pick a representative band or current date. Do not convert AFUE/SEER/HSPF
into constant burner efficiency/COP by renaming the number.

**Closure check:** Test capacity/date boundaries, all supported metrics, unmatched
or overlapping rules and fuel preservation. Compare source-selected model inputs
at representative points in each rule branch. Missing rules still block readiness.

**Your comments (unreviewed; blank does not mean agreement):**

<!-- comments:H03:begin -->

<!-- comments:H03:end -->

## H04 — Curve assignments and valid operating domains

**Gap description and pattern:** 726 component occurrences need curve
assignments. Some curve resources already exist, but their association with the
actual source equipment is unresolved; residential performance also needs its
source-derived operating functions.

**Reason:** Curve names/coefficient tables are supporting resources, not proof
of assignment. Temperature, flow-fraction, part-load and defrost functions have
different inputs, domains, normalization and clamping behavior.

**Proposal to fix:** Recover each equipment setter's actual curve reference and
embed the required curve definitions: type, coefficients, independent-variable
units, domains, output limits and source clamping behavior. Preserve stage/speed
associations. Where the source derives curves from a seasonal rating, retain that
derivation and the source defaults used. No all-ones fallback curve or arbitrary
nearest-name match is proposed.

**Closure check:** Compare source/reference curve evaluations at rating points
and domain boundaries; test assignments, unit conversion, stage/speed identity
and out-of-domain behavior. Reject missing or dangling active curve references.

**Your comments (unreviewed; blank does not mean agreement):**

<!-- comments:H04:begin -->

<!-- comments:H04:end -->

## H05 — Fan performance and electrical accounting

**Gap description and pattern:** 869 frozen fan-component occurrences have
unresolved efficiency and pressure rise. Residential fan operands also need the
upstream default/translation routines. Some sources specify W/cfm rather than
pressure and total efficiency separately.

**Reason:** Source helper defaults, template fan-power rules and motor/air-stream
heat settings were not fully executed during the initial extraction. Fan power
is often included in a rating, so adding an independent fan can double-count it.

**Proposal to fix:** Recover fan type, pressure or specific-power model, efficiency,
motor efficiency, control/part-load function, design-flow operand and heat host
from the assigned helper and template rule. Preserve a source-specific-power
representation where appropriate rather than inventing a pressure/efficiency
pair. Apply source fan corrections when translating coil ratings. Include fans
once, with their source-defined heat-to-air/zone behavior.

**Closure check:** Verify design and part-load electrical power against source
calculations and test motor heat, variable/constant fan branches, SI conversion
and rating/fan double-counting. Sizing flow remains a consumer operand.

**Your comments (unreviewed; blank does not mean agreement):**

<!-- comments:H05:begin -->

<!-- comments:H05:end -->

## H06 — Controls, terminals, outdoor air and schedules

**Gap description and pattern:** Controls/curves remain unresolved for 993 general
commercial systems; terminal type and ventilation strategy are unknown in the
1,005 commercial rows. Residential component requirements include 70 older
heating/cooling/heat-pump role occurrences needing control/fan/curve translation.
Later recovery expands residential equipment to 76 records, so these populations
must be reconciled rather than added together.

**Reason:** Operation and OA-damper schedule references do not determine night
cycling, economizer/DCV behavior, terminal minimum flow, reheat, supply-temperature
reset, plant setpoints or heat-pump backup control. Some settings depend on climate,
template and source system branch.

**Proposal to fix:** Recover actual control setters and terminal/OA strategy from
the pinned source branch. Embed assigned operation, OA, setpoint and other needed
schedules with date/day/design-day semantics and source order intact. Keep
program thermostat demand separate from HVAC availability and control behavior.
Retain climate/template predicates where they affect controls. Link to the scoped
air requirements from C06 without creating a second outdoor-air demand.

**Closure check:** Exercise occupied/unoccupied and design-day operation, terminal
and night-cycle branches, economizer/DCV predicates and backup heating as applicable.
Verify all schedule references/units and source selectors before ready export.

**Your comments (unreviewed; blank does not mean agreement):**

<!-- comments:H06:begin -->

<!-- comments:H06:end -->

## H07 — Residential performance translation

**Gap description and pattern:** All 41 residential HVAC fixtures retain
`performance_curves_and_fan_defaults` blockers. Their 76 recovered equipment
records comprise 42 heating, 30 cooling and four heat pumps. Fuel, equipment
selection, served fractions and reported ratings are evidence, not complete
instantaneous performance models.

**Reason:** Option selection and HPXML setters run before the upstream defaults,
rating conversion and engine equipment translation. Secondary heaters and
heat-pump backups can have different fuels and controls from the main equipment.

**Proposal to fix:** Extend the pinned residential execution through relevant
HVAC default/performance routines and engine translation. Recover speed/stage
performance, fans, heating/cooling functions, lockouts/defrost/backup logic and
served fractions, preserving the exact producing method for every field.
Keep primary, secondary and backup equipment distinct. Use explicit test sizing
only to verify the source rule; actual model capacity remains a consumer input.

**Closure check:** Compare translated source objects and operating-point
calculations for a residential pilot, then every supported equipment branch
and fixture. Include secondary heaters and all four HVAC heat-pump records;
the simplified solar DHW skip does not remove that fixture's HVAC.

**Your comments (unreviewed; blank does not mean agreement):**

<!-- comments:H07:begin -->

<!-- comments:H07:end -->

## H08 — Residential distribution and equipment hosting

**Gap description and pattern:** All 41 residential HVAC fixtures retain
`distribution_and_control_translation` blockers. Equipment can have null
`distribution_system_idref` or `location`; those nulls have not all been classified
as source defaults, inapplicability or consumer hosting inputs.

**Reason:** Central ducted, ductless and room/unit equipment need different
distribution models. Duct losses, insulation and leakage depend on source
selections plus actual lengths/areas and thermal hosts. A recovered furnace
rating does not define its distribution network.

**Proposal to fix:** Trace source distribution creation and option/default
routines. Recover distribution family, source leakage/insulation and control
rules; expose actual duct geometry, thermal host and serving assignment as
consumer bindings when applicable. Export an explicit source-proven absence
for ductless/non-distributed branches. Resolve equipment location separately
from supply/return loss hosts, and do not assign every loss to the conditioned zone.

**Closure check:** Validate ducted and ductless branches, reference integrity,
supply/return distinction, hosted losses and unit conversions. Confirm omitted
distribution means source-proven inapplicability rather than unknown-as-zero.

**Your comments (unreviewed; blank does not mean agreement):**

<!-- comments:H08:begin -->

<!-- comments:H08:end -->

## H09 — Sizing, serving assignment and source applicability

**Gap description and pattern:** Every HVAC variant needs external serving
assignment and model sizing. Commercial systems currently have null climate
labels even where their later control/performance rules may use climate context.
Nominal prototype sizes and residential source fixtures cannot determine the
consumer building's capacity, equipment count or actual EPW.

**Reason:** The Atlas describes energy semantics independently of geometry and
population prevalence. Model-independent records can still have source-dependent
capacity/climate branches; unspecified applicability is not proof of universal
applicability.

**Proposal to fix:** Declare exact required sizing/serving operands and their
units, with internal topology from H01 already resolved. Recover source climate,
template and subtype applicability predicates; distinguish documented shared
applicability from unknown context. Include a complete source sizing algorithm
only if that is the selected executable recipe; otherwise require explicit sized
capacities/flows. Do not silently invoke autosizing, adopt nominal prototype
geometry or choose a plant to make the export pass. Preserve independent system
identity without implementing cross-contract compatibility resolution.

**Closure check:** Test missing bindings, unsupported climates/templates,
capacity-rule selection and one/multiple-zone assignment. An export may require
consumer sizing, but must contain every source rule needed to use that sizing.

**Your comments (unreviewed; blank does not mean agreement):**

<!-- comments:H09:begin -->

<!-- comments:H09:end -->

## X01 — Consumer schemas, complete dependencies and migration

**Gap description:** The proposed construction/system v1 consumer schemas and
exporters do not exist yet. Four source-recovery pilots exist, but they are not
ready consumer exports. Existing separate raw catalogue pages/resources remain.

**Reason:** Source recovery was deliberately stored in independent sidecars to
preserve frozen releases. A ready exporter still needs to apply that evidence,
enforce model-specific requirements and deliver all materials/components/curves/
schedules needed by a single copied object.

**Proposal to fix:** Implement separate versioned construction and HVAC contracts,
following program JSON conventions for SI, active operands, provenance and
required bindings. Use element/package forms for construction and explicit
conditional component graphs for HVAC. Embed required dependencies with stable
IDs and validate closure; keep raw evidence and simulation-ignored metadata
separate from active physics. Ready export fails on unresolved active physics.
Add migration notes/ADRs and representative Medium Office/residential examples.

**Closure check:** Validate schema, applicability, physical constraints,
dependency closure, schedule semantics and complete source provenance. Copying
one ready object must not require undisclosed Atlas manifest lookups or defaults.
Neither construction nor HVAC exports may require detailed DHW models.

**Your comments (unreviewed; blank does not mean agreement):**

<!-- comments:X01:begin -->

<!-- comments:X01:end -->

## X02 — All-variant completeness, reproducibility and publication

**Gap description:** No final ready consumer catalogue or corresponding
all-variant completeness receipt has been generated for constructions/HVAC.
Source-resolved rows and passing pilots cannot substitute for that deliverable.

**Reason:** Recovery dispositions certify only their recorded boundary. They do
not prove final dependency closure, engine-ready source semantics, deterministic
consumer exports or deployed copy behavior.

**Proposal to fix:** Validate Medium Office first, then residential, then all
3,798 construction and 1,046 HVAC IDs. Produce receipts containing eligible IDs,
successful/failed exports, schema/source/policy/code identities and output hashes.
Require zero eligible source-physics blockers and reproducible bytes on the
supported Python/platform matrix. Preserve frozen bundles; freeze a new version
when canonical definitions change. Add separate contract/copy pages through
existing generators and styling. Defer full site builds and lengthy CI until
publication; integrate through a protected-main PR with every required check
passing and review conversations resolved, then verify live resources.

**Closure check:** Ready counts equal the complete eligible inventories; no
variant is dropped or replaced to reach coverage. Release checks cover schema,
physical, referential, schedule, provenance and reproducibility requirements.
Live schema versions, JSON hashes and copy behavior match the release receipt.

**Your comments (unreviewed; blank does not mean agreement):**

<!-- comments:X02:begin -->

<!-- comments:X02:end -->

## X03 — Retaining detailed DHW evidence without expanding delivery scope

**Gap description:** Older recovery documents list 196 detailed DHW/solar
translation blockers and commercial heater-efficiency gaps. These can be
misread as current HVAC release requirements.

**Reason:** The field review predates the draw-only program contract and the
later decision that detailed DHW models are unnecessary. Commercial conversion
efficiencies were subsequently recovered for all 154 channels; the 41 residential
heater conversions remain known. Detailed controls/loss translation is a
different task that is now outside delivery scope.

**Proposal to fix:** Preserve the detailed source records and historical census,
but label their exclusions and superseded efficiency gaps clearly in current
coverage reports/pages. Keep supported water-heating energy in the program
contract with the agreed exclusions, source fuels/conversions and SmallHotel
delivery cap. Do not implement detailed tanks, standby, auxiliary, pilot or
solar-credit models as a prerequisite for construction/HVAC readiness. Do not
delete the retained evidence or count excluded effects as observed zero.

**Closure check:** Current coverage denominators contain construction/HVAC only;
no detailed DHW dependency appears in a ready system export. Published scope and
consumer accounting prevent applying both simplified energy and explicit heater
energy to the same demand.

**Your comments (unreviewed; blank does not mean agreement):**

<!-- comments:X03:begin -->

<!-- comments:X03:end -->

## Current construction-only work order

1. Freeze the above-ground boundary under ADR 0020 and reconcile all source
   selectors, including C09's missing above-ground dependencies.
2. Validate Medium Office's above-ground closure through C03–C06, with infiltration
   only. Ground, foundation-dependent assemblies and mechanical air are deferred.
3. Recover C01's residential above-ground assemblies and settle C07's constant-ACH
   reference conditions; preserve C04/C05 glazing and climate-zone decisions.
4. Implement the independent above-ground consumer contract, validate every
   eligible variant, and publish the 100%-ready construction milestone.

H and X entries remain unreviewed. No acceptance of the earlier HVAC or shared
contract/publication proposals is inferred from their blank comments.

## Earlier combined work-order proposal (deferred)

1. Close C02's specific source-classification issue and validate the Medium Office
   construction closure, including C03–C06 and applicable C08 bindings.
2. Complete the Medium Office PVAV pilot through H02–H06; use it to settle the
   executable graph/dependency contract in X01 before expanding commercial families.
3. Recover residential assemblies/airflow (C01/C07) and HVAC performance/distribution
   (H07/H08), keeping geometry and sizing explicit.
4. Expand by source factory/material/control branch, reconcile every catalogue ID,
   and close remaining applicability/binding cases in C05/C08/H09.
5. Apply X02's all-variant release gate and X03's scope labels. Run full publication
   checks only at that stage. No fallback physical constants are proposed here.
