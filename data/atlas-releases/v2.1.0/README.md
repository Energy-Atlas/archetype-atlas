# Energy Archetype Atlas release 2.1.0 (commercial and residential, delta on 2.0.0)

A delta release (ADR 0036 section 2, ADR 0046 section 12): this folder holds only the
files that differ from release 2.0.0, which `manifest.json` names as `base_release` with
its manifest's SHA-256. Every other file is 2.0.0's; nothing is removed. Resolve it with
`python -m scripts.atlas_delta` (`scripts.atlas_delta.files('2.1.0')`), or copy the 2.0.0
folder and overlay this one.

What differs from 2.0.0:

- `LICENSE`: original code MIT, original data and documentation CC BY 4.0 (ADR 0048);
- `generator.json` of the eight apartment folders: every apartment-unit recipe is the
  generator 3.0.0 ResStock multifamily unit recipe (ADR 0047), which the `atlas-schedules`
  3.0.0 package ships (ADR 0049; `manifest.json` `generator`).

Verify with `python -m scripts.atlas_delta --verify`; rebuild and compare with `--check`.
Upstream notices are in 2.0.0's `notices/`.
