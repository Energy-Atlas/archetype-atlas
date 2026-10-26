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
6. **Not yet applied** (each needs a user decision):
   - research-assumption fillings under the resolution policy's rules;
   - hot-water services from the prototype inputs;
   - completion of the Courthouse schedules, which have no design-day rules.

   Until then the new programs hold source values only. Their `source` exports
   validate; 179 of their 858 `filled` exports do not, where a magnitude, the
   conditioning or schedule coverage is still unknown.

## Consequences

- Release 1.2.0 adds 858 programs (819 source programs and 39 general mixes) and
  193 HVAC systems.
- `python -m scripts.construction_only_programs --check` reproduces the input from
  the pinned sources. `python -m scripts.atlas_minor_release --release 1.2.0
  --check` reproduces the release.
- A later full rebuild of the pipeline would fold these types into the frozen
  releases. This ADR's input then retires.
