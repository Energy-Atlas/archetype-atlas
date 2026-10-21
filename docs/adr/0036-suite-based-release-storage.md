# ADR 0036: Suite-based release storage and a lighter site

Status: accepted (2026-10-21, user decisions). Resolves
[roadmap item 5](../roadmap.md#5-discuss-a-lighter-site-and-decoupled-generation),
which is no longer deferred behind BEMGen testing. Amends ADR 0003 (no-JavaScript
reading applies to suite pages only) and ADR 0011 (one JSON store). Replaces the
source/reviewed overlay records of the [definition contract](../definition-contract.md).
Residential (ResStock) storage is deferred and stays frozen meanwhile.

## Context

Measured on `main` at `d1b58aa` with the foundation branch rebased onto it:

- A checkout is 1.2 GB, of which 1.1 GB is 2,776 committed JSON files; the whole
  history of `main` packs to 65 MB. Git already removes most repetition in
  storage; the cost is checkout size, CI parse time, the 50/100 MB per-file
  limits and site payloads.
- 61% of the minified JSON repeats content found elsewhere: 251 MB of whole files
  copied between versions, records carried forward unchanged, and sub-objects
  embedded in every record (rule-ID lists, evidence, layer properties).
- The site has 79,316 HTML pages and about 220k files (677 MB), mostly
  provenance and evidence pages; `json/` and `delivery/v2` are two overlapping
  content-addressed stores. CI takes about 88 minutes, dominated by one serial
  Windows job.
- 902 of 1,900 programs are reviewed twins of a source record. The twin differs
  only where a resolution fills a gap: a median of one load in five.

## Decision

### 1. What Git holds

Release data (frozen, checksummed, cited) is committed. Site output (`json/`,
`delivery/`, record pages) is not: it is a pure function of the release and the
scripts. CI caches generated site input under a digest of its inputs; a stale or
mismatched output still fails `site-manifest.json` verification.

### 2. Release layout

New releases live in `data/atlas-releases/vX.Y.Z/`. A major version is a full
snapshot; a minor version is a delta that holds only changed files, with
`manifest.json` naming `base_release` and that base manifest's SHA-256, replacing
whole files and listing deletions. A reader never resolves more than one base.

```
data/atlas-releases/v1.0.0/
  manifest.json  README.md  LICENSE  notices/  schemas/  sources/
  commercial/
    <template>/
      library/            shared within the template (sections 5 and 6)
      <building-type>/
        schedules.json
        programs/source/<id>.json
        programs/department/<id>.json
        programs/general/<id>.json
        constructions/<id>.json
        systems.json
        services.json
  residential/            deferred; same pattern
  evidence/
    glossary.json
    commercial/<template>/<building-type>.json
    commercial/<template>/library.json
```

`commercial/` and `residential/` stay as the top split even though a template
implies its provenance. Folder and file names use lowercase slugs
(`90.1-2019` becomes `90-1-2019`).

### 3. Programs

One file per program. Aggregation mode is a folder: SourcePrograms (`source/`),
DepartmentMixes (`department/`) and GeneralMix (`general/`). A mix holds
`members: [{program_id, area_share, evidence}]` and never embeds member loads; the
mixing policy keeps every member in the same folder. Mixed schedules are stored
and marked derived; CI checks them against the area-weighted members. The
generator recipe is part of the program file, which retires the separate recipe
tree and the paired `__source`/`__reviewed` generator configurations. The
`compositions` table disappears into the mix files.

### 4. Values, fillings and the two exports

A program is one record; there are no source/reviewed twins.

- **Actual values** are what the source states, including values the source
  implies as zero (`source_zero`: 239 commercial rows, e.g. a complete water path
  with no fixture draw). They are stored as known values with their evidence.
- **Fillings** are stored inline on the field they fill, with value, rule, basis
  and evidence: researcher assumptions (`research_assumption`, 1,519 commercial
  rows, of which 1,426 are the approved gas-equipment absence) and values from
  executing upstream code (`executed_upstream`, 19 rows). Every commercial
  filling sets an unknown to zero or off.
- **Unresolved fields** keep an explicit null with a reason ID (313 fields).
- Rule and reason texts live once in the evidence glossary.

Two consumer exports ship: **source-backed** (actual values only) and **filled**
(actual values plus fillings), each filling tagged with rule and basis. The site
shows both; BEMGen consumes the filled export. Mixes are stored in filled form and
recomputed from members for the source-backed export.

### 5. Schedules

One schedules table per template × building type folder, with a `days` section
(each distinct 24-value profile once) and a `schedules` section whose calendar
rules reference day IDs. There are no shared schedules across folders: a schedule
used by several building types is copied into each and may then be edited
independently. Measured cost for commercial schedules: 3.1 MB in 83 tables
against 1.5 MB per building type, against 12.2 MB today.

Always-zero placeholder schedules become `{"constant": 0}` on the slot. Schedules
no program, service or system uses move to source evidence when they document a
source's inventory and are otherwise dropped.

### 6. Constructions and systems

Each construction set (suite) is one file in its folder, holding its contexts,
detailed configurations, unified component sets, mass-accounting contracts and
foundation extensions; all of these are local to one folder. The template
`library/` holds what is shared between building types and never across
templates (sizes per template vs copied into every folder):

| Library table | Per template | Per folder copies |
| --- | --- | --- |
| Detailed assemblies | 3.0 MB | 17.9 MB |
| Materials | 0.7 MB | 6.7 MB |
| Unified assemblies | 1.8 MB | 9.8 MB |
| Foundation assemblies and materials | 0.6 MB | 0.7 MB |
| HVAC components, curves and rules | 14.3 MB | 27.4 MB |

The HVAC row covers the 3,281 components systems reach; 707 of them, mostly
performance curves and rules, are shared between building types and go to the
library, the rest stay with their systems. HVAC systems, services, water reporting
and completion records are local to their folder. The definition-release `constructions` and
`materials` tables are superseded by the combined construction suite.

### 7. Evidence

Evidence lives in its own tree that mirrors the record tree, never inside record
folders: one file per template × building type for program and system evidence
(median 28 KB, largest 393 KB, 32 KB gzipped) and one per template for library
evidence. `evidence/glossary.json` holds source files, interpretation and
transformation texts, filling rules and unresolved reasons once (30 interpretation
texts and 31 transformations currently repeat 7.2 MB). Construction selector
receipts and the coverage report move into the evidence tree. A shared evidence
record (40 of 15,754 program-cited records) is copied like a cross-type schedule.

### 8. Identity and format

- **Readable IDs** for programs, schedules, construction sets, assemblies and
  materials: `<template>.<building-type>.<origin>.<h6>` (library records omit the
  building type), where `h6` is the first
  six hex digits of the SHA-256 of the record's canonical content, name excluded.
  An edit yields a new ID; any clash fails validation. Evidence keeps hash IDs.
- **Old IDs, conventions and schemas retire** without a compatibility map.
  Documentation is preserved and each schema change is described in the docs.
- **Canonical JSON:** UTF-8, LF, sorted keys, shortest round-trip floats. Suite
  files are indented by two spaces; tables hold one record per line sorted by ID.
  No file exceeds 25 MB.

### 9. Consumer contracts

The new layout publishes new majors: Program JSON 5.0.0 (with water heating folded
in from the opt-in v4) and detailed/unified construction JSON 4.0.0/3.0.0. The
exporter resolves every reference into complete standalone documents, so
consumers never see library or evidence references. BEMGen component changes are
deferred.

### 10. Site

- One static page per suite: about 1,175 (998 programs once the twins merge, plus
  177 construction sets). These read without JavaScript, appear in search and
  keep stable URLs, with version and context in the query string
  (`?version=filled&climate=4A`).
- Dependent objects (schedules, assemblies, materials, evidence) render inside
  their suite page with anchors.
- One viewer page, `view/?id=<readable id>`, serves direct links to any dependent
  object; it needs JavaScript. GitHub Pages ignores query strings, and the site
  already keeps state this way (`website/assets/construction.js`,
  `website/assets/definition.js`).
- `json/` and `delivery/v2` merge into one content-addressed store.

### 11. Migration and CI

Frozen release folders under `data/` leave the checkout once the first new release
verifies; they remain in history and are tagged. The first release is
`data/atlas-releases/v1.0.0`. CI is split into parallel research jobs, Windows runs
only the pinned-producer checks, and the build job no longer repeats release
verification; that change lands as its own pull request.

## Consequences

The checkout shrinks to roughly the new tree, the site to about 1.2k pages, and a
schedule, filling or construction edit touches one folder. Consumers and BEMGen
must move to the new contract majors. Residential data keeps its current form
until its own decision. Each stage is implemented test-first on
`codex/atlas-storage-restructure` and validated before any release.
