# Catalogue redesign: three object kinds and element-level definitions

Date: 2026-10-07.
Status: conversation decisions recorded for design review; implementation has not
started. Recording this design does not approve an implementation plan or dispatch
the BEMGen stage.

## Purpose and boundaries

Provide a small catalogue for selecting deterministic energy semantics for
zoning-LOD experiments. Its first-class object kinds are **Programs**,
**Constructions**, and **HVAC systems**. Support generic JSON consumers beyond
BEMGen. Keep canonical research archives whole, frozen releases immutable and
the existing checksum-verified selective static delivery architecture.

The target for constructions and HVAC is identity or explicitly described
similarity of corresponding elements and their parameters. Building-level
selection may choose a package of element definitions; it does not reduce those
elements to a building-average U-value, COP or whole-building equivalence claim.
Geometry and assignment remain downstream responsibilities.

The approved mixture memberships, weights, exclusions and controls in
[ADR 0012](../../adr/0012-program-composition-simplification.md) and the
[family matrix](../../reviews/program-aggregation-matrix.md) remain authoritative.
The committed decision baseline is not implemented mixture data.

## Entry gate and navigation

The catalogue entry page presents two selection buttons:

- **Residential**
- **Non Residential**

Each route offers the three object kinds, with a **Find an entry** view within
each kind. A shared definition can be reached through both routes using the same
identity. Mixed-use consumers can select definitions from both routes.

The gate classifies intended building use for browsing. It must not be inferred
directly from an upstream `is_residential` flag: source flags also occur on hotel
and hospital programs. Standards-derived apartment programs belong under
Residential while retaining their original source lineage. They remain distinct
from ResStock dwelling fixtures.

Schedules, material records, mixture recipes, component performance rules,
shared-service records, mappings and provenance are supporting resources reached
through the three kinds. Upstream generator arguments are not active catalogue
entries or consumer configuration inputs in this release. Existing published
record URLs and source evidence remain accessible.

## Find an entry: Programs

Use these visible controls:

| Control | Meaning and behavior |
| --- | --- |
| Search | Search program names, building-family names, source labels and IDs. |
| Building type | Building/program family, including the named DOE/Standards families; keep readable labels and exact source identities distinct. |
| Program detail | **Finest**, **Intermediate**, **Coarse**, exposing only meaningful modes supported by the selected family and template. |
| Vintage (standard/source) | Exact standard/template or source-fixture context. Show the source family so code editions and existing-stock evidence are not conflated. |
| Climate | Show only when the selected program definition or determined profile genuinely differs by reported climate context. Omit for climate-independent program definitions. |

Program detail maps to the approved modes: Finest = `SourcePrograms`, Intermediate
= `DepartmentMixes`, Coarse = `GeneralMix`. It is separate from geometric or
thermal-zoning LOD. Families without three meaningful modes expose fewer choices.
Do not fabricate a mixture to populate a selector.

Default to ASHRAE 90.1-2019 for families supporting that template, and to the
finest supported source-program mode. Do not substitute that template for a
ResStock fixture or another unsupported context. Unsupported combinations are
reported explicitly.

Determine climate applicability from the actual source inputs, profile metadata
and applied rules. A climate-independent base table does not establish that
every post-table control or generated profile is climate independent. Keep
fixture-reported climate and proxy-weather bindings traceable.

## Find an entry: HVAC systems

Use these visible controls:

| Control | Meaning and behavior |
| --- | --- |
| Search | Search system/component names, source labels and IDs. |
| Building type | Include when source-supported building applicability differentiates the available definitions. |
| Vintage (standard/source) | Exact standard/template or source context, with its source family explicit. |
| Climate | Exact reported or resolved climate applicability; retain an explicit unreported/unassigned state. |
| System type | Principal grouping attribute, such as PTAC, PSZ-AC, VAV, CAV or DOAS, using the supported source vocabulary. |

Heating technology/fuel and cooling technology may be conditional refinements
when they materially distinguish supported results. Do not add a long list of
empty controls or infer missing fuel from a display name. System-type labels are
groupings, not proof of identical component performance.

## Find an entry: Constructions

Use these visible controls:

| Control | Meaning and behavior |
| --- | --- |
| Search | Search construction names, material/assembly labels and IDs. |
| Building type | Source-supported applicability or construction-set assignment; shared/unassigned definitions remain explicit. |
| Vintage (standard/source) | Exact standard/template or source context, with its source family explicit. |
| Climate | Exact source climate-set applicability, without broadening or interpolating labels. |

The repeated vintage item in the conversation specifies one control, not two.
Within a result, identify its element role, such as wall, roof, floor, window,
internal partition or ground-contact surface. A construction package links the
appropriate element definitions. Derive building applicability through actual
source construction-set rules; do not create a Cartesian building-by-climate
library from shared records. Preserve conditioning categories such as Residential,
Nonresidential and Semiheated independently of the navigation gate.

## Programs, dwelling scope and addition

Programs contain determined loads, explicit units and scaling bases, schedule
references, setpoints and other relevant energy semantics. Preserve provenance
for every extracted or derived field. Null remains unknown or not reported.

A residential program may represent a whole dwelling unit. Use an existing
aggregate dwelling/apartment definition when available; no room-area mixture is
required. Per-unit/absolute quantities do not require room-area weights. A
per-area quantity still requires the downstream represented area. If an upstream
magnitude routine requires area or another missing input, report that dependency
rather than inventing it. The current ResStock profiles do not by themselves
establish complete load magnitudes.

Support the appropriate original or conserved unit basis for a load. Summation
is used for the approved mixtures and for an isolated building-serving device
added to its host zone. Alternative unit representations of one demand are not
additional physical contributions. Different physical quantities, such as water
flow and heating power, require explicit conversion inputs before comparison or
combination. Volume values retain their period and schedule normalization.

For mixtures, retain the exact leaf IDs, unrounded represented source areas,
weights, input source/reviewed view and derivation method. Blend load trajectories
as `sum(w_i * d_i * s_i(t))` and heating/cooling setpoints pointwise according to
ADR 0012. Keep unmixed originals. Basement and attic programs, including named
variants, remain optional separate presets outside every mixture and denominator.

An isolated building-serving facility can be placed once in a suitable mechanical,
core or other zone where applicable. Record its identity, absolute magnitude,
host/assignment and thermal effect. Electrical demand, zone heat release and
plant demand remain distinguishable. Referencing a service from several programs
does not duplicate it; reporting allocations and the original shared service
must not both become additional physical loads. No extra zone is required solely
to host a demand curve.

## Constructions, air exchange and generic assumptions

Resolve constructions to element definitions with their relevant physical
properties. Opaque assemblies retain ordered layers and material thickness,
conductivity, density, specific heat and surface properties where supported.
Glazing retains its actual model and thermal/optical parameters. Equal U-values
alone do not establish full element identity.

Air-change settings are part of the construction selection/package by design.
Keep infiltration, outdoor ventilation and total supply air separately named,
with their actual bases, schedules and scope. Apply supported space/element
overrides where needed; a clinical total-air requirement must not become a
building-wide infiltration rate. Retain source program requirement evidence even
when the consumer-facing settings are reached through Constructions.

For **internal and ground-contact constructions**, use source-supported element
definitions when they can be resolved. **Building-level generic assumptions are
permitted when this is not possible.** Such an assumption set supplies explicit
defaults for the relevant element roles across the building. It remains an
experimental fallback, with:

- A stable, versioned assumption identity and explicit applicable roles/context.
- Actual SI properties or a declared model, with required geometry inputs stated.
- Rationale, provenance and a visible distinction from source-reported values.
- Consistent reuse across the experiment's compared models unless the scenario
  explicitly changes that assumption.

This permission does not choose numerical fallback values in this design, and
does not convert unknown source fields into source measurements. Ground-contact
representations that require perimeter, area or depth retain those dependencies.
No additional generic defaults are authorized: unresolved residential load,
infiltration and HVAC inputs remain explicit gaps or consumer requirements.

## HVAC elements and comparison

HVAC packages reference their components, relevant connections, operating/control
schedules and serving scope. Element identity includes the applicable resolved
technology/fuel, rated performance and rating basis, fan/pump parameters, curves,
control parameters and sizing inputs. Keep capacities and instance multiplicities
explicit. A common type label is insufficient.

The atlas is a library of fixed performance definitions, independent of the
model to which a consumer applies them. Model sizing and experiment sizing modes
are downstream responsibilities and are outside the atlas contract. Preserve
source-reported capacities or capacity bands as definition metadata and retain
unresolved requirements explicitly. Conditional efficiency tables must expose
their actual capacity/subtype/fuel/date predicates; deterministic resolved
variants must state their source-supported rating context. Do not choose an
arbitrary capacity to manufacture a fixed COP. Pin the lookup date instead of
relying on the machine's current date. Preserve metric distinctions and any
source-specific conversion method, including fan inclusion/exclusion.

Similarity reports identify compared properties and tolerances. Missing values
prevent claims of full identity; they do not count as matched zeros. No requirement
to reproduce a whole prototype building is introduced solely to compare resolved
element definitions.

## Schedules and deferred generators

Use the existing determined schedules now. Retain rule order, dates, day selectors,
holidays, winter/summer design days, timestep, normalization and calendar metadata.
Annual source realizations retain their original year, seed and weather/proxy
context. Do not silently compile or transplant them to another calendar.

Later, a program may optionally reference a versioned schedule-generation recipe.
Related residential schedule channels can share one seeded generation run so
occupancy, appliances, lighting and water remain coordinated. An individual
channel can stay fixed. Generated outputs use the same schedule interface as the
determined baseline. Commercial generation can use its own supported mechanism.
Generator runtime, arguments and distribution/calibration interfaces are deferred.

## Delivery and implementation boundaries

Reuse the exact-filter, field-projection and lazy-resource architecture in
[ADR 0011](../../adr/0011-static-query-delivery.md). No online backend or database
is needed. Natural-context packets remain bounded; consumers need not download
the full library. Supporting schedules and evidence remain lazy resources.

Source/reviewed selection and mixture derivation are independent dimensions.
Derived approximations and generic assumptions must be explicitly identified.
Version incompatible load/projection/status changes rather than changing the
meaning of the published v1 contract. Retain old snapshot URLs and exporter
compatibility. The eventual public MkDocs contract must be sufficient for an
independent consumer implementation.

Validate a Medium Office pilot before expanding. The implementation must then
exercise whole-dwelling semantics, mixed programs, one-time shared equipment,
construction layer/target resolution, generic internal/ground assumptions and
component-level fixed HVAC performance definitions. Run the repository's schema,
physical, referential, schedule, provenance and reproducibility checks before
release; check the gate, filters and supporting links in the browser.

The execution sequence remains: settle the stage 2 design, implement the approved
mixtures and redesigned catalogue/contract, then arrange the user-requested BEMGen
agent stage for plan generators, presets/schema and value retrieval. Keep this
work on `feature/query-dto`; do not merge main or modify BEMGen from this task.
