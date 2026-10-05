# Finite Schedule Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Inspect and resolve every approved finite schedule group using primary
source rules, retaining explicitly documented unknowns where allocation is absent.

**Architecture:** Extend finite fixed defaults and additive resolution policies.
Use locked source/control/path inventories for commercial decisions, keep
unallocated water services separate, and derive site/coverage from the selected
verified release. Historical snapshots and source nulls remain immutable.

**Tech Stack:** Python, JSON Schema, pinned OpenStudio Ruby for source-phase
inspection, unittest, MkDocs/Plotly/Playwright and existing GitHub Pages workflows.

**Spec:** `docs/superpowers/specs/2026-10-04-schedule-completion-design.md`.

## Global Constraints

- The repository research brief governs provenance, security and release validation.
- EV is excluded from active outputs.
- Preserve every source rule, selector/date/design day/order.
- Keep atlas v0.2.0 and every existing supplement/water snapshot immutable.
- No implicit occupant-based allocation, invented restroom program or duplicated central demand is introduced.
- HVAC equipment unavailability and complete magnitudes/full-model controls remain outside this milestone.
- Parametric generator shipping remains deferred.

## Review Focus

- Missing stochastic columns must not erase separately installed refrigeration.
- Zero occupants must not disable background refrigeration or common-area lights.
- Late HVAC customization or shared controllers must prevent false inactive status.
- Unallocated positive central water demand must prevent blanket program zeros.
- Selecting a historical supplement must use its own coverage/evidence, not current defaults.

---

### Task 1: Lock source-completion evidence and scope

**Files:** Create `sources/completion-evidence-lock.json`,
`docs/adr/0008-reviewed-schedule-completion.md`; modify
`sources/schedule-release-scope.json`, `scripts/schedule_coverage.py`,
`tests/test_schedule_coverage.py`.

**Interfaces:** Source inspection consumes existing atlas IDs and source revisions;
produces locked entries compatible with `scripts.fetch.verify_file(entry, cache)`.
`schedule_coverage.build(data, resolutions, scope, supplement_version)` retains its
selected-release contract and excludes EV from additional assessed end uses.

- [x] Write a failing coverage test: explicit excluded EV never appears in
  assessed/additional missing columns, while exterior lighting remains assessed.
- [x] Run `python -m unittest tests.test_schedule_coverage -v`; observe the expected failure.
- [x] Lock inspected primary files/receipts and document decisions, source-phase
  boundaries and historical preservation. Implement explicit scope filtering.
- [x] Rerun targeted tests; verify all locked source bytes offline and by fresh retrieval.
- [x] Inspect staged diff, run `python -m scripts.audit --staged`, commit a focused unit.

### Task 2: Resolve residential refrigeration, vacancy and exterior lighting

**Files:** Modify `scripts/fixed_background.py`, `scripts/resolve.py`,
`sources/resolution-policy.json`, `schemas/resolution.schema.json`;
create `tests/test_schedule_completion.py` and source-bound review data as needed.

**Interfaces:** `fixed_background.build(cache_root, evidence_lock, names=None)`
defaults to the historical two refrigeration tables; explicit names request new
finite source shapes. `resolve_records(data, policy, profiles, fixed_background,
completion=None)` adds version-gated reviewed applications without changing old
policy behavior. New schema/policy version is 0.4.0.

- [x] Write failing tests for selected positive refrigeration beyond vacant
  records, selected absence, zero-occupant foreground/end-use rules, positive
  occupied exterior lighting and occupied loads blocked from vacancy zeros.
- [x] Run `python -m unittest tests.test_schedule_completion -v`; observe feature failures.
- [x] Extend source shape parsing, installation/zero guards and policy/evidence.
  Verify upstream zero calculations for the three exact vacant fixtures. Add no EV binding.
- [x] Run new and historical resolution tests. Confirm unknown option bindings,
  contradictory positive profiles and temperature coefficients cannot be guessed.
- [x] Stage/inspect/security-audit and commit the independently usable residential unit.

### Task 3: Inspect commercial controls and all water paths

**Files:** Create `scripts/commercial_completion.py`,
`schemas/commercial-completion.schema.json`,
`sources/commercial-completion-policy.json`,
`tests/test_commercial_completion.py`; extend resolution integration where needed.

**Interfaces:** `commercial_completion.build(data=None, lock_path=..., cache_root=...)`
returns source-bound water service components, program assignments/statuses and
19 inspected control decisions. `validate_bundle(path)` checks checksums/schema,
source-derived inventory and non-duplicating assignment/conservation constraints.
`freeze(target)` refuses an existing destination.

- [x] Write failing tests for no-SWH, per-space source assignment/zero, positive
  lumped unallocated demand, unchanged selector/date/order and deduplication.
- [x] Write failing control tests for inactive equipment/empty controllers and
  positive late/shared controllers blocking inactive classifications.
- [x] Run `python -m unittest tests.test_commercial_completion -v`; observe failures.
- [x] Implement branch extraction against locked prototype inputs/code and exact
  model/source inspection receipts. Keep ambiguous services distinct and unknown.
- [x] Verify all affected program/template paths; independently reproduce the
  inspection inventory and interval conservation. Test mutation/tampering guards.
- [x] Stage/inspect/security-audit and commit the reviewed commercial unit.

### Task 4: Freeze releases and update the catalogue

**Files:** Create new immutable completion/supplement directories and release notes;
modify `scripts/site.py`, `scripts/site_smoke.py`, `tests/test_site.py`,
`website/content/guides/coverage.md`, `website/content/guides/hot-water.md`,
`website/content/guides/schedule-methods.md` and CI workflow paths/checks.

**Interfaces:** Supplement v0.4.0 carries reviewed resolutions and source locks;
the independent commercial bundle retains building services/control evidence.
The site attaches existing-program references, supplies appropriate plots and
downloads, and computes coverage using its actual selected overlay.

- [x] Add failing site tests for new fixed/zero profiles, commercial component
  evidence and EV exclusion without altering canonical historical downloads.
- [x] Freeze new snapshots; repeat into ignored directories and compare every
  artifact byte. Reverify all historical snapshots with their own schemas/policies.
- [x] Implement presentation/download integration and current docs, retaining
  original and resolved meanings. Preserve public historical URLs and budget.
- [x] Run full Python/JavaScript suites, source comparison, schema/physical/
  referential/schedule/provenance/security checks, strict build, links and browser.
- [x] Stage/inspect/security-audit and commit; obtain a fresh whole-change review,
  fix material findings with regression tests, then push the publisher branch.
- [x] Wait for hosted validation/deployment, verify served artifact hashes and
  browser behavior, tag verified data and append publication evidence.

## Execution record

Execution is native and autonomous under the user's standing instruction. The
parallel agents investigate independent source domains read-only; implementation
and integration remain in this checkout. The approved design does not promise
zero remaining gaps when the source lacks beneficiary allocation.
