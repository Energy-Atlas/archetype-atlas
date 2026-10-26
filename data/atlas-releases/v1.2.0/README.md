# Energy Archetype Atlas release 1.2.0 (commercial, delta)

A delta on release 1.0.0 (ADR 0036): this folder holds only the files that differ
from `data/atlas-releases/v1.0.0`, and `manifest.json` names that base with its
manifest's SHA-256 and lists deleted files. Resolve it by reading the base and
replacing or removing the files listed here (`scripts.atlas_minor_release.files`).

It holds everything release 1.1.0 changed, the DOE reference reconciliation of the
DOE Ref templates (docs/adr/0037-doe-reference-reconciliation.md), and adds programs
to the 51 folders that had construction sets only
(docs/adr/0039-construction-only-programs.md): college, courthouse, laboratory,
data centres, the detailed offices, the generic office and the tall buildings.

Verify with `python -m scripts.atlas_minor_release --release 1.2.0 --verify`; rebuild
and compare with `--check`. Upstream notices are in `notices/` of either folder;
original Atlas work remains unlicensed (see `LICENSE`).
