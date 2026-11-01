# Atlas release 2.4.0 (delta on 2.3.0): release and migration notes

Release 2.4.0 publishes the PNNL prototype corrections of the 2026-10-31 review, round 2
([ADR 0062](adr/0062-release-2-4-0.md); data [ADR 0060](adr/0060-release-2-4-0-pnnl-prototype-corrections.md),
contract [ADR 0061](adr/0061-program-json-6-1-0-unoccupied-lighting-cap.md)). It is a delta on 2.3.0:
`data/atlas-releases/v2.4.0` holds only its own files, and its `manifest.json` names 2.3.0 as `base_release`, with
that manifest's SHA-256, and lists the 2.3.0 paths it removes. Status `released` (2026-11-01).

## What changes for readers

- **Resolve the chain.** Read `v2.0.0`, then lay `v2.1.0`, `v2.2.0`, `v2.3.0` and `v2.4.0` over it, removing each
  manifest's `removed` paths (`scripts.atlas_delta.files('2.4.0')`). `scripts.atlas_exports.Release()`, the
  generator and the site default to 2.4.0.
- **The unoccupied lighting cap** (ADR 0060 section 1). Every known `lighting_controls` block gains
  `unoccupied_lighting_cap: {rule, evidence_id}`.
  - `rule` is PNNL's per-zone EMS program of the 90.1-2019 prototypes on 19 programs: while the zone's occupant count
    is 0 and its lighting is at least 0.02 W/ft² (`lighting_threshold_W_m2` 0.2150538), the zone's lights are set to
    0.02 W/ft² (`cap_W_m2` 0.2152782). The programs are the small, medium and large office whole building, the dining
    and kitchen of both restaurants, five stand-alone retail and three strip-mall programs, and the three warehouse
    programs. The rule keeps the condition, the comparison, the calling point and PNNL's variants as written: the
    large office calls it after the predictor, one perimeter zone of the medium and large office is capped only outside
    07:00 to 16:00 (`zone_conditions`), the small office's `Perimeter_ZN_2` also needs the building occupancy at 0, the
    warehouse storage zones read the office's occupant count (`condition_zone`), and the strip-mall display lighting
    goes to 0 while capped (`additional_lighting_when_capped_W_m2`).
  - **Explicit nulls.** `rule` is null, a source zero, on the 1,875 other known blocks, whose complete source models
    were read and carry no such program: 90.1-2007 (149) and 90.1-2013 (153), whose office headers say
    `LPD_Ctrl = 0`; the other 90.1-2019 types (134), including the schools, whose header says `LPD_Ctrl = 0.02`
    without a program; IECC 2006 to 2021 (918, `LPD_Ctrl = 0`); and the DOE reference models (521, no EMS at all).
    Program JSON gives each null's reason at `nulls["/lighting_controls/unoccupied_lighting_cap/rule"]` (status
    `none`). Blocks with `status: unknown` and the mixes carry no field, as for daylighting.
  - The atlas records the rule; applying it per zone and timestep is the consumer's (ADR 0061 section 4).
- **Office lighting power follows PNNL** (section 2). The 11 whole-building office programs of the 90.1 folders take
  the PNNL prototype `Lights` density, with evidence citing the IDF objects and the replaced value (W/m²):

  | Template | Program | Before (openstudio-standards) | After (PNNL) | Change |
  | --- | --- | ---: | ---: | ---: |
  | 90.1-2007 | `WholeBuilding - Sm Office` | 10.7639 | 10.67131 | −0.9 % |
  | 90.1-2007 | `WholeBuilding - Md Office` | 10.7639 | 11.02666 | +2.4 % |
  | 90.1-2007 | `WholeBuilding - Lg Office` | 10.7639 | 11.61158 | +7.9 % |
  | 90.1-2013 | `WholeBuilding - Sm Office` | 8.8264 | 10.90742 | +23.6 % |
  | 90.1-2013 | `WholeBuilding - Md Office` | 8.8264 | 10.19587 | +15.5 % |
  | 90.1-2013 | `WholeBuilding - Lg Office-basement`, `-others` | 8.8264 | 10.27324 | +16.4 % |
  | 90.1-2019 | `WholeBuilding - Sm Office` | 6.8889 | 6.98149 | +1.3 % |
  | 90.1-2019 | `WholeBuilding - Md Office` | 6.8889 | 6.66362 | −3.3 % |
  | 90.1-2019 | `WholeBuilding - Lg Office-basement`, `-others` | 6.8889 | 6.59986 | −4.2 % |

  Unchanged: the DOE Ref offices (already their DOE files' values), the detailed and generic office folders (no
  source value per room), and every other lighting difference between PNNL and openstudio-standards. Those 204 other
  rows are listed for the owner in [`docs/reviews/lighting-power-pnnl-vs-90-1.md`](reviews/lighting-power-pnnl-vs-90-1.md)
  (`python -m scripts.pnnl_lighting_power --review`), not changed.
- **PNNL building services** (section 3). 84 PNNL 90.1 objects become building services of 36 folders (90.1-2007,
  2013 and 2019 alike), stored as the IECC and DOE Ref families store theirs, with their PNNL schedules, heat fractions
  and evidence:
  - zone services (66): the elevator lift and lights and fan of the medium office, the secondary school, both
    apartments, the outpatient and the small hotel, and the kitchen reach-in freezers and refrigerators of both
    restaurants, both schools, the hospital and the large hotel. Each serves the program of its zone, which lists it in
    Program JSON `building_service_ids`;
  - building-level services (18): the exterior elevators and their lights and fans of the hospital, the large hotel
    and the large office, with no beneficiary and all heat lost (`assignment` `building_level`).

  The two objects an atlas program already carries are left out (the small-hotel lift motor, the outpatient elevator
  lights and fan). The services carry no generation block, as the IECC and DOE Ref elevators do not. The 90.1 folders
  now export building services 1.0.1.
- **IDs move.** 2,301 programs have new IDs (1,894 source programs, 296 department and 111 general mixes; no
  construction set). `id-map-2.4.0.json` at the release root maps each 2.3.0 ID to its 2.4.0 ID (`ids`). The old files
  are in `removed`, and every citing file follows. `id-map-2.3.0.json` and 2.0.0's `id-map.json` keep the earlier moves.
- **Counts.** `counts.services` is 1,635 (84 more) and `counts.unoccupied_lighting_cap` gives 19 programs with a rule
  and 1,875 with a null rule. Generation is 2.3.0's: 189 folders, 2,270 programs, 2,847 program views.
- **Export contracts** (ADR 0061):

  | Contract | Version | Schema |
  | --- | --- | --- |
  | Program JSON | **6.1.0** | `schemas/program-json-v6.1.schema.json` |
  | Detailed constructions | 5.0.0 | `schemas/construction-json-v5.schema.json` |
  | Unified constructions | 4.0.0 | `schemas/construction-equivalent-v4.schema.json` |
  | Source-model constructions | 2.0.0 | `schemas/construction-source-model-v2.schema.json` |
  | Building services | 1.0.1 | `schemas/building-services-v1.schema.json` |

  Program JSON 6.1.0 is 6.0.0 with the optional `lighting_controls.unoccupied_lighting_cap` (a minor change): a 6.0.0
  reader that embeds the new schema reads everything else as before. Every export names `atlas-release-2.4.0`.

## The generator

`atlas-schedules` 4.1.1 is 4.1.0's code whose wheel bundles the generator view of this release (ADR 0062 section 4).
The request and the bundle stay schema 4.0.0. A request that names a 2.3.0 program ID that moved is refused as an
unknown program; translate it through `id-map-2.4.0.json`. The 11 90.1 whole-building offices generate with their PNNL
lighting power. Install the wheel from the `atlas-schedules-v4.1.1` GitHub release and verify it with its
`SHA256SUMS.txt` ([the generator guide](schedule-generator.md)).

## Assets

The `v2.4.0` GitHub release carries `atlas-release-2.4.0.zip` (the `v2.0.0/` to `v2.4.0/` folders),
`atlas-release-2.4.0.manifest.json` (the release `manifest.json`), `id-map-2.4.0.json` and `SHA256SUMS.txt`, which
lists all three. Verify the tree with `python -m scripts.atlas_delta --verify`, and rebuild and compare with `--check`.

## Not in this release

- Not taken from the PNNL 90.1 prototypes, listed for the owner (ADR 0060 section 3): the kitchen walk-in refrigeration
  cases and racks, zone exhaust fans and exterior lights, which the IECC and DOE Ref families carry; the DOE Ref midrise
  apartment elevator. Types without a PNNL prototype were not checked.
- The large office data-center programs and the office space types inside other building types keep their
  openstudio-standards lighting power (in the owner list).
- The systems and water heaters of the IECC commercial and residential families stay deferred (ADR 0040, ADR 0038
  section 7), and the generation coverage is 2.3.0's (ADR 0055).
