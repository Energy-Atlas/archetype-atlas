# ADR 0026 — Shared source mass accounting for both construction representations

Status: Accepted for local implementation, 2026-10-16.

## Problem

Detailed construction JSON has layer physics and assignment rules but lacks the
reference capacity budgets and native commercial additional-mass quantities
already used by the unified exporter. Program matching selects a construction;
it does not reconstruct those quantities. Requiring a detailed consumer to load
unified JSON would contradict standalone delivery and mix representations.

## Decision

Add mass-accounting contract 1.0.0 to detailed JSON 2.1.0 and unified JSON 1.2.0.
Both embed the identical source inventory for a matching context/selection.
The common builder consumes frozen construction-weighting-v1.1.0 profiles and
detailed assignment precedence, independently of equivalent fitting/export.

The contract contains source reference counted floor area, InteriorWall and
InteriorFloor capacity budgets normalized by counted floor area, and native
additional-mass quantities with source scopes and original material recipes.
Its local recipe registry uses original SI layers, not the equivalent layer
format. Detailed consumers can use those original recipes; unified consumers
retain their existing blended InternalMass/FloorDistributedMass representations.
The registry does not replace the existing envelope material registry.

Keep source fixed-area/per-floor coefficients, source space floor area and
multipliers as operands. Default execution scales precomputed reference quantities
by actual counted building floor area, retaining scope allocation information.
Non-counted attics/plenums can contribute source mass: do not drop them or divide
by their zero counted-floor share. If a source scope cannot be mapped, BEMGen must
state its allocation policy rather than discard or silently redistribute mass.

Known-zero native additional mass is explicit and has no invented recipe. Missing
profiles, unknown quantities, invalid materials or person-based quantities lacking
their required source operands fail export. Source optional coefficient nulls are
inactive only under the pinned API's documented calculation branch; the recovered
total area itself must always be a known nonnegative number.

Additional source mass and restoration mass are separate ledgers. In detailed
2.1, legacy InteriorPartition rules remain material/assignment evidence; the new
inventory owns additional-mass quantities. Never instantiate the same source
object from both. In unified 1.2, original inventory recipes are evidence and the
existing equivalent recipe realizes the aggregate once. Its aggregate quantity
must equal the inventory sum, including zero-quantity wall-transfer cases.

Explicit interior surfaces contribute capacity from actual physical area and
their selected layers. Subtract that represented capacity once from the matching
reference wall/slab budget scaled by actual counted floor area. Restore only the
positive residual. Preserve the signed residual and excess as diagnostics; never
remove explicit geometry's mass. Exterior walls and ground slabs do not consume
an InteriorFloor/InteriorWall budget. Additional furnishings are not restoration.

Preserve the approved mean of multiplied paired-face areas. Preserve residential
inferred adiabatic floor/ceiling object quantities as source capacity evidence;
they do not command duplicate physical slabs in the generated building. Changing
this historical source convention is outside this completion task.

## Versioning and delivery

Add new modules/schemas and a normalized mass release at
data/construction-mass-releases/v1.0.0. Do not modify historical hashed scripts,
schemas, releases or handover packets. Source recipes, explicit assignments,
infiltration, equivalent thermal fitting and error reports remain unchanged.
The new CLI explicitly selects detailed 2.1 or unified 1.2; historical APIs stay
historical. The public site remains on its existing frozen delivery until a
separate site/publication update. This implementation does not publish anything.

Seven paired review examples cover Medium Office, Warehouse, sparse residential,
garage-facing interior floors/walls, outdoor-exposed residential floors, and the two apartment cases carried forward from local packet v3.
Update the local ignored BEMGen prompt and packet with new schema/hash pins.
Ground/foundation, systems, programs, schedules and BEMGen implementation remain
outside this change. Preserve Atlas and upstream licensing/notices.

## Verification

Pilot-first tests cover exact original mass physics, native scaling/multipliers,
non-counted scopes, sparse and known-zero cases, orphan recipes, forged capacities,
unknown operands, negative residuals, identical cross-representation metadata,
immutable historical exports, manifest tampering and deterministic release bytes.
Check both standalone representations across all supported source contexts,
with schema/physical/reference/provenance and source-capacity conservation checks.
No annual EnergyPlus, schedule/site build or systematic energy-error experiment.
