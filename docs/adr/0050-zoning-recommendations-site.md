# ADR 0050: Publishing the geometric LOD study's zoning recommendations

Status: accepted (2026-10-29, stage A3 of
`docs/superpowers/plans/2026-10-29-public-release-stages.md`; the owner gave blanket
authority for the stage, so every choice below is an agent decision under the plan and
reversible by the next data drop).

## 1. Context

- The geometric LOD study ("How Much Thermal Zoning Detail Is Enough?", BEMGen
  `docs/plans/2026-10-29-lod-study-run-plan.md`) simulates each DOE prototype at its
  own dimensions with its atlas 2.0.0 programs and 90.1 construction set, zoned every
  room (the reference) and under 24 zoning simplifications (the test sites), and scores
  each test site against its reference with the batch runner's paired metrics. The plan's
  section 9 says the owner publishes the zoning recommendation per program, climate zone
  and vintage on the atlas site, and that the site integration is atlas work.
- BEMGen's `scripts/lod-study/report.py` writes `lod-recommendations.json` (schema
  `lod-recommendations-v1.schema.json`): one entry per prototype × climate zone ×
  vintage × orientation with the atlas program IDs of its program keys, the reference's
  benchmark values, every zoning's metrics and flags, whether it meets a threshold and
  which limits it misses, and the coarsest zonings that meet it; `by_program` indexes
  the entries by atlas program ID.
- Stages R3 (the main matrix, 264 cells) and R4 (the heat-transfer sub-study, 22 cells)
  ran on 2026-10-29 (D-193). R5 (serial timing) and R6 (the report) are pending.
- The site is generated from one release by `scripts/suite_site.py` (ADR 0043) and
  cached in CI under a digest of its inputs.

## 2. Decisions

1. **A versioned data drop in the repository.** `data/lod-recommendations/v1/` holds
   `lod-recommendations.json` (R3), `lod-recommendations-ht.json` (R4) and
   `provenance.json`. The two recommendation files are the report writer's output with
   CRLF line endings normalised to LF; the sidecar records both digests, the BEMGen
   commits (the writer and schema at `b29931c`, the runs' IDF writer at `2ed856c`), the
   suite and run IDs from each report folder's `state.json`, the atlas inputs (release
   2.0.0 at `96a2e928`, filled programs, unified constructions, from the specs' headers),
   EnergyPlus 26.2.0, the threshold, and what is pending. The schema is copied verbatim
   to `schemas/lod-recommendations-v1.schema.json` (BEMGen is MIT) and
   `tests/test_lod_site.py` validates both files against it.
2. **This is drop 1.** A consolidated drop after R5 and R6 replaces the files in place
   with the same layout and bumps `drop` in the sidecar; the loader admits added fields
   (a later timing block, a new reference benchmark, a new zoning metric) and refuses
   another format or major version. A `v2/` folder is for a schema major only.
3. **Pages generated at build time**, like the suite pages (`scripts/lod_site.py`,
   called from `suite_site.generate` before the program pages):
   `zoning/` (the overview: what was measured, the threshold, a prototype table, a tally of
   recommended zonings, status and licence); `zoning/<prototype>/` (one page per
   prototype: a summary row per climate zone × vintage × orientation with the reference
   zone count and annual sensible heating and cooling in kWh/m² of conditioned floor, the
   recommended zoning, its zone count, annual errors, CV(RMSE), NMBE and conditioned-area
   change, ties as further rows, a cell with no zoning meeting the threshold said so; then
   every kept zoning of every cell with its metrics and verdict, failed runs as not
   applicable, duplicates named under the table; then the atlas programs by vintage, linked
   to their catalogue pages); `zoning/heat-transfer/` (the R4 cells with the IWHT and FHT
   switches); `zoning/method/` (what was compared, metrics, threshold, deduplication,
   limits, provenance). No table is hand-written; numbers that appear in prose (failed
   runs, duplicates, zonings per cell) are counted from the files.
4. **Orientation is a row, not aggregated.** The plan leaves aggregation over orientations
   to atlas work; drop 1 shows the two orientations as two rows so the owner sees the
   spread before deciding. A later drop may add an aggregate without changing these rows.
5. **The pages reuse the suite look**: `ea-suite` block, facts, contents, sections, tables,
   the `data-filters` form (climate, vintage, orientation, or prototype) and the JSON copy
   and download buttons over the content-addressed store. The filter script now filters
   rows and sections independently and reads the count's unit from the form, which leaves
   the construction pages as they were. Each catalogue program page the study used gains
   a "Zoning recommendations" fact linking to its prototype's page (from `by_program`).
6. **Navigation.** A "Zoning recommendations" tab lists the overview, the sub-study and
   the method page; the prototype pages are reached from the overview and the program
   pages, like catalogue pages, so a later drop with other prototypes needs no `mkdocs.yml`
   edit. The landing page gains a strip.
7. **Checks and cache.** `data/lod-recommendations` joins `DIGEST_INPUTS` and
   `scripts.lod_site` enters `generator_modules()` through its import, so the CI cache key
   changes with the drop, the schema (`schemas/` was already in) and the generator.
   `site_check` requires every zoning page the manifest names; the manifest records the
   drop, the pages and the cell counts.
8. **Licence.** The drop is original atlas data under CC BY 4.0 (ADR 0048); attribution
   "Archetype Atlas, Energy-Atlas, LOD recommendations drop N". The values derive from
   BEMGen runs of the prototypes' public DOE/PNNL geometry and the atlas's own inputs; no
   upstream notice beyond the release's applies.

## 3. Agent decisions

- **Whole files in the repository (11 MB and 3.5 MB).** *Alternative:* a trimmed copy
  without duplicates or unused metrics. *Reason:* source traceability; the sidecar's
  digest ties the repository file to the writer's output, and consumers get the metrics
  the pages do not show (P99 peaks, load-duration-curve errors, KS distances, temperature
  errors, zone-count and CPU-time ratios).
- **Readable zoning labels** (`Conditioned merge + Single zone building`,
  `Perimeter core 3 m + Stack (IWHT off)`) are derived from the zoning fields by a
  camel-case split, so a simplifier or stacker BEMGen adds later renders without a code
  change; the method page explains the ones known today.
- **Unjudged loads are shown muted, not hidden.** A load whose reference is below
  1 kWh/m² a year is not judged by the threshold, but its metrics are the runner's values
  and stay visible with a title saying why they do not count. The runner's own flags
  (`NearZeroReference`) render as a dotted-underlined value with the flag as its title.
- **Duplicates are listed, not tabulated.** The 3,323 duplicate test sites of the main
  matrix would triple the tables; each cell names them under a disclosure with the zoning
  they duplicate, so the row count of the metric table matches the report's.
- **No new JavaScript beyond the filter generalisation**; the pages read completely
  without it.

## 4. Consequences

- The site gains 14 pages (the overview, 11 prototypes, the sub-study, the method page)
  and 14 store documents (the three files and one slice per prototype). In drop 1 a
  zoning meets the threshold in 218 of the 264 main cells and 18 of the 22 sub-study
  cells; 24 small-hotel zonings with IWHT off did not run and are shown as not applicable.
- Applying a later drop: copy the writer's three outputs over the files in
  `data/lod-recommendations/v1/`, normalise line endings, update `provenance.json`
  (drop number, commits, suite and run IDs, digests, pending items), run
  `python -m unittest tests.test_lod_site`, then `python -m scripts.suite_site` and
  `python -m mkdocs build --strict`; the CI cache key changes by itself. If the writer's
  schema moves to a new major, copy it beside the old one and raise `MAJOR` in
  `scripts/lod_site.py` with the loader changes the new fields need.
- The threshold on the pages is the one in the files; a drop with another threshold
  changes every page at the next build and nothing else.

## 5. Drop 2 (2026-10-29): the consolidated drop after R5 and R6

Applied per section 4 from BEMGen `38ff521` (the merge of its R6 pull request; D-200 to
D-203), with the files copied from `research/lod-study/results/` rather than from a report
folder, since BEMGen now commits its published results.

- **What changed in the data.** `lod-recommendations.json` is R3's 264 cells unchanged
  (the recommendations are drop 1's) plus the serial costs of the R5 timing pass: a
  `cost` object on the 12 timed references and 206 timed test sites (medians over three
  repeats of processor time, wall clock and peak committed memory, each test site's ratio
  to its reference, the per-site CV) and a top-level `timing` block (the pass, its gate
  verdict, the repeat check, the writer's medians by zoning and by prototype). The file is
  written compact (7.8 MB against 11 MB). `lod-recommendations-ht.json` is R4 written
  again by the fixed writer so that its 24 failed small-hotel sites carry their zoning
  from the suite instead of null (D-203); nothing else differs. The sidecar records
  drop 2, the four BEMGen builds (`2ed856c` runs, `b29931c` timing, `d32fa2a` repeat
  check, `38ff521` writer and schema), every stage with its suite, run and gate verdict,
  the report and methodology paths, the digests (the HT file's `source_sha256` is BEMGen's
  CRLF file, `sha256` the LF copy; the main file needed no normalisation) and an empty
  `pending` list.
- **Schema 1.1.0.** A minor bump that adds optional members only (`timing`, `cost`); the
  copy in `schemas/` is replaced verbatim, `MAJOR` stays `1`, and the loader accepts both
  versions, which `tests/test_lod_site.py` shows with a 1.0.0 and a 1.1.0 document. The
  sub-study file stays a 1.0.0 document.
- **What the pages add**, all generated from the files and shown only when the document
  carries a timing block, so a 1.0.0 drop renders as before: cost columns (CPU, wall and
  memory ratio of the zoning to its reference) in every summary table of the main matrix,
  "not timed" spanning them where a cell was not timed (the medium office and the primary
  school were not among the 12 timed cells); the same columns in the zoning table of each
  timed cell, with the reference's seconds and MiB in its benchmark sentence; a
  "Serial cost" fact per prototype; a "Cost" section on the overview with the pass in
  brief and the writer's medians by prototype and by zoning; a status section saying
  every stage is complete, linking the report, methodology, run plan and results at the
  writer's commit, and tabulating the stages' gate verdicts; on the method page a "Cost
  protocol" section (the R5 protocol, the gate numbers, the repeat check, why costs are
  medians), a "Reading the recommendations" section with the report's two cautions (an
  "off" recommendation in the sub-study is often the deduplicated twin of the both-on
  zoning; "coarsest" counts modelled zones and can exceed the reference's, the restaurant
  in 4A being the case, counted from the file), D-201's "not applicable" wording for the
  failed sites, which are now listed with their zoning, and the extra builds and documents
  under provenance.
- **Agent decisions.** The cost columns stay on every prototype page of a costed drop,
  untimed rows saying so, rather than appearing on the nine timed prototypes only, so the
  tables read alike across pages; the per-cell zoning tables carry them in the timed cells
  only, since 24 rows of "not timed" per untimed cell would say nothing. Ratios are shown
  to three decimals, as the report prints them. The overview's cost tables are the
  writer's own medians, not recomputed. The writer's zoning labels in the timing block are
  re-cased to the pages' labels for a consistent read.

## 6. Amendment (2026-10-29): a robust recommendation across orientations

Open item 10 of the LOD study; the owner approved the rule on the agent's recommendation.
Decision 4 stands (the two orientations stay two rows); this section adds a headline over
each pair, computed at site build.

- **The rule.** For each prototype × climate zone × vintage (a *cell pair*, 132 in drop 2),
  the robust zoning is the coarsest, by the study's coarseness (fewest modelled zones),
  that meets the threshold at both orientations, judged by the writer's own verdict on
  each zoning at each orientation (`meets_threshold`); a duplicate carries the writer's
  "never recommended" verdict and does not qualify. Ties at the fewest zones go to a
  zoning both orientations recommend, else to the first in the study's zoning order
  (simplifier, join pieces, perimeter depth, stacker, IWHT, FHT, the writer's
  deduplication order); tied zonings are named in the row. Where both orientations
  recommend the same zoning it is the robust one by construction. Where no zoning meets
  the threshold at both, the pair says so and names each orientation's own
  recommendation, which stays the closest reading for that orientation. A prototype ×
  climate zone × vintage with one orientation in the file has no pair and no pick; a
  drop with one orientation throughout shows no robust table and says so on the method
  page. Reported beside the pick: the worse (larger magnitude, signed) of the two
  orientations' stored values of each error (annual heating and cooling, CV(RMSE), NMBE,
  conditioned-area change), so the row bounds both orientations; and the cost ratios of
  the robust zoning as the median over the pair's timed sites of that zoning (one site at
  most in drop 2, since only 0° cells were timed), or "not timed".
- **What the data allowed.** The file lists every kept zoning of every cell with its
  metrics and verdict, so the rule compares the zonings themselves at both orientations,
  not only the two recommendations: the full rule applies. Nothing is recomputed from
  hourly data; the generator chooses among the writer's verdicts, takes the worse of two
  stored errors and a median of stored ratios. Resolving a duplicate to the verdict of the
  zoning it duplicates (the same model) was checked at the time and changes no pick in
  drop 2; the simpler reading of the writer's verdict is the one implemented. A later drop
  with more orientations is judged over all of them by the same rule; the robust zoning is
  at least as fine as each orientation's own recommendation, never coarser.
- **Pages.** The overview's prototype table gains a "Robust across orientations (cell
  pairs)" column, its paragraph the pair count, and the tally section a second table
  "Robust across orientations: N of 132 cell pairs" (drop 2: 109 of 132; in 100 of the
  109 the robust zoning is recommended at both orientations, in 38 a tie at the fewest
  zones is named). Each prototype page opens with a "Robust across orientations" section
  (one row per climate zone × vintage, the rule's note, a fact in the header) above the
  per-orientation table; its rows carry `data-across="orientation"` so the orientation
  filter leaves them visible (`suite.js`). The catalogue program fact "Zoning
  recommendations" now reads "<prototype>: robust across orientations in k of m cell
  pairs: <zoning> (n), …" and links the section. The method page gains a "Robust across
  orientations" section (the rule, what the data allows, the limits) and its design
  section no longer calls orientation unaggregated. Each prototype's stored JSON slice
  carries a `robust` block (the rule, a `computed_by` label naming the generator, one
  record per pair with the pick's site names, the orientation each worst value came from
  and the cost); the writer's own files in the store are unchanged. The manifest records
  `cell_pairs` and `robust_pairs`.
- **Tests.** `tests/test_lod_site.py` checks the rule on synthetic cells (the same pick at
  both orientations, different picks with a common coarser one, none in common, a missing
  orientation, ties and duplicates, failed sites and unknown zone counts, the cost median),
  every page element and the JSON block on the drop, the 109 of 132 tally with the
  invariants above, and a one-orientation drop.

## 7. Drop 3 (2026-11-01): schema 1.2.0, refused zonings, the reference's bound and the R4 rerun

Applied per section 4 from BEMGen `8d2e3bd` (stage LOD1, D-219 to D-224). The files are copied byte for byte,
since BEMGen writes LF, and BEMGen's own `provenance.json` is kept beside the sidecar as
`bemgen-provenance.json`. What the pages change is in [ADR 0059](0059-release-2-3-0.md) section 6:
- refused zonings (`status` Invalid) are shown as not generated;
- the four cells that are finer than the reference are flagged;
- the robust rule of section 6 takes the reference's zone count as a bound;
- D-201's caution goes, since no R4 run fails (D-224);
- the cost medians are medians of prototype medians (D-222);
- program links follow the site release's IDs.

## 8. Drop 4 (2026-11-02): the study on atlas release 2.4.0 inputs, not timed

Applied per section 4 by stage AT-LOD4, on the owner's approval of 2026-11-02 ("archive the published results; the
new results become a new atlas-site data drop", BEMGen D-261). BEMGen stage LOD2 (D-261 to D-264) ran the study
again at BEMGen `35e8a132` (1.10.0 with the LOD2 inputs) on atlas release 2.4.0 inputs (commit `7c543f5d`,
release manifest `51ce9c9e…`) and moved the drop of 2026-10-29 (drop 3 here, atlas 2.0.0 inputs) unchanged into
`research/lod-study/archive/2026-10-29-atlas-2-0-0/`. The new files come from BEMGen main `dbbd872` (the merge of
its pull request 35).

- **Files.** `research/lod-study/results/lod-recommendations.json` (`76e6f2bb…`), `lod-recommendations-ht.json`
  (`2b452b1d…`) and `provenance.json` (`3a2ebe3e…`, kept as `bemgen-provenance.json`) are copied byte for byte
  into `data/lod-recommendations/v1/`; BEMGen writes LF, so nothing is normalised and `sha256` equals
  `source_sha256`. The schema is unchanged (1.2.0, `adbce622…`), so `schemas/` and `MAJOR` stay. The sidecar
  records drop 4, the merge and run builds, the stages R3 and R4 with their suites, runs and concurrency (16),
  R5 as `pending`, the new report and methodology, the archive folder, the previous drop (`archived`: drop 3,
  its BEMGen commit and digests, which equal BEMGen's `compared_with`), three input notes from D-261 and D-262,
  and one pending item.
- **What changed in the data** (BEMGen D-264). R3: 213 of 264 cells with a recommendation (214 in drop 3); the
  recommendation changed in 36 cells, one gained (the supermarket 5A 90.1-2019 at 45°), two lost (the
  stand-alone retail 4A 90.1-2019); the four restaurant 4A cells are still finer than the reference. R4: 18 of
  22, no failed run, no rerun stage. Robust across orientations: 106 of 132 pairs (107 in drop 3). The causes
  are in the inputs: the retail's core and front keyed to their own programs (D-246), the source skylights
  (D-249, D-252) and the small hotel's halved mechanical-room equipment (D-262).
- **No ID translation.** The study's program IDs are release 2.4.0's, the site release's, so
  `id_translation` (ADR 0059 section 6) returns an empty map and the pages link the IDs as written; a test
  checks that all 235 IDs resolve in the site release and that the map is empty while the two releases agree.
  It stays in place for a later site release.
- **Not timed.** The drop carries no `timing` block and no `cost` (R5 needs an otherwise idle machine, D-263),
  and drop 3's costs belong to other models, so none of them is shown. *Agent decisions:* an untimed drop now
  says so plainly instead of leaving the cost out silently: the overview's kicker and the prototype and
  sub-study kickers read "not timed", the overview keeps a "Cost" section that says the drop is not timed, why,
  and where the archived drop is, each prototype page has a "Serial cost (R5)" fact "not timed", the method
  page's cost protocol and limits say the same with the stages' concurrency from the sidecar (16, no longer a
  hard-coded 20), the metrics paragraph no longer mentions cost columns, and the robust rule's limits say a
  robust row carries no cost. The overview's status lists the pending R5 and links the archived drop; the
  method page's provenance names it as "Previous drop". The prose that described drop 3's timing is now drawn
  from the timing block (the number of timed test cases) or general (the per-cell note), and the heat-transfer
  page names a rerun only where the sidecar records one. The coverage limit no longer names release 2.0.0, and
  the input notes are a limits bullet "Inputs (release 2.4.0)".
- **Tests.** `tests/test_lod_site.py` checks the drop 4 files, digests, pins and counts (213, 106 of 132, the
  restaurant 4A flags, 9 of 18 sub-study cells with an off switch, the sensitivity row), that nothing on any
  zoning page is a cost or a drop 3 timing figure, and what each page says about the untimed drop. The cost
  pages, which drop 4 does not show, keep their tests on a synthetic timed drop built from this one
  (`timed_drop`, made-up costs on two outpatient cells and a timing block of the writer's shape, valid against
  the schema).
- **Going live.** The drop is site data, not a data release: `data/lod-recommendations` is outside every release
  manifest and inside the site digest (section 2, decision 7), so a merge to `main` changes the digest, the
  catalogue workflow builds the full site uncached and deploys it to Pages. No release version changes.
- **Left for later.** When R5 runs on these models, a drop 5 with the timing block brings the cost pages back.
  Some of the timed method prose (the gate's short and long misses, the repeat check) still describes drop 3's
  pass and should be checked against that drop's timing block then.
