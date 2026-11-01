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

## Limits

- The fractions come from the prototype geometry (`daylighting_origin`). A model with
  other windows or zoning should recompute them.
- Dwellings carry no block: none of the residential or manufactured-housing models
  has daylighting controls.
