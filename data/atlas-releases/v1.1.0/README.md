# Energy Archetype Atlas release 1.1.0 (commercial, delta)

A delta on release 1.0.0 (ADR 0036): this folder holds only the files that differ
from `data/atlas-releases/v1.0.0`, and `manifest.json` names that base with its
manifest's SHA-256 and lists deleted files. Resolve it by reading the base and
replacing or removing the files listed here (`scripts.atlas_delta_release.files`).

It applies the DOE reference reconciliation to the DOE Ref templates
(docs/adr/0037-doe-reference-reconciliation.md): the DOE v1.4_7.2 post-1980 and
pre-1980 models are the authority for their schedules and loads. The register in
`data/reconciliation/doe-reference-v1.json` records every difference and its
decision; `data/reconciliation/doe-reference-values-v1.json` holds the extracted
values. The 90.1 templates are unchanged.

Verify with `python -m scripts.atlas_delta_release --verify`; rebuild and compare
with `--check`. Upstream notices are in `notices/` of either folder; original Atlas
work remains unlicensed (see `LICENSE`).
