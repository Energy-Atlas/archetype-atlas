# Atlas release 2.0.0 (full snapshot): release and migration notes

Release 2.0.0 is a full snapshot ([ADR 0046](adr/0046-release-2-0-0.md)): it names no
base release and holds the resolved release 1.6.0 with the same values, apart from
daylighting as plain values. It is the only release in the tree; status `candidate`
until milestone B.

## What changes for readers

- Open `data/atlas-releases/v2.0.0` alone; there is no delta to resolve.
  `scripts.atlas_snapshot.files()` verifies and reads it, and
  `scripts.atlas_exports.Release(release='2.0.0')` exports it.
- Indented JSON files are one record per line down to three levels. Their decoded
  values equal 1.6.0's, with one exception.
- **Daylighting fractions are plain values** (user decision L-1, ADR 0046 section 6).
  `lighting_controls.geometry_dependent` is gone from the 1,373 programs that carried
  it. Apply the fractions as given; do not recompute them from your own geometry
  (BEMGen: `docs/bemgen-handoff-release-2-0-0.md`). Program IDs stay those of 1.6.0;
  milestone B re-derives every ID once, with a published map.
- Folders gain `generator.json`, keyed by release program ID:
  - 90.1: the source and reviewed generator recipes of 610 programs;
  - DOE Ref: the source recipes of 357 programs, written from this release with the
    DOE file zones (`scripts/build_reference_recipes.py`). The generator accepts these
    release IDs directly.
- Exports equal 1.6.0's apart from the dropped flag, with `source.release`
  `atlas-release-2.0.0`.
- `exporter-inputs.json` carries the values the exporters read from the frozen folders
  (capped-delivery IDs, programs with no setpoint schedules), so reading and exporting
  2.0.0 needs no other folder (ADR 0046 section 5).

## Earlier releases

Releases 1.0.0 to 1.6.0 and every frozen folder before them left the tree in stage X1.3
(ADR 0046 section 7). Read, verify or rebuild them at the tag `frozen-data-2026-10-27`;
`atlas_exports.Release` refuses them here and names the tag.

## Not in this release

- Recipes for the later families (IECC, residential, construction-only, plenum) and
  for the DOE Ref types without a sampling building type.
- Rewritten writers (milestone B): the next release is a delta on 2.0.0, written by
  them; the 90.1 construction IDs move to interpreter-independent hashing with a map.
- Selection decisions in the evidence tree.

## Verify

```
python -m scripts.atlas_snapshot --verify
python -m unittest tests.test_release_2_0_0 tests.test_reference_recipes
```

The writer and `--check` read release 1.6.0 and the frozen definitions; run them at the
tag `frozen-data-2026-10-27`.
