# Shared construction mass-accounting contract 1.0.0

Detailed construction JSON **2.1.0** and unified construction JSON **1.2.0** embed
the same `mass_accounting` object for the same selected source context. The
reference and quantity data are independent of the representation's layer format.
Both documents remain complete, separate importer inputs. Neither requires a
program file, the other representation, a source-geometry model or a catalogue.

The standalone schema is `schemas/construction-mass-accounting-v1.schema.json`.
Its definitions are also embedded into both new construction schemas: no external
schema resolution is required. All earlier schemas/exports remain unchanged.

## Contents and units

| Field | Meaning |
| --- | --- |
| `reference.profile_id` | Selected native source-reference identity |
| `reference.counted_floor_area_m2` | Normalization denominator from the source reference |
| `physical_capacity_budgets.InteriorWall` / `InteriorFloor` | One entry per selected source assembly, including reference area, normalized area and capacity |
| `additional_mass.status` | `provided` or explicitly `known_zero` |
| `additional_mass.entries` | Original source objects, their scopes, quantities, scaling operands and locators |
| `recipes` | Original ordered SI material layers and areal capacity for additional source mass |
| `reference_area_approximation` | Frozen paired-face area policy and unequal-multiplier counts |
| `provenance` | Source revision, original normalization value/units, pinned profile SHA-256, transformation and native provenance |

`area_per_counted_floor_area` is m² of source mass area per m² of counted building
floor area. `capacity_per_counted_floor_area_J_m2_K` is J/K per m² of that same
counted building floor area. `source_areal_capacity_J_m2_K` and recipe
`capacity_J_m2_K` are capacities per m² of the corresponding physical recipe.

Normalize against the actual building's counted floor area, including actual
floor multipliers once. A source object's `counted_floor_area: false` does not
mean it has no mass. Source plenum/attic quantities remain part of the reference.
`source_operands` retain optional native direct-area/per-floor/per-person fields,
source space area and source multiplier. Their native optional nulls mean inactive
coefficients in the pinned source rule; an unknown recovered total is an error.

Precomputed archetype quantities are the default. The original coefficient is
trace evidence, not an instruction to multiply both source and consumer geometry
or apply a multiplier twice. Scope records retain native building/space type,
story and source-space identity for detailed allocation. Source scopes absent
from generated geometry require an explicit BEMGen allocation policy; space-type
matching alone does not supply the missing quantities.

## Import and instantiate

Detailed JSON retains its existing `assemblies`, `materials`, component rules
and source variants. New original additional-mass recipes live in the common
contract's `recipes` registry, so furnishings are not replaced by a generic
InteriorPartition selector. Residential original partition layers and both-side
area convention remain explicit. Legacy component selectors do not create a
second copy of the additional-mass objects.

Unified JSON retains its existing equivalent InternalMass and FloorDistributedMass
recipes, quantities, fit errors and source contributors. The common inventory
defines the source budget; the equivalent recipe implements the chosen aggregate.
Do not instantiate both the original inventory and equivalent additional mass.
Capacity and total additional area agree with the frozen source quantities.

Explicit BEM walls/slabs already contribute `actual physical area * sum(t*rho*cp)`.
For a reference-preserving simplification, separately for walls and floors:

1. Multiply normalized reference capacity by actual counted building floor area.
2. Subtract capacity already represented by matching explicit physical surfaces.
3. Add `max(0, reference - represented)` using appropriate source/equivalent mass
   recipes. Retain the signed difference and excess in the report.

Count a paired floor/ceiling as one physical construction. Keep the frozen
source pairing and inferred residential adiabatic-object conventions as reference
evidence; do not create duplicate slabs from two faces. Do not deduct exterior
wall or ground-slab capacity from the interior budgets. Keep source additional
mass separate from residual restoration. Never subtract mass to hide an excess.
This accounting conserves reference capacity; it does not promise identical
heat exchange or annual building energy.

## Medium Office check

For the 90.1-2019 / 3B Medium Office example:

- Original native additional mass is approximately **4 m²/m²** counted floor area,
  including non-counted source scopes; its wood recipe has **98,010 J/(m² K)**.
- InteriorWall reference capacity is **5,698.484913 J/(m² K)** counted floor area.
- InteriorFloor reference capacity is **133,854.898875 J/(m² K)** counted floor area.

Those budgets match the previous unified release. No source material physics,
infiltration, thermal fitting or program/schedule inputs change.

## Local reproduction

```console
python -m scripts.construction_mass_release --check --examples
python -m scripts.construction_mass_release --check --validate-all
python -m scripts.construction_mass_release --context-id construction-set-beb5e983644344ce44d4a299 --representation detailed --output build/medium-office.detailed.json
python -m scripts.construction_mass_release --context-id construction-set-beb5e983644344ce44d4a299 --representation unified --output build/medium-office.unified.json
```

The normalized release deduplicates shared contracts and locks source manifests,
profiles, implementation and all schemas by SHA-256. Seven paired, Git-controlled
examples are in `docs/examples/construction-mass-v1/`. Their manifest pins exact
bytes. Ground/foundation, systems, programs, schedules, BEMGen code and publication
are unchanged. Source notices and the Atlas original-work license still apply.
