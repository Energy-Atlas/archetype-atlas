# Answer-key extraction

These scripts wrote the compact answer keys in `tests/answer_keys/` once, during
the 2026-10-17 restructure (ADR 0035). They read native captures and the frozen
v0.8.0 legacy generator from `data/schedule-generator/` and
`data/generator-releases/`. Those trees were then deleted and purged from the
branch history for size. The scripts are kept as the record of how each answer
key was derived: which source file, which cases, and how values were packed.

The answer keys are now the fixtures. To add or refresh a native key, capture it
with the OpenStudio 3.10 / Ruby 3.2.2 harnesses in `scripts/capture/` and adapt
the matching extractor here. `legacy_*.py` compared against the retired
generator and cannot be rerun.

`scripts/migrate/` is the same kind of one-time record. It converted the legacy
package's sampling tables and recipes into `atlas_schedules/data/`.
`scripts/build_sampling_tables.py` (pinned ComStock TSVs) and
`scripts/build_family_recipes.py` (frozen definitions plus prototype geometry)
built the nine new families; `--check` also reproduces the migrated Retail,
restaurant and sampling data. The office, warehouse, ResStock dwelling,
apartment and fixed recipes remain migrated and are checked by the legacy
answer keys.
