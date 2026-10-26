# Energy Archetype Atlas release 1.4.0 (commercial and residential, delta)

A delta on release 1.0.0 (ADR 0036): this folder holds only the files that differ
from `data/atlas-releases/v1.0.0`, and `manifest.json` names that base with its
manifest's SHA-256 and lists deleted files. Resolve it by reading the base and
replacing or removing the files listed here (`scripts.atlas_minor_release.files`).

Commercial: everything of release 1.2.0 (the DOE reference reconciliation, ADR 0037,
and the programs of the construction-only folders, ADR 0039), unchanged.

Residential (new, docs/adr/0038-residential-release-storage.md):
- `residential/resstock-sdr/<building-type>/`: the 41 ResStock SDR fixture dwellings,
  one program per dwelling with its fillings, its annual series in
  `schedules/<program-id>.json` and one construction set of one context. Values are
  those of the frozen definition, resolution and construction releases.
- `residential/iecc-<edition>/{single-family,multifamily}/`: the IECC residential
  prototypes, editions 2006 to 2024 (docs/adr/0041-iecc-residential-family.md).
  Programs per type and appliance fuel, whose entries carry `applies_with` where they
  hold only for some climate codes, foundations or heating systems; one construction
  set per type with a context per climate code and foundation.
- `residential/{hud-code,doe-final-rule}/{single-section,multi-section}/`: the
  manufactured-housing prototypes (docs/adr/0042-manufactured-housing-family.md).
- Loads keep the source basis, per dwelling unit where the source gives one. Systems
  are not stored for residential families (ADR 0038 section 7).

Exports: dwelling programs as Program JSON 5.3.0 (`python -m scripts.atlas_exports
--release 1.4.0 --program ID`), ResStock construction sets as constructions 4.1.0 /
3.1.0, and the IDF-derived sets as source model constructions 1.0.0.

Verify with `python -m scripts.atlas_minor_release --release 1.4.0 --verify`; rebuild
and compare with `--check`. Upstream notices are in `notices/` of either folder;
original Atlas work remains unlicensed (see `LICENSE`).
