# DOE reference reconciliation plan

Status: **round 4.** Your round-3 answers (given in chat) are recorded in section 0b. The
questions still open after them are in **section 6c**; sections 0 to 6b are kept as they
were.

## 0g. Round 11: after the S3 gate (given in chat)

- **S3 found real construction differences** between the PNNL prototypes and the atlas
  90.1 templates: walls, doors and some glazing
  ([review](../../reviews/prototype-equivalence-90-1.md)).
- **Decision:** record those differences as evidence only, and decide the 90.1
  construction authority separately.
- Continue S4–S9 for the DOE reconciliation (release v1.1.0).

## 0f. Round 9 (given in chat)

- **IECC is a completely different family from ASHRAE.** IECC commercial
  (`iecc_commercial_prototype`), IECC residential (`iecc_residential_prototype`) and
  manufactured housing (`manufactured_housing_prototype`) are separate source families.
  They have no pairing with the 90.1 editions and share no records with them; geometry
  is the one exception.
- Section 9 is updated: the family structure table and stages S11–S13.

## 0e. Round 7: answers to O1–O4 (given in chat)

- **O1, register:** (a). One register, `data/reconciliation/doe-reference-v1.json`, and one
  generated page, with `source_family` on every row.
  - The register is atlas-internal: it is the audit trail, a build input and a test input.
  - BEMGen never receives it. BEMGen sees only the resulting values, their provenance and
    any alternates, through the consumer exports.
- **O2, residential:** treat the residential and manufactured prototypes as new families,
  aligned to the 90.1 family (2007, 2013, 2019).
  - How the prototypes' IECC and HUD years map onto that alignment is open as **S-Q1** in
    section 9.
- **O3, versioning:** (a). The DOE reconciliation is v1.1.0, and the construction-only
  programs are v1.2.0.
- **O4, kickoff:** accepted. All work stages are planned in **section 9**.

## 0d. Round 6: pre-kickoff answers (given in chat)

**Recorded decisions:**
1. **DOE Ref load and schedule fixes:** (b). Keep them as decided (holidays, conversion
   errors, edits, heat fractions, fills). They are the deterministic baseline that the
   stochastic schedules will be checked against. The "loads don't matter" rule applies
   only to prototype vs openstudio-standards.
2. **Equivalence proof scope:** accepted.
   - Geometry (zones, areas, heights, footprint, windows, skylights), constructions
     (layers, U-value, SHGC per surface type), infiltration, internal mass and WWR.
   - Not HVAC.
   - Tolerance about 1% (ADR 0035 style).
   - Coverage: 90.1-2007, 2013 and 2019 × 16 types, apartments included, against the
     matching climate contexts.
3. **Q5c:**
   - The "explicitly wrong" rule covers occupancy as well as power densities.
   - DOE goes in as an alternate only where the two differ by more than 50%.
   - The cafe case is kept.
4. **Q1-D':** you asked what a register is. Explained below; still open.
5. **Q16-B:**
   - Per-zone skylight ratios that vary by climate: store the majority climate group's
     value in the program, with the others as alternates.
   - Mixed zones: split windows and walls by area share.
6. **Residential:** you said no comparison is needed if the atlas never had
   single-family, and that prototype apartments should be compared with the existing
   up-to-code apartment definitions. The premise does not hold; see below, still open.
7. **IECC and manufactured housing:**
   - Extraction straight from the prototype IDFs is accepted (the IDF is the primary
     source, recorded in an ADR).
   - Manufactured housing goes under `residential/` as a new family.
8. **Redundant prototype bundles:** done.
   - `ASHRAE901_all`, `IECC_all` and `ASHRAE901_epw` were moved to the Recycle Bin,
     about 27 GB, so they can be restored.
   - Check first: the two "all" bundles duplicated every IDF, results file and scorecard
     byte for byte. Their only unique content was weather files, which are out of scope.
   - The manifest keeps their records, marked as moved.

### Still open

**O1. What a register is (Q1-D').**
- The register is the file that holds every reconciliation decision, one row per item.
  The site page is generated from it, and the tests read it.
- Example row, the holiday case for one schedule:

```json
{
  "id": "rec-0042",
  "source_family": "doe-reference",
  "category": "inconsistency",
  "class": "A1-holidays",
  "template": "doe-ref-1980-2004",
  "building_type": "medium-office",
  "target": "schedules.json#doe-ref-1980-2004.medium-office.medium-office-bldg-occ",
  "field": "rules (Hol)",
  "current": {"value": "holiday uses the weekday Default profile", "locator": "data/atlas-releases/v1.0.0/commercial/doe-ref-1980-2004/medium-office/schedules.json"},
  "source_value": {"value": "holiday uses the Sunday profile", "file": "refbldg_mediumoffice_post1980_v1-4_7-2/…_5A_USA_IL_CHICAGO-OHARE.idf", "sha256": "…", "object": "Schedule:Compact BLDG_OCC_SCH", "line": 7350},
  "upstream_evidence": {"row": "Medium Office Bldg Occ", "last_semantic_edit": "2015-10-27"},
  "decision": "replace",
  "reason_id": null,
  "alternate": null
}
```

- **What Q1-D' asked:** whether DOE-reference rows and PNNL-prototype rows go into one
  file, told apart by `source_family`, or into two files.
- **Updated options:**
  - [ ] (a) One register, one generated page, with `source_family` on every row.
  - [ ] (b) Two registers and two pages.
- **Recommendation:** (a). Either way, each atlas value cites exactly one source family.
- **Your choice / notes:**

**O2. Residential: the atlas already has single-family and manufactured homes.**
- **What the atlas has:** the release v0.2.0 `residential_archetypes.json` holds 41 ResStock
  configurations:
  - 22 single-family detached
  - 5 single-family attached
  - 6 multifamily 5+ low-rise
  - 3 multifamily 2–4
  - 3 manufactured homes
  - 1 midrise and 1 high-rise apartment
- These are existing-stock sample rows (vintages from before 1940 to the 2010s). Their
  storage under ADR 0036 is deferred, which is why they are easy to miss.
- **Consequences:**
  - Single-family and multifamily do exist, as ResStock existing stock.
  - Manufactured housing exists too, as 3 ResStock existing-stock homes. So the
    "no existing manufactured housing" gap is partly covered by ResStock.
  - The prototypes are new construction by IECC code, while ResStock is sampled stock.
    They are different families, and matching them needs a key (type, climate zone,
    vintage 2000s/2010s, foundation, heating).
  - The commercial prototype apartments (Midrise and Highrise, 90.1) are already covered
    by the equivalence proof against the atlas 90.1 apartment programs.
- **Updated options:**
  - [ ] (a) Treat the residential and manufactured prototypes as new new-construction
    families, with no comparison against ResStock existing stock. Record the overlap as
    a note.
  - [ ] (b) Compare the residential prototypes against the ResStock 2000s/2010s
    configurations of the same type and climate zone, and discuss the real differences.
  - [ ] (c) As (a) now, and do (b) when residential storage is restructured.
- **Recommendation:** (c). The families differ by definition (code vs stock), and the
  ResStock records are not in the new storage yet.
- **Your choice / notes:**

**O3. Release versioning: reconciliation vs construction-only programs (section 8).**
Both target a delta release on top of v1.0.0.
- [ ] (a) DOE reconciliation as v1.1.0, then construction-only programs as v1.2.0.
- [ ] (b) Construction-only programs first (v1.1.0), then the reconciliation (v1.2.0).
- [ ] (c) One combined v1.1.0.
- **Recommendation:** (a). The reconciliation is planned and reviewed, and separate
  releases keep the reviews separate.
- **Your choice / notes:**

**O4. Kickoff order and branch.**
1. Create `codex/doe-reference-reconciliation` from `main`, and commit this plan doc
   there (this worktree's branch is stale).
2. Phase 0: pin the 48 DOE zips and 163 prototype archives in `sources/`, and move the
   comparison scripts into `scripts/`.
3. The 90.1-vs-prototype equivalence proof.
4. ADR 0037, the register and release v1.1.0.
5. Then section 8, IECC, residential and manufactured housing.
- [ ] accepted  [ ] change:
- **Your choice / notes:**

## 0c. Round 5: your direction after round 4 (given in chat)

**Which differences matter.**
- Differences in geometry and construction are hard to change across definitions, so
  they matter.
- Schedules, occupancy and the other loads are easy to change. They will be replaced by
  stochastic schedules derived from ResStock and ComStock anyway.
- So if the prototypes and openstudio-standards differ *only* in those, we do not care.
- The goal is to show that the PNNL prototypes equal the atlas's new-construction 90.1
  templates (openstudio-standards) in every aspect we care about. This is to be proven,
  not assumed.
- Consequences:
  - Q1-B' (constant schedules) and Q1-C' (prototype vs atlas load densities) no longer
    need a replace-or-keep decision. The prototype values are recorded as evidence only.
  - The equivalence proof is the next piece of work: geometry and construction, including
    fenestration (see below).

**Q16-B decision 1, settled:**
- Per-zone WWR (N, E, S, W, roof) lives in the **program definitions**.
- The 15 whole-building values (5 directions × conditioned, unconditioned and all zone
  surfaces) live in the **construction package**.
- A whole-building program carries the whole-building WWR, which by definition equals the
  construction-level building record. These are two representations of the same
  information in two parts of the atlas; a test checks that they agree.

**Phases, revised:**
1. **DOE reference (existing buildings):** kept as they are. The existing-building
   templates come only from the reference buildings.
2. **90.1 new construction vs prototypes:** prove that they are the same in what matters.
   If they are, add no templates; the atlas 90.1 templates are then declared backed by
   both the openstudio-standards source and the prototype models. Real differences are
   discussed.
3. **IECC:** not in the current ComStock-style definitions. Extract the same level of
   definition, in the same schema as the ComStock/DOE reference definitions, as new
   templates.
4. **Residential prototypes:** compare them against the existing residential definitions:
   the 90.1, existing-building and reference-building style ones, such as the Midrise and
   Highrise Apartment programs and the ResStock configurations. If they differ only in
   occupancy, they count as the same; real differences are discussed.
5. **Manufactured housing:** not in the repository anywhere, so it is incorporated fully,
   possibly as a new program family.
   - The prototypes are all new builds up to code; there is no existing-building
     manufactured-housing category.
   - That gap cannot be bridged and is documented as such.

**New bucket-list item:** "Complete the program catalogue for the construction-only
building types". These are 51 template × building-type folders that have construction
sets but no programs. It is kept in this doc only for now (section 8), not filed as a
GitHub issue.

- **Your notes:**

## 0b. Round 4 summary: your round-3 answers

- **WWR goes into the program** for now (not the construction package).
- **Q1-A:** (b), phased, with a plan for adding everything (section 6c, "Plan for adding
  everything").
- **Q1-B:** no need to worry *if* the prototypes have no missing or constant schedules.
  The inspection found none missing, but many constant ones, so this stays open as
  **Q1-B'**.
- **Q1-C:** discuss the inconsistencies (below). Regardless of that, reference-building
  power densities (the existing, not-up-to-code templates) are not replaced unless they
  are explicitly wrong. This revisits Q5b, now **Q5c**.
- **Q1-D:** you asked why keep them apart, since they are variants like the code
  templates we already have. Answered in **Q1-D'**.
- **Q8-A:** (a), reference the schedule by ID ("ok if it has to").
- **Q15-A:** document Basement as a program in every building type that has one.
- **Q16-A:** store directional WWR in the program definition:
  - per zone or program, five directions: N, E, S, W and roof (skylight);
  - plus whole-building area-weighted averages over conditioned zone surfaces,
    unconditioned zone surfaces and all zone surfaces (5 directions × 3 = 15 values).
  - The follow-ups are in **Q16-B**.

Status (round 3): **round 3.** Your round-2 annotations are processed.
- **Round 3 summary** (section 0) lists what you decided and what is still open.
- **Section 6b** holds the questions that are still open or new. Each gives the original
  question, my recommendation, your feedback, the new evidence, updated options and a
  recommendation, with space for your choice.
- **Sections 1–6 are kept as you annotated them in round 2**, so your notes stay where
  you wrote them.

Mark a choice with `[x]` and write in the **Notes** lines.

## 0. Round 3 summary

**Decided in round 2:**
- **Q2:** (a), the matching vintage.
- **Q3b:** (c).
  - Rows that have differed since their first import: replace.
  - Warehouse 2024 ComStock calibration: keep, with the DOE value as an alternate.
  - Supermarket 2025 edit aimed at 90.1: replace in DOE Ref, keep in 90.1.
- **Q5b:** (a), replace all.
- **Q8:** the shape is accepted; your comment is answered in 6b, with one small new
  choice.
- **Q12:** (c). No new-2004 template; the files become evidence and a cross-check for any
  future 90.1-2004 template.
- **Q15:** (a), add a Large Office basement program. Your follow-up ("what about other
  basement programs?") is answered in 6b.
- **Q16:** directional N/E/S/W WWR plus a skylight ratio, relative to the program's (or
  merged program/zone's) own geometry, averaged by area. The follow-ups are in 6b.
- **Q17:** all four as recommended:
  - A12 replace
  - B8 fill
  - C13 omit
  - Hospital Office1 multiplier: use DOE (4)
- **Q1:** your direction is to include the PNNL prototype models fully, kept separate from
  the reference buildings, with permission to download. The download and its inventory
  are in 6b, along with the new scope questions.

**Still open (section 6b):** Q1-A, Q1-B, Q1-C, Q1-D, Q8-A, Q15-A and Q16-A.

Related: GitHub issues #13 (typological consistency with BEMGen) and #14 (reference
schedules for program presets).

## 1. Purpose

Reconcile the atlas's DOE Reference templates with the DOE Commercial Reference
Building files (v1.4_7.2) and record a decision for every item in one of three
categories.

| Category | Decision without a reason | Decision that needs a reason |
| --- | --- | --- |
| A. Inconsistency: atlas value a differs from DOE value b | **replace** (a becomes b) | **keep** (a stays) |
| B. Gap: the atlas value is null or unknown, DOE has one | **fill** (null becomes b) | **leave** (stays null) |
| C. Missing component: DOE has it, the atlas does not | **add** | **omit** |

Each reason is written once in a reason table (for example "R-ADR0020: fixed natural
ACH is the accepted infiltration method") and cited by ID. Where two backed values are
both kept, the register records an **alternate value**: the second value with its own
source and reason, shipped in the same artifact.

Notes:

## 2. What the evidence shows so far

The scripts and JSON results are in the session scratchpad and move into `scripts/` in
phase 0.

- **Sources.**
  - The 48 per-building v1.4 zips (16 types × new 2004, post-1980 and pre-1980) are
    official energy.gov files.
  - Sizes match the live server, and checksums match Internet Archive captures.
  - Local copies are in `D:\Reference Building Models\v1.4_7.2\`, with
    `SOURCES-v1.4_7.2-post1980-pre1980.json` and `SHA256SUMS-…txt`.
  - Licence: US government work, public domain under energy.gov policy, with
    attribution requested.
- **Vintages.**
  - Geometry, schedules, and occupancy, plug and gas loads are the same in all three
    vintages.
  - Lighting, the infiltration rate (new 2004: 0.000302 m³/s·m²; post-1980 and
    pre-1980: 0.001133 m³/s·m²), envelope and HVAC change.
  - Pre-1980 also changes a few HVAC schedules.
  - "New 2004" means new construction to 90.1-2004; post-1980 means 90.1-1989.
- **Schedules, like for like.** 204 references from loads, thermostats, water use and
  infiltration, compared over the full year with holidays and design days:
  - 74 identical
  - 57–59 differ only on holidays
  - ~22 openstudio-standards edited the row
  - ~11–13 openstudio-standards assigned a different schedule
  - 23–26 outside program scope
  - the rest have no counterpart
- **Loads, like for like.**
  - 94–100% of 397 zones match per load, and gas matches in every zone.
  - People heat fractions match everywhere; lights and equipment fractions match in
    almost every zone (see A12).
  - Internal mass is 2.0 m² per m² of floor in every DOE zone, matching the atlas where
    the atlas has an entry (see B8).
- **Hot water.**
  - All 5,232 water-use objects in the non-residential files (all vintages and
    climates) name a zone and use constant fractions of 0.2 sensible and 0.05 latent.
  - Water heaters lose heat to a constant 22 °C, not to a zone.
  - Retail, strip mall and warehouse have no hot water.
- **Release basis.**
  - `main` moved from `e57d6a1` to `0ec58c0` (PR #15).
  - The 197 program files that changed differ only in identifiers; construction
    packages and evidence are byte-identical.
  - So the comparisons stand; phase 0 still reruns them from `scripts/`.

Notes:

## 3. How it is documented

- **Register:** `data/reconciliation/doe-reference-v1.json`, one row per item. Each row
  holds:
  - category, class, template, building type, program, schedule or zone, and field
  - current value a, with its atlas location
  - DOE value b, with IDF file, SHA-256, object, field and line
  - the decision and, where required, its reason ID
  - the openstudio-standards row as evidence, with the date of its last semantic edit
    and the commit (section 5, A3 and A5)
  - an alternate value, if any
- **Site page:** `website/content/guides/doe-reference-reconciliation.md`, generated
  from the register (Q13 decided) and added to the site nav. It opens with the rules and
  the reason table, then has one table per building type: item, a, b, decision, reason.
- **Tests:**
  - no item is undecided
  - every keep, leave or omit cites a reason
  - the page matches the register
  - DOE Ref values equal the DOE value unless a keep row says otherwise

Notes:

## 4. Phases

All work goes on a new branch, `codex/doe-reference-reconciliation`, from `main`.

0. **Source.**
   - Pin the 48 zips in `sources/lock.json`: URL, size, SHA-256, and an Internet Archive
     fallback.
   - Add a locked-fetch script and an IDF reader module.
   - Move the comparisons and the openstudio-standards history trace into `scripts/`.
1. **Policy.** ADR 0037 records the authority rule, the scope, the reason table, the
   "newer edit" rule (A3/A5), the alternate-value rule, and the answers to section 6.
   It amends ADR 0018 (hot-water gains) and ADR 0020 (a second infiltration method).
2. **Register.** Generate candidate rows with an automatic class, then review each class
   and set its decision.
3. **Apply.** Release v1.1.0 as a delta release under ADR 0036 (Q14 decided).
   - Replaced, filled and added values cite the DOE file.
   - Superseded openstudio-standards values stay as evidence.
   - Regenerate the consumer exports. New fields (hot-water fractions, a second
     infiltration method, fenestration defaults) need a minor contract version.
4. **Verify.** Use the DOE files as an answer key at engineering tolerance (as in ADR
   0035). Generate the site page.
5. **Downstream.** Hand BEMGen the changes:
   - the holiday calendar
   - building services and refrigeration
   - hot-water draws with zone gains
   - the DOE infiltration method
   - the fenestration defaults

Notes:

## 5. Inventory and recorded decisions

### A. Inconsistencies

**A1. Holidays.** Decided: **replace**. Size: 57–59 references, 120 schedules.

**A2. openstudio-standards conversion errors.** Decided: **replace**.
- Items: school heating and cooling setpoints (weekends at the occupied setpoint all
  year) and the 1 September overlap.
- Only the DOE Ref templates are affected: four schedules each in `doe-ref-1980-2004`
  and `doe-ref-pre-1980`.
- The same shared-boundary convention (a rule ending on the day the next one starts)
  appears in 48 DOE Ref and 51–53 schedules per 90.1 template. It matters only where
  the two rules differ on that day, which the full-year comparison catches.

**A3. openstudio-standards schedule edits.** Open; see **Q3b**. The history trace
answers your "which is newer" question.

**A4. Assignment.** Decided: **replace**. Your question was why openstudio-standards
does this. There are two causes, neither an intentional change:
1. **Generic schedule names in the DOE Ref space-type table.**
   - Since the first import (2015-10-27, "Initial NREL/NRCAN code"), the DOE Ref rows
     give small and medium office the same `Office Bldg Light`.
   - The DOE Medium Office file uses the large-office lighting shape, which also exists
     upstream as `Medium Office Bldg Light` but is not referenced.
   - The primary-school rows likewise give the kitchen and office the generic
     `PrimarySchool Bldg Occ`, where DOE has separate schedules.
   - The 90.1 rows use per-prototype names (`OfficeMedium BLDG_LIGHT_SCH_2004`), so this
     looks like a simplification when the DOE Ref table was assembled.
2. **Space-type tags in the shared geometry files.**
   - `ASHRAEOutpatient.osm` tags 14 storage and utility rooms "Outpatient Janitor", for
     example Sterile Storage (line 73) and Utility Room (line 287). It is used by every
     template.
   - `DOERefPrimarySchool.osm` tags Computer_Class (line 321) and Library (line 514) as
     Classroom, although a Library row exists. `ASHRAEPrimarySchool.osm` tags them
     correctly.
- Implementation note: replacing means re-tagging these spaces. The primary-school suite
  then gains a Library program, and the outpatient storage rooms get their DOE plug load
  (1.08 W/m²).

**A5. Load values.** Open; see **Q5b**. The history trace answers "which is newer".

**A6. ER triage plug load.** Decided: **29.05 W/m²**. The v1.3 scorecard's 21.53 goes
into the evidence. Upstream history: openstudio-standards had 2.0 W/ft² until a 2016-06-03
bulk regeneration; since then it has been null in 1980-2004 and 2.67 W/ft² in pre-1980.

**A7. Rounding.** Decided: **keep** (reason: same source value, rounded in the file).

**A8. Schedule times inside an hour.** Decided: **keep hourly means** (Q9). Size: 34
schedules.

**A9. Design days.** Decided: **replace**.

**A10. Infiltration method.** Decided: **add as a second method** (Q8). Both methods ship
side by side in the same construction artifact. Details are under Q8 in section 6 for
the record; no new question.

**A11. Heat fractions and internal mass.** Compared; the results are new items A12 and
B8. They need your confirmation in **Q17**.

**A12 (new). Heat-fraction differences.** Proposed: **replace**, for the DOE Ref
templates.
- **Differences the DOE Ref templates have:**
  - Quick-service restaurant dining lights: radiant fraction 0.7 in DOE vs 0.37.
  - Supermarket bakery and deli gas fractions: latent / radiant / lost 0 / 0.5 / 0 in
    DOE vs 0.1 / 0.2 / 0.7.
  - Small hotel laundry plug radiant: 0.2 in DOE vs 0.5.
  - Outpatient sterile storage plug: radiant 0.5, lost 0 in DOE vs 0.3 / 0.7. This
    follows from the A4 re-tagging.
- **Already correct:** elevator and exhaust objects carry radiant 0 and lost 1.0 in DOE,
  and the atlas folds them into row fractions. This is handled by C3, which adds them
  as separate building services.
- **Out of scope:** the new 2004 differences (Medium Office lights, warehouse, hospital
  kitchen and others) are against 90.1-2007 rows (Q1 and Q12).

### B. Gaps

**B1. Hot-water schedules.** Decided: **fill** from the DOE zone draws, with zero where a
DOE zone has no draw (Q4).

**B2. Additional lighting.** Decided: **fill** zero where the atlas base LPD already equals
the DOE total; otherwise leave, with a reason.

**B3. Plenum and attic equipment schedules.** Decided: **fill** zero.

**B4. Small-hotel mixes.** Decided: **fill** from the matching DOE zones.

**B5. ER triage.** Decided: **fill**, 29.05 W/m².

**B6. Data-centre leap day.** Decided: **leave** (reason: no DOE counterpart).

**B7. Existing zero fills.** Recorded as confirmed.

**B8 (new). Internal-mass coverage.** Proposed: **fill** 2.0 m²/m², the DOE value. Needs
your confirmation in **Q17**.
- openstudio-standards adds internal mass only to spaces that are both heated and
  cooled (`Prototype.Model.rb:696-740`); the DOE files put it in every zone.
- So the atlas has none for:
  - warehouse bulk storage (6,410 m²)
  - retail front entry
  - 17 small-hotel stair, elevator and storage zones (post-1980 and pre-1980)

### C. Missing components

**C1. Holiday calendar.** Decided: **add**. Your note: schedules will become parametric
(year, holiday array, stochastic generators), so the calendar is an input, not a fixed
part of each schedule.

**C2. Daylight saving time.** Decided: **add** as metadata, not applied to schedules.

**C3. Building services** (elevators, kitchen exhaust fans, exterior lights). Decided:
**add**.

**C4. Refrigeration cases and racks.** Decided: **add**.

**C5. Hot-water zone gain fractions.** Decided: **add and apply** (Q6 b). What the new
inspection shows, for the record:
- **Fractions:** all 5,232 water-use objects use constant 0.2 sensible and 0.05 latent.
  There is no variation by zone, type, vintage or climate, so one constant pair per draw
  is enough.
- **How EnergyPlus uses them** (`WaterUse.cc:1165-1200`):
  - Sensible gain = sensible fraction × mass flow × cp × (mixed water temperature −
    zone air temperature).
  - Latent gain = latent fraction × the water that can evaporate (the smaller of the
    draw's water mass and what the zone air can absorb before saturation) × latent heat.
  - So the latent fraction is a share of evaporable water, not of heat.
  - Both fractions are schedules per water-use object, so they can vary in time; DOE
    keeps them constant.
- **Inputs the gain needs:** the mixed temperature, which needs the target temperature
  (DOE 43.3 °C) and the hot-supply temperature schedule. The cold side is mains water,
  supplied by BEMGen at IDF creation (C11). The atlas already ships target
  temperatures.

**C6. Humidity setpoints** (hospital, outpatient). Decided: **add** as program controls.

**C7. Systems side.** Decided: **omit**, including water heaters (your Q10 note: BEMGen
tests at ideal-loads grade, so neither the HVAC water loop nor DHW heating equipment
counts). The water-use draws themselves stay, because C5 needs them for zone gains.

**C8. Large Office basement program.** Open; see **Q15**.

**C9. A new-2004 template.** Open; see **Q12**.

**C10. Fenestration defaults.** Your note: include default WWR in constructions,
separating façade and roof (skylight). Direction recorded; the details are open in
**Q16**.

**C11. Site, weather and cost data.** Decided: **omit**. BEMGen supplies these at IDF
creation; benches need no sizing or tariffs.

**C12. Comfort-only People fields.** Decided: **omit**.

**C13 (new). Lights "replaceable" fraction** (1.0 in every DOE file; the atlas does not
store it). Proposed: **omit** (reason: it only affects daylighting control, and the DOE
Ref models have none). Confirm in **Q17**.

## 6. Open questions

### Q1. Scope of authority

- **Original question:** should the DOE files' authority apply to the DOE Ref templates
  only, or should shared fixes such as holidays also go to the 90.1 templates?
- **Original recommendation:** (a) DOE Ref only.
- **Your feedback:** "i am leaning towards b but discuss why you think b is not
  recommended. what other shared fixes than holidays are we talking about?"
- **Why I recommended against (b):**
  - The 90.1 templates' source is the PNNL prototype models, not these DOE files.
  - A fix is safe to share only if it is a structural error that does not depend on the
    source. Pulling DOE-specific values into code models would mix source families,
    which the repository rules forbid.
- **Candidate shared fixes, checked against the 90.1 templates:**

| Fix | Present in 90.1 templates? | Shareable? |
| --- | --- | --- |
| Holidays falling back to the weekday profile | Much smaller: 19 such schedules vs 120 in DOE Ref; 405 already fall back to a Sunday-like default | Structural, but the holiday convention should be confirmed against the PNNL prototypes |
| School weekend-setpoint conversion error | No: 90.1 schools use other rows | Not applicable |
| Rule ending on the day the next one starts | Yes, 51–53 schedules per template | Structural, but harmless unless the rules differ on that day |
| Outpatient storage rooms tagged Janitor | Yes: the same geometry file serves every template | Structural; DOE plug value 1.08 W/m² |
| Supermarket Produce plug 0.05 W/ft² (DOE: 0.5) | Yes: every 90.1 row has 0.05 | Value. PNNL may differ, so check the PNNL model first |
| Internal mass only in heated-and-cooled spaces | Yes; small hotel 90.1 has none | Code-level rule; check PNNL |
| The 2025 supermarket schedule edit (Q3b) | It was aimed at 90.1 models | Keep in 90.1 by design |

- **Updated options:**
  - [ ] (a) DOE Ref templates only, now. 90.1 items get leave or keep rows with the
    reason "awaiting PNNL prototype source".
  - [ ] (b) Also apply the structural fixes (holiday rule, Janitor tags, rule
    boundaries) to 90.1 now, but no value changes.
  - [ ] (c) Pin the PNNL 90.1 prototype models from energycodes.gov (a download for your
    approval) and run the same reconciliation for the 90.1 templates as a follow-on.
    Meanwhile, (a).
- **Recommendation:** (c). It gives your lean towards (b) a source-backed basis, and it
  catches value errors like the Produce load, which (b) cannot. If you would rather not
  add a source, take (b) for the structural fixes only.
- **Your choice / notes:** Did you mean the https://www.energycodes.gov/prototype-building-models prototype building models? They should be fully included (commercial, residential, manufactured housing; things to include: construction, program (some programs in prototype buildings have a constant schedule. that should not be included as correct ref, try to use existing sources for these schedules. power den kind of values should be consistent)). You have the permission to download. But differentiate reference buildings from prototype buildings.

### Q2. Which DOE value applies (clarification only)

- **Original question:** (a) the matching vintage (post-1980 for 1980-2004, pre-1980 for
  pre-1980), or (b) any vintage?
- **Original recommendation:** (a). I added "climate does not matter, since operating
  schedules are the same in every climate file".
- **Your feedback:** "ok but what does 'b any vintage' mean here? it does not mention
  climate - why do you reason 'climate' here?"
- **Clarification:**
  - (b) meant treating the three DOE vintages as interchangeable, for example always
    reading the new 2004 file.
  - The climate remark answered a different point: which of the 16 climate files to
    read. It did not belong under this question, and the wording was confusing.
  - The new evidence makes the vintage matter. Lighting, the infiltration rate (3.75×
    lower in new 2004), envelope and HVAC differ by vintage. So (b) would bring code-era
    lighting and infiltration into existing-stock templates.
- **Updated options:**
  - [ ] (a) Matching vintage. Climate: any file, since operating schedules are
    identical; Chicago 5A is used for comparison.
  - [ ] (b) Any vintage.
- **Recommendation:** (a). You said "ok", so I am treating this as decided unless you mark
  otherwise.
- **Your choice / notes:** ok to a

### Q3b. openstudio-standards schedule edits (A3): which is newer?

- **Original question:** for documented upstream recalibrations such as warehouse
  Saturday occupancy, (a) replace with the DOE value or (b) keep the recalibration?
- **Original recommendation:** (a) replace.
- **Your feedback:** you chose (a) in Q3, but in A3 you asked "which one is newer? if
  openstudio standards is newer, maybe no need to replace the newer with the older (i
  meant the last edit time, not the vintage)".
- **New evidence:** I traced each differing row through openstudio-standards' full git
  history (2015–2026, 114 versions of the schedules file, plus the space-type files) and
  compared every version with the DOE file
  over the full year. The DOE v1.4 files date from 2012-11-13. The rows fall into two
  groups:
  1. **Different since the row first appeared upstream, never edited in substance since**
     (only formatting changes). openstudio-standards did not exist before 2015, so these
     are newer in timestamp only. The difference was there from the first import, with no
     recorded rationale. Most rows are like this:
     - school setpoints and occupancy periods (2015-10-27)
     - hospital and outpatient setpoints, upstream "NO_OPTIMUM" rows that differ on
       Saturdays (2015-10-27)
     - warehouse cooling setpoint (2016-02-17)
     - outpatient and school hot-water schedules (2015–2016)
     - Medium Office lighting assignment (2015-10-27)
  2. **Equal to DOE (apart from holidays), then deliberately edited later:**
     - Warehouse occupancy and lighting, on **2024-06-07**: "remove comstock ashrae
       schedules", which merged ComStock's calibrated schedules into the shared file. The
       occupancy row notes "Day Types changed … based on EULP calibration"; the lighting
       row has no note.
     - Supermarket occupancy and lighting, on **2025-06-10**: "Update Lighting, Occupancy,
       and Equipment Schedules for 90.1 Models". The rows are shared by name with the DOE
       Ref templates, so the DOE Ref supermarket changed as a side effect. Their notes
       still say "From DOE Reference Buildings".
- **Updated options:**
  - [ ] (a) Replace both groups with the DOE value.
  - [ ] (b) Group 1: replace. Group 2: keep the newer upstream value, and record the DOE
    value as an alternate value.
  - [ ] (c) Group 1: replace. Group 2, warehouse (a documented ComStock calibration): keep,
    with the DOE value as an alternate. Group 2, supermarket (an edit aimed at 90.1 that
    leaked into DOE Ref): replace with DOE in the DOE Ref templates, and keep it in 90.1.
- **Recommendation:** (c). It follows your "newer wins" idea where the newer edit was
  deliberate and documented, and it does not let an edit aimed at other templates
  override the DOE Ref source.
- **Your choice / notes:** ok to (c)

### Q5b. Load values (A5): which is newer?

- **Original item:** A5, replace the load values that differ from DOE.
- **Original recommendation:** replace.
- **Your feedback:** "which one is newer (last edited)?? reason".
- **New evidence** (same trace, on the space-type rows):

| Value | Atlas (openstudio-standards) | DOE | Upstream history |
| --- | --- | --- | --- |
| Supermarket Produce plug | 0.05 W/ft² | 0.5 W/ft² (5.38 W/m²) | 0.05 since the row first appeared (2017-05/09), every template |
| Supermarket Sales plug | 1.02 W/ft² | 0.5 W/ft² | since the row first appeared |
| Supermarket Sales lighting, pre-1980 | 5.04 W/ft² | 2.78 W/ft² (same as post-1980) | since 2017-09-27 |
| Large Hotel cafe lighting, 1980-2004 | 1.46 W/ft² | 2.56 W/ft² (pre-1980 row also 2.56) | since 2015-10-27 |
| Hospital nurse-station occupancy | 7.14 per 1,000 ft² | 70 m²/person (≈1.33) | since 2015-10-27 |
| Hospital ICU patient-room plug, 1980-2004 | 2.69 W/ft² | 3.0 W/ft² | was 3.0; changed 2016-06-03 |
| Hospital lobby lighting | 1.03 W/ft² | 1.46 W/ft² | was 1.46 (1980-2004) and 1.49 (pre-1980); changed 2016-06-03 |

- **About the 2016-06-03 change:** it is a bulk regeneration of the JSON from the
  upstream spreadsheet. Its message is "Added efficiency lookups for heat pumps", so it
  says nothing about these values. The same commit nulled the ER triage load. The
  pre-1980 ICU row kept 3.0, which equals DOE. That pattern suggests a spreadsheet error
  rather than a deliberate recalibration.
- **Conclusion:** none of these upstream values is a documented, deliberate newer edit.
  They are either transcription differences from the first import or an unexplained bulk
  regeneration.
- **Updated options:**
  - [ ] (a) Replace all with the DOE value.
  - [ ] (b) Replace the first-import differences; keep the 2016 values with DOE as an
    alternate.
  - [ ] (c) Keep all, with DOE as alternate values.
- **Recommendation:** (a). This is consistent with the rule in Q3b: keep the upstream
  value only when it is newer *and* documented.
- **Your choice / notes:** ok to your recommendation

### Q8. Infiltration (decided; recorded for confirmation of the shape)

- **Decision:** (c), a second, selectable method. Your note: "both methods should be
  shipped side by side within the same artefact".
- **New evidence:**
  - Method, coefficients (1, 0, 0, 0), schedules and the zones that carry infiltration
    are the same in all three DOE vintages. Only the rate changes: 0.000302 m³/s·m² in
    new 2004 vs 0.001133 in post-1980 and pre-1980.
  - **Methods by type:** Flow/ExteriorArea (offices, retail, restaurants, supermarket,
    warehouse, small hotel) or Flow/ExteriorWallArea (hospital, large hotel, schools,
    outpatient).
  - **Air changes per hour** for attics (1.0), small-office core (0.36), secondary-school
    gym (0.14), outpatient stairs and elevators (1.0), and retail front entry (1.0).
  - **Schedules:** quarter-on or half-on while the HVAC runs, otherwise always on.
  - **Zones without infiltration:** basements, office cores, and some hospital and
    outpatient zones.
- **Proposed shape** (inside the existing construction package):
  `infiltration: {default_method: "nist_natural_ach", methods: {nist_natural_ach: {…},
  doe_design_flow: {zone_rules: [...], excluded_zones: …}}}`.
  - Each method cites its own schedule, and the DOE schedules ship in the folder's
    `schedules.json`.
  - BEMGen computes exterior wall and roof areas and volumes from its own geometry.
- **Your choice / notes:**
  - [x] shape accepted  [ ] change: accepted with 1 comment: should infiltration ach not be in construction? or is such construction referencing the schedule

### Q12. A new-2004 template

- **Original question:** (a) add a `doe-ref-new-2004` template from these files, or (b)
  not add it?
- **Original recommendation:** (a), as a separate later release.
- **Your feedback:** "why? is there anywhere this is mentioned in comstock? what is the
  current new 2004 version? doe should come from one of the 2004 versions we have now
  no? why? list the current 2004 new variants (per standard?) - i am leaning towards not
  add a new version and only add when absolutely necessary an 'alternate value' if doe
  differ from comstock very much and both are backed by reasoning. discuss."
- **New evidence:**
  - **ComStock's templates** (the pinned `options_lookup.tsv`): DOE Ref Pre-1980, DOE Ref
    1980-2004, then ComStock 90.1-2004, 2007, 2010, 2013, 2016 and 2019. So ComStock
    models 2004-era buildings as "ComStock 90.1-2004".
  - **Current 2004 variants:**
    - openstudio-standards template `90.1-2004`, the PNNL prototype lineage that
      ComStock 90.1-2004 builds on
    - ComStock 90.1-2004
    - DOE Reference new 2004, these files
  - **The atlas has none of them.** Its templates are DOE Ref Pre-1980, DOE Ref
    1980-2004, and 90.1-2007, 2013 and 2019. So there is no current 2004 template to
    attach an alternate value to.
  - **How DOE new 2004 relates to them:** it equals the DOE Ref common loads (occupancy,
    plug, gas, schedules) plus 90.1-2004 lighting (it matches openstudio-standards 2004
    and 2007 lighting in 349 of 397 zones). The openstudio-standards 90.1-2004 template
    instead has recalibrated plug, occupancy and gas loads.
  - **Why I first recommended (a):** to have a reference matching the files exactly. That
    is not needed, because geometry, schedules and non-lighting loads are already covered
    by the post-1980 and pre-1980 reconciliation.
- **Updated options:**
  - [ ] (a) Add a `doe-ref-new-2004` template.
  - [ ] (b) Do not add it. Keep the new 2004 files as pinned evidence only (geometry,
    skylights, cross-checks).
  - [ ] (c) Do not add it now. If a 90.1-2004 template is ever added (from
    openstudio-standards, aligned with ComStock 90.1-2004), use the new 2004 files as its
    cross-check, with alternate values only where they differ substantially and both are
    backed.
- **Recommendation:** (c). It matches your lean (no new version, alternates only when
  necessary) and keeps the files useful.
- **Your choice / notes:** ok to your recommendation

### Q15. Large Office basement

- **Original question:** (a) add a program for each zone with distinct values, or (b)
  keep whole-building programs, recorded with a reason?
- **Original recommendation:** (a), only where values truly differ (Large Office
  basement, Supermarket Sales split).
- **Your feedback:** "construction info should have basement related qualities. what do
  you need that is not able to be supported by this design? discuss. do you mean doe
  differs from comstock basement spec?"
- **New evidence:**
  - **Large Office basement.**
    - The construction side is already covered: the basement envelope (foundation walls,
      ground floor) is in the construction package, and the DOE basement has no
      infiltration.
    - The only difference is a program value: occupancy is 37.16 m²/person (0.0269
      person/m²) in all three DOE vintages, while the whole-building office program used
      for the basement has 0.0538.
    - Lighting, plug, gas and thermostat schedules equal the other floors.
    - So "DOE differs from the ComStock basement spec" is right, but only for occupancy.
  - **Hospital and Large Hotel basements** already have their own Basement programs, and
    they match DOE in the DOE Ref templates.
  - **Supermarket Sales** is no longer a Q15 case. Its differences are load values
    (plug, pre-1980 lighting) and moved to Q5b; the rest is only area weighting.
- **Updated options:**
  - [ ] (a) Add a Large Office basement program: the whole-building office program with
    DOE occupancy (0.0269 person/m²), as Hospital and Large Hotel already have.
  - [ ] (b) Keep the whole-building program for the basement, with a keep row
    (reason: one program per building type).
  - [ ] (c) Keep one program, and record the basement occupancy as an alternate value
    for zones below grade.
- **Recommendation:** (a). BEMGen assigns programs per zone, so a basement program is the
  simplest way to reproduce DOE, and it follows the existing Hospital and Large Hotel
  pattern.
- **Your choice / notes:** this is sensible - but what about other basement programs? or is this the only basement program ever in the entire repo.

### Q16 (new). Fenestration defaults in constructions (C10)

- **Your direction:** default WWR in constructions, with façade and roof (skylight)
  separate.
- **Current state:** construction packages keep WWR operands only as selection evidence.
  The contract (`construction-json-v1-contract.md:92`) says "not an invented consumer
  WWR".
- **DOE values:**
  - Identical in all three vintages, except skylights, which only new 2004 schools have
    (skylight-to-roof ratio 0.0019 primary, 0.0112 secondary). The DOE Ref templates
    therefore have no skylights.
  - Façade WWR varies by orientation. For example:
    - retail, strip mall and supermarket glaze only the south façade (0.25–0.36)
    - restaurants have none on the north
    - the hospital ranges from 0.12 to 0.26
  - Offices: 0.33 counting plenum walls vs 0.48 counting conditioned walls only.
- **Decision 1, which wall area WWR is relative to:**
  - [ ] (a) Gross exterior wall, including plenum walls, as DOE reports it.
  - [ ] (b) Conditioned-zone walls only.
  - [ ] (c) Ship both.
  - Recommendation: (a), labelled with its basis. It is DOE's own definition, and BEMGen
    can convert it if it does not model plenums.
- **Decision 2, resolution:**
  - [ ] (a) Per orientation (N, E, S, W) plus the total.
  - [ ] (b) Total only.
  - Recommendation: (a). The orientation split is large for retail and restaurants.
- **Decision 3, source for the 90.1 templates:**
  - [ ] (a) Compute from the pinned openstudio-standards geometry files that the atlas
    already uses.
  - [ ] (b) Leave the 90.1 templates without defaults until the PNNL models are pinned
    (Q1).
  - Recommendation: (a). The files are already pinned, and they are the 90.1 templates'
    own geometry source.
- **Your choice / notes:** ok to separate nesw directional wwr based on the model geometry. We need to thus include wwr for 4 directions and wwr for skylight. I believe area should be relative to that zone (program or merged program/zone) geometry, on average. you may open a new question if my recommendation does not fully answer your question and you need extra info

### Q17 (new). Confirm the A11 follow-ups

These follow the rules you already set (DOE authority; absence in a complete DOE model
counts as a source-backed zero). They are listed for confirmation because they are new.

- **A12, heat-fraction differences:**
  - [x] replace  [ ] keep
  - Recommendation: replace (quick-service restaurant dining lights, supermarket
    bakery and deli gas, small-hotel laundry plug).
- **B8, internal-mass coverage:**
  - [x] fill 2.0 m²/m²  [ ] leave
  - Recommendation: fill (warehouse bulk storage, retail front entry, 17 small-hotel
    zones).
- **C13, lights replaceable fraction:**
  - [x] omit  [ ] ads
  - Recommendation: omit (reason: daylighting only; none in DOE Ref).
- **Hospital Office1 multiplier:** 5 in the openstudio-standards geometry vs 4 in DOE.
  It skews that zone's area-based loads and mass.
  - [x] use DOE (4)  [ ] keep (5)
  - Recommendation: use DOE, recorded against geometry evidence for BEMGen (#13).
- **Your choice / notes:**

## 6b. Round 3: open and new questions

### Prototype download (for Q1-A to Q1-D)

The PNNL/DOE prototype models are downloaded from
https://www.energycodes.gov/prototype-building-models into a separate root,
`D:\Prototype Building Models\`, so they stay apart from `D:\Reference Building Models\`.

- **Size:** 163 archives, 4.57 GB. Every archive was size-checked against the server and
  hashed. The records are in `SOURCES-prototypes.json` and `SHA256SUMS-prototypes.txt`;
  the archives themselves are not kept there.
- **Contents:**

| Family | Folder | Contents |
| --- | --- | --- |
| Commercial, ASHRAE 90.1 | `commercial-ashrae901/` | 16 types × 7 versions (2004, 2007, 2010, 2013, 2016, 2019, 2022) × 19 climates; 4,256 IDFs with `.htm` results and a scorecard `.xlsx` per type |
| Commercial, IECC | `commercial-iecc/` | 16 types × 6 versions (2006, 2009, 2012, 2015, 2018, 2021) × 19 climates; 3,648 IDFs |
| Residential | `residential/` | 11,840 IDFs: single-family (6,080) and multifamily (5,760) × 19 climates × 4 heating types (electric resistance, gas furnace, heat pump, oil furnace) × 4 foundations (crawlspace, heated basement, unheated basement, slab) × IECC 2006–2024 |
| Manufactured housing | `manufactured-housing/` | 1,216 IDFs: HUD code, plus the Final Rule tier 1 and tier 2, × 19 cities × 4 heating types |

- **The 16 commercial types:** the same as the DOE reference set, except that
  Supermarket is absent and High-rise Apartment is present.
- **Not downloaded:**
  - Per-version commercial zips: the bundles contain them byte for byte (checked on
    Small Office 2019).
  - Appendix G baseline/proposed models.
  - Stand-alone weather files.
- **Downloaded but redundant:** two "all types" bundles (`ASHRAE901_all`, `IECC_all`) and
  one weather bundle came in too. They duplicate other content, and I can delete them if
  you want.
- **Disk use:** extracted, the files take about 77 GB (commercial 90.1 28 GB, IECC 24 GB,
  residential 25 GB, manufactured 0.4 GB). Drive D: still has about 1.5 TB free.
  - [ ] delete the redundant bundles  [ ] keep them
- **Not yet done:** none of this has been compared with the atlas yet.

### Q1-A. Scope and phasing of the prototype reconciliation

- **Original question:** should the DOE files' authority reach the 90.1 templates?
- **Original recommendation:** (c), pin the PNNL prototypes and reconcile the 90.1
  templates as a follow-on.
- **Your feedback:** "They should be fully included (commercial, residential,
  manufactured housing; things to include: construction, program (…)). You have the
  permission to download. But differentiate reference buildings from prototype
  buildings."
- **What the atlas covers today:**
  - Commercial: 90.1-2007, 2013 and 2019 only. It has no 90.1-2004, 2010, 2016 or 2022,
    and no IECC templates.
  - Residential: ResStock, whose storage is deferred.
  - Manufactured housing: nothing.
- **What is unclear:** whether "fully included" means new atlas templates for every
  prototype version and family. That would be about 30 commercial templates plus the
  residential and manufactured sets. Or does it mean the prototypes are fully pinned and
  reconciled where the atlas already has a matching template? Your Q12 answer (no new
  version unless necessary) points to the second reading.
- **Updated options:**
  - [ ] (a) Phase 1: reconcile the three existing 90.1 templates against their prototypes
    (construction and program). Pin everything else as evidence, with no new templates.
  - [ ] (b) Phase 1 as in (a). Phase 2: add atlas templates for the other 90.1 versions
    and IECC. Phase 3: residential and manufactured housing, as part of the residential
    storage work (which ADR 0036 deferred).
  - [ ] (c) Add templates for every prototype version and family now.
- **Recommendation:** (b). It honours "fully included" in a deliverable order: each
  phase is its own release, and phase 1 reuses the DOE reconciliation machinery
  directly.
- **Your choice / notes:**

### Q1-B. Constant schedules in the prototypes

- **Your rule:** "some programs in prototype buildings have a constant schedule. that
  should not be included as correct ref, try to use existing sources for these
  schedules."
- **What still needs defining:**
  - **"Constant":** I propose a schedule with a single value all year, or one that only
    switches between 0 and 1 for design days, where the atlas's schedule for the same
    space and load varies by hour. I have not yet counted how many prototype loads are
    like this; that count comes in phase 1.
  - **"Existing sources":** which one?
- **Updated options for the source of such a schedule:**
  - [ ] (a) Keep the atlas's current schedule, from openstudio-standards, and record the
    prototype's constant schedule as not taken (reason: a simplification in the
    prototype).
  - [ ] (b) Use the DOE reference schedule for the same space and load, where one
    exists; otherwise (a).
  - [ ] (c) Leave it as a gap and decide case by case.
- **Recommendation:** (a). It is the template's own source family. DOE reference
  schedules belong to the existing-stock templates, and borrowing them would mix
  families.
- **Your choice / notes:**

### Q1-C. Power densities: prototype vs atlas

- **Your rule:** "power den kind of values should be consistent".
- **Proposal:** treat the prototype as the authority for the matching 90.1 template, the
  same way the DOE files are the authority for the DOE Ref templates. That means:
  - replace where they differ;
  - keep an upstream value only when its edit is newer than the prototype release *and*
    documented (the Q3b rule), with the prototype value as an alternate.
- **Updated options:**
  - [ ] (a) Prototype is the authority, with the Q3b rule for newer documented edits.
  - [ ] (b) Keep openstudio-standards, and record prototype values as alternates.
- **Recommendation:** (a). It keeps one rule for both source families.
- **Your choice / notes:**

### Q1-D. Keeping reference and prototype buildings apart

- **Proposal:**
  - Two source families with their own pins: "DOE Commercial Reference Buildings
    (v1.4_7.2)" and "DOE/PNNL Prototype Building Models (energycodes.gov)".
  - Two local roots (done).
  - Two registers: `data/reconciliation/doe-reference-v1.json` and
    `data/reconciliation/pnnl-prototype-v1.json`.
  - Two generated site pages.
  - Each atlas value cites exactly one family as its source, and the other family can
    appear only as evidence or an alternate.
- [ ] accepted  [ ] change:
- **Your choice / notes:**

### Q8-A. Infiltration: does the construction reference a schedule?

- **Your comment:** "should infiltration ach not be in construction? or is such
  construction referencing the schedule".
- **Answer:**
  - Yes, both infiltration methods stay in the construction package.
  - Today the package references no schedule: the NIST ACH applies as a constant, which
    the evidence notes as "schedule=1".
  - The DOE method needs a schedule (quarter-on or half-on while the HVAC runs), so the
    construction package would reference one for the first time.
- **Updated options:**
  - [ ] (a) The construction package references the schedule by ID in the same folder's
    `schedules.json`. ADR 0036 puts `constructions/` and `schedules.json` side by side
    in each building-type folder, so nothing is duplicated.
  - [ ] (b) Embed the schedule inside the construction package, so it is self-contained.
- **Recommendation:** (a). The schedules file is already the shared store for the folder,
  and the consumer exports can inline it, as they do for programs.
- **Your choice / notes:**

### Q15-A. Other basement programs

- **Your feedback:** "this is sensible - but what about other basement programs? or is
  this the only basement program ever in the entire repo."
- **Inventory:**
  - **Hospital and Large Hotel:** a `Basement` program in all five atlas templates.
  - **Large Office:**
    - openstudio-standards has a "WholeBuilding - Lg Office-basement" space type in
      90.1-2004 to 2019. It has the same occupancy as the office (5 per 1,000 ft²) but
      lower plug load (0.45 W/ft², always on).
    - The atlas already ships it for 90.1-2013 and 2019.
    - In 90.1-2007, the shared geometry file tags the basement as the whole-building
      office.
    - The DOE Ref templates have no Large Office basement program. That is the one DOE
      adds (occupancy 0.0269 person/m², everything else as the office).
  - **Large Office Detailed, Tall and Super Tall buildings:** their basement spaces use
    ordinary space types (corridor, mechanical, storage, office…), so they need no
    basement program.
  - **Residential:** basements are foundation types (construction), not programs.
- **Updated options:**
  - [ ] (a) Add the Large Office basement program to the two DOE Ref templates now.
    Settle 90.1-2007 (the tag and its values) in the prototype reconciliation (Q1-A
    phase 1).
  - [ ] (b) Also re-tag the 90.1-2007 basement now, using the 2013/2019 basement space
    type.
- **Recommendation:** (a). The 90.1-2007 Large Office prototype will show which values
  are right, so the tag is better fixed with evidence.
- **Your choice / notes:**

### Q16-A. Directional WWR per program: semantics and storage

- **Your direction:** N/E/S/W WWR plus a skylight ratio, relative to the program's (or
  merged program/zone's) own geometry, averaged by area.
- **New evidence:** I computed this for every DOE Ref program (post-1980 geometry, zones
  grouped by their space-type mapping). Two things show up:
  1. **Directional values depend on where a program sits in the as-built plan.** For
     example:
     - small-hotel guest rooms: N 0.149, S 0.158, W 0 (end wall), with no east wall;
     - retail entry: south only (0.32);
     - outpatient lobby: west only (0.44).
     Many program/direction pairs have no exterior wall at all. Once BEMGen rotates or
     rearranges a plan, those directions no longer apply.
  2. **Mixed zones exist:** the supermarket Sales zone spans 9 space types.
- **Decision 1, semantics:**
  - [ ] (a) Per program, per direction, as computed. A direction with no wall is null; a
    wall with no window is 0.
  - [ ] (b) Per program, one value over all directions, with the directional split kept
    only at building level.
  - [ ] (c) Both: per program per direction (exact for the as-built plan), plus per
    program over all directions (for rearranged plans).
  - Recommendation: (c).
- **Decision 2, where it lives:**
  - [ ] (a) In the construction package, keyed by program ID, next to the window
    constructions. This follows your C10 direction.
  - [ ] (b) In each program file.
  - Recommendation: (a). It keeps fenestration with the envelope, and programs stay
    geometry-free.
- **Decision 3, mixed zones:**
  - [ ] (a) Split windows and walls by the area share of each space type.
  - [ ] (b) Record the mixed zone as its own entry.
  - Recommendation: (a).
- **Your choice / notes:**

## 6c. Round 4: open questions

### New evidence: PNNL 90.1 prototypes vs the atlas

These compare the Denver files (there is no Chicago file in the prototype set) with the
atlas release on `main`. All 112 files are EnergyPlus 22.1, released 2023-10.

- **Same family, different values.** Zone names and space types line up. The atlas
  equals openstudio-standards in every zone where both have a value, so every difference
  below is between openstudio-standards and PNNL.

| Load | Zones matching, 2007 | 2013 | 2019 |
| --- | --- | --- | --- |
| Occupancy | 66% | 67% | 67% |
| Lighting | 61% | 51% | 44% |
| Plug | 99% | 100% | 100% |
| Gas | 100% | 100% | 100% |

- **Lighting:** PNNL sets its own per-zone densities. The prototype-to-atlas ratio ranges
  from 0.41 to 3.95. For example:
  - Large Office 2019: 6.60 vs 6.89 W/m²
  - Hospital ICU patient room 2013: 12.38 vs 6.67 W/m²
  - apartments: 10.01 vs 14.42 W/m²
- **Occupancy:** the prototypes give support spaces (corridors, stairs, storage,
  mechanical rooms) 0.016–0.054 person/m² where the atlas has 0. The strip mall is
  0.1615 vs 0.0861 person/m².
- **Plug:** matches once elevators, exhaust fans and reach-in refrigerators are left out.
  The 2007 Large Office basement is an assignment difference; the 2013/2019 basement
  program already matches.
- **DOE reference new 2004 vs PNNL 90.1-2004:** occupancy matches in only 36% of zones,
  lighting in 63%, plug in 67% and gas in 98%. PNNL 2004 aligns with openstudio-standards
  90.1-2004, not with the DOE files.
- **Constant schedules:** none are missing, but many are constant all year:
  - 280 of 3,143 People objects, 259 of 3,535 Lights and 376 of 3,178 electric equipment
    objects, with no gas equipment
  - 1,480 of 3,346 heating and 2,046 of 3,269 cooling thermostat schedules
  - examples are listed under Q1-B'.

### Q1-B'. Constant schedules in the prototypes

- **Original question:** what is the source for a prototype load whose schedule is
  constant?
- **Original recommendation:** (a), keep the atlas schedule from openstudio-standards.
- **Your feedback:** "if you do not see missing or constant (all same value) schedule in
  prototype buildings then ok no need to worry".
- **New evidence:** none are missing, but there are many constant ones. They fall into
  three groups:
  1. **Constant because the space runs 24/7 or by design.** These look like correct
     references:
     - hospital setpoints 21/24 °C in every zone
     - data-center 18/27 °C
     - reach-in refrigerators and freezers always on
     - the Large Office basement plug load always on
     - warehouse bulk storage heated only, at 10 °C
     - semi-heated small-hotel spaces at 7.2 °C
     - apartment and guest-room setpoints
     - offices with no cooling setback through 2010 (data centers only from 2013)
  2. **Constant zero ("always off") that cancels a non-zero density.**
     - People and plug loads in 39 small-hotel support zones
     - People in one large-hotel zone
     - lights in 14 vacant small-hotel guest rooms
     - The effective load is zero.
  3. **A constant fraction instead of a profile.** Corridor, stair and restroom lighting
     held at 0.25–1.0 in the hotels and apartments. This looks like a code lighting-control
     assumption (for example, corridors partly dimmed), not real operation.
- **Updated options:**
  - [ ] (a) Accept group 1 as correct. Treat group 2 as a source-backed absence (zero
    load). For group 3, keep the atlas's existing varying schedule and record the
    prototype's constant fraction as not taken (reason: control simplification).
  - [ ] (b) Accept all three groups as they are in the prototype.
  - [ ] (c) Replace every constant with an existing varying schedule wherever the atlas
    has one.
- **Recommendation:** (a). Group 1 is physically constant. Group 2 is how the prototype
  says "nobody here". Group 3 is the one case where your concern applies.
- **Your choice / notes:**

### Q1-C'. Prototype vs atlas inconsistencies in the 90.1 templates

- **Original question:** is the prototype the authority for the 90.1 templates' power
  densities?
- **Original recommendation:** (a), yes, with the Q3b rule for newer documented edits.
- **Your feedback:** "discuss inconsistencies; regardless, reference building (existing
  not up to code) pow den need not to be replaced unless explicitly wrong and should".
- **The inconsistencies:** almost all are lighting densities and support-space occupancy
  (see the new evidence above).
- **Dating them (the Q3b rule):** this needs the openstudio-standards git history of the
  90.1 space-type rows, which the trace tool from Q3b can do in phase 1.
  - The prototypes date from 2023-10.
  - The pinned openstudio-standards commit is newer, but individual rows may be older
    than the prototypes or newer.
- **Updated options:**
  - [ ] (a) The prototype is the authority for the 90.1 templates. Replace, except where
    the openstudio-standards row is newer than 2023-10 *and* the change is documented;
    in that case keep it, with the prototype value as an alternate.
  - [ ] (b) Keep openstudio-standards for code templates, recording prototype values as
    alternates.
  - [ ] (c) Replace only lighting, which is code-defined, and keep occupancy, which is
    not set by the code.
- **Recommendation:** (a). The prototypes are what the code templates are meant to
  represent. Under the Q3b rule nothing deliberate and newer is lost. The dating runs in
  phase 1 before anything is applied.
- **Your choice / notes:**

### Q1-D'. Why keep reference and prototype buildings apart?

- **Your question:** "why keep apart? they are different variants like the code we have
  already. i assume the code we have from doe or ref or comstock for new buildings should
  be the same as protypte buildings or no?"
- **Answer:** you are right that they are variants, and the atlas templates already map
  onto them one to one:
  - DOE Ref Pre-1980 and 1980-2004 come from the DOE reference buildings.
  - 90.1-2007, 2013 and 2019 come from the PNNL prototypes, through openstudio-standards.
- **They are not the same values, though**, so it matters which file backs which
  template:
  - The atlas code templates differ from the prototypes mainly in lighting (44–61% of
    zones match).
  - The DOE reference new 2004 differs from the PNNL 2004 prototype (occupancy matches
    in only 36% of zones).
  - So "new buildings" exist in three versions: DOE reference new 2004, the PNNL
    prototypes, and openstudio-standards (which follows PNNL closely, plus later ComStock
    edits).
- **So "apart" only needs to mean provenance:** every value says which source family
  backs it, and each family reconciles only its own templates. Separate folders, registers
  and pages are not needed.
- **Updated options:**
  - [ ] (a) One register and one site page, with a `source_family` field on every row
    (`doe-reference` or `pnnl-prototype`). The local folders stay separate because they
    are already downloaded that way.
  - [ ] (b) Two registers and two pages, as proposed in round 3.
- **Recommendation:** (a). It is simpler and still traceable.
- **Your choice / notes:**

### Q5c. DOE Ref power densities under the "explicitly wrong" rule

- **The original decision (Q5b):** (a), replace every DOE Ref load value that differs
  from DOE.
- **Your new rule:** existing-building power densities are not replaced unless they are
  explicitly wrong.
- **Proposed test for "explicitly wrong":**
  - a unit or decimal slip (a factor of 10 or more)
  - a value missing where the source has one
  - a value contradicted by the same upstream source's sibling rows with no rationale
- **Each item under that test:**

| Item | Atlas | DOE | Explicitly wrong? | Proposed |
| --- | --- | --- | --- | --- |
| Supermarket Produce plug | 0.05 W/ft² | 0.5 W/ft² | yes: factor 10, in every template | replace |
| Supermarket Sales plug | 1.02 W/ft² | 0.5 W/ft² | no: plausible, since the row's first appearance | keep, DOE as alternate |
| Supermarket Sales lighting, pre-1980 | 5.04 W/ft² | 2.78 W/ft² | no: plausible for older stock | keep, DOE as alternate |
| Large Hotel cafe lighting, 1980-2004 | 1.46 W/ft² | 2.56 W/ft² | not by the test, though the pre-1980 row has 2.56 | keep, DOE as alternate |
| Hospital nurse-station occupancy | 7.14 per 1,000 ft² | ≈1.33 | not power; see below | keep |
| Hospital ICU patient-room plug, 1980-2004 | 2.69 W/ft² | 3.0 W/ft² | no: 10% apart, changed in the 2016 regeneration | keep, DOE as alternate |
| Hospital lobby lighting | 1.03 W/ft² | 1.46 W/ft² | no | keep, DOE as alternate |
| Hospital ER triage plug | null | 29.05 W/m² | missing (already a B5 fill) | fill (already decided) |

- **Decision 1, does the rule cover occupancy density too?**
  - [ ] (a) Yes, all densities (people, lighting, plug, gas).
  - [ ] (b) Only power densities (lighting, plug, gas); occupancy follows the Q5b replace
    rule.
  - Recommendation: (a). The same reasoning (existing stock varies) applies.
- **Decision 2, record DOE as an alternate on each "keep"?**
  - [ ] (a) Yes, on every keep.
  - [ ] (b) Only where the two differ by more than 50%.
  - Recommendation: (b). It follows your "alternates only when necessary" lean.
- **Decision 3, the cafe case** (the pre-1980 sibling row agrees with DOE):
  - [ ] (a) Treat as explicitly wrong and replace.
  - [ ] (b) Keep.
  - Recommendation: (b). A lower post-1980 lighting density is plausible.
- **Your choice / notes:**

### Q16-B. WWR in the program definition: the follow-ups

- **Decided:** per program, five directions (N, E, S, W, roof), plus 15 whole-building
  values: 5 directions × (conditioned, unconditioned, all zone surfaces), each
  area-weighted.
- **Computed for all 15 DOE Ref types** (post-1980 geometry, zone multipliers included).
  Two examples:
  - Medium Office, conditioned: N/E/S/W 0.477, roof none. Unconditioned (plenums): walls
    0, roof 0. All: 0.33.
  - Large Hotel, conditioned: N 0.26, E 0.245, S 0.367, W 0.245, roof 0.
  - A direction with no wall is null; a wall with no window is 0.
  - Full results: `wwr_15_post1980.json` in the session scratchpad.
- **Decision 1, where the 15 whole-building values go**, since a program is per space
  type:
  - [ ] (a) On the building type's whole-building ("general") program, which the atlas
    already has.
  - [ ] (b) On a building-level record in the suite folder.
  - Recommendation: (a). It keeps WWR in program definitions, as you decided.
- **Decision 2, skylights that vary by climate.**
  - Some prototypes change skylight-to-roof ratio by climate: Stand-alone Retail 2019
    has 0.0104 in 15 climates and 0.0029 in 4; Warehouse 2019 has 0.0149 and 0.0032.
  - Programs are climate-free, and the DOE Ref templates have no skylights, so this only
    affects the 90.1 templates.
  - [ ] (a) Store the roof value per climate group inside the program, as the one
    exception.
  - [ ] (b) Store the value of the majority climate group and record the others as
    alternates.
  - [ ] (c) Leave roof values that vary by climate to the construction package's climate
    contexts.
  - Recommendation: (c). Programs stay climate-free, and the variation is a code envelope
    requirement.
- **Decision 3, mixed zones** (carried over from Q16-A; the supermarket Sales zone spans 9
  space types):
  - [ ] (a) Split windows and walls by area share.
  - [ ] (b) Record the mixed zone as its own entry.
  - Recommendation: (a).
- **Your choice / notes:**

### Plan for adding everything (Q1-A)

Each phase is its own release, and each reuses the register, the comparison scripts and
the generated page.

1. **DOE reference** (the current plan): reconcile the DOE Ref templates and record the
   new-2004 files as evidence.
2. **PNNL commercial, existing templates:** reconcile 90.1-2007, 2013 and 2019 against
   their prototypes (Q1-B', Q1-C').
3. **PNNL commercial, new 90.1 templates:** add 90.1-2004, 2010, 2016 and 2022, built from
   the prototypes plus openstudio-standards rows. The DOE new-2004 files cross-check
   90.1-2004 (Q12 c).
4. **PNNL commercial, IECC:** add IECC 2006–2021 templates. These are new atlas families,
   with their own selection rules.
5. **Residential prototypes:** single-family and multifamily, by heating type and
   foundation, IECC 2006–2024. This goes with the residential storage work ADR 0036
   deferred, and needs mapping against the ResStock configurations.
6. **Manufactured housing:** HUD code and the Final Rule tiers. This is new to the atlas.

Phases 3–6 add templates. Each needs its own ADR for selection, climate coverage (the
prototypes have 19 cities) and naming.
- **Your notes:**

## 8. Bucket list

### Complete the program catalogue for the construction-only building types

From the atlas storage-restructure work. `main` is at `0ec58c0` (PR #15 merged). This
item is kept in this doc for now and is not filed as a GitHub issue.

**Where the atlas is now**
- **Release candidate:** `data/atlas-releases/v1.0.0`, commercial only, laid out per ADR
  0036.
  - One file per program and per construction set under
    `commercial/<template>/<building-type>/`.
  - Folder tables: schedules, systems, components, services, water.
  - Per-template libraries and an evidence tree.
  - `python -m scripts.atlas_release --verify` checks it; `--check` rebuilds it byte for
    byte (pinned Windows / CPython 3.14.7 in CI).
- **Consumer exports:** `python -m scripts.atlas_exports`. Program JSON 5.0.0 comes in
  versions `source` and `filled` (water heating folded in). Constructions export as
  detailed 4.0.0 and unified 3.0.0. `docs/consumer-contracts-release-1.0.0.md` lists the
  changes.
- **Writers:** `scripts/atlas_programs.py`, `atlas_constructions.py`, `atlas_systems.py`
  and `atlas_release.py`. They read the frozen definition release
  `data/definition-releases/v0.1.1`.

**The gap:** 51 template × building-type folders have construction sets but no programs.
- **In each 90.1 template (2007, 2013, 2019), 13 types:** college, courthouse, laboratory,
  large/small data-centre high/low ITE (4), large/medium/small office *detailed*, office
  (generic), tall building, super tall building.
- **In each DOE Ref template (1980–2004, Pre-1980), 6 types:** college, courthouse,
  large/medium/small office *detailed*, office.

**Why the gap exists:**
- Programs follow ADR 0002's selection: 17 types from the DOE Reference and PNNL prototype
  suites, 83 folders in all.
- Construction sets follow the wider openstudio-standards construction catalogue.
- The pinned 90.1 space-type tables do include space types for these:

| Building type | Space types |
| --- | --- |
| College | 15 |
| Courthouse | 22 |
| Laboratory | 4 |
| Each data-centre variant | 1 |
| Generic Office | 52–53 |

- The Detailed-office, Tall and Super Tall types reuse office space types. The DOE Ref
  space-type tables have not been checked.

**What "complete" means**
1. **Record the scope extension** as an ADR amending ADR 0002: which types, which
   templates.
2. **Recover source programs** for each new type × template from the pinned
   openstudio-standards source, following the existing conventions:
   - SI values, explicit nulls, evidence for every value;
   - resolutions only where evidence supports them;
   - no invented values.
3. **Build department and general mixes** from represented source floor areas of the
   prototype geometry (where the reference-model geometry work comes in). Follow
   `docs/reviews/program-aggregation-matrix.md`:
   - each mix comes from one template and family;
   - renormalize when a member is missing;
   - basement and attic are excluded from every mix;
   - no fabricated members.
4. **Map types without their own space types** (Detailed offices, Tall, Super Tall,
   generic Office) to office space types explicitly; do not copy or invent records.
5. **Add HVAC systems, services and water records** where the source supports them.
6. **Deliver through the ADR 0036 release:**
   - a new definition input and the writers extended to read it;
   - a delta release `v1.1.0` (manifest naming `base_release` 1.0.0 and that manifest's
     SHA-256), or a regenerated full release;
   - tests in the style of `tests/test_atlas_*.py`;
   - exports through `scripts/atlas_exports.py`.

**Constraints learned so far**
- **Never reuse a program across 90.1 editions.** Across the 158 programs present in all
  three editions:
  - lighting power density differs in 150 (2019 is a median 0.65× of 2007);
  - lighting schedules differ in 55;
  - equipment schedules differ in 66;
  - cooling setpoints differ in 48;
  - occupancy, hot water and gas are nearly identical.
- **Readable IDs** hash their content, and some records cite each other: programs and
  services, components and their systems, sets that cite other sets. Each of these hashes
  the other side's ID as a placeholder. Reuse the helpers in `scripts/atlas_format.py`.
- **Residential (ResStock)** storage stays deferred.
- **Required CI checks:** `build`, `research / atlas (ubuntu-latest, 3.11)` and
  `research / atlas (windows-latest, 3.14)`. Any change to a pinned input means
  regenerating the release manifest.
- Follow `AGENTS.md`: a short-lived branch and a PR to `main`.

**Done looks like**
- Every one of the 51 folders has programs, or a recorded reason why it can't.
- The release verifies and rebuilds.
- `tests/test_atlas_*.py` pass.
- Exports validate against `program-json-v5`.

**Related:** the geometry work in this plan supplies the represented floor areas for
step 3; also #13 and #16.

## 9. Work stages

The ETAs are rough agent working time; review waits and CI runs come on top. Each stage
starts with a fresh ETA and ends with a short progress note.

**Stop rule:** if the same kind of failure recurs after about three attempts (for
example memory limits, a parser or a CI job), I stop and report with evidence instead of
trying further fixes.

**Gates:** a stage marked **gate** ends with a report to you. The next stage starts only
after your answer.

### Release v1.1.0: DOE reference reconciliation

**S0. Set up** (0.5 h)
- Create the branch `codex/doe-reference-reconciliation` from `main`.
- Commit this plan doc.
- Done when: the branch is pushed only when you approve it, with the plan in
  `docs/superpowers/plans/`.

**S1. Pin the sources** (2–3 h)
- **Lock entries** in `sources/lock.json` for the 48 DOE v1.4 per-building zips and the
  163 prototype archives: URL, size, SHA-256 and Last-Modified.
  - For DOE, add an Internet Archive fallback URL.
  - The three recycled prototype bundles are recorded as excluded.
- **A locked-fetch script** with hash checking. It is opt-in, so CI never downloads
  4.6 GB.
- **Inventory updates:**
  - Update `sources/inventory.json` and `docs/source_inventory.md`, replacing the stale
    "HTTP 404" notes.
  - Licence: US government work, public domain under energy.gov policy, attribution
    requested.
- Done when: `--check` verifies every pinned hash against the local copies.

**S2. Tooling** (3–4 h)
- **`scripts/idf_reader.py`** handles the EnergyPlus 5.0, 7.2 and 22.1 field layouts,
  including the Space Name field and the missing shading-control field.
- **Into `scripts/`, as tested modules:** the full-year schedule evaluator (holidays,
  design days, the atlas rule semantics), the zone-load and geometry comparators, and
  the openstudio-standards history trace.
- **Tests** run on small fixtures cut from the pinned files.
- Done when: the scripts reproduce this plan's counts, for example 74 identical and 59
  holiday-only.

**S3. The 90.1-vs-prototype equivalence proof** (6–10 h, **gate**)
- **Checked:**
  - geometry: zones, areas, heights, footprint, windows, skylights
  - constructions: layers, U-value and SHGC per surface type and climate
  - infiltration
  - internal mass
  - WWR
- **Coverage:** 90.1-2007, 2013 and 2019 × 16 types, apartments included. The prototypes'
  19 cities are mapped onto the atlas climate contexts.
- **Tolerance:** about 1%.
- **Outcome:**
  - Where it holds, the 90.1 templates are declared backed by both sources, and no
    templates are added.
  - Real differences come to you for discussion.
  - Load and schedule differences are recorded as evidence only.

**S4. ADR 0037 and contract changes** (2–3 h, **gate**)
- **ADR 0037 records the rules:**
  - authority per source family
  - the "newer and documented" rule
  - the "explicitly wrong" rule for existing-building densities
  - alternate values
  - the register
  - the outcome of the equivalence proof
- **It amends** ADR 0018 (hot-water zone gains) and ADR 0020 (a second infiltration
  method).
- **Contract additions, as minor versions:**
  - a holiday calendar and DST metadata
  - per-zone WWR in programs and the 15 whole-building WWR values in constructions
  - both infiltration methods, with schedule references
  - hot-water gain fractions and zone attachment
  - humidity setpoints
  - building services and refrigeration
  - an `alternate` field

**S5. The register** (4–6 h, **gate** only for unclassified rows)
- Generate candidate rows from the comparisons: schedules, loads, heat fractions,
  internal mass, infiltration, hot water, WWR and basements.
- Apply the decided rules and the reason table.
- Rows that no rule covers come to you as a short list.
- Done when: no row is undecided, and every keep, leave or omit has a reason.

**S6. Apply to the release** (8–12 h)
- **A new definition input** in the existing style. The writers are extended:
  - **Schedules:** holidays, the school fixes, the Q3b edits.
  - **Programs:**
    - the fills: hot water, additional lighting, plenum equipment, small-hotel mixes,
      ER triage
    - the heat fractions
    - the Large Office basement program
    - the A4 re-tags (library, computer room, janitor)
    - humidity setpoints and per-zone WWR
  - **Constructions:** the second infiltration method, the internal-mass fill and the
    building WWR.
  - **Services:** elevators, exhaust fans, exterior lights and refrigeration.
  - **Water:** zone attachment and gain fractions.
  - **Metadata:** the holiday calendar and DST.
- **Delta release v1.1.0**, whose manifest names `base_release` 1.0.0 with its SHA-256.
- Done when: `atlas_release --verify` and `--check` pass, and the `tests/test_atlas_*`
  tests and the new answer-key tests pass, with the DOE files at ADR 0035 tolerance.

**S7. Exports, site page, documentation** (4–6 h)
- **Contract versions:** Program JSON 5.1.0, constructions 4.1.0 (detailed) and 3.1.0
  (unified), with their schemas.
- **The site page** is generated from the register, at
  `website/content/guides/doe-reference-reconciliation.md`, and added to the nav.
- **Documentation:** the release notes and the consumer-contract change list.
- Done when: the exports validate and the site builds.

**S8. Pull request** (1–2 h, plus CI)
- A PR to `main`, with the three required checks green and review conversations resolved.
- Opened only with your go-ahead.

**S9. BEMGen handoff** (2 h)
- A handoff note covering:
  - the holiday calendar
  - building services and refrigeration
  - hot-water draws with zone gains
  - the DOE infiltration method
  - per-zone and building WWR
  - the basement program
- It is aligned with the geometry session's gap note (zone multipliers, the D-097 change,
  and the room-level office plans).

**Subtotal for v1.1.0:** about 33–48 h of agent time, over several sessions.

### Release v1.2.0: construction-only programs (section 8)

**S10. The program catalogue for the 51 construction-only folders** (2–3 days)
- An ADR amending ADR 0002.
- Source programs recovered from openstudio-standards, including the room-level
  Detailed office types (the geometry session found that every room type is defined for
  both DOE Ref vintages).
- Department and general mixes from the represented prototype floor areas.
- Explicit mappings for Tall, Super Tall and the generic Office type.
- Systems, services and water records.
- Delta release v1.2.0.

### Later releases: new families

**Family structure (round 9 decision: IECC is a completely different family from
ASHRAE).** The source-family names below are proposals; the ADR in each stage fixes them.

| Family | Source | Templates | Relation to other families |
| --- | --- | --- | --- |
| `existing_stock_benchmark` (current) | DOE reference buildings, through openstudio-standards | DOE Ref Pre-1980, 1980-2004 | none |
| `code_prototype_rules` (current, ASHRAE 90.1) | openstudio-standards, backed by the PNNL ASHRAE 90.1 prototypes if S3 proves equivalence | 90.1-2007, 2013, 2019 | none |
| `iecc_commercial_prototype` (new) | PNNL IECC commercial prototypes | IECC 2006, 2009, 2012, 2015, 2018, 2021 | none: no pairing with 90.1 editions, no shared records |
| `iecc_residential_prototype` (new) | PNNL IECC residential prototypes | IECC 2006–2024 | none |
| `manufactured_housing_prototype` (new) | DOE/PNNL manufactured-housing prototypes | HUD code, Final Rule tier 1, tier 2 | none |

- **No mixing:** a program, construction or mix never combines records from two families
  (as ADR 0012 already requires within the current families).
- **Geometry is BEMGen's concern, not the atlas's** (round 10). The atlas carries no plan
  geometry; it carries only the per-zone and building WWR records decided in Q16.

**S11. IECC commercial family** (2–4 days, **gate** after the first type)
- **An ADR for the new family:** its name, its templates (six IECC years), climate
  coverage (the prototypes' 19 cities mapped onto atlas climate contexts) and its
  selection rules.
  - It states that IECC is independent of the ASHRAE 90.1 family. The comparison in this
    section showed different envelope, glazing, lighting, HVAC, infiltration and, for some
    types, WWR.
- **Extraction** straight from the IECC prototype IDFs into the existing program,
  construction and schedule schema, with the IDF as the primary source: 6 years × 16
  types.
  - It uses the S2 IDF reader.
  - It covers the same level of definition as the current templates: programs, mixes,
    constructions, infiltration, internal mass, WWR, services and water.
- **Storage:** new template folders under `commercial/`, for example
  `commercial/iecc-2015/<building-type>/`, in the ADR 0036 layout.
- **Answer key:** the IECC prototypes themselves, at ADR 0035 tolerance.
- **Release:** a minor delta release of its own, after v1.2.0.

**S12. Residential prototypes** (2–3 days, **gate**)
- Single-family and multifamily × foundation × heating, as the new family
  `iecc_residential_prototype`, keyed by IECC year (S-Q1 decided: no pairing).
- Prerequisite: a residential storage layout under ADR 0036, which deferred it. That
  storage decision also covers the ResStock records.

**S13. Manufactured housing** (1–2 days)
- HUD code and the Final Rule tiers, as the new family `manufactured_housing_prototype`
  under `residential/`.
- The existing-building gap is documented. ResStock's three manufactured homes are the
  only existing-stock coverage.

### Open question for these stages

**S-Q1. How residential and manufactured prototypes align to the 90.1 years**
- The residential prototypes are coded to IECC 2006–2024, and manufactured housing to
  HUD and the Final Rule tiers; neither is coded to 90.1.
- DOE's commercial equivalence pairs IECC 2009 with 90.1-2007, IECC 2015 with 90.1-2013,
  and IECC 2021 with 90.1-2019. That pairing is for commercial buildings; the residential
  chapters are separate code text.
- **Options:**
  - [ ] (a) Extract only the IECC years paired with 2007, 2013 and 2019 (2009, 2015,
    2021), labelled with that pairing.
  - [ ] (b) Extract all IECC years (2006–2024), each with an alignment field naming its
    paired 90.1 year where one exists.
  - [ ] (c) Use the IECC years as their own templates, with no alignment.
- **Manufactured housing** has no year pairing. Its three code levels (HUD, Final Rule
  tier 1, tier 2) become its templates in every option.
- **Recommendation:** (b). Nothing is lost, and the 2007, 2013 and 2019 alignment you
  asked for is explicit.
- **Your choice / notes:**
- **Decided (round 8, in chat):** no pairing. IECC is a different standard, so the
  residential prototypes get their own family name, keyed by IECC year. Manufactured
  housing keeps its own three code levels. This replaces the O2 wording "aligned to the
  90.1 family" for residential.

### Finding: paired IECC and 90.1 commercial prototypes are not the same (for S11)

I compared IECC 2009 with 90.1-2007, IECC 2015 with 90.1-2013 and IECC 2021 with 90.1-2019:
all 16 types, Denver files, object by object, with a closer look at four types.

- **Geometry:** building surfaces are identical in every pair.
- **WWR:**
  - The same in the 2009/2007 pairs.
  - In the 2015/2013 and 2021/2019 pairs, IECC shrinks the windows of some types: medium
    office 0.30 vs 0.33, primary school 0.30 vs 0.35. Warehouse and small hotel are
    unchanged.
- **Envelope:** it differs in every pair.
  - Wall, roof and door insulation R-values differ. For example, the semi-heated roof
    insulation is R 3.47 vs 1.28 m²K/W in the 2009/2007 pair.
  - Glazing differs: medium-office window U is 2.17 vs 2.38 W/m²K in the 2015/2013 pair.
  - Skylight glazing differs too.
- **Lighting:** IECC is lower in most pairs. For example, the medium-office mean LPD is
  9.06 vs 10.20 W/m² in 2015/2013, and the small hotel is 5.33 vs 8.45.
- **Also different:** HVAC and controls objects in every pair (energy-management programs
  exist only in 90.1-2019), and infiltration objects in the 2021/2019 pairs.

**Conclusion:** IECC commercial differs from its paired 90.1 edition in what matters
(construction and fenestration), so S11 stays as a separate family. There is no shortcut
through the 90.1 templates.

### S-Q2. (Withdrawn, round 10: the geometry rule behind it belongs to BEMGen, not the atlas. The atlas adds no data-centre program to the DOE Ref templates; any mapping is BEMGen's.)

- **From the geometry session:** one geometry serves every vintage and edition, so the
  Large Office keeps its data-centre zone as drawn.
- **The problem:**
  - The DOE reference Large Office has no data centre; that floor area is part of its
    basement and core zones.
  - The atlas DOE Ref templates have no data-centre program.
- **Options:**
  - [ ] (a) Give the zone the program DOE gives that floor area: the Large Office basement
    program in the basement, the office program in the core.
  - [ ] (b) Use the 90.1 data-centre program. This mixes source families, which ADR 0012
    forbids.
  - [ ] (c) Leave it without a program for the DOE Ref vintages, and record why.
- **Recommendation:** (a). It reproduces the DOE loads on that floor area, and stays in one
  family.
- **Your choice / notes:**

## 10. Execution plan: all stages, workloads, deliverables (round 10)

The work runs autonomously under the rules in 10.2. Workloads are rough agent working
time, excluding CI and your reviews.

### 10.1 Stages

| Stage | Workload | Deliverables | Done when |
| --- | --- | --- | --- |
| **S0** Set up | 0.5 h | Branch `codex/doe-reference-reconciliation` from `main`, with this plan committed | The branch exists and the commit passes the staged-diff and secrets checks |
| **S1** Pin sources | 2–3 h | `sources/lock.json` entries for the 48 DOE and 163 prototype archives (the 3 recycled ones marked excluded); `scripts/fetch_reference_models.py` (opt-in locked fetch with hash check); updated `sources/inventory.json` and `docs/source_inventory.md` (the 404 notes replaced, licence notes added) | `--check` verifies every pinned hash, and CI downloads nothing |
| **S2** Tooling | 3–4 h | `scripts/idf_reader.py` (EnergyPlus 5.0, 7.2 and 22.1 layouts); the full-year schedule comparator, zone-load and geometry/construction comparators, and the openstudio-standards history trace as tested modules; fixture-based tests | The scripts reproduce this plan's counts |
| **S3** Equivalence proof, 90.1 vs PNNL prototypes | 6–10 h | `docs/reviews/prototype-equivalence-90-1.md` plus a JSON result: geometry, constructions (layers, U, SHGC), infiltration, internal mass and WWR for 3 editions × 16 types, about 1% tolerance | Every aspect is either equal or listed as a real difference |
| **S4** Policy and contracts | 2–3 h | ADR 0037 (rules, families, register, proof outcome; amends ADR 0018 and 0020); contract drafts for Program JSON 5.1.0 and constructions 4.1.0 / 3.1.0 | The ADR is accepted under this plan's decisions |
| **S5** Register | 4–6 h | `data/reconciliation/doe-reference-v1.json`, the reason table, the generator script and tests | No row is undecided, and every keep, leave or omit has a reason |
| **S6** Apply, release v1.1.0 | 8–12 h | A new definition input; writer changes (schedules, programs, constructions, services, water, metadata, as in section 9); the `data/atlas-releases/v1.1.0` delta; answer-key tests | `atlas_release --verify` and `--check` pass, and all tests pass |
| **S7** Exports, site, docs | 4–6 h | Program JSON 5.1.0 and construction 4.1.0 / 3.1.0 exports and schemas; the generated site page; release notes; the consumer-contract change list | Exports validate and the site builds |
| **S8** PR for v1.1.0 | 1–2 h plus CI | A PR to `main` with the three required checks green | You merge it |
| **S9** BEMGen handoff | 2 h | A handoff note: holiday calendar, building services and refrigeration, hot-water gains, the DOE infiltration method, WWR records, the basement program | The note is committed and sent to BEMGen |
| **S10** Construction-only programs, release v1.2.0 | 2–3 days | An ADR amending ADR 0002; programs, mixes, systems, services and water for the 51 folders; the v1.2.0 delta; tests; a PR | Section 8's "done" list |
| **S11** IECC commercial family, release v1.3.0 | 2–4 days | ADR for `iecc_commercial_prototype`; IDF-based extraction; `commercial/iecc-<year>/` folders for 6 years × 16 types; answer-key tests; a PR | Release verifies, and values equal the IECC prototypes at tolerance |
| **S12** IECC residential family | 2–3 days, plus the residential storage layout (a prerequisite) | ADR for the residential layout under ADR 0036; ADR for `iecc_residential_prototype`; extraction; release; a PR | As S11 |
| **S13** Manufactured housing family | 1–2 days | ADR for `manufactured_housing_prototype` (HUD, Final Rule tiers 1 and 2), with the existing-stock gap documented; extraction; release; a PR | As S11 |

**Totals:** about 33–48 h of agent time for v1.1.0 (S0–S9), then about 9–15 days for
S10–S13.

### 10.2 How the autonomous run works

- **Decisions:** follow the rules recorded in this doc. Each decision lands in the
  register or an ADR, with its reason.
- **Commits:**
  - Commit freely on the branch, in small reversible units.
  - Use Conventional Commits.
  - Check the staged diff and run the secrets audit before every commit.
  - Follow AGENTS.md for the automated identity and the `Agent-Model` trailer.
- **Progress:** an ETA at the start of each stage, and a short progress note when it ends.
- **Stop and ask only when:**
  - S3 finds a real geometry or construction difference between the prototypes and the
    90.1 templates;
  - a register row matches no recorded rule;
  - a licensing, public-feasibility or architecture ambiguity comes up (AGENTS.md);
  - a change would rewrite released data instead of adding a delta;
  - the same kind of failure recurs after about three attempts (the stop rule);
  - pushing, a PR or a merge needs the permission set below.
- **Push, PR and merge** (to be confirmed):
  - Push the branch and open one PR per release.
  - Never merge: you merge after review.
  - Never bypass branch protection.

## 7. General notes

Notes:
