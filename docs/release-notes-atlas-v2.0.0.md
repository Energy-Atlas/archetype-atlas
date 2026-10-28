# Atlas release 2.0.0 (full snapshot): release and migration notes

Release 2.0.0 is a full snapshot ([ADR 0046](adr/0046-release-2-0-0.md)): it names no
base release and holds the resolved release 1.6.0 with the same values. It is phase 1 of
stage X1; phase 2 waits on the conditions in ADR 0046 section 4.

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

## Not in this release

- The folder itself is not committed yet (337 MB); build it with
  `python -m scripts.atlas_snapshot`.
- Recipes for the later families (IECC, residential, construction-only, plenum) and
  for the DOE Ref types without a sampling building type.
- Retiring the frozen folders, rewritten writers, selection decisions in the evidence
  tree.

## Verify

```
python -m scripts.atlas_snapshot            # write
python -m scripts.atlas_snapshot --verify
python -m scripts.atlas_snapshot --check
python -m unittest tests.test_release_2_0_0
```
