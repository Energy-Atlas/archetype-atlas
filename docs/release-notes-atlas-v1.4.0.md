# Atlas release 1.4.0 (commercial and residential, delta): release and migration notes

Release 1.4.0 is a delta on release 1.0.0 (ADR 0036), like 1.1.0 to 1.3.0. A reader
resolves one base only, so 1.4.0 holds everything 1.3.0 changed (the DOE reference
reconciliation, the construction-only programs and the IECC commercial family of
[ADR 0040](adr/0040-iecc-commercial-family.md)), byte for byte, and adds the residential tree of [ADR 0038](adr/0038-residential-release-storage.md):

- the 41 ResStock SDR fixture dwellings, migrated unchanged (S12a);
- the IECC residential prototypes, editions 2006 to 2024
  ([ADR 0041](adr/0041-iecc-residential-family.md), S12);
- the manufactured-housing prototypes, HUD Code and DOE Final Rule 2022
  ([ADR 0042](adr/0042-manufactured-housing-family.md), S13).

Release 1.4.0 was rebuilt on release 1.3.0 after both were written (plan section 1):
its entry adds the `iecc_commercial` overlay, and the builder carries 1.4.0 as a
tagged block, as 1.3.0 does, so releases 1.2.0 and 1.3.0 still verify against the
exact builder bytes that wrote them.

## What the release holds

- `data/atlas-releases/v1.4.0/` has 3,743 changed files and lists 371 deleted files.
  It is written and verified by `scripts.atlas_minor_release --release 1.4.0`.
- The commercial files equal release 1.3.0's, except `README.md` and
  `evidence/glossary.json`, which gains the residential texts and source files.
- The residential tree has 25 folders, 73 programs, 59 construction sets with 1,153
  contexts, and 641 annual schedules.

| Folder | Programs | Construction sets (contexts) |
| --- | --- | --- |
| `residential/resstock-sdr/<building-type>/` (7 types) | 41 dwellings | 41 (one each) |
| `residential/iecc-<edition>/single-family/` (7) | 2 per edition (gas, electric appliances) | 1 per edition (76) |
| `residential/iecc-<edition>/multifamily/` (7) | 2 per edition, per dwelling unit | 1 per edition (72) |
| `residential/hud-code/{single-section,multi-section}/` | 1 each | 1 each (19) |
| `residential/doe-final-rule/{single-section,multi-section}/` | 1 each (tier 1, tier 2) | 1 each (19) |

## ResStock dwellings (S12a)

- One program per dwelling, ID from climate, vintage, floor-area bin and source
  building (`resstock-sdr.single-family-detached.5a-pre1940-2000-2499ft2-b101526.<h6>`).
- Annual series in `schedules/<program-id>.json`, value arrays stored once per
  folder. ResStock dwellings have no ruleset schedules, so their folders have no
  `schedules.json`.
- Fillings move unchanged: the recovered magnitudes, controls and fixed background
  schedules of `data/program-inputs/residential-v1.json`, citing the dwelling's
  resolution rows (`evidence/residential/resstock-sdr/resolutions.json`).
- One construction set per dwelling with one context. Six dwellings with labels
  7AK or 8AK had two identical expanded contexts (A and B); the A document is kept.
- Multifamily and attached dwellings carry their building context (the source's
  geometry options); apartments cite the commercial apartment folders.

## Code prototypes (S12, S13)

- Extracted offline from the pinned IDFs into `data/program-inputs/` (each file
  under 25 MB): `iecc-residential-<edition>.json` from 4,144 models, and
  `manufactured-housing.json` from 304 models (CompleteSet checked identical).
- Program entries that hold only for some climate codes, foundations, locations or
  heating systems carry `applies_with`. Examples: the heated basement's lighting and
  adjustment loads, the 1AWHTS unconditioned zone's services, IECC 2024's appliance
  levels and draw schedules by heating system.
- `IECC_Adj` loads have `role: reference_design_adjustment`; every load has its host
  zone. Multifamily is one per-unit program with its building context.
- Construction contexts: IECC climate code × foundation; manufactured housing per
  location, with the five 3A cities as sub-contexts. Each holds assemblies by surface
  class, windows, doors, internal mass, window shading control and the source
  infiltration (AirflowNetwork leakage or effective leakage area).
- Systems (HVAC, water heaters, solar water heating) are not stored.
- Gap: the manufactured-housing set has no existing-building category.

## Exports

- **Program JSON 5.3.0** (`schemas/program-json-v5.3.schema.json`), an additive minor
  of 5.2.0 (IECC commercial, ADR 0040) for dwelling programs: a `dwelling` block,
  `host_zone`, `role` and `applies_with` on loads.
  - ResStock: `source` and `filled`, from the frozen v3 and v4 exporters.
  - Code prototypes: `source` only (complete models; the filled version needs water
    heaters). `scripts.prototype_dwellings.document(..., context=...)` resolves the
    entries for one climate code, foundation or location and heating system.
- **Source model constructions 1.0.0** (`schemas/construction-source-model-v1.schema.json`)
  for one context of an IDF-derived construction set. ResStock sets export as
  constructions 4.2.0 / 3.1.0, like the commercial sets of 1.3.0 and 1.4.0.
- Commercial programs of 1.4.0 export as Program JSON 5.2.0, as in 1.3.0, and their
  detailed construction sets as 4.2.0; both now also accept `atlas-release-1.4.0`.

```
python -m scripts.atlas_exports --release 1.4.0 --program <id> --version source
python -m scripts.atlas_exports --release 1.4.0 --construction <set id> --context 4-a.slab
```

## Verify

```
python -m scripts.atlas_minor_release --release 1.4.0 --verify
python -m scripts.atlas_minor_release --release 1.4.0 --check
python -m scripts.atlas_exports --check-schemas
python -m unittest tests.test_residential_storage tests.test_residential_release
ATLAS_PROTOTYPE_ROOT=<extracted PNNL models> python -m unittest tests.test_prototype_answer_keys
```

The extraction is reproduced from the IDFs with
`python -m scripts.iecc_residential --idf-root <dir>/residential` and
`python -m scripts.manufactured_housing --idf-root <dir>/manufactured-housing`.

## Migration notes

- No commercial file changes meaning. Readers that list programs under
  `commercial/` are unaffected; residential programs live under `residential/` in a
  dwelling shape (ADR 0038, ADR 0041 section 2).
- The builder carries release 1.4.0 as a tagged block after the 1.3.0 block. `--verify`
  of an earlier release strips the blocks of later releases before comparing the
  builder's digest (ADR 0040), so every release still verifies against the exact
  builder bytes that wrote it.

## Open decisions

None for this release. The agent decisions are listed in ADR 0041 section 4 and
ADR 0042 section 4.
