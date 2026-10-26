# Consumer contracts of release 1.1.0 (draft)

Release 1.1.0 applies the DOE reference reconciliation ([ADR 0037](adr/0037-doe-reference-reconciliation.md))
to the DOE Ref templates, as a delta on release 1.0.0. The exports gain fields; no
existing field changes meaning.

| Export | Version | Previous |
| --- | --- | --- |
| Program JSON | **5.1.0** | 5.0.0 |
| Detailed construction set | **4.1.0** | 4.0.0 |
| Unified construction set | **3.1.0** | 3.0.0 |

Status: draft from stage S4. The exact JSON shapes are fixed in stage S7, when the
schemas are derived.

## Program JSON 5.1.0

1. **`fenestration`** (per program):
   - `{"basis": "program_zone_surfaces", "wwr": {"N": …, "E": …, "S": …, "W": …},
     "roof": …, "evidence_id": …}`.
   - A WWR value is the window area over the exterior wall area of the program's zones
     in that direction, averaged by area over the reference model's zones.
   - `roof` is the skylight area over the exterior roof area.
   - `null` means the program has no exterior surface in that direction; `0` means it
     has wall but no window.
   - For a whole-building program the values equal the construction's
     `fenestration_defaults.conditioned`.
2. **Water-use gains.** A `hot_water` load (and `water_heating[].draw`) gains
   `thermal_effects`:
   - `{"zone_gains": "applied", "sensible_fraction": 0.2, "latent_fraction": 0.05,
     "semantics": "EnergyPlus WaterUse:Equipment"}`.
   - Sensible gain = fraction × mass flow × cp × (mixed − zone air temperature). The
     latent fraction is a share of the water that can evaporate.
   - The draw keeps its zone or program attachment.
3. **Humidity controls.** `parameters.humidifying_setpoint_schedule_id` and
   `parameters.dehumidifying_setpoint_schedule_id` are added where the source has a
   humidistat (DOE hospital, outpatient).
4. **`source_calendar`**:
   - `{"holidays": [{"name": …, "rule": …}], "daylight_saving": {"start": …, "end": …,
     "applied": false}, "evidence_id": …}`.
   - `holidays` lists the source's 10 US holidays as rules, for example "Last Monday in
     May".
   - Consumers that build a calendar for a given year use them to select `Hol`
     schedule rules.
5. **`alternates`** on any value: `[{"value": …, "source_family": …, "evidence_id": …,
   "reason_id": …}]`. An alternate is a second backed value, recorded where two sources
   disagree by more than the register's threshold. The primary value is unchanged.

## Construction sets 4.1.0 (detailed) and 3.1.0 (unified)

1. **`fenestration_defaults`**:
   - `{"conditioned": {"N", "E", "S", "W", "roof"}, "unconditioned": {…}, "all": {…},
     "evidence_id": …}`.
   - These are the reference model's whole-building WWR values, 15 in all, area-weighted
     over conditioned, unconditioned and all zone surfaces. The same nulls and zeros
     apply as in programs.
   - `roof` may differ by climate context where the source's skylights do.
2. **`infiltration`** keeps `method: fixed_source_reference_natural_ach` and gains:
   - `default_method`;
   - `methods.doe_design_flow`, with `zone_rules` (method, rate, coefficients, schedule
     ID) and `excluded_zones`.
   - The schedule IDs resolve in the building-type folder's schedules, which the export
     inlines.
   - The consumer computes the exterior wall and roof areas from its own geometry.

## Services (inlined in the program and construction exports as today)

- New building-service end uses: `elevator`, `exhaust_fan`, `exterior_lighting`,
  `refrigeration_case`, `refrigeration_rack`.
- Each has absolute or per-area loads, schedules, heat-gain fractions where the source
  gives them, and its evidence.
- They are building services, not program loads. Refrigeration cases name the program
  whose zones receive their case credits.

## Unchanged

- The DOE Ref templates' program IDs, and the shape of every 1.0.0 field.
- The 90.1 templates. The prototype comparison is evidence only (see the
  [equivalence review](reviews/prototype-equivalence-90-1.md)).
