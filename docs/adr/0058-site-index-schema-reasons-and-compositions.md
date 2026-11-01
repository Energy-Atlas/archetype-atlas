# ADR 0058: A schema for the site index, reasons beside its nulls, and the composition of every mix

Status: accepted (2026-11-01, stage AT2 of the 2026-10-31 review's fix plan, which the owner approved on 2026-11-01:
the site-index part of issue C1, issue C7, and issue B1 part 3). The choices marked *agent decision* are reversible
by a later site build; no data release, export schema or generator changes. It extends
[ADR 0052](0052-site-index-space-types-and-folders.md) and the store descriptor of
[ADR 0057](0057-site-pages-from-exports.md).

## 1. Context

- `site-manifest.json`, the index BEMGen reads (ADR 0052), had no schema (C1). Its shape was defined only by the
  generator and by `site_check.check_index`.
- Its nulls did not all carry their reason (C7). Every `filled: null` has `filled_reason`, but the 165
  `folders[*].generation: null` had none, and `contexts[*].unified: null` meant two things: no unified
  representation, or the one document already serving both (the 1,112 contexts of the IECC residential and
  manufactured-housing sets in release 2.2.0, every one of the second kind).
- BEMGen's *Mix Programs* component needs one *Program JSON* per member and hand-typed weights (B1). The atlas's 446
  general and department mixes are area-weighted mixes of a prototype's source programs, but the index listed only
  the mix itself. In the exports the members appear as evidence (`source.evidence[].original_value`) under the
  definition IDs generator 3.0.0 used (`program-…`); `definition-map.json` translates those of 119 mixes, the ones
  that had generator recipes. The release records themselves carry each mix's members under their release program
  IDs (`composition.members[].program_id`, with `represented_area_m2`, `weight`, `source_program_id` and
  `source_geometry_file_id`): 446 of 446 mixes, 2,794 members, every member a program of the mix's own folder.

## 2. Decisions

1. **A Draft 2020-12 schema**, `schemas/site-manifest.schema.json` (`urn:archetype-atlas:site-manifest:1.0.0`). The
   index gains `schema_version: "1.0.0"`. `site_check` validates every build against it before its other index
   checks. Readers ignore keys they do not know; a key's meaning changes only with a major version.
2. **Every null beside its reason** (C7), each enforced by the schema:
   - `folders[*].generation: null` carries `generation_reason`, stated by folder class in
     `website/content/templates.json` (ADR 0057 decision 3). A null with no matching class fails the site check.
   - `contexts[*].unified` names the same store file as `detailed` where one document serves both representations
     (*agent decision*: the store path itself says "same document", with no flag to keep in step); it is null only
     where there is no unified representation, and then `unified_reason` gives the exporter's reason.
   - `programs[*].filled: null` keeps `filled_reason`; `contexts[*].detailed: null` keeps `reason`.
3. **`folders[*].compositions`** (B1 part 3): for every general and department mix of the folder, by its program ID,
   `mode` and `members`, each member's `program_id` (the release ID), `represented_area_m2` and `weight`, in the
   record's order. They are read from the release record's `composition.members`, which already holds the release
   IDs, rather than translated from the export evidence: the definition map covers 119 of the 446 mixes. A unit test
   checks that the map's translation of the evidence equals the record's members for every mix it covers (119 of
   119), and `site_check.check_compositions` that each folder lists exactly its mixes, each with its record's members,
   every member a program of the folder and the weights its members' area shares, summing to one. Folders without
   mixes have `{}`. *Agent decision:* the field names are the record's (`program_id`, `represented_area_m2`,
   `weight`), so a reader of the index and a reader of the record read the same words; `source_program_id` and
   `source_geometry_file_id` stay in the record, since a picker needs neither.
4. **`json_sha256` in every store descriptor** (ADR 0057 decision 6), including `folders[*].generation`: the SHA-256
   of the canonical JSON, which the schema documents.
5. **A guide for software** (`guides/site-index.md`) describes the index, the compositions with an example, the store
   and the canonical form, and links the schema.

## 3. Consequences

- BEMGen can build its *Mix Programs* picker from the index alone: pick a folder, list `compositions[<mix>].members`
  with their default weights, and fetch each member's export from `programs[<member>]`.
- BEMGen 1.8.0 reads `generation` descriptors by their `href`, `sha256`, `encoding` and sizes and ignores other keys;
  it does not read `contexts[*].unified`. The new keys change nothing it reads.
- The index grows from 3,319,679 to 3,980,487 bytes for release 2.2.0: 446 compositions with 2,794 members, 165
  generation reasons (IECC commercial 96, construction-only 51, IECC residential 14, manufactured housing 4), the
  1,112 same-document `unified` paths and the `json_sha256` of the 90 generation descriptors.

## 4. Alternatives considered

- **`unified_same_as_detailed: true`** beside a null. *Rejected:* a second field to keep consistent; a reader would
  still need the detailed path to fetch the document.
- **Compositions under `programs[<mix>]`.** *Rejected:* the picker starts from a folder, and the folder entry already
  lists its programs.
- **Translate the evidence through `definition-map.json`.** *Rejected:* it covers 119 of 446 mixes; the record's own
  members are the source and the check proves they agree where both exist.
