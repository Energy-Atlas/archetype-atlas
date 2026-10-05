# Selective Schedule Resolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Execution is autonomous under the user's instruction.

**Goal:** Execute reproducible residential schedule generation and selectively resolve justified inactive loads/conditioning with explicit provenance.

**Architecture:** A checksum-locked upstream runner produces profile artifacts; an evidence-gated resolver produces assumptions. A separately versioned supplement references immutable v0.2.0 and is displayed alongside source facts in the catalogue.

**Tech Stack:** Python, JSON Schema, pinned OpenStudio 3.10.0/Ruby and bundled OpenStudio-HPXML 1.11.0; existing MkDocs/Plotly.

**Spec:** docs/superpowers/specs/2026-10-03-schedule-resolution-design.md

## Global constraints

- Preserve frozen releases and reported nulls; never infer zero solely from absence.
- Prioritize actual upstream execution for all 41 residential configurations.
- Fix seed/year/timestep and label any reference-context input explicitly.
- Disable inactive conditioning explicitly; numerical sentinel temperatures are not source facts.
- No automatic support-space or electric-HVAC classification.
- SI normalized values; original values/units, locators, transformations and interpretation are retained.
- Source/runtime archives stay immutable and locked; original work remains unlicensed.
- Every commit requires staged diff inspection, staged audit and automated identity/trailer.

## Review focus

- A missing/positive load or mixed-fuel appliance must prevent an unjustified zero.
- Generic generated appliance columns must not imply appliance installation.
- Calendar, location, stochastic seed and thermostat offsets must remain interpretable.
- A partial generation failure must remain visible and not appear as simulation readiness.
- Catalogue evidence and downloads must distinguish source facts from assumptions.

## Task 1: Execute residential generator (highest priority)

Files: sources/runtime-lock.json; scripts/runtime.py; scripts/residential_profiles.py;
scripts/run_residential_profiles.rb; tests/test_residential_profiles.py;
docs/residential-generation.md. Generated outputs: ignored build/residential/.

Interfaces: runtime.fetch_runtime(lock, destination) returns verified paths;
residential_profiles.build_inputs(release, policy) returns deterministic run inputs;
residential_profiles.validate_profiles(path, metadata) checks executed output.

- [x] Inspect pinned generator/runtime requirements and source input translation; document exact generation boundary.
- [x] Test corrupted locks/unsafe paths, annual dimensions, invalid fractions and explicit input provenance; watch tests fail.
- [x] Implement locked retrieval and upstream runner; test one recipe before expansion.
- [x] Execute all 41 recipes with fixed seeds/calendar; validate outputs, match source controls and absent end uses; rerun pilot deterministically.
- [x] Commit runner, locks, validation and scientific decisions after staged audit.

## Task 2: Selective resolution supplement

Files: schemas/resolution.schema.json; sources/resolution-policy.json;
scripts/resolve.py; tests/test_resolution.py; docs/adr/0004-selective-resolution.md.
Outputs: data/resolution-releases/v0.1.0/ with manifest, resolutions and profile index.

Interfaces: resolve.resolve_records(data, policy, profiles) returns explicit
resolution rows; resolve.validate_bundle(path) verifies schema, references,
evidence, units and hashes. Profiles are linked from Task 1, never fabricated.

- [x] Test fail-closed handling of absent/positive loads, mixed/unknown fuels, conditioned spaces, water-use ambiguity and unchanged source records.
- [x] Implement exact evidence-backed rules and explicit reviewed record IDs; emit unresolved candidates separately.
- [x] Validate all applied assumptions and executed profiles, reproducibility and complete provenance; freeze the supplement with checksums and notices.
- [x] Commit the versioned supplement and ADR after audit.

## Task 3: Catalogue delivery and review

Files: scripts/site.py; website/assets/site.js; website/content/guides/residential.md;
website/content/methods.md; tests/test_site.py; scripts/site_smoke.py;
docs/site-publication.md; this plan's implementation ledger.

Interfaces: site consumes only a validated resolution bundle; detail packets
include source record plus separately labelled resolution/profile metadata.

- [x] Test resolution labels, original null preservation, referenced profile downloads and annual/day plot selection.
- [x] Render assumption evidence and generated residential plots with units, seed/calendar and unresolved controls visible.
- [x] Run Python/Node suites, release/supplement validation, strict site build, links and browser checks.
- [x] Obtain one fresh whole-branch review, fix material findings with regressions, and publish the verified artifact autonomously without merging research branches.

## Implementation ledger

- Authorization: user's five rules plus prior autonomous/no-intervention instruction.
- Isolation: feat/schedule-resolution starts from aff4d3f; existing checkout retained by prior branch preference.
- Pre-flight: immutable v0.2.0 -> upstream input projection -> profiles -> supplement validation -> catalogue. Original record identities survive every boundary.
- Ruling: use an additive resolution release rather than mutate the atlas schema/frozen rows. Cost if wrong: a later normalized-schema migration; scientific source evidence stays intact.
- Ruling: use explicit inactive conditioning, not arbitrary extreme setpoints. Cost if wrong: a downstream numerical adapter must implement its own documented sentinel policy.
- Ruling: autonomous instruction supersedes skill design/plan approval handoffs. Cost if wrong: reversible branch/documentation changes and publication rollback.
- Ruling: retain the plan's committed ledger instead of mechanically creating a second scratch ledger; it already survives compaction and records the same contracts. Cost if wrong: manual review-package preparation.
- Task 1: Ruling: extract only declared upstream schedule/argument subtrees under a short runtime root to avoid Windows MAX_PATH failures in unrelated income-distribution paths. All 1,021 selected files were independently checked against Git blobs. Cost if wrong: broaden the locked include set for a later model-generation stage.
- Task 1: Ruling: unavailable FIPS county weather is replaced only in an explicitly labelled variant by pinned ZIP-to-TMY3-station mapping from an official working archive. Cost if wrong: location-dependent profiles must be regenerated with accessible county weather; no claim of exact baseline equivalence is made.
- Task 1: Ruling: execute the upstream schedule core and thermostat routines directly, with full source inputs, rather than generate unrelated building geometry. Honor three upstream zero-occupant skips; leave other stochastic loads unknown. Nominal thermostat profiles expose unavailable-day counts without claiming effective equipment availability. Cost if wrong: later full HPXML execution is needed for those unresolved controls/end uses.
- Task 1 evidence: all 41 annual CSV and canonical JSON artifacts reproduce byte-for-byte on independent upstream reruns; 38 stochastic runs, three explicit zero-occupant skips, 41 nominal thermostat profiles; 8,760 hourly rows each.
- Task 1: complete; six focused regression tests (observed RED→GREEN), whole suite 56/56 passed; runner/locks/documentation committed as the first implementation unit.
- Task 2: complete; seven focused tests pass, including observed RED→GREEN path/rule/release contracts; expanded whole suite 64/64 passed. Frozen supplement v0.1.0 has 677 resolutions across 80 records, 503 executed profile-column references, 33 source-zero schedules, 24 reviewed unconditioned cavities, 24 reviewed no-occupancy cavities, 29 reviewed no-hot-water programs, four demonstrated all-electric dwelling zeros, and 60 selected absent-end-use fractions. All 1,286 unsupported commercial program fields remain explicit.
- Task 2: exact Windows upstream CSV bytes are retained with a scoped Git text-normalization exemption; canonical SI JSON uses LF. No original atlas release files changed.
- Task 3 implementation checkpoint: record packets retain source rows unchanged and attach a separately labelled supplement; annual/day plots use actual 2007 calendar hours. Schema/rule/profile validation precedes rendering. Python 64/64 and Node 8/8 passed; strict full MkDocs build completed in 246.46 seconds. Browser/link checks and final full suite remain in progress before publication.
- Task 3 regression: a transient Windows tree-rename lock was observed during the independent site generation. A bounded retry of the same validated rename passes an observed RED→GREEN file-lock test; permanent permission failures still propagate. Independent generation then completed.
- Task 3 verification: strict MkDocs, all internal links/fragments and browser interactions pass; independent full generations produced 30,277 byte-identical files. Browser checks compare July 1 plotted residential values against canonical hours and exercise annual 8,760-hour plots.
- Final review: one fresh whole-branch review found one Important failure-lifecycle defect; no Critical or Minor findings and no declined-to-judge items. An unsuccessful rerun could leave old profiles eligible for freezing. Two observed RED→GREEN regressions now cover failure before any output and after partial unchanged output, and reject stale raw output during freezing. Fresh attempts record running/failed/completed status; freezing requires the latest completed receipt and matching inventory/hash. The immutable supplement retains its original independently reproduced runner snapshot.
- Final review verification: 67 Python tests and eight Node tests pass after the fix. A third real upstream execution of all 41 configurations under the new lifecycle reproduces the frozen index, CSV and canonical JSON bytes exactly. Publication remains the final delivery step; no second review pass is planned.
- Final: fixed stale-success outputs after failed reruns — test_failed_attempts_preserve_previous_output_and_record_failure and test_failed_latest_attempt_cannot_freeze_previous_success RED→GREEN, suite 67/67 Python and 8/8 Node. Fix committed as 4c651d3; completed-receipt freezing validated on a real 41-record execution.
- Task 3: complete. GitHub Windows/Python 3.14 and Linux/Python 3.11 validation passed for 4c651d3; strict site/link/browser build and deployment passed. Live HTTPS files (11) match local bytes and annual/day profiles match canonical values. Publisher branch feat/schedule-resolution remains separate; resolution-v0.1.0 identifies this supplement release. Publication and per-record availability are documented in docs/site-publication.md and docs/schedule-availability.md.
- Final: no deferred minors and no declined-to-judge items. No scratch plan workspace was created; the committed ledger is retained under the documented ruling.
