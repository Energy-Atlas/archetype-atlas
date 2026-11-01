# ADR 0054: Export contracts of release 2.3.0 (Program JSON 6.0.0, constructions 5.0.0 / 4.0.0 / source model 2.0.0)

Status: accepted (2026-11-01; owner decisions of the 2026-10-31 review, issues C2, C3, C4, C6, C10, implemented in
stage AT1). The exporters, schemas, tests and guide change together on `main`; exports of releases 2.0.0 to 2.2.0
keep their contracts, exports of release 2.3.0 on take these (`scripts/atlas_contracts.py`, `RELEASES`). There is no
compatibility form: consumers move with the release (BEMGen in stage REL-B).

## 1. Versions

| Export | Before (release 2.2.0) | Release 2.3.0 on | Why a major |
| --- | --- | --- | --- |
| Program JSON | 5.4.0 | **6.0.0** (`schemas/program-json-v6.schema.json`, `urn:archetype-atlas:program-json:6.0.0`) | evidence rows renamed (section 2) |
| Detailed constructions | 4.3.0 | **5.0.0** (`construction-json-v5.schema.json`) | `source.definition_release` renamed, `export_mode` and `source.evidence_view` removed |
| Unified constructions | 3.1.0 | **4.0.0** (`construction-equivalent-v4.schema.json`) | `provenance.detailed_release` renamed |
| Source model constructions | 1.0.0 | **2.0.0** (`construction-source-model-v2.schema.json`) | evidence rows renamed |
| Mass accounting | 1.1.0 | 1.1.0 (unchanged) | – |
| Building services | 1.0.0 | **1.0.1** (same file; `$id` 1.0.1) | a patch, not a major: the release is named by pattern, and a 1.0.0 document still validates |

Each new schema is derived from the one before (`python -m scripts.atlas_exports --schemas`, `--check-schemas`),
so the unchanged rules cannot drift, and each change is a recorded revision (`schemas/revisions.json`,
[schema versioning](../schema-versioning.md), ADR 0056). The schemas of the releases before 2.3.0 (Program JSON
5.1.0 to 5.4.0, constructions 4.x and 3.x, source model constructions 1.0.0) do not change: their release enums
stop at 2.2.0, because 2.3.0 exports the majors above (`atlas_exports.labels`). Within one 2.3.0 export the 5.4.0
and 1.0.0 forms are intermediate steps, validated before they become the published form.

## 2. One evidence shape, every row resolvable in the document (issue C6, review S1-04)

- Every evidence row of every family has the shape constructions already used: `id`, `source_project`,
  `source_revision`, `source_locator` (`<file path>#<locator in the file>`), `source_file_sha256` (null only for an
  atlas record or decision with no file, such as a filling rule or a composition), `original_value`,
  `original_unit`, `transformation`, `extraction_date`, `interpretation_note`, and `source_url` where the file has
  one. Construction rows keep their extra fields (`normalized_unit`, `supporting_source_locators`, …).
- A program's `source.evidence` holds every row the document cites (`evidence_id`, `evidence_ids`,
  `climate_evidence_ids` anywhere outside `source` and `metadata`), sorted by ID, so each citation resolves in the
  document; before, 4,986 citations in source exports resolved to nothing. The source file of a program row is
  resolved from the release glossary into the row (project, revision, path, SHA-256, URL).
- The water-heating stage rows (`conversion_evidence`, `temperature_evidence`, `fuel_evidence`) and the delivery
  policy's `evidence` were already construction-shaped and gain their `id`.
- Source model constructions' rows (program-shaped before) take the shared shape.

Alternative: keep the program shape and add a `source_files` table. Rejected: two shapes would stay, and the
construction rows (several files per row, IP unit maps) do not fit the program shape.

## 3. Status and reason beside every value that can be null (issue C2, review S1-07, S2-05, S2-06, S2-08, S3-09)

- **Loads** (`loads`, shared-service loads, water-heating draws) carry `status`: `known` (the source value, a source
  zero included), `unknown` (value null; `reason`, and `reason_id` where the record has one) or `filled` (filled
  version; `filling` with the stored rules, basis and evidence IDs); and `evidence_id`, the record's evidence of the
  value. The filled version's `metadata.absent_demands` entries carry the same fields.
- **`nulls`**, required: the meaning of every null outside `metadata`, `schedules` and `source`, keyed by JSON
  pointer: `unknown` (the source does not give it), `none` (known: there is none) or `not_applicable` (the field
  does not apply), with the reason and its ID where the record has one. The meanings come from one table,
  `atlas_contracts.NULLS`, which the exporter applies (a null with no row stops the export) and the consumer guide
  prints ([Program JSON guide](../../website/content/guides/program-json.md#nulls-and-zeros)).
- **Zeros.** A known 0 is a value: a source zero (`known`) or an accepted absence (`filled`, rule
  `accepted_absence`, ADR 0053 section 3). The filled version moves zero loads to `metadata.absent_demands`.
- **Hot water by family** (S2-06). DOE Ref and IECC programs carry hot water as a program load (0 where the source
  zone has no draw). 90.1 programs carry it only where openstudio-standards assigns a draw to the space type. A 90.1
  program without a hot-water load is not a known zero: the folder's `water.json` records whether its space type has
  no local draw, an unknown assignment or a share of a building draw (served by the water services), and a program
  with no `water.json` entry (mostly construction-only) has unknown hot water. This is stated in the guide; the
  records do not change.
- **Conditioning by family** (S2-08). IECC source programs state `parameters.conditioning`; 90.1 and DOE Ref
  programs state it only where a filling sets it, and otherwise the setpoint schedules imply it; `nulls` says so for
  `controls.heating_enabled` and `cooling_enabled`.

## 4. The atlas release in construction exports (issue C4, review S1-05)

- `release` (`atlas-release-<version>`, required) names the atlas release in detailed, unified and (already)
  source model constructions, as `source.release` does in Program JSON.
- The old labels were the construction deliveries, not the atlas release: detailed `source.definition_release`
  (`v0.1.1`) is `source.construction_definition_release`; unified `provenance.detailed_release` (`v2.2.0`, a literal
  of `construction_equivalent_export.py` naming the construction delivery 2.2.0 of 2026-10-15) is
  `provenance.construction_delivery_release`. The values are kept as history.
- The retired `export_mode` (`source_ready`) and `source.evidence_view` (`source`) leave detailed constructions, as
  they left Program JSON in 5.0.0.

## 5. Dwelling window ratios in `fenestration` (issue C10, review S1-09)

A code-prototype dwelling whose window ratios do not depend on its context already had `fenestration`. The 14 whose
ratios depend on foundation and climate (IECC single-family) kept them only in `metadata.fenestration`, which no
consumer reads. Program JSON 6.0.0 gives them `fenestration: {basis, variants: [{applies_with, wwr, roof,
evidence_id, model_count}]}`, a second form of `fenestration` that a consumer selects by context as it selects the
dwelling's loads; `metadata.fenestration` is gone.

## 6. One vocabulary through a normative mapping table (issue C3, review S1-03, S1-08, S1-12)

The layers keep their spellings, because changing them would move every record ID (records), or change the
generator's contracts (generation.json and bundle, stage AT3). The mapping is normative instead:
[`schemas/vocabulary-v1.json`](../../schemas/vocabulary-v1.json) lists, per concept, the spelling of each layer:

- units: fraction `dimensionless`/`1` (records), `1` (exports), `fraction` (generation, bundle); temperature `C`
  (records, generation, bundle), `degC` (exports); and the other units, which agree;
- field names: `thermal_effects.to_return_air` (records, bundle) and `heat_fractions.return_air` (exports,
  generation); `units`/`unit`; `time_resolution_minutes`/`timestep_minutes`; `quantity`/`type` + `end_use`; rule
  dates; the filled view (`filling`, `filled`, the frozen `__reviewed` configuration suffix);
- climate zones: `4A` (Program JSON keys and construction `source.climate`), `4-a` (construction context keys and
  IDs), the request's IECC 2004 enum with `7AK`/`8AK`, and the residential `applies_with.climate` axis, with the
  conversions.

`tests/test_atlas_contracts.py` requires every unit spelling of the release records, `generation.json` and the
exports to be in the table.

## 7. What a consumer changes

- Read `schema_version` 6.0.0 / 5.0.0 / 4.0.0 / 2.0.0 and embed the new schemas.
- Program JSON: evidence rows by their new field names (`source_locator`, `source_file_sha256`, `interpretation_note`;
  `source_file_id` and `locator` are gone); resolve any `evidence_id` in `source.evidence`; read `status` on loads and
  `nulls` for any null; read `fenestration.variants` where `fenestration.wwr` is absent.
- Constructions: read `release`; the renamed provenance labels; no `export_mode`.
- IDs of release 2.3.0 differ from 2.2.0 where ADR 0053 section 5 says; the delta's ID map translates them.
