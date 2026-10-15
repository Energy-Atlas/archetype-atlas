# ADR 0025: Add precomputed building-level construction equivalents

Date: 2026-10-15. Status: accepted architecture; source shading and unequal
paired-face multiplier policies pending.

The user approved an additional one-assembly-per-semantic representation for
applications without program-specific envelope allocation. Preserve detailed
construction v2.2.0, original assemblies, source mappings and assignment rules.
The new `building_level_equivalent` schema is independently versioned at 1.0.0;
it does not replace or migrate any detailed or program JSON release.

## Source profiles and selection

Publish precomputed reference compositions, net opaque/opening exposure, volume,
story and physical mass inventories in the program library's supporting data at
`data/program-support/construction-weighting-v1/`. Recover 129 commercial reference
models and 41 residential fixtures from pinned source revisions and runtime.
Preserve stock fixtures and source vintages separately; do not use population
weights. A consumer does not supply program-to-face geometry to compute a blend.

Use exact native source program identifiers, with links to existing program
definitions where available. Recovered support keys are share identifiers, not
claims that missing typologies' full program load contracts are now published.
Do not rebuild annual schedules or alter program load data to publish shares.

Resolve source precedence before accumulating component area: space type, then
story, then building default. Generic hotel applicability without instantiated
source area adds no share. Source multipliers apply once. Non-counted attic and
plenum scopes retain direct exposure rather than an invented counted floor share.
Known zero exposure can be not applicable; unknown operands block readiness.

## Fixed-complexity material reduction

Conserve common-reference-film conductance and source areal heat capacity using
two massive layers and a massless resistance. Optimize only capacity split and
mass-layer resistance fraction, using the approved deterministic grid. Keep
reported errors and review flags even when the representation is inadequate;
do not increase layer count or fitting complexity to improve an error score.

Numerical normalization policy 1.0.1 retains fixed specific heat and a derived
density/thickness gauge, with nominal 6 mm total massive-layer thickness minimum
instead of the probe's arbitrary 40 mm. Two 3 mm sides allow low-capacity metal
doors to satisfy the existing thickness/diffusivity bounds. A 1e-9 relative
margin prevents floating-point rounding below the minimum. This changes no R/C
target, response equation, layer count or optimized parameter. The old probe
artefact remains unchanged as historical evidence.

Analytical homogeneous-wall tests at 1, 6, 24, 72 and 168 h verify both boundary
excitations, unequal-film ordering and inward flux signs against an independent
closed-form solution. InternalMass exchanges at the last/interior layer with an
adiabatic first side; verify that convention independently too.

For glazing, retain identical source layered physics or area-weight known simple
glazing properties. Do not silently average geometric shadows. Differing source
overhang geometries currently block the unified residential window semantic;
the detailed definitions and source evidence remain available pending a decision
on leaving overhang geometry to BEMGen.

## Quantities and consumer responsibilities

Recover actual source furnishing/internal-mass objects, rather than attaching a
mass recipe without a quantity. Partition quantities for residential fixtures
retain the pinned exposed-side convention. Physical wall and floor ledgers count
paired faces once. Unequal source face multipliers are not resolved by choosing
the first face encountered: preserve both operands and mark their area unknown
until a reference-area policy is accepted. The proposed symmetric mean remains
a pending decision. Furnishings/partition objects are additional mass; distributed
floor mass represents only physical slab capacity omitted from explicit surfaces.

For a paired floor/ceiling, the floor is the canonical construction side and its
adjacent ceiling uses the reverse of that same recipe. The separate
InteriorCeiling recipe applies only to unpaired ceilings. This carries forward
the detailed reverse-order pairing policy and aligns selection with the
floor-owned physical mass ledger. Original ceiling rules remain in the detailed
export. The additional schema fixes this rule explicitly for BEMGen.

BEMGen reconciles reference capacity budgets with represented geometry. Removed
wall capacity can be converted to InternalMass area using its equivalent areal
capacity; this preserves capacity without claiming identical heat exchange. A
zero-added-mass source may retain a source-backed wall-transfer recipe at zero
reference quantity. Do not add that recipe as invented furnishings. Likewise,
do not add distributed slab capacity to a slab already represented explicitly.
The source profile supplies complete inventories; the JSON supplies normalized
budgets and one recipe per semantic. Translator implementation remains separate.

Copy the accepted fixed natural ACH unchanged from the selected detailed context.
No mechanical ventilation, ground/foundation or system work is added here.

## Validation and publication

Check schema, source and assembly references, physical material constraints,
provenance, quantity accounting and deterministic bytes for every context. Small
EnergyPlus material/input smoke cells use the bundled 25.1.0 engine; they are not
whole-building accuracy tests. Defer systematic separation of construction and
zoning simplification errors to journal experiments or a reviewer request.

The release is an additive local research artefact. No site build, push, CI/CD or
production deployment is authorized. Keep upstream license notices and frozen
retrieval/checksum receipts. Unresolved source effects remain explicitly blocked.
