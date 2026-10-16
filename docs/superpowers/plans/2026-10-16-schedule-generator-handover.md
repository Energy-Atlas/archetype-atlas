# Stochastic schedule generator handover and continuation plan

> **For agentic workers:** Read this handover, `AGENTS.md`, and the full
> `docs/AGENT_RESEARCH_BRIEF.md` before work. Use
> `superpowers:subagent-driven-development` for resumed implementation, as the
> user requested; GPT-6.1 Sol is the maximum permitted model. The implementation
> is PAUSED at the user's request. This documentation commit does not resume it.

**Goal:** Let another agent review and continue the incomplete extraction without
repeating experiments, losing adverse evidence, or confusing partial coverage
with a qualified release.

**Architecture:** A standard-library Python runtime maps explicit arguments and
one master seed to referenced, related hourly schedules. Source mechanisms and
annual budget definitions are separate from generated realizations. Constituent
schedules are generated before mixing; immutable source and release references
remain distinct from experimental validation machinery.

**Tech stack:** Python 3.11 and 3.14, JSON/SHA-256, unittest, offline ZIP runtime;
Ruby/OpenStudio only for explicitly bounded development reference capture.

**Spec:** [Approved design](../specs/2026-10-13-schedule-generator-design.md),
[original implementation plan](2026-10-13-schedule-generator.md), ADRs 0017–0033.
This is a status/continuation overlay, not a change to scientific acceptance.

**Snapshot date:** 2026-10-16, America/New_York. Product-code checkpoint before
this documentation commit: `b1facd2df7cf95385fcde6972f60852f6848f779`.

## 1. Read first: status and authority

- Work exclusively in branch `codex/stochastic-schedule-extraction`, in the
  existing managed worktree whose directory ends in
  `.codex/worktrees/stochastic-schedule-extraction/archetype-atlas`.
  Do not write the unrelated `e79c` checkout or interfere with other developments.
- The full extraction is **NOT COMPLETE**. Core Tasks 1–9 and several Task 10
  staged family releases exist. Task 10, apartment A5 release qualification,
  remaining families, and weather expansion remain unfinished.
- Last completed batch: **R144 nonrunnable full-science source preparation**.
  Its author reports passing narrow synthetic/cache/metadata checks. It has
  **not received independent specification/quality review** and has not run
  against the full reference. Do not activate its templates on reading this file.
- R142's metadata-framing source fix has independently accepted source/finite
  results. This is not full-science qualification. R128's full run remains FAIL;
  R140's diagnostic overall result remains FAIL with a reporting erratum.
- No agents remain active at the pause. No merge, push, PR, publication, new
  freeze, or cleanup is authorized by this handover. Routine implementation
  choices may proceed under the approved scope **after the user resumes work**;
  do not invent repeated user-approval gates for routine steps.
- Retain immutable failed runs and unavailable evidence. A later successful
  check does not retroactively qualify an earlier run.

## 2. What is preserved in Git, and what is only local

The [handover manifest](2026-10-16-schedule-generator-handover/manifest.json)
inventories the accompanying documentation snapshots. Each records its original
ignored source path, original byte size/SHA-256, copied size/SHA-256, and exact
local-path substitutions. Inspection copies also normalize LF line endings,
strip line-end whitespace and retain one final LF, as declared in the manifest.
The ledger copy HTML-escapes hyphens in long `task-…` filename substrings that
the credential scanner otherwise flags; the manifest records the exact rule and
count. Decode `&#45;` to `-` when looking up those original filenames.
These are documentation copies, not byte-identical
replacements for raw execution evidence. Do not substitute their hashes into an
old source guard. No source launcher, runtime binary, raw download, or large
reference was promoted by this documentation unit.

Relative references inside a snapshot retain their original SDD context; resolve
them using its `source_relative_path` in the manifest, not the new snapshot
directory. Historical plans may refer to local companion TSVs or source contracts
that remain in SDD; those prerequisites must be inventoried before execution.

The accompanying [decision ledger](2026-10-16-schedule-generator-handover/progress.md)
preserves all 144 formal controller decisions plus the recorded addenda and
adverse facts. Read targeted sections, not the whole history on every task.
The readable [pause checkpoint](2026-10-16-schedule-generator-handover/pause-checkpoint.md)
and this handover supersede stale *current-status wording* in historical plans.
Historical outcomes themselves remain unchanged.

`build/` and `.superpowers/` are ignored. A fresh clone contains the tracked
handover and committed runtime, but **does not contain all work in progress or
the raw qualification evidence**. Prefer takeover in the existing worktree.
If those local artifacts are missing, stop at inventory/recovery: recover the
original immutable artifacts or plan a source-locked reconstruction. Do not mark
R144 reviewed, silently rebuild historical receipts, or replay expensive runs
merely because a clone is missing them. There is no claimed portable archive of
all local experiments in this commit.

### Local aliases used below

All paths are relative to the isolated repository root.

| Alias | Path |
| --- | --- |
| SDD | `.superpowers/sdd/2026-10-13-schedule-generator` |
| BASE | `build/task-10/apartment-a5/framed-reference-v1` |
| H | `BASE/oracle-framed-fix1` — original full-science helper/history root |
| E3 | `H/oracle-execution-outer-launch-fix1` — R128 execution evidence |
| T | `BASE/outer-launch-fix1` — reviewed outer launcher parent |
| D | `BASE/capacity-observation-v1` — diagnostic source/evidence |
| M | `BASE/metadata-framing-fix1` — accepted R142 reader and finite proof |
| F | `BASE/metadata-full-oracle-fix1` — stopped R144 source, UNREVIEWED |
| K | `BASE/cache-gate-fixtures-fix1` — R144 synthetic fixtures outside F |

Use the actual Python executable, not an assumed shell alias. The recorded
primary interpreter is Python 3.14.7; official Windows Python 3.11.9 is locally at
`build/task-10/python311-grammar/runtime/python.exe`. Source runtime archives in
the separate read-only cache are not execution/scratch directories. Do not
rehash runtime binaries or traverse inventories merely to orient yourself.

## 3. Scientific requirements and public contract

1. Pure Python generation, offline and independent of repository scripts,
   native runtimes, network access, and external services.
2. `atlas_schedules.generate(params, seed) -> dict`; variable schedule count,
   exactly 8,760 hourly values per schedule. Related channels are generated as
   one coherent object. Programs bind schedule IDs/references rather than
   duplicating arrays. Preserve API/CLI and schema compatibility explicitly.
3. Explicit unsigned 64-bit master seed. Preserve upstream full-width derived
   seed arithmetic and residential draw order; do not truncate derived seeds.
   Operating hours are sampled from the seed, not required as caller hours.
4. Preserve known annual budgets for **both RES and COM**. Bind original
   definition-derived targets to the actual generated integral. Effective
   intensity/flow may change as normalization; installed capacity and controls
   retain their own meanings. Do not force fractional schedules above one.
5. Generate each constituent before mixing. Residential units receive native
   source-compatible distinct seeds/offsets. Coordinated commercial operating
   groups share their proper timing draws. Preserve area, multiplicity, physical
   host, fuel, absolute-service ownership, allocation, aliases and denominator.
6. ComStock's conditional seeded policy is an explicit atlas adaptation. The
   original population sampler involves sample/bucket/allocation context; do
   not claim sample-matrix/Sobol/population realization equivalence. Preserve
   raw conditional CDF behavior, draw order, and failure tails; no retries or
   normalization to conceal a source failure.
7. ResStock timing does not supply apartment prototype demand magnitudes.
   Apartment resident/cohort operands and appliance allocations must be explicit
   and evidenced. A hotel guest-room name is not authority for a household HMM.
8. Non-leap local-standard-time calendar, initial year 2007, hourly intervals
   `[hour, hour+1)`, no implicit DST/holiday/time-zone conversion. Preserve source
   rule order, dates, selectors, special/design-day profiles where applicable.
9. Preserve source/reviewed view, code prototype/existing-stock benchmark,
   template/vintage, and weather/proxy distinctions. Null means unknown, not zero.
   Keep provenance, SI units, source revision/checksums and upstream notices.
10. Exact manifests are authoritative. Do not shrink a denominator to successful
    cases or invent a climate/vintage Cartesian product. Original Program JSON
    v3 and historical frozen releases remain immutable reference cases.

### Runtime and tooling map

| Files | Responsibility |
| --- | --- |
| `atlas_schedules/generator.py`, `programs.py`, `apartment_recipes.py` | Public orchestration, program bindings and apartment recipes |
| `atlas_schedules/residential/` | Activity, events, shapes and selected apartment timing |
| `atlas_schedules/commercial/` | Conditional draws and source parametric transforms |
| `atlas_schedules/budgets.py`, `seeds.py`, `calendar.py` | Conserved targets, native seed allocation and time semantics |
| `atlas_schedules/mixtures.py`, `source_compositions.py` | Actual constituent and parent assembly |
| `atlas_schedules/owners.py`, `physical_sets.py`, `services.py`, `service_graph.py` | Physical ownership, caller water, alias/reference closure |
| `atlas_schedules/resources.py`, `schemas/`, `reproduction.py` | Pinned runtime inputs, contracts and packaged reproduction |
| `scripts/schedule_generator_apartments.py` | Source/budget/domain compilation |
| `scripts/schedule_generator_case_matrix.py` | Exact case compiler, reference routing and original union |
| `scripts/schedule_generator_release.py`, `schedule_generator_release_reproduction.py` | Existing release/layout handling; case-matrix extension still pending |
| `scripts/schedule_generator_coverage.py`, `schedule_generator_native_codec.py` | Two existing uncommitted A5 drafts; preserve separately |
| `sources/schedule-generator-*-scope.json`, source locks, `data/schedule-generator/` | Exact supported contexts, source identities and evidence associations |
| `tests/test_schedule_generator_*.py`, `tests/fixtures/schedule_generator_case_matrix/` | Existing tests and durable adapter fixture inputs |

## 4. Completed and partial milestones

| Work | Recorded status and limits |
| --- | --- |
| Tasks 1–9 / M1 | Completed staged shipment. Exact ten contexts: six residential fixture/weather bindings and four Medium Office Office/Plenum source/reviewed cases. Inactive cases stay in the denominator. This is not whole-catalogue coverage. |
| Residential expansion | Shipped 41 actual source fixtures, 38 occupied and three native zero-resident skips, with 37 station proxies and 766 channels; all 12 applicable fixed companion methods covered. |
| Commercial expansion through v0.7.0 | Medium Office, Small Office, Warehouse, Full/Quick Service Restaurant and standalone Retail added progressively, including compositions and once-owned physical services. v0.7 has 229 program cases plus 32 physical/configuration cases = 261 ordered requests; its full example has 2,136 schedules/2,160 bindings. |
| Physical-service core 1.2 | Seven-stage core completed and reviewed before apartment integration. Keep caller-unit water, absolute/shared services and public 1.2 ownership semantics. |
| Apartment A1–A4 | Selected timing, source recipes/budgets, fixed rules/controls and public integration completed within their reviewed scopes. Target is 84 program IDs: 40 dwellings plus 44 common/support; 37 timing-location tuples. |
| Apartment A5 matrix adapter Task 1 | Committed adapter and durable fixtures reviewed. 385 original requests, 313 program IDs plus 72 physical/configuration requests, preserved by exact case closure. Not a shipped A5 release. |
| Full-science validator | Earlier attempts failed; latest R144 stopped templates are unreviewed. No complete A5 science/release claim. |
| Remaining families/weather | Reviewed planning and selected native pilots exist. Implementation and full qualification are still future work. |

v0.7.0 ZIP: 95,441,527 bytes,
SHA-256 `366b2f1596cb1f29173d5541e7074b0dababa7430327f9108650d98d602462cf`.
Keep existing releases and exact M1 scope intact. Never overwrite an old release
to fix a new runtime. No v0.8.0 completion is claimed.

Useful Git anchors (not review results by themselves):

- Whole-branch review base: `3e786ad`.
- Task 10 base: `d48cb12`.
- v0.7 staged report/retail work precedes the later core/apartment commits.
- `aba1115323491b121ccceeea644920f77ca4882c`: apartment A4.
- `496b47b`: explicit local release reference sidecars.
- `42d05b7`: bounded validation copies/native getter work.
- `4462d29`: exact case-matrix adapter.
- `b1facd2`: durable case-matrix fixtures; current pre-handover product HEAD.

## 5. Uncommitted state: preserve, do not sweep into this commit

Only two tracked product files were modified at the pause:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `scripts/schedule_generator_coverage.py` | 43,437 | `12ca72720212f5cb6393242f71b98f63906f94a5bf9c78b54c5ea36697483b6e` |
| `scripts/schedule_generator_native_codec.py` | 4,958 | `14993530a2e8df8c5d8ade2376e2e5f8518dbe604b7ad69277e3d17aabdfa42b` |

Inspect against their recorded intended A5 scope before any future commit.
Do not stash/reset/format/stage them as part of documentation. Experimental
reader/controller/outer files in F are local ignored source, not committed
runtime patches. The handover preserves documentation, not an assertion that
all local drafts are already reviewed or portable.

## 6. Past experiments: what happened and what not to repeat

Detailed per-decision rationale, costs, actual attempts and raw locators are in
the accompanying ledger. This table is the navigation summary. A resource STOP
establishes failure under that chosen envelope, not universal impossibility.

| Stage | Recorded outcome | Consequence |
| --- | --- | --- |
| Earlier packaged commercial expansion | Repeated ResourceSet loads made actual packaged CLI approximately 247.5 s versus a 240 s gate. Request-scoped reuse reduced 31 loads to one and approximately 181.9 s, with no science differences. | Fixed in staged runtime; do not treat bare checkout timing as packaged qualification. |
| Apartment whole-cohort generation, R63–R73 | Several bounded optimizations still left current Python full request at 240.3415451 s. A prior official 3.11 result passed; another 3.11 overrun's cause was not established. | Adopted exact semantically closed case matrix after separate architecture review; do not claim original mega-request passed. |
| R74–R79 architecture/adapter | Split preserves all original components, native unit positions, operating groups, aliases and cross-case closure. Adapter/durable fixture tests passed on both runtimes. | Full original union/scientific comparison remains required; splitting is not permission to drop cases. |
| R80 initial reference materialization | Original large reference parsed into normal Python graph exhausted 5 GiB Job envelope after decoding. | Investigated reader memory, not generator science. |
| R85/R88 pooled variants | Smaller 3 GiB and original 5 GiB pooled variants did not complete reference materialization. | Pooling did not prove full feasibility. Keep the failed variants immutable. |
| R96 ASCII transport/tokenizer | First large attempt failed AttributeError; exact failed allocation/stack details were not all emitted. | Later corrected variant required its own source/finite checks. |
| R101 corrected ASCII variant | Authenticated exact 1,092,759,826-byte ASCII reference, then MemoryError during whole parse under 5 GiB. | ASCII transport alone insufficient; do not infer universal required memory from the cap. |
| R103–R119 framed reader and Windows cold/runtime-origin plumbing | Parser finite corpus and paired-runtime checks progressed, with intervening provenance/bootstrap/origin/launcher issues corrected in fresh source cuts. | Framing finite correctness is separate from full reference and control-plane qualification. |
| R123/R125 launcher attempts | Helper-selection/outer-path setup failed before full payload; later fixed source/finite checks led to R128. | These were setup failures, not completed scientific runs. |
| R128 full framed run | Exit 1 after approximately 173.6 s; child emitted `ValueError: frame_limit` at reference framing. Full parsing/science did not finish. | Main full-science Important finding remains OPEN. |
| R136 metadata assembly mistake | Root used filesystem-aware path resolution on inventory target strings despite a no-target-query boundary. Actual native query results were not emitted; a zero-query claim was withdrawn. | Preserve erratum; use pure lexical comparison in metadata-only stages. Later pure checks cannot undo the past scope breach. |
| R139 diagnostic setup | An overbroad label replacement changed a historical `taskOld` filename. Static STOP before actual diagnostic launch. | Failed setup retained; field-specific R140 correction only. |
| R140 lexical measurement | One approximately 519.1 s contained diagnostic authenticated full input and measured topology. Overall review FAIL because post-run cache absence was not checked/emitted; scoped lexical measurements accepted with erratum. | No science comparison occurred. Do not repeat diagnostic or probe later cache state to invent past proof. |
| R142 metadata framing fix | Genuine old RED; one candidate passed 47 new and 1,229 original evaluations on both 3.14 and 3.11. Independent source/finite review PASS. | Selected candidate is qualified only within source/finite scope; full science still required. |
| R144 full-science source preparation | One old-fragment RED (0.5000 s), one GREEN (1.3206 s): five cache, 17 metadata/predicate and 38 source/static checks. No actual activation or full-science run. | Sealed, author-checked, UNREVIEWED; current pause boundary. |

Some time went into real generator changes; much recent work was validation
engineering, repeated source preparation/sealing/review and correction of our
own tooling. Do not add another general framework or replay old proof just to
reconstruct context. No aggregate wall-time/token-cost accounting was computed;
do not invent one from isolated timings.

### R140 measurement that motivated R142

- Full authenticated decoded input: 1,092,759,826 bytes, SHA-256
  `06bfc6aa7d01d0cc76fd099616a7ac94ab2ba807220ff4653cea5ba5dfb6e33d`.
- Compressed reference: 65,467,798 bytes, SHA-256
  `62ccd3e3b6a11b2ad81d34b51c8157164f2d96365bd3efc24398e76eda0e583b`.
- Sole oversized current container: `/metadata`, 19,240,377 bytes.
- It has **seven immediate children**. `building_realizations` is a 19,237,691
  byte array with eight records, maximum 2,885,414 bytes. Opening metadata and
  that array gives 14 frontier pieces (six other fields plus eight records),
  **not 14 immediate metadata fields**.
- Measured 8 MiB frontier: 6,012 bounded pieces; maximum 7,314,455 bytes at
  `/constituents/166`. These are lexical measurements, not semantic validation.
- Raw OS creation timestamps and child-exit UTC not emitted in applicable
  receipts remain unknown. Do not relabel controller end or last sample as exit.

## 7. Exact current checkpoint and immediate review packet

Read the tracked copies of the
[R144 brief](2026-10-16-schedule-generator-handover/apartment-a5-metadata-full-oracle-preparation-brief.md),
[R144 report](2026-10-16-schedule-generator-handover/apartment-a5-metadata-full-oracle-preparation-report.md),
[R143 transition plan](2026-10-16-schedule-generator-handover/apartment-a5-full-oracle-transition-plan.md),
[R142 review](2026-10-16-schedule-generator-handover/apartment-a5-metadata-framing-fix1-review.md),
and [R140 erratum](2026-10-16-schedule-generator-handover/apartment-a5-capacity-observation-actual-002-cache-erratum.md).
Use local original raw bytes for actual evidence verification.

| Local artifact | Bytes | Raw SHA-256 |
| --- | ---: | --- |
| `SDD/apartment-a5-metadata-full-oracle-preparation-report.md` | 7,712 | `23d68b52afa8045b8eda5b7a08e0c15ffce7c44f646fffd985de75d9022b76f2` |
| `F/source-index-001.json` | 21,298 | `e6887b35679877a01402344e97b56034c38f0767aff00c12888b2663bfbefdf9` |
| `F/source-seal-001.json` | 2,570 | `404a064e2ad2c9b27e3c86d4b3c3a551e9ae7145154e69e30b19ff6962b526c0` |
| `F/closed-sidecar-001.json` | 1,224 | `c26463200085e02cd0432deeabdf88afd53634afb7707fd5a62f866f97819def` |
| `F/expected-operative-sources-001.json` | 7,009 | `07a89084a6567ec4ce15c75a7bd301a3f719182ff762b0d8ac52d84ccb910c04` |
| `F/pending-whole-identifiers-001.json` | 2,335 | `ac7ad97619cdfecc2f740b1478f7b5220228e3ca594a11cbb2f580597b2bb187` |
| `M/framed_reference.py` | 15,183 | `232cc1e27536b871f6503b8156011bf7a5bdad61dca7a283fb68234806a162f3` |
| `SDD/apartment-a5-metadata-framing-fix1-review.md` | 13,145 | `de0d9cba43ea8cca920f4be7b00c6999bdc349d867a1981b1dbfd76c3003fd98` |

F index covers 64 files; only its own closing index/seal/sidecar cycle is
excluded. Source entrypoints are stopped: three Python templates begin the exact
63-byte `SOURCE_PREPARED_ONLY_NO_ACTUAL_AUTHORITY` raise line; the outer template
begins its exact 49-byte throw line. Libraries are under `F/source/`. No operative
six, actual inventory/bindings, `attempt-001`, or actual execution directory was
created at F root in R144.

R144 adds an explicit final cache collector/gate before the first PASS receipt,
querying only its owned F scope/attempt unused-cache prefix and recursive cache
artifacts. Unknown, inaccessible, bounded-out or reparse/escape conditions must
not become zero counts or PASS. Synthetic negative fixtures reside in K, outside
F. This prepares future proof; it does not supply a real final-run cache receipt.

## 8. Resume sequence: apartment A5 and release

### Stage A: independent R144 source/finite review

- [ ] Confirm user has resumed implementation, correct branch/worktree, tracked
  drafts preserved, no competing implementation writer or heavy benchmark.
- [ ] Assign one independent reviewer, Sol/high or lighter appropriate model.
  Review specification and quality together for this exact source/metadata
  finite cut; do not start actual execution or another parser finite replay.
- [ ] Verify raw index/seal/sidecar/report and only the source/fixture inputs
  explicitly admitted by the R144 brief. Record read scope/budget and adverses.
- [ ] Check original full-science preservation, current-versus-history helper
  identity, stopped entrypoints, inverse/AST edits, exact metadata membership,
  whole pending identifiers including SHA256 digits, and final cache evidence.
- [ ] If an Important/Critical defect exists, specify its narrow fix and scoped
  evidence before another source cut. A real failed finite window is not an
  automatic retry/reset entitlement. Do not expand to generic refactoring.

### Stage B: fixed-data assembly/review, then one actual qualification

- [ ] Only after accepted source review, assemble the fixed current inventory
  and actualization bindings under the prepared contract; preserve original
  rows/roles/order and full source/role projection. Source, data and GO identities
  must stay acyclic. Review the fixed data separately before activation.
- [ ] Build one explicit, bounded actual run packet from accepted source/data.
  Bind whole identifiers only, remove exact stops only, verify forward/inverse
  changes and no unresolved tokens. No global text replacement or stale GO reuse.
- [ ] Keep original H history distinct from F execution. Preserve H's seven
  fixed artifacts, seed set 1,095, ledger 314, seal 315, eleven groups and exact
  666-row preparation-cycle manifest. Do not replace these with diagnostic 24.
  Keep all 3,756 original inventory rows plus six current helpers = 3,762.
- [ ] Preserve all seven validators, public case compiler, both reference routes,
  original union, normal Python graph/full original canonical-byte equality,
  operand/input nonmutation, cold schemas/resources, source-only import/audit
  guards and runtime-origin checks before/after. A hash check is not science.
- [ ] Retain the recorded Windows envelope: 5 GiB child Job commit cap;
  admission at least 9 GiB physical/7 GiB available commit/4 GiB disk; reserves
  4 GiB physical/2 GiB commit; 600 s total/560 s work/590 s finalization policy,
  monitoring 0.1 s target/0.2 s maximum, 1 MiB raw pipes, child attached before GO,
  Job active-zero/reap/true handle close/readers/three transients/final cache
  receipt. Full current brief and parents govern exact lifecycle semantics.
- [ ] Run one qualified attempt only when admitted; first setup invocation
  consumes its scope. Capture argv, UTC, source identities, raw output, phases,
  actual resource and cleanup evidence from the first attempt. Preserve STOP.
- [ ] Independently review actual evidence. Success qualifies only what that
  run actually exercised; opposite-runtime gates remain separate.

### Stage C: case-matrix release work still pending

Use the promoted [case-matrix subplan](2026-10-16-schedule-generator-handover/apartment-a5-r74-case-matrix-subplan.md)
and [adapter report](2026-10-16-schedule-generator-handover/apartment-a5-r74-case-matrix-report.md).
Task 1's adapter/fixtures are complete; remaining Tasks 2–5 are **not** complete:

- [ ] Implement case-matrix release/standalone reproduction support using the
  existing adapter APIs `compile_case_matrix`, `route_reference_case`, and
  `assemble_original_union`. Planned module: `scripts/schedule_generator_case_matrix_release.py`.
  Prepare the corresponding focused release tests; do not invent a second adapter.
- [ ] Finish the approved four-file case-matrix layout version 3: manifest,
  generator ZIP, standalone `reproduce.py`, and original external compressed
  reference. Preserve legacy/layout-2 behavior and explicit version rejection;
  ADR 0033 describes existing layout 2, not completed layout 3.
- [ ] Test mixed RES/COM parents, area versus absolute service semantics,
  overlapping ownership/reference closure, denominators, zero participation,
  and projections. Preserve all original methods/components; no ignored fields.
- [ ] Qualify every ordinary case at <=240 s on current Python and official
  Windows 3.11; one complete-matrix cold/original-reference/full-union scientific
  reproduction <=600 s on each runtime. Each transported blob/member/ZIP
  remains <=104,857,600 bytes. Do not add case times and call it measured union
  time, or use one passing interpreter to qualify the other.
- [ ] Run affected A5 integration checks, freeze a fresh immutable version only
  if every required gate passes, verify/reproduce it using its own runtime and
  resources, and obtain final A5 review. Defer the single final full-suite run
  to the final family code cut unless a new change/failure/unresolved concern
  justifies an earlier run; do not repeat it on every metadata checkpoint.

## 9. Remaining family/location plan

These are planned denominators, not shipped coverage, population counts, or
independent weather cross products. Use exact canonical IDs and view/template
memberships, never count-only acceptance. Existing 2013 native pilots are reusable
evidence; do not rerun them merely to fill a proposed observation count.

| Family | Programs / compositions | Tracked continuation plan |
| --- | --- | --- |
| RetailStripmall | 40 / 10 | [Retail/Office](2026-10-16-schedule-generator-handover/retail-office-followup-subplan.md) |
| LargeOffice | 36 / 0 | Same plan; independently shippable after its gates |
| LargeHotel | 226 / 70 | [Hotels](2026-10-16-schedule-generator-handover/hotel-expansion-subplan.md) |
| SmallHotel | 255 / 68 | Same plan; no unsupported household-HMM guest adaptation |
| PrimarySchool | 123 / 26 | [Schools](2026-10-16-schedule-generator-handover/schools-expansion-subplan.md) |
| SecondarySchool | 145 / 30 | Same plan; preserve actual seasonal/source Kitchen memberships |
| SuperMarket | 150 / 40 | [Supermarket](2026-10-16-schedule-generator-handover/supermarket-expansion-subplan.md) |
| Hospital | 243 / 54 | [Clinical](2026-10-16-schedule-generator-handover/clinical-expansion-subplan.md) |
| Outpatient | 369 / 50 | Same plan; preserve rates, fixtures, allocations and clinical control semantics |

- [ ] For each family, bind P0 to the actual final predecessor cut/interfaces
  and packaging; do not treat a planning draft's old A5 status/hash as current.
- [ ] Reuse accepted native pilots/source locks, capture only missing evidence,
  implement exact methods/budgets/ownership, qualify all included channels and
  source/reviewed cases, then ship a new cumulative immutable release. Do not
  delay a fully qualified family for an unrelated unfinished family.
- [ ] Execute the [weather plan](2026-10-16-schedule-generator-handover/weather-expansion-subplan.md)
  from its actual W0 predecessor: differentiating domain ledger, missing input
  locks, source proofs, public cases/resources and both-runtime gates. Its old
  planning note is historical, not present authorization.

Weather distinctions that must survive takeover:

- 41 residential fixture contexts already use 37 verified proxy EPWs. They are
  not national weather coverage or county-EPW equivalence. Many required weather
  members are already available; do not download 31 existing resources again.
- Apartment's 37 `(state, latitude, longitude, UTC offset)` tuples are timing
  contexts, not 37 apartment EPWs. Selected timing is independent of weather
  except its actual lighting/location inputs; full residential fan/default
  methods may consume dry-bulb weather and have separate obligations.
- DOE's 16 required location/weather locks are not all resolved. Coastal
  Los Angeles and inland Las Vegas 3B are not Riverside/Sacramento by default.
- Five commercial templates remain distinct: 90.1-2007, 90.1-2013, 90.1-2019,
  DOE Ref 1980–2004, DOE Ref Pre-1980. `climate: null` is not proof of universal
  weather applicability. The 1,900 program/378 composition inventory is not a
  certified all-weather Cartesian product.

## 10. Final review, deferred findings and publication boundary

- [ ] Complete Task 10 family/location coverage review, then one whole-branch
  review from `3e786ad`, with current science/runtime/artifact evidence.
- [ ] Adjudicate the promoted [deferred-findings ledger](2026-10-16-schedule-generator-handover/deferred-findings.md).
  It contains 25 entries, including entries fulfilled naturally; it is not 25
  current bugs. Recorded fulfillments include R82 typo (19) and R137 started
  versus completed frame semantics (25). For A2 descriptor tightening (13),
  inspect the later A4 evidence before final closure. Do not reopen fulfilled
  items blindly.
- [ ] Use one combined final minor-fix wave/scoped rereview where still needed,
  rather than an endless loop. Important failures such as full science/cache
  evidence are not deferred minor findings.
- [ ] Run required source/schema/physical/referential/schedule/provenance/
  reproducibility checks on the final release cut. Historical passing suites
  are evidence for their own cut only; rerun when final changes justify it.
- [ ] Curate durable decisions, source locators, releases, reports and adverse
  limitations; inspect staged diff and run `python -m scripts.audit --staged`
  before EVERY commit. Neutral automated identity; `Agent-Model: unavailable`
  where exact runtime details cannot be verified.
- [ ] Cleanup only after the full objective is complete and needed evidence has
  been retained. No current scratch deletion, worktree archival or reset.
- [ ] Any integration into `main` requires a PR, required checks and resolved
  review conversations. Production deployment remains separate and main-only.

## 11. Review focus and stop conditions

- Loss of a case/member/group/alias despite matching totals: compare exact IDs,
  order, roles and ownership closure at the stage owning that boundary.
- Seed allocation or commercial coordination changed by case splitting: compare
  source positions/draws and actual original union, not only schedule hashes.
- Unknown data silently converted to zero/absence: fail contextually; counts and
  post-run filesystem state must come from emitted, complete checks.
- Resource/time evidence for a different package/runtime/cut: do not promote
  component measurements or cached timings to actual integrated qualification.
- Missing local artifacts: recover explicitly; Git documentation is not an
  executable authority and does not replace raw evidence.

No `Path.resolve`, `realpath`, `stat`, `exists` or target traversal on original
inventory target strings during metadata-only work; use lexical `ntpath`
normalization. Explicitly named source reads are a separate bounded permission.
Never re-read/hash/stat the two R122 17 MiB adverse giant files: their old hash
allowance is consumed; six chunk authorities are the accepted alternative.
Do not follow nested index targets, audit the entire historical graph, rerun
parser finite tests, repeat the 519 s diagnostic, or run the full suite simply
to orient yourself. If a current exact proof is insufficient, state the concrete
gap and plan the smallest new proof; preserve the old outcome.

## 12. Short takeover message

> Take over the paused stochastic schedule extraction on
> `codex/stochastic-schedule-extraction` in its existing isolated worktree. Read
> `docs/superpowers/plans/2026-10-16-schedule-generator-handover.md` first, then
> AGENTS/research brief. Core/staged releases exist; Task 10 and apartment A5
> remain incomplete. Latest R144 templates are sealed but UNREVIEWED and must
> not be activated. First report your review of the checkpoint and local artifact
> availability; resume implementation only when the user requests it. Preserve
> both uncommitted drafts and failed experiments. Use subagents no larger than
> GPT-6.1 Sol, one implementation writer, and the documented scoped gates.
