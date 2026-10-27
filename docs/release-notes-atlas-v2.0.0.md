# Atlas release 2.0.0 (full snapshot): release and migration notes

Release 2.0.0 is a full snapshot ([ADR 0046](adr/0046-release-2-0-0.md)): it names no
base release and holds the resolved release 1.6.0 with the same values. It is phase 1 of
stage X1; phase 2 waits on the conditions in ADR 0046 section 4.

## What changes for readers

- Open `data/atlas-releases/v2.0.0` alone; there is no delta to resolve.
  `scripts.atlas_snapshot.files()` verifies and reads it, and
  `scripts.atlas_exports.Release(release='2.0.0')` exports it.
- Indented JSON files are one record per line down to three levels. Their decoded
  values equal 1.6.0's.
- The 90.1 folders gain `generator.json`: the source and reviewed generator recipes of
  610 programs, keyed by release program ID.
- Exports equal 1.6.0's, with `source.release` `atlas-release-2.0.0`.
- `exporter-inputs.json` carries the values the exporters read from the frozen folders
  (capped-delivery IDs, programs with no setpoint schedules), so reading and exporting
  2.0.0 needs no other folder (ADR 0046 section 5).

## Not in this release

- The folder itself is not committed yet (337 MB); build it with
  `python -m scripts.atlas_snapshot`.
- Recipes for the DOE Ref programs (stale since 1.1.0) and the later families.
- Retiring the frozen folders, rewritten writers, selection decisions in the evidence
  tree.

## Verify

```
python -m scripts.atlas_snapshot            # write
python -m scripts.atlas_snapshot --verify
python -m scripts.atlas_snapshot --check
python -m unittest tests.test_release_2_0_0
```
