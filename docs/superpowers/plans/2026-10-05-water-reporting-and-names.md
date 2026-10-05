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

- [ ] Write and run failing tests for reference-floor area, mapping deduplication, service allocation, complete active-program inventory, conservation, and tamper rejection.
- [ ] Implement conservative source-bound reporting rules and inspect the Medium Office pilot.
- [ ] Validate schema and reproduce the new bundle; freeze with dependency manifests, source lock, schema, policy documentation and license.
- [ ] Inspect staged diff, run staged audit, commit logical data/tooling unit.

## Task 2: Site integration and naming

Files: `scripts/site.py`, new focused presentation helper if needed, `scripts/schedule_coverage.py`, site tests, workflows and website guides.

Interfaces: optional `water_reporting` argument in site generation and coverage; common display functions used for building/program labels and their aliases.

- [ ] Write and observe failing tests for operational coverage, program JSON/page/reporting plots and old-name filtering.
- [ ] Integrate bundle downloads and program/shared-service links; publish source-only and operational counts together.
- [ ] Audit names, apply controlled labels and variant-qualified titles, retain old queries/category URLs.
- [ ] Run full Python/JS suites, scientific checks, strict MkDocs, link/size/browser verification.
- [ ] Fresh independent review; fix material findings and rerun affected checks.
- [ ] Inspect staged diff and security audit, commit, publish through the already-authorized branch workflow, verify hosted results.

## Execution ledger

- Initial state: clean `feat/schedule-resolution`, HEAD `cb0aa54`.
- Ruling: continue in existing user-requested separate branch; no additional checkout is needed.
- Ruling: shared references provide operational coverage without pretending a known local assignment. Preserve original 279 source-only gaps.
