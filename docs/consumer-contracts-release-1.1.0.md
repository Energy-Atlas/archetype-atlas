# Consumer contracts of release 1.1.0

Release 1.1.0 applies the DOE reference reconciliation ([ADR 0037](adr/0037-doe-reference-reconciliation.md))
to the DOE Ref templates, as a delta on release 1.0.0. The exports gain fields; no
existing field changes meaning. `scripts.atlas_exports` produces them with
`Release(release='1.1.0')`, and the schemas are derived from the 1.0.0 majors
(`python -m scripts.atlas_exports --check-schemas`).

| Export | Version | Schema | Previous |
| --- | --- | --- | --- |
| Program JSON | **5.1.0** | `schemas/program-json-v5.1.schema.json` | 5.0.0 |
| Detailed construction set | **4.1.0** | `schemas/construction-json-v4.1.schema.json` | 4.0.0 |
| Unified construction set | **3.1.0** | `schemas/construction-equivalent-v3.1.schema.json` | 3.0.0 |
| Building services | **1.0.0** | `schemas/building-services-v1.schema.json` | new |

`source.release` is `atlas-release-1.1.0`. Every new field is optional. A record
from a template the reconciliation did not touch has none of them.

## Program JSON 5.1.0

1. **`fenestration`**:
   - `{"basis": "program_zone_surfaces", "wwr": {"N", "E", "S", "W"}, "roof", "evidence_id"}`.
   - Each `wwr` value is the window area over the exterior wall area of the program's
     DOE zones in that direction, zone multipliers applied.
   - `roof` is the skylight area over the exterior roof area.
   - `null` means the program has no exterior surface in that direction; `0` means it
     has wall but no window.
2. **`source_calendar`**:
   - `{"holidays": [{"name", "rule"}], "daylight_saving": {"start", "end", "applied": false}, "evidence_id"}`.
   - The rules are as the DOE files write them, for example "Last Monday in May".
   - A consumer that builds a calendar for a year selects `Hol` schedule rules on
     those dates.
   - Daylight saving is recorded, not applied to schedules.
3. **`source_spaces`**, on the programs a DOE zone group gets:
   - Outpatient `Utility`, PrimarySchool `ComputerRoom` and `Library`, Large Office
     `Basement`.
   - Format: `[{"name", "floor_area_m2", "multiplier"}]` for the source spaces the
     program represents.
4. **`excluded_source_spaces`**, on their parent programs: the source spaces of that
   space type that the new programs now represent.
5. **Humidity controls:**
   - `controls.humidifying_setpoint_schedule_id` and
     `controls.dehumidifying_setpoint_schedule_id` (hospital and outpatient).
   - Their schedules are inlined with unit `%` (relative humidity, 0–100).
6. **`alternates`**:
   - Format: `[{"quantity", "value" or "schedule_id", "source_family", "evidence_id", "reason_id"}]`.
   - These are second backed values where two sources disagree beyond the register's
     threshold. The primary value is unchanged.
   - An alternate schedule is inlined in `schedules`.
7. **`water_use_gains`**:
   - Format: `[{"demand_id", "zone_gains": "applied", "sensible_fraction", "latent_fraction", "semantics", "zone_heat_assignment", "evidence_id"}]`.
   - One entry for each hot-water demand of the document (a load or a
     `water_heating[].demand_id`) that carries DOE's gains.
   - The gains follow EnergyPlus `WaterUse:Equipment`:
     - sensible = fraction × mass flow × cp × (mixed − zone air temperature);
     - latent = the fraction of the water that can evaporate.
   - `zone_heat_assignment` says where the gains go: `program_zones`,
     `beneficiary_program_zones` or `unresolved`.
8. **`building_service_ids`**: the IDs of the building services whose DOE objects sit
   in this program's zones. The services themselves are in the building-services
   export.

## Construction sets 4.1.0 (detailed) and 3.1.0 (unified)

1. **`fenestration_defaults`**:
   - `{"conditioned", "unconditioned", "all": {"N", "E", "S", "W", "roof"}, "basis": "whole_building_zone_surfaces", "evidence_id"}`.
   - These are the source model's 15 whole-building ratios. The same nulls and zeros
     apply as in programs.
   - Every climate context carries the same values: the 16 DOE climate files agree.
2. **`infiltration`**:
   - It keeps `method: fixed_source_reference_natural_ach` and gains
     `default_method` (the same value) and `methods.doe_design_flow`.
   - `methods.doe_design_flow` holds `zone_rules` and `excluded_zones`. Each rule has
     a method (flow per exterior area, flow per exterior wall area, or air changes
     per hour), value, unit, coefficients, DOE zone names and schedule.
   - The schedule is inlined in the rule (`source_name`, `rules`), so the document
     stays standalone.
   - The consumer computes exterior surface and wall areas from its own geometry.
3. **Internal mass:**
   - `mass_accounting.additional_mass.entries` gains entries for the source spaces
     where DOE has internal mass and openstudio-standards does not.
   - They use the set's existing mass recipe ("Std Wood 6inch", as DOE) and carry an
     `evidence_id`.

## Building services 1.0.0

`Release(release='1.1.0').building_services('<template>/<building-type>')` returns:

- `{"schema_version": "1.0.0", "kind": "building_services", "release", "template", "building_type", "services", "schedules", "evidence"}`.
- Each service has an `end_use`: `elevator`, `exhaust_fan`, `exterior_lighting`,
  `exterior_equipment`, `refrigeration_case` or `refrigeration_rack`.
- Each service also has:
  - `beneficiary_program_ids`;
  - `ownership: instantiate_once`;
  - `assignment`: `consumer_host_when_applicable` when it sits in program zones,
    otherwise `building_level`;
  - its `load`: the value, basis, unit and schedule ID, heat fractions where the
    source gives them, and the case or rack fields for refrigeration.
- Schedules are inlined in the Program JSON schedule form.
- Hot-water services stay in the program exports, as in 1.0.0.

## Unchanged

- The 90.1 templates and the DOE Ref Midrise Apartment folders.
- The meaning of every 1.0.0 field.
- Program names and upstream source IDs. Records whose content changed have new
  readable IDs (ADR 0036 section 8).
- The prototype comparison of the 90.1 templates is evidence only (see the
  [equivalence review](reviews/prototype-equivalence-90-1.md)).
