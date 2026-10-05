# ADR 0003: Release-backed static catalogue

Date: 2026-10-03. Status: accepted for implementation.

The site is an inspection and discovery view of frozen releases. It must not
create scientific inputs or imply complete simulation configurations.

Generate MkDocs documents into ignored `build/site-docs/`, using verified
`data/releases/v*/manifest.json` snapshots. Curated reader guides and browser
assets live in `website/`. Canonical records, schemas and release files remain
unchanged. Every published release gets stable release-prefixed record URLs.

Catalogue axes are presentation metadata, not a schema migration. Climate values
mean directly reported context for residential recipes or conditional envelope
applicability; missing climate labels are explicitly unspecified. Building
overviews do not invent climate combinations. Shared schedule context is inferred
only through actual record references. Display metadata is never exported as a
replacement for canonical records.

The browser uses small indexed metadata, paginated results and lazy schedule
payloads. Static axis tables and record pages remain usable without JavaScript.
Plots use pinned local Plotly assets with notices and locked SHA-256 retrieval.
Schedule selection mirrors the atlas inspection helper (last matching specific
rule, then default), including wrapped seasons and the documented DummySmrDsn
interpretation. It is not an annual simulation calendar.

MkDocs/Material and dependencies are pinned. CI builds and verifies an artifact;
deployment uses an explicit workflow dispatch or a push to the default branch
or designated publisher branch feat/catalogue-site. Other feature branches build
without automatically replacing the public site.

Original site code/documentation retains the repository's unlicensed status.
Upstream data and dependency notices are retained in the generated downloads.

## Implementation ledger

- Authorization: the user requested autonomous implementation on a separate
  branch. Branch `feat/catalogue-site` starts at v0.2.0 and includes the content
  plan. Work proceeds in the existing checkout; no extra worktree is needed.
- Pre-flight interfaces: verified releases -> generator -> canonical URLs and
  browser metadata -> filters/explorer -> MkDocs output -> link/browser checks
  -> Pages artifact. The content plan defines these interfaces consistently.
- Ruling: retain the content plan as a design guide rather than rewriting it as
  a detailed implementation transcript. This ADR records implementation choices
  and verification. Cost if wrong: additional documentation work only.
- Task 1: verified release loader, pilot/full generator and static provenance.
- Task 2: catalogue filters, source-faithful schedules and browser plots.
- Task 3: reader guides, pinned build, Pages workflow and verification.
- Task 1 complete: the Medium Office pilot generated 114 linked entries and
  retained SI values, original field evidence, nulls and unresolved residential
  profiles. Generator tests pass, including release tampering, inert source
  text, frozen-data preservation, exact snapshot archive bytes and output guards.
- Task 2 complete: browser interaction checks pass on the pilot. Six Node
  tests cover filtering, schedule precedence, wrapped seasons, holidays,
  design days and thermostat diagnostics. All 39,830 sampled selections across
  all 569 v0.2.0 schedules agree with the canonical Python inspector.
- Ruling: use static directory URLs and local browser assets without instant
  navigation. This avoids stale explorer state on navigation. Cost if wrong:
  full-page navigation rather than an optional client-navigation optimization.
- Ruling: distribute Markdown-bearing frozen snapshots as a deterministic ZIP,
  with direct JSON/CSV downloads, because MkDocs renders Markdown into HTML.
  Cost if wrong: readers need to unpack the ZIP to verify the complete snapshot.
- Task 3 complete: strict full MkDocs build, all internal links/fragments/assets,
  real Chromium checks and 30,180-file byte reproducibility passed. Linux GitHub
  Actions also built and uploaded the tested artifact successfully.
- Final review: a fresh read-only reviewer found three Important defects and no
  Critical or Minor defects. See docs/site-review.md for reproductions and fixes.
- Final: fixed shared-ID schedule role loss — real Hospital profile/CSV/zero-
  deadband browser regression RED→GREEN; bindings are distinct from record cache.
- Final: fixed fabricated combined filter associations — exact-reference-pair
  Python/Node regressions RED→GREEN; no Cartesian association is inferred.
- Final: fixed stale asynchronous plot append — delayed Plotly browser regression
  RED (five mixed charts) → GREEN (three current charts).
- Final: Ruling: annual calendars, simulation generation and automatic gap
  resolution remain outside this presentation. The atlas's explicit research
  boundaries govern these operations. Cost if wrong: additional downstream work.
- Final: Ruling: preserve frozen extraction/licensing evidence without claiming
  the presentation review re-established upstream science or reuse eligibility.
  Existing release validation and source-specific notices remain authoritative.
  Cost if wrong: an upstream defect would require a separately versioned correction.
- Final: Ruling: publish the verified artifact from the designated feature branch
  using existing administrative access, because the user authorized autonomous
  implementation of the Pages plan with no human intervention. No research
  branch merge is required. Cost if wrong: revert the publisher policy and Pages
  deployment; canonical data and research branches are unaffected.
- Publication complete: implementation 5fd0d2b passed both GitHub workflows,
  deployed through Pages and passed live HTTPS byte/browser checks. See
  docs/site-publication.md. Initial hosting enabled HTTPS and added only the
  designated publisher branch to the existing deployment allowlist.

## Filter alignment correction, 2026-10-04

User catalogue review identified duplicate climate labels. Normalize presentation
labels such as `ClimateZone 2B` to `2B`, so envelope rules and residential context
can be found with one filter. Preserve source values and climate basis on record
pages. `2` remains distinct from `2A`/`2B`; `7AK`/`8AK` remain distinct regional
source labels. Climate-independent programs and unspecified climate are separate
categories. A shared label does not establish compatibility between climate-zone
editions, applicability sets, source families or code vintages.

Audit all nine filter axes in both frozen release catalogues. Building, program,
template, stock vintage, system, record kind and data status have no verified
equivalent-label duplicates requiring a merge. Source labels have one historical
family alias (`existing_stock_benchmark` versus `existing_stock_benchmark_rules`)
and inconsistent project capitalization. Align these known presentation aliases
to the same existing-stock benchmark family and official project display names.
Keep source-only rows, source-fixture rows, existing-stock rules and code rules
distinct. Do not infer equivalence between differently named program variants.
Mapping entries previously displayed program and system as not applicable even
when their foreign keys identified both. Derive these two presentation facets
from exact references. A mapping without a system keeps an explicit unassigned
label; it does not become proof of absent conditioning.

Per-entry facet aliases preserve old query parameters, and static alias pages
preserve published category URLs. Unknown or ambiguous aliases remain unmatched;
do not silently discard a user's filter. Index generation and browser filtering
have regression tests for combined `2B` coverage, distinct thermal-only sets and
legacy shared links. Research table bytes and all frozen data remain unchanged.

The hot-water guide also clarifies that plant-connected water demand with no
zone reference is valid EnergyPlus modeling. Program beneficiary allocation,
physical fixture location and zone heat/moisture gains are separate questions.
No remaining scientific gap is closed by this presentation correction.
