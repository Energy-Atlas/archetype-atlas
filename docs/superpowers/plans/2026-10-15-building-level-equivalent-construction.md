# Additive building-level equivalent construction implementation plan

> **For agentic workers:** Use superpowers:executing-plans task by task. The user approved the design and explicitly authorized implementation; execute inline on the existing feature/json-completion branch.

**Goal:** Add precomputed, source-archetype construction equivalents with one recipe per semantic while preserving every detailed export.

**Architecture:** Separate the thermal reducer, source weighting profiles and additive exporter. Reuse immutable detailed releases; publish versioned supporting profiles in the program library. Report approximation errors and unresolved operands without increasing model complexity.

**Tech stack:** Python standard library, existing jsonschema dependency, pinned OpenStudio 3.10.0 source-recovery runtime. No new dependencies.

**Spec:** [Approved proposal](../specs/2026-10-15-uniform-construction-semantics-proposal.md), including the final chat clarifications.

## Global constraints

- Three slots by default: two massive layers plus one massless resistance; do not add layers or a sophisticated optimizer.
- Preserve existing detailed assemblies, mappings, assignment rules and exports.
- Precomputed archetype shares are the default; no consumer geometry-specific weighting.
- Report measured approximation errors even where this representation is inadequate.
- Keep ground, systems and BEMGen translation deferred.
- Local validation only; no push, site build, CI/CD or systematic building-level error validation.
- Unknown inputs remain unknown; do not silently invent shares, quantities or optical properties.

## Review focus

1. Reversed boundaries/signs: analytical homogeneous slab at several frequencies, independently checked air-film boundary equations.
2. Missing or zero exposures: distinguish known absence, unknown and imputation; apply precedence before normalization.
3. Mass duplication: paired interior surfaces represent one physical inventory item; added mass and explicit surface mass must not overlap.
4. Source geometry/program aliases: recover exact native keys and source locators, never infer equal programs from similar building names.
5. Poor fits and malformed source layers: preserve measured errors/quality flags; invalid inputs cannot become ready through clipping.

## Task 1: Verify and isolate the thermal reducer

**Files:** Add scripts/construction_equivalence.py and tests/test_construction_equivalence.py; update the proposal and analytical probe without rewriting its frozen v1 results.

**Interfaces:** response(layers, period_h, films=(0.04,0.13)) returns four inward-flux admittances. reduce_opaque(contributors, films=(0.04,0.13), one_sided=False) returns one valid recipe, conserved targets and errors, or an explicit unresolved status.

- [ ] Write tests for homogeneous-wall analytical fluxes at 1/6/24/72/168 h, both unit boundary excitations, unequal-film ordering, zero capacity, negative/nonfinite operands, conservation and unchanged two-parameter search.
- [ ] Observe failure before implementing the production interface.
- [ ] Implement the approved grid and material normalization; retain quality flags on poor fits instead of expanding the model.
- [ ] Run the focused numerical tests and record results.

## Task 2: Recover source archetype support profiles

**Files:** Add scripts/recover_construction_weights.rb, scripts/construction_weighting.py, tests/test_construction_weighting.py and versioned data/program-support/construction-weighting-v1/ files.

**Interfaces:** build_profiles() returns all reference compositions with native program keys, source matches, story/exposure/volume allocations and mass inventories. recover() executes only pinned geometry/material/source-data methods; no HVAC or annual schedules.

- [ ] Test exact program joins, multipliers once, non-counted scopes, known zero exposure, generic GuestRoom non-duplication and paired mass accounting.
- [ ] Recover net opaque/opening areas and story memberships from source geometry, first Medium Office then remaining references.
- [ ] Resolve missing exact contexts through native source rows and explicit cross-context source matches; retain unresolved quantities visibly.
- [ ] Freeze profiles with source revision/checksum/locator, original operands, units, transformations and interpretation notes.
- [ ] Run focused profile tests and deterministic reproduction checks.

## Task 3: Add the derived schema and exporter

**Files:** Add schemas/construction-equivalent-v1.schema.json, scripts/construction_equivalent_export.py, tests/test_construction_equivalent_export.py and docs/adr/0025-additive-building-level-equivalents.md.

**Interfaces:** export_equivalent(release, context_id, profiles) returns a standalone building_level_equivalent document with source-compatible metadata, exactly one selected assembly per applicable semantic, conserved quantities and fixed ACH. Existing detailed loaders and CLI stay untouched.

- [ ] Test Medium Office schema/hydration first, then Warehouse precedence, residential adjacency and quantity conventions, opening-property availability and unsupported contexts.
- [ ] Implement opaque, glazing and mass reductions with separate quality/status metadata and derivation receipts; never require a program-to-consumer-face mapping.
- [ ] Ensure source/detailed structures are unchanged, and no rule list escapes into an active unified semantic.
- [ ] Validate SI, references, provenance, physical values and quantity conservation.

## Task 4: Freeze, inspect and document the additive release

**Files:** Add scripts/construction_equivalent_release.py, tests/test_construction_equivalent_release.py, data/construction-equivalent-releases/v1.0.0/ and a concise review coverage report.

**Interfaces:** artifacts() produces deterministic interned release tables and a completeness report; --context-id ID --output PATH exports a standalone document; --check verifies existing bytes.

- [ ] Test checksum tampering, deterministic output and preservation of all 177 sets / 3,320 contexts without claiming unresolved records ready.
- [ ] Freeze a Medium Office pilot, then expand the same data checks to all contexts; record ready/blocked/absent and quality flags per semantic.
- [ ] Run focused construction tests and representative engine smoke checks where runtime inputs permit; do not run broad program/site/CI generation.
- [ ] Inspect staged changes and run python -m scripts.audit --staged before each logical commit.
- [ ] Perform a final fresh review, address correctness findings, and report actual coverage and remaining source gaps.

## Execution record

2026-10-15: Design approved with two final clarifications. User authorized direct implementation. Existing feature branch reused; detailed release baseline v2.2.0 remains immutable. No deployment authorization.
