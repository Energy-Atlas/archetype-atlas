# ADR 0035: Readable schedule generator restructure

Status: accepted (2026-10-17, user decision). Supersedes ADR 0024, 0033 and
0034. Amends ADR 0005 and 0017–0032: their semantic decisions stand, their
exactness, authority-lock and certification ceremony does not.

## Context

The stochastic schedule generator (`atlas_schedules`) was built to reproduce
upstream ComStock and ResStock output bit for bit, with every pinned file
change recorded as an authority-lock transition. That made the code hard to
read and very expensive to extend: about two thirds of the commercial kernel
is input re-validation, receipts and Ruby float emulation, and stage 6 (nine
remaining families) was estimated at 110–180 hours. Nothing in the generator
has been released, so there is no compatibility obligation.

## Decision

1. **Precision.** Bit-level agreement with upstream is never required.
   Acceptance against native answer keys (real OpenStudio / Ruby runs) is:
   - schedule fractions within 1e-6 absolute (magnitudes 1e-6 relative);
   - annual totals within 0.01 %;
   - discrete outcomes (inferred hours of operation, day categories,
     sampled options, event counts for replayed streams) identical, with any
     near-threshold flip listed explicitly in the validation report.
2. **Commercial (ComStock / openstudio-standards).** A faithful, readable
   port written from the upstream code (not from papers alone), structured as
   small single-purpose modules with family behaviour in data files. An
   upstream quirk is kept only if removing it breaks the acceptance bar on an
   answer key. Extracting intermediate formulas from OpenStudio is a per-quirk
   fallback, not the default.
3. **Residential (ResStock / OpenStudio-HPXML `schedules.rb`).** Ship two RNG
   modes behind one stream interface: R1 replays the Ruby 3.2.2 MT19937
   streams (validated against native draws), R2 uses numpy PCG64. Test R1 and
   R2 for statistical equivalence; if equivalent, retire R1 and ship R2 with
   the equivalence evidence as justification.
4. **Verification lives in tests, not the runtime.** Inputs are validated once
   at the request boundary with JSON Schema; kernels assume valid input.
   Answer keys are compact test fixtures. No runtime authority locks, pinned
   per-file hashes, proofs or per-edit transitions; one checksum manifest per
   release.
5. **Provenance stays.** Pinned upstream revisions and download checksums,
   source locators, explicit nulls, labelled source/reviewed and code-era/DOE
   distinctions, and retained upstream notices remain mandatory.
6. **Dependencies.** numpy (pinned) is a runtime dependency; statistical tests
   are written in numpy (no scipy).
7. **History.** Large generator artifacts are purged from the feature
   branch history before it is next published.

## Consequences

- Legacy machinery is deleted without migration: authority locks and
  transitions, proofs and qualification copies, case-matrix and layout-3
  release code, old generator releases, schema 1.0–1.2 compatibility.
- Semantic decisions recorded in ADR 0005 and 0017–0032 (annual-budget
  conservation, seed derivation, stream topology, mixtures, compositions,
  physical-service identity, timing domains, recipes, source/reviewed
  separation, nulls) are carried into the rewrite and listed in the
  restructure design (`docs/superpowers/plans/2026-10-17-generator-restructure.md`).
- New families need a native answer key (an offline OpenStudio run) but no
  bit-level reproduction.
