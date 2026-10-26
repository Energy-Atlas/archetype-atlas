# ADR 0037: Reconcile the DOE Ref templates with the DOE reference building files

Status: accepted (2026-10-25, user decisions recorded in the
[reconciliation plan](../superpowers/plans/2026-10-24-doe-reference-reconciliation.md),
rounds 1 to 11). Amends ADR 0018 (water-use zone gains) and ADR 0020 (a second
infiltration method). Applies to release v1.1.0, a delta on v1.0.0 under ADR 0036.

## Context

The atlas DOE Ref templates (Pre-1980, 1980-2004) are read from openstudio-standards,
which reimplemented the DOE commercial reference buildings. The DOE files themselves
are now pinned: 48 v1.4_7.2 building ZIPs (`sources/reference-models-lock.json`).
- **Schedules.** Compared over a full year with holidays and design days, 74 of 204
  schedule references are identical and 57–59 differ only on holidays. About 22
  differ because openstudio-standards edited or converted the row, and about 11–13
  because it assigns a different schedule. 23–26 are outside program scope.
- **Loads.** 94–100% of 397 zones match per load.
- **Vintages.** Geometry, schedules and non-lighting loads are the same in all three
  DOE vintages.
- **Upstream history.** Most differences date from openstudio-standards' first import
  (2015–2017) with no recorded reason. Two groups of rows were edited deliberately later:
  warehouse occupancy and lighting (2024, a ComStock calibration) and supermarket
  occupancy and lighting (2025, an edit aimed at the 90.1 models).

The PNNL prototype models are pinned in the same lock. Their comparison with the 90.1
templates ([review](../reviews/prototype-equivalence-90-1.md)) found real construction
differences (walls, doors, some glazing). That is recorded here as evidence only; the
construction authority for the 90.1 templates is decided separately.

## Decision

### 1. Source families and authority

- **Families.**
  - `existing_stock_benchmark`: DOE reference buildings.
  - `code_prototype_rules`: ASHRAE 90.1 through openstudio-standards.
  - Later families, each separate with no pairing: `iecc_commercial_prototype`,
    `iecc_residential_prototype`, `manufactured_housing_prototype`.
  - A record never mixes families.
- **For the DOE Ref templates, the DOE files of the matching vintage are the authority
  for schedules and internal-load semantics:** post-1980 for 1980-2004, pre-1980 for
  Pre-1980. Climate does not matter, since operating schedules are the same in all 16
  climate files; the Chicago file is used.
- **Exceptions to that authority:**
  - **Newer and documented.** An openstudio-standards value is kept, with the DOE value
    as an alternate, only if its row was edited after the DOE v1.4 release (2012-11-13)
    *and* the edit is documented. At this pin that is the 2024 warehouse occupancy and
    lighting calibration. The 2025 supermarket edit targeted the 90.1 models, so the DOE
    Ref templates take the DOE value and the 90.1 templates keep theirs.
  - **Existing-building densities.** Occupancy, lighting, plug and gas densities are
    replaced only when the atlas value is explicitly wrong: a unit or decimal slip
    (10× or more), a missing value where DOE has one, or a contradiction with the same
    source's sibling rows with no rationale. Otherwise the atlas value is kept, and the
    DOE value is added as an alternate where the two differ by more than 50%.
  - **Rounding.** Differences within 1%, from the IDFs printing SI values to 2–4
    significant figures, keep the atlas value.
- **Absence in a complete DOE model is a source-backed zero** for the DOE Ref templates:
  plenum equipment, additional lighting where the base already equals the DOE total, and
  hot water in zones without a draw.

### 2. The register

Every comparison item has one row in `data/reconciliation/doe-reference-v1.json`.
- **What a row holds:**
  - its source family, category (inconsistency, gap or missing component) and class
  - template, building type, target and field
  - the current atlas value with its location
  - the DOE value with file SHA-256, object and line
  - the upstream row's last semantic edit
  - the decision (replace, keep, fill, leave, add or omit), a reason ID where the
    decision needs one, and any alternate
- **Who reads it:** the register is atlas-internal. The release writer applies its
  decisions, tests check it, and a site page is generated from it. Consumers see only
  the resulting values, their evidence and any alternates.

### 3. What changes in the DOE Ref templates (release v1.1.0)

- **Schedules.**
  - Holidays follow the DOE rule: the Sunday profile or a constant.
  - The openstudio-standards conversion errors are corrected: school weekend setpoints
    and the 1 September overlap.
  - Edited rows take the DOE profile, except under the newer-and-documented rule.
  - Assignments follow the DOE zone schedules, including Medium Office lighting and the
    school cafeteria, kitchen and office schedules.
  - Design days follow DOE.
  - Schedule times inside an hour stay hourly means.
- **Programs.**
  - **Fills:** hot-water schedules from the DOE zone draws (zero where a DOE zone has
    none); additional lighting and plenum equipment as zero where the DOE model is
    complete; small-hotel mix setpoints and activity from the matching zones; ER triage
    plug load 29.05 W/m² (the v1.3 scorecard's 21.53 W/m² becomes evidence).
  - **Heat fractions** take the DOE values where they differ.
  - **Re-tagging:** the outpatient storage and utility rooms and the primary-school
    library and computer room are re-tagged as DOE has them.
  - **Basement programs:** every building type with a basement has a Basement program.
    Large Office gains one: the office program with DOE's basement occupancy,
    0.0269 person/m².
  - **Humidity setpoints** become program controls for the hospital and outpatient.
  - **Per-zone WWR** is added: directions N, E, S and W plus roof (skylight), relative to
    the program's own zone surfaces and averaged by area. A direction with no wall is
    null, and a wall with no window is 0.
- **Constructions.**
  - **The 15 whole-building WWR values:** the five directions over conditioned,
    unconditioned and all zone surfaces. A whole-building program's per-zone WWR equals
    them by definition, and a test checks that.
  - **The DOE infiltration method** as a second method beside the fixed natural ACH, in
    the same package. It is design flow per exterior area or per exterior wall area,
    with air changes per hour for attics and entries, and it references its schedules
    in the folder's `schedules.json`.
  - **Internal mass** is filled where DOE has it and openstudio-standards does not.
- **Services.** Elevators, kitchen exhaust fans, exterior lights, and refrigeration
  cases and racks are added as building services with their DOE values and schedules.
- **Water (amends ADR 0018).**
  - Water-use draws keep their DOE zone attachment and carry EnergyPlus's sensible (0.2)
    and latent (0.05) fractions, which are applied.
  - The sensible gain is fraction × flow × cp × (mixed temperature − zone air
    temperature).
  - The latent fraction is a share of the evaporable water, not of heat.
  - Water heaters and plant stay out of scope, since BEMGen tests at ideal-loads grade.
- **Calendar.**
  - The DOE files' 10 US holidays are recorded as the family's source calendar.
  - Daylight-saving time is recorded as metadata and not applied to schedules.
- **Midrise Apartment** in the DOE Ref templates was not compared. Its rows are left with
  that reason and are taken up with the residential work.

### 4. Out of scope for v1.1.0

- The 90.1 templates; their prototype comparison is evidence only.
- HVAC, outdoor air, zone mixing and ventilation, and water heaters (systems stay
  deferred).
- Site, weather and cost data.
- Comfort-only People fields.
- The lights "replaceable" fraction (no daylighting in the DOE Ref models).
- Plan geometry, which is BEMGen's.

### 5. Consumer contracts

These are additive minor versions:
- Program JSON **5.1.0**
- detailed constructions **4.1.0**
- unified constructions **3.1.0**

The [consumer contract changes](../consumer-contracts-release-1.1.0.md) list them.
Existing fields keep their meaning.

## Consequences

- **Matching DOE.** The DOE Ref templates reproduce the DOE files at engineering
  tolerance, except where the register records a reason.
- **Testing.** The DOE files become an answer key, in the style of ADR 0035.
- **Retrieval stays opt-in.** CI cannot fetch the 4.6 GB of pinned archives, so
  answer-key tests read a committed extract of the compared values. The full
  comparison is rerun locally from the pinned archives.
- **BEMGen** receives a handoff for the new fields.
