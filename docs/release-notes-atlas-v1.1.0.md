# Atlas release 1.1.0 (commercial, delta): release and migration notes

Release 1.1.0 is a delta on release 1.0.0 (ADR 0036). It applies the DOE reference
reconciliation ([ADR 0037](adr/0037-doe-reference-reconciliation.md)) to the two DOE
Ref templates, `doe-ref-1980-2004` and `doe-ref-pre-1980`. The 90.1 templates, and
the DOE Ref Midrise Apartment folders, are unchanged.

## What the release holds

- `data/atlas-releases/v1.1.0/` has the 504 files that differ from 1.0.0. Its
  manifest names 1.0.0 with that manifest's SHA-256 and lists 371 deleted files:
  programs and schedules whose content-hashed IDs changed (ADR 0036 section 8).
- The resolved release has 967 programs (1.0.0: 957) and 375 services (217). Its
  other counts are unchanged: 134 folders, 136 construction sets, 3,273 construction
  contexts, 1,005 HVAC systems, 734 water programs.
- The register, `data/reconciliation/doe-reference-v1.json`, has 1,874 rows: 725 add,
  242 replace, 264 keep, 590 fill, 43 leave and 10 omit. A further 148 identical
  schedules are counted but not listed. The site page
  [DOE reference reconciliation](../website/content/guides/doe-reference-reconciliation.md)
  is generated from it.
- The definition input, `data/reconciliation/doe-reference-values-v1.json`, holds the
  values the release applies. It is extracted from the 30 pinned IDFs (Chicago 5A),
  so a rebuild does not need the IDFs. It has 324 converted schedules and 1,558
  evidence rows, and records that the other 15 climate files of each model give the
  same window ratios and infiltration.

## What changes in the DOE Ref folders

- **Schedules:** 920 program schedule slots (230 programs) take their DOE schedules.
  This covers holiday rules, design days, the dated upstream edits, assignments, and
  22 slots whose atlas schedule differed from DOE over the year (for example, the
  hospital ER cooling setpoint pointed at a heating schedule). The Warehouse
  occupancy and lighting edit of 2024-06-07 is documented upstream and kept, with
  DOE's profile as an alternate.
- **Densities:**
  - Explicitly wrong values are replaced: Supermarket produce plug load, 0.54 to
    5.38 W/m².
  - The small-hotel elevator, which openstudio-standards folded into Elec/MechRoom,
    moves to a building service.
  - 226 densities the atlas held only through a research-assumption filling are now
    DOE source values.
  - Additional lighting is filled as zero where DOE's single lighting object equals
    the atlas lighting.
  - Existing-building densities that are plausible are kept, 40 of them, with DOE
    values as alternates where the two differ by more than half.
- **Heat fractions** take DOE's values where they differ.
- **Hot water:**
  - The 72 programs that had no hot-water demand are filled with zero, because they
    have no DOE draw.
  - DOE's water-use gains (sensible fraction 0.2, latent 0.05) are applied to every
    hot-water demand in the 12 types with DOE draws.
  - DOE's flow schedules replace the edited ones.
- **New programs:**
  - Outpatient `Utility` (utility rooms and sterile storage, previously Janitor).
  - PrimarySchool `ComputerRoom` and `Library` (previously Classroom).
  - Large Office `Basement` (previously the whole-building office program).
  - Each lists the source spaces it represents, and its parent lists them as
    excluded. The mixes are recomposed by the composer itself with those areas.
    PrimarySchool gains the `Activity_Mixed` department its recipe already named.
- **Controls:** the humidity setpoints of the hospital and outpatient.
- **Calendar:** the DOE files' 10 holidays and the daylight-saving rule (recorded, not
  applied) on every program.
- **Window ratios:** per program (N, E, S, W and roof) and, on the construction sets,
  the 15 whole-building values.
- **Constructions:**
  - The DOE design-flow infiltration method sits beside the fixed natural ACH, which
    stays the default.
  - Internal mass is filled for the 20 source spaces per template where DOE has it
    and openstudio-standards does not.
- **Building services:** 158 are added. They are 46 refrigeration cases,
  36 exhaust fans, 32 refrigeration racks, 30 exterior lighting objects and
  14 elevators, each with DOE values and schedules.

## Consumer contracts

These are additive minors. Every 1.0.0 field keeps its meaning.

| Export | 1.1.0 | 1.0.0 |
| --- | --- | --- |
| Program JSON | 5.1.0 | 5.0.0 |
| Detailed construction | 4.1.0 | 4.0.0 |
| Unified construction | 3.1.0 | 3.0.0 |
| Building services | 1.0.0 (new) | — |

[Consumer contracts of release 1.1.0](consumer-contracts-release-1.1.0.md) lists the
fields.

## Migration

- Read 1.1.0 through `scripts.atlas_delta_release.files()`, or with
  `Release(release='1.1.0')` in `scripts.atlas_exports`. Programs whose content
  changed have new IDs. Their names and source IDs are unchanged.
- Consumers that build a calendar take the holiday rules from `source_calendar` and
  select `Hol` schedule rules on those dates.
- BEMGen:
  - assigns the new programs to the listed source spaces;
  - instantiates building services once per building;
  - takes the infiltration method by `default_method` or by name.
  The [handoff note](bemgen-handoff-doe-reconciliation.md) lists the tests.

## Verify

```
python -m scripts.atlas_release --verify
python -m scripts.atlas_delta_release --verify
python -m scripts.atlas_delta_release --check
python -m scripts.atlas_exports --check-schemas
python -m scripts.reconciliation_page --check
python -m unittest tests.test_reconciliation_register tests.test_reconciliation_values tests.test_reconciliation_release
```

With `ATLAS_DOE_IDF_ROOT` set to the extracted `doe-reference/v1.4_7.2` folder, the
release tests also compare all 1,370 program slots with the DOE Schedule:Compact
objects over the full year.

## Limits

- **Building-level hot water** in the Hospital (main, booster, laundry), both
  schools, Small Office and Supermarket carries the DOE gain fractions but names no
  beneficiary program. DOE attaches these draws to zones; the atlas keeps them as
  absolute building demands, so their zone attachment stays unresolved
  (`zone_heat_assignment`).
- **Small-hotel elevator cores and attic:** DOE gives these zones no thermostat, so
  their null setpoints are source-backed (`R-UNCONTROLLED`). The mixes that include
  them keep null setpoints.
- **Six program slots** are served by several DOE schedules across the program's
  zones, all in the secondary school. The area-dominant schedule is applied, and the
  others are recorded (`R-SLOT-CONFLICT`).
- **Not compared:** Midrise Apartment, systems, site data and plan geometry (ADR 0037
  section 4).
