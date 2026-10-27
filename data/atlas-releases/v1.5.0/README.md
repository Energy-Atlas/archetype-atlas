# Energy Archetype Atlas release 1.5.0 (commercial and residential, delta)

A delta on release 1.0.0 (ADR 0036): this folder holds only the files that differ
from `data/atlas-releases/v1.0.0`, and `manifest.json` names that base with its
manifest's SHA-256 and lists deleted files. Resolve it by reading the base and
replacing or removing the files listed here (`scripts.atlas_minor_release.files`).

Everything of release 1.4.0 (the DOE reference reconciliation, ADR 0037, the
construction-only programs, ADR 0039, the IECC commercial family, ADR 0040, and the
residential tree, ADR 0038, 0041, 0042), and (docs/adr/0044-lighting-controls.md):
- Lighting controls: every commercial source program and twin records its
  `lighting_controls`. IECC and 90.1 programs take the daylighting controls of the
  PNNL prototype zones they represent (floor and lighting-power fractions controlled,
  setpoint, control type, minimum fractions), with the locations that differ in
  `daylighting_by_climate`; 90.1 programs also carry the openstudio-standards
  space-type inputs. No DOE reference model has daylighting controls, so the DOE Ref
  programs record a source zero. Occupancy-sensor credits stay inside the lighting
  schedules. Values come from data/program-inputs/lighting-controls-v1.json.
- Plenums: the 90 spaces ADR 0039 left without a standards row (tall-building,
  detailed-office and laboratory plenums) take the template's Any/Plenum row by the
  alias table sources/plenum-aliases.json, adding a plenum program and its reviewed
  twin to 19 folders. They do not count toward floor area, so no mix changes.

Exports: commercial programs as Program JSON 5.4.0 (5.2.0 and the dwelling fields of
5.3.0, plus `lighting_controls`); dwelling programs as Program JSON 5.3.0.

Verify with `python -m scripts.atlas_minor_release --release 1.5.0 --verify`; rebuild
and compare with `--check`. Upstream notices are in `notices/` of either folder;
original Atlas work remains unlicensed (see `LICENSE`).
