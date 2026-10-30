# Atlas release 2.2.0 (delta on 2.1.0): release and migration notes

Release 2.2.0 publishes the schedule generator's parameters with the programs
([ADR 0051](adr/0051-generation-parameters-in-the-release.md)). It is a delta on 2.1.0, which is
a delta on the 2.0.0 snapshot: `data/atlas-releases/v2.2.0` holds only its own files, and its
`manifest.json` names 2.1.0 as `base_release` with that manifest's SHA-256. Status `released`
(2026-10-30). No program, schedule, service, system or construction value changes, and every ID
is 2.0.0's: the program ID rule leaves the new `generation` block out.

## What changes for readers

- **Resolve the chain.** Read `v2.0.0`, lay `v2.1.0` over it, then `v2.2.0`, removing the paths
  its manifest lists under `removed` (`scripts.atlas_delta.files('2.2.0')`).
  `scripts.atlas_exports.Release()` defaults to 2.2.0, and exports name `source.release`
  `atlas-release-2.2.0`. Every export is byte for byte 2.1.0's apart from that field.
- **Program JSON 5.4.0 names its release by pattern.** `source.release` is
  `^atlas-release-\d+\.\d+\.\d+$` instead of an enum of four labels, a 5.4.x widening: every
  earlier label still validates, and later releases need no schema edit. A consumer that embeds
  the 5.4.0 schema refreshes its copy once (BEMGen D-198). Program JSON 5.1.0 and 5.2.0, building
  services 1.0.0 and source model constructions 1.0.0 keep their enums and gain the label.
- **`generation.json` per generated folder** (83 commercial folders of the 90.1 and DOE Ref
  templates, 7 ResStock dwelling folders): the folder's program `generation` blocks (the method
  and, per view, the parameters the record cannot give: a building configuration, the ResStock
  unit characteristics, or a dwelling's executed OpenStudio-HPXML inputs), its services' blocks
  and its building configurations. A program reads with its block as `generation`. 1,008
  programs carry blocks (734 `comstock_hours`, 191 `composition`, 22 `fixed`, 20 `resstock_unit`,
  41 `resstock_dwelling`), 1,585 program views; 186 services; 120 configurations.
- **`definition-map.json`**: each definition program ID generator 3.0.0 took (1,216), with its
  release program and view (`values`), each definition service ID (150) with its release
  service, and the 12 retired hotel corridor compositions no release program holds.
- **`generator.json` removed** (83 paths, among them the eight 2.1.0 rewrote). The apartment
  units they carried are the same ResStock units as the `resstock_unit` blocks.
- **The manifest names its generator**: `generator.version` 4.0.0, the wheel
  `atlas_schedules-4.0.0-py3-none-any.whl` on `atlas-schedules-v4.0.0`, request schema 4.0.0;
  `generation.schema_version` 1.0.0; `counts.generation`; `input_sha256` pins the licence, the
  base manifest and the writer `scripts/atlas_delta.py`.
- **Release 2.1.0's manifest** is edited in place (`edited_by`): it pins the licence and the base
  manifest only, because the packaged recipes it pinned left the tree with generator 4.0.0; its
  `generator.json` files are unchanged and verified by checksum.

## The generator

Generator 4.0.0 (`atlas-schedules` 4.0.0) assembles its recipes from this release and ships no
copy of release values. Requests take release IDs and a `values` view (schema 4.0.0); a 3.0.0
request translates with `atlas-schedules translate`. The wheel bundles the generator view of
2.2.0; `ATLAS_RELEASES` or `--release-dir` reads the extracted `atlas-release-2.2.0.zip` or a
checkout instead. Each bundle records `release.version` and `release.manifest_sha256`. See
[the generator guide](schedule-generator.md) and ADR 0051 section 8 for what a consumer changes.

## Not in this release

- Exports carrying `generation` (a Program JSON 5.5.0); the blocks stay in release storage.
- Generation blocks for the IECC, manufactured-housing, construction-only and plenum programs
  and for the DOE Ref types without a sampling building type.
- Systems and water heaters of the IECC commercial and residential families.

## Assets and verification

The GitHub release `v2.2.0` carries `atlas-release-2.2.0.zip` (the `v2.0.0/`, `v2.1.0/` and
`v2.2.0/` folders as they sit in the repository; sorted entries, fixed times) and
`SHA256SUMS.txt`:

```
sha256sum -c SHA256SUMS.txt
python -m scripts.atlas_snapshot --verify
python -m scripts.atlas_delta --verify --release 2.1.0
python -m scripts.atlas_delta --verify
python -m scripts.atlas_delta --check            # the manifest around the files; every block assembles
python -m scripts.release_editor --check         # every program keeps its ID with its block
python -m unittest tests.test_release_2_2_0
```
