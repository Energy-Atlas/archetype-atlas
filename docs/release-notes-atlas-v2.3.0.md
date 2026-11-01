# Atlas release 2.3.0 (delta on 2.2.0): release and migration notes

Release 2.3.0 publishes the corrections and contracts of the 2026-10-31 review
([ADR 0059](adr/0059-release-2-3-0.md)). It is a delta on 2.2.0: `data/atlas-releases/v2.3.0`
holds only its own files, and its `manifest.json` names 2.2.0 as `base_release`, with that
manifest's SHA-256, and lists the 2.2.0 paths it removes. Status `released` (2026-11-01).

## What changes for readers

- **Resolve the chain.** Read `v2.0.0`, then lay `v2.1.0`, `v2.2.0` and `v2.3.0` over it, removing
  each manifest's `removed` paths (`scripts.atlas_delta.files('2.3.0')`).
  `scripts.atlas_exports.Release()`, the generator and the site default to 2.3.0.
- **Values that change** ([ADR 0053](adr/0053-release-2-3-0-data-corrections.md)):
  - The unified `InternalMass` of 8 DOE Ref building-scope construction sets counts their whole
    additional-mass inventory (152 contexts; warehouse 0.674 to 2.0 m²/m², small hotel 2.369 to
    2.522).
  - The 90.1 small-hotel `Elec/MechRoom` elevator is the PNNL prototype's 16 024.3 W over 15.0503
    m² (1 064.717 W/m²), in place of DOE Ref's 32 110 W, and its support mixes follow (126.16 to
    67.88 W/m²).
  - Every other filled value is unchanged. Every unknown commercial load now carries its reason,
    and the ADR 0016 accepted absence is a stored filling (known 0 in the filled view), so the
    exporter no longer applies it by a name rule. Same-named records take the name of their source
    distinction (42 programs, 4 construction sets).
- **IDs move.** 1,550 programs and 12 construction sets have new IDs. `id-map-2.3.0.json` at the
  release root maps each 2.2.0 ID to its 2.3.0 ID (`ids`). The old files are in `removed`, and
  every citing file follows. 2.0.0's `id-map.json` still maps into 2.0.0.
- **Generation for the IECC commercial and detailed office folders**
  ([ADR 0055](adr/0055-generation-for-iecc-and-detailed-offices.md)): 99 new `generation.json`
  documents (84 IECC, 15 detailed offices). In all, 189 folders, 2,270 programs and 2,847 program
  views generate. The 66 folders without blocks are listed by class in the manifest's
  `deferred`.
- **New export contracts** ([ADR 0054](adr/0054-release-2-3-0-export-contracts.md)):

  | Contract | Version | Schema |
  | --- | --- | --- |
  | Program JSON | 6.0.0 | `schemas/program-json-v6.schema.json` |
  | Detailed constructions | 5.0.0 | `schemas/construction-json-v5.schema.json` |
  | Unified constructions | 4.0.0 | `schemas/construction-equivalent-v4.schema.json` |
  | Source-model constructions | 2.0.0 | `schemas/construction-source-model-v2.schema.json` |
  | Building services | 1.0.1 | `schemas/building-services-v1.schema.json` |

  - Program JSON 6.0.0 gives every evidence row one shape, with an ID, and holds every row it cites.
  - Its loads carry `status`, `reason`, `filling` and `evidence_id`, and a required `nulls` map gives
    the meaning of every null.
  - A dwelling's window ratios that depend on its context are in `fenestration.variants`.
  - `lighting_controls.daylighting_origin` says where the daylighting fractions come from (ADR 0059
    section 4).
  - The construction contracts name the release and rename their delivery labels.
  - Every export names `atlas-release-2.3.0`.
- **Licences** (issue #44): `LICENSE` is the MIT License for code and `LICENSE-DATA` the CC BY 4.0
  legal code for data and documentation. Attribute as "Archetype Atlas, Energy-Atlas" with the
  release number. Releases 2.1.0 and 2.2.0 keep their two-part `LICENSE`.
- **Release records** validate against the JSON Schemas of ADR 0056 (manifest, definition map,
  `generation.json`, programs, `schedules.json`, `services.json`).

## The generator

`atlas-schedules` 4.1.0 reads this release. The request and the bundle stay schema 4.0.0. A request
that names a 2.2.0 program ID that moved is refused as an unknown program; translate it through
`id-map-2.3.0.json`. Install the wheel from the `atlas-schedules-v4.1.0` GitHub release and verify it
with its `SHA256SUMS.txt` ([the generator guide](schedule-generator.md)).

## Assets

The `v2.3.0` GitHub release carries `atlas-release-2.3.0.zip` (the `v2.0.0/` to `v2.3.0/` folders)
and `SHA256SUMS.txt`. Verify the tree with `python -m scripts.atlas_delta --verify`, and rebuild and
compare with `--check`.

## Not in this release

- The systems and water heaters of the IECC commercial and residential families stay deferred (ADR
  0040, ADR 0038 section 7).
- No generation blocks for the commercial types without a ComStock sampling type, the IECC
  apartments or the residential code prototypes (ADR 0055).
