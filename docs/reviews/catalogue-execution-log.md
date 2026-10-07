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

Task 3: complete. Nine construction/comparison tests pass, including the real
Medium Office extraction. Source ground F/C targets were available outside the
old envelope projection and are now preserved with geometry dependencies.
Generic fallbacks reuse pinned typical assemblies only when source assignment
cannot resolve the role. Material record IDs retain assembly provenance while
physical comparison ignores provenance-only identifiers. A regression test
caught and fixed conflicting evidence on shared physical material identities.

Task 4: complete. Three HVAC tests and three comparison tests pass. Source
component roles and conditional capacity/date/rating rules are preserved.
Finding: current descriptors do not establish fan pressure, complete topology,
curve assignments or a resolved COP. These remain explicit rather than inferred
from the system label. Ancillary refrigeration/exhaust records are distinguished.

Task 5: pilot implementation validated. Three-kind integration, corruption and
immutability tests pass. Canonical pilot rebuilt byte-identically. Initial v2
pilot snapshot fa09a9e2e194e69afa74d37425c81e1452e4d9b12327730ae4f8c5558125e4af.
Selective queries for the three 2019 contexts transferred 207,581 bytes in 25
requests; no supporting schedules/evidence were loaded automatically. Existing
v1 compatibility tests are running separately before the full release gate.
Ruling: subclass the existing verified transport instead of modifying v1 modules;
this preserves their public default behavior. Cost if wrong: shared transport
changes later require compatibility tests for both majors.

Task 5 gate complete: 47 pilot/v1 compatibility tests passed in 203 seconds.
Task 6: complete. Seven composition tests pass, covering all 83 contexts/768
source rows, source calendar/design days, required unknowns and conserved loads.
Strip-mall 25/25/50 weights are reproduced from geometry. Recipe-specific
schedule evidence prevents identical shapes from losing their distinct lineage.
The review area extractor now delegates to production code without import side
effects; its inspection format remains available. Full-family unknown magnitudes
and missing member demands are explicitly retained, not averaged away.

Task 6 finding: aggregate weekday selectors must precede explicit weekdays in
derived rules. A seasonal/wrap-year regression caught and verifies the correction.
The OpenStudio 2.2.1 counted-area default is checked against its locked source.
Baseline full suite: 141 tests passed (1326 seconds).

Task 7: four residential tests pass. All 41 source fixtures are separate whole-
dwelling programs, enclosure definitions and HVAC packages. Exact matched
arguments supply occupancy, ACH50 and nominal ratings; unresolved arguments,
assemblies and load magnitudes stay explicit. All existing determined annual
channels retain year/seed/weather and nominal-control limitations. Three vacant
fixtures export occupancy only; absent end-use channels are unknown, not zero.
No HPXML defaults, capacity sizing or generators are executed.
