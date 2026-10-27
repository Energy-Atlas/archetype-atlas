# Energy Archetype Atlas release 1.3.0 (commercial, delta)

A delta on release 1.0.0 (ADR 0036): this folder holds only the files that differ
from `data/atlas-releases/v1.0.0`, and `manifest.json` names that base with its
manifest's SHA-256 and lists deleted files. Resolve it by reading the base and
replacing or removing the files listed here (`scripts.atlas_minor_release.files`).

It holds everything releases 1.1.0 and 1.2.0 changed (the DOE reference
reconciliation, ADR 0037, and the construction-only programs, ADR 0039), and adds
the IECC commercial prototype family (docs/adr/0040-iecc-commercial-family.md):
16 building types in the IECC 2006, 2009, 2012, 2015, 2018 and 2021 editions,
96 folders under `commercial/iecc-<year>/`, extracted from the pinned PNNL IDFs
into data/program-inputs/iecc-commercial-<year>.json.
- Programs per standards space type, area-weighted over the IDF zones; absence of an
  object in the complete model is a source zero. A load that differs by location
  keeps the most common value and lists the others in `value_by_climate`.
- One construction set per folder with 19 contexts, one per climate zone (zones 7
  and 8 keyed `7-a` and `8-a`). The IDF design-flow infiltration is the source
  method. The unified representation is deferred.
- Building services and hot-water draws with their zone gains. HVAC is deferred.

Verify with `python -m scripts.atlas_minor_release --release 1.3.0 --verify`; rebuild
and compare with `--check`. Upstream notices are in `notices/` of either folder;
original Atlas work remains unlicensed (see `LICENSE`).
