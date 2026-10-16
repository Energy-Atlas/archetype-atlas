# Unified construction-set implementation plan

> **For agentic workers:** Use superpowers:executing-plans inline. Perform a fresh technical review at completion, then stop for the user's review.

**Goal:** Implement the agreed construction-set schema/exporter and two review examples (steps 1–3 only).

**Architecture:** Transform immutable construction v1 resources into resolved,
self-contained v2 sets. Reuse all physics and provenance; embed source-defined
space overrides in the same building set. Keep a small context index instead of
duplicating the source library across climates.

**Tech Stack:** Python, JSON Schema 2020-12, unittest.

**Spec:** `docs/construction-json-v2-contract.md`; accepted chat decisions.

## Global constraints

- Match Program JSON header/source naming, climate/vintage interpretation and provenance conventions.
- One component census per set; no packages/enclosures, generic required_bindings or deferred_scope in the consumer contract.
- Filters resolve climate/reference; BEMGen owns BEM assignment/geometry/IDF translation.
- Preserve source IDs, variants, exact SI physics, source conditions, fixed ACH and provenance.
- No source/program regeneration, ground/systems, site/CI, publication or merge.
- Work in the existing clean user-selected feature checkout; stop after concrete artifacts are ready for review.

## Review focus

- Generic Office/Any and space-only source sets retain scope and separate reference forms.
- Building sets embed source-selected plenum/space overrides; compatibility lookups do not alter active assignments.
- Residential windows/doors retain parent-wall adjacency and variant/overhang differences.
- Source geometry conditions remain structured and never become guessed materials or implicit zero.
- Standalone evidence closure retains source-layer references; no orphan assembly/material/evidence dependency.

## Task 1: Define the contract and regression expectations

Files: new `schemas/construction-json-v2.schema.json`,
`tests/test_construction_set_export.py`, contract and ADR 0022.
Interface: `validate_set(document)` validates the schema, component rules and resource closure.

- [x] Write failing tests for a unified Medium Office/residential interface, source-compatible headers, forbidden legacy fields and invalid role/reference/context rejection.
- [x] Observe the tests fail before adding the schema/implementation.
- [x] Define a complete schema-controlled component census and structured rule/geometry types.

## Task 2: Implement the context-selected exporter

Files: new `scripts/construction_set_export.py`, `scripts/construction_set_validation.py`,
`scripts/construction_set_geometry.py` (shared source geometry declarations).
Interface: `export_set(catalogue, construction_id, climate_zone, reference_id=None)` returns one validated self-contained construction set.

- [x] Test both source representations, same-set exterior/interior roles, exact ACH, retained physics, source-selected space overrides, residential adjacency/pitch/scaling and unsupported contexts.
- [x] Implement the exporter from frozen v1 and pinned source geometry/source metadata; reuse immutable proof resources.
- [x] Add a compact 224-definition selection index and CLI for explicit selections; no translator or site changes.
- [x] Run focused migration tests and inspect resulting JSON structures.

## Task 3: Produce examples and stop for review

Files: `docs/examples/construction-json-v2/{medium-office,residential,index,review-manifest}.json`.

- [x] Generate Medium Office 2019/4A and source_building_101526/5A, with complete dependency closure and checksum manifest.
- [x] Verify schema/physics/references, exact-byte reproducibility and unchanged frozen inputs.
- [x] Fresh independent technical review; repair substantive findings with regression tests.
- [x] Update ADR/work record. Inspect staged diff and audit before a reversible feature commit; stop for human review, without site/publication work.

## Execution ledger

Baseline `18e58c5`, `feature/json-completion`, clean. Existing feature checkout is
the user-selected workspace; no new worktree needed. Steps 1–3 are already
authorized for unattended execution; skill plan-review prompts do not add a new
approval gate. The only intended pause is final artifact review.

Task 1: complete — failing feature tests observed; standalone schema includes
fixed component targets, structured geometry and Program-compatible headers.
Task 2: complete — all 224 source definitions indexed; both representations use
one selected-set API. First 13 focused tests passed.
Final review: two Important issues and one scope issue originally labeled Minor.
The scope issue is treated as Important because it can mislabel consumer
assignments despite the schema-controlled assignment requirement.
Final fixes: native Attic floor selector/legacy role exception, all mirrored
geometry conventions, and standalone scoped-condition/root consistency checks.
Regression cases were observed failing before fixes; 16 migration tests pass.
Shared geometry declarations prevent exporter/validator rule drift.
Declined review areas (BEM/IDF execution, native recovery, all-context release
completeness and publication) remain outside these authorized steps.

Task 3: complete — Medium Office and residential examples, 224-definition index
and review manifest generated. Final command: python -m unittest
tests.test_construction_set_export tests.test_construction_export — 26/26 pass.
Exact-byte example check and 18 input / 3 artifact hashes pass. Source v1 and
program files remain unchanged. Human review remains the next step; no push,
site integration, publication or translator implementation in this phase.
