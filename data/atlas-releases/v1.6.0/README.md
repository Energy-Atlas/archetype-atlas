# Energy Archetype Atlas release 1.6.0 (commercial and residential, delta)

A delta on release 1.0.0 (ADR 0036): this folder holds only the files that differ
from `data/atlas-releases/v1.0.0`, and `manifest.json` names that base with its
manifest's SHA-256 and lists deleted files. Resolve it by reading the base and
replacing or removing the files listed here (`scripts.atlas_minor_release.files`).

Everything of release 1.5.0 (the DOE reference reconciliation, ADR 0037, the
construction-only programs, ADR 0039, the IECC commercial family, ADR 0040, the
residential tree, ADR 0038, 0041, 0042, and the lighting controls and plenum programs,
ADR 0044), and (docs/adr/0045-iecc-unified-constructions.md):
- Unified constructions of the IECC commercial sets: every one of the 1,824 contexts
  now holds a building-level equivalent in place of the deferred stub. Component
  recipes use the existing equivalence physics, weighted by the net surface areas of
  the source IDFs (data/program-inputs/iecc-unified-areas-v1.json); F- and C-factor
  ground constructions keep their native assemblies; mass accounting, foundation
  methods and design-flow infiltration equal the detailed documents'.

Exports: IECC unified contexts as construction-equivalent 3.1.0; programs as Program
JSON 5.4.0, as in release 1.5.0.

Verify with `python -m scripts.atlas_minor_release --release 1.6.0 --verify`; rebuild
and compare with `--check`. Upstream notices are in `notices/` of either folder;
original Atlas work remains unlicensed (see `LICENSE`).
