# ADR 0052: Space types and folder generation settings in the site index

Status: accepted (2026-10-30, phase 3a of BEMGen `docs/plans/2026-10-30-atlas-program-picker.md`
section 4.3, "Atlas side", which the owner accepted on 2026-10-30; the choices marked *agent
decision* are reversible by a later site build). It extends the site manifest of
[ADR 0043](0043-suite-based-site.md) and publishes the `generation.json` files of
[ADR 0051](0051-generation-parameters-in-the-release.md) through the site store.

## 1. Context

- BEMGen's DOE program map components (*DOE … Programs*) carry illustrative presets. Phase 3 of
  its atlas program picker fills them from one atlas folder: per DOE program key, the atlas
  program of that space type in the chosen folder, downloaded from the live site and verified.
  To find the programs without downloading every export, BEMGen needs each program's space
  type, building type, folder and mode in one index, and its *Schedule Draw* needs the folder's
  `generation.json` (its *Generator JSON* input).
- `site-manifest.json` already lists every program with its page and export paths. It is
  2.6 MB on the live site for release 2.2.0 (3,051 programs, 255 folders), with the keys
  `construction_sets`, `counts`, `generated_by`, `inputs_sha256`, `kind`, `partial`,
  `programs`, `release`, `release_manifest_sha256` and `zoning`.
- Every commercial program name follows `<space type>_<building type>`: 2,978 of 2,978 in
  release 2.2.0, as in 2.0.0. The 73 residential dwelling names do not (`IECC 2021 Multifamily
  dwelling, electric appliances`; the ResStock dwellings' `Whole dwelling / source_building_…`
  contain an underscore but do not end in their building type).
- Release 2.2.0 holds 90 `generation.json` files (83 commercial, 7 ResStock dwelling folders),
  written with sorted keys. The generator reads them parsed, and its generator view
  (`scripts/build_generator_view.py`) stores them re-serialised as sorted compact JSON.

## 2. Decisions

1. **Program index fields.** Each `programs[<id>]` entry gains `space_type`, `building_type`,
   `folder` and `mode`, written by `scripts/suite_site.py` (`program_index`) from the release
   record:
   - `space_type` is the record's `name` before its last `_` where the name ends in `_` and the
     record's `building_type` (`site_release.space_type`), else an explicit `null`. For every
     commercial program this is the name before its last `_`, since no building type contains
     an underscore. *Agent decision:* the rule requires the building-type suffix rather than
     any underscore, so the ResStock names get `null` and not a fragment of their source label.
   - `building_type` is the record's `building_type` (`MediumOffice`), or `null`.
   - `folder` is the release folder path as the site already keys it: the `release.folders`
     key, which `sample.folders` uses too, with a trailing slash
     (`commercial/90-1-2019/medium-office-detailed/`). *Agent decision:* the existing key, not a
     second spelling without the slash.
   - `mode` is the program's mode: `source`, `department`, `general` or `dwelling`.
2. **A folder index.** A new top-level `folders` object, keyed by the same folder path. Each
   value holds `family`, `template`, `building_type` (the folder's slug, the site's folder
   name, `medium-office-detailed`), `programs` (the folder's program IDs, sorted) and
   `generation`.
3. **`generation.json` in the store.** `generation` is the store descriptor of the folder's
   release-2.2.0 `generation.json`, put in the one content-addressed store like every other
   document (canonical JSON, gzip, ADR 0043), or an explicit `null` where the folder has none
   (165 of 255 folders in 2.2.0: IECC, manufactured housing, the detailed offices and the other
   folders without generation blocks, ADR 0051 section 3). The stored document is the file's
   JSON: verified on all 90 files, it equals the release file parsed, the generator's own read
   (`atlas_schedules.release.Release.generation`) and the generator view's copy, with the same
   key order, since the release files are already key-sorted. Canonical re-serialisation
   therefore changes nothing the generator or BEMGen's `GeneratorRecipes` reads. It does change
   the bytes (compact separators instead of the release file's layout), so the SHA-256 of the
   text that *Schedule Draw* records as provenance is the stored document's, not the release
   file's.
4. **Checks.** `scripts/site_check.py` (`check_index`) compares the index with the release on
   every build: each program has the four fields with the release's building type, folder and
   mode; each commercial program has a non-null `space_type`; a non-null `space_type` + `_` +
   `building_type` rebuilds the record's `name`; each program's folder is indexed and lists it;
   each folder's family, template, building type and program list are the release's; each
   `generation` descriptor verifies (path named by its SHA-256, size, checksum, decoded size)
   and decodes to the release's document, and is null exactly where the release has none. A
   full build must index every folder of the release; a sample (`--sample`) exactly its sampled
   folders; an `--only` preview the folders it includes.
5. **Additive, no data release.** The fields are new keys in an existing JSON document; a
   reader that does not know them ignores them, and no existing key changes. The site is
   rebuilt from the same release 2.2.0, so no data release, export schema or generator change
   is needed. The input digest moves with the generator scripts, so the main push rebuilds
   the site rather than restoring a cached tree.

## 3. Size

The index grows from 2,633,292 to 3,319,679 bytes (+686,387, +26 %; projected from the live
2.2.0 manifest with the new fields, the folder index being 246,361 bytes of it); gzip-compressed,
as Pages serves it, from 764 KB to 830 KB. The store gains 90 small documents (0.8 MB of JSON
before compression).

## 4. Consequences

- BEMGen reads `site-manifest.json` once, picks a folder from `folders`, maps its DOE program
  keys to programs by `space_type`, and downloads the programs' exports and the folder's
  `generation` document, each verified by its descriptor or its store path's SHA-256.
- The space type is derived from the name at build time, not stored in the release; a future
  release whose commercial names leave the `<space type>_<building type>` form fails
  `site_check` before publication.

## 5. Alternatives considered

- **A separate index file** (`program-index.json`). *Rejected:* a second document to fetch and
  keep consistent with the manifest, for about 0.7 MB.
- **Store the release file's bytes unchanged.** *Rejected:* the store holds canonical JSON
  only (ADR 0043); the content is identical and the generator reads parsed JSON.
- **Split space types out of the name by a lookup table.** *Rejected:* the name rule holds for
  every commercial program and the check guards it.
