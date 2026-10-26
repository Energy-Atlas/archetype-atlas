# Construction-only programs

Release 1.2.0 adds programs to the 51 template × building-type folders that earlier
releases gave construction sets only. The decision record is ADR 0039; the release
notes are `docs/release-notes-atlas-v1.2.0.md`.

| Templates | Building types |
| --- | --- |
| 90.1-2007, 2013, 2019 | College, Courthouse, Laboratory, four data centres, Small/Medium/Large Office Detailed, Office (generic), Tall Building, Super Tall Building |
| DOE Ref Pre-1980, 1980-2004 | College, Courthouse, Small/Medium/Large Office Detailed, Office (generic) |

## Where the values come from

- **Space-type programs:** one per space type found in the type's openstudio-standards
  geometry file, with that template's space-type row. Source values only.
- **Mixes:** each type has one general mix weighted by represented floor area, and no
  department mixes. A data centre has a single program, so it has no mix.
- **Systems:** from each type's openstudio-standards HVAC file. The tall buildings
  have none upstream.
- **Hot water:** from the prototype inputs, along the same source branches as the
  original types:
  - **College, Courthouse and the detailed offices:** a lumped building draw.
  - **Laboratory and the tall buildings:** per-space-type draws.
  - **Tall buildings:** booster and laundry loops, which their prototypes create
    for their fixed hotel floors.
  - **Data centres:** none.

## Research assumptions

These are user decisions (2026-10-26), each recorded with its evidence in the
release:

- **Generic office floor areas.** The generic office has no geometry file. Its
  general mix borrows the represented areas of the large detailed office, whose
  spaces carry the same Office space types.
- **Generic office hot water.** It has no prototype either. Its hot water is the
  large detailed office's lumped main draw divided by that building's counted floor
  area, as one building draw per floor area:
  - 7.9 × 10⁻¹⁰ m³/s·m² in the 90.1 templates;
  - 4.8 × 10⁻¹⁰ m³/s·m² in the DOE Ref templates.

  The source does not make this assumption; treat it as an estimate.
- **Fillings.** The atlas's filling rules extend to the new programs:
  - no gas where the source gas is null;
  - no occupancy for shafts, machine rooms, data centres, computer rooms and
    attics;
  - no lighting for shafts and machine rooms;
  - unconditioned and no hot water for attics, and unconditioned for shafts.

  Corridors, stairs, storage, restrooms and utility rooms keep unknown occupancy.
- **Courthouse schedules, filled export only:**
  - ten schedules without design-day rules take the Wednesday profile on design
    days;
  - `Courthouse BLDG_EQUIP_SCH` takes the Sunday profile on holidays.

## Known gaps

- **Unmapped spaces:** 90 spaces have no standards space-type tags or no matching
  row. They are tall-building spaces, detailed-office plenums and laboratory
  plenums.
- **Spreadsheet errors:** three DOE Ref Courthouse rows give `#N/A` as lighting
  density. The value stays unknown.
- **Blocked filled exports:** some new programs have no filled export because a
  value stays unknown. Their source exports are complete.
