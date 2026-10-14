# ADR 0026: Generate actual members of source compositions

Status: accepted by the Task 10 controller for the Warehouse C4 scope.

A packaged source composition identifies an exact parent programme, source view,
template, ordered member IDs, represented areas and original allocation weights.
Its generated result resolves every original member budget before RNG, generates
and binds the actual members, then sums their bound hourly trajectories. The
frozen parent magnitude and averaged legacy schedule remain provenance; their
product is not the authority for a new stochastic annual target. The Warehouse
audit found agreement for 25 finite load operands and retained 15 null operands.

An instance of the known parent expands into collision-checked ordered child
keys. Children share its explicit operating group, or its parent key when no
group is supplied. Existing requests retain their instance and residential seed
order. The output retains the requested parent ID/key and indexes actual children,
their emitted schedules, original targets and derived parent references.

The additive recipe operand `composition_basis_mode` must explicitly select
`source_reference_area_normalized` or `caller_parent_floor_area`. The former
requires no caller area and labels the result as reference prototype allocation;
the latter requires a positive caller floor-area extent and scales all source
member areas proportionally. With original areas A_i and total A, each physical
member participates once and contributes A_i/A. Original weights are validated
against these ratios and retained as model allocation provenance, never applied
again or interpreted as population weights. Caller multiplicity, other bases,
foreign members, conflicting composition IDs, source views, or extents reject.

Public `compose_constituents` accepts a known composition only when its exact
packaged member order, unit participation, source area proportions, denominator
and parent ID close. Arbitrary normalized mixtures keep their existing contract.
Known parent recipes may supply their authoritative composition ID internally.
Request schema 1.0.0 already permits recipe-specific `inputs`; these additions
and source-derived output receipts fit that schema without changing old request
meaning. Program JSON v3 and previous generator artifacts remain immutable.

Ruling: exact source-composition representative setpoints follow ADR 0012's
pointwise represented-area weighting among eligible active controls. Generic
mixtures retain their participation-weight policy. The source-defined composition
approximation is binding; unknown and absent controls are never zero-filled.
Receipts disclose the control method separately from load conservation. Tests
use unequal areas and unequal densities, validate source eligibility and reject
incorrect area factors. Paired member people/activity trajectories remain intact
through a later mixed-family composition; no averaged activity replaces them.

Source evidence: immutable v0.1.1 compositions/programmes and their per-field
provenance; ADR 0012; the exact 40-programme/10-composition Warehouse audit in
`build/task-10/warehouse-readiness-target-audit-20261014-01.json`; approved
implementation sketch `c4-source-composition-design.md` in the Task 10 scratch
folder. Native qualification must compare each actual Warehouse room schedule
using the same-template/view WarehouseOffice source carrier (the actual normalized
catalogue name is `Office_Warehouse`). Research and architecture
approval do not certify an uncaptured native method or unresolved channel.

The complete119-request example exposed repeated whole-bundle copying and
validation for10 source parents (879.712s on the recorded host). Ruling16 limits
the correction to private orchestration: project complete actual child owners,
owned bindings/schedule/service references into a local bundle; invoke the
unchanged public composer; remap every nested binding reference to its exact
global index; append only the parent result and retain all root RNG/order/group
receipts. One final global validation follows all parents. Public/generic
composition semantics, source transforms and RNG allocation remain unchanged.
The full1146-schedule old/new comparison at a fixed resource ID found zero
scientific differences, identical owner/binding/root receipts and no metadata
restructuring, with generation92.737s. Fresh final references and own-runtime
reproduction still qualify the new immutable artifact; earlier full-suite results
predate this bounded change.

C4 review P1 also applies the strict inverse-map rule to public composition of
multiple independently generated bundles. Every copied incoming explicit
binding reference, including nested component/target/magnitude/service and
retained generation receipts, must be rebased before it is appended. Validation
requires actual generated trajectory components to identify their binding,
owner, schedule and demand; an existing integer alone does not close ownership.
Immutable v0.5.0 retains the former public-helper defect when a source-parent
bundle follows another bundle. Patch v0.5.1 supersedes that helper while preserving
its source scope, operands, native evidence, RNG allocation and numerical methods.
