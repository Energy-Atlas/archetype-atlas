# Plan: the stages after release 1.4.0

Status: **accepted for unsupervised running** (2026-10-27, user answers in section 6).
It plans every stage left after the DOE reconciliation plan
(`2026-10-24-doe-reference-reconciliation.md`, S0–S13, all built). Section 2 carries
forward every question and decision that was still open; section 4 adds the new ones.
Both are discussed together while the stages run (section 5).

**Run:** S (site), L (lighting controls) with G1 (plenums), R1 (review), U (unified
constructions), then X1 (release 2.0.0). **Not run:** W (water heaters, still
deferred) and H (HVAC, not approved).

## 1. Starting point

- **Open PRs, merged by the user in this order:** #18 (release 1.2.0), #20 (1.3.0),
  #19 (1.4.0). Every stage below starts from the tip of #19
  (`codex/residential-families`) and merges `main` in after each merge (rule G2 of the
  residential plan).
- **Built:** releases 1.0.0–1.4.0 (5 commercial templates, 6 IECC commercial
  editions, 7 IECC residential editions, 2 manufactured-housing templates, 41 ResStock
  dwellings), Program JSON 5.1–5.3, constructions 4.1/4.2/3.1 and source model
  constructions 1.0.0.
- **Not built** (each a deferral in an ADR or a release manifest):
  - the suite-based site (ADR 0036 §10);
  - systems: HVAC parameters, plant, and the water heaters of the IECC commercial and
    code-prototype families (ADR 0037 §4, 0040 item 10, 0041 item 12, 0038 §7);
  - the unified construction representation for the IDF families (ADR 0040 item 6);
  - lighting controls (plan C4: evidence only);
  - generator recipes in program files, retiring the frozen folders, folding the
    ADR 0039 input into a full rebuild (ADR 0036 §3, 0039 §3);
  - small gaps: 90 unmapped plenums, the manufactured existing-building category,
    IECC 2024 commercial.

## 2. Carried-forward open items

Each keeps its original wording and source. **Blocks** names the stage that cannot
start until it is answered; the others have a default that applies if unanswered.
Answered on 2026-10-27: P1 and P15 as recommended, P6 kept deferred, P7 reopened
(section 6).

| ID | Item | Source | Recommendation | Blocks |
| --- | --- | --- | --- | --- |
| P1 | **Construction authority for the 90.1 templates.** S3 found real wall, door and glazing differences between the PNNL prototypes and the atlas 90.1 sets. Keep openstudio-standards, adopt the prototypes, or carry both with one as an alternate. | Round 11; ADR 0037:28; `docs/reviews/prototype-equivalence-90-1.md:110` | Keep openstudio-standards; record the prototype assembly as an alternate where U or SHGC differ by more than 1% (the S3 evidence already lists them). | X1 (2.0.0) |
| P2 | Geometry inputs from S3 (hospital, warehouse, plenum mass). | same review :112 | Close: geometry is BEMGen's (round 10); internal mass is already reconciled. | — |
| P3 | Refine the S3 comparison for scoped roof assignments and attic roles before P1. | same review :114 | Not needed if P1 keeps openstudio-standards. | — |
| P4 | **Compare the IECC residential prototypes with the ResStock 2000s/2010s dwellings** of the same type and zone, once residential storage is restructured (O2 option c). | Plan 2026-10-24 O2 | Now unblocked (ADR 0038 is built): stage R1, evidence only. | — |
| P5 | **Agent decisions awaiting review:** ADR 0040 §4 (20), ADR 0041 §4 (21), ADR 0042 §4 (6). The ones later stages build on: 0040-2 (zones 7, 8 keyed `7-a`, `8-a`), 0040-3 (`value` is the most common location value), 0040-14 (unified stub), 0040-20 / 0041-6 / 0042-6 (source-only export), 0041-5 (source model constructions instead of 4.1.0), 0041-7 (mains temperature left unresolved), 0041-8 (ventilators kept as program ventilation), 0042-2 (W/m² basis). | the ADRs | Confirm as they stand; stages W, U and L revisit 0040-14/20, 0041-6/7, 0042-6. | — |
| P6 | **Water heaters deferred** (user, 2026-10-26). | memory; release 1.4.0 notes | Lift it for stage W (filled exports for 1.3.0 and 1.4.0 families). | W |
| P7 | **Daylighting controls: evidence only** (plan C4, user 2026-10-26). Lighting-control recording was discussed on 2026-10-27, not approved. | residential plan :191 | Reopen for stage L with a minimal record. | L |
| P8 | Schedule generator: O4 release build and checksum manifest (not yet), O5 run the updated CI (not now), O10 local pre-purge history copies (deferred). | `2026-10-17-generator-restructure.md` §7 | Settle O4 inside X1, where recipes move into program files. | X1 |
| P9 | Release size: per-context `metadata.selection_decisions` (28.7 MB in 1.0.0, 10.6 MB repeated in 1.3.0/1.4.0) and indented set files (146 MB indented vs 94 MB minified in 1.0.0). | ADR 0036 :177; storage memory | Fix in X1 (evidence tree, compact JSON). | — |
| P10 | BEMGen component changes for the new export majors. | ADR 0036 §9 | Stays with BEMGen; each stage's handoff note lists what changed for it. | — |
| P11 | Stale worktrees: `agent-a18a5d66…` (holds `codex/residential-families`), `agent-acd4ec10…` (`codex/iecc-commercial`), and older Claude/Codex ones. | `git worktree list` | Remove after the PRs merge, on your approval. | — |
| P12 | URL stability: ADR 0003 promised stable URLs and kept alias pages; ADR 0036 §8 retires old IDs "without a compatibility map". | ADR 0003 :114; ADR 0036 :175 | Follow ADR 0036 (see S-2). | — |
| P13 | IECC 2024 commercial, until PNNL publishes. | ADR 0040 item 10 | Check availability at the start of each data release; downloading needs your permission. | — |
| P14 | Manufactured housing has no existing-building category (user decision: documented gap). | ADR 0042 item 7 | Keep the gap; ResStock's 3 manufactured homes are the existing stock. | — |
| P15 | 90 plenums without a standards row (tall, super-tall, detailed offices, laboratory). ADR 0039 chose "excluded, not guessed". | ADR 0039 :55 | Stage G1 maps them (reverses ADR 0039, so it waits for you). | G1 |
| P16 | Residential systems are not stored. | ADR 0038 §7 | Stays until stage H's gate. | H |

## 3. Stages

Workloads are rough agent time, excluding CI and reviews. Every data stage ends with a
minor release (a delta on 1.0.0 holding every change since, ADR 0036), its notes, ADR,
guide, CHANGELOG entry and one PR. The stage table first, then each stage.

| Stage | Release | Workload | Depends on | Status |
| --- | --- | --- | --- | --- |
| **S** Suite-based site | none (site PR) | 4–6 days | #18–#20 merged before it deploys | run |
| **L** Lighting controls | 1.5.0 | 1–2 days | — | run (P7 reopened) |
| **G1** Plenum aliases | 1.5.0 | 0.5 day | — | run (P15 approved) |
| **R1** ResStock vs IECC residential review | none (review doc) | 0.5–1 day | — | run |
| **U** Unified constructions, IECC commercial | 1.6.0 | 2–3 days | L | run |
| **X1** Consolidation, release 2.0.0 | 2.0.0 | 4–7 days | every data stage above | run last (X-1, P1 approved) |
| **W** Water heaters | — | 2–3 days | — | deferred (P6) |
| **H** HVAC | — | — | W | not approved |

S and the data chain (L with G1 → U → X1) touch different files and can run in two
sessions. R1 changes no data and can run in either.

### S. Suite-based site (ADR 0036 §10)

**Today:** `scripts/active_site.py` builds about 79k pages (677 MB) from the frozen
`definition-releases/v0.1.1` and `construction-releases/v2.0.0`; it never reads
`data/atlas-releases`. The roadmap line "Replace per-record pages with suite pages, one
viewer page and one JSON store" (`docs/roadmap.md:242`) is open.

**Work:**
1. An ADR 0036 amendment fixing S-1 to S-9.
2. A generator that reads one release through `atlas_exports.Release` (commercial
   programs, construction sets, building services) and `.dwellings` (residential):
   - one suite page per program (source, department, general, dwelling) with its
     schedules, loads, evidence and alternates anchored inline, and `?version=` and
     context switches in the query string;
   - one suite page per construction set, contexts switched by `?climate=` (and
     `foundation=`, `location=` for residential);
   - one folder page per template × building type (S-3);
   - the `view/?id=` viewer for any dependent object;
   - one content-addressed JSON store replacing `json/` and `delivery/v2`.
3. Search over suite pages; nav and landing counts from the release.
4. New `site_check`, smoke and Playwright tests replacing the `definitions/` and
   `objects/` assumptions; retire `definition_site`, `object_site`,
   `construction_site` and `query_v2` (S-9).
5. CI caches site output under a digest of its inputs (ADR 0036 §1).

**Done when:** `mkdocs build --strict`, the new `site_check`, the smoke and browser
tests pass; every program and set of the release has a page; the site is under the
1 GB ceiling; the guides still render.

### W. Water heaters (deferred, user 2026-10-27)

Kept deferred. The findings and the planned work stay here for when it is lifted; IECC
programs and code-prototype dwellings keep exporting `source` only.

**Today:** no IECC or code-prototype heater records exist. `atlas_exports.py:459`
refuses `filled` for IECC programs and `prototype_dwellings.py:293` for dwellings.
`program_water_heating.py:52` rejects efficiencies above 1, so heat-pump water heaters
(IECC commercial 2021 in 16 of 19 cities; IECC residential 2021 and 2024) cannot be
expressed; `:206` excludes solar.

**Work:**
1. **W1, IECC commercial.** Extract every `WaterHeater:*` (Mixed, Stratified,
   HeatPump) per type, edition, channel and location into
   `data/program-inputs/iecc-dhw-v1.json`, the shape of `dhw-conversion-v1.json` with
   `value_by_climate` (W-1). Answer keys in Buffalo, Miami and Fairbanks (G4).
2. **W2, code prototypes.** Per-dwelling heater entries with `applies_with` on
   heating, climate and foundation (W-2), from all 4,144 residential and the
   manufactured-housing models; answer keys in 4A and `1A-warm-humid`, and every
   manufactured location.
3. **W3, contract.** A Program JSON minor, additive: a heater `technology`
   (`storage`, `tankless`, `heat_pump`) and a `cop` used in place of
   `conversion_efficiency` for heat pumps (W-3); tank volume and standby loss as
   source fields that the draw-only recipe does not use (W-6); solar as W-4.
4. Lift both guards; `filled` exports for every IECC program and code-prototype
   dwelling, in a minor release of its own.

**Done when:** every IECC program and dwelling exports `filled` and validates; heater
answer keys pass at ADR 0035 tolerance; 1.0.0–1.4.0 still verify.

### L. Lighting controls (release 1.5.0)

**Today:** the lighting load holds W/m² and a schedule; occupancy-sensor credits are
already inside the schedule fractions (office weekday 0.9 → 0.797 → 0.753). Nothing
records daylighting. The IECC IDFs hold `Daylighting:Controls` (e.g. medium office 2021
Buffalo: 12 controls, SplitFlux, continuous/off, 377 lux, minimum fractions 0.15, two
reference points controlling 0.38 and 0.14). openstudio-standards holds the rules
(`space_add_daylighting_controls`, 375 lux, minimum 0.2) and the credits in
`spc_typ.json`.

**Work:**
1. Program JSON 5.4.0, an additive minor of 5.3.0, gains an optional
   `lighting_controls` block per program (L-1):
   daylit floor-area fraction, fraction of lights controlled, setpoint (lux), control
   type, minimum power and light fractions, availability schedule; no reference-point
   coordinates (geometry is BEMGen's).
2. IECC commercial: values from the IDFs, `value_by_climate` where locations differ.
3. 90.1 templates (2010 onward in the source; atlas 2013 and 2019): the rule
   parameters from openstudio-standards, with the daylit fraction marked
   `geometry_dependent` (L-2).
4. DOE Ref and residential: a source zero (no controls in the models).
5. Occupancy-sensor credits stay in the schedules and are cited as evidence only (L-3).

**Done when:** every IECC and 90.1 program states its controls or their absence;
answer keys compare the IECC IDFs; the release verifies.

### G1. Plenum aliases (release 1.5.0, with L)

Map the 90 unmapped spaces to their template's `Plenum` row by an alias table with a
reason per entry (as ADR 0040 did for IECC zones); the laboratory plenums use the same
row (G-1). Amends ADR 0039. **Done when:** 1.2.0's `coverage_gaps` is empty in the new
release.

### R1. ResStock vs IECC residential review (P4)

An evidence-only report, `docs/reviews/resstock-vs-iecc-residential.md`, matching
ResStock dwellings (2000s and 2010s vintages) with IECC residential prototypes by
type, zone, foundation and heating: loads, schedules, envelope and infiltration. No
data changes, no pairing (families stay separate). **Done when:** each matched pair's
differences are tabled, and unmatched dwellings listed.

### U. Unified constructions for IECC commercial (release 1.6.0)

**Today:** the unified (equivalent 3.x) form needs a weighting profile per context,
recovered with OpenStudio over the openstudio-standards geometry; the IECC contexts
have none, so they carry a `deferred` stub (ADR 0040 item 14) and the export refuses
them. The 90.1 recipe IDs hash full-precision fit errors, so they reproduce only under
the pinned CPython 3.14.7 on Windows.

**Work:**
1. An IDF-native weighting-profile builder: floor, exposure and mass shares from IDF
   surfaces and zone multipliers (U-1).
2. Run the existing equivalence fit on those profiles; IDs from rounded fit errors so
   the output does not depend on the interpreter (U-2). The 90.1 pins stay as they are.
3. Replace the stubs by a delta overlay (the writer stays pinned, as in ADR 0040
   item 14). Construction-equivalent 3.2.0 if a field is added.
4. Residential and manufactured sets stay without a unified form (U-3).

**Done when:** every IECC context exports `unified` and passes
`construction_delivery_validate` (conservation, schema, shared mass).

### H. HVAC (not approved, 2026-10-27)

Not run, not even the ADR draft. Recorded for later.

**Today:** release 1.0.0 holds 1,005 systems and 2,574 components whose parameters are
all `unknown`; 1.3.0's IECC `systems.json` files are empty; there is no system export.
The IDFs hold full HVAC (DOE Ref 7.2, IECC 22.1, residential 23.1 with AirflowNetwork,
manufactured 8.0).

**Work to the gate, once approved:** an ADR draft answering H-1 to H-3 with a measured
inventory of HVAC object classes per family. **Then stop** for your review;
implementation is planned from the accepted ADR.

### X1. Consolidation: release 2.0.0

**Today:** every minor is a delta on 1.0.0; writers are pinned and patched around with
tagged builder blocks and monkeypatches; 1,900 generator recipes live in
`atlas_schedules/data/recipes/` and are not referenced by release IDs; ten frozen
folder families (about 890 MB) are read by `--check`, the old site and tests.

**Work:**
1. A full snapshot 2.0.0 from rewritten writers (new pins), with the ADR 0039
   construction-only input, the IECC and residential families and every delta folded
   in (X-1).
2. Generator recipes in program files as a `generator` block, for the
   openstudio-standards families that have them (X-3); settles P8 O4.
3. Selection decisions moved to the evidence tree; compact JSON (P9).
4. Frozen folders retired to tags (roadmap :243); releases 1.x become verify-only
   (checksums), as plan S3 of 2026-10-26 allowed (X-2).
5. P1 applied: openstudio-standards stays the 90.1 construction authority, and the
   prototype assembly is an alternate where U or SHGC differ by more than 1%.
6. P8 O4 checked first: the generator's release build and checksum manifest come with
   the recipes. If the generator branch (`codex/stochastic-schedule-extraction`) is
   not on `main` by then, stop and ask.

**Done when:** 2.0.0 reproduces under `--check`; every export equals its 1.x
counterpart except the documented changes; CI no longer reads the frozen folders.

## 4. New questions

**Blocks** marks a question the stage waits for; the others proceed on the
recommendation and record it as an agent decision you can reverse before the PR
merges.

W-, H- rows are parked with their stages.

| ID | Question | Recommendation | Blocks |
| --- | --- | --- | --- |
| S-1 | Which releases the site shows. | **Decided:** the latest release only, with its number on every page; older releases stay as tags and JSON. | — |
| S-2 | Old `definitions/<hash>` URLs. | Retire without a map (ADR 0036 §8); a 404 page with search; ADR 0003's promise amended. | — |
| S-3 | Page grain. | One page per program and per construction set (about 3,300 for 1.4.0, not ADR 0036's 1,175), plus one folder page per template × type for mixes, services, systems and water. | — |
| S-4 | `?version=filled` where only source exists. | Show source with a notice giving the reason. | — |
| S-5 | Annual residential schedules (8,760 values). | A monthly and typical-day plot plus the JSON download; no hourly table. | — |
| S-6 | Store format. | Keep ADR 0011: gzip, SHA-256, packets of at most 131,072 bytes. | — |
| S-7 | Search. | MkDocs search over suite pages; the viewer has its own ID index. | — |
| S-8 | Climate display. | Show the atlas label (`1A-tropical-semi-conditioned`), filter by zone. | — |
| S-9 | Old site generators. | Retire them in the same PR. | — |
| W-1 | IECC heaters that vary by city. | `value_by_climate`, as loads do. | — |
| W-2 | Dwelling heaters. | Program entries with `applies_with` (heating, climate), as IECC 2024 loads; multifamily stores one unit heater with the unit count. | — |
| W-3 | Heat-pump water heaters. | `technology: heat_pump` with `cop` in Program JSON 5.4.0. | — |
| W-4 | Solar water heating in `1A-tropical-semi-conditioned`. | Store the collectors as source equipment; the filled recipe uses the backup heater and marks solar `not_modelled`. | — |
| W-5 | The multifamily shared oil boiler. | HVAC, so it waits for H. | — |
| W-6 | Tank volume and standby loss. | Source fields; the draw-only recipe ignores them. | — |
| L-1 | Where controls live. | A program-level `lighting_controls` block (Program JSON 5.4.0). | — |
| L-2 | 90.1 daylit area depends on geometry. | Store the rule parameters; mark the area `geometry_dependent` for BEMGen. | — |
| L-3 | Occupancy-sensor credits. | Evidence only; they are already in the schedules. | — |
| G-1 | Laboratory plenums have no exact row. | **Decided:** the template's `Plenum` row, recorded as an alias with its reason. | — |
| U-1 | Weighting source for IECC contexts. | An IDF-native profile builder. | — |
| U-2 | Byte pinning of unified IDs. | Rounded fit errors in IDs; tolerance acceptance (ADR 0035). | — |
| U-3 | Residential unified form. | None (R7 stands). | — |
| H-1 | HVAC scope. | Source equipment records for the IDF families (DOE Ref, IECC commercial) first; 90.1 stays rule-based. | H |
| H-2 | Storage. | The existing `systems.json` and `components.json` with parameters filled; loop membership only, no plant topology. | H |
| H-3 | Residential HVAC (P16). | Separate decision after H-1. | H |
| X-1 | Release 2.0.0 as a full snapshot ending the delta chain. | **Decided:** yes, after every data stage. | — |
| X-2 | 1.x releases after 2.0.0. | Verify-only (checksums), no `--check` rebuilds. | — |
| X-3 | Recipes for IECC, residential and manufactured families. | None: they have no generator families. | — |

## 5. How the run works

Carried over from the residential plan (G1–G6), with these changes:

- **Order:** S and L start together in two sessions (different files). G1 joins L in
  release 1.5.0; U follows as 1.6.0; R1 fits anywhere; X1 comes last, after S, L, G1
  and U are merged.
- **Branches:** `codex/atlas-site` and `codex/lighting-controls` from the tip of #19;
  `codex/unified-iecc` from `codex/lighting-controls`; `codex/release-2-0-0` from
  `main` once the others are merged. One PR per release or site change; the agent
  never merges.
- **Decisions:** an agent decides an open point when it has reasoned confidence and
  records it in its ADR's "Agent decisions" (decision, alternatives, reason,
  evidence); the PR repeats them.
- **Discussion:** section 6 of this plan is the running register. Each stage's
  progress note lists the items it defaulted and any new ones; you answer at any time.
  An answer that reverses a default is applied on that branch before its PR merges.
- **Stop only for:** a question marked **Blocks** for the stage at hand; licensing;
  rewriting released data; a download; the same kind of failure three times.
- **Checks before every commit:** `python scripts/audit.py --staged`; Conventional
  Commits with the `Agent-Model` trailer; files written with LF (`write_bytes`).
- **Progress:** an ETA at the start of each stage, a short note at its end.

## 5a. X1 phase 2 stages

Ordered by dependency. X1.1 merged as PR #25. X1.2 to X1.3 run as **milestone A** on
one branch (`codex/release-2-0-0-milestone-a`) and end in one PR, updated with further
commits rather than replaced (user, 2026-10-27); X1.4 opens milestone B. Milestone A
also carries these user answers of 2026-10-27 (register):

- **X1.2a Daylighting as plain values** (L-1), before 2.0.0 is committed: 2.0.0
  drops `lighting_controls.geometry_dependent` (1,373 programs); the "equal values"
  check allows this one change. Program IDs stay those of 1.6.0 (agent decision, ADR
  0046 section 6): milestone B re-derives every ID once, with one map. BEMGen's side:
  `docs/bemgen-handoff-release-2-0-0.md`.
- **X1.3 without stopping:** the agent decides the removal list and writes it into the
  PR description with a reason for each item; an annotated tag
  `frozen-data-2026-10-27` on `main` before removal; releases 1.0.0 to 1.6.0 removed
  from the tree and verifiable from the tag; git history left alone.
- **Status:** 2.0.0 stays `candidate` through milestone A; it becomes `released` in
  milestone B, after the 90.1 IDs move to interpreter-independent hashing (U).
- **PR description:** the agent decisions of ADRs 0040 to 0042, one line each, for
  review (P5).

Milestone B: X1.4 rewritten writers with the interpreter-independent 90.1 IDs (U),
the construction alternates field (P1), the openstudio-standards daylighting rules
fetched and checked (L-2), then 2.0.0 `released` and minor releases on it.

1. **X1.1 Self-contained 2.0.0.** Freeze the run-time inputs into the release
   (`evidence/exporter-inputs.json`: the capped services and programs under release
   IDs, the commercial programs with no setpoint schedules); `Release` reads only
   release files; 2.0.0 verifies by its file checksums alone, its manifest keeps the
   inputs as provenance.
2. **X1.2 DOE Ref recipes.** `build_family_recipes` reads the release programs (1.1.0
   values) and the DOE file geometry for the People topology; the 672 recipes and 60
   configurations are rewritten; catalogue smoke and coverage stay at zero failures;
   2.0.0's `generator.json` gains them. Then commit the 2.0.0 folder.
3. **X1.3 Retire the frozen folders.** Tag the tree before removal; remove the 1.x
   deltas and the v0.x, resolution, water-reporting, completion and construction
   release folders with their builders, recovery scripts and tests; 1.x stays
   verifiable from the tag. CI keeps the 2.0.0 checks; the reproduction jobs of the
   retired releases go, and the required check names stay. The list of removed
   scripts, tests and CI jobs goes into the PR description (user, 2026-10-27; replaces
   "asks first").
4. **X1.4 Rewritten writers.** Writers that read and write the 2.0.0 layout, with
   release enums read from the release, selection decisions in the evidence tree, and
   the construction alternates field (P1). The next minor release is a delta on 2.0.0.

## 6. Discussion register

| Date | ID | Status | Note |
| --- | --- | --- | --- |
| 2026-10-27 | all | open | Plan drafted; questions asked in chat. |
| 2026-10-27 | P6 | decided | Water heaters stay deferred; stage W is not run. |
| 2026-10-27 | P7 | decided | Daylighting reopened: stage L with the minimal record (replaces C4's "evidence only"). |
| 2026-10-27 | S-1 | decided | The site shows the latest release only. |
| 2026-10-27 | P15, G-1 | decided | Plenum aliases approved (amends ADR 0039). |
| 2026-10-27 | P1 | decided | openstudio-standards stays the 90.1 construction authority; prototype assemblies are alternates above 1% difference. |
| 2026-10-27 | X-1 | decided | Release 2.0.0 approved as the last stage. |
| 2026-10-27 | H | not approved | No HVAC work, not even the ADR draft. |
| 2026-10-27 | run | started | User: run S, L, G1, R1, U and X1 through. S proposed as its own session (`codex/atlas-site`, ADR 0043); the data chain runs in the main session. Generator branch confirmed on `main` (X1 stop condition does not apply). |
| 2026-10-27 | L | done | Release 1.5.0 on `codex/lighting-controls`, ADR 0044. 195 programs with controls, 1,178 source zeros; 17 vary by climate (6A–8A skylights). No DOE, residential or manufactured model has controls (0 of 768, 11,840, 1,216). |
| 2026-10-27 | L-2 | agent decision | The pinned openstudio-standards cache has no template daylighting rules, so 90.1 control settings come from the PNNL 90.1 prototypes (same family); the openstudio-standards inputs ride along as `standards_rule`; fractions marked geometry-dependent (ADR 0044 decision 4.1). |
| 2026-10-27 | L | agent decisions | Mixes carry no block; types without a prototype are `unknown`, not zero; lighting-power weighting; availability stored as a descriptor; dwellings export 5.4.0 through a wrapper because release 1.4.0 pins the residential exporters (ADR 0044 section 4). |
| 2026-10-27 | L | open | ADR 0044 section 5: make the 90.1 daylit fractions plain values? Fetch the openstudio-standards template rules (a download) to check them? |
| 2026-10-27 | G1 | done | 90 spaces aliased to Any/Plenum; 38 programs (19 folders); no mix, system or service changes; stored as a delta input so `construction-only-v1.json` stays as 1.2.0 pinned it. |
| 2026-10-27 | G1 | fixed | The export sweep found the 19 new plenum twins could not export `filled` (conditioning unresolved). They now take the 1.0.0 policy's plenum rules (no occupancy, lighting, hot water; unconditioned), as the 1.0.0 office plenums do. |
| 2026-10-27 | finding | issue | Pinned modules hard-code release enums (`prototype_dwellings.construction_schema`, `residential_exports.program_schema`); every later release needs a wrapper until X1 rewrites them. |
| 2026-10-27 | R1 | done | `docs/reviews/resstock-vs-iecc-residential.md`: 10 pairs. ResStock interior lighting runs at a median 0.41× the prototypes, hot water 0.45×, electric equipment 0.87×; window SHGC lower in every prototype. One ResStock 5+ multifamily dwelling records only its refrigerator. |
| 2026-10-27 | L, G1, R1 | PR | #21 (`codex/lighting-controls`), stacked on #19. |
| 2026-10-27 | U | done | Release 1.6.0, ADR 0045, PR #22 (`codex/unified-iecc`). All 1,824 IECC contexts export unified 3.1.0 `ready`; weights are IDF net surface areas; no interpreter pin needed. |
| 2026-10-27 | U | finding | PNNL gives some adiabatic core floors an F-factor construction (570 contexts); left out of the fits and listed in the unified provenance (ADR 0045 decision 4.1). |
| 2026-10-27 | U | open | ADR 0045 section 5: move the 90.1 recipe IDs to interpreter-independent hashing in 2.0.0? |
| 2026-10-27 | X1 | phase 1 done | `scripts.atlas_snapshot`, ADR 0046, PR on `codex/release-2-0-0`: 2.0.0 = resolved 1.6.0 with equal values, compact (439 → 337 MB), generator recipes for 610 90.1 programs in `generator.json`. |
| 2026-10-27 | X1 | blocked | Phase 2 (ADR 0046 section 4): commit the 337 MB folder only with the deltas' retirement (your go-ahead); DOE Ref recipes are stale since 1.1.0 and need regeneration (generator owner); retiring the frozen folders needs stage S merged (the current site reads them); rewritten writers and P1 alternates follow. |
| 2026-10-27 | finding | issue | Repository size: the six 1.x deltas take about 1.1 GB on top of 1.0.0's 216 MB, because each delta repeats every change since 1.0.0. |
| 2026-10-27 | R1 | open | Pair 2010s ResStock with IECC 2009 or 2012? A weather-based conversion of the prototype leakage areas for a like-for-like infiltration comparison? |
| 2026-10-27 | CI | fixed | The 1.5.0+ PRs failed CI: release test classes held whole releases for the rest of the run (about 1.8 GiB each) and the 16 GB Linux runner shut down; the Windows job passed its 60-minute cap. Classes now free their state in `tearDownClass`; the Windows checks run as three jobs behind the required check. |
| 2026-10-27 | merge | done | User: merge CI-cleared PRs. #23 merged with the stack (#18–#22 marked merged); #24 brought up to date with `main` (site now builds from 1.6.0) and set to auto-merge. |
| 2026-10-27 | X1 phase 2 | decided | User: commit 2.0.0; regenerate the DOE Ref recipes; rewrite the pinned writers after the merges. |
| 2026-10-27 | X1 | correction | ADR 0046 section 4 item 2 said regeneration re-baselines the generator answer keys; they hold no DOE Ref cases, so only the packaged recipes and configurations change, checked by the catalogue smoke and coverage runs. |
| 2026-10-27 | X1 | finding | Every `atlas_exports.Release`, 2.0.0 included, still reads the frozen folders at run time: release verification re-hashes their manifests, filled exports read `definition-releases/v0.1.1` (capped delivery, ADR 0018), and the source exporter reads `data/releases/v0.2.0/programs.json` (inactive controls). 2.0.0 must carry these before the folders can go. |
| 2026-10-27 | milestone A | decided | User: run X1.2, commit 2.0.0 and X1.3 as one milestone on one branch, with one PR at the end, updated with further commits rather than replaced. |
| 2026-10-27 | X1.3 tag | decided | Push an annotated tag `frozen-data-2026-10-27` on `main` before the frozen folders are removed. |
| 2026-10-27 | X-2 | decided | Releases 1.0.0 to 1.6.0 leave the tree (about 1.3 GB) and stay verifiable from the tag; replaces "verify-only in the tree". |
| 2026-10-27 | X1.3 list | decided | The agent decides the removal list and writes it into the PR description with a reason per item; no stop mid-run. |
| 2026-10-27 | finding (repository size) | resolved | User: leave git history alone for now (no filter-repo purge, no new repository); removing the folders shrinks the checkout, not the clone. Reopen if clone size becomes a problem. |
| 2026-10-27 | X1 status | decided | 2.0.0 stays `candidate` through milestone A and is declared `released` in milestone B, after the 90.1 IDs change (U). |
| 2026-10-27 | U | decided | The 90.1 construction IDs move to interpreter-independent hashing in milestone B (X1.4), with a published map from old to new IDs; the Windows pinned-producer jobs then go. |
| 2026-10-27 | L-1 (ADR 0044 §5) | decided | Daylit fractions become plain values now: 2.0.0 drops `geometry_dependent` (stage X1.2a). BEMGen's updates are logged in `docs/bemgen-handoff-release-2-0-0.md`. |
| 2026-10-27 | L-2 (ADR 0044 §5) | decided | Fetch the openstudio-standards template daylighting rules in milestone B, pinned in a source lock, and check the 90.1 records against them. The download is approved by this answer. |
| 2026-10-27 | R1-a | discussed | User asked why ResStock existing stock is paired with a new-construction code. Answer: the IECC prototypes are the only code-labelled reference with the same end uses; the edition stands for the code in force when the dwelling was built. Only envelope and interior lighting differ by edition (IECC 2009 and 2012 require 50% and 75% high-efficacy lamps); equipment and hot water are the prototypes' fixed reference-home assumptions. Revised recommendation in chat; waits for the user. |
| 2026-10-27 | R1-b | decided | Convert the prototype leakage areas to annual-average ACH only once a consumer needs the comparison; until then the review states the caveat. |
| 2026-10-27 | P5 | decided | The agent decisions of ADRs 0040 to 0042 go into the milestone A PR description, one line each, for review there. |
| 2026-10-27 | X1.2 | done | `scripts/build_reference_recipes.py` writes the DOE Ref recipes from release 2.0.0 under release IDs (279 commercial, 72 composition, 6 Midrise; 30 configurations; 54 services; 422 schedules), with People topology from the DOE file zones; it replaces 786 packaged files built from the frozen definitions. `tests/test_reference_recipes.py` checks every value against the release. |
| 2026-10-27 | X1.2 | correction | The DOE Ref answer-key claim (row "X1 correction") was wrong: the native and legacy keys capture 66 + 96 programs, 60 configurations and 149 legacy programs of the replaced recipes. Agent decision: keep the captures, list the replaced IDs in `tests/answer_keys/retired-doe-ref.json`, skip those cases in the tests (ADR 0046 section 6, decision 4). |
| 2026-10-27 | X1.2 | agent decisions | Source recipes only for DOE Ref (the fills change no slot); the generator request schema accepts release IDs (additive); Midrise keeps the frozen recipe shapes; types without a sampler stay without recipes (ADR 0046 section 6). |
| 2026-10-27 | X1.2a | done, agent decision | 2.0.0 drops `geometry_dependent` from 1,373 programs. Program IDs stay those of 1.6.0 rather than being re-hashed now and again in milestone B (ADR 0046 section 6, decision 1). |
| 2026-10-27 | X1.2 | done | 2.0.0 committed (`b44984ec`); the full site builds from it (3,051 program, 291 construction and 255 folder pages, not partial). `mkdocs build` and `site_check` run in CI (mkdocs-material is not installed locally). |
| 2026-10-27 | X1.3 | done | Tag `frozen-data-2026-10-27` pushed on `main` (`fdb07f9d`). About 2.45 GB of frozen folders and inputs, 80 scripts and 68 test modules removed (list in the PR description); readers rewired to 2.0.0; CI reshaped under the same required checks (ADR 0046 section 7). |
| 2026-10-27 | X1.3 | agent decisions | Kept: the construction-equivalence fitting engine (U needs it), the DOE reconciliation tooling and `atlas_programs.Sources` (unreachable from CI; milestone B replaces them), `data/processed` and its pipeline. Retired with their inputs: `schedule_coverage`, `program_completeness`, `build_family_recipes`, the IECC and ResStock review generators (their reports stay). The Program JSON v3 exporter tests that ran on the frozen definitions went; the full site build exports every 2.0.0 program in CI. |
| 2026-10-28 | R1-a | deferred | User: defer. The review pairs 2000s dwellings with IECC 2006 and 2010s with 2012; 2009, 2015, 2018, 2021 and 2024 are compared against nothing. Proposed when reopened: an edition ladder (loads against the reference-home assumptions once; envelope and lighting against every edition in force per vintage; 2018 to 2024 as a new-construction reference only). |
