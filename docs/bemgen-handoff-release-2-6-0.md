# BEMGen handoff: atlas release 2.6.0 (unconditioned attics in the unified constructions)

What BEMGen receives when it moves to atlas release 2.6.0 ([ADR 0066](adr/0066-release-2-6-0.md)), and the exact fields
it reads. The contract and the rule are [ADR 0065](adr/0065-unconditioned-attic-boundaries.md), raised by BEMGen's gap
G2: its DOE SmallOffice models omit the source attic and map `ExteriorRoof` (the attic roof deck, U 2.61 W/m2K) to the
zones' outdoor-facing ceilings, where the source's thermal boundary is the insulated attic floor (U 0.10 to 0.55 W/m2K).

## 1. Versions and IDs

| Item | Release 2.5.0 | Release 2.6.0 |
| --- | --- | --- |
| Release label (`release`, `source.release`) | `atlas-release-2.5.0` | `atlas-release-2.6.0` |
| Unified constructions | 4.0.0 (4.1.0 only as an opt-in export, `--attics`) | **4.1.0**, `urn:archetype-atlas:construction-equivalent:4.1.0`, `schemas/construction-equivalent-v4.1.schema.json`, for every unified context |
| Program JSON, detailed constructions, source-model constructions, building services | 6.2.0, 5.0.0, 2.0.0, 1.0.1 | unchanged |
| Generator | `atlas-schedules` 4.1.2 | unchanged (4.1.2; same recipes) |
| ID map | `id-map-2.5.0.json` | **`id-map-2.6.0.json`**: 24 construction sets, no program |

- [ ] Re-key every stored 2.5.0 construction set ID through `id-map-2.6.0.json` (`ids`: old to new). A unified or detailed
  context ID is `<set ID>.<context key>` (`.unified` for the unified document), so it follows its set. Program, schedule
  and service IDs do not move.
- [ ] Embed the 4.1.0 schema and dispatch on `schema_version` MINOR 1. Every 4.0.0 field keeps its meaning; a context
  without an attic is its 4.0.0 document with the version raised.

The four small office eras of the LOD study:

| Template | 2.5.0 set ID | 2.6.0 set ID |
| --- | --- | --- |
| 90.1-2007 | `90-1-2007.small-office-detailed.construction-package.b1ba8a` | `90-1-2007.small-office-detailed.construction-package.7fae32` |
| 90.1-2019 | `90-1-2019.small-office-detailed.construction-package.7eee9d` | `90-1-2019.small-office-detailed.construction-package.ff7fc8` |
| DOE Ref 1980-2004 | `doe-ref-1980-2004.small-office-detailed.construction-package.8575fa` | `doe-ref-1980-2004.small-office-detailed.construction-package.bdc90e` |
| DOE Ref pre-1980 | `doe-ref-pre-1980.small-office-detailed.construction-package.db34c2` | `doe-ref-pre-1980.small-office-detailed.construction-package.14f979` |

The other 20 moved sets are the 90.1 and DOE Ref SmallOffice, FullServiceRestaurant, QuickServiceRestaurant and generic
office sets and the DOE Ref small hotel (the map lists them all).

## 2. The attic (unified 4.1.0)

**What changed.** 926 unified contexts carry `attics` (568 openstudio-standards, 342 IECC, 16 ResStock). The 4.0.0 roles
are unchanged: `ExteriorRoof` over an attic is still the attic roof deck, and the attic floor is still an `InteriorFloor`
contributor.

**Fields BEMGen reads** (90.1-2019 SmallOfficeDetailed 4A, `90-1-2019.small-office-detailed.construction-package.ff7fc8.4-a.unified`):

- `attics[0].conditioned_boundary`: role `InteriorFloor`, contributor `90-1-2019.typical-wood-joist-attic-floor.fe2a18`
  (511.156 m2, U 0.11823 W/m2K), `zone_side` `{"orientation": "reverse_layers", "zone_role": "InteriorCeiling"}`.
- `attics[0].exterior_parts`: `ExteriorRoof` `90-1-2019.typical-uninsulated-wood-joist-attic-roof.c5b0de` (598.762 m2,
  U 2.6144, share 1.0 of the role) and `ExteriorFloor` (the soffit, 56.821 m2).
- `attics[0].area_ratio_roof_to_boundary`: 1.17139.
- `attics[0].attic_omitted_roof`: `assembly_id` `90-1-2019.attic-omitted-roof.5e866b` (in `assemblies`), status `ready`,
  `u_bounds_W_m2_K` `{"equivalent_sealed_roof_only": 0.11384, "sealed_all_exterior_parts": 0.11429,
  "boundary_only_attic_at_outdoor_temperature": 0.11823, "roof_deck_alone": 2.6144}`, `capacity_J_m2_K`
  `{"equivalent": 31414.3, "roof_deck_scaled": 17549.5, "boundary": 13864.8}`.
- `components.ExteriorRoof.attics` and `components.InteriorFloor.attics`: the share of each role that belongs to the attic.

- [ ] Where the attic is **not** instantiated (the LOD study's SmallOffice models): give the occupied zones' top surfaces
  `attics[].attic_omitted_roof.assembly_id`, not `ExteriorRoof`, and deduct the boundary contributor from
  `FloorDistributedMass` once (its capacity is in the equivalent; mass accounting: count a represented slab once).
- [ ] Where the attic **is** instantiated: keep the 4.0.0 roles; the zone ceilings take the `InteriorFloor` attic floor
  with its layers reversed (`zone_side.orientation`), not `InteriorCeiling`.
- [ ] Keep `ExteriorRoof` for roofs over occupied space only where the document has no attic.
- [ ] Log `attic_omitted_roof.status`: `blocked` (with `reason`) means no equivalent could be formed; none is blocked in
  release 2.6.0.

## 3. The corrected InteriorCeiling (openstudio-standards sets)

**What changed.** In the 568 openstudio-standards attic contexts the stored `InteriorCeiling` derivation no longer counts
the ceilings under the attic: its reference area is 0 and `weight_basis` is
`unique_source_recipe_without_reference_exposure`. The assembly (`Typical Interior Ceiling`, carpet pad over 100 mm
concrete) is unchanged.

```json
"export_corrections": [{"pointer": "/components/InteriorCeiling/derivation", "status": "corrected",
  "stored": {"contributors": [{"assembly_id": "90-1-2019.typical-interior-ceiling.e4b01c", "reference_area_m2": 511.15624589999993, "weight": 1.0}],
             "source_reference_area_m2": 511.15624589999993, "weight_basis": "source_archetype_net_component_area"},
  "corrected": {"contributors": [{"assembly_id": "90-1-2019.typical-interior-ceiling.e4b01c", "reference_area_m2": 0.0, "weight": 1.0}],
                "source_reference_area_m2": 0.0, "weight_basis": "unique_source_recipe_without_reference_exposure"},
  "paired_ceiling_area_m2": 511.15624589999993, "reason": "…", "evidence_ids": ["attic-evidence-16def2"]}]
```

From 2.6.0 the record holds `corrected`; `stored` is the derivation releases 2.0.0 to 2.5.0 stored. The IECC and ResStock
sets already gave the zone ceilings the insulated construction and carry no correction.

- [ ] Do not assign `InteriorCeiling` to ceilings under an attic. A 2.5.0 package BEMGen consumed with 511 m2 of interior
  ceiling area on the zone tops reads 0 in 2.6.0.

## 4. Comparison with the pre-release 4.1.0 exports

The pre-release 4.1.0 exports (ADR 0065, `scripts.attic_boundary --export` over release 2.5.0, the correction applied
at export) equal the 2.6.0 exports except `release`, `id`, `detailed_context_id` and `source.construction_set_id`: every
assembly, layer, attic statement and attic-omitted roof is the same (`tests/test_release_2_6_0.py` checks every corrected
context). The JSON key order of the corrected contributor differs (`reference_area_m2` before `weight`: the stored record
is canonical); compare decoded JSON, not bytes.

## 5. What is not in this release

The open questions of ADR 0065 section 4 and its consequences stay open: plenum ceilings, attic air for a consumer that
omits the attic (the source's attic infiltration, 0.2001 m3/s in 90.1 SmallOfficeDetailed, is not in the package), the
DOE Ref pre-1980 attic (openstudio-standards has one, the DOE original a flat roof), ResStock gable walls in the unified
`ExteriorWall`, the attic film convention, and IECC 2024 (no unified representation).
