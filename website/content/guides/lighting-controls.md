# Lighting controls

Release 1.5.0 records the lighting controls of the source models on every commercial
program, as the `lighting_controls` block of Program JSON 5.4.0 (release {{ release }} exports
Program JSON {{ schema:program }}). The decision record is ADR 0044; the release notes are
[`docs/release-notes-atlas-v1.5.0.md`](https://github.com/Energy-Atlas/archetype-atlas/blob/main/docs/release-notes-atlas-v1.5.0.md).

## The three parts of lighting

| Part | Where it is |
| --- | --- |
| Installed power (design level) | the `lighting` load, W/m²; fixed by template, except IECC 2021, which lowers it in some climates (`value_by_climate`) |
| Usage, with occupancy-sensor credits | the lighting schedule; from 90.1-2010 and IECC 2012 the credits are inside its fractions |
| Daylight dimming | `lighting_controls.daylighting`, new in 1.5.0 |

## Reading the block

```json
"lighting_controls": {
  "status": "known", "source": "pnnl_prototype",
  "daylighting": {
    "controlled_floor_fraction": 0.408, "controlled_lighting_fraction": 0.213,
    "illuminance_setpoint_lux": 377.0, "control_type": "continuous_off", "method": "split_flux",
    "minimum_input_power_fraction": 0.15, "minimum_light_output_fraction": 0.15,
    "stepped_control_steps": 3, "availability": "all_days_except_design_days",
    "controlled_zones": 12, "zones": 15},
  "evidence_id": "evidence-…"
}
```

(IECC 2021 medium office, rounded.)

- `daylighting: null` means the complete source model has no controls in these zones:
  a source zero. That holds for IECC 2006 and 2009, 90.1-2007, the DOE Ref templates,
  and the zones without windows in later editions.
- `status: unknown` means no source model represents the program (construction-only
  types, SuperMarket); the block gives the reason.
- `controlled_lighting_fraction` is the share of the program's lighting power under
  daylight control, the sum of the reference-point fractions weighted by zone
  lighting power. Multiply it by the daylight savings your simulation finds; do not
  apply it to the schedule.
- `daylighting_by_climate` lists the climate zones that differ (6A, 6B, 7A, 8A for
  skylit spaces, where the prototypes have smaller skylights).
- 90.1 programs also carry `standards_rule`: openstudio-standards' target
  illuminance for the space type and, for office whole-building types, the share of
  the primary and secondary sidelit areas assumed daylightable.

## Where the fractions come from

From release 2.3.0, Program JSON 6.0.0 labels the origin of every known block in
`lighting_controls.daylighting_origin` (ADR 0059):

```json
"daylighting_origin": {
  "kind": "prototype_zone_set",
  "climates": ["0A", "0B", "1A", "…", "8A"],
  "cited_climate": "0A",
  "note": "The fractions are geometry-derived from the Daylighting:Controls of the PNNL prototype zones …"
}
```

(90.1-2019 medium office, whole building.)

- `kind: prototype_zone_set`: the fractions are derived from the PNNL prototype's
  geometry: the floor fraction of the program's prototype zones with
  `Daylighting:Controls`, and the reference-point fractions weighted by zone lighting
  power. `kind: reference_model_scan`: no DOE reference model has controls, a source
  zero whatever the geometry.
- `climates` lists the prototype climates whose model gives `daylighting`; the
  others are in `daylighting_by_climate`. All 19 for most programs.
- `cited_climate` is the climate of the one model the evidence row cites. When all
  19 climates agree, as for the climate-independent 90.1-2019 medium office whole
  building, it is a copy (the first in climate order, 0A), not a choice of climate.

## The unoccupied lighting cap

From release 2.4.0, Program JSON 6.1.0 adds `lighting_controls.unoccupied_lighting_cap` to every known
block (ADR 0060, ADR 0061). PNNL's ASHRAE 90.1-2019 prototypes (header comment `LPD_Ctrl = 0.02`) give each
zone of the office, restaurant, retail and warehouse types one EMS program: while the zone's occupant count
is 0 and its lighting power is at least 0.02 W/ft², its lights are set to 0.02 W/ft² (0.215 W/m²).

```json
"unoccupied_lighting_cap": {
  "rule": {
    "cap_W_m2": 0.2153, "lighting_threshold_W_m2": 0.2151,
    "source_values": {"cap": 0.02, "threshold": 0.02, "unit": "W/ft2",
                      "cap_conversion_m2_per_ft2": 0.09290304, "threshold_conversion_m2_per_ft2": 0.093},
    "condition": "zone_occupant_count_zero",
    "comparison": "zone_lighting_power_density_at_least_threshold",
    "action": "set_lights_to_cap", "calling_point": "BeginTimestepBeforePredictor",
    "zones": 15, "controlled_zones": 15,
    "zone_conditions": [{"zone": "Perimeter_mid_ZN_2", "condition": "((DaylightSavings==0) && …"}]},
  "evidence_id": "evidence-…"
}
```

(90.1-2019 medium office, whole building, rounded.)

- `rule: null` is a source zero: the complete source model has no such program in these zones, and
  `nulls` gives the reason. That holds for 90.1-2007, 90.1-2013 and every IECC edition (no program in any of
  their 304 models; the office headers say `LPD_Ctrl = 0`), the DOE Ref templates (no EMS program at all), the
  90.1-2019 types whose prototypes carry no program (apartments, hospital, hotels, outpatient and the schools,
  whose headers say `LPD_Ctrl = 0.02` without a program) and the large office data centers.
- The threshold compares all of the zone's lighting; the cap sets its general Lights object. The PNNL program
  converts W/m² to W/ft² with 0.093 for the threshold and 0.09290304 for the cap, so the two differ in the
  fourth digit; both are kept as written (`source_values`).
- `condition`: `zone_occupant_count_zero` reads the zone's own People object. The warehouse storage zones read
  the office's (`other_zone_occupant_count_zero`, `condition_zone: "Zone1 Office"`).
- The strip mall stores also set their display lighting to 0 while capped
  (`additional_lighting_when_capped_W_m2`).
- `zone_conditions` keeps PNNL's own variants as written: one perimeter zone of the medium and large office
  is capped only outside 07:00 to 16:00 standard time, one small office zone only while the building's binary
  occupancy schedule is 0.
- The rule acts per zone and per timestep, on that zone's occupant count. A consumer applies it to each zone
  the program is assigned to; a zone whose people are never 0 is never capped.

## Limits

- The fractions come from the prototype geometry (`daylighting_origin`). A model with
  other windows or zoning should recompute them.
- Dwellings carry no block: none of the residential or manufactured-housing models
  has daylighting controls.
