# Atlas release 1.3.0 (commercial, delta): release and migration notes

Release 1.3.0 is a delta on release 1.0.0 (ADR 0036), like 1.1.0 and 1.2.0. A reader
resolves one base only, so 1.3.0 holds everything 1.1.0 and 1.2.0 changed, byte for
byte. It adds the IECC commercial prototype family
([ADR 0040](adr/0040-iecc-commercial-family.md)). Nothing else changes.

## What the release holds

- `data/atlas-releases/v1.3.0/` has 3,505 changed files and lists 371 deleted
  files. It is written and verified by `scripts.atlas_minor_release`.
- The resolved release has:
  - 230 folders (1.2.0: 134);
  - 2,959 programs (1,825);
  - 232 construction sets with 5,097 contexts (136 sets, 3,273 contexts);
  - 1,551 services (474).
- The six definition inputs, `data/program-inputs/iecc-commercial-<year>.json`
  (13.5 to 14.8 MB each), are extracted offline by `scripts.iecc_commercial_values`
  from the pinned PNNL archives (`sources/reference-models-lock.json`, family
  `commercial-iecc`). The extractor checks every IDF against the archive member
  checksums recorded at extraction and every converted schedule over the full year,
  holidays and design days (11,037 conversions).

## The new folders

- **Types:** HighriseApartment, MidriseApartment, Hospital, LargeHotel, SmallHotel,
  LargeOffice, MediumOffice, SmallOffice, Outpatient, QuickServiceRestaurant,
  FullServiceRestaurant, RetailStandalone, RetailStripmall, PrimarySchool,
  SecondarySchool and Warehouse, in `commercial/iecc-2006/` to `commercial/iecc-2021/`.
  Each program keeps the PNNL type name as `pnnl_building_type`.
- **Programs:** 153 source programs and 36 mixes per edition. A program is one
  standards space type, area-weighted over its IDF zones and their multipliers.
  Absence in the complete model is a source zero, so there are no fillings.
- **By climate:** loads that differ between the 19 locations keep the most common
  value and list the others in `value_by_climate`. This occurs in IECC 2021 lighting
  and in some 2021 hot-water draws. Skylight ratios of Stand-alone Retail and
  Warehouse vary from 2015.
- **Constructions:** one set per folder, 19 contexts keyed `0-a` … `8-a`, in the
  detailed representation only. Infiltration is the IDF design-flow method with its
  schedules inline, and the whole-building window ratios are on the set.
- **Services:** elevators, reach-in refrigeration, exhaust fans, exterior lights and
  equipment, and hot-water draws with their zone gains.

## Consumer contracts (additive minors)

- **Program JSON 5.2.0** (`schemas/program-json-v5.2.schema.json`):
  - `value_by_climate` and `schedule_id_by_climate` on loads;
  - `fenestration.value_by_climate`;
  - `source_zones`, `pnnl_building_type` and `standards_building_type`.

  Every 5.1.0 field keeps its meaning. Release 1.3.0 exports all its programs in 5.2.0.
  IECC programs export in the `source` version only: they have no fillings, and the
  `filled` version's water-heating fold needs source water heaters, which are deferred.
  A fraction schedule above 1 (two 2006/2009 small-hotel lighting schedules reach 1.1)
  is stored peak-normalized with the density scaled (`schedule_peak_scaling`).
- **Detailed constructions 4.2.0** (`schemas/construction-json-v4.2.schema.json`): the
  infiltration method `source_design_flow`, under `methods.source_design_flow`, which
  needs no `natural_ach`. Release 1.3.0 exports all its detailed sets in 4.2.0.
- **Unified constructions:** unchanged at 3.1.0. The IECC sets have none yet, and the
  export says so.
- **Building services 1.0.0:** the release enum gains 1.3.0.

## Migration

- Readers of 1.2.0 can read 1.3.0 unchanged; the new fields are optional.
- A consumer instantiating an IECC program for a climate zone takes
  `value_by_climate[zone]` where present, else `value`. Zones 7 and 8 are labelled `7A`
  and `8A`.
- IECC construction assignments may be scoped to a story position (`ground_floor`,
  `middle_floors`, `top_floor`, `basement`, `single_story`) or carry surface-level
  `source_element_ids` (selection decision `surface_override`).

## Verification

- `python -m scripts.atlas_minor_release --release 1.3.0 --verify` and `--check`
  (rebuild byte for byte).
- Releases 1.0.0, 1.1.0 and 1.2.0 still verify. Release 1.2.0 pins the builder script,
  so release 1.3.0 is a tagged block that is stripped when checking 1.2.0 (ADR 0040,
  agent decision 17).
- `tests/test_iecc_commercial.py` runs the answer keys against the IDFs in Buffalo,
  Miami and Fairbanks for every type and edition at 1e-6. The checks cover program
  densities and schedules, window ratios, infiltration rules and exterior wall
  resistances. The tests skip without the IDFs.
- Evidence only: `docs/reviews/iecc-commercial-vs-90-1.md`
  (`python -m scripts.iecc_commercial_review --check`).
