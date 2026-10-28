# Energy Archetype Atlas release 2.0.0 (commercial and residential, full snapshot)

A full snapshot (ADR 0036 section 2, ADR 0046): this folder holds every file of the
release and names no base. It is release 1.6.0 resolved (the DOE reference
reconciliation, the construction-only programs, the IECC commercial family, the
residential tree, the lighting controls and plenum programs, and the IECC unified
constructions; ADR 0037 to 0045), with the same values, stored more compactly, and
the generator recipes of the 90.1 and DOE Ref programs in each folder's `generator.json`.

Releases 1.1.0 to 1.6.0 are deltas on 1.0.0; later minors are deltas on this release.

Verify with `python -m scripts.atlas_snapshot --verify`; rebuild and compare with
`--check`. Upstream notices are in `notices/`; original Atlas work remains unlicensed
(see `LICENSE`).
