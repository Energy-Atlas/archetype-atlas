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
