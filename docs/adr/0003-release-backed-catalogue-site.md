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
deployment uses an explicit workflow dispatch or a push to the default branch.
Feature branches build without automatically replacing the public site.

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
