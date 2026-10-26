# Plan: residential storage, IECC residential and manufactured housing (S12, S13)

Written 2026-10-26. These stages continue the stage table of
`2026-10-24-doe-reference-reconciliation.md` (section 10). ADR 0038 decides the
residential storage. ADR 0040 decides the IECC commercial family, built in parallel
as S11.

## 1. Parallel work

| Agent | Stages | Branch | Release |
| --- | --- | --- | --- |
| 1 | S11, IECC commercial (ADR 0040) | `codex/iecc-commercial` | 1.3.0 |
| 2 | S12a, S12 and S13 below | `codex/residential-families` | 1.4.0 |

**Release base.** Both branches start from `codex/construction-only-programs` (release
1.2.0, PR #18). A reader resolves one base only, so every minor release is a delta on
1.0.0 that holds all earlier changes. A release is cumulative in the order the PRs
merge.
- The branch that merges second merges `main` and adds the other's overlay to its
  release entry in `scripts/atlas_minor_release.py`.
- It then rebuilds its delta.

**Shared files.** Each agent adds its own entries and resolves conflicts at merge:
- `scripts/atlas_minor_release.py` (`RELEASES`), `scripts/atlas_exports.py`
  (release names, contract minors) and `schemas/`;
- `.github/workflows/validate.yml`, `CHANGELOG.md`, `mkdocs.yml` and
  `scripts/active_site.py` (site guides).

Neither agent changes the other's family code.

**Rules for both agents.**
- Pinned writers and frozen releases stay untouched; overlays reach the writers
  through their loaders.
- Offline extraction goes into committed definition inputs, each file under 25 MB.
- Answer-key tests compare a pinned sample with the source files at the ADR 0035
  tolerance.
- Run the full suite and the release `--check` before each PR. Each release gets
  one PR, and the user merges.

## 2. Sources (pinned in `sources/reference-models-lock.json`, extracted locally)

**IECC residential** (`residential/`, EnergyPlus 23.1). `resstd_AllCodes` holds every
model; the per-climate folders are subsets of it.
- **4,144 models:** single-family (SF) and multifamily (MF) × 19 climate codes ×
  4 heating systems × 4 foundations × 7 editions.
  - **Climate codes:** 1AWH, 1AWHT, 1AWHTS, 2AWH, 2B, 3A, 3AWH, 3B, 3C, 4A to 4C, 5A
    to 5C, 6A, 6B, 7 and 8.
  - **Heating systems:** electric resistance, gas furnace, heat pump, oil furnace.
  - **Foundations:** crawlspace, heated basement, slab, unheated basement.
  - **Editions:** IECC 2006, 2009, 2012, 2015, 2018, 2021 and 2024.
- **SF:** one living zone, a garage and an attic, plus an unconditioned living zone
  in the 1AWHTS variant.
- **MF:** one building with 18 living units (3 floors × front and back rows ×
  3 units) and a breezeway.
- **Schedules:** `Schedule:Compact` and `Schedule:Year`, with no `Schedule:File`.

**Manufactured housing** (`manufactured-housing/`, EnergyPlus 8.0).
- **Types:** single-section (SS) and multi-section (MS) homes.
- **Locations:** 19, one per climate zone except 3A, which has five (Atlanta,
  Birmingham, Charleston, Jackson, Memphis).
- **Standards:** the HUD Code baseline, and the DOE 2022 Final Rule, tier 1 for SS
  and tier 2 for MS.
- **Heating:** the same 4 systems.
- **Zones:** a living zone, an attic and a crawlspace.

## 3. Stages

### S12a. Residential storage (ADR 0038), with the ResStock fixture migrated

1. **Residential writer** for `residential/<family>/<building-type>/`, following
   ADR 0038:
   - one file per dwelling;
   - climate, vintage and size bin as record fields and in the readable ID;
   - per-dwelling annual schedule files under `schedules/`, plus the folder
     ruleset table;
   - one construction set per dwelling with a single context;
   - no systems.

   It reuses `scripts.atlas_format` (canonical JSON, readable IDs). The commercial
   writers are not changed.
2. **ResStock migration:** the 41 SDR fixture dwellings, with their annual
   schedules, constructions, fillings and evidence, from the frozen definition and
   resolution releases into `residential/resstock-sdr/`.
3. **Exports:** Program JSON gains the `dwelling_unit` basis as an additive minor,
   plus a residential export path in `scripts.atlas_exports`.
4. **Tests:**
   - every migrated value equals its frozen source;
   - files stay under 25 MB;
   - IDs reproduce.

**Done when:** release 1.4.0 holds the residential tree, the release reproduces byte
for byte, and the exports validate. **Estimate:** 2 days.

### S12. IECC residential family (ADR 0041)

1. **ADR 0041** for family `iecc_residential_prototype`. Its scope follows the
   decisions in section 4.
2. **Extraction:** offline, from `resstd_AllCodes`, into
   `data/program-inputs/iecc-residential-<edition>.json`:
   - **Programs:** one per edition, type and unit position.
   - **Loads:** occupancy, lighting, plug and appliance loads, hot water with its
     zone, and internal gains, all on a per-dwelling basis.
   - **Schedules:** converted and checked over the full year. The schedule converter
     gains `Schedule:Year`, `Schedule:Week` and `Schedule:Day`.
   - **Thermostat setpoints:** included.
   - **Infiltration:** the source ELA or ACH method.
   - **Window ratios:** program level.
   - **Construction sets:** one per edition and type, with contexts by climate code
     and foundation (19 × 4 = 76).
3. **Release 1.4.0:** `residential/iecc-<year>/single-family/` and `multifamily/`,
   7 editions × 2 types.
4. **Answer-key tests:** loads, schedules and U-factors against a pinned sample of
   IDFs.

**Estimate:** 2–3 days.

### S13. Manufactured housing family (ADR 0042)

1. **ADR 0042** for family `manufactured_housing_prototype`.
   - **Templates:** `hud-code` and `doe-final-rule`, with the tier as a record field.
   - **Types:** single-section and multi-section.
   - **Gap:** there is no existing-building category, which is documented (user
     decision).
2. **Extraction:** as in S12, into `data/program-inputs/manufactured-housing.json`.
   - The idf reader's EnergyPlus 8.0 field layout is checked against the 7.2 and
     23.1 layouts.
   - Construction contexts are keyed by climate zone. The five 3A cities become
     sub-contexts (`3-a.atlanta`, …).
3. **Release:** 1.4.0, together with S12 if both are ready, otherwise 1.5.0.

**Estimate:** 1–2 days.

## 4. Decisions (for approval before agent 2 starts)

| ID | Decision | Recommendation |
| --- | --- | --- |
| R1 | Branching and release order | As section 1. Each branch builds its own release, and the second to merge folds in the first. |
| R2 | Migrate the 41 ResStock dwellings in S12a | Yes. ADR 0038 needs a working residential tree before the IECC and MH families. |
| R3 | IECC residential multifamily representation | One dwelling program per unit position, but only where loads differ between positions. Building context (18 units, 3 floors, breezeway) as record fields. Otherwise one program for the identical units. |
| R4 | Variant axes | Climate code and foundation become construction contexts. Heating systems are not stored (ADR 0038 section 7). If a load differs by heating system, which S12 checks, that load gets a program variant. |
| R5 | The 1A sub-codes (WH, WHT, WHTS) | Keep them as distinct contexts named after the source codes. Their meaning (moisture regime or tropical variants) goes in the ADR once decoded from the PNNL documentation in the archive. |
| R6 | Manufactured-housing templates | `hud-code` (baseline) and `doe-final-rule` (2022, tiers 1 and 2 by section), with the 3A cities as sub-contexts. |
| R7 | Out of scope | Systems for all residential families, and the unified construction representation (as ADR 0040). |
| R8 | Editions | All 7 IECC residential editions, including IECC 2024, which the residential set has but the commercial set does not. |

R1 to R8 were approved as recommended (user, 2026-10-26).

## 5. Clarified decisions (user, 2026-10-26)

The two agents work without supervision. These answers settle the ambiguities found
by probing the source files; follow them before falling back on G1.

### General (both agents)

- **G1. Undecided questions.**
  - An agent may decide when it has reasoned confidence, and need not take the most
    conservative option. Every such decision goes in the "Agent decisions" section
    of its family's ADR (decision, alternatives, reason, evidence), and the PR
    repeats the list.
  - Stop only for:
    - a licensing question;
    - a change that would rewrite released data;
    - the same kind of failure three times.
- **G2. Push and PR.**
  - Each agent pushes its own branch and opens one PR per release; it never merges.
  - When the other branch reaches `main`, merge `main` in and fold the other
    release into the cumulative delta.
- **G3. Docs per family.** An ADR, release notes, a docs-site guide in the nav
  (staged by `scripts/active_site.py` as well), and a CHANGELOG entry.
- **G4. Answer-key samples.**
  - Commercial: every type and edition in Buffalo (5A), Miami (1A) and
    Fairbanks (8).
  - Residential: every edition in 4A and 1AWH.
  - Manufactured housing: every location under the HUD Code.
- **G5. Progress.** A short note at the end of each stage.
- **G6. Time box.** If S13 is not done when S12 is, release 1.4.0 ships without it
  and S13 becomes 1.5.0.

### S11, IECC commercial

- **C1. Zone to space type.**
  - IECC zones get their space type from a single lookup table, built from the
    openstudio-standards geometry of all three 90.1 templates (2007, 2013, 2019).
  - Names are normalized: lower case, spaces as underscores.
  - The table is checked so that a zone name never maps to two space types. No
    values come from the 90.1 geometry, only the tags.
- **C2. Unmatched zones.** An agent may map them by reasoned guess. Each guess goes
  in a committed alias table with its reason, under G1.
- **C3. Type names.** Rename PNNL type names to the atlas vocabulary (OfficeMedium
  becomes MediumOffice, and so on), keeping PNNL's name as a field.
- **C4. Daylighting controls.** Evidence only.
- **C5. PNNL scorecards.** Evidence only.
- **C6. Climate-dependent values.** Where a load differs by climate (rare),
  `value` keeps the value for most zones and an additive `value_by_climate`
  (`{"0B": 6.59, …}`) gives the exceptions. This is Program JSON 5.2.0, an
  additive minor.

### S12a, residential storage

- **S1. The ResStock dwellings.** Their fillings move unchanged.
  - New research-assumption fillings, for example from IECC knowledge, are allowed
    only where the source is null. They never overwrite a source value.
  - Each cites its source file and reason and is listed in the ADR.
- **S2. Dwelling identity.** IDs come from the source building ID plus climate,
  vintage and size bin. Folders are the ResStock building types.
- **S3. Older releases.**
  - They are not maintained: no new versions, no edits. They remain frozen,
    verify-only inputs, because the `--check` rebuilds of releases 1.0.0 to 1.4.0
    and the ResStock migration read them.
  - They can be archived at a future 2.0.0 full snapshot.

### S12, IECC residential

- **R1. Program variants.** One program per edition, type and appliance fuel. Gas
  homes have a gas range, gas dryer and other gas appliances; electric-resistance,
  heat-pump and oil homes have electric ones. A separate basement entry is used only
  with the heated-basement foundation, which adds basement lighting and a larger
  adjustment load.
- **R2. The IECC adjustment load.** `IECC_Adj` is its own load quantity, labelled as
  a reference-design adjustment.
- **R3. Auxiliary zones.** Garage, attic, crawlspace and breezeway loads stay inside
  the dwelling program, tagged with their host zone.
- **R4. Multifamily.** The 18 units have identical loads, so there is one per-unit
  program. The building context (18 units, 3 floors, front and back rows,
  breezeway) goes in record fields.
- **R5. The 1AWHTS unconditioned living zone.** It has walls but no floor or
  ceiling. Its absolute loads (lighting about 169 W, `Addl_IECC_Adj` 253 W) become
  building-level services attached to the dwelling and instantiated once. The
  tropical-zone reading (WH warm-humid, T tropical, S semi-conditioned) is
  confirmed from the PNNL documentation, or recorded as an agent decision.
- **R6. Infiltration.** The source method per dwelling, as it is.

### S13, manufactured housing

- **M1. Source folders.** Read only the HUD and FinalRule folders. CompleteSet
  duplicates them; check by checksum.
- **M2. Programs.** Loads are identical across heating systems and code variants,
  so there is one program per section type (single, multi). Envelope and the
  standard vary by construction context and template.
- **M3. The 3A cities.** Five sub-contexts of 3A (`3-a.atlanta`, …).

### Probe findings for the agents

- **Zone name normalization.** IECC commercial zone names match the 90.1 geometry
  after normalization. Outpatient, Warehouse and High-rise Apartment match only
  after it.
- **1AWHTS floor area.** The unconditioned zone has no floor, so a per-floor-area
  computation divides by zero; guard for it.
- **Schedule converter.** The residential and manufactured-housing models use
  `Schedule:Year`/`Week`/`Day`, which `scripts/idf_schedules.py` must learn to read
  and to check over the full year.
- **EnergyPlus 8.0.** Manufactured-housing models are EnergyPlus 8.0. Confirm the
  idf reader's field layout for that version.
