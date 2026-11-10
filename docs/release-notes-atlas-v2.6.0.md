# Atlas release 2.6.0 (delta on 2.5.0): release and migration notes

Release 2.6.0 publishes the unconditioned-attic repair ([ADR 0066](adr/0066-release-2-6-0.md); contract and rule
[ADR 0065](adr/0065-unconditioned-attic-boundaries.md)): unified constructions 4.1.0 become the release's unified
contract, and the stored records carry the corrected code-prototype `InteriorCeiling` derivation. It is a delta on
2.5.0: `data/atlas-releases/v2.6.0` holds only its own files, and its `manifest.json` names 2.5.0 as `base_release`,
with that manifest's SHA-256, and lists the 2.5.0 paths it removes. Status `released` (2026-11-09).

## What changes for readers

- **Resolve the chain.** Read `v2.0.0`, then lay `v2.1.0` to `v2.6.0` over it, removing each manifest's `removed` paths
  (`scripts.atlas_delta.files('2.6.0')`). `scripts.atlas_exports.Release()`, the generator read from the tree and the
  site default to 2.6.0.
- **Unified constructions 4.1.0 for every unified context** (`schemas/construction-equivalent-v4.1.schema.json`,
  `urn:archetype-atlas:construction-equivalent:4.1.0`). An additive minor over 4.0.0: every 4.0.0 field keeps its
  meaning. 926 contexts state an unconditioned attic (568 openstudio-standards: 90.1 and DOE Ref SmallOffice,
  SmallOfficeDetailed, the restaurants, the generic office, the DOE Ref small hotel; 342 IECC SmallOffice and
  restaurants; 16 ResStock dwellings):
  - `attics[]`: the attic's exterior parts (roof deck, soffit or gable walls), the `conditioned_boundary` (the attic
    floor, with `zone_side.orientation` `reverse_layers`, or a ResStock ceiling `as_listed`), other interior parts, the
    roof-to-boundary area ratio, the source's default roof rule for a roof over occupied space, and
    `attic_omitted_roof`: the derived assembly (method `attic_series_stack_1.0.0`) for the top of the occupied zones
    when the attic is not modelled, with its stack, U bounds and capacity;
  - `components.<role>.attics`: which part of a role's reference area belongs to the attic;
  - `export_corrections`: the corrected `InteriorCeiling` derivation of the openstudio-standards contexts (below).
  The other 4,212 of the 5,138 unified contexts are their 4.0.0 document with `schema_version` 4.1.0.
- **The InteriorCeiling of the openstudio-standards attic contexts** (ADR 0065 section 3). OpenStudio gives the occupied
  zones' ceilings under an `Attic` space type the attic floor's construction reversed, not the building-default
  `Typical Interior Ceiling` (OpenStudio 3.10.0 interzone resolution; the PNNL and DOE reference IDFs agree). The
  unified records counted those ceilings under `InteriorCeiling`; in 2.6.0 they do not. In all 568 contexts (24 sets) the
  `InteriorCeiling` reference area becomes 0 (`unique_source_recipe_without_reference_exposure`); the recipe and its
  assembly are kept. The record keeps the derivation it replaced (`provenance.interior_ceiling_correction` in the stored
  record; `export_corrections[0].stored` in the export) with the OpenStudio evidence row `attic-evidence-16def2`.

  | 90.1-2019 SmallOfficeDetailed, every climate | 2.5.0 | 2.6.0 |
  | --- | --- | --- |
  | `InteriorCeiling` reference area | 511.156 m² of `typical-interior-ceiling` | 0 |
  | Attic floor (`InteriorFloor`, the conditioned boundary) | 511.156 m², unchanged | unchanged, now stated as `attics[0].conditioned_boundary` |
  | Attic-omitted roof, 4A | not in 4.0.0 | U 0.11384 W/m²K, C 31,414 J/m²K |

- **IDs.** The 24 corrected construction sets move (construction set IDs hash the set): `id-map-2.6.0.json` maps them.
  No program, schedule, service, assembly or material moves, and no program value changes.
- **Contracts.** Unified constructions **4.1.0**. Program JSON 6.2.0, detailed constructions 5.0.0, source-model
  constructions 2.0.0 and building services 1.0.1 are unchanged; every export names `atlas-release-2.6.0`.
- **Generator.** No change: `atlas-schedules` 4.1.2 (its wheel bundles the 2.5.0 view, with the same recipes) is the
  generator the 2.6.0 manifest names.

## Site

The catalogue builds release 2.6.0: a construction page's unified button reads `Unified 4.1.0`, and the unified
document of an attic context carries its attic statement.

## Migration

1. Re-key stored 2.5.0 construction set IDs (and unified context IDs, which are the set ID and the context key) through
   `id-map-2.6.0.json`. Program IDs are unchanged.
2. Read unified constructions 4.1.0: dispatch on `attics`. Where the attic is not modelled, use
   `attics[].attic_omitted_roof.assembly_id` for the occupied zones' top surfaces in place of `ExteriorRoof`, and deduct
   the boundary contributor from `FloorDistributedMass` once. Where it is modelled, keep the 4.0.0 roles and reverse the
   `InteriorFloor` attic floor on the zone ceilings.
3. Do not apply `InteriorCeiling` to the ceilings under an attic: its reference area is 0 in the openstudio-standards
   attic contexts.

The BEMGen items are in [`docs/bemgen-handoff-release-2-6-0.md`](bemgen-handoff-release-2-6-0.md).

## Verify

```console
python -m scripts.atlas_delta --verify                    # the delta against its manifest and base
python -m scripts.atlas_delta --check                     # rebuild 2.6.0 from its inputs; 2,847 views assemble
python -m scripts.atlas_edits_2_6_0                       # what the edit changes over 2.5.0
python -m scripts.attic_boundary --export DIR             # unified 4.1.0 of every attic context, with SHA256SUMS
python -m scripts.attic_boundary --inventory DIR          # the attic inventory of the release
```
