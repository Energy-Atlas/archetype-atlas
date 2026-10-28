# ADR 0023: Generated constituents and explicit physical mixtures

> Amended by ADR 0035 (2026-10-17): the semantic decisions stand; bit-level exactness, authority locks and certification ceremony are superseded.

Accepted 2026-10-14. Implements public M1 generation without changing frozen
Program JSON v3 or source/reviewed case meanings. Shipment remains a later gate.

`generate(params, seed)` validates the current resource identity and exact M1
calendar/configurations. It resolves every recipe and original annual target
before drawing any RNG, assigns residential seeds in declared residential unit
order, samples each commercial operating group once, emits selected related
channels, and fits effective magnitudes to those actual emitted integrals. A
positive source target over a zero realization is an error; no seed retry occurs.
Both accepted-inactive Plenum cases remain source-backed zero-channel results.

Bundles index schedules once. Constituents retain full resolved slots, demands,
controls, evidence and source identity, effective caller operands, and generated
source decisions. Internal preparation arrays and budget buffers are excluded
from caller operands and public constituent inputs. Source rule definitions,
special profiles, transformations, native stream allocation (including EV's
reserved slot), activity decisions/states/checkpoint and event receipts remain
visible. Heat fractions unavailable from the source remain null.

`compose_constituents(bundles, mixture, calendar)` consumes complete generated
bundles. It validates and retains their actual realizations and adds a mixed
owner. Public generation composes its single bundle after assigning unit seeds
once across the full ordered set. Composing independent precomputed bundles
uses `precomputed_bundle_composition_v1` with complete input generation receipts;
it does not claim a shared native multifamily allocation, reseed, or rewrite
source decisions. Equal commercial group names require equal actual sampled
receipts and configuration/carrier/calendar contexts. Wrapper Python version
differences are administrative; draws, source parameters and group seeds agree.

The optional request additions are `mixture.result_basis` and
`mixture.denominator = {value, unit, evidence}`. They must appear together.
`basis_bindings.extents[source_basis] = {value, unit, evidence}` explicitly
cancels each source denominator. Basis units are floor_area/m2,
dwelling_unit/dwelling, person/person and absolute/1. `basis_bindings.multiplicity`
is finite nonnegative and defaults to one. The earlier explicit `floor_area_m2`
field is a compatibility alias for `extents.floor_area` with unit m2. Its caller
value, locator, transformation and interpretation remain in
`generation.basis_alias_receipts`; a differing canonical area or unit rejects.

The general v1 `basis_bindings` object remains open for structural compatibility
with earlier inspection fixtures. Public M1 generation/composition rejects
unknown physical binding fields; it never silently interprets or discards them.

For explicit physical conversion:

`q[h] = sum(weight_i * extent_i * multiplicity_i * amplitude_i * shape_i[h]) / denominator`.

These weights are recorded as participation multipliers with explicit extents.
Without physical conversion, only a homogeneous source basis is allowed; the
result records denominator one source basis unit and normalized source-basis
weights. This does not infer unit area, geometry, stock prevalence or installed
capacity. Constituent program IDs may differ from the derived result program ID.
Catalogue compositions outside the audited M1 recipes remain unsupported.
Fractional trajectories divide by the sum of the scaled constituent effective
magnitudes, then bind their emitted integral to the conserved original targets.
This keeps fractions in range without clipping or rounding mixed arrays.

Load components remain separated by quantity, carrier, fuel and physical host.
The derived annual target is the same scaled sum of original targets; only
the realization's shape and effective magnitude change. Singletons retain their
actual shape. Constant heat fractions are weighted by conserved component annual
energy; zero energy does not create missing fractions. This conserves annual
partition, while an aggregate constant hourly partition is an approximation.

People heat uses each member's source density/count times its own occupancy and
activity, preserving the pair and source evidence in receipts. It never
multiplies separately averaged schedules. Thermostats use weight-normalized
averages over positive-weight, physically active members that possess the
control. Their receipt identifies a representative control, not conserved HVAC
load. Other water/activity/occupancy controls remain with original constituents.

Shared-service source IDs alone do not identify one physical service. An explicit
lower-level descriptor identifies `physical_id`, `mode: whole`, `demand_id`,
`source_service_id` and physical `extent`. Copies must have identical source,
original budget, extent and actual trajectory. That whole service is emitted
once, divided by the explicit result denominator; program weights and
informational allocations do not scale it again. Allocated-component semantics
without audited source-total/already-allocated meaning fail `requires_binding`.
This follows v3's `ownership: instantiate_once` and ADR 0009's instruction to
apply components or the original service once, never both. No real M1 shared
service mapping is added: all ten recipes have no active shared services.

Scientific comparison projects generated references to ownership keys. Exact
source evidence/operands, option choices, RNG vectors/states and event timing
remain exact. Generated daily profiles and arithmetic receipts use their named
fraction, temperature, activity or `source_arithmetic` tolerances; no floating
array rounding/hash requirement is introduced. Runtime version metadata does
not defeat equivalence. Original source magnitude exact comparison is unchanged.

Runtime validation uses a bounded standard-library checker for the enumerated
v1 schema vocabulary. Unknown schema keywords fail closed, including optional
branches. Package-local schema copies are byte-checked against canonical schemas
in development tests and remain available when the package runs independently.
Development JSON Schema tests remain the oracle. Runtime requires only Python's
standard library and packaged immutable resources.

## Amendment (generator 3.0.0, 2026-10-28)

Amended by [ADR 0047](0047-resstock-apartment-units-and-source-magnitudes.md) (O15):
commercial and service members bind their source magnitudes, so their annual totals are
generated, not original. The mixed shape is still `Σ factor × amplitude × shape`, now
weighted by source magnitudes, and the mixed annual target is the same scaled sum of
member totals; it no longer equals the scaled sum of original targets.
