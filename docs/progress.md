# Execution ledger

Plan: `docs/superpowers/plans/2026-10-02-atlas.md`.

- Governing brief read in full; found under `docs/` rather than repository root.
- User selected no license for original work.
- New workspace contained only the brief and no Git repository.
- Decision: implement in this new repository on a research branch; no existing
  checkout needs isolation. User's autonomous execution instruction supersedes
  repeated design/plan approval gates in workflow skills.
- Preflight: retrieval lock, selection, table contracts, and validator interfaces
  form one sequential pipeline; source-dependent selections await inspection.
- Task 1 complete: initialized repository; five families inventoried; 91 raw
  blobs pinned to three repository commits with SHA-256 and license notices.
- Tasks 2/3 complete: schema and source-semantic ADR implemented; Medium Office
  pilot passed before expansion; independent unit/source comparisons added.
- Task 4 complete: 43 building/template combinations across nine typologies;
  deterministic ComStock/ResStock option evidence added without stock sampling.
- Ruling: 16 pre-1980 mass-floor source zeros are withheld as null U-values with
  original zero evidence — zero is physically invalid — downstream assembly
  resolution is required rather than choosing an undocumented substitute.
- Ruling: direct DOE/PNNL linked benchmark downloads returned 404 — preserve
  this gap and label standards inputs accurately — final generated-model/scorecard
  equivalence remains unverified.
- Ruling: track normalized JSON tables plus metadata; ignore generated monolithic
  JSON and CSV views — avoid duplicate ~40 MB payloads — consumers can regenerate
  the convenience exports locally.
- Task 5 in progress: clean pinned Python environment installed; mutation,
  security, release and reproducibility tests implemented; final review follows.
- Final review: separate read-only agent found no Critical issues. Three Important
  findings reproduced RED: empty-key audit false-positive, source-drift release
  acceptance and missing mapping flag provenance. One fix pass adds horizontal
  whitespace scanning, source/rebuild release gates and original flag evidence.
- Final: minor (deferred): exact source key-set uniqueness/coverage in standalone
  validator; current canonical/release rebuild gates enforce the selected data.
- Final: minor (deferred): schema-version-dispatched historical unit constants;
  0.1.0 is correct, future unit changes must preserve that contract.
- Final: minor (deferred): independent manifest release-label contract; other
  inventory/hash/count/schema/source-lock checks remain enforced.
- Final: fixed Important findings — three regression classes observed RED then
  GREEN; full 23-test suite passed. Fresh retrieval verified all 91 locked blobs;
  full build/validation, 15,866 independent source checks and byte reproduction
  passed. Security audit also passes after the empty-example correction.
- Task 5 complete: clean Python 3.14 environment, pinned dependencies, Linux/
  Windows CI definition (not remotely executed), and independent review complete.
- Task 6 in progress: scientific coverage/reproduction/schema docs and release
  notes written; freeze and fresh Git-checkout integrity checks remain.
- Task 6 complete: v0.1.0 frozen at release commit `ee3830f`, generated from
  `372ea5a`. Every staged snapshot byte matched the manifest before commit.
  Fresh Git clone passed frozen release integrity, canonical schema validation,
  tracked security audit, and full byte reproduction from the separately fetched
  raw cache. No remote CI run, OpenStudio/EnergyPlus simulation or direct external
  scorecard validation is claimed. All release work is local; tag follows this
  final execution-record commit.
