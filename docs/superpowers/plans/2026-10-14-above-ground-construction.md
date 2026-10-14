# Above-ground construction completion plan

> **For agentic workers:** Execute the contract/exporter inline. Use the parallel-agent skill for the independent commercial and residential source recovery domains, and a fresh technical reviewer before delivery.

**Goal:** Complete source recovery, dependency closure and the independent construction schema/exporter with 100% coverage of eligible above-ground inputs.

**Architecture:** Retain frozen v0.1.1 and previous recovery/ACH receipts. Add construction-only recovery sidecars; produce a versioned catalogue with central material/evidence resources and ready assembly/package/enclosure records. Derive the completeness denominator from source closure, not the old extracted subset.

**Tech stack:** Python/jsonschema, pinned Standards/ResStock and OpenStudio Ruby.

**Spec:** `docs/construction-json-v1-contract.md`; ADR 0020; accepted C01/C03–C07 annotations and fixed-ACH decisions.

## Constraints and review focus

- Ground/foundation/basement, foundation-dependent interfaces and all systems are deferred.
- No program regeneration, site build, CI, production deployment or protected-main bypass.
- Source revisions/hashes, original units/values, transformations and notes accompany physical fields.
- Preserve old source IDs/stock distinctions, all missing source selector roles and separate reference variants.
- Check native source setters/adjustments, not just legacy recovery classification. Targets may differ from actual engine values.
- Validate glazing by model; explicit native VT autocalculation is allowed, fabricated optical or mass defaults are not.
- Keep geometry-dependent source operands/rules explicit; reference geometry is not delivered consumer geometry.
- No new agreement inferred from blank H/X comments.

## Task 1: Recover source construction closure

- [x] Write/observe failing source recovery tests before implementation.
- [x] Residential recovery: `scripts/recover_residential_assemblies.py` and `.rb`, `tests/test_residential_assemblies.py`, `data/construction-inputs/residential-assemblies-v1.json`.
- [x] Commercial recovery: `scripts/recover_construction_selectors.py` and optional `.rb`, `tests/test_construction_selectors.py`, `data/construction-inputs/selector-closure-v1.json`.
- [x] Validate pilots and expand only source construction phases; account for every above-ground selector and deferred ground slot.
- [x] Compare source-native layers/material defaults and source targets; preserve variants and real selection predicates.

## Task 2: Implement the independent consumer contract

- [x] Test material-model requirements, exact climate/role resolution, ambiguous physical candidates, immutable baseline IDs, all-source closure and active-gap rejection.
- [x] Implement `scripts/construction_export.py`, `scripts/construction_validation.py`, `schemas/construction-json-v1.schema.json`, `tests/test_construction_export.py`.
- [x] Export central materials/evidence, ready assemblies/packages/enclosures, accepted ACH and explicit source applicability/geometry rules.
- [x] Pilot Medium Office then residential before validating all eligible variants.
- [x] Freeze `data/construction-releases/v1.0.0/` with catalogue/manifest/completeness receipt/licenses and two standalone examples; verify deterministic bytes.

## Task 3: Review and deliver

- [x] Run focused recovery/export/schema/physical/provenance/reproducibility checks; reconcile eligible ready IDs with zero active blockers.
- [x] Fresh independent review; repair substantive findings and rerun affected checks.
- [x] Update ADR/contract/review/work record/roadmap with final counts and limitations.
- [x] Inspect staged diff and run staged security audit before each logical commit. Use automated identity/model trailer; push the existing feature branch.

## Execution ledger

Baseline `ba10588`; branch `feature/json-completion` clean. Existing ACH constants are validated. Source baseline contains 2,982 above-ground elements, 183 commercial packages and 41 enclosures; 592 ground elements are deferred. New selector/child assemblies must expand this preliminary population. Existing 166 material default recoveries close legacy required fields but source-native setter/adjustment parity still needs validation.

Final implementation: 5,092/5,092 ready IDs; source-native commercial and
residential checks passed; 52 focused tests pass. Fresh technical review findings
were repaired and verified. Protected-main publication remains outside this
execution, with ground and systems deferred.
