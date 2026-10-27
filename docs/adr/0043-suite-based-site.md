# ADR 0043: The suite-based site

Status: accepted for stage S of the plan
`docs/superpowers/plans/2026-10-27-stages-after-release-1-4-0.md` (2026-10-27). S-1 is a
user decision; S-2 to S-9 follow the plan's recommendations and, with the choices the
plan left open, are agent decisions (section 4), reversible before the pull request
merges. Amends [ADR 0036](0036-suite-based-release-storage.md) section 10 (page grain,
URLs, store), [ADR 0003](0003-release-backed-catalogue-site.md) (stable release-prefixed
record URLs) and [ADR 0011](0011-static-query-delivery.md) (one store replaces
`json/` and `delivery/v2`; the query snapshots retire).

## 1. Context

Until this change the site (`scripts/active_site.py`) rendered the frozen definition
release v0.1.1 and construction release v2.0.0: 79,316 pages and about 220k files
(677 MB), with two overlapping content-addressed stores. It never read
`data/atlas-releases`, which now holds releases 1.0.0 to 1.4.0 (ADR 0036, 0037 to 0042).
Release 1.4.0 resolves to 4,875 files: 3,032 programs (2,513 source, 305 department,
141 general, 73 dwelling), 291 construction sets with 6,250 contexts, 255 template ×
building type folders, 9,039 schedules, 12,555 library rows and 70,626 evidence rows.
ADR 0036 section 10 estimated 1,175 suite pages before the IECC and residential families
were added.

## 2. Decision

1. **One release.** The site shows the newest release under `data/atlas-releases`
   (`python -m scripts.suite_site`; `--release` names another), with its number on every
   page. Older releases stay as tags and release folders. Release data is read only
   through `scripts.atlas_exports.Release` and its `dwellings`; the site never parses a
   release on its own.
2. **Pages.** One page per program and per construction set, one folder page per
   template × building type (programs, mixes and their members, construction sets,
   services, systems, components, water-reporting records), one library page per
   template (`template-library/`), an evidence glossary, the catalogue indexes and
   the `view/?id=` viewer.
   The guides stay. Programs render every field of the stored record, with fillings on
   the field they fill, the schedules they use and the evidence they cite, all anchored.
   Construction pages render the fields shared by every context once, then each
   context's own fields and components, and list the assemblies and materials used.
3. **URLs.** `catalogue/<family>/<template>/<building type>/programs/<name>/` and
   `…/constructions/<name>/`, the record ID without its folder prefix and content hash,
   so an edit keeps the URL. Version and context sit in the query string:
   `?version=source|filled`, `?climate=`, `?foundation=`, `?location=`, `?reference=`.
4. **Store.** `store/<sha256>.json.gz`: canonical JSON, gzip with a fixed header, named
   by the SHA-256 of the encoded bytes, with encoded and decoded sizes in every
   descriptor. It holds every program export (source and filled), every construction
   context export (detailed and unified, or source model constructions), every schedule
   and the viewer's ID index packets.
5. **Generic rendering.** Records render generically: objects as definition lists,
   lists of objects as tables, null as an explicit null, IDs as links to their page,
   anchor or the viewer. A field the renderer does not know, such as a later minor's
   optional block, renders without a code change.
6. **Checks and CI.** `scripts.site_check` and `scripts.site_smoke` replace the
   definition-catalogue checks. CI caches `build/site-docs` under a digest of the
   release manifests and every input the generator and MkDocs read
   (`python -m scripts.suite_site --digest`); `site_check --require-complete` rejects a
   cached tree whose recorded digest differs, and a partial build.
7. **Retirement.** `active_site`, `definition_site`, `object_site`, `construction_site`
   (and its refresh, smoke and foundation and equivalent presentation modules),
   `query_v2`, `query_history`, `query_site`, the old `site` generator and its water
   reporting page, `card_preview`, `site_assets`, the old smoke tests and their browser
   scripts, the Plotly asset lock and their tests are removed. `query_delivery` and `query_client` stay: the
   definition release still uses them.

## 3. Consequences

For release 1.4.0 the site has 3,639 HTML pages (79,316 before) and 763,998,924 bytes in
27,826 files (677 MB in about 220k before), of which the store is 237 MB in 24,097 files;
the 1 GB publication ceiling leaves about 236 MB of room.
Every program and construction set of the release has a page and its exports. Old
`definitions/`, `objects/`, `json/` and `delivery/` URLs return the 404 page, which
offers search; ADR 0003's promise of stable release-prefixed record URLs is withdrawn
for them, as ADR 0036 section 8 retired their IDs. Release 1.5.0 (Program JSON 5.4.0,
optional `lighting_controls`) renders without a site change once `atlas_exports`
knows the release. On the build machine generation takes 6.5 minutes on six workers and
`mkdocs build --strict` 7.5 minutes; generation is skipped when the input digest is cached. No deployment happens until the pull requests of
releases 1.2.0 to 1.4.0 and this one are merged.

## 4. Agent decisions

Each entry: decision; alternatives; reason; evidence.

1. **S-2, old URLs: retired without a map.** *Alternatives:* redirect pages for the
   79,316 old URLs; a JSON map from old to new IDs. *Reason:* ADR 0036 section 8 retires
   the old IDs without a compatibility map, and a redirect needs that map. The custom
   404 page (`website/overrides/404.html`) names the retired routes and offers search,
   the catalogue and the viewer. *Evidence:* `site_check` fails on any retired route in
   the output or the search index; the smoke test opens `definitions/old-record/`.
2. **S-3, page grain: one page per program and per set, plus one folder page per
   template × building type and one library page per template.** *Alternatives:* ADR
   0036's 1,175 pages (programs before the new families); pages per context. *Reason:*
   the plan's recommendation; contexts are a query-string switch. Library pages hold the
   canonical anchors of assemblies, materials and performance rules, which several sets
   share. Their URL is `<template>/template-library/`, a name no building-type folder can
   take, and the generator refuses two pages on one path. *Evidence:* release 1.4.0 has 3,032 programs
   and 291 sets: 3,323 suite pages, 255 folder pages, 21 library pages.
3. **Page URLs without the content hash.** *Alternatives:* the full readable ID in the
   URL. *Reason:* ADR 0036 section 10 asks for stable URLs; the hash changes with every
   edit. Two records of a folder that would share a URL keep their hash (none in 1.4.0).
   *Evidence:* `site_release.page_slug`; `tests/test_suite_site.py`.
4. **S-4, filled where only source exists: the source with a notice.** The page offers
   the filled export as absent with the exporter's reason, and `?version=filled` shows
   a notice with that reason above the source record. *Alternative:* hide the switch.
   *Reason:* the plan's recommendation; the reason is the exporter's own message, so it
   cannot drift. *Evidence:* 1,134 IECC commercial and 32 code-prototype dwelling
   programs export the source version only.
5. **Default view: source and fillings together.** Without a query the page shows the
   stored record, which holds the actual values with each filling on its field.
   `?version=source` hides the fillings, `?version=filled` highlights them. *Alternative:*
   default to one version. *Reason:* the stored record is one record (ADR 0036 section 4);
   showing both keeps the page complete without JavaScript.
6. **S-5, annual schedules: monthly and typical-day plots with tables, plus the JSON.**
   No hourly table. *Reason:* the plan's recommendation; 8,760 values per schedule
   would dominate the dwelling pages. *Evidence:* the 41 ResStock dwellings carry
   annual series; `tests/test_suite_site.py` checks the summary.
7. **Plots are inline SVG drawn at build time; Plotly is no longer shipped.**
   *Alternatives:* keep the pinned Plotly bundle and draw in the browser. *Reason:*
   pages read without JavaScript (ADR 0003 as amended by ADR 0036), the plots are
   simple step and bar series, and the build needs no asset download. The interactive
   annual heatmap and calendar preview of the old schedule viewer are dropped, and the
   Plotly asset lock (`website/assets.lock.json`) is removed.
8. **S-6, store transport: ADR 0011's gzip, SHA-256 and declared sizes; the 131,072-byte
   bound applies to packets, not documents.** Exports are stored whole (decoded at most
   16 MB, the old object limit) so a copy is one verified file; the viewer index is
   split into packets of at most 131,072 decoded bytes. *Alternative:* split large
   exports into packets. *Reason:* 26 program exports (ResStock dwellings with annual
   schedules) exceed 131,072 bytes even gzipped (largest 210,169 bytes encoded; up to
   2,282,275 decoded), and splitting would make copying reassemble documents in the
   browser.
9. **Evidence rows render on the program and folder pages that cite them and are
   otherwise served by the viewer.** Construction sets cite about 300 KB of evidence
   per context; their pages link each evidence ID to the viewer, which shows the row's
   JSON. *Alternative:* render construction evidence inline. *Reason:* size; the
   evidence is in every context's JSON. *Evidence:* a medium-office detailed document
   is 0.45 MB, of which 0.30 MB is evidence.
10. **The viewer's home for an object is its first page.** A schedule's home is the
    first program page (by ID) that uses it, else its folder page; assemblies,
    materials and performance rules live on their library page; services, systems and
    components on their folder page; glossary texts on the glossary page. Other pages
    render local copies with their own anchors.
11. **S-7, search: one entry per suite page.** MkDocs search runs over every page; the
    `search_index` hook replaces a suite page's sections with one entry whose text is
    its name, ID, template, building type and kind. The viewer has its own ID index.
    *Reason:* full-text entries of 3,300 record pages would make the index larger than
    the pages it serves.
12. **S-8, climate: the atlas label, filtered by zone.** Contexts show their atlas
    label (`1A-tropical-semi-conditioned`); `?climate=1A` selects every label in zone 1A
    and `?climate=1A-tropical` that label only. Commercial context keys (`4-a`) show as
    `4A`; a key's suffix is the source reference, foundation or location.
13. **S-9: the old generators retire in this pull request**, with their tests and
    browser scripts (section 2, item 7).
14. **The unified representation is exported, not rendered.** A construction page shows
    the detailed representation; the unified one is a JSON export per context. Sets
    whose two exports are the same document (source model constructions) show one.
15. **Worker processes, at most six by default.** Each worker holds the resolved release
    (about 2 GB); 28 workers exhausted 32 GB on the build machine. Results are consumed
    in completion order.

## 5. Open questions

1. **Old URLs.** Should a small map from the most-cited old `definitions/<hash>` URLs to
   their suite pages be published after all (ADR 0003's promise)? The default is no.
2. **Interactive schedule views.** Is the dropped annual heatmap and calendar preview
   needed for rule schedules, or are the rules table and day profiles enough?
3. **Construction evidence on pages.** Should construction pages render their evidence
   inline despite the size (decision 9)?
4. **Size headroom.** The site uses 764 MB of the 1 GB ceiling. The five office
   construction pages (126 contexts each) are 7.5 to 8.5 MB; if release 2.0.0 grows the
   site past the ceiling, those pages could list contexts and leave their fields to the
   JSON. Should that be decided now?
5. **CI time.** A cold generation exports every program and context on the CI runner's
   four cores; if that is too slow for pull requests, the export step could be cached
   per release instead of per input digest.
