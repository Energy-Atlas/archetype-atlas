# ADR 0039: Programs for the construction-only folders

Status: accepted (2026-10-26, user decisions). Amends ADR 0002, whose selection gave
programs to 17 commercial types (83 template x building-type folders). Applies to
release 1.2.0, a delta on 1.0.0 under ADR 0036 that also holds release 1.1.0's
changes (ADR 0037).

## Context

51 folders had construction sets but no programs:
- **In each 90.1 template (2007, 2013, 2019), 13 types:** college, courthouse,
  laboratory, four data centres, the small, medium and large detailed offices, the
  generic office, and the tall and super-tall buildings.
- **In each DOE Ref template, 6 types:** college, courthouse, the three detailed
  offices and the generic office.

Every type except the generic office has a pinned openstudio-standards geometry
file and prototype definition. Every type's space types have rows in the template's
space-type table.

Every frozen pipeline stage rebuilds all its records from the legacy release and
verifies by full rebuild. The stages hard-code their scope:
- program-ID lists in the resolution policy;
- a gap count and an OpenStudio run receipt in the completion release;
- exact program and service sets in water reporting.

Extending them would rebuild five frozen releases and change existing construction
records.

## Decision

1. **A committed definition input instead of rebuilt releases (user, option B).**
   - `scripts/construction_only_programs.py` builds
     `data/program-inputs/construction-only-v1.json` offline from pinned sources.
     It runs the existing definition code for the new types only:
     - `scripts.build.Builder` for legacy records;
     - `scripts.program_definitions` and `scripts.hvac_definitions` for definitions;
     - `scripts.program_composition.compose` for mixes.
   - The release build overlays the input through the writers' source loaders
     (`scripts.construction_only_overlay`, `scripts.atlas_minor_release`). No frozen
     release changes, and no existing record changes.
2. **Sources.**
   - The new types' geometry, HVAC and prototype files are pinned in
     `sources/construction-only-programs-lock.json`. They were copied from the
     pinned openstudio-standards archive and checked against the foundation lock's
     digests.
   - A blank "Part of Total Floor Area" flag takes the OS:Space default of its OSM
     version, "Yes" in OpenStudio 2.6.0, 2.7.0, 2.7.1 and 2.8.0. The default is
     pinned in `sources/openstudio-area-default-lock.json` (downloaded with user
     permission, 2026-10-26).
3. **Programs.** One source program per space type found in the geometry, as for the
   original types.
   - **Generic office:** it has no geometry file, so it takes every Office space-type
     row of its template.
   - **Unmapped spaces:** spaces with no standards tags, or tags with no row, stay
     unmapped and are listed in `coverage_gaps` (90 spaces). These are:
     - the tall buildings' untagged spaces;
     - the detailed offices' untagged plenums;
     - the laboratory plenums.
   - **Spreadsheet errors:** the DOE Ref Courthouse rows give `#N/A` as lighting
     density for Cell, Courtroom and Parking. It stays unknown, and the error is
     kept in the evidence.
4. **Mixes (user).**
   - Every new type gets a general mix over its counted programs, and no department
     mixes. A data centre has one program, so it has no mix.
   - The generic office's general mix borrows the represented areas of
     `ASHRAELargeOfficeDetailed.osm`, whose spaces carry the same Office space types.
     It sits beside the unmixed space-type programs.
5. **Systems** come from each type's HVAC file. The tall buildings have none upstream.
6. **Fillings (user, 2026-10-26, F1 and F2).**
   - `scripts.resolve.resolve_records` runs on the new programs with the
     resolution policy's lists extended by the policy's own criteria:
     - no gas: every program whose source gas is null;
     - no occupancy: shafts, machine rooms, data centres, computer rooms and attics
       with null occupancy;
     - no hot water: attics;
     - unconditioned: attics.
   - Rows of the same form add "no lighting" for elevator and service shafts and
     machine rooms, and "unconditioned" for elevator and service shafts.
   - The rule for zero-density schedules (`explicit_zero_magnitude`) applies as
     everywhere.
   - These stay unknown: corridors, stairs, storage, restrooms and utility rooms
     with null occupancy; the Entrance Lobby with null lighting; the Courthouse
     plug-load gaps; the `#N/A` rows; and other null setpoints.
   - The reviewed twins come from `scripts.program_definitions.apply_reviewed`.
7. **Courthouse design days (user, F3).** Ten Courthouse schedules give every
   weekday, weekends and holidays, but no default or design-day rule. In the
   `filled` export, their design days take the profile of the rule that applies on
   Wednesday. This is recorded on the schedule as `accepted-design-day-weekday`,
   and the `source` export keeps the source rules. `Courthouse BLDG_EQUIP_SCH` is a
   different gap: it has design days but no holiday rule, so it is not completed.
8. **Hot water (user, F4).** The fixture paths of `scripts.commercial_water_paths`
   are ported for the new types:
   - **College, courthouse and the detailed offices:** one lumped building draw,
     with no beneficiary program.
   - **Laboratory and the tall buildings:** per-space-type draws from the
     space-type rows. The tall prototypes add one per space with a source flow.
   - **Data centres:** no hot-water loop.

   Programs that a source path proves have no draw get the zero-water fill
   (`source_complete_no_water_draw`). The tall buildings' booster and laundry loops
   depend on prototype hotel-floor parameters that the pinned data does not carry,
   so their programs' hot water stays unknown. The generic office has no prototype,
   so its hot water stays unknown too.

9. **What still blocks `filled` exports.** 137 of the 1,716 exports of the new
   programs do not validate, each for a recorded reason:
   - **72 left unknown by the decisions above:**
     - occupancy of corridors and other occupied support spaces;
     - conditioning of corridors;
     - Courthouse plug-load gaps, the `#N/A` lighting rows, the Entrance Lobby and
       undefined space types.
   - **60 from the missing holiday rule of `Courthouse BLDG_EQUIP_SCH`.**
   - **5 Courthouse service shafts.** The "no lighting" filling sets their schedule,
     as for plenums, but the writers map no lighting-density filling, and the
     export's accepted-absence list (ADR 0016) does not name service shafts.

   Every `source` export validates.

## Consequences

- Release 1.2.0 adds 858 programs (819 source programs and 39 general mixes), 193
  HVAC systems and 82 hot-water services.
- `python -m scripts.construction_only_programs --check` reproduces the input from
  the pinned sources. `python -m scripts.atlas_minor_release --release 1.2.0
  --check` reproduces the release.
- A later full rebuild of the pipeline would fold these types into the frozen
  releases. This ADR's input then retires.
