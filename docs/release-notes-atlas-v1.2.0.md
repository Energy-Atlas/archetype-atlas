# Atlas release 1.2.0 (commercial, delta): release and migration notes

Release 1.2.0 is a delta on release 1.0.0 (ADR 0036), like 1.1.0. A reader resolves
one base only, so 1.2.0 holds everything 1.1.0 changed (the DOE reference
reconciliation, ADR 0037), byte for byte. It also adds programs to the 51 folders
that had construction sets only
([ADR 0039](adr/0039-construction-only-programs.md)). Nothing else changes.

## What the release holds

- `data/atlas-releases/v1.2.0/` has 1,648 changed files and lists 371 deleted files.
  It is written and verified by `scripts.atlas_minor_release`.
- The resolved release has:
  - 1,825 programs (1.1.0: 967);
  - 1,198 HVAC systems (1,005);
  - 457 services (375).
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

  Corridors, stairs, storage, restrooms and utility rooms keep unknown occupancy.
- **Hot water:** 82 services from the prototype inputs.
  - **College, courthouse and the detailed offices:** a lumped building draw.
  - **Laboratory and the tall buildings:** per-space-type draws.
  - **Data centres:** none.

  The tall buildings' booster and laundry loops depend on prototype parameters that
  the pinned data does not carry, so their programs' hot water stays unknown.
- **Systems:** 193 HVAC systems from the types' HVAC files. The tall buildings have
  no HVAC file upstream.
- **Courthouse design days:** in the `filled` export, ten Courthouse schedules
  without design-day rules take the Wednesday profile on design days
  (`accepted-design-day-weekday`).
- **Gaps recorded:** 90 spaces have no standards tags or no matching row (tall
  buildings, detailed-office plenums, laboratory plenums). Spreadsheet errors (`#N/A`)
  in three DOE Ref Courthouse rows stay unknown.

## Exports

The contracts are unchanged from 1.1.0: Program JSON 5.1.0, constructions 4.1.0 and
3.1.0, and building services 1.0.0. They now also accept the release name
`atlas-release-1.2.0`. Read with `Release(release='1.2.0')`.

- **Source:** every export of the new programs validates.
- **Filled:** 137 of their exports do not, each for a recorded reason:
  - **72:** values left unknown by the decisions above;
  - **60:** `Courthouse BLDG_EQUIP_SCH`, which has no holiday rule;
  - **5:** Courthouse service shafts, which the export's accepted-absence list does
    not name.

## Verify

```
python -m scripts.atlas_release --verify
python -m scripts.atlas_minor_release --release 1.2.0 --verify
python -m scripts.atlas_minor_release --release 1.2.0 --check
python -m scripts.construction_only_programs --check
python -m unittest tests.test_construction_only
```

## Open decisions

- **Holiday rule for `Courthouse BLDG_EQUIP_SCH`.** An earlier completion uses the
  Sunday profile on holidays for two office schedules.
- **Lighting density of Courthouse service shafts.** The writers map no
  lighting-density filling.
- **Hot water of the tall buildings' booster and laundry loops, and of the generic
  office.**
