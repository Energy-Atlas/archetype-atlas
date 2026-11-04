# ADR 0063: Conditioning sides from the source equipment, per-side mixes and Program JSON 6.2.0

Status: accepted (2026-11-04; owner decisions D1b, D2b, D3 and D5 of the setpoint-placeholder discussion of 2026-11-04,
`D:/reviews/2026-11-04-setpoint-placeholders/discussion.md`, implemented in stage AT5). D1c (a temperature warning) and
D4 (merging in zonings) are BEMGen's. It amends [ADR 0012](0012-program-composition-simplification.md) (the setpoint rule
of the mixes) and the implementation notes of [ADR 0037](0037-doe-reference-reconciliation.md) (the small-hotel mixes
that kept null setpoints). The release is [ADR 0064](0064-release-2-5-0.md).

## 1. Context

The DOE and PNNL prototypes give some zones a thermostat whose setpoint no equipment acts on: 50 °C cooling in the
warehouse bulk storage, 100 °C in the stand-alone retail entry, 40 °C cooling and 7.2 °C heating in the small-hotel
stairs, mechanical room and storage. The atlas shipped them as schedules, and its mixes averaged them by area
(ADR 0012): `warehouse.department.storage-mixed` cooled at 42.9 °C in release 2.4.0. The source evidence that they are
placeholders is the equipment, not the temperature (owner D1b): the prototype's HVAC map says which system serves
each space, and what the source builds for a system type says which sides it serves.

## 2. Decisions

### 2.1 Which sides the source equipment serves (`scripts.conditioning_sides`)

- **Source per family.**
  - **90.1 and DOE Ref**: the openstudio-standards prototype (pinned `c8c1b9eb`, every file through its checksum lock
    in `sources/`, fetched into `data/raw`). The HVAC map is the file the template's `prototype_inputs.json` names as
    `hvac_json` (`data/geometry/ASHRAE*.json`, `DOERef*.json`): systems with a `type` and the `space_names` they serve.
    The geometry is the template's `geometry_osm`, as the compositions read it. One map was not locked
    (`ASHRAE2013LargeDataCenter.json`, the 90.1-2013 and 2019 large data centres) and is pinned by
    `sources/conditioning-sides-lock.json`.
  - **IECC**: the PNNL IECC prototype IDFs, from which ADR 0040 built the programs. Their thermostats already give each
    program its sides (`parameters.conditioning`; a heating-only thermostat, `ThermostatSetpoint:SingleHeating`, or
    none). The IDFs' zone equipment agrees: the warehouse bulk storage, the retail entry and the small-hotel stairs and
    mechanical room have unit heaters and heating-only thermostats; the small-hotel storage and laundry and the
    apartment corridors have neither (`docs/reviews/conditioning-sides-idf-check.md`). IECC source programs do not
    change.
- **What a system type serves is what the source builds.** `Prototype.Model.hvac.rb#model_add_hvac` dispatches each type
  to a builder in `Prototype.hvac_systems.rb`; the builder's coils are its sides. The map's `cooling_type` field is not
  used on its own: a PVAV record has no `cooling_type`, yet `model_add_pvav` makes a two-speed DX (or chilled-water)
  cooling coil. `SYSTEMS` in the script names each builder; the build checks the dispatch calls it and that the builder
  creates heating coils exactly where a heating side is declared and cooling coils exactly where a cooling side is
  (the line numbers are recorded in the input's `system_types`):

  | Type | Builder | Heating | Cooling |
  | --- | --- | --- | --- |
  | PSZ-AC, PTAC, SAC | `model_add_psz_ac`, `model_add_ptac`, `model_add_split_ac` | the record's `heating_type` | the record's `cooling_type` |
  | PVAV, VAV, CAV, DC, DOAS Cold Supply, Packaged DOAS, WSHP, PTHP | `model_add_pvav`, `…_vav_reheat`, `…_cav`, `…_data_center_hvac`, `…_doas_cold_supply`, `…_doas`, `…_water_source_hp`, `…_pthp` | yes | yes |
  | UnitHeater, Baseboards | `model_add_unitheater`, `model_add_baseboard` | yes | **no** |
  | CRAC, CRAH | `model_add_crac`, `model_add_crah` | **no** | yes |
  | Exhaust Fan, Zone Ventilation, Refrigeration_system | (no coil) | no | no |

- **A space is served on a side** when a system serving that side names a space of its thermal zone. OpenStudio matches
  names without regard to case, so the strip mall's `LGSTORE1` serves `LGstore1` (the PNNL strip-mall IDFs serve it).
- **A program's side** is `served` when every space of the program (by its standards space type; the DOE Ref zones that
  ADR 0037 gave programs of their own keep them) is served on it, `not_served` when none is, and `mixed` otherwise.
- **The DOE file holds for DOE Ref** (ADR 0037 section 1): `DOERefHospital.json` names no system for the hospital
  basement, but the DOE hospital files serve it from VAV_1 in all 16 climates, pre-1980 and post-1980. The input records
  that override (`DOE_FILE_SIDES`, with the IDF's SHA-256); the basement stays conditioned. No other DOE Ref program
  disagrees with its DOE file (the review).
- **Mixed service** (*agent decision*, the brief's first option): the DOE Ref outpatient `Utility` program (re-tagged
  by ADR 0037: the sterile storage, served by PVAV, and three utility rooms, served by nothing; served share 0.361) is
  left unchanged and listed. A rule (a served-area threshold, or splitting the program) is the owner's call.
- **Not decided**: the tall and super-tall buildings, whose prototype inputs name `ASHRAETallBuildingbase.json` and
  `ASHRAESuperTallBuildingbase.json`, which openstudio-standards does not have at this revision (HTTP 404). Their
  programs are unchanged.

The input, `data/program-inputs/conditioning-sides-v1.json`, holds 1,168 programs of 123 folders with both sides each
(`python -m scripts.conditioning_sides --check` rebuilds it).

### 2.2 A side with no equipment is an explicit null (D2b, D3)

- **The record** (`scripts.atlas_edits_2_5_0`, release 2.5.0): the setpoint parameter of a not-served side becomes
  `{"status": "known", "value": null, ...}`, a source-stated absence (the release-record rule of ADR 0040 item 9), and
  `parameters.conditioning` states both sides, `{"status": "known", "unit": "state", "value": {"heating_enabled": true,
  "cooling_enabled": false}}`. Both cite one new evidence row per program: the HVAC map file, the system indices as the
  locator, the systems with their sides and every space with its serving systems, and `replaced_schedules`: the
  replaced schedule's ID, source name, range (°C) and evidence ID. The schedule itself stays in the folder's
  `schedules.json`: nothing of the source is dropped.
- **A space no system serves has both sides absent**, even where the space type gives it a thermostat (the 90.1
  small-hotel storage).
- **The existing unconditioned treatment is kept**: programs that already carry a conditioning filling with both sides
  off (the small-hotel elevator cores and Elec/MechRoom, `R-UNCONTROLLED`; attics, plenums, shafts, the 90.1 high-rise
  apartment corridors) keep their records; the input must agree with each of them, and it does (76 programs).
- **Status vocabulary.** The record's statuses stay `known` and `unknown`; Program JSON 6.2.0 reports such a null as
  `not_conditioned` (section 2.4). *Alternative:* a new record status. *Rejected:* the release-record schema already
  reads a known null as a source-stated absence, and the reason sits with the evidence.

### 2.3 Per-side mixes (D5; amends ADR 0012)

ADR 0012 averaged each setpoint by area over all members. From release 2.5.0:

- **A member has a side** when its setpoint is known; **it lacks the side** when its record states the side is not
  conditioned: `parameters.conditioning` known (the new nulls, the IECC thermostats) or the stored unconditioned filling
  of ADR 0016 and ADR 0037; otherwise the side is **unknown**, and so is the mix's (null is not zero).
- **Each side is averaged over the members that have it, with the weights renormalised**:
  `w_i = A_i / Σ_{j has the side} A_j`, `T_side(t) = Σ w_i T_i(t)` (pointwise, `program_composition.mix_schedule`). Where
  every member has the side the stored schedule is unchanged, bit for bit.
- **Coverage**: `composition.setpoint_coverage = {"heating": c_h, "cooling": c_c}`, with
  `c = Σ_{has the side} A_i / Σ A_i` (1.0 where all members have it, null where a side is unknown).
- **A side no member has** is a known null (`not_conditioned`, coverage 0).
- The mix states `parameters.conditioning` from its coverage (a side is on when its coverage is above 0), citing a new
  evidence row with the members, which have the side, the weights and the coverage. **Other mixed values do not change.**
- **No coverage threshold** (the discussion's further option): a mix is not withheld below some coverage. The
  over-conditioning a low coverage implies in a zoning is BEMGen's D4d metric.
- The filled export already mixed each side over the members its view conditions (`program_json_v3`,
  `area-weighted-active-member-controls`); the record now does the same in the source view.

The release-record program schema becomes **1.1.0** (`schemas/atlas-release-program-v1.1.schema.json`, a minor: the
optional `composition.setpoint_coverage`); every earlier record validates against it with the same meaning.

### 2.4 Program JSON 6.2.0

| Export | Release 2.4.0 | Release 2.5.0 on | Class |
| --- | --- | --- | --- |
| Program JSON | 6.1.0 | **6.2.0** (`schemas/program-json-v6.2.schema.json`, `urn:archetype-atlas:program-json:6.2.0`) | minor: a new null status, an optional field |
| Constructions, building services | 5.0.0 / 4.0.0 / 2.0.0, 1.0.1 | unchanged | – |

6.2.0 is derived from 6.1.0 (`atlas_contracts.program_schema_6_2`); every 6.1.0 field keeps its meaning.

- **`nulls[*].status` gains `not_conditioned`**: a setpoint side no source equipment serves (for a mix: none of its
  members has it), so the side is absent. It applies to `/controls/heating_setpoint_schedule_id` and
  `/controls/cooling_setpoint_schedule_id` wherever the record states the side not conditioned, including the IECC
  programs' heating-only and unconditioned thermostats (6.1.0 called those `none`). The reason is the evidence row's
  interpretation, for example: "Bulk (1 source space): served by UnitHeater, 2 x Zone Ventilation in
  ASHRAEWarehouse.json; no cooling equipment. … cooling (source schedule 'Warehouse ClgSetp BulkStorage', 50.0 degC)."
- **`controls.setpoint_coverage`** (mixes only): `{"heating": number or null, "cooling": number or null}`, each in
  [0, 1]. A null coverage has its reason in `nulls` (`/controls/setpoint_coverage/*`, `unknown`).
- **`controls.conditioning_state`** in the source version is derived from `heating_enabled` and `cooling_enabled` where
  both are known (6.1.0 always wrote `unknown` there); the filled version already did.

```json
"controls": {"heating_enabled": true, "cooling_enabled": true, "conditioning_state": "heating_and_cooling",
             "heating_setpoint_schedule_id": "90-1-2019.warehouse.storage-mixed-heating-setpoint.98c1b8",
             "cooling_setpoint_schedule_id": "90-1-2019.warehouse.storage-mixed-cooling-setpoint.<h6>",
             "setpoint_coverage": {"heating": 1.0, "cooling": 0.30303030303030376}, ...}
```

## 3. What changes (release 2.5.0)

**Source programs: 72 with a side not conditioned** (60 cooling sides, 47 heating sides; 90.1 = 2007, 2013 and 2019):

| Program | Templates | Sides now absent | 2.4.0 setpoint (°C) |
| --- | --- | --- | --- |
| Warehouse `Bulk` | 90.1, DOE Ref | cooling | 50 (90.1); 24 to 30 (DOE Ref: the DOE thermostat is real, the equipment a unit heater) |
| Stand-alone retail `Entry` | 90.1, DOE Ref | cooling | 100 (90.1), 90 (DOE Ref) |
| Small hotel `Stair`, `Stair4`, `Mechanical` | 90.1 | cooling | 40 |
| Small hotel `Stair`, `Storage` | DOE Ref | cooling (both have unit heaters in DOE Ref) | 40 |
| Small hotel `Storage`, `Storage4Front`, `Storage4Rear` | 90.1 | heating and cooling | 7.2 / 40 |
| Small hotel `Laundry` | 90.1 | heating and cooling (no system; the PNNL IDFs have no thermostat either) | 21.1 / 23.9 |
| Midrise apartment `Corridor`, `Corridor_topfloor` | 90.1 | heating and cooling (no system, as in PNNL) | 21.7 / 24.4 |
| Midrise apartment `Corridor` | DOE Ref | cooling (unit heaters) | 15.6 / 40 |
| Outpatient `Elec/MechRoom`, `ElevatorPumpRoom`, `Janitor`, `Stair`, `Toilet`, `Undeveloped` | DOE Ref | heating and cooling (no system, as in the DOE files) | 18.3 to 21.1 / 22.2 to 25 |
| Courthouse `Parking` | 90.1, DOE Ref | heating and cooling (no system) | 15.6 to 21 / 24 to 26.7 |
| Large and small data centres (`StandaloneDataCenter`, `ComputerRoom`, high and low ITE) | 90.1 | heating (CRAH and CRAC build no heating coil) | 15 |

Unchanged: the 76 programs that already carry the unconditioned treatment, the DOE Ref outpatient `Utility` (mixed
service) and every IECC source program.

**Mixes: 69 with a coverage below 1**, 373 with full coverage (values unchanged), 4 with an unknown side (the 90.1-2007
and 2013 tall and super-tall general mixes, whose corridor members have unknown setpoints; unchanged). In every
template the five mixes the discussion named change; in 90.1-2019:

| Mix | Heating coverage | Cooling coverage | Cooling setpoint |
| --- | ---: | ---: | --- |
| `warehouse.department.storage-mixed` | 1.0 | 0.303 | 26.7 °C, the fine storage's (2.4.0: 42.9 °C) |
| `retail-standalone.general.general-mixed` | 1.0 | 0.994 | the retail zones' (no longer 100 °C at weight 0.006) |
| `small-hotel.department.vertical-circulation-mixed` | 0.781 | 0 | none (heated only) |
| `small-hotel.department.support-mixed` | 0.118 | 0 | none (heated only, at the mechanical room's 7.2 °C) |
| `small-hotel.general.general-mixed` | 0.917 | 0.862 | the conditioned members' |

The heating setpoint of `storage-mixed` is unchanged (11.69 °C, both members heat). The IECC warehouse mix has cooling
coverage 0.265 (its areas differ); the DOE Ref small-hotel support mix 0.945 / 0.473 (DOE Ref storage is heated and
the mechanical room and laundry fully conditioned). Beyond the five: the college and courthouse general mixes (0.993,
0.885: shafts and parking), the DOE Ref outpatient general mix (0.799) and the 90.1-2019 tall and super-tall general
mixes (0.937, 0.941), which ADR 0037's rule had left null because of their shafts.

**IDs.** Every mix gains its coverage, so all 446 mixes move, with the 72 source programs: 518 IDs
(`id-map-2.5.0.json`).

## 4. Consequences

- BEMGen reads a `not_conditioned` side as absent (ADR-018's `SingleHeating`), and a mix's coverage as the share of its
  floor area the side covers (handoff: `docs/bemgen-handoff-release-2-5-0.md`). The generator already averaged
  setpoints over the members that have them and reads a known null as no slot (atlas-schedules 4.1.0), so its code does
  not change; its bundled view does (atlas-schedules 4.1.2, ADR 0064).
- The LOD study's references change where these zones are (drop 6): the small-hotel storage and laundry become
  unconditioned, the bulk storage, the entry and the stairs lose their cooling side.
- A later prototype with a heating-only or unserved space is handled by the same rule when its HVAC map is read.

## 5. Open for the owner

- The DOE Ref outpatient `Utility` program (mixed service): keep, threshold, or split.
- The data-centre heating sides (CRAH, CRAC: no heating coil) follow the same rule and are now absent; the 15 °C was a
  heating setpoint no equipment acts on.
- The 90.1 small-hotel support mix is heated only at coverage 0.118; a coverage threshold for withholding a mix was not
  adopted.
- The tall and super-tall buildings have no HVAC map at the pinned revision.
