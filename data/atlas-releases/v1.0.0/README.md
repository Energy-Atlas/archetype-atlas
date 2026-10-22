# Energy Archetype Atlas release 1.0.0 (commercial)

Suite-based storage under ADR 0036 (docs/adr/0036-suite-based-release-storage.md).
This release covers the commercial templates; residential (ResStock) storage is
deferred and remains in the frozen earlier releases.

- `commercial/<template>/<building-type>/`: one file per program under
  `programs/{source,department,general}/` and per construction set under
  `constructions/`; the folder's `schedules.json`, `systems.json`,
  `components.json`, `services.json` and `water.json` tables.
- `commercial/<template>/library/`: assemblies, materials, HVAC performance curves
  and rules shared between that template's building types.
- `evidence/`: evidence per folder and per template library, and `glossary.json`
  for texts, source files, filling-rule notes and unresolved reasons.
- `manifest.json`: every file with its SHA-256 and size, the pinned inputs and
  record counts.

Verify with `python -m scripts.atlas_release --verify`; rebuild and compare with
`--check`. Programs store fillings inline: the source-backed reading ignores them,
the filled reading applies them. Upstream notices are in `notices/`; original
Atlas work remains unlicensed (see `LICENSE`).
