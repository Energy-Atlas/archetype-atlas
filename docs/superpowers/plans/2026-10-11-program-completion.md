# Program completion implementation plan

All implementation tasks below are complete. The user's revised remaining work
and its order are recorded in the [current roadmap](../../roadmap.md), updated
2026-10-12.

> **For agentic workers:** Use superpowers:executing-plans to implement this plan inline, task by task.

**Goal:** Implement the approved program completion policy, recover available residential inputs, and expose any genuinely unresolved assumptions precisely.

**Architecture:** Preserve frozen definitions and the v2 contract as historical inputs. Produce a versioned v3 ready export through source recovery, accepted resolution, then aggregation. Keep evidence outside executable operands. Raw exports retain source unknowns.

**Tech Stack:** Python, JSON Schema, pinned OpenStudio/Ruby source calculations, unittest.

**Spec:** `docs/adr/0016-program-completion-policy.md` and `docs/reviews/program-json-annotation-responses.md`.

## Global constraints

- Source recovery precedes accepted defaults; frozen source releases remain immutable.
- No unknown active program operand may be called simulation ready.
- Preserve fuel, host, scaling basis, calendar, rule precedence and design days.
- SI output with original values, source locators, transformations and checksums.
- Work on the user's existing `fix/program-consistency` branch. The user explicitly requested implementation of the reviewed policy; no additional design approval is required.

## Review focus

- Vacant dwellings retain refrigeration while occupancy-dependent uses vanish.
- Fuel appliances retain electrical auxiliaries and propane identity.
- Unknown non-support-space loads fail resolution instead of silently becoming zero.
- Mixtures preserve hourly input energy and annual heat partition.
- Shared water demands remain physical singletons; weather mains is an executable binding.

### Task 1: Recover remaining source data

Files: new `scripts/recover_program_inputs.py`, `scripts/recover_residential_inputs.rb`, versioned recovery JSON under `data/program-inputs/`, and `tests/test_program_recovery.py`.

Interface: `recover()` generates source-traceable per-fixture magnitudes, heat splits, fuel components and available schedules for the export resolver.

- [x] Write failing tests for 41 fixture coverage, nonzero occupied loads, zero vacancy operational loads, retained refrigeration and split fuel appliances.
- [x] Execute pinned source option/default/calculation routines; verify source hashes and deterministic outputs.
- [x] Inspect ER_Triage source density and helper behavior; recover a value or document a concrete unresolved proposal.
- [x] Run recovery tests, inspect staged diff/security audit, commit logical recovery unit (`6038df7`).

### Task 2: Versioned ready export

Files: `scripts/program_json.py`, new `scripts/program_json_v3.py`, versioned schema/default policy, `tests/test_program_completion.py`.

Interface: `ProgramExporter(bundle).export(id, mode)` retains raw/defaulted calling convention; v3 ready output resolves active inputs or raises a specific unresolved-input error.

- [x] Add failing tests for typed fractions, explicit inactive conditioning, weather mains, accepted schedule completions and rejection of unsupported unresolved operands.
- [x] Recover leaves, apply accepted assumptions, omit inactive demands, embed schedules and context metadata; preserve historical v2 implementation.
- [x] Validate Medium Office pilot plus residential examples before whole-library expansion.

### Task 3: Aggregation

Files: new `scripts/program_json_aggregation.py` and tests in `tests/test_program_completion.py`.

Interface: aggregate resolved loads by compatible type/fuel/host/basis; retain component metadata and output normalized summed trajectories.

- [x] Add failing conservation tests for unequal EFLH, zero demand, separate fuels and incompatible hosts.
- [x] Sum hourly power; use annual-energy weights for supported heat fractions; preserve design-day coverage and shared services.
- [x] Run tests; include aggregation in the inspected/audited version 3 delivery unit.

### Task 4: Delivery and completeness validation

Files: export/build integration, contract/examples, new completeness report and validation command.

- [x] Validate every selected program, reference closure, physical operands, schedules, fuel identity, and reproducibility; report unresolved records without declaring success.
- [x] Update contract, examples, ADR implementation status and review record.
- [x] Run relevant existing tests and full-library checks; obtain final code review and resolve material findings.
- [x] Inspect staged changes, run staged security audit and commit. Bring remaining material assumptions to the user with exact scope and proposals.

## Execution evidence

The complete Python suite passed 260 tests. After the final fixes, 43 focused
export/schema/completeness/aggregation/site/browser tests passed. Eight recovery
tests and the checksum-verified ER_Triage regeneration check passed. Independent
residential extractions produced identical canonical LF bytes. No EnergyPlus
simulation or release publication was performed.

Final receipt: 1,900 of 1,900 programs ready, zero failures and zero open
decisions within agreed scope. A fresh `--check` pass reproduced the complete
export-set checksum. Ninety commercial mixtures record the accepted calendar
decision because their component heat fractions differ. Frozen releases are
unchanged. Receipt input hashes match both working files and staged Git bytes.

Independent final review found the missing mixture activity recovery and
incomplete ready-schema constraints. Both now have observed-failing regressions
and passing fixes. Review also required retaining aggregation component
schedules and explicit scope reporting; both were corrected. The re-review
reported no remaining Critical/Important findings, and independently verified
active-member mixed setpoints to floating-point tolerance.

The user accepted the 2007/no-holidays heat-weighting reference calendar and
left general-water signed gains and distribution-water effects outside program
scope. The follow-up decision document preserves the proposals, responses,
affected patterns and comment spaces. These decisions do not assume those
physical effects are zero.
