# ADR 0055: Generation blocks for the IECC commercial and detailed office folders; coverage by folder class

Status: accepted (2026-11-01; owner decision F1 and review issues B2 and C8 of the 2026-10-31 review, stage
AT3). It amends [ADR 0051](0051-generation-parameters-in-the-release.md) section 3 (section 6 below). The
blocks ship in data release 2.3.0, which stage REL-A writes; generator 4.1.0 reads them.

## 1. Context

- **IECC commercial (F1, review S2-11).** The 96 IECC commercial folders (ADR 0040) had no
  `generation.json`. The generator's template table listed only 90.1 and DOE Ref, and the stage plan
  (X-3) said IECC "has no generator families". The IECC prototypes are PNNL's models of the same
  building types the generator samples from ComStock, with the 90.1 prototypes' geometry and zone names
  (ADR 0040 section 1). The owner accepted adding them (2026-11-01).
- **Detailed offices (B2, review S2-01).** BEMGen maps the DOE small, medium and large offices to the
  `*-office-detailed` folders (ADR 0039: the office prototypes with their space types), which had no
  blocks: 200 programs in 15 folders (3 types x 90.1-2007, 2013, 2019 and both DOE Ref templates), and
  33 of BEMGen's 153 layout keys per family. The plain office folders, which do have blocks, hold only
  the whole-building, data-centre and plenum programs.
- **The recorded deferral (C8, review S2-03).** Release 2.2.0's manifest and ADR 0051 section 3 said the
  plenum programs have no blocks; 10 plenums do (90.1 and DOE Ref large and medium office), because a
  generated folder gives every program a block. The clause about "DOE Ref types without a sampling
  building type" named an empty set.

## 2. Decisions

1. **Tables.** `atlas_schedules.programmes.TEMPLATES` names the six IECC editions (`IECC 2006` to `IECC 2021`,
   slugs `iecc_2006` to `iecc_2021`) beside 90.1 and DOE Ref; the table keeps only the slug (its second
   column, an unused openstudio-standards name, is dropped). `SAMPLING` maps `SmallOfficeDetailed`,
   `MediumOfficeDetailed` and `LargeOfficeDetailed` to the small, medium and large office sampling types.
2. **Builder.** `scripts/build_zone_recipes.py` writes each folder's document as
   `scripts.build_reference_recipes` writes the DOE Ref ones: a `comstock_hours` block per source program
   (the folder's configuration), a `composition` block per mix, the shared hot-water services with a
   known volume on a schedule under the folder's configurations, and one building configuration per view
   (sampling type, People, rule-day inversion). 99 folders: 84 IECC (14 sampled types x 6 editions) and
   15 detailed offices; 1,262 programs (1,031 `comstock_hours`, 231 `composition`), 321 services, 99
   configurations.
3. **People.** A zone contributes floor area x its program's occupancy density, on the program's occupancy
   schedule, in zone-name order; residential spaces hold the dominant group when they hold most design
   people with multipliers (the DOE Ref rule, `build_reference_recipes.occupancy_carrier`). The zones are:
   - IECC: each program's `source_zones`, the PNNL IDF zones it was extracted from (ADR 0040 item 3; no
     zone belongs to two programs);
   - detailed offices: the spaces of the pinned openstudio-standards geometry
     (`data/construction-inputs/geometry-v1.json`) with the program of their standards space type.
     DOE Ref has no detailed office models; its detailed programs come from the same geometry (ADR 0039).
   *Alternative:* copy the plain office's configuration. *Reason:* its People are the whole-building
   program's; the detailed programs have their own densities and schedules.
4. **Views.** `source` only. IECC programs have no fillings (ADR 0040 items 4 and 20); the detailed offices'
   fillings set zero loads and unconditioned plenums, which carry no slot, so the filled program generates
   as the source one (checked per program: `program_views`). The ADR 0051 rule stands: a `filled` view is
   written only where the filled program generates differently.
5. **Configuration IDs** are `<sampling type>[_detailed]__<template slug>__source`
   (`medium_office__iecc_2021__source`, `large_office_detailed__90_1_2019__source`), unique in the release.
6. **A known null schedule parameter is a known absence.** IECC plenums and attics without a thermostat
   carry `heating_setpoint_schedule_id` as `known` with value `null` (ADR 0040 item 9). The assembler made
   a setpoint slot with no schedule from it, and 102 IECC programs (and 30 mixes holding them) failed to
   generate. `programmes.known_schedule` now adds a setpoint or activity slot only for a known parameter
   that names a schedule. No 2.2.0 block reads such a parameter, so no 2.2.0 recipe changes.
7. **Climate-dependent magnitudes.** In IECC 2021, 133 lighting, 6 additional-lighting and 5 hot-water
   loads and 9 services carry `value_by_climate` (ADR 0040 decision 3). The generator takes no climate:
   a bundle's amplitude and annual total use the record's `value` (the most common over the 19
   locations). The schedules do not vary by climate in any IECC program, and the ComStock transform does
   not depend on the magnitude, so the hourly fractions are right in every climate; a consumer takes a
   climate's magnitude from the program (Program JSON `value_by_climate`). *Alternative:* a climate input
   on commercial instances. *Reason:* a request and bundle change for magnitudes the consumer already
   reads from the program.
8. **IECC apartment buildings stay without blocks.** An apartment is a ResStock unit drawn under the
   folder's heating and cooling systems (`scripts.build_apartment_units`, ADR 0047), and the IECC systems
   are deferred (ADR 0040 item 10). The folder's corridors and offices could take `fixed` blocks, but a
   folder whose apartments cannot be drawn is not usable; the 12 folders wait for the systems.
9. **Checks** (`tests/test_zone_recipes.py`, ADR 0035 tolerance):
   - the geometry rule reproduces all 45 90.1 source configurations of the plain sampled types from the
     same geometry file, schedule order and inversion exactly and People within 1e-6 (largest difference
     1.3e-6 persons, relative 1e-9); those configurations carry the native openstudio-standards People
     (`tests/answer_keys/commercial/occupancy-dominance.json`);
   - the IECC People agree with the PNNL IDFs: `tests/answer_keys/commercial/iecc-people.json`
     (`scripts/capture/iecc_people.py`, the 84 Buffalo IDFs checked against their archive member
     checksums) gives each zone's design people from its People objects; total design people with
     multipliers per group agree within 1e-6 (largest relative difference 2.5e-11), the inversion and the
     zone floor areas exactly;
   - every document validates against `generation-v1.schema.json` and every block assembles; a sample
     generates bundles valid against the bundle schema with `amplitude x sum = annual total`;
   - a full run over the 2.2.0 release with the documents laid over it generated all 1,262 program views
     (45 of them inactive: plenums, attics and other spaces without loads) and 321 service variants without a failure (stage log, not a test:
     it takes about 25 minutes).
   The ComStock transform itself stays covered by the native family answer keys.
10. **Delivery.** Release 2.3.0 (stage REL-A) carries the 99 `generation.json` files:
    `python -m scripts.build_zone_recipes --out data/atlas-releases/v2.3.0` over the release it is built
    on (program IDs follow AT1's data changes, so the documents are derived, not committed). With them the
    release has 189 generated folders, 2,270 programs with blocks (2,847 views), 507 services and 219
    configurations.

## 3. Generation coverage by folder class (C8)

`scripts/generation_coverage.py` classifies every building folder with programs. A folder carries a
`generation.json` when the generator can generate its programs, and then every program has a block,
plenums and attics included: an unconditioned program without loads generates as inactive, so a block
says nothing about a plenum's conditioning. The folders without one:

| Class | Folders (with this ADR) | Reason |
| --- | --- | --- |
| Commercial types without a ComStock sampling building type | 36: 90.1 college, courthouse, laboratory, four data centres, generic office, tall, super-tall (x3); DOE Ref college, courthouse, office (x2) | the generator samples ComStock operating hours for 15 building types (`SAMPLING`) |
| IECC commercial apartment buildings | 12: high-rise and mid-rise x 6 editions | ResStock units need the folder's systems, deferred for IECC (decision 8) |
| Residential code-prototype dwellings | 18: IECC residential 2006 to 2024, HUD Code and DOE Final Rule | EnergyPlus prototypes with no ResStock dwelling inputs and no generator family (ADR 0041, ADR 0042) |

`generation_coverage.unexplained` lists any folder whose state matches no class; the tests require it to
be empty. From release 2.3.0 the manifest's `deferred` states these classes, with counts and members, in
place of 2.2.0's entry (`scripts/atlas_delta.py`, block `release 2.3.0`; `deferred(release)`). The site
index's per-folder reasons (review C7) are stage AT2's; they can read `folder_class` and `CLASSES`.

## 4. Generator 4.1.0

`atlas-schedules` 4.1.0 (minor): the tables of decision 1, the known-absence rule of decision 6, and the
validation of each `generation.json` against its schema when it is read (ADR 0056). Requests and bundles
are 4.0.0's; 4.1.0 reads release 2.2.0 as 4.0.0 does. The wheel REL-A builds bundles the 2.3.0 view.

## 5. Consequences

- BEMGen can draw the DOE offices (the detailed folders' programs now have blocks) and offer the IECC
  families in its DOE maps (owner F1; BEMGen stage REL-B). The new configuration IDs are opaque strings
  as before; every new block has a `source` view only, which is also the default view.
- IECC 2021 bundles report the most common magnitude for climate-dependent loads (decision 7).
- The plan X-3 exclusion of IECC from recipes is withdrawn for the commercial non-apartment types.

## 6. Amendment of ADR 0051 section 3

ADR 0051 section 3 says the generator cannot generate "IECC, manufactured housing, plenums without loads,
the construction-only programs, the DOE Ref types without a sampling building type". Read instead: blocks
are given by folder, every program of a generated folder has one (plenums included), and the folders
without blocks are the classes of section 3 above; the IECC commercial non-apartment types and the
detailed offices are generated from release 2.3.0.
