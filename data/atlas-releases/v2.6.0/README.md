# Energy Archetype Atlas release 2.6.0 (unconditioned attics in the unified constructions, delta on 2.5.0)

A delta release (ADR 0036 section 2, ADR 0066): this folder holds only its own files, and a
reader resolves every other path in `../v2.5.0/`, `../v2.4.0/`, `../v2.3.0/`, `../v2.2.0/`,
`../v2.1.0/` and then `../v2.0.0/`, whose manifest hashes the chain of `manifest.json` files
records. `removed` lists the 2.5.0 paths this release drops: the old names of the construction
sets whose IDs move.

- InteriorCeiling of the openstudio-standards attic contexts (ADR 0065 section 3): in the 90.1
  and DOE Ref sets with an unconditioned `Attic` space type, the occupied zones' ceilings under
  the attic take the attic floor reversed in the source (OpenStudio interzone resolution), not
  the building-default interior ceiling. Their area leaves the unified `InteriorCeiling`
  derivation of 568 contexts in 24 construction sets (SmallOffice and SmallOfficeDetailed,
  the restaurants, the generic office, the DOE Ref small hotel); in each the reference area
  becomes 0. The derivation it replaced stays in the record
  (`provenance.interior_ceiling_correction`) with the OpenStudio evidence. The recipe, its
  assembly, the detailed rules and every other component are unchanged.
- `id-map-2.6.0.json`: every 2.5.0 ID that moves (the 24 construction sets), mapped to its
  2.6.0 ID (`ids`). The earlier maps keep the earlier moves. No program, schedule or service
  moves.
- Citing files follow the new IDs: the small-hotel evidence and `id-map-2.3.0.json`.
- `LICENSE` is the MIT License for code and `LICENSE-DATA` the CC BY 4.0 legal code for data
  and documentation; attribute as "Archetype Atlas, Energy-Atlas" with the release number.

Exports of this release take unified constructions 4.1.0 (ADR 0065) for every unified context:
`attics` (the unconditioned attic, its conditioned boundary and the derived
`attic_omitted_roof`), `components.<role>.attics` and `export_corrections`; Program JSON 6.2.0,
detailed constructions 5.0.0, source-model constructions 2.0.0 and building services 1.0.1 are
unchanged, naming `atlas-release-2.6.0`. The generator (`atlas-schedules` 4.1.2) reads it; its
recipes are 2.5.0's. Resolve the chain with `python -m scripts.atlas_delta`
(`scripts.atlas_delta.files('2.6.0')`); verify with `--verify`, rebuild and compare with
`--check`. Upstream notices are in 2.0.0's `notices/`.
