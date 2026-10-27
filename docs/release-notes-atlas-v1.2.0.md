# Atlas release 1.2.0 (commercial, delta): release and migration notes

Release 1.2.0 is a delta on release 1.0.0 (ADR 0036), like 1.1.0. A reader resolves
one base only, so 1.2.0 holds everything 1.1.0 changed (the DOE reference
reconciliation, ADR 0037), byte for byte. It also adds programs to the 51 folders
that had construction sets only
([ADR 0039](adr/0039-construction-only-programs.md)). Nothing else changes.

## What the release holds

- `data/atlas-releases/v1.2.0/` has 1,668 changed files and lists 371 deleted files.
  It is written and verified by `scripts.atlas_minor_release`.
- The resolved release has:
  - 1,825 programs (1.1.0: 967);
  - 1,198 HVAC systems (1,005);
  - 474 services (375).
- The definition input, `data/program-inputs/construction-only-v1.json`, is built
  offline from pinned sources by `scripts.construction_only_programs`, which
  reproduces it:
  - `sources/construction-only-programs-lock.json`: the new types' geometry, HVAC
    and prototype files;
  - `sources/openstudio-area-default-lock.json`: the floor-area flag default of
    OpenStudio 2.6.0 to 2.8.0.

## The new folders

- **Types:**
  - **90.1-2007, 2013, 2019:** college, courthouse, laboratory, the four data
    centres, the small, medium and large detailed offices, the generic office, and
    the tall and super-tall buildings.
  - **DOE Ref Pre-1980 and 1980-2004:** college, courthouse, the three detailed
    offices and the generic office.
- **Programs:** 819 source programs, one per space type found in the geometry. The
  generic office, which has no geometry, takes every Office space-type row.
- **Mixes:**
  - 39 general mixes, one per type with more than one counted program, and no
    department mixes. A data centre has a single program.
  - The generic office's mix borrows the large detailed office's represented areas.
- **Fillings,** by the resolution policy's rules (user-approved, 2026-10-26):
  - no gas where the source gas is null;
  - no occupancy for shafts, machine rooms, data centres, computer rooms and attics;
  - no lighting for elevator and service shafts and machine rooms;
  - unconditioned and no hot water for attics, and unconditioned for elevator and
    service shafts;
  - the zero-density schedule rule as everywhere.

- **Borrowed values (research assumptions, user decision):** the values these rules
  left null are borrowed so that every filled export validates (ADR 0039 section 6).
  - **Occupancy and plug loads of college support rooms:** the same space type of a
    school or the courthouse in the same template.
  - **Courthouse plug loads:** the same or an analogous space type (Library from the
    secondary school, Jury Assembly from Jury Deliberation, Courtroom from
    Conference, Cell from a hotel guest room, Parking from Storage, Security
    Screening from the 90.1-2007 courthouse).
  - **Lighting:** the `#N/A` DOE Ref Courthouse rows from the 90.1-2007 courthouse,
    and the 90.1-2019 College Entrance Lobby from the 90.1-2019 courthouse.
  - **Setpoints:** the tall buildings' corridors and the generic office's undefined
    rows take their building's most common thermostat.
  - **Undefined rows:** zero occupancy and plug load, like their zero lighting.
  - **Schedules:** the building's own most common schedule.
- **Hot water:** 99 services from the prototype inputs.
  - **College, courthouse and the detailed offices:** a lumped building draw.
  - **Laboratory and the tall buildings:** per-space-type draws.
  - **Tall buildings:** also booster and laundry loops; the prototypes fix 9 and 17
    hotel floors.
  - **Data centres:** none.
  - **Generic office (research assumption, user decision):** it has no prototype.
    Its hot water is the large detailed office's lumped main draw divided by that
    building's counted floor area, as a building draw per floor area:
    7.9 × 10⁻¹⁰ m³/s·m² in the 90.1 templates, 4.8 × 10⁻¹⁰ in the DOE Ref templates.
- **Systems:** 193 HVAC systems from the types' HVAC files. The tall buildings have
  no HVAC file upstream.
- **Courthouse schedules, `filled` export only:**
  - ten schedules without design-day rules take the Wednesday profile on design
    days (`accepted-design-day-weekday`);
  - `Courthouse BLDG_EQUIP_SCH` takes the Sunday profile on holidays
    (`accepted-holiday-sunday`).
- **Shafts:** the export's accepted-absence rule (ADR 0016) now also names shafts. A
  shaft's null lighting density therefore exports as zero beside its zero schedule.
  No earlier program is named for a shaft.
- **Gaps recorded:** 90 spaces have no standards tags or no matching row (tall
  buildings, detailed-office plenums, laboratory plenums). Spreadsheet errors (`#N/A`)
  in three DOE Ref Courthouse rows stay unknown in the source export.

## Exports

The contracts are unchanged from 1.1.0: Program JSON 5.1.0, constructions 4.1.0 and
3.1.0, and building services 1.0.0. They now also accept the release name
`atlas-release-1.2.0`. Read with `Release(release='1.2.0')`.

- **Source and filled:** every export of the new programs validates, mixes included.
  The source export keeps the borrowed values null.

## Verify

```
python -m scripts.atlas_release --verify
python -m scripts.atlas_minor_release --release 1.2.0 --verify
python -m scripts.atlas_minor_release --release 1.2.0 --check
python -m scripts.construction_only_programs --check
python -m unittest tests.test_construction_only
```

## Open decisions

None for this release. The borrowed values are listed in ADR 0039 section 6.
