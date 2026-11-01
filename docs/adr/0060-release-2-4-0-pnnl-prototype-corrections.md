# ADR 0060: Data corrections for release 2.4.0 from the PNNL prototypes (unoccupied lighting cap, office lighting power, elevators and reach-ins)

Status: accepted (2026-11-01; owner decisions of the 2026-10-31 review, round 2, items G4 (the atlas record), G5 and G7,
implemented in stage AT4). The owner principle of the round: follow the source evidence; add or change a value only where
the source definitions carry it, and trace it there. The edits are source changes on `main`
(`scripts/atlas_edits_2_4_0.py` and its three inputs); the delta folder of release 2.4.0 is written by stage REL-A2.
It amends [ADR 0044](0044-lighting-controls.md) (a new field of the lighting-controls block),
[ADR 0037](0037-doe-reference-reconciliation.md) section 1 (a second exception to its prototype rule) and
[ADR 0053](0053-release-2-3-0-data-corrections.md) section 2 (the small-hotel elevator lights and fan). The export
contract is [ADR 0061](0061-program-json-6-1-0-unoccupied-lighting-cap.md).

Sources: the PNNL prototype IDFs (`D:/Prototype Building Models`, `ATLAS_PROTOTYPE_ROOT`; archives and checksums in
`sources/reference-models-lock.json`), 90.1 and IECC, 16 types x 19 locations per edition, and the DOE reference IDFs
v1.4_7.2 (`ATLAS_DOE_IDF_ROOT`). Zones are grouped into programs by their template's geometry tags, as the lighting
controls are (ADR 0044; `scripts/pnnl_901.py`). Every value must agree in all 19 locations; the evidence cites the
Buffalo (5A) file, as ADR 0044 and ADR 0053 do. Each input is rebuilt from the IDFs by its script with `--check`.

## 1. The unoccupied lighting cap (G4)

**Context.** PNNL's ASHRAE 90.1-2016 to 2022 prototypes (header comment `LPD_Ctrl = 0.02`) give each controlled zone
an EMS program, for example `SET_Core_bottom_Light_EMS_Program` of `ASHRAE901_OfficeMedium_STD2019_Buffalo.idf`:

```text
SET Core_bottom_LSr_IP =0.093*Core_bottom_LSr/Core_bottom_Area          ! Zone Lights Electricity Rate / Zone Floor Area
IF (Core_bottom_Occ_Sensor <= 0) && (Core_bottom_LSr_IP >= 0.02)        ! People Occupant Count of the zone's People
  SET Core_bottom_Light_Actuator = 0.02*Core_bottom_Area/0.09290304      ! Lights Electricity Rate
ELSE
  SET Core_bottom_Light_Actuator = NULL
ENDIF
```

called at `BeginTimestepBeforePredictor`. The atlas holds 90.1-2019 of that series and did not record the rule.

**What the sources carry** (`python -m scripts.lighting_cap`, `data/program-inputs/unoccupied-lighting-cap-v1.json`):

| Source | Models | With the rule |
| --- | --- | --- |
| PNNL 90.1-2019 | 304 | 152: the small, medium and large office, both restaurants, both retail types and the warehouse (8 types x 19) |
| PNNL 90.1-2019 apartments, hospital, hotels, outpatient | 114 | 0 (no `LPD_Ctrl` header) |
| PNNL 90.1-2019 primary and secondary school | 38 | 0, although the header says `LPD_Ctrl = 0.02` |
| PNNL 90.1-2007 and 90.1-2013 | 304 each | 0 (the office headers say `LPD_Ctrl = 0`) |
| PNNL IECC 2006 to 2021 | 304 each | 0 (`LPD_Ctrl = 0`) |
| DOE reference models, pre-1980 and 1980-2004 (and new 2004) | 256 each | 0 (no EMS program at all) |

BEMGen's D-234 says the same five type groups carry it in 90.1-2016/2019; the scan confirms it per prototype for
90.1-2019. Within the eight types, 19 atlas programs have zones with the rule, every zone of each program (the large office
data-center zones and the plenums and attics have none). PNNL's own variants, kept as written:
- the large office programs are called `AfterPredictorAfterHVACManagers`;
- one perimeter zone of the medium and the large office (`Perimeter_mid_ZN_2`) is capped only outside 07:00 to 16:00
  standard time (`(DaylightSavings==0) && ((Hour < 7) || (Hour > 16))`, one hour earlier in daylight saving);
- one small office zone (`Perimeter_ZN_2`) only while the building's binary occupancy schedule is also 0;
- the warehouse fine and bulk storage zones read the occupant count of the office's People object (`Zone1 Office`);
- the strip mall stores also set their display lighting (`*_lights_ALLOWANCE`) to 0 while capped.

The threshold uses the program's 0.093 m²/ft² and the cap 0.09290304: 0.02 W/ft² is 0.21505 W/m² as a threshold and
0.21528 W/m² as a cap. Both are kept, with the values as written.

**Decision.**
- **Every known `lighting_controls` block gains `unoccupied_lighting_cap: {rule, evidence_id}`** (1,894 source programs).
  `rule` is the rule of the program's zones (19 programs, 90.1-2019) or **null**, a source zero, where the complete source
  model has none in those zones (1,875 programs: 90.1-2007 149, 90.1-2013 153, 90.1-2019 134, DOE Ref 521, IECC 918).
  `evidence_id` cites the EMS programs of the zones (their lines as `original_value`) or the scan that found none, whose
  interpretation is the reason the export gives for the null. Blocks with `status: unknown` (no source model represents
  the program) and mixes are unchanged: consumers read the members' blocks, as for daylighting.
- **The rule's fields**: `cap_W_m2` (0.2152782), `lighting_threshold_W_m2` (0.2150538), `source_values` (0.02 and 0.02
  W/ft², the two conversions), `condition` (`zone_occupant_count_zero`, or `other_zone_occupant_count_zero` with
  `condition_zone`), `comparison` (`zone_lighting_power_density_at_least_threshold`: all of the zone's lighting),
  `action` (`set_lights_to_cap`: the zone's general Lights object), `calling_point`, `zones` and `controlled_zones`, and
  where they apply `zone_conditions` (zone, condition as written, named sensors) and
  `additional_lighting_when_capped_W_m2` (0, the strip mall).
- **Explicit nulls everywhere, not only in 90.1-2019.** *Alternative:* record the field only in the 90.1-2019 folders,
  so that 189 rather than 2,301 IDs move. Rejected: an absent field reads as "not stated", while every source model of
  the other templates was read and states that there is none (the owner's G4 note on IECC is exactly that statement);
  one shape across families lets a consumer test `rule` without knowing the family.
- **Application stays with the consumer.** The rule acts per zone and timestep on the zone's occupant count. BEMGen
  applies it only to zones whose people are not zero at all times (G4, BEMGen side, stage REL-B2).

## 2. Office lighting power follows PNNL (G5)

**Context.** The atlas 90.1 programs take their lighting power density from openstudio-standards space-type rows. The
whole-building office rows give one code value per template (90.1-2019: 0.64 W/ft², 6.889 W/m²). PNNL's 90.1 office
prototypes give every zone of the office one `Lights` density that differs from it. The reconciliation (ADR 0037) holds
that such prototype against openstudio-standards load differences do not matter. The owner decided that office lighting
power follows PNNL.

**Decision.** A second recorded exception to that rule (ADR 0037 amendment). The 11 whole-building office programs of
the 90.1 folders take the PNNL density (`python -m scripts.pnnl_lighting_power`,
`data/program-inputs/pnnl-lighting-power-exceptions-v1.json`): the `Watts per Zone Floor Area` of the zone `Lights`
objects of the program's zones, which are equal on every zone and in every location. The load cites a new evidence row:
locator `Lights <objects>/Watts per Zone Floor Area {W/m2}`, the Buffalo IDF as its source file, and the replaced value
and evidence ID in its original value. The lighting schedule and heat fractions stay.

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

(W/m². No mix holds these programs, so no mix is recomposed; the edit refuses to run if one did.)

**Checked and unchanged.**
- **DOE Ref offices** (small, medium, large; pre-1980 and 1980-2004): the DOE files give 19.48, 16.89 and 16.14 W/m²
  on every zone, which the atlas values (19.4827, 16.8993, 16.1459) equal within the IDFs' printed precision (ADR 0037's
  rounding rule). The DOE Ref offices are already the source file's value.
- **The detailed office folders** (small, medium and large office detailed, 90.1 and DOE Ref) keep their room densities.
  They are openstudio-standards space types (open office, conference, corridor, …), and no PNNL or DOE model has a zone
  per room, so there is no source value per room; scaling the rooms to PNNL's building value would invent one. Their
  area-weighted general mixes are consistent with PNNL's whole-building values in 90.1 (2019: large −0.9 %, medium
  −0.3 %, small +1.2 %; 2007: +0.0 %, −0.8 %, −1.7 %; 2013: +1.7 %, +1.9 %, +8.6 %), and differ from the DOE Ref
  building values (−27 % to +15 %), which use a building-area method the rooms do not follow.
- **The generic `office` folders** (openstudio-standards' Office building type, ComStock's) keep their copies of the
  whole-building rows: no prototype represents that building type.
- **Other office programs**: the large office data-center programs (90.1: 10.76 / 8.83 / 6.89 W/m² against PNNL's
  data-center zones 14.85 / 17.87 / 9.78) and the office space types inside other building types are listed for the owner,
  not changed.

**The owner list.** `python -m scripts.pnnl_lighting_power --review` writes
[`docs/reviews/lighting-power-pnnl-vs-90-1.md`](../reviews/lighting-power-pnnl-vs-90-1.md): every 90.1 program whose PNNL
zone group gives a different lighting or additional-lighting density (relative difference above 1e-5), 215 rows, 11 of
which take the PNNL value. The rest, by type (PNNL against atlas, all three templates):

| Type | Rows | Range | Largest |
| --- | ---: | --- | --- |
| Highrise and midrise apartment | 34 lighting, 18 additional | −34 % to +20 %; additional −67 % | apartment units −21 % to −34 %, additional lighting 0.97 against 2.91 W/m²; corridors +5 % to +20 % |
| Hospital | 27 | −44 % to +86 % | ICU patient rooms +84 % (2013, 2019), ER exam, trauma and triage −44 % (2007), offices +15 % to +35 % |
| Outpatient | 20 | −44 % to +295 % | electrical and elevator pump rooms +226 % to +295 % (2013, 2019), procedure room −44 % (2007) |
| Large hotel | 16 | −15 % to +100 % | banquet and cafe +100 %, lobby +65 % (2019) |
| Small hotel | 17 | −15 % to +65 % | guest lounge +65 % (2019), corridors and exercise +20 % |
| Primary and secondary school | 32 | −13 % to +54 % | gym +54 % (2013), library +19 % to +34 % |
| Large office (not whole building) | 6 | −4 % to +103 % | data center +38 % to +103 %, main data center −4 % to +16 % |
| Full and quick service restaurant | 12 | −59 % to −1 % | quick-service dining −59 % (2007), kitchens −8 % to −25 % |
| Stand-alone retail | 6 | −22 % to +14 % | entry −22 % (2007) |
| Strip mall | 7 lighting, 6 additional | −1 % to +7 %; additional −0.1 % to +0.8 % | stores +7 % (2019) |
| Warehouse | 3 | −0.4 % to +23 % | office +23 % (2013) |
| Office space types of other types | (in the rows above) | −8 % to +35 % | |

## 3. Elevators and kitchen reach-ins (G7)

**Context.** AT1 found (ADR 0053 section 2) that the 90.1 programs carry the PNNL elevator lift motors only in the small
hotel and no kitchen reach-in refrigeration. The PNNL 90.1 prototypes carry them as objects of their own:
- zone `ElectricEquipment`, subcategory `ElevatorLift` and `ElevatorLightsFan` (medium office, both apartments, small
  hotel, outpatient, secondary school) and `ReachInFreezer` and `ReachInRefrigerator` (the kitchens of both restaurants,
  both schools, the hospital and the large hotel);
- `Exterior:FuelEquipment` `Elevators` and `Elevators_Lights_Fan` (hospital, large hotel, large office): no zone.

The IECC family stores the same objects of the IECC prototypes as building services (ADR 0040 item 9) and the DOE Ref
family its DOE elevators (ADR 0037 section 3), in `services.json`: a zone object as a service instantiated once per
building, serving the program of its zone, with its heat fractions; an exterior object as a `building_level` service whose
power is all lost.

**Decision.** The 90.1 objects become building services the same way (`python -m scripts.pnnl_services`,
`data/program-inputs/pnnl-building-services-v1.json`): 84 services in 36 folders (90.1-2007, 2013 and 2019 alike), with
their PNNL schedules (converted and checked over the year, ADR 0040's converter), heat fractions and evidence.

| Type | Objects (90.1-2019 values) | Representation |
| --- | --- | --- |
| Medium office | lift 16 363.22 W, lights and fan 125 W in `Core_bottom` | zone service of `WholeBuilding - Md Office` (radiant 0.5) |
| Secondary school | lift 22 659.35 W, lights and fan 125 W in `Mech_ZN_1_FLR_1` | zone service of `Mechanical` |
| Highrise / midrise apartment | lift 17 212.05 / 8 012.15 W, lights and fan 63 W in the top / ground corridor | zone service of the corridor program (lost 0.95) |
| Outpatient | lift 13 672.78 W in `Floor 1 Elevator Pump Room` | zone service of `ElevatorPumpRoom` (lost 0.9, radiant 0.1) |
| Small hotel | lights and fan 125 W in `ElevatorCoreFlr1` | zone service of `Elec/MechRoom` |
| Hospital, large hotel, large office | `Elevators` 57 630.4 / 75 383.39 / 226 203.93 W; lights and fan 501 / 376 / 752 W | `building_level`, lost 1.0 (no zone heat) |
| Kitchens of both restaurants, both schools, hospital, large hotel | reach-in freezer and refrigerator (156.7 to 555 W each), `Always_on` | zone services of `Kitchen` (`refrigeration_equipment`) |

- **Left out, already carried** (`EXCLUDED`, 6 objects): the small-hotel lift motor (the `Elec/MechRoom` program carries
  it, ADR 0053 section 2) and the outpatient elevator lights and fan (the `ElevatorPumpRoom` openstudio-standards density,
  57.05 / 22.60 W/m², is that load: the PNNL zone has no other equipment).
- **The small-hotel lights and fan**, which ADR 0053 left out with openstudio-standards' extra objects, is taken: it is a
  PNNL object (324 W in 2007, 125 W in 2013 and 2019). The second 32 110 W motor stays out (PNNL has none).
- **Service IDs** are readable and fixed at creation: `<template>.<type>.<end use>.<h6>` over the template, type, end use,
  object name, zone and source. Programs do not cite services by ID, so no program ID moves for them; Program JSON lists
  them in the beneficiary's `building_service_ids`, and the 90.1 folders now export building services 1.0.1.
- **Not taken** (not part of G7, listed for the owner): the PNNL 90.1 kitchen walk-in refrigeration cases and racks
  (hospital, large hotel, restaurants, schools), zone exhaust fans and exterior lights, which the IECC and DOE Ref families
  carry and the 90.1 family does not; the DOE Ref midrise apartment elevator (`G Corridor_Elevators_Equip`), whose
  folder ADR 0037 left uncompared. Types without a PNNL prototype (college, courthouse, laboratory, data centers, office,
  supermarket, tall buildings) were not checked.

## 4. IDs, references and the delta

`atlas_edits_2_4_0.edit(files('2.3.0'))` applies the three edits, re-derives every program ID by its rule and follows
them in every citing file (the 2.3.0 `generation.json` blocks, `definition-map.json`, `exporter-inputs.json`,
`services.json` beneficiaries). Over release 2.3.0 it changes or adds 2,938 files, removes 2,301 and moves 2,301 program
IDs (1,894 source programs, 296 department and 111 general mixes; no construction set). `id_map_bytes` writes the map
from 2.3.0 to 2.4.0 IDs for the delta. Re-deriving the IDs of the result moves none, no file cites a moved ID, every
edited file meets its release-record schema, and the generator assembles the edited folders.

## 5. Consequences

- Values change only in the 11 office lighting loads; the cap is a new record field, and the services are new records.
- Stage REL-A2 writes the 2.4.0 delta from `edit(files('2.3.0'))` with `id-map-2.4.0.json`, adds the three inputs and the
  edit module to the release block's `input_sha256`, and moves `IN_TREE`, the site and the generator view to 2.4.0.
- BEMGen moves to 2.4.0 in REL-B2: the ID map, Program JSON 6.1.0, the new 90.1 building services (zone services into
  their beneficiary's zones; building-level services with no zone heat) and the cap (G4, applied per zone).
