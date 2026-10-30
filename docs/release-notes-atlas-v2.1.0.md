# Atlas release 2.1.0 (delta on 2.0.0): release and migration notes

Release 2.1.0 is the first delta on the 2.0.0 snapshot
([ADR 0046 section 12](adr/0046-release-2-0-0.md)): `data/atlas-releases/v2.1.0` holds
only the files that differ from 2.0.0, and its `manifest.json` names 2.0.0 as
`base_release` with that manifest's SHA-256. Status `released` (2026-10-29). Every
program, construction set, service and system ID is 2.0.0's.

## What changes for readers

- **Resolve one base.** Read `data/atlas-releases/v2.0.0`, then lay `v2.1.0` over it
  (`scripts.atlas_delta.files('2.1.0')`); nothing is removed. `scripts.atlas_exports.Release()`
  now defaults to 2.1.0 (`--release 2.1.0`), and exports name `source.release`
  `atlas-release-2.1.0`. The Program JSON 5.1.0, 5.2.0 and 5.4.0, building services and
  source model construction schemas admit the new name; every other export is byte for byte
  2.0.0's apart from that field.
- **`LICENSE`**: original code MIT, original data and documentation CC BY 4.0
  ([ADR 0048](adr/0048-open-licences.md)). 2.0.0 was already covered by the root licence;
  2.1.0 packages the text.
- **Apartment units are ResStock multifamily units** in the eight apartment folders'
  `generator.json` (90.1-2007, 2013 and 2019 Midrise and Highrise; DOE Ref Pre-1980 and
  1980-2004 Midrise): each of the 38 apartment-unit recipes carries a `resstock_unit` block
  and its `caller_water` in place of the prototype's slots, loads and controls
  ([ADR 0047](adr/0047-resstock-apartment-units-and-source-magnitudes.md)). They are the
  recipes the `atlas-schedules` 3.0.0 package ships
  ([ADR 0049](adr/0049-atlas-schedules-packaging.md)); the other 1,506 recipes are
  unchanged. A request for an apartment unit now needs `residents`, `location` and
  `extent.floor_area` (generator request schema 3.0.0).
- **The manifest names its generator**: `generator.version` 3.0.0, `generator.wheel`
  `atlas_schedules-3.0.0-py3-none-any.whl`, `generator.release_tag`
  `atlas-schedules-v3.0.0` and the packaged recipes' digest. Install the wheel from
  <https://github.com/Energy-Atlas/archetype-atlas/releases/tag/atlas-schedules-v3.0.0>;
  its `SHA256SUMS.txt` (attached 2026-10-29) gives the wheel's digest
  `f082bb12f951fdebd78ddcf8ab20cc65a267a02a70213de4d7f13d56648229cb`, verified with
  `sha256sum -c SHA256SUMS.txt` ([generator guide](schedule-generator.md#quick-start)).

## Not in this release

- Recipes for the later families (IECC, residential, construction-only, plenum) and for
  the DOE Ref types without a sampling building type.
- Writers for new releases from source inputs (2.0.0's writers left the tree in stage X1.3);
  this delta is written from the packaged recipes and the root licence.
- Systems and water heaters of the IECC commercial and residential families.

## Verify

```
python -m scripts.atlas_snapshot --verify
python -m scripts.atlas_delta --verify
python -m scripts.atlas_delta --check
python -m unittest tests.test_release_2_1_0
```
