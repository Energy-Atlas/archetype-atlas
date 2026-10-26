# BEMGen handoff: DOE reference reconciliation (atlas release 1.1.0)

For BEMGen's DOE generators (issue #13, branch `feature/doe-geom`). Atlas release
1.1.0 reconciles the DOE Ref templates (`doe-ref-1980-2004`, `doe-ref-pre-1980`)
with the DOE v1.4_7.2 reference models ([ADR 0037](adr/0037-doe-reference-reconciliation.md)).
The [release notes](release-notes-atlas-v1.1.0.md) and
[consumer contracts](consumer-contracts-release-1.1.0.md) are the reference; this note
says what BEMGen reads, and how it lines up with the geometry session's gap note of
2026-10-25.

## Read

```python
from scripts.atlas_exports import Release
release = Release(release='1.1.0')
release.program(program_id, 'filled')                    # Program JSON 5.1.0
release.construction(set_id, '5-a', 'detailed')          # constructions 4.1.0
release.building_services('doe-ref-1980-2004/hospital')  # building services 1.0.0
```

Programs whose content changed have new readable IDs; select by name and template.

## What BEMGen takes from 1.1.0

1. **Windows and skylights: `fenestration` per program.**
   - Each program gives N, E, S and W WWR plus a roof skylight ratio, and BEMGen
     reads them from the program, not from generator parameters. This is the gap
     note's decision on old gaps 6 and 7.
   - `null` means the program's zones have no exterior surface in that direction;
     `0` means wall without glazing.
   - The denominator is the true outdoor wall, as settled for BEMGen T4 and atlas
     input A2: Outdoors walls minus every stretch that coincides with another zone's
     wall on the same plane, whatever its boundary (tolerance 0.01 m).
   - The atlas finds the same stretches the T4 run found: 8 in the secondary school
     (auditorium, bathrooms and main corridor on x = 79 m) and the outpatient
     `Floor 2 Reception Hall`, 26.5 of 28.7 m.
   - The construction set's `fenestration_defaults` holds the 15 whole-building
     values (conditioned, unconditioned and all zone surfaces). A generator can check
     its total glazed area against them.
2. **DOE zone groups become programs (the D-097 relaxation).**
   - The DOE zone is the generators' most detailed level. Where DOE gives a group
     of zones loads of its own, the atlas now has a program:
     - Outpatient `Utility_Outpatient`: `Floor 1 Sterile Storage`,
       `Floor 1 Utility Room`, `Floor 2 Utility`, `Floor 3 Utility`.
     - `ComputerRoom_PrimarySchool`: `Computer_Class_ZN_1_FLR_1`.
     - `Library_PrimarySchool`: `Library_Media_Center_ZN_1_FLR_1`.
     - `Basement_LargeOffice`: `Basement`.
   - Each lists them in `source_spaces`, and the parent (Janitor, Classroom,
     WholeBuilding - Lg Office) lists them in `excluded_source_spaces`. Assign the
     zones by those names.
   - PrimarySchool also gains `Activity_Mixed_PrimarySchool` (ComputerRoom, Gym,
     Library) for Semantic Merge at department level.
3. **Basements (G3).** The Large Office `Basement` program exists so the program set is
   complete. Hospital and Large Hotel already had theirs. BEMGen still does not build
   basements (G3), so a generator that omits the basement omits its program too.
4. **Zone multipliers (kept in the DOE form).** `source_spaces[].multiplier` carries
   the source multiplier. The atlas does not unfold multiplied rooms. The four BEMGen
   changes in the gap note stand: a per-zone multiplier, self-referencing interzone
   surfaces, plates with gaps, and merge rules for multiplied zones.
5. **Holiday calendar: `source_calendar` on every program.**
   - It holds the 10 US holidays as rules ("Last Monday in May") and daylight
     saving, which is recorded, not applied.
   - Resolve the rules for the simulation year and write them as
     `RunPeriodControl:SpecialDays`. The schedules carry `Hol` rules.
6. **Building services: building services 1.0.0, instantiated once.**
   - These are elevators, kitchen and laundry exhaust fans, exterior lights,
     refrigeration cases and refrigeration racks.
   - A service with `beneficiary_program_ids` sits in those programs' zones. Those
     programs list it in `building_service_ids`.
   - `building_level` services (exterior lights, the hospital and hotel elevators
     modelled as exterior equipment, racks) have no zone.
   - Refrigeration cases give their capacity per metre, length, temperatures, fan
     and lighting power, and schedules. Their zone credits go to the beneficiary
     program's zones.
7. **Hot-water zone gains: `water_use_gains` in the program.**
   - The fractions are DOE's: sensible 0.2, latent 0.05.
   - They follow EnergyPlus `WaterUse:Equipment`: sensible = fraction × ṁ × cp ×
     (T_mixed − T_zone); latent = the fraction of the water that can evaporate.
   - `zone_heat_assignment` tells BEMGen where the gains go:
     - `program_zones`: the program's own zones;
     - `beneficiary_program_zones`: the beneficiary programs' zones;
     - `unresolved`: a building-level demand with no zone (hospital, schools, Small
       Office, Supermarket). BEMGen either leaves its gains out or attaches them by
       its own rule, and says which.
8. **Infiltration: two methods in the construction set.**
   - `infiltration.default_method` stays `fixed_source_reference_natural_ach`.
   - `methods.doe_design_flow` gives DOE's zone rules: flow per exterior surface
     area or per exterior wall area at 0.001133 m³/s·m² in both vintages,
     air changes for attics and entries, and an inlined schedule.
   - BEMGen computes each zone's exterior area from its own geometry. The rule
     names the DOE zones it covers.
9. **Humidity setpoints.** The hospital and outpatient programs carry humidifying and
   dehumidifying setpoint schedules (unit %). They apply where BEMGen models
   humidistats; at ideal-loads grade they can be ignored, with that stated.

## Not in 1.1.0

- **Room-level office plans.** The openstudio-standards `*OfficeDetailed` geometry
  is the sourced room layout (gap note decision). Its 35 standards space types need
  atlas programs, which belong to release 1.2.0 (plan stage S10), not 1.1.0.
- **Data-centre zones** in the large office. The DOE Ref vintages have no data-centre
  program; S10 settles the program those zones take.
- **Systems, plant and water heaters** (ideal-loads grade), and the Midrise
  Apartment.

## Tests BEMGen should add

- **Per program and orientation:** generated glazed area over the generated true
  outdoor wall area equals `fenestration` within T4's tolerance. Summed glazed area
  equals the source's within 1%.
- The new programs' zones are assigned by `source_spaces`, and no parent program
  covers them.
- Holiday rules resolve to the same dates as the DOE files for 2006, and `Hol` rules
  are selected on them.
- Building services appear once per building, with their beneficiary zones.
- Water-use gains appear only where `zone_heat_assignment` is not `unresolved`,
  unless BEMGen's own rule is named.
- The DOE design-flow infiltration gives the DOE zone flow at the reference geometry
  (exterior areas from the reference IDF): exact for flow per area, within the
  geometry tolerance otherwise.
