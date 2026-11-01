# ADR 0056: JSON Schemas for generation.json, the bundle and the release records; schema versioning

Status: accepted (2026-11-01; review issues C1 and C5 of the 2026-10-31 review, stage AT3). The site
index schema is stage AT2's (ADR 0057 or 0058).

## 1. Context

- **C1 (review S1-02).** Only the consumer exports and the generator request had JSON Schemas. The
  formats BEMGen and third parties read or write next to them had their contracts in ADR prose and in
  hand-written checks on each side: `generation.json` 1.0.0 (ADR 0051 section 3), the bundle 4.0.0
  (`docs/schedule-generator.md#bundle`), and the release records (manifests, `definition-map.json`,
  program records, `schedules.json`, `services.json`). The generator read only the manifest's
  generation version.
- **C5 (review S1-06).** No written rule said what bumps patch, minor or major, and schemas carried no
  revision marker. Program JSON 5.4.0 was edited in place five times under one `$id`, once in meaning.
- Published release manifests are pinned by hash and are not edited; the schemas apply from the next
  release, and the published files must validate as they are.

## 2. Decisions

1. **Schemas** (Draft 2020-12):

   | File | `$id` | Validates |
   | --- | --- | --- |
   | `atlas_schedules/schemas/generation-v1.schema.json` | `urn:archetype-atlas:generation:1.0.0` | each folder's `generation.json`: blocks per method (`comstock_hours` names a configuration; `composition` and `fixed` take none; `resstock_unit` and `resstock_dwelling` their parameter shapes), services, configurations |
   | `atlas_schedules/schemas/bundle-v4.schema.json` | `urn:archetype-atlas:schedule-bundle:4.0.0` | the generator's bundle: release provenance, 8,760-value schedules, owners by kind (`program` names its program and view; services and caller water a service and no view), loads, controls, mixture, operating groups, seeds |
   | `schemas/atlas-release-manifest-v1.schema.json` | `urn:archetype-atlas:atlas-release-manifest:1.0.0` | `manifest.json` of a snapshot (`snapshot_of`) or a delta (`base_release`, `removed`), files with size and SHA-256, inputs, generator pin |
   | `schemas/atlas-definition-map-v1.schema.json` | `urn:archetype-atlas:definition-map:1.0.0` | `definition-map.json` |
   | `schemas/atlas-release-program-v1.schema.json` | `urn:archetype-atlas:atlas-release-program:1.0.0` | program records in three shapes (commercial program or mix, ResStock dwelling, code-prototype dwelling) and the null rule: an unknown load or parameter has a null value, a known load a number |
   | `schemas/atlas-release-schedules-v1.schema.json` | `urn:archetype-atlas:atlas-release-schedules:1.0.0` | a folder's day profiles and schedule rules |
   | `schemas/atlas-release-services-v1.schema.json` | `urn:archetype-atlas:atlas-release-services:1.0.0` | a folder's shared services |

   Every published release validates as written: the 2.0.0, 2.1.0 and 2.2.0 manifests, the 2.2.0
   delta's files and every record of the resolved 2.2.0 (`python -m scripts.release_schemas --all`, 30 s).
   The schemas state what the releases hold; none changes a file or a meaning. The `reviewed` suffix of
   generator 3.0.0's configuration IDs stays admitted.
2. **Where they are checked.**
   - **Generator:** `atlas_schedules.release.check_generation` validates each `generation.json` when it is
     first read (also a document laid over a release in tests), and refuses an invalid one with
     `GeneratorError` code `release` and the path of the first error
     (`/commercial/<template>/<type>/generation.json/programs/<id>/…`). The bundle schema ships with the
     package for consumers; the generator does not validate its own output at run time (ADR 0035: checks in
     tests, not runtime locks).
   - **`scripts/atlas_delta.py`:** building a delta (`--check`, `--write`) validates every delta file of a
     kind with a schema and the manifest (`scripts.release_schemas`); `--check` of 2.1.0 and 2.2.0 passes.
   - **Tests:** `tests/test_release_schemas.py` (every schema is Draft 2020-12; the published manifests
     and deltas; a fixed sample of the 2.2.0 records; the null rule; the generator refusal; the 2.3.0
     manifest inputs), `tests/schedules/test_examples.py` (the example bundles), `tests/test_zone_recipes.py`
     (the new documents and sample bundles). The bundle check in tests leaves the per-value type rule to
     numpy (`tests.schedules.helpers.bundle_errors`), since jsonschema takes seconds per bundle on it.
3. **Not covered.** Construction packages, `systems.json`, `water.json`, `components.json`, evidence and
   `id-map.json` are the writers' internal records; their consumer contracts are the export schemas
   (Construction JSON, building services, Program JSON). They get schemas when a consumer reads them.
4. **Versioning policy:** [docs/schema-versioning.md](../schema-versioning.md). Version `MAJOR.MINOR.PATCH`
   in `$id` and `schema_version`; editorial changes are revisions of the same version; a widened open
   label set is a patch; a new optional field a minor; a removal, a new requirement, a narrowed constraint
   or any change of meaning, including a description's, a major. No edit in place changes a published
   version's meaning.
5. **Revision markers.** Every published schema's top-level `$comment` reads `revision <n> (<date>). …`, and
   `schemas/revisions.json` records every revision of every file (number, date, commit, class, change,
   SHA-256), the committed history read from git. `python -m scripts.schema_revisions --write --change …
   --class …` records an edit; the tests fail while a file differs from its last recorded revision. The
   derived export schemas keep their file's marker (`scripts.atlas_exports.with_marker`); BEMGen-docs'
   `lod-recommendations-v1` keeps its owner's. 50 schemas carry revisions; adding the marker is an
   editorial revision of each.
6. **Program JSON 5.4.0 history** is in the policy document: revisions 2, 3, 5 and 6 were patch-class
   label widenings, revision 4 (`72e117e0`) a change of the daylighting fractions' stated meaning made in
   place, recorded and not renumbered.
7. **The writer pin.** Release 2.2.0's manifest pins `scripts/atlas_delta.py` by SHA-256. Changes for later
   releases therefore go into a tagged block (`# >>> release 2.3.0` … `# <<< release 2.3.0`) before the main
   guard that redefines what it changes; `pinned_writer(release)` strips the blocks of later releases, which
   restores the bytes 2.2.0 pinned, so `--check` of 2.2.0 still reproduces its manifest. This is ADR 0040
   agent decision 17's mechanism. The block holds this ADR's validation, ADR 0055's generation counts over
   base and delta and its coverage statement; stage REL-A adds release 2.3.0 itself (its `CHAIN`, decisions,
   generator pin and files) inside the same block.

## 3. Consequences

- A user who edits or writes a `generation.json`, or parses a bundle in another language, has a contract
  to validate against; a malformed `generation.json` fails at the generator's boundary with its path.
- BEMGen can validate `generation.json` and bundles against the published schemas instead of its
  member-by-member checks, and can tell which revision of an embedded schema it holds. Every schema file
  changed by one line (the marker); no document changes, so BEMGen's embedded Program JSON 5.4.0 copy stays
  valid and can be refreshed at leisure.
- Every later schema edit is a recorded revision with a class; meaning changes take a new version.
