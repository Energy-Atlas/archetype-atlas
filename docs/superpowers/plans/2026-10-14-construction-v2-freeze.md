# Construction v2 migration validation and freeze

> **For agentic workers:** Execute inline using the existing feature checkout; request one fresh technical review before the reversible freeze commit.

**Goal:** Record accepted examples, verify the complete migration, and freeze construction JSON v2. Stop before site/publication/BEMGen implementation.

**Architecture:** Keep the selected consumer interface approved in ADR 0022.
Package a normalized catalogue with 224 source definitions, resolved context
records, interned component configurations and shared assembly/material/evidence
resources. Rehydrate exactly the same self-contained consumer document from a
frozen context. Preserve all source alternatives and story/space overrides.

**Spec:** `docs/construction-json-v2-contract.md`; user acceptance and instruction
to proceed through acceptance, full validation and freeze only.

## Constraints and review focus

- No v1/source/program changes or regeneration; ground, systems, translator, site and CI deferred.
- SI, source IDs, variants, source-native ordering, provenance and fixed ACH unchanged.
- No generic required_bindings or deferred_scope in the consumer contract.
- Every supported climate/reference context must validate; unsupported source contexts must fail explicitly.
- Retained alternative assemblies must be explicitly selectable, not dropped by source-first defaults or counted only as raw evidence.
- SmallHotel story overrides must use original story conditions; compatibility-only queries remain evidence.
- Normalized context hydration must reproduce standalone exports and their evidence dependency closure.
- Deduplicate validation of identical immutable resource blocks, without skipping checks for distinct contexts/resources.

## Tasks

1. [x] Record explicit user acceptance, preserving existing comments.
2. [x] Add regression tests for source alternatives, story overrides and complete source/context reconciliation; observe failures then implement.
3. [x] Build normalized freeze and portable context hydration with schema, examples, licenses and manifest.
4. [x] Validate all contexts, all eligible physical resources/variants, exact source equality and deterministic bytes; repair real failures.
5. [x] Fresh technical review; repair substantive findings with regressions. Update ADR/contract/work record.
6. [x] Inspect staged diff, security audit and byte/hash parity before committing; stop before site/publication.

## Execution ledger

Baseline `1e38c0e`, `feature/json-completion`, clean; preceding local review commit
is not yet pushed. Accepted design and both examples recorded on 2026-10-14.
Read-only primary-context survey: all 224 definitions export without errors.
Source census: 4,751 commercial contexts and 47 residential forcing contexts.
Geometry query census includes 71 space-type and 15 story overrides; migration
must include both. Store shared resources/configurations rather than duplicating
large provenance and material dictionaries for each selected context.

Fresh independent review identified receipt/assignment contradictions, changed
direct-selector semantics/source order during explicit hydration, and a missing
v1 catalogue-manifest checksum gate. New regressions reproduced those failures
before repairs. All 37 focused tests pass after the final implementation changes.
Shared resource validation also covers independent source-table recipes, rather
than relying only on inherited v1 checks. No source defaults/physics changed.

The first final reproduction attempt correctly rejected an unexpected working-
tree schema reset to the exact pre-migration HEAD version. The staged and frozen
schema bytes were unchanged. Preserved the reset file in the ignored build
folder and restored the validated staged schema; every input hash again matched
the frozen manifest. The repeated full reproduction passed with stable inputs.

Final freeze and `--check`: 5,092/5,092 ready source identities; 224 definitions,
4,798 supported contexts, 4,868 assemblies, 858 materials and 8,014 evidence
records; 17,564 distinct explicit source-selector choices checked. Every frozen
context reproduces its standalone document and all release files reproduce exact
UTF-8/LF bytes. Both pilots match the accepted document values; the frozen-context
CLI export/check passed. All staged release/input bytes match the manifest,
upstream notices match v1 exactly, staged diff is inspected and security audit
passes. Stop at the local freeze commit; site integration/publication, BEMGen,
ground and systems remain deferred.
