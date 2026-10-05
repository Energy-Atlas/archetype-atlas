# Complete water reporting and catalogue names implementation plan

> For agentic workers: use superpowers:executing-plans task-by-task. User requested autonomous implementation; additional approval handoffs are superseded by that standing instruction.

**Goal:** Deliver the approved water-reporting variant and then align catalogue building/program names.

**Architecture:** A separately frozen Python-built bundle references immutable source/completion/resolution releases. Catalogue presentation reads this bundle and a controlled name vocabulary without rewriting original records.

**Tech Stack:** Python, JSON Schema, unittest, MkDocs, existing browser smoke tests.

**Spec:** `docs/adr/0009-complete-water-reporting-variant.md` and `docs/AGENT_RESEARCH_BRIEF.md`.

## Global constraints

- Original work unlicensed; preserve source licenses and checksums.
- No silent null-to-zero conversions; no fixture-gain assignments from reporting weights.
- Source-only coverage and reporting coverage are separate metrics.
- Existing release contents remain immutable; inspect staged diff and run staged security audit before every commit.
- Work on the existing separate `feat/schedule-resolution` branch.

## Review focus

- Duplicate HVAC mappings must not multiply reference areas or people.
- Missing/invalid geometry or density must retain a shared service rather than invent weights.
- Mixed service temperatures must not become an inferred heating-energy schedule.
- Historical browsing aliases must select the same records after label alignment.
- Numbered/floor/source variants must remain distinguishable even when display spellings align.

## Task 1: Water reporting bundle

Files: create `scripts/water_reporting.py`, `schemas/water-reporting.schema.json`, `tests/test_water_reporting.py`; freeze `data/water-reporting-releases/v0.1.0`.

Interfaces: `build(data=None, completion=None) -> dict`, `validate_packet(packet, data, completion)`, `validate_bundle(path=DEFAULT) -> dict`, `freeze(target=DEFAULT) -> dict`.

- [x] Write and run failing tests for reference-floor area, mapping deduplication, service allocation, complete active-program inventory, conservation, and tamper rejection.
- [x] Implement conservative source-bound reporting rules and inspect the Medium Office pilot.
- [x] Validate schema and reproduce the new bundle; freeze with dependency manifests, source lock, schema, policy documentation and license.
- [x] Inspect staged diff, run staged audit, commit logical data/tooling unit.

## Task 2: Site integration and naming

Files: `scripts/site.py`, new focused presentation helper if needed, `scripts/schedule_coverage.py`, site tests, workflows and website guides.

Interfaces: optional `water_reporting` argument in site generation and coverage; common display functions used for building/program labels and their aliases.

- [x] Write and observe failing tests for operational coverage, program JSON/page/reporting plots and old-name filtering.
- [x] Integrate bundle downloads and program/shared-service links; publish source-only and operational counts together.
- [x] Audit names, apply controlled labels and variant-qualified titles, retain old queries/category URLs.
- [x] Run full Python/JS suites, scientific checks, strict MkDocs, link/size/browser verification.
- [x] Fresh independent review; fix material findings and rerun affected checks.
- [x] Inspect staged diff and security audit, commit, publish through the already-authorized branch workflow, verify hosted results.

## Execution ledger

- Initial state: clean `feat/schedule-resolution`, HEAD `cb0aa54`.
- Ruling: continue in existing user-requested separate branch; no additional checkout is needed.
- Ruling: shared references provide operational coverage without pretending a known local assignment. Preserve original 279 source-only gaps.

- Foundation: `2bd3113`; schema, Medium Office pilot, conservation, source-path completeness, tamper rejection and reproduction verified before freezing.
- Catalogue: `b653d5a`; all 22 building codes and 108 program codes reviewed; original records and variant identities preserved. The independent final review found a legacy compound-search regression, fixed with a failing-then-passing test.
- Local verification: 116 Python tests, ten JavaScript/parity tests, seven final naming/site Python regressions, strict MkDocs, all links/size, Chromium plots/CSV/mobile/no-JS and 33,173 primary-source comparisons passed. Site size: 995,497,562 bytes.
- Publication: branch and annotated `water-reporting-v0.1.0` tag pushed. Hosted scientific run `37281126958` passed 116 tests on each OS and all release/security checks; catalogue run `37281126977` passed strict build, links/browser/size and deployment. Live canonical JSON, complete snapshot inventory and both catalogue indexes match local artifacts; live aliases and reporting CSV passed. Receipt: `docs/validation/water-reporting-v0.1.0.json`. Branch remains unmerged.
