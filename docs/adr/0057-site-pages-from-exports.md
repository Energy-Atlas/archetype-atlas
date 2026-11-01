# ADR 0057: Site pages from the exports, generation settings, coverage, current guides and canonical downloads

Status: accepted (2026-11-01, stage AT2 of the 2026-10-31 review's fix plan, which the owner approved on 2026-11-01
for issues D1 to D8). The choices marked *agent decision* are reversible by a later site build; no data release,
export schema or generator changes. It amends [ADR 0043](0043-suite-based-site.md) sections 2.2, 2.4 and 4 (what a
program page renders, what the store descriptor holds, the version switch) and extends
[ADR 0052](0052-site-index-space-types-and-folders.md) with the pages that show a folder's generation settings.
The site index changes are [ADR 0058](0058-site-index-schema-reasons-and-compositions.md).

## 1. Context

The review of 2026-10-31 (subject 3, the website; subject 2, coverage) found the site accurate but its pages partly
misleading or hard to use with release 2.2.0:

- **D1.** Program pages rendered the release record. Its `?version=filled` only outlined the record's `filling`
  blocks, while the filled export applies further resolutions the page never showed: absences as 0, holiday rules
  (`resolved-schedule-…`), mixes split per member, ResStock loads aggregated, water heating, controls and bindings.
- **D2.** The 90 folders' `generation.json` (ADR 0051) was reachable only through `site-manifest.json`.
- **D3.** Every published guide command used `--release 1.4.0`, which the exporter refuses (it reads 2.0.0, 2.1.0 and
  2.2.0); the Program JSON guide stopped at 5.3.0, the construction guide said IECC commercial sets had no unified
  form. Eleven guide sources were not published.
- **D4.** No coverage report for 2.x existed; `docs/coverage.md` (v0.2.0) and the `coverage.md` guide (v0.4.0) did.
- **D5.** Template indexes showed bare slugs; the 41 ResStock dwellings were all "Whole dwelling / source_building_N";
  labels were record keys (`parameters`, `thermal_effects`) where the download has `controls`, `heat_fractions`;
  template and building type were spelled two ways; program pages did not link their construction sets.
- **D6.** With JavaScript, Download saved `JSON.stringify(value, null, 2)`, whose SHA-256 matches nothing published;
  no checksum was printed.
- **D7.** Search covered names and IDs only, cut construction-set climates at 40, and the 12.3 MB index carried the
  template libraries as full text; office construction pages weigh 7.5 to 8.6 MB.
- **D8.** Single-value day profiles put the hour ticks off the canvas; plots had no axis titles; the "filled not
  exported" notice printed a raw program ID, unlinked ADR numbers, and needed JavaScript.

## 2. Decisions

1. **Program pages render the two consumer exports** (*agent decision*). The sections show the source export
   under the download's own keys, each heading naming its key (`Loads <code>loads</code>`). A **Filled export**
   section lists every block the filled export changes, one level down (`site_pages.changes`): for an object, only
   its members that differ or are new. Schedules the exports carry that are not release schedules (resolved
   holiday schedules, water targets) render with the release schedules, from the export's inline profiles, and are
   placed so the viewer finds their IDs. A block whose JSON exceeds 32 kB (a mix's per-member aggregation) is named
   with its size and left to the download. A **Release record** section keeps what no export carries: every
   `filling` block at the field it fills, with its rules, basis and resolutions, and every other record value that
   neither export holds, by its path (`gate`, `derivation`, `source_id` …). A mix's members are a table with their
   represented areas and weights. Rendering is generic, so an export field another stage adds (status and reason
   beside a null, display names) appears without a site change.
   *Reason:* the page is what a modeller checks against the file BEMGen reads; the keys and values must be the
   file's. *Alternative:* rename the view and add a notice (the review's second option). Rejected: it leaves the
   filled values unseen.
2. **Version switch** (*agent decision*). Sections carry `data-view="source"` (a source block the filled export
   replaces) or `data-view="filled"` (the Filled export section and the record's fillings). The page without a
   query shows both; `?version=source` hides the filled view, `?version=filled` the replaced source blocks. Without
   JavaScript everything shows, with headings that say which export each block is; a program without a filled
   export says why in its Filled export section, with the exporter's reason stripped of the record ID and its ADR
   numbers linked (`site_render.prose`, `reason_text`).
3. **Generation settings on folder and program pages.** Every folder page has a *Generation settings* section: the
   download of its `generation.json` (the store descriptor ADR 0052 publishes), a coverage line (programs with a
   block of all, by method; configurations; services), the programs' methods and per-view parameters, each building
   configuration with its own anchor (so the viewer opens it) and its People as occupancy schedule and design
   people, and the services; or the reason the folder has none. Program pages state their method and the
   configuration of each view in one line, or why they are not generated. The reason is the folder's class in
   `scripts.generation_coverage` (stage AT3, ADR 0055): commercial types without a ComStock sampling type, IECC
   commercial apartment buildings, residential code-prototype dwellings, each with its stated reason; a folder whose
   class the generator covers but whose release predates its blocks (the IECC commercial and detailed office folders
   in release 2.2.0, which ADR 0055 derives for release 2.3.0) says so with the release number, and loses the
   sentence once a release carries its blocks. A short guide (`guides/generation-settings.md`) explains the file.
4. **Guides take versions and commands from the release.** Guide sources hold placeholders (`{{ release }}`,
   `{{ releases }}`, `{{ schema:<export kind> }}`, `{{ generator }}`, `{{ generation_schema }}`) that
   `suite_site.write_guides` fills from the build: the release, the releases the exporter reads (`IN_TREE`), the
   schema versions of every export kind it wrote, and the generator the release manifest names. An unknown
   placeholder, or one without a value in the build, fails the build; `site_check.check_guides` fails a built guide
   that names a release the exporter does not read or keeps a placeholder, and a unit test fails a guide source that
   writes a release number into a command. Of the eleven unpublished guide sources, `geometry.md` and
   `lighting-controls.md` are current and are published; `catalogue-names.md` (the retired catalogue's vocabulary),
   `coverage.md` (v0.4.0), the three `data-delivery*.md` (the retired `delivery/v1` interface), `hot-water.md` and
   `residential.md` (links into retired routes, v0.x content), `medium-office.md` (a v0.2.0 walk-through) and
   `schedule-methods.md` (the generator design before ADR 0035 shipped) are deleted; Git history keeps them. Two
   guides are added: generation settings and the site index for software (ADR 0058). The landing page counts the
   guides; a unit test keeps every guide source published and in the navigation.
5. **A coverage page generated from the release** (`coverage/`, `site_pages.coverage_page`), counted from the
   build's own index: per family and template the folders, programs by mode, filled exports, generation folders and
   programs, construction sets, contexts and their unified representation (own, same document as detailed, none),
   and climate zones; then the reasons for every absent filled export, generation setting and unified
   representation, with their counts; then one row per folder. A sampled build says it is partial. `docs/coverage.md`
   and `docs/validation/coverage.json` (v0.2.0) are deleted; `scripts/coverage.py`, the legacy pipeline's gate,
   stays and writes its report under `build/`.
6. **Canonical downloads with their checksum.** The store descriptor gains `json_sha256`, the SHA-256 of the
   canonical JSON bytes (`site_store.canonical`: keys sorted, no insignificant whitespace, UTF-8 without escapes,
   numbers as Python's `json` writes them, no trailing newline). The browser verifies the gzip file's SHA-256, then
   the decompressed bytes' `json_sha256`, and Download saves those bytes unchanged; Copy still puts an indented
   rendering on the clipboard. Every download control prints the release and the SHA-256 of the file it saves.
   `python -m scripts.site_store FILE` prints the canonical SHA-256 of any JSON file, so an export written in another
   layout can be compared. The canonical form is described in the Program JSON and site index guides; BEMGen's
   checksum (review issue B5) follows it in its own stage.
7. **Findability.** Template indexes show each template's records' own label (`90.1-2013`, `HUD Code`), its slug, a
   one-line description of the source and a link to its family guide (`templates.json`, which the site check requires
   for every template). Template and building type read the same on program, construction and folder pages: the
   records' own spelling (`90.1-2013`, `PrimarySchool`), with the folder path beside it. ResStock dwellings carry a
   label from their context (`5A · 1980s · 1500-1999 ft² · building 290025`) as a fact, in the folder table and in
   search. Program pages link their construction sets (the dwelling's own set, or the folder's); construction pages
   link their programs.
8. **Search and weight.** Program summaries add their end uses, load types, units and generation method; construction
   sets list all their climate zones instead of the first 40 labels; template library pages and the glossary are one
   summary entry each instead of full text. A construction page whose per-context fields would render larger than
   1.5 MB (the five generic office sets of release 2.2.0, 7.5 to 8.6 MB before) stores each context's own fields as a
   small store document and renders them in the browser when asked, with the same generic rules; the context table's
   downloads hold the complete documents without JavaScript. *Agent decision:* the threshold keeps every other page
   readable without JavaScript.
9. **Plots.** A one-value day profile reads "Constant 1.0 1 all day" instead of a plot. Hour labels spread over the
   series' length, so 96 quarter-hour values place them like 24 hourly ones. Plots carry axis titles (the hour or
   month, and the unit) and their minimum and maximum.

## 3. Consequences

- Program pages grow: they render the source export and the filled changes instead of the record. The site check's
  1 GB ceiling still holds (section 4).
- The input digest covers the ADR file names the pages link to, so a new ADR rebuilds the site.
- The smoke test checks the new version switch (`data-view`), the canonical download's SHA-256 against the printed
  one, and a filled-absent program's reason without JavaScript.

## 4. Size

Measured on the full local build of release 2.2.0 (2026-11-01; `site_check --require-complete` passed):

| | Before (live 2.2.0 tree) | After |
| --- | --- | --- |
| Program pages (Markdown) | 212.5 MB, 69.7 kB each | 318.9 MB, 104.5 kB each |
| Construction pages | 152.5 MB, largest 8.6 MB, 33 above 1 MB | 116.6 MB, largest 1.3 MB, 2 above 1 MB |
| Store | 261.1 MB, 26,120 files | 266.5 MB, 26,752 files |
| Search index | 12.3 MB | 1.7 MB |
| Built site | (not measured) | 880,274,918 bytes, 3,677 HTML pages; 120 MB under the 1 GB ceiling |

Generation took 21 minutes and `mkdocs build --strict` 18 minutes on the (shared) build machine.
