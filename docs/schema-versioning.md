# Schema versions and revisions

This policy covers every JSON Schema the repository publishes: the export contracts in `schemas/`
(Program JSON, Construction JSON, building services, …), the release-record schemas in `schemas/`
(`atlas-release-*`, `atlas-definition-map-*`), and the generator contracts in
`atlas_schedules/schemas/` (request, bundle, `generation.json`). It was adopted in
[ADR 0056](adr/0056-release-record-schemas-and-versioning.md) and applies from 2026-11-01; the
history before that date is recorded, not renumbered.

## Versions

A schema has a version `MAJOR.MINOR.PATCH`. It is the last part of the schema's `$id`
(`urn:archetype-atlas:<contract>:<version>`) and, where the documents carry one, the
`schema_version` they state. The file name carries `MAJOR` or `MAJOR.MINOR`
(`program-json-v5.4.schema.json`).

| Change | Class | What happens |
| --- | --- | --- |
| Wording, examples or layout that change neither which documents validate nor what any value means | editorial | same version, new revision |
| A label set that is declared open grows (a release label, an ID pattern, an enum of names), so every earlier document still validates with the same meaning | patch | `PATCH + 1`; the schema admits the `schema_version` of every earlier patch of the same minor |
| A new optional field, or a new enum value with a meaning of its own; every earlier document still validates with the same meaning | minor | `MINOR + 1`, new file and `$id` |
| A field removed or renamed, a field made required, a constraint narrowed, or a change in what an existing field or value means, including a description that states a different meaning | major | `MAJOR + 1`, new file and `$id`, migration notes in the ADR and the release notes |

**No edits in place to a published schema's meaning.** Once a version has been published (in a data
release, a package or on the site), what its documents mean is fixed. A change of meaning, even in a
`description` alone, takes a new version under the table above. Editorial and patch changes may edit
the file of the current version, and each edit is a revision.

Readers dispatch on `MAJOR`, and on `MINOR` for the optional features they use. A reader that embeds a
copy of a schema (BEMGen does) refreshes the copy on a patch or minor without changing its logic, and
can tell which revision it holds from the marker below.

## Revisions

Every published schema carries a revision marker as its top-level `$comment`:

```json
"$comment": "revision 7 (2026-11-01). Versioning: docs/schema-versioning.md; revisions and hashes: schemas/revisions.json."
```

[`schemas/revisions.json`](../schemas/revisions.json) lists every revision of every schema file: number,
date, commit (null for the commit that recorded it), change class, change and the file's SHA-256. Any
change to a schema file's bytes is a new revision:

```text
python -m scripts.schema_revisions --write --change "<what changed>" --class patch
python -m scripts.schema_revisions --check
```

`--write` raises the marker and records the new bytes; `tests/test_release_schemas.py` fails while a
schema differs from its last recorded revision. The
derived export schemas (`python -m scripts.atlas_exports --schemas`) keep their file's marker. Schemas
another project owns (`schemas/lod-recommendations-v1.schema.json`, BEMGen-docs) are recorded by hash
and keep their owner's marker.

## History: Program JSON 5.4.0

`schemas/program-json-v5.4.schema.json` (`urn:archetype-atlas:program-json:5.4.0`) was edited in place
five times after it was created for release 1.5.0, before this policy existed. Revision 7 adds the marker.

| Revision | Commit | Change | Class under this policy |
| --- | --- | --- | --- |
| 1 | `58adf746` | created (release 1.5.0, ADR 0044: `lighting_controls`) | created |
| 2 | `c984cb34` | `source.release` enum gains `atlas-release-1.6.0` | patch |
| 3 | `b8194449` | enum gains `atlas-release-2.0.0` | patch |
| 4 | `72e117e0` | `lighting_controls.daylighting` description: the fractions "hold for the source model geometry" became "are the source model values and are applied as given" (ADR 0046 section 6) | major: a change of stated meaning, made in place |
| 5 | `77ebad7e` | enum gains `atlas-release-2.1.0` | patch |
| 6 | `06db34b9` | the enum becomes the pattern `^atlas-release-\d+\.\d+\.\d+$` (ADR 0051 section 5) | patch |
| 7 | (ADR 0056) | revision marker | editorial |

The four label widenings would each have been a patch version (5.4.1 to 5.4.4) and are not
renumbered: every 5.4.0 document validates under every revision. Revision 4 changed what the daylighting
fractions are said to mean without a new version. The data did not change; the release 2.0.0 decision
(ADR 0046 section 6) is what the description now states. Under this policy that statement would have
needed Program JSON 5.5.0 or 6.0.0; the next change to Program JSON follows the table above.
