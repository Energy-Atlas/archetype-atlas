# Catalogue redesign execution log

Plan: `docs/superpowers/plans/2026-10-07-catalogue-redesign.md`.
Authorized scope: Tasks 1-10, autonomously; Task 11 explicitly excluded.
Starting commit: `3636390`. Branch: `feature/query-dto`.

## Decisions and findings

- Ruling: reuse the clean, approved feature checkout rather than creating a
  second checkout. The plan fixes this branch and existing locked caches are
  large. Cost if wrong: concurrent edits require reconciliation; check status
  before every commit and preserve unrelated files.
- Ruling: the skill's temporary ledger is supplemented by this committed log;
  important findings must remain available after execution and cleanup.
- Pre-flight: Tasks 2-4 consume Task 1's BuildContext and return DefinitionBundle;
  Task 5 combines them; Tasks 6-8 extend the same tables; Tasks 9-10 consume the
  verified release. No conflicting producer/consumer signatures found.
- The source/reviewed view is independent of composition and assumptions.
- Fixed HVAC performance does not authorize choosing arbitrary capacity or
  converting capacity-dependent ratings to an invented COP.

## Task progress

Task 1: complete. Six contract tests failed on the missing module, then passed.
Locked 15 additional source files at the existing Standards revision; all four
frozen input manifests and their file hashes verified. Initial full-suite baseline
is still running in the background; no failures reported yet.

Task 2: complete. Four program tests RED/GREEN; fixed source/reviewed overlays
keep original fields intact. Water extraction uses the frozen helper branch,
not simultaneous per-area and alternate absolute values. Services retain one-time
ownership and distinct physical heat assignment. Medium Office source scope:
10 programs, 5 services, 17 original schedule references before reviewed overlays.
