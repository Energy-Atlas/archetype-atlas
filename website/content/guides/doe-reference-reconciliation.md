# DOE reference reconciliation

Release 1.1.0 reconciles the DOE Ref templates with the DOE Commercial Reference
Building models (v1.4_7.2, post-1980 and pre-1980, Chicago 5A) under ADR 0037.
Every difference, gap and missing component has one register row with its
decision. This page is generated from
`data/reconciliation/doe-reference-v1.json`; the 90.1 templates are not changed.

## Rules

- The DOE model of the matching vintage is the authority for the DOE Ref
  templates' schedules and loads.
- Where openstudio-standards edited a row after DOE v1.4 (2012-11-13) and
  documented why, the atlas keeps its value and the DOE value becomes an
  alternate.
- An existing-building density is replaced only when it is explicitly wrong: a
  factor of ten or more, a missing value or a contradiction. Otherwise it is
  kept, with the DOE value as an alternate when they differ by more than half.
- Absence in the complete DOE model counts as a source-backed zero.
- Differences within the IDF printing precision (1%) keep the atlas value.

Decisions: **replace** an atlas value with DOE's, **fill** a gap, **add** a
missing component; **keep**, **leave** or **omit** with a reason.

## Decisions by class

| Class | replace | fill | add | keep | leave | omit |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Holiday rules follow the DOE model (`A1-holidays`) | 116 |  |  |  |  |  |
| A DOE schedule with no atlas counterpart (`A3-no-atlas-counterpart`) | 10 |  |  |  |  |  |
| openstudio-standards edited the row after DOE v1.4 (`A3-upstream-edit`) | 42 |  |  | 4 |  |  |
| A vintage variant of the same schedule (`A3-vintage-variant`) | 2 |  |  |  |  |  |
| A program used another schedule than its DOE zones (`A4-assignment`) | 22 |  |  |  |  |  |
| A DOE zone group gets a program of its own (`A4-retag`) |  |  | 6 |  |  |  |
| A program slot differed from its DOE schedule over the year (`A4-slot-assignment`) | 22 |  |  |  |  |  |
| Several DOE schedules serve one program slot (`A4-slot-conflict`) |  |  |  | 6 |  |  |
| A DOE schedule used by a minority of a program's zones (`A4-slot-minority`) |  |  |  |  | 2 |  |
| An existing-building density differs from DOE (`A5-existing-density`) |  |  |  | 40 |  |  |
| A density off by a factor of ten (`A5-explicitly-wrong`) | 2 |  |  |  |  |  |
| A building service folded into a space type (`A5-folded-service`) | 2 |  |  |  |  |  |
| The same value within the IDF printing precision (`A7-rounding`) |  |  |  | 210 |  |  |
| Design-day profiles follow DOE (`A9-design-days`) | 4 |  |  |  |  |  |
| The DOE design-flow infiltration method (`A10-infiltration-method`) |  |  | 30 |  |  |  |
| A DOE infiltration schedule (`A10-infiltration-schedule`) |  |  | 33 |  |  |  |
| Lighting and equipment heat fractions (`A12-heat-fraction`) | 20 |  |  |  |  |  |
| Hot water where the atlas had none (`B1-hot-water`) |  | 72 |  |  |  |  |
| A DOE hot-water flow schedule (`B1-hot-water-schedule`) |  | 10 |  |  |  |  |
| Additional lighting (`B2-additional-lighting`) |  | 230 |  |  | 37 |  |
| Plenum and attic equipment (`B3-unconditioned-equipment`) |  | 9 |  |  |  |  |
| Setpoints where the atlas had none (`B4-setpoints`) |  |  |  | 4 |  |  |
| A density the atlas lacked (`B5-missing-density`) |  | 3 |  |  |  |  |
| A filled density re-based on the DOE value (`B7-filling-sourced`) |  | 226 |  |  |  |  |
| Internal mass (`B8-internal-mass`) |  | 40 |  |  |  |  |
| The source holiday calendar (`C1-holiday-calendar`) |  |  | 2 |  |  |  |
| Daylight-saving time (`C2-daylight-saving`) |  |  | 2 |  |  |  |
| A building service (elevator, exhaust fan, exterior lights) (`C3-building-service`) |  |  | 80 |  |  |  |
| A building-service schedule (`C3-building-service-schedule`) |  |  | 16 |  |  |  |
| Refrigeration cases and racks (`C4-refrigeration`) |  |  | 78 |  |  |  |
| Water-use zone gains (`C5-water-use-gains`) |  |  | 218 |  |  |  |
| Humidity setpoints (`C6-humidity-setpoint`) |  |  | 6 |  |  |  |
| HVAC and plant (`C7-systems`) |  |  |  |  |  | 2 |
| A basement program (`C8-basement-program`) |  |  | 2 |  |  |  |
| Building window ratios (`C10-building-wwr`) |  |  | 30 |  |  |  |
| Plan geometry (`C10-geometry`) |  |  |  |  |  | 2 |
| Program window ratios (`C10-program-wwr`) |  |  | 222 |  |  |  |
| Site, weather and cost data (`C11-site-data`) |  |  |  |  |  | 2 |
| Comfort-only People fields (`C12-comfort-fields`) |  |  |  |  |  | 2 |
| The lights replaceable fraction (`C13-replaceable-fraction`) |  |  |  |  |  | 2 |
| Midrise Apartment (`midrise-apartment`) |  |  |  |  | 2 |  |
| A DOE zone spanning several atlas space types (`mixed-zone`) |  |  |  |  | 2 |  |
| **All** | **242** | **590** | **725** | **264** | **43** | **10** |

Identical schedules are counted, not listed: 148.

## Reasons

| Reason | Meaning |
| --- | --- |
| `R-COMFORT-ONLY` | Comfort-only People fields have no effect on the heat balance. |
| `R-DAYLIGHTING-ONLY` | The lights replaceable fraction only affects daylighting control, which the DOE Ref models do not have. |
| `R-EXISTING-DENSITY` | Existing-building density kept: the atlas value is plausible and not explicitly wrong (ADR 0037 section 1). |
| `R-GEOMETRY-BEMGEN` | Plan geometry, shading and skylight placement belong to BEMGen; the atlas carries only window ratios. |
| `R-HOURLY` | Atlas schedules are hourly; a time inside an hour is stored as its energy-conserving hourly mean. |
| `R-MIXED-ZONE` | The DOE zone spans several atlas space types, so its single value cannot be assigned to one program. |
| `R-NEWER-DOCUMENTED` | The openstudio-standards row was edited after the DOE v1.4 release (2012-11-13) and the edit is documented; the DOE value is kept as an alternate. |
| `R-NO-ATLAS-PROGRAM` | No atlas program represents this DOE zone. |
| `R-NO-LIGHTING-SPLIT` | The DOE model has one lighting object per zone; the additional-lighting share cannot be separated. |
| `R-NOT-COMPARED` | Midrise Apartment was not compared in this reconciliation; it is taken up with the residential work. |
| `R-ROUNDING` | Same source value; the IDF prints SI values to 2-4 significant figures (within 1%). |
| `R-SITE-DATA` | Site, weather and cost data are supplied by the consumer at model creation. |
| `R-SLOT-CONFLICT` | Several DOE schedules serve this slot across the program zones; the program takes the area-dominant one (a tie goes to the first name). |
| `R-SYSTEMS-DEFERRED` | Systems are deferred; BEMGen tests at ideal-loads grade (HVAC, outdoor air, zone mixing, water heaters). |
| `R-UNCONTROLLED` | The DOE model gives these zones no thermostat, so the atlas null setpoint is source-backed. |

## doe-ref-1980-2004 · All building types

| Row | Class | Target | Field | Atlas | DOE | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| rec-00935 | `C1-holiday-calendar` | — | source_calendar.holidays | — | [["New Years Day", "January 1"], ["Veterans Day", "November 11"], ["Christmas", "December… | add |
| rec-00936 | `C2-daylight-saving` | — | source_calendar.daylight_saving | — | RunPeriodControl:DaylightSavingTime, not applied | add |
| rec-00937 | `C7-systems` | — | HVAC, outdoor air, zone mixing, water heaters | — | present in the DOE files | omit (`R-SYSTEMS-DEFERRED`) |
| rec-00941 | `C10-geometry` | — | plan geometry, shading, skylight placement | — | present in the DOE files | omit (`R-GEOMETRY-BEMGEN`) |
| rec-00938 | `C11-site-data` | — | ground temperatures, water mains, sizing, tariffs | — | present in the DOE files | omit (`R-SITE-DATA`) |
| rec-00939 | `C12-comfort-fields` | — | People comfort fields | — | present in the DOE files | omit (`R-COMFORT-ONLY`) |
| rec-00940 | `C13-replaceable-fraction` | — | Lights replaceable fraction | — | present in the DOE files | omit (`R-DAYLIGHTING-ONLY`) |

## doe-ref-1980-2004 · FullServiceRestaurant

| Row | Class | Target | Field | Atlas | DOE | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| rec-00002 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | FullServiceRestaurant Bldg Occ | Schedule:Compact BLDG_OCC_SCH | replace |
| rec-00004 | `A7-rounding` | dining | occupancy | 0.721182 | 0.719424 | keep (`R-ROUNDING`) |
| rec-00005 | `A7-rounding` | dining | lighting | 27.3403 | 27.38 | keep (`R-ROUNDING`) |
| rec-00007 | `A7-rounding` | kitchen | gas_equipment | 1194.8 | 1197.9 | keep (`R-ROUNDING`) |
| rec-00018 | `A10-infiltration-method` | constructions | infiltration.methods.doe_design_flow | fixed_source_reference_natural_ach | [["airchanges/hour", 1.0, "ALWAYS_ON"], ["flow/exteriorarea", 0.001133, "INFIL_HALF_ON_SC… | add |
| rec-00001 | `A10-infiltration-schedule` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (infiltration) | FullServiceRestaurant Bldg Light | Schedule:Compact ALWAYS_ON | add |
| rec-00003 | `A10-infiltration-schedule` | — | schedule (infiltration) | — | Schedule:Compact INFIL_HALF_ON_SCH | add |
| rec-00019 | `B2-additional-lighting` | attic | additional_lighting | — | one lighting object per zone | leave (`R-NO-LIGHTING-SPLIT`) |
| rec-00021 | `B2-additional-lighting` | dining | additional_lighting | — | 0 | fill |
| rec-00022 | `B2-additional-lighting` | kitchen | additional_lighting | — | 0 | fill |
| rec-00020 | `B3-unconditioned-equipment` | attic | electric_equipment | — | no ElectricEquipment in the complete DOE model: 0, constant 0 | fill |
| rec-00006 | `B7-filling-sourced` | dining | gas_equipment | 0 | 0 | fill |
| rec-00009 | `C3-building-service` | services.json#exhaust_fan | exhaust_fan | — | {"end_use": "exhaust_fan", "fractions": {"latent": 0.0, "lost": 1.0, "radiant": 0.0}, "me… | add |
| rec-00010 | `C3-building-service` | services.json#exterior_lighting | exterior_lighting | — | {"control": "AstronomicalClock", "design_level_W": 5081.0, "end_use": "exterior_lighting"… | add |
| rec-00011 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 688.0, "end_use": "refrigeration_case", "fa… | add |
| rec-00012 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 734.0, "end_use": "refrigeration_case", "fa… | add |
| rec-00013 | `C4-refrigeration` | services.json#refrigeration_rack | refrigeration_rack | — | {"condenser_fan_W": 330.0, "cop": 1.5, "end_use": "refrigeration_rack", "heat_rejection":… | add |
| rec-00014 | `C4-refrigeration` | services.json#refrigeration_rack | refrigeration_rack | — | {"condenser_fan_W": 330.0, "cop": 3.0, "end_use": "refrigeration_rack", "heat_rejection":… | add |
| rec-00008 | `C5-water-use-gains` | kitchen | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction": 0.… | add |
| rec-00017 | `C10-building-wwr` | constructions | fenestration_defaults | — | {"all": {"E": 0.2022, "N": 0.0, "S": 0.28, "W": 0.2022, "roof": 0.0}, "conditioned": {"E"… | add |
| rec-00015 | `C10-program-wwr` | dining | fenestration | — | {"E": 0.278, "N": null, "S": 0.28, "W": 0.278, "roof": null} | add |
| rec-00016 | `C10-program-wwr` | kitchen | fenestration | — | {"E": 0.0, "N": 0.0, "S": null, "W": 0.0, "roof": null} | add |

## doe-ref-1980-2004 · Hospital

| Row | Class | Target | Field | Atlas | DOE | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| rec-00027 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | — | Schedule:Compact ADMIN_OCC_SCH | replace |
| rec-00031 | `A3-no-atlas-counterpart` | — | schedule (cooling setpoint) | — | Schedule:Compact Kitchen_CLGSETP_SCH | replace |
| rec-00034 | `A3-no-atlas-counterpart` | — | schedule (heating setpoint) | — | Schedule:Compact Kitchen_HTGSETP_SCH | replace |
| rec-00035 | `A3-no-atlas-counterpart` | — | schedule (cooling setpoint) | — | Schedule:Compact OR_CLGSETP_SCH | replace |
| rec-00023 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (cooling setpoint) | — | Schedule:Compact ADMIN_CLGSETP_SCH | replace |
| rec-00025 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (heating setpoint) | — | Schedule:Compact ADMIN_HTGSETP_SCH | replace |
| rec-00026 | `A4-assignment` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (lighting) | — | Schedule:Compact ADMIN_LIGHT_SCH | replace |
| rec-00036 | `A4-assignment` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (heating setpoint) | — | Schedule:Compact OR_HTGSETP_SCH | replace |
| rec-00037 | `A4-slot-assignment` | er-exam | cooling_setpoint_schedule_id schedule (cooling) | Hospital Critical HtgSetp | Schedule:Compact CRITICAL_CLGSETP_SCH | replace |
| rec-00038 | `A4-slot-assignment` | er-exam | electric_equipment schedule (electric_equipment) | Hospital Admin Equipment | Schedule:Compact CRITICAL_EQUIP_SCH | replace |
| rec-00039 | `A4-slot-assignment` | er-trauma | cooling_setpoint_schedule_id schedule (cooling) | Hospital Critical HtgSetp | Schedule:Compact CRITICAL_CLGSETP_SCH | replace |
| rec-00040 | `A4-slot-assignment` | er-triage | cooling_setpoint_schedule_id schedule (cooling) | Hospital Critical HtgSetp | Schedule:Compact CRITICAL_CLGSETP_SCH | replace |
| rec-00041 | `A4-slot-assignment` | icu-open | cooling_setpoint_schedule_id schedule (cooling) | Hospital Critical HtgSetp | Schedule:Compact CRITICAL_CLGSETP_SCH | replace |
| rec-00042 | `A4-slot-assignment` | icu-pat-rm | cooling_setpoint_schedule_id schedule (cooling) | Hospital Critical HtgSetp | Schedule:Compact CRITICAL_CLGSETP_SCH | replace |
| rec-00050 | `A5-existing-density` | er-nurse-stn | occupancy | 0.0672744 | 0.0143 | keep (`R-EXISTING-DENSITY`) |
| rec-00058 | `A5-existing-density` | icu-open | occupancy | 0.215278 | 0.0538 | keep (`R-EXISTING-DENSITY`) |
| rec-00060 | `A5-existing-density` | icu-nurse-stn | occupancy | 0.0538196 | 0.0143 | keep (`R-EXISTING-DENSITY`) |
| rec-00063 | `A5-existing-density` | icu-pat-rm | electric_equipment | 28.9549 | 32.28 | keep (`R-EXISTING-DENSITY`) |
| rec-00067 | `A5-existing-density` | lobby | occupancy | 0.0768543 | 0.0143 | keep (`R-EXISTING-DENSITY`) |
| rec-00068 | `A5-existing-density` | lobby | lighting | 11.0868 | 15.73 | keep (`R-EXISTING-DENSITY`) |
| rec-00071 | `A5-existing-density` | nurse-stn | occupancy | 0.0768543 | 0.0143 | keep (`R-EXISTING-DENSITY`) |
| rec-00044 | `A7-rounding` | corridor | occupancy | 0.0107639 | 0.0108 | keep (`R-ROUNDING`) |
| rec-00047 | `A7-rounding` | er-exam | occupancy | 0.215278 | 0.214998 | keep (`R-ROUNDING`) |
| rec-00048 | `A7-rounding` | er-exam | electric_equipment | 16.1459 | 16.04 | keep (`R-ROUNDING`) |
| rec-00051 | `A7-rounding` | er-nurse-stn | lighting | 17.8681 | 17.89 | keep (`R-ROUNDING`) |
| rec-00053 | `A7-rounding` | er-trauma | occupancy | 0.215278 | 0.214998 | keep (`R-ROUNDING`) |
| rec-00055 | `A7-rounding` | er-triage | occupancy | 0.215278 | 0.214998 | keep (`R-ROUNDING`) |
| rec-00061 | `A7-rounding` | icu-nurse-stn | lighting | 18.4063 | 18.45 | keep (`R-ROUNDING`) |
| rec-00065 | `A7-rounding` | lab | lighting | 22.6042 | 22.65 | keep (`R-ROUNDING`) |
| rec-00069 | `A7-rounding` | lobby | electric_equipment | 1.07639 | 1.08 | keep (`R-ROUNDING`) |
| rec-00076 | `A7-rounding` | phys-therapy | lighting | 27.0174 | 26.93 | keep (`R-ROUNDING`) |
| rec-00078 | `A7-rounding` | radiology | lighting | 23.7882 | 23.82 | keep (`R-ROUNDING`) |
| rec-00024 | `A9-design-days` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | — | Schedule:Compact ADMIN_EQUIP_SCH | replace |
| rec-00032 | `A9-design-days` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | Hospital Kitchen_Elec_Equip_SCH | Schedule:Compact Kitchen_Elec_Equip_SCH | replace |
| rec-00144 | `A10-infiltration-method` | constructions | infiltration.methods.doe_design_flow | fixed_source_reference_natural_ach | [["flow/exteriorwallarea", 0.001133, "INFIL_QUARTER_ON_SCH"]] | add |
| rec-00030 | `A10-infiltration-schedule` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (infiltration) | Hospital HVACOperationSchd | Schedule:Compact INFIL_QUARTER_ON_SCH | add |
| rec-00080 | `B1-hot-water` | basement | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-00081 | `B1-hot-water` | corridor | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-00082 | `B1-hot-water` | dining | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-00083 | `B1-hot-water` | er-nurse-stn | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-00084 | `B1-hot-water` | icu-nurse-stn | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-00085 | `B1-hot-water` | icu-open | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-00086 | `B1-hot-water` | icu-pat-rm | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-00087 | `B1-hot-water` | lobby | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-00088 | `B1-hot-water` | nurse-stn | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-00089 | `B1-hot-water` | office | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-00028 | `B1-hot-water-schedule` | — | schedule (hot-water flow) | — | Schedule:Compact BLDG_SWH_EXTD_SCH | fill |
| rec-00029 | `B1-hot-water-schedule` | — | schedule (hot-water flow) | — | Schedule:Compact BLDG_SWH_SCH | fill |
| rec-00145 | `B2-additional-lighting` | basement | additional_lighting | — | 0 | fill |
| rec-00146 | `B2-additional-lighting` | corridor | additional_lighting | — | 0 | fill |
| rec-00147 | `B2-additional-lighting` | dining | additional_lighting | — | 0 | fill |
| rec-00148 | `B2-additional-lighting` | er-exam | additional_lighting | — | 0 | fill |
| rec-00149 | `B2-additional-lighting` | er-nurse-stn | additional_lighting | — | 0 | fill |
| rec-00150 | `B2-additional-lighting` | er-trauma | additional_lighting | — | 0 | fill |
| rec-00151 | `B2-additional-lighting` | er-triage | additional_lighting | — | 0 | fill |
| rec-00152 | `B2-additional-lighting` | icu-nurse-stn | additional_lighting | — | 0 | fill |
| rec-00153 | `B2-additional-lighting` | icu-open | additional_lighting | — | 0 | fill |
| rec-00154 | `B2-additional-lighting` | icu-pat-rm | additional_lighting | — | 0 | fill |
| rec-00155 | `B2-additional-lighting` | kitchen | additional_lighting | — | 0 | fill |
| rec-00156 | `B2-additional-lighting` | lab | additional_lighting | — | 0 | fill |
| rec-00157 | `B2-additional-lighting` | lobby | additional_lighting | — | one lighting object per zone | leave (`R-NO-LIGHTING-SPLIT`) |
| rec-00158 | `B2-additional-lighting` | nurse-stn | additional_lighting | — | 0 | fill |
| rec-00159 | `B2-additional-lighting` | office | additional_lighting | — | 0 | fill |
| rec-00160 | `B2-additional-lighting` | or | additional_lighting | — | 0 | fill |
| rec-00161 | `B2-additional-lighting` | pat-room | additional_lighting | — | 0 | fill |
| rec-00162 | `B2-additional-lighting` | phys-therapy | additional_lighting | — | 0 | fill |
| rec-00163 | `B2-additional-lighting` | radiology | additional_lighting | — | 0 | fill |
| rec-00056 | `B5-missing-density` | er-triage | electric_equipment | — | 29.05 | fill |
| rec-00043 | `B7-filling-sourced` | basement | gas_equipment | 0 | 0 | fill |
| rec-00045 | `B7-filling-sourced` | corridor | gas_equipment | 0 | 0 | fill |
| rec-00046 | `B7-filling-sourced` | dining | gas_equipment | 0 | 0 | fill |
| rec-00049 | `B7-filling-sourced` | er-exam | gas_equipment | 0 | 0 | fill |
| rec-00052 | `B7-filling-sourced` | er-nurse-stn | gas_equipment | 0 | 0 | fill |
| rec-00054 | `B7-filling-sourced` | er-trauma | gas_equipment | 0 | 0 | fill |
| rec-00057 | `B7-filling-sourced` | er-triage | gas_equipment | 0 | 0 | fill |
| rec-00059 | `B7-filling-sourced` | icu-open | gas_equipment | 0 | 0 | fill |
| rec-00062 | `B7-filling-sourced` | icu-nurse-stn | gas_equipment | 0 | 0 | fill |
| rec-00064 | `B7-filling-sourced` | icu-pat-rm | gas_equipment | 0 | 0 | fill |
| rec-00066 | `B7-filling-sourced` | lab | gas_equipment | 0 | 0 | fill |
| rec-00070 | `B7-filling-sourced` | lobby | gas_equipment | 0 | 0 | fill |
| rec-00072 | `B7-filling-sourced` | nurse-stn | gas_equipment | 0 | 0 | fill |
| rec-00073 | `B7-filling-sourced` | or | gas_equipment | 0 | 0 | fill |
| rec-00074 | `B7-filling-sourced` | office | gas_equipment | 0 | 0 | fill |
| rec-00075 | `B7-filling-sourced` | pat-room | gas_equipment | 0 | 0 | fill |
| rec-00077 | `B7-filling-sourced` | phys-therapy | gas_equipment | 0 | 0 | fill |
| rec-00079 | `B7-filling-sourced` | radiology | gas_equipment | 0 | 0 | fill |
| rec-00120 | `C3-building-service` | services.json#exhaust_fan | exhaust_fan | — | {"end_use": "exhaust_fan", "fractions": {"latent": 0.0, "lost": 1.0, "radiant": 0.0}, "me… | add |
| rec-00121 | `C3-building-service` | services.json#exterior_lighting | exterior_lighting | — | {"control": "AstronomicalClock", "design_level_W": 20829.0, "end_use": "exterior_lighting… | add |
| rec-00122 | `C3-building-service` | services.json#elevator | elevator | — | {"design_level_W": 162962.637362637, "end_use": "elevator", "fuel": "Electricity", "name"… | add |
| rec-00033 | `C3-building-service-schedule` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | — | Schedule:Compact Kitchen_Exhaust_SCH | add |
| rec-00123 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 734.0, "end_use": "refrigeration_case", "fa… | add |
| rec-00124 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 886.5, "end_use": "refrigeration_case", "fa… | add |
| rec-00125 | `C4-refrigeration` | services.json#refrigeration_rack | refrigeration_rack | — | {"condenser_fan_W": 1000.0, "cop": 1.5, "end_use": "refrigeration_rack", "heat_rejection"… | add |
| rec-00126 | `C4-refrigeration` | services.json#refrigeration_rack | refrigeration_rack | — | {"condenser_fan_W": 1000.0, "cop": 3.0, "end_use": "refrigeration_rack", "heat_rejection"… | add |
| rec-00090 | `C5-water-use-gains` | er-exam | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-00091 | `C5-water-use-gains` | er-exam | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-00092 | `C5-water-use-gains` | er-trauma | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-00093 | `C5-water-use-gains` | er-trauma | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-00094 | `C5-water-use-gains` | er-triage | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-00095 | `C5-water-use-gains` | kitchen | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-00096 | `C5-water-use-gains` | lab | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction": 0.… | add |
| rec-00097 | `C5-water-use-gains` | lab | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction": 0.… | add |
| rec-00098 | `C5-water-use-gains` | or | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction": 0.… | add |
| rec-00099 | `C5-water-use-gains` | or | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction": 0.… | add |
| rec-00100 | `C5-water-use-gains` | or | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction": 0.… | add |
| rec-00101 | `C5-water-use-gains` | or | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction": 0.… | add |
| rec-00102 | `C5-water-use-gains` | pat-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-00103 | `C5-water-use-gains` | pat-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-00104 | `C5-water-use-gains` | pat-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-00105 | `C5-water-use-gains` | pat-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-00106 | `C5-water-use-gains` | pat-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-00107 | `C5-water-use-gains` | pat-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-00108 | `C5-water-use-gains` | pat-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-00109 | `C5-water-use-gains` | pat-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-00110 | `C5-water-use-gains` | pat-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-00111 | `C5-water-use-gains` | pat-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-00112 | `C5-water-use-gains` | pat-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-00113 | `C5-water-use-gains` | pat-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-00114 | `C5-water-use-gains` | pat-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-00115 | `C5-water-use-gains` | pat-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-00116 | `C5-water-use-gains` | pat-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-00117 | `C5-water-use-gains` | pat-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-00118 | `C5-water-use-gains` | phys-therapy | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction": 0.… | add |
| rec-00119 | `C5-water-use-gains` | radiology | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-00127 | `C6-humidity-setpoint` | er-exam | humidity setpoints | — | {"dehumidifying": 60.0, "humidifying": 40.0, "zone": "ER_Exam3_Mult4_Flr_1"} | add |
| rec-00128 | `C6-humidity-setpoint` | or | humidity setpoints | — | {"dehumidifying": 60.0, "humidifying": 40.0, "zone": "OR2_Mult5_Flr_2"} | add |
| rec-00143 | `C10-building-wwr` | constructions | fenestration_defaults | — | {"all": {"E": 0.1358, "N": 0.1244, "S": 0.1488, "W": 0.258, "roof": 0.0}, "conditioned": … | add |
| rec-00129 | `C10-program-wwr` | corridor | fenestration | — | {"E": null, "N": 0.0, "S": 0.0, "W": null, "roof": 0.0} | add |
| rec-00130 | `C10-program-wwr` | dining | fenestration | — | {"E": 0.0, "N": null, "S": 0.2749, "W": null, "roof": 0.0} | add |
| rec-00131 | `C10-program-wwr` | er-exam | fenestration | — | {"E": 0.0, "N": null, "S": 0.0, "W": null, "roof": null} | add |
| rec-00132 | `C10-program-wwr` | er-nurse-stn | fenestration | — | {"E": 0.2751, "N": null, "S": null, "W": null, "roof": null} | add |
| rec-00133 | `C10-program-wwr` | er-trauma | fenestration | — | {"E": 0.0, "N": 0.0, "S": 0.0, "W": null, "roof": null} | add |
| rec-00134 | `C10-program-wwr` | er-triage | fenestration | — | {"E": null, "N": 0.0, "S": null, "W": null, "roof": null} | add |
| rec-00135 | `C10-program-wwr` | icu-open | fenestration | — | {"E": null, "N": null, "S": 0.0, "W": 0.2748, "roof": null} | add |
| rec-00136 | `C10-program-wwr` | icu-pat-rm | fenestration | — | {"E": null, "N": 0.2513, "S": null, "W": 0.2514, "roof": null} | add |
| rec-00137 | `C10-program-wwr` | kitchen | fenestration | — | {"E": 0.0, "N": 0.0, "S": null, "W": null, "roof": 0.0} | add |
| rec-00138 | `C10-program-wwr` | lobby | fenestration | — | {"E": null, "N": 0.0, "S": 0.0, "W": 0.2751, "roof": null} | add |
| rec-00139 | `C10-program-wwr` | nurse-stn | fenestration | — | {"E": null, "N": 0.0, "S": 0.1527, "W": null, "roof": 0.0} | add |
| rec-00140 | `C10-program-wwr` | office | fenestration | — | {"E": null, "N": 0.2356, "S": 0.2379, "W": 0.2514, "roof": 0.0} | add |
| rec-00141 | `C10-program-wwr` | or | fenestration | — | {"E": 0.0, "N": 0.0, "S": null, "W": null, "roof": null} | add |
| rec-00142 | `C10-program-wwr` | pat-room | fenestration | — | {"E": 0.2513, "N": 0.2514, "S": 0.2514, "W": 0.2513, "roof": null} | add |

## doe-ref-1980-2004 · LargeHotel

| Row | Class | Target | Field | Atlas | DOE | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| rec-00164 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | LargeHotel Bldg Equip | Schedule:Compact BLDG_EQUIP_SCH | replace |
| rec-00165 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (lighting) | — | Schedule:Compact BLDG_LIGHT_SCH | replace |
| rec-00166 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | — | Schedule:Compact Common_Occ_Sch | replace |
| rec-00167 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | — | Schedule:Compact GuestRoom_Eqp_Sch | replace |
| rec-00168 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (lighting) | — | Schedule:Compact GuestRoom_Ltg_Sch_Base | replace |
| rec-00169 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | — | Schedule:Compact GuestRoom_Occ_Sch | replace |
| rec-00172 | `A4-slot-assignment` | mechanical | cooling_setpoint_schedule_id schedule (cooling) | LargeHotel ClgSetp | Schedule:Compact Corr_CLGSETP_SCH | replace |
| rec-00173 | `A4-slot-assignment` | mechanical | heating_setpoint_schedule_id schedule (heating) | LargeHotel HtgSetp | Schedule:Compact Corr_HTGSETP_SCH | replace |
| rec-00174 | `A4-slot-assignment` | storage | cooling_setpoint_schedule_id schedule (cooling) | LargeHotel ClgSetp | Schedule:Compact Corr_CLGSETP_SCH | replace |
| rec-00175 | `A4-slot-assignment` | storage | heating_setpoint_schedule_id schedule (heating) | LargeHotel HtgSetp | Schedule:Compact Corr_HTGSETP_SCH | replace |
| rec-00180 | `A5-existing-density` | cafe | lighting | 15.7153 | 27.55 | keep (`R-EXISTING-DENSITY`) |
| rec-00176 | `A7-rounding` | banquet | occupancy | 0.721182 | 0.719424 | keep (`R-ROUNDING`) |
| rec-00179 | `A7-rounding` | cafe | occupancy | 0.721182 | 0.719424 | keep (`R-ROUNDING`) |
| rec-00182 | `A7-rounding` | corridor2 | lighting | 13.132 | 13.11 | keep (`R-ROUNDING`) |
| rec-00184 | `A7-rounding` | corridor | lighting | 13.132 | 13.11 | keep (`R-ROUNDING`) |
| rec-00186 | `A7-rounding` | kitchen | lighting | 16.7917 | 16.83 | keep (`R-ROUNDING`) |
| rec-00187 | `A7-rounding` | laundry | lighting | 12.2709 | 12.23 | keep (`R-ROUNDING`) |
| rec-00188 | `A7-rounding` | lobby | occupancy | 0.322917 | 0.322581 | keep (`R-ROUNDING`) |
| rec-00189 | `A7-rounding` | lobby | lighting | 20.2362 | 20.28 | keep (`R-ROUNDING`) |
| rec-00191 | `A7-rounding` | mechanical | lighting | 8.61113 | 8.6 | keep (`R-ROUNDING`) |
| rec-00195 | `A7-rounding` | guest-room | lighting | 19.0521 | 19.09 | keep (`R-ROUNDING`) |
| rec-00196 | `A7-rounding` | guest-room | electric_equipment | 14.316 | 14.3 | keep (`R-ROUNDING`) |
| rec-00198 | `A7-rounding` | guest-room3 | lighting | 19.0521 | 19.09 | keep (`R-ROUNDING`) |
| rec-00199 | `A7-rounding` | guest-room3 | electric_equipment | 14.316 | 14.3 | keep (`R-ROUNDING`) |
| rec-00201 | `A7-rounding` | guest-room2 | lighting | 19.0521 | 19.09 | keep (`R-ROUNDING`) |
| rec-00202 | `A7-rounding` | guest-room2 | electric_equipment | 14.316 | 14.3 | keep (`R-ROUNDING`) |
| rec-00204 | `A7-rounding` | guest-room4 | lighting | 19.0521 | 19.09 | keep (`R-ROUNDING`) |
| rec-00205 | `A7-rounding` | guest-room4 | electric_equipment | 14.316 | 14.3 | keep (`R-ROUNDING`) |
| rec-00207 | `A7-rounding` | storage | lighting | 3.98265 | 3.96 | keep (`R-ROUNDING`) |
| rec-00245 | `A10-infiltration-method` | constructions | infiltration.methods.doe_design_flow | fixed_source_reference_natural_ach | [["flow/exteriorwallarea", 0.001133, "INFIL_QUARTER_ON_SCH"]] | add |
| rec-00170 | `A10-infiltration-schedule` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (infiltration) | — | Schedule:Compact INFIL_QUARTER_ON_SCH | add |
| rec-00209 | `B1-hot-water` | basement | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-00246 | `B2-additional-lighting` | banquet | additional_lighting | — | 0 | fill |
| rec-00247 | `B2-additional-lighting` | basement | additional_lighting | — | 0 | fill |
| rec-00248 | `B2-additional-lighting` | cafe | additional_lighting | — | one lighting object per zone | leave (`R-NO-LIGHTING-SPLIT`) |
| rec-00249 | `B2-additional-lighting` | corridor | additional_lighting | — | 0 | fill |
| rec-00250 | `B2-additional-lighting` | corridor2 | additional_lighting | — | 0 | fill |
| rec-00251 | `B2-additional-lighting` | guest-room | additional_lighting | — | 0 | fill |
| rec-00252 | `B2-additional-lighting` | guest-room2 | additional_lighting | — | 0 | fill |
| rec-00253 | `B2-additional-lighting` | guest-room3 | additional_lighting | — | 0 | fill |
| rec-00254 | `B2-additional-lighting` | guest-room4 | additional_lighting | — | 0 | fill |
| rec-00255 | `B2-additional-lighting` | kitchen | additional_lighting | — | 0 | fill |
| rec-00256 | `B2-additional-lighting` | laundry | additional_lighting | — | 0 | fill |
| rec-00257 | `B2-additional-lighting` | lobby | additional_lighting | — | 0 | fill |
| rec-00258 | `B2-additional-lighting` | mechanical | additional_lighting | — | 0 | fill |
| rec-00259 | `B2-additional-lighting` | retail | additional_lighting | — | 0 | fill |
| rec-00260 | `B2-additional-lighting` | retail2 | additional_lighting | — | 0 | fill |
| rec-00261 | `B2-additional-lighting` | storage | additional_lighting | — | 0 | fill |
| rec-00177 | `B7-filling-sourced` | banquet | gas_equipment | 0 | 0 | fill |
| rec-00178 | `B7-filling-sourced` | basement | gas_equipment | 0 | 0 | fill |
| rec-00181 | `B7-filling-sourced` | cafe | gas_equipment | 0 | 0 | fill |
| rec-00183 | `B7-filling-sourced` | corridor2 | gas_equipment | 0 | 0 | fill |
| rec-00185 | `B7-filling-sourced` | corridor | gas_equipment | 0 | 0 | fill |
| rec-00190 | `B7-filling-sourced` | lobby | gas_equipment | 0 | 0 | fill |
| rec-00192 | `B7-filling-sourced` | mechanical | gas_equipment | 0 | 0 | fill |
| rec-00193 | `B7-filling-sourced` | retail | gas_equipment | 0 | 0 | fill |
| rec-00194 | `B7-filling-sourced` | retail2 | gas_equipment | 0 | 0 | fill |
| rec-00197 | `B7-filling-sourced` | guest-room | gas_equipment | 0 | 0 | fill |
| rec-00200 | `B7-filling-sourced` | guest-room3 | gas_equipment | 0 | 0 | fill |
| rec-00203 | `B7-filling-sourced` | guest-room2 | gas_equipment | 0 | 0 | fill |
| rec-00206 | `B7-filling-sourced` | guest-room4 | gas_equipment | 0 | 0 | fill |
| rec-00208 | `B7-filling-sourced` | storage | gas_equipment | 0 | 0 | fill |
| rec-00221 | `C3-building-service` | services.json#exhaust_fan | exhaust_fan | — | {"end_use": "exhaust_fan", "fractions": {"latent": 0.0, "lost": 1.0, "radiant": 0.0}, "me… | add |
| rec-00222 | `C3-building-service` | services.json#exhaust_fan | exhaust_fan | — | {"end_use": "exhaust_fan", "fractions": {"latent": 0.0, "lost": 1.0, "radiant": 0.0}, "me… | add |
| rec-00223 | `C3-building-service` | services.json#exterior_lighting | exterior_lighting | — | {"control": "AstronomicalClock", "design_level_W": 27826.0, "end_use": "exterior_lighting… | add |
| rec-00224 | `C3-building-service` | services.json#elevator | elevator | — | {"design_level_W": 122221.978021978, "end_use": "elevator", "fuel": "Electricity", "name"… | add |
| rec-00171 | `C3-building-service-schedule` | — | schedule (plug) | — | Schedule:Compact Kitchen_Exhaust_SCH | add |
| rec-00225 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 367.0, "end_use": "refrigeration_case", "fa… | add |
| rec-00226 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 734.0, "end_use": "refrigeration_case", "fa… | add |
| rec-00227 | `C4-refrigeration` | services.json#refrigeration_rack | refrigeration_rack | — | {"condenser_fan_W": 350.0, "cop": 1.5, "end_use": "refrigeration_rack", "heat_rejection":… | add |
| rec-00228 | `C4-refrigeration` | services.json#refrigeration_rack | refrigeration_rack | — | {"condenser_fan_W": 350.0, "cop": 3.0, "end_use": "refrigeration_rack", "heat_rejection":… | add |
| rec-00210 | `C5-water-use-gains` | kitchen | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "Kitchen_SWH_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction":… | add |
| rec-00211 | `C5-water-use-gains` | laundry | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "LaundryRoom_SWH_Sch", "hot_supply_temperature_C": 60.0, "latent_fracti… | add |
| rec-00212 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00213 | `C5-water-use-gains` | guest-room3 | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00214 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00215 | `C5-water-use-gains` | guest-room3 | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00216 | `C5-water-use-gains` | guest-room2 | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00217 | `C5-water-use-gains` | guest-room4 | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00218 | `C5-water-use-gains` | guest-room2 | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00219 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00220 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00244 | `C10-building-wwr` | constructions | fenestration_defaults | — | {"all": {"E": 0.2448, "N": 0.2604, "S": 0.3667, "W": 0.2448, "roof": 0.0}, "conditioned":… | add |
| rec-00229 | `C10-program-wwr` | banquet | fenestration | — | {"E": null, "N": 0.3302, "S": null, "W": null, "roof": 0.0} | add |
| rec-00230 | `C10-program-wwr` | cafe | fenestration | — | {"E": 0.0, "N": null, "S": 0.5078, "W": null, "roof": 0.0} | add |
| rec-00231 | `C10-program-wwr` | corridor | fenestration | — | {"E": null, "N": 0.3302, "S": 0.3302, "W": null, "roof": 0.0} | add |
| rec-00232 | `C10-program-wwr` | corridor2 | fenestration | — | {"E": null, "N": 0.33, "S": 0.3299, "W": null, "roof": null} | add |
| rec-00233 | `C10-program-wwr` | guest-room | fenestration | — | {"E": 0.3299, "N": 0.33, "S": 0.33, "W": 0.3299, "roof": null} | add |
| rec-00234 | `C10-program-wwr` | guest-room2 | fenestration | — | {"E": null, "N": 0.33, "S": 0.3299, "W": null, "roof": null} | add |
| rec-00235 | `C10-program-wwr` | guest-room3 | fenestration | — | {"E": null, "N": 0.3302, "S": 0.3302, "W": 0.3302, "roof": 0.0} | add |
| rec-00236 | `C10-program-wwr` | guest-room4 | fenestration | — | {"E": null, "N": null, "S": 0.3302, "W": null, "roof": 0.0} | add |
| rec-00237 | `C10-program-wwr` | kitchen | fenestration | — | {"E": 0.3302, "N": 0.2154, "S": 0.3302, "W": null, "roof": 0.0} | add |
| rec-00238 | `C10-program-wwr` | laundry | fenestration | — | {"E": 0.0, "N": 0.0, "S": null, "W": null, "roof": null} | add |
| rec-00239 | `C10-program-wwr` | lobby | fenestration | — | {"E": null, "N": 0.0, "S": 0.5078, "W": 0.0, "roof": 0.0} | add |
| rec-00240 | `C10-program-wwr` | mechanical | fenestration | — | {"E": null, "N": 0.0, "S": null, "W": null, "roof": null} | add |
| rec-00241 | `C10-program-wwr` | retail | fenestration | — | {"E": null, "N": null, "S": 0.5078, "W": 0.0, "roof": 0.0} | add |
| rec-00242 | `C10-program-wwr` | retail2 | fenestration | — | {"E": null, "N": null, "S": null, "W": 0.0, "roof": null} | add |
| rec-00243 | `C10-program-wwr` | storage | fenestration | — | {"E": null, "N": 0.0, "S": null, "W": null, "roof": null} | add |

## doe-ref-1980-2004 · LargeOffice

| Row | Class | Target | Field | Atlas | DOE | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| rec-00262 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | Large Office Bldg Equip | Schedule:Compact BLDG_EQUIP_SCH | replace |
| rec-00263 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (lighting) | Large Office Bldg Light | Schedule:Compact BLDG_LIGHT_SCH | replace |
| rec-00264 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | Large Office Bldg Occ | Schedule:Compact BLDG_OCC_SCH | replace |
| rec-00266 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (cooling setpoint) | Large Office ClgSetp | Schedule:Compact CLGSETP_SCH | replace |
| rec-00267 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (heating setpoint) | Large Office HtgSetp | Schedule:Compact HTGSETP_SCH | replace |
| rec-00277 | `A10-infiltration-method` | constructions | infiltration.methods.doe_design_flow | fixed_source_reference_natural_ach | [["flow/exteriorarea", 0.001133, "INFIL_QUARTER_ON_SCH"]] | add |
| rec-00268 | `A10-infiltration-schedule` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (infiltration) | Large Office Bldg Equip | Schedule:Compact INFIL_QUARTER_ON_SCH | add |
| rec-00265 | `B1-hot-water-schedule` | — | schedule (hot-water flow) | — | Schedule:Compact BLDG_SWH_SCH | fill |
| rec-00279 | `B2-additional-lighting` | whole-building-lg-office | additional_lighting | — | 0 | fill |
| rec-00278 | `B3-unconditioned-equipment` | plenum | electric_equipment | — | no ElectricEquipment in the complete DOE model: 0, constant 0 | fill |
| rec-00269 | `B7-filling-sourced` | whole-building-lg-office | gas_equipment | 0 | 0 | fill |
| rec-00273 | `C3-building-service` | services.json#exterior_lighting | exterior_lighting | — | {"control": "AstronomicalClock", "design_level_W": 61595.0, "end_use": "exterior_lighting… | add |
| rec-00274 | `C3-building-service` | services.json#elevator | elevator | — | {"design_level_W": 244443.956043956, "end_use": "elevator", "fuel": "Electricity", "name"… | add |
| rec-00270 | `C5-water-use-gains` | whole-building-lg-office | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-00271 | `C5-water-use-gains` | whole-building-lg-office | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-00272 | `C5-water-use-gains` | whole-building-lg-office | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-00280 | `C8-basement-program` | whole-building-lg-office | program Basement_LargeOffice | WholeBuilding - Lg Office | {"electric_equipment": 10.76, "gas_equipment": 0.0, "lighting": 16.14, "occupancy": 0.026… | add |
| rec-00276 | `C10-building-wwr` | constructions | fenestration_defaults | — | {"all": {"E": 0.4017, "N": 0.4, "S": 0.4, "W": 0.4017, "roof": 0.0}, "conditioned": {"E":… | add |
| rec-00275 | `C10-program-wwr` | whole-building-lg-office | fenestration | — | {"E": 0.5813, "N": 0.5778, "S": 0.5778, "W": 0.5813, "roof": null} | add |

## doe-ref-1980-2004 · MediumOffice

| Row | Class | Target | Field | Atlas | DOE | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| rec-00282 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | Medium Office Bldg Equip | Schedule:Compact BLDG_EQUIP_SCH | replace |
| rec-00284 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | Medium Office Bldg Occ | Schedule:Compact BLDG_OCC_SCH | replace |
| rec-00286 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (cooling setpoint) | Medium Office ClgSetp | Schedule:Compact CLGSETP_SCH | replace |
| rec-00287 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (heating setpoint) | Medium Office HtgSetp | Schedule:Compact HTGSETP_SCH | replace |
| rec-00283 | `A4-assignment` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (lighting) | Office Bldg Light | Schedule:Compact BLDG_LIGHT_SCH | replace |
| rec-00297 | `A10-infiltration-method` | constructions | infiltration.methods.doe_design_flow | fixed_source_reference_natural_ach | [["flow/exteriorarea", 0.001133, "INFIL_QUARTER_ON_SCH"]] | add |
| rec-00288 | `A10-infiltration-schedule` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (infiltration) | Medium Office Bldg Equip | Schedule:Compact INFIL_QUARTER_ON_SCH | add |
| rec-00285 | `B1-hot-water-schedule` | — | schedule (hot-water flow) | — | Schedule:Compact BLDG_SWH_SCH | fill |
| rec-00299 | `B2-additional-lighting` | whole-building-md-office | additional_lighting | — | 0 | fill |
| rec-00298 | `B3-unconditioned-equipment` | plenum | electric_equipment | — | no ElectricEquipment in the complete DOE model: 0, constant 0 | fill |
| rec-00289 | `B7-filling-sourced` | whole-building-md-office | gas_equipment | 0 | 0 | fill |
| rec-00293 | `C3-building-service` | services.json#elevator | elevator | — | {"end_use": "elevator", "fractions": {"latent": 0.0, "lost": 0.0, "radiant": 0.5}, "metho… | add |
| rec-00294 | `C3-building-service` | services.json#exterior_lighting | exterior_lighting | — | {"control": "AstronomicalClock", "design_level_W": 17809.0, "end_use": "exterior_lighting… | add |
| rec-00281 | `C3-building-service-schedule` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | Medium Office Bldg Occ | Schedule:Compact BLDG_ELEVATORS | add |
| rec-00290 | `C5-water-use-gains` | whole-building-md-office | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-00291 | `C5-water-use-gains` | whole-building-md-office | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-00292 | `C5-water-use-gains` | whole-building-md-office | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-00296 | `C10-building-wwr` | constructions | fenestration_defaults | — | {"all": {"E": 0.3301, "N": 0.3301, "S": 0.3301, "W": 0.3301, "roof": 0.0}, "conditioned":… | add |
| rec-00295 | `C10-program-wwr` | whole-building-md-office | fenestration | — | {"E": 0.4768, "N": 0.4768, "S": 0.4768, "W": 0.4768, "roof": null} | add |

## doe-ref-1980-2004 · MidriseApartment

| Row | Class | Target | Field | Atlas | DOE | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| rec-00942 | `midrise-apartment` | — | all | — | not compared | leave (`R-NOT-COMPARED`) |

## doe-ref-1980-2004 · Outpatient

| Row | Class | Target | Field | Atlas | DOE | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| rec-00302 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (gas) | — | Schedule:Compact BLDG_EQUIP_SCH | replace |
| rec-00303 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | — | Schedule:Compact BLDG_EQUIP_SCH | replace |
| rec-00304 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (lighting) | — | Schedule:Compact BLDG_LIGHT_SCH | replace |
| rec-00305 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | — | Schedule:Compact BLDG_OCC_SCH | replace |
| rec-00310 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | Outpatient Radiology Equip | Schedule:Compact RADIOLOGY_EQUIP_SCH | replace |
| rec-00306 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (hot-water flow) | OutPatientHealthCare BLDG_SWH_SCH_Pre2004 | Schedule:Compact BLDG_SWH_SCH | replace |
| rec-00307 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (cooling setpoint) | — | Schedule:Compact CLGSETP_SCH | replace |
| rec-00308 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (heating setpoint) | — | Schedule:Compact HTGSETP_SCH | replace |
| rec-00300 | `A3-vintage-variant` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | OutPatientHealthCare BLDG_OA_SCH_Pre2004 | Schedule:Compact AHU-1_Fan_Sch | replace |
| rec-00454 | `A4-retag` | janitor | program Utility_Outpatient | Janitor | {"electric_equipment": 1.08, "gas_equipment": 0.0, "lighting": 10.8, "occupancy": 0.0} | add |
| rec-00332 | `A5-existing-density` | toilet | electric_equipment | 7.53474 | 4.31 | keep (`R-EXISTING-DENSITY`) |
| rec-00312 | `A7-rounding` | bio-hazard | lighting | 10.7639 | 10.8 | keep (`R-ROUNDING`) |
| rec-00313 | `A7-rounding` | bio-hazard | electric_equipment | 1.07639 | 1.08 | keep (`R-ROUNDING`) |
| rec-00317 | `A7-rounding` | office | occupancy | 0.0500522 | 0.05 | keep (`R-ROUNDING`) |
| rec-00318 | `A7-rounding` | office | lighting | 19.375 | 19.4 | keep (`R-ROUNDING`) |
| rec-00320 | `A7-rounding` | dressing-room | occupancy | 0.0500522 | 0.05 | keep (`R-ROUNDING`) |
| rec-00321 | `A7-rounding` | dressing-room | lighting | 19.375 | 19.4 | keep (`R-ROUNDING`) |
| rec-00325 | `A7-rounding` | hall | electric_equipment | 4.30556 | 4.31 | keep (`R-ROUNDING`) |
| rec-00327 | `A7-rounding` | it-room | occupancy | 0.0500522 | 0.05 | keep (`R-ROUNDING`) |
| rec-00328 | `A7-rounding` | it-room | lighting | 19.375 | 19.4 | keep (`R-ROUNDING`) |
| rec-00330 | `A7-rounding` | lobby | lighting | 10.7639 | 10.8 | keep (`R-ROUNDING`) |
| rec-00338 | `A7-rounding` | med-gas | lighting | 10.7639 | 10.8 | keep (`R-ROUNDING`) |
| rec-00339 | `A7-rounding` | med-gas | electric_equipment | 1.07639 | 1.08 | keep (`R-ROUNDING`) |
| rec-00342 | `A7-rounding` | janitor | lighting | 10.7639 | 10.8 | keep (`R-ROUNDING`) |
| rec-00344 | `A7-rounding` | pacu | lighting | 24.757 | 24.7 | keep (`R-ROUNDING`) |
| rec-00346 | `A7-rounding` | pre-op | lighting | 15.0695 | 15.1 | keep (`R-ROUNDING`) |
| rec-00348 | `A7-rounding` | procedure-room | lighting | 17.2223 | 17.2 | keep (`R-ROUNDING`) |
| rec-00350 | `A7-rounding` | reception | lighting | 10.7639 | 10.8 | keep (`R-ROUNDING`) |
| rec-00353 | `A7-rounding` | hall-infil | electric_equipment | 4.30556 | 4.31 | keep (`R-ROUNDING`) |
| rec-00355 | `A7-rounding` | conference | lighting | 19.375 | 19.4 | keep (`R-ROUNDING`) |
| rec-00357 | `A7-rounding` | exam | lighting | 17.2223 | 17.2 | keep (`R-ROUNDING`) |
| rec-00359 | `A7-rounding` | xray | electric_equipment | 13.9931 | 14.0206 | keep (`R-ROUNDING`) |
| rec-00361 | `A7-rounding` | physical-therapy | lighting | 17.2223 | 17.2 | keep (`R-ROUNDING`) |
| rec-00421 | `A10-infiltration-method` | constructions | infiltration.methods.doe_design_flow | fixed_source_reference_natural_ach | [["airchanges/hour", 1.0, "INFIL_SCH"], ["flow/exteriorwallarea", 0.001133, "INFIL_SCH"]] | add |
| rec-00309 | `A10-infiltration-schedule` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (infiltration) | OutPatientHealthCare BLDG_OA_SCH_Pre2004 | Schedule:Compact INFIL_SCH | add |
| rec-00365 | `A12-heat-fraction` | janitor | electric_equipment.thermal_effects.radiant | 0.3 | 0.5 | replace |
| rec-00366 | `A12-heat-fraction` | janitor | electric_equipment.thermal_effects.lost | 0.7 | 0 | replace |
| rec-00422 | `B2-additional-lighting` | anesthesia | additional_lighting | — | 0 | fill |
| rec-00423 | `B2-additional-lighting` | bio-hazard | additional_lighting | — | 0 | fill |
| rec-00424 | `B2-additional-lighting` | cafe | additional_lighting | — | 0 | fill |
| rec-00425 | `B2-additional-lighting` | clean-work | additional_lighting | — | 0 | fill |
| rec-00426 | `B2-additional-lighting` | conference | additional_lighting | — | 0 | fill |
| rec-00427 | `B2-additional-lighting` | dressing-room | additional_lighting | — | 0 | fill |
| rec-00428 | `B2-additional-lighting` | elec-mech-room | additional_lighting | — | 0 | fill |
| rec-00429 | `B2-additional-lighting` | elevator-pump-room | additional_lighting | — | 0 | fill |
| rec-00430 | `B2-additional-lighting` | exam | additional_lighting | — | 0 | fill |
| rec-00431 | `B2-additional-lighting` | hall-infil | additional_lighting | — | 0 | fill |
| rec-00432 | `B2-additional-lighting` | hall | additional_lighting | — | 0 | fill |
| rec-00433 | `B2-additional-lighting` | it-room | additional_lighting | — | 0 | fill |
| rec-00434 | `B2-additional-lighting` | janitor | additional_lighting | — | 0 | fill |
| rec-00435 | `B2-additional-lighting` | lobby | additional_lighting | — | 0 | fill |
| rec-00436 | `B2-additional-lighting` | locker-room | additional_lighting | — | 0 | fill |
| rec-00437 | `B2-additional-lighting` | lounge | additional_lighting | — | 0 | fill |
| rec-00438 | `B2-additional-lighting` | med-gas | additional_lighting | — | 0 | fill |
| rec-00439 | `B2-additional-lighting` | mri-control | additional_lighting | — | 0 | fill |
| rec-00440 | `B2-additional-lighting` | mri | additional_lighting | — | 0 | fill |
| rec-00441 | `B2-additional-lighting` | nurse-station | additional_lighting | — | 0 | fill |
| rec-00442 | `B2-additional-lighting` | office | additional_lighting | — | 0 | fill |
| rec-00443 | `B2-additional-lighting` | or | additional_lighting | — | 0 | fill |
| rec-00444 | `B2-additional-lighting` | pacu | additional_lighting | — | 0 | fill |
| rec-00445 | `B2-additional-lighting` | physical-therapy | additional_lighting | — | 0 | fill |
| rec-00446 | `B2-additional-lighting` | pre-op | additional_lighting | — | 0 | fill |
| rec-00447 | `B2-additional-lighting` | procedure-room | additional_lighting | — | 0 | fill |
| rec-00448 | `B2-additional-lighting` | reception | additional_lighting | — | 0 | fill |
| rec-00449 | `B2-additional-lighting` | soil-work | additional_lighting | — | 0 | fill |
| rec-00450 | `B2-additional-lighting` | stair | additional_lighting | — | 0 | fill |
| rec-00451 | `B2-additional-lighting` | toilet | additional_lighting | — | 0 | fill |
| rec-00452 | `B2-additional-lighting` | undeveloped | additional_lighting | — | 0 | fill |
| rec-00453 | `B2-additional-lighting` | xray | additional_lighting | — | 0 | fill |
| rec-00311 | `B7-filling-sourced` | anesthesia | gas_equipment | 0 | 0 | fill |
| rec-00314 | `B7-filling-sourced` | bio-hazard | gas_equipment | 0 | 0 | fill |
| rec-00315 | `B7-filling-sourced` | cafe | gas_equipment | 0 | 0 | fill |
| rec-00316 | `B7-filling-sourced` | clean-work | gas_equipment | 0 | 0 | fill |
| rec-00319 | `B7-filling-sourced` | office | gas_equipment | 0 | 0 | fill |
| rec-00322 | `B7-filling-sourced` | dressing-room | gas_equipment | 0 | 0 | fill |
| rec-00323 | `B7-filling-sourced` | elec-mech-room | gas_equipment | 0 | 0 | fill |
| rec-00324 | `B7-filling-sourced` | elevator-pump-room | gas_equipment | 0 | 0 | fill |
| rec-00326 | `B7-filling-sourced` | hall | gas_equipment | 0 | 0 | fill |
| rec-00329 | `B7-filling-sourced` | it-room | gas_equipment | 0 | 0 | fill |
| rec-00331 | `B7-filling-sourced` | lobby | gas_equipment | 0 | 0 | fill |
| rec-00333 | `B7-filling-sourced` | toilet | gas_equipment | 0 | 0 | fill |
| rec-00334 | `B7-filling-sourced` | locker-room | gas_equipment | 0 | 0 | fill |
| rec-00335 | `B7-filling-sourced` | lounge | gas_equipment | 0 | 0 | fill |
| rec-00336 | `B7-filling-sourced` | mri-control | gas_equipment | 0 | 0 | fill |
| rec-00337 | `B7-filling-sourced` | mri | gas_equipment | 0 | 0 | fill |
| rec-00340 | `B7-filling-sourced` | med-gas | gas_equipment | 0 | 0 | fill |
| rec-00341 | `B7-filling-sourced` | nurse-station | gas_equipment | 0 | 0 | fill |
| rec-00343 | `B7-filling-sourced` | janitor | gas_equipment | 0 | 0 | fill |
| rec-00345 | `B7-filling-sourced` | pacu | gas_equipment | 0 | 0 | fill |
| rec-00347 | `B7-filling-sourced` | pre-op | gas_equipment | 0 | 0 | fill |
| rec-00349 | `B7-filling-sourced` | procedure-room | gas_equipment | 0 | 0 | fill |
| rec-00351 | `B7-filling-sourced` | reception | gas_equipment | 0 | 0 | fill |
| rec-00352 | `B7-filling-sourced` | soil-work | gas_equipment | 0 | 0 | fill |
| rec-00354 | `B7-filling-sourced` | hall-infil | gas_equipment | 0 | 0 | fill |
| rec-00356 | `B7-filling-sourced` | conference | gas_equipment | 0 | 0 | fill |
| rec-00358 | `B7-filling-sourced` | exam | gas_equipment | 0 | 0 | fill |
| rec-00360 | `B7-filling-sourced` | xray | gas_equipment | 0 | 0 | fill |
| rec-00362 | `B7-filling-sourced` | physical-therapy | gas_equipment | 0 | 0 | fill |
| rec-00363 | `B7-filling-sourced` | undeveloped | gas_equipment | 0 | 0 | fill |
| rec-00364 | `B7-filling-sourced` | stair | gas_equipment | 0 | 0 | fill |
| rec-00382 | `C3-building-service` | services.json#elevator | elevator | — | {"end_use": "elevator", "fractions": {"latent": 0.0, "lost": 0.9, "radiant": 0.1}, "metho… | add |
| rec-00383 | `C3-building-service` | services.json#exhaust_fan | exhaust_fan | — | {"end_use": "exhaust_fan", "fractions": {"latent": 0.0, "lost": 1.0, "radiant": 0.0}, "me… | add |
| rec-00384 | `C3-building-service` | services.json#exhaust_fan | exhaust_fan | — | {"end_use": "exhaust_fan", "fractions": {"latent": 0.0, "lost": 1.0, "radiant": 0.0}, "me… | add |
| rec-00385 | `C3-building-service` | services.json#exhaust_fan | exhaust_fan | — | {"end_use": "exhaust_fan", "fractions": {"latent": 0.0, "lost": 1.0, "radiant": 0.0}, "me… | add |
| rec-00386 | `C3-building-service` | services.json#exhaust_fan | exhaust_fan | — | {"end_use": "exhaust_fan", "fractions": {"latent": 0.0, "lost": 1.0, "radiant": 0.0}, "me… | add |
| rec-00387 | `C3-building-service` | services.json#exhaust_fan | exhaust_fan | — | {"end_use": "exhaust_fan", "fractions": {"latent": 0.0, "lost": 1.0, "radiant": 0.0}, "me… | add |
| rec-00388 | `C3-building-service` | services.json#exhaust_fan | exhaust_fan | — | {"end_use": "exhaust_fan", "fractions": {"latent": 0.0, "lost": 1.0, "radiant": 0.0}, "me… | add |
| rec-00389 | `C3-building-service` | services.json#exhaust_fan | exhaust_fan | — | {"end_use": "exhaust_fan", "fractions": {"latent": 0.0, "lost": 1.0, "radiant": 0.0}, "me… | add |
| rec-00390 | `C3-building-service` | services.json#exhaust_fan | exhaust_fan | — | {"end_use": "exhaust_fan", "fractions": {"latent": 0.0, "lost": 1.0, "radiant": 0.0}, "me… | add |
| rec-00391 | `C3-building-service` | services.json#exhaust_fan | exhaust_fan | — | {"end_use": "exhaust_fan", "fractions": {"latent": 0.0, "lost": 1.0, "radiant": 0.0}, "me… | add |
| rec-00392 | `C3-building-service` | services.json#exhaust_fan | exhaust_fan | — | {"end_use": "exhaust_fan", "fractions": {"latent": 0.0, "lost": 1.0, "radiant": 0.0}, "me… | add |
| rec-00393 | `C3-building-service` | services.json#exterior_lighting | exterior_lighting | — | {"control": "AstronomicalClock", "design_level_W": 16951.0, "end_use": "exterior_lighting… | add |
| rec-00301 | `C3-building-service-schedule` | — | schedule (plug) | — | Schedule:Compact BLDG_ELEVATORS | add |
| rec-00367 | `C5-water-use-gains` | anesthesia | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-00368 | `C5-water-use-gains` | mri-control | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-00369 | `C5-water-use-gains` | mri | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-00370 | `C5-water-use-gains` | or | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-00371 | `C5-water-use-gains` | or | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-00372 | `C5-water-use-gains` | or | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-00373 | `C5-water-use-gains` | pacu | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-00374 | `C5-water-use-gains` | pre-op | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-00375 | `C5-water-use-gains` | pre-op | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-00376 | `C5-water-use-gains` | procedure-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-00377 | `C5-water-use-gains` | pacu | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-00378 | `C5-water-use-gains` | pacu | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-00379 | `C5-water-use-gains` | xray | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-00380 | `C5-water-use-gains` | physical-therapy | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-00381 | `C5-water-use-gains` | physical-therapy | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-00394 | `C6-humidity-setpoint` | or | humidity setpoints | — | {"dehumidifying": 60.0, "humidifying": 40.0, "zone": "Floor 1 Operating Room 1"} | add |
| rec-00420 | `C10-building-wwr` | constructions | fenestration_defaults | — | {"all": {"E": 0.1914, "N": 0.2052, "S": 0.2408, "W": 0.1288, "roof": 0.0}, "conditioned":… | add |
| rec-00395 | `C10-program-wwr` | anesthesia | fenestration | — | {"E": null, "N": null, "S": 0.2667, "W": null, "roof": null} | add |
| rec-00396 | `C10-program-wwr` | cafe | fenestration | — | {"E": null, "N": null, "S": 0.48, "W": null, "roof": null} | add |
| rec-00397 | `C10-program-wwr` | conference | fenestration | — | {"E": 0.2, "N": null, "S": 0.2571, "W": null, "roof": null} | add |
| rec-00398 | `C10-program-wwr` | dressing-room | fenestration | — | {"E": null, "N": 0.2778, "S": null, "W": null, "roof": 0.0} | add |
| rec-00399 | `C10-program-wwr` | elec-mech-room | fenestration | — | {"E": 0.2, "N": null, "S": null, "W": null, "roof": 0.0} | add |
| rec-00400 | `C10-program-wwr` | elevator-pump-room | fenestration | — | {"E": null, "N": 0.0, "S": null, "W": 0.0, "roof": null} | add |
| rec-00401 | `C10-program-wwr` | exam | fenestration | — | {"E": 0.256, "N": 0.2826, "S": 0.2492, "W": 0.24, "roof": 0.0} | add |
| rec-00402 | `C10-program-wwr` | hall-infil | fenestration | — | {"E": 0.1067, "N": 0.0, "S": null, "W": 0.0, "roof": 0.0} | add |
| rec-00403 | `C10-program-wwr` | hall | fenestration | — | {"E": null, "N": 0.0, "S": 0.0727, "W": 0.0, "roof": 0.0} | add |
| rec-00404 | `C10-program-wwr` | janitor | fenestration | — | {"E": null, "N": 0.1552, "S": null, "W": 0.0, "roof": 0.0} | add |
| rec-00405 | `C10-program-wwr` | lobby | fenestration | — | {"E": null, "N": null, "S": null, "W": 0.4364, "roof": null} | add |
| rec-00406 | `C10-program-wwr` | locker-room | fenestration | — | {"E": null, "N": 0.2727, "S": null, "W": null, "roof": 0.0} | add |
| rec-00407 | `C10-program-wwr` | lounge | fenestration | — | {"E": null, "N": 0.2609, "S": null, "W": null, "roof": 0.0} | add |
| rec-00408 | `C10-program-wwr` | med-gas | fenestration | — | {"E": 0.0, "N": 0.0, "S": null, "W": null, "roof": 0.0} | add |
| rec-00409 | `C10-program-wwr` | mri-control | fenestration | — | {"E": null, "N": 0.0, "S": null, "W": null, "roof": null} | add |
| rec-00410 | `C10-program-wwr` | office | fenestration | — | {"E": 0.237, "N": 0.27, "S": 0.1143, "W": null, "roof": 0.0} | add |
| rec-00411 | `C10-program-wwr` | or | fenestration | — | {"E": 0.2553, "N": null, "S": 0.24, "W": null, "roof": null} | add |
| rec-00412 | `C10-program-wwr` | pacu | fenestration | — | {"E": null, "N": null, "S": 0.2057, "W": 0.2, "roof": null} | add |
| rec-00413 | `C10-program-wwr` | physical-therapy | fenestration | — | {"E": 0.36, "N": null, "S": 0.3692, "W": null, "roof": 0.0} | add |
| rec-00414 | `C10-program-wwr` | pre-op | fenestration | — | {"E": null, "N": null, "S": null, "W": 0.0, "roof": null} | add |
| rec-00415 | `C10-program-wwr` | procedure-room | fenestration | — | {"E": null, "N": 0.3158, "S": null, "W": null, "roof": null} | add |
| rec-00416 | `C10-program-wwr` | reception | fenestration | — | {"E": null, "N": null, "S": 0.313, "W": 0.45, "roof": null} | add |
| rec-00417 | `C10-program-wwr` | stair | fenestration | — | {"E": 0.0178, "N": 0.1677, "S": 0.0174, "W": 0.0, "roof": 0.0} | add |
| rec-00418 | `C10-program-wwr` | toilet | fenestration | — | {"E": null, "N": 0.25, "S": null, "W": 0.0, "roof": 0.0} | add |
| rec-00419 | `C10-program-wwr` | undeveloped | fenestration | — | {"E": null, "N": null, "S": 0.322, "W": 0.3391, "roof": 0.0} | add |

## doe-ref-1980-2004 · PrimarySchool

| Row | Class | Target | Field | Atlas | DOE | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| rec-00455 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | PrimarySchool Bldg Equip | Schedule:Compact BLDG_EQUIP_SCH | replace |
| rec-00456 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (lighting) | — | Schedule:Compact BLDG_LIGHT_SCH | replace |
| rec-00457 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | PrimarySchool Bldg Occ | Schedule:Compact BLDG_OCC_SCH | replace |
| rec-00459 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | PrimarySchool Gym Occ | Schedule:Compact BLDG_OCC_SCH_Gym | replace |
| rec-00461 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (hot-water flow) | SchoolPrimary BLDG_SWH_SCH | Schedule:Compact BLDG_SWH_SCH | replace |
| rec-00462 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (cooling setpoint) | PrimarySchool ClgSetp | Schedule:Compact CLGSETP_SCH | replace |
| rec-00463 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (heating setpoint) | PrimarySchool HtgSetp | Schedule:Compact HTGSETP_SCH | replace |
| rec-00458 | `A4-assignment` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | PrimarySchool Cafeteria Occ | Schedule:Compact BLDG_OCC_SCH_Cafeteria | replace |
| rec-00460 | `A4-assignment` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | No attributed fixture draw (reporting equivalent) | Schedule:Compact BLDG_OCC_SCH_Offices | replace |
| rec-00465 | `A4-assignment` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | PrimarySchool Kitchen Equip | Schedule:Compact KITCHEN_ELEC_EQUIP_SCH | replace |
| rec-00467 | `A4-assignment` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (gas) | — | Schedule:Compact KITCHEN_GAS_EQUIP_SCH | replace |
| rec-00525 | `A4-retag` | classroom | program ComputerRoom_PrimarySchool | Classroom | {"electric_equipment": 20.0, "gas_equipment": 0.0, "lighting": 21.52, "occupancy": 0.3003} | add |
| rec-00526 | `A4-retag` | classroom | program Library_PrimarySchool | Classroom | {"electric_equipment": 15.0, "gas_equipment": 0.0, "lighting": 22.75, "occupancy": 0.2298… | add |
| rec-00474 | `A5-existing-density` | corridor | lighting | 9.68752 | 21.52 | keep (`R-EXISTING-DENSITY`) |
| rec-00483 | `A5-existing-density` | mechanical | occupancy | 0.0100104 | 0 | keep (`R-EXISTING-DENSITY`) |
| rec-00468 | `A7-rounding` | restroom | electric_equipment | 3.98265 | 4 | keep (`R-ROUNDING`) |
| rec-00470 | `A7-rounding` | cafeteria | occupancy | 0.71763 | 0.719424 | keep (`R-ROUNDING`) |
| rec-00472 | `A7-rounding` | classroom | electric_equipment | 14.9618 | 15 | keep (`R-ROUNDING`) |
| rec-00475 | `A7-rounding` | corridor | electric_equipment | 3.98265 | 4 | keep (`R-ROUNDING`) |
| rec-00477 | `A7-rounding` | gym | lighting | 11.5174 | 11.47 | keep (`R-ROUNDING`) |
| rec-00478 | `A7-rounding` | gym | electric_equipment | 4.9514 | 5 | keep (`R-ROUNDING`) |
| rec-00480 | `A7-rounding` | kitchen | lighting | 17.2223 | 17.2 | keep (`R-ROUNDING`) |
| rec-00481 | `A7-rounding` | lobby | electric_equipment | 3.98265 | 4 | keep (`R-ROUNDING`) |
| rec-00484 | `A7-rounding` | mechanical | lighting | 8.28821 | 8.26 | keep (`R-ROUNDING`) |
| rec-00485 | `A7-rounding` | mechanical | electric_equipment | 3.98265 | 4 | keep (`R-ROUNDING`) |
| rec-00487 | `A7-rounding` | office | occupancy | 0.0500522 | 0.05 | keep (`R-ROUNDING`) |
| rec-00488 | `A7-rounding` | office | electric_equipment | 10.7639 | 10.8 | keep (`R-ROUNDING`) |
| rec-00515 | `A10-infiltration-method` | constructions | infiltration.methods.doe_design_flow | fixed_source_reference_natural_ach | [["flow/exteriorwallarea", 0.001133, "INFIL_SCH"]] | add |
| rec-00464 | `A10-infiltration-schedule` | — | schedule (infiltration) | — | Schedule:Compact INFIL_SCH | add |
| rec-00490 | `B1-hot-water` | cafeteria | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-00491 | `B1-hot-water` | classroom | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-00492 | `B1-hot-water` | corridor | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-00493 | `B1-hot-water` | gym | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-00494 | `B1-hot-water` | lobby | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-00495 | `B1-hot-water` | mechanical | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-00496 | `B1-hot-water` | office | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-00516 | `B2-additional-lighting` | cafeteria | additional_lighting | — | 0 | fill |
| rec-00517 | `B2-additional-lighting` | classroom | additional_lighting | — | one lighting object per zone | leave (`R-NO-LIGHTING-SPLIT`) |
| rec-00518 | `B2-additional-lighting` | corridor | additional_lighting | — | one lighting object per zone | leave (`R-NO-LIGHTING-SPLIT`) |
| rec-00519 | `B2-additional-lighting` | gym | additional_lighting | — | 0 | fill |
| rec-00520 | `B2-additional-lighting` | kitchen | additional_lighting | — | 0 | fill |
| rec-00521 | `B2-additional-lighting` | lobby | additional_lighting | — | 0 | fill |
| rec-00522 | `B2-additional-lighting` | mechanical | additional_lighting | — | 0 | fill |
| rec-00523 | `B2-additional-lighting` | office | additional_lighting | — | 0 | fill |
| rec-00524 | `B2-additional-lighting` | restroom | additional_lighting | — | 0 | fill |
| rec-00469 | `B7-filling-sourced` | restroom | gas_equipment | 0 | 0 | fill |
| rec-00471 | `B7-filling-sourced` | cafeteria | gas_equipment | 0 | 0 | fill |
| rec-00473 | `B7-filling-sourced` | classroom | gas_equipment | 0 | 0 | fill |
| rec-00476 | `B7-filling-sourced` | corridor | gas_equipment | 0 | 0 | fill |
| rec-00479 | `B7-filling-sourced` | gym | gas_equipment | 0 | 0 | fill |
| rec-00482 | `B7-filling-sourced` | lobby | gas_equipment | 0 | 0 | fill |
| rec-00486 | `B7-filling-sourced` | mechanical | gas_equipment | 0 | 0 | fill |
| rec-00489 | `B7-filling-sourced` | office | gas_equipment | 0 | 0 | fill |
| rec-00499 | `C3-building-service` | services.json#exhaust_fan | exhaust_fan | — | {"end_use": "exhaust_fan", "fractions": {"latent": 0.0, "lost": 1.0, "radiant": 0.0}, "me… | add |
| rec-00500 | `C3-building-service` | services.json#exterior_lighting | exterior_lighting | — | {"control": "AstronomicalClock", "design_level_W": 10519.0, "end_use": "exterior_lighting… | add |
| rec-00466 | `C3-building-service-schedule` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | No attributed fixture draw (reporting equivalent) | Schedule:Compact Kitchen_Exhaust_SCH | add |
| rec-00501 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 734.0, "end_use": "refrigeration_case", "fa… | add |
| rec-00502 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 734.0, "end_use": "refrigeration_case", "fa… | add |
| rec-00503 | `C4-refrigeration` | services.json#refrigeration_rack | refrigeration_rack | — | {"condenser_fan_W": 350.0, "cop": 1.5, "end_use": "refrigeration_rack", "heat_rejection":… | add |
| rec-00504 | `C4-refrigeration` | services.json#refrigeration_rack | refrigeration_rack | — | {"condenser_fan_W": 350.0, "cop": 3.0, "end_use": "refrigeration_rack", "heat_rejection":… | add |
| rec-00497 | `C5-water-use-gains` | restroom | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-00498 | `C5-water-use-gains` | kitchen | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction": 0.… | add |
| rec-00514 | `C10-building-wwr` | constructions | fenestration_defaults | — | {"all": {"E": 0.35, "N": 0.35, "S": 0.35, "W": 0.35, "roof": 0.0}, "conditioned": {"E": 0… | add |
| rec-00505 | `C10-program-wwr` | cafeteria | fenestration | — | {"E": 0.35, "N": 0.35, "S": null, "W": null, "roof": 0.0} | add |
| rec-00506 | `C10-program-wwr` | classroom | fenestration | — | {"E": null, "N": 0.35, "S": 0.35, "W": 0.35, "roof": 0.0} | add |
| rec-00507 | `C10-program-wwr` | corridor | fenestration | — | {"E": null, "N": null, "S": null, "W": 0.35, "roof": 0.0} | add |
| rec-00508 | `C10-program-wwr` | gym | fenestration | — | {"E": 0.35, "N": null, "S": null, "W": null, "roof": 0.0} | add |
| rec-00509 | `C10-program-wwr` | kitchen | fenestration | — | {"E": 0.35, "N": null, "S": null, "W": null, "roof": 0.0} | add |
| rec-00510 | `C10-program-wwr` | lobby | fenestration | — | {"E": null, "N": null, "S": 0.35, "W": null, "roof": 0.0} | add |
| rec-00511 | `C10-program-wwr` | mechanical | fenestration | — | {"E": null, "N": null, "S": null, "W": null, "roof": 0.0} | add |
| rec-00512 | `C10-program-wwr` | office | fenestration | — | {"E": 0.35, "N": null, "S": 0.35, "W": null, "roof": 0.0} | add |
| rec-00513 | `C10-program-wwr` | restroom | fenestration | — | {"E": null, "N": null, "S": null, "W": 0.35, "roof": 0.0} | add |

## doe-ref-1980-2004 · QuickServiceRestaurant

| Row | Class | Target | Field | Atlas | DOE | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| rec-00528 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | QuickServiceRestaurant Bldg Occ | Schedule:Compact BLDG_OCC_SCH | replace |
| rec-00529 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (hot-water flow) | QuickServiceRestaurant Bldg Swh | Schedule:Compact BLDG_SWH_SCH | replace |
| rec-00531 | `A5-existing-density` | dining | occupancy | 0.753474 | 0.719424 | keep (`R-EXISTING-DENSITY`) |
| rec-00532 | `A7-rounding` | dining | lighting | 15.5 | 15.45 | keep (`R-ROUNDING`) |
| rec-00534 | `A7-rounding` | kitchen | lighting | 16.6841 | 16.64 | keep (`R-ROUNDING`) |
| rec-00546 | `A10-infiltration-method` | constructions | infiltration.methods.doe_design_flow | fixed_source_reference_natural_ach | [["airchanges/hour", 1.0, "ALWAYS_ON"], ["flow/exteriorarea", 0.001133, "INFIL_HALF_ON_SC… | add |
| rec-00527 | `A10-infiltration-schedule` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (infiltration) | QuickServiceRestaurant Bldg Light | Schedule:Compact ALWAYS_ON | add |
| rec-00530 | `A10-infiltration-schedule` | — | schedule (infiltration) | — | Schedule:Compact INFIL_HALF_ON_SCH | add |
| rec-00535 | `A12-heat-fraction` | dining | lighting.thermal_effects.radiant | 0.37 | 0.7 | replace |
| rec-00547 | `B2-additional-lighting` | attic | additional_lighting | — | one lighting object per zone | leave (`R-NO-LIGHTING-SPLIT`) |
| rec-00549 | `B2-additional-lighting` | dining | additional_lighting | — | 0 | fill |
| rec-00550 | `B2-additional-lighting` | kitchen | additional_lighting | — | 0 | fill |
| rec-00548 | `B3-unconditioned-equipment` | attic | electric_equipment | — | no ElectricEquipment in the complete DOE model: 0, constant 0 | fill |
| rec-00533 | `B7-filling-sourced` | dining | gas_equipment | 0 | 0 | fill |
| rec-00537 | `C3-building-service` | services.json#exhaust_fan | exhaust_fan | — | {"end_use": "exhaust_fan", "fractions": {"latent": 0.0, "lost": 1.0, "radiant": 0.0}, "me… | add |
| rec-00538 | `C3-building-service` | services.json#exterior_lighting | exterior_lighting | — | {"control": "AstronomicalClock", "design_level_W": 2963.0, "end_use": "exterior_lighting"… | add |
| rec-00539 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 688.0, "end_use": "refrigeration_case", "fa… | add |
| rec-00540 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 734.0, "end_use": "refrigeration_case", "fa… | add |
| rec-00541 | `C4-refrigeration` | services.json#refrigeration_rack | refrigeration_rack | — | {"condenser_fan_W": 330.0, "cop": 1.5, "end_use": "refrigeration_rack", "heat_rejection":… | add |
| rec-00542 | `C4-refrigeration` | services.json#refrigeration_rack | refrigeration_rack | — | {"condenser_fan_W": 330.0, "cop": 3.0, "end_use": "refrigeration_rack", "heat_rejection":… | add |
| rec-00536 | `C5-water-use-gains` | kitchen | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction": 0.… | add |
| rec-00545 | `C10-building-wwr` | constructions | fenestration_defaults | — | {"all": {"E": 0.14, "N": 0.0, "S": 0.28, "W": 0.14, "roof": 0.0}, "conditioned": {"E": 0.… | add |
| rec-00543 | `C10-program-wwr` | dining | fenestration | — | {"E": 0.28, "N": null, "S": 0.28, "W": 0.28, "roof": null} | add |
| rec-00544 | `C10-program-wwr` | kitchen | fenestration | — | {"E": 0.0, "N": 0.0, "S": null, "W": 0.0, "roof": null} | add |

## doe-ref-1980-2004 · RetailStandalone

| Row | Class | Target | Field | Atlas | DOE | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| rec-00797 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | — | Schedule:Compact BLDG_EQUIP_SCH | replace |
| rec-00798 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (lighting) | — | Schedule:Compact BLDG_LIGHT_SCH | replace |
| rec-00799 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | — | Schedule:Compact BLDG_OCC_SCH | replace |
| rec-00800 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (cooling setpoint) | Retail ClgSetp | Schedule:Compact CLGSETP_SCH | replace |
| rec-00801 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (heating setpoint) | — | Schedule:Compact HTGSETP_SCH | replace |
| rec-00804 | `A7-rounding` | back-space | occupancy | 0.0358438 | 0.035881 | keep (`R-ROUNDING`) |
| rec-00805 | `A7-rounding` | back-space | lighting | 12.5938 | 12.55 | keep (`R-ROUNDING`) |
| rec-00816 | `A10-infiltration-method` | constructions | infiltration.methods.doe_design_flow | fixed_source_reference_natural_ach | [["airchanges/hour", 1.0, "INFIL_FRONT_SCH"], ["flow/exteriorarea", 0.001133, "INFIL_HALF… | add |
| rec-00802 | `A10-infiltration-schedule` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (infiltration) | Always On | Schedule:Compact INFIL_FRONT_SCH | add |
| rec-00803 | `A10-infiltration-schedule` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (infiltration) | Always On | Schedule:Compact INFIL_HALF_ON_SCH | add |
| rec-00818 | `B2-additional-lighting` | back-space | additional_lighting | — | 0 | fill |
| rec-00819 | `B2-additional-lighting` | entry | additional_lighting | — | 0 | fill |
| rec-00820 | `B2-additional-lighting` | point-of-sale | additional_lighting | — | 0 | fill |
| rec-00821 | `B2-additional-lighting` | retail | additional_lighting | — | 0 | fill |
| rec-00806 | `B7-filling-sourced` | back-space | gas_equipment | 0 | 0 | fill |
| rec-00807 | `B7-filling-sourced` | retail | gas_equipment | 0 | 0 | fill |
| rec-00808 | `B7-filling-sourced` | entry | gas_equipment | 0 | 0 | fill |
| rec-00809 | `B7-filling-sourced` | point-of-sale | gas_equipment | 0 | 0 | fill |
| rec-00817 | `B8-internal-mass` | entry | mass_accounting.additional_mass | — | 2 | fill |
| rec-00810 | `C3-building-service` | services.json#exterior_lighting | exterior_lighting | — | {"control": "AstronomicalClock", "design_level_W": 9995.0, "end_use": "exterior_lighting"… | add |
| rec-00815 | `C10-building-wwr` | constructions | fenestration_defaults | — | {"all": {"E": 0.0, "N": 0.0, "S": 0.2537, "W": 0.0, "roof": 0.0}, "conditioned": {"E": 0.… | add |
| rec-00811 | `C10-program-wwr` | back-space | fenestration | — | {"E": 0.0, "N": 0.0, "S": null, "W": 0.0, "roof": 0.0} | add |
| rec-00812 | `C10-program-wwr` | entry | fenestration | — | {"E": null, "N": null, "S": 0.3211, "W": null, "roof": 0.0} | add |
| rec-00813 | `C10-program-wwr` | point-of-sale | fenestration | — | {"E": null, "N": null, "S": 0.2484, "W": 0.0, "roof": 0.0} | add |
| rec-00814 | `C10-program-wwr` | retail | fenestration | — | {"E": 0.0, "N": null, "S": 0.2484, "W": 0.0, "roof": 0.0} | add |

## doe-ref-1980-2004 · RetailStripmall

| Row | Class | Target | Field | Atlas | DOE | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| rec-00822 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | — | Schedule:Compact BLDG_EQUIP_SCH | replace |
| rec-00823 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (lighting) | — | Schedule:Compact BLDG_LIGHT_SCH | replace |
| rec-00824 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | — | Schedule:Compact BLDG_OCC_SCH | replace |
| rec-00825 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (cooling setpoint) | — | Schedule:Compact CLGSETP_SCH | replace |
| rec-00826 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (heating setpoint) | — | Schedule:Compact HTGSETP_SCH | replace |
| rec-00828 | `A7-rounding` | strip-mall-type-1 | electric_equipment | 4.30556 | 4.3 | keep (`R-ROUNDING`) |
| rec-00830 | `A7-rounding` | strip-mall-type-3 | electric_equipment | 4.30556 | 4.3 | keep (`R-ROUNDING`) |
| rec-00832 | `A7-rounding` | strip-mall-type-2 | electric_equipment | 4.30556 | 4.3 | keep (`R-ROUNDING`) |
| rec-00839 | `A10-infiltration-method` | constructions | infiltration.methods.doe_design_flow | fixed_source_reference_natural_ach | [["flow/exteriorarea", 0.001133, "INFIL_HALF_ON_SCH"]] | add |
| rec-00827 | `A10-infiltration-schedule` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (infiltration) | — | Schedule:Compact INFIL_HALF_ON_SCH | add |
| rec-00840 | `B2-additional-lighting` | strip-mall-type-1 | additional_lighting | — | 0 | fill |
| rec-00841 | `B2-additional-lighting` | strip-mall-type-2 | additional_lighting | — | 0 | fill |
| rec-00842 | `B2-additional-lighting` | strip-mall-type-3 | additional_lighting | — | 0 | fill |
| rec-00829 | `B7-filling-sourced` | strip-mall-type-1 | gas_equipment | 0 | 0 | fill |
| rec-00831 | `B7-filling-sourced` | strip-mall-type-3 | gas_equipment | 0 | 0 | fill |
| rec-00833 | `B7-filling-sourced` | strip-mall-type-2 | gas_equipment | 0 | 0 | fill |
| rec-00834 | `C3-building-service` | services.json#exterior_lighting | exterior_lighting | — | {"control": "AstronomicalClock", "design_level_W": 13499.0, "end_use": "exterior_lighting… | add |
| rec-00838 | `C10-building-wwr` | constructions | fenestration_defaults | — | {"all": {"E": 0.0, "N": 0.0, "S": 0.2624, "W": 0.0, "roof": 0.0}, "conditioned": {"E": 0.… | add |
| rec-00835 | `C10-program-wwr` | strip-mall-type-1 | fenestration | — | {"E": null, "N": 0.0, "S": 0.2628, "W": 0.0, "roof": 0.0} | add |
| rec-00836 | `C10-program-wwr` | strip-mall-type-2 | fenestration | — | {"E": null, "N": 0.0, "S": 0.2623, "W": null, "roof": 0.0} | add |
| rec-00837 | `C10-program-wwr` | strip-mall-type-3 | fenestration | — | {"E": 0.0, "N": 0.0, "S": 0.2623, "W": null, "roof": 0.0} | add |

## doe-ref-1980-2004 · SecondarySchool

| Row | Class | Target | Field | Atlas | DOE | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| rec-00555 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | — | Schedule:Compact BLDG_EQUIP_SCH | replace |
| rec-00556 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (lighting) | — | Schedule:Compact BLDG_LIGHT_SCH | replace |
| rec-00557 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | — | Schedule:Compact BLDG_OCC_SCH | replace |
| rec-00558 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | SecondarySchool Auditorium Occ | Schedule:Compact BLDG_OCC_SCH_Auditorium | replace |
| rec-00561 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | SecondarySchool Gym Occ | Schedule:Compact BLDG_OCC_SCH_Gym | replace |
| rec-00562 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | SecondarySchool Office Occ | Schedule:Compact BLDG_OCC_SCH_Offices | replace |
| rec-00567 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | — | Schedule:Compact KITCHEN_ELEC_EQUIP_SCH | replace |
| rec-00569 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (gas) | — | Schedule:Compact KITCHEN_GAS_EQUIP_SCH | replace |
| rec-00563 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (hot-water flow) | SchoolSecondary BLDG_SWH_SCH | Schedule:Compact BLDG_SWH_SCH | replace |
| rec-00564 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (cooling setpoint) | — | Schedule:Compact CLGSETP_SCH | replace |
| rec-00565 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (heating setpoint) | — | Schedule:Compact HTGSETP_SCH | replace |
| rec-00570 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (hot-water flow) | — | Schedule:Compact Showers_SWH_SCH | replace |
| rec-00559 | `A4-assignment` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | — | Schedule:Compact BLDG_OCC_SCH_Cafeteria | replace |
| rec-00551 | `A4-slot-conflict` | classroom | schedule (occupancy) | — | {"BLDG_OCC_SCH": 5958.0, "BLDG_OCC_SCH_Extend": 954.0} | keep (`R-SLOT-CONFLICT`) |
| rec-00552 | `A4-slot-conflict` | lobby | schedule (cooling) | — | {"CLGSETP_SCH": 210.0, "CLGSETP_SCH_BathCorrMechKitchen": 210.0} | keep (`R-SLOT-CONFLICT`) |
| rec-00553 | `A4-slot-conflict` | lobby | schedule (heating) | — | {"HTGSETP_SCH": 210.0, "HTGSETP_SCH_BathCorrMechKitchen": 210.0} | keep (`R-SLOT-CONFLICT`) |
| rec-00560 | `A4-slot-minority` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | — | Schedule:Compact BLDG_OCC_SCH_Extend | leave (`R-SLOT-CONFLICT`) |
| rec-00574 | `A5-existing-density` | gym-audience | lighting | 11.4097 | 11.81 | keep (`R-EXISTING-DENSITY`) |
| rec-00582 | `A5-existing-density` | classroom | lighting | 21.5278 | 21.0273 | keep (`R-EXISTING-DENSITY`) |
| rec-00585 | `A5-existing-density` | corridor | occupancy | 0.100212 | 0.045714 | keep (`R-EXISTING-DENSITY`) |
| rec-00586 | `A5-existing-density` | corridor | lighting | 9.25696 | 9.64086 | keep (`R-EXISTING-DENSITY`) |
| rec-00592 | `A5-existing-density` | kitchen | occupancy | 0.166625 | 0.15 | keep (`R-EXISTING-DENSITY`) |
| rec-00571 | `A7-rounding` | auditorium | lighting | 12.0556 | 12.08 | keep (`R-ROUNDING`) |
| rec-00572 | `A7-rounding` | auditorium | electric_equipment | 4.9514 | 5 | keep (`R-ROUNDING`) |
| rec-00575 | `A7-rounding` | gym-audience | electric_equipment | 4.9514 | 5 | keep (`R-ROUNDING`) |
| rec-00577 | `A7-rounding` | restroom | lighting | 9.57988 | 9.6 | keep (`R-ROUNDING`) |
| rec-00578 | `A7-rounding` | restroom | electric_equipment | 3.98265 | 4 | keep (`R-ROUNDING`) |
| rec-00580 | `A7-rounding` | cafeteria | lighting | 14.4236 | 14.38 | keep (`R-ROUNDING`) |
| rec-00583 | `A7-rounding` | classroom | electric_equipment | 10.0104 | 10 | keep (`R-ROUNDING`) |
| rec-00587 | `A7-rounding` | corridor | electric_equipment | 3.98265 | 4 | keep (`R-ROUNDING`) |
| rec-00589 | `A7-rounding` | gym | lighting | 11.4097 | 11.38 | keep (`R-ROUNDING`) |
| rec-00590 | `A7-rounding` | gym | electric_equipment | 4.9514 | 5 | keep (`R-ROUNDING`) |
| rec-00593 | `A7-rounding` | kitchen | lighting | 16.7917 | 16.76 | keep (`R-ROUNDING`) |
| rec-00594 | `A7-rounding` | library | lighting | 16.3611 | 16.33 | keep (`R-ROUNDING`) |
| rec-00595 | `A7-rounding` | library | electric_equipment | 10.0104 | 10 | keep (`R-ROUNDING`) |
| rec-00597 | `A7-rounding` | lobby | lighting | 11.9479 | 12 | keep (`R-ROUNDING`) |
| rec-00598 | `A7-rounding` | lobby | electric_equipment | 3.98265 | 4 | keep (`R-ROUNDING`) |
| rec-00600 | `A7-rounding` | mechanical | occupancy | 0.0100104 | 0.01 | keep (`R-ROUNDING`) |
| rec-00601 | `A7-rounding` | mechanical | lighting | 8.07293 | 8.05 | keep (`R-ROUNDING`) |
| rec-00602 | `A7-rounding` | mechanical | electric_equipment | 3.98265 | 4 | keep (`R-ROUNDING`) |
| rec-00604 | `A7-rounding` | office | occupancy | 0.0500522 | 0.05 | keep (`R-ROUNDING`) |
| rec-00605 | `A7-rounding` | office | lighting | 20.1285 | 20.09 | keep (`R-ROUNDING`) |
| rec-00606 | `A7-rounding` | office | electric_equipment | 10.7639 | 10.8 | keep (`R-ROUNDING`) |
| rec-00640 | `A10-infiltration-method` | constructions | infiltration.methods.doe_design_flow | fixed_source_reference_natural_ach | [["airchanges/hour", 0.14, "INFIL_SCH"], ["flow/exteriorwallarea", 0.001133, "INFIL_SCH"]] | add |
| rec-00566 | `A10-infiltration-schedule` | — | schedule (infiltration) | — | Schedule:Compact INFIL_SCH | add |
| rec-00608 | `B1-hot-water` | auditorium | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-00609 | `B1-hot-water` | cafeteria | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-00610 | `B1-hot-water` | classroom | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-00611 | `B1-hot-water` | corridor | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-00612 | `B1-hot-water` | library | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-00613 | `B1-hot-water` | lobby | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-00614 | `B1-hot-water` | mechanical | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-00615 | `B1-hot-water` | office | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-00641 | `B2-additional-lighting` | auditorium | additional_lighting | — | 0 | fill |
| rec-00642 | `B2-additional-lighting` | cafeteria | additional_lighting | — | 0 | fill |
| rec-00643 | `B2-additional-lighting` | classroom | additional_lighting | — | one lighting object per zone | leave (`R-NO-LIGHTING-SPLIT`) |
| rec-00644 | `B2-additional-lighting` | corridor | additional_lighting | — | one lighting object per zone | leave (`R-NO-LIGHTING-SPLIT`) |
| rec-00645 | `B2-additional-lighting` | gym-audience | additional_lighting | — | one lighting object per zone | leave (`R-NO-LIGHTING-SPLIT`) |
| rec-00646 | `B2-additional-lighting` | gym | additional_lighting | — | 0 | fill |
| rec-00647 | `B2-additional-lighting` | kitchen | additional_lighting | — | 0 | fill |
| rec-00648 | `B2-additional-lighting` | library | additional_lighting | — | 0 | fill |
| rec-00649 | `B2-additional-lighting` | lobby | additional_lighting | — | 0 | fill |
| rec-00650 | `B2-additional-lighting` | mechanical | additional_lighting | — | 0 | fill |
| rec-00651 | `B2-additional-lighting` | office | additional_lighting | — | 0 | fill |
| rec-00652 | `B2-additional-lighting` | restroom | additional_lighting | — | 0 | fill |
| rec-00573 | `B7-filling-sourced` | auditorium | gas_equipment | 0 | 0 | fill |
| rec-00576 | `B7-filling-sourced` | gym-audience | gas_equipment | 0 | 0 | fill |
| rec-00579 | `B7-filling-sourced` | restroom | gas_equipment | 0 | 0 | fill |
| rec-00581 | `B7-filling-sourced` | cafeteria | gas_equipment | 0 | 0 | fill |
| rec-00584 | `B7-filling-sourced` | classroom | gas_equipment | 0 | 0 | fill |
| rec-00588 | `B7-filling-sourced` | corridor | gas_equipment | 0 | 0 | fill |
| rec-00591 | `B7-filling-sourced` | gym | gas_equipment | 0 | 0 | fill |
| rec-00596 | `B7-filling-sourced` | library | gas_equipment | 0 | 0 | fill |
| rec-00599 | `B7-filling-sourced` | lobby | gas_equipment | 0 | 0 | fill |
| rec-00603 | `B7-filling-sourced` | mechanical | gas_equipment | 0 | 0 | fill |
| rec-00607 | `B7-filling-sourced` | office | gas_equipment | 0 | 0 | fill |
| rec-00620 | `C3-building-service` | services.json#exhaust_fan | exhaust_fan | — | {"end_use": "exhaust_fan", "fractions": {"latent": 0.0, "lost": 1.0, "radiant": 0.0}, "me… | add |
| rec-00621 | `C3-building-service` | services.json#elevator | elevator | — | {"end_use": "elevator", "fractions": {"latent": 0.0, "lost": 0.0, "radiant": 0.5}, "metho… | add |
| rec-00622 | `C3-building-service` | services.json#exterior_lighting | exterior_lighting | — | {"control": "AstronomicalClock", "design_level_W": 21874.0, "end_use": "exterior_lighting… | add |
| rec-00554 | `C3-building-service-schedule` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | — | Schedule:Compact BLDG_ELEVATORS | add |
| rec-00568 | `C3-building-service-schedule` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | — | Schedule:Compact Kitchen_Exhaust_SCH | add |
| rec-00623 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 734.0, "end_use": "refrigeration_case", "fa… | add |
| rec-00624 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 734.0, "end_use": "refrigeration_case", "fa… | add |
| rec-00625 | `C4-refrigeration` | services.json#refrigeration_rack | refrigeration_rack | — | {"condenser_fan_W": 750.0, "cop": 1.5, "end_use": "refrigeration_rack", "heat_rejection":… | add |
| rec-00626 | `C4-refrigeration` | services.json#refrigeration_rack | refrigeration_rack | — | {"condenser_fan_W": 750.0, "cop": 3.0, "end_use": "refrigeration_rack", "heat_rejection":… | add |
| rec-00616 | `C5-water-use-gains` | restroom | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-00617 | `C5-water-use-gains` | restroom | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-00618 | `C5-water-use-gains` | gym | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "Showers_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction":… | add |
| rec-00619 | `C5-water-use-gains` | kitchen | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction": 0.… | add |
| rec-00639 | `C10-building-wwr` | constructions | fenestration_defaults | — | {"all": {"E": 0.3505, "N": 0.35, "S": 0.35, "W": 0.35, "roof": 0.0}, "conditioned": {"E":… | add |
| rec-00627 | `C10-program-wwr` | auditorium | fenestration | — | {"E": null, "N": 0.35, "S": null, "W": null, "roof": 0.0} | add |
| rec-00628 | `C10-program-wwr` | cafeteria | fenestration | — | {"E": 0.35, "N": 0.35, "S": null, "W": null, "roof": null} | add |
| rec-00629 | `C10-program-wwr` | classroom | fenestration | — | {"E": null, "N": 0.35, "S": 0.35, "W": 0.35, "roof": 0.0} | add |
| rec-00630 | `C10-program-wwr` | corridor | fenestration | — | {"E": null, "N": null, "S": null, "W": 0.35, "roof": 0.0} | add |
| rec-00631 | `C10-program-wwr` | gym-audience | fenestration | — | {"E": 0.35, "N": null, "S": 0.35, "W": null, "roof": 0.0} | add |
| rec-00632 | `C10-program-wwr` | gym | fenestration | — | {"E": null, "N": null, "S": null, "W": null, "roof": 0.0} | add |
| rec-00633 | `C10-program-wwr` | kitchen | fenestration | — | {"E": 0.35, "N": null, "S": null, "W": null, "roof": null} | add |
| rec-00634 | `C10-program-wwr` | library | fenestration | — | {"E": 0.3529, "N": 0.35, "S": null, "W": null, "roof": 0.0} | add |
| rec-00635 | `C10-program-wwr` | lobby | fenestration | — | {"E": null, "N": null, "S": 0.35, "W": null, "roof": 0.0} | add |
| rec-00636 | `C10-program-wwr` | mechanical | fenestration | — | {"E": null, "N": null, "S": null, "W": null, "roof": 0.0} | add |
| rec-00637 | `C10-program-wwr` | office | fenestration | — | {"E": 0.35, "N": null, "S": 0.35, "W": null, "roof": 0.0} | add |
| rec-00638 | `C10-program-wwr` | restroom | fenestration | — | {"E": 0.35, "N": 0.35, "S": null, "W": null, "roof": 0.0} | add |

## doe-ref-1980-2004 · SmallHotel

| Row | Class | Target | Field | Atlas | DOE | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| rec-00653 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | SmallHotel Bldg Equip | Schedule:Compact BLDG_EQUIP_SCH | replace |
| rec-00654 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (lighting) | SmallHotel Bldg Light | Schedule:Compact BLDG_LIGHT_SCH | replace |
| rec-00655 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | SmallHotel Bldg Occ | Schedule:Compact BLDG_OCC_SCH | replace |
| rec-00656 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (lighting) | SmallHotel StaffLounge Light | Schedule:Compact EmployeeLounge_Ltg_Sch | replace |
| rec-00657 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | SmallHotel StaffLounge Occ | Schedule:Compact EmployeeLounge_Occ_Sch | replace |
| rec-00658 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | SmallHotel GuestRoom Equip | Schedule:Compact GuestRoom_Eqp_Sch | replace |
| rec-00660 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | SmallHotel GuestRoom Occ | Schedule:Compact GuestRoom_Occ_Sch | replace |
| rec-00662 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | SmallHotel Office Equip | Schedule:Compact Office_Eqp_Sch | replace |
| rec-00663 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | SmallHotel Office Occ | Schedule:Compact Office_Occ_Sch | replace |
| rec-00659 | `A4-assignment` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (lighting) | — | Schedule:Compact GuestRoom_Ltg_Sch_Base | replace |
| rec-00664 | `A4-slot-assignment` | guest-lounge | electric_equipment schedule (electric_equipment) | SmallHotel Bldg Equip | Schedule:Compact EmployeeLounge_Eqp_Sch | replace |
| rec-00683 | `A5-existing-density` | laundry | occupancy | 0.107639 | 0.112444 | keep (`R-EXISTING-DENSITY`) |
| rec-00666 | `A5-folded-service` | elec-mech-room | electric_equipment | 2133.41 | 0 | replace |
| rec-00671 | `A7-rounding` | exercise | electric_equipment | 11.5174 | 11.5 | keep (`R-ROUNDING`) |
| rec-00673 | `A7-rounding` | guest-lounge | occupancy | 0.322917 | 0.324675 | keep (`R-ROUNDING`) |
| rec-00675 | `A7-rounding` | office | occupancy | 0.0768543 | 0.076666 | keep (`R-ROUNDING`) |
| rec-00676 | `A7-rounding` | office | electric_equipment | 12.9167 | 12.9 | keep (`R-ROUNDING`) |
| rec-00680 | `A7-rounding` | guest-room | occupancy | 0.0427327 | 0.043126 | keep (`R-ROUNDING`) |
| rec-00681 | `A7-rounding` | guest-room | electric_equipment | 14.316 | 14.3 | keep (`R-ROUNDING`) |
| rec-00684 | `A7-rounding` | laundry | electric_equipment | 21.8507 | 21.8754 | keep (`R-ROUNDING`) |
| rec-00686 | `A7-rounding` | meeting | occupancy | 0.538196 | 0.534759 | keep (`R-ROUNDING`) |
| rec-00687 | `A7-rounding` | meeting | electric_equipment | 12.9167 | 12.9 | keep (`R-ROUNDING`) |
| rec-00744 | `A10-infiltration-method` | constructions | infiltration.methods.doe_design_flow | fixed_source_reference_natural_ach | [["airchanges/hour", 1.0, "ALWAYS_ON"], ["flow/exteriorarea", 0.001133, "INFIL_HALF_ON_SC… | add |
| rec-00661 | `A10-infiltration-schedule` | — | schedule (infiltration) | — | Schedule:Compact INFIL_HALF_ON_SCH | add |
| rec-00690 | `A12-heat-fraction` | laundry | electric_equipment.thermal_effects.radiant | 0.5 | 0.2 | replace |
| rec-00762 | `B2-additional-lighting` | attic | additional_lighting | — | one lighting object per zone | leave (`R-NO-LIGHTING-SPLIT`) |
| rec-00764 | `B2-additional-lighting` | corridor | additional_lighting | — | 0 | fill |
| rec-00765 | `B2-additional-lighting` | elec-mech-room | additional_lighting | — | 0 | fill |
| rec-00766 | `B2-additional-lighting` | elevator-core | additional_lighting | — | 0 | fill |
| rec-00767 | `B2-additional-lighting` | exercise | additional_lighting | — | 0 | fill |
| rec-00768 | `B2-additional-lighting` | guest-lounge | additional_lighting | — | 0 | fill |
| rec-00769 | `B2-additional-lighting` | guest-room | additional_lighting | — | 0 | fill |
| rec-00770 | `B2-additional-lighting` | laundry | additional_lighting | — | 0 | fill |
| rec-00771 | `B2-additional-lighting` | mechanical | additional_lighting | — | 0 | fill |
| rec-00772 | `B2-additional-lighting` | meeting | additional_lighting | — | 0 | fill |
| rec-00773 | `B2-additional-lighting` | office | additional_lighting | — | 0 | fill |
| rec-00774 | `B2-additional-lighting` | public-restroom | additional_lighting | — | 0 | fill |
| rec-00775 | `B2-additional-lighting` | staff-lounge | additional_lighting | — | 0 | fill |
| rec-00776 | `B2-additional-lighting` | stair | additional_lighting | — | 0 | fill |
| rec-00777 | `B2-additional-lighting` | storage | additional_lighting | — | 0 | fill |
| rec-00763 | `B3-unconditioned-equipment` | attic | electric_equipment | — | no ElectricEquipment in the complete DOE model: 0, constant 0 | fill |
| rec-00778 | `B4-setpoints` | elec-mech-room | ["heating_setpoint_schedule_id", "cooling_setpoin… | — | no ZoneControl:Thermostat | keep (`R-UNCONTROLLED`) |
| rec-00779 | `B4-setpoints` | elevator-core | ["heating_setpoint_schedule_id", "cooling_setpoin… | — | no ZoneControl:Thermostat | keep (`R-UNCONTROLLED`) |
| rec-00668 | `B5-missing-density` | elevator-core | electric_equipment | — | 0 | fill |
| rec-00665 | `B7-filling-sourced` | corridor | gas_equipment | 0 | 0 | fill |
| rec-00667 | `B7-filling-sourced` | elec-mech-room | gas_equipment | 0 | 0 | fill |
| rec-00669 | `B7-filling-sourced` | elevator-core | gas_equipment | 0 | 0 | fill |
| rec-00670 | `B7-filling-sourced` | staff-lounge | gas_equipment | 0 | 0 | fill |
| rec-00672 | `B7-filling-sourced` | exercise | gas_equipment | 0 | 0 | fill |
| rec-00674 | `B7-filling-sourced` | guest-lounge | gas_equipment | 0 | 0 | fill |
| rec-00677 | `B7-filling-sourced` | office | gas_equipment | 0 | 0 | fill |
| rec-00678 | `B7-filling-sourced` | stair | gas_equipment | 0 | 0 | fill |
| rec-00679 | `B7-filling-sourced` | storage | gas_equipment | 0 | 0 | fill |
| rec-00682 | `B7-filling-sourced` | guest-room | gas_equipment | 0 | 0 | fill |
| rec-00685 | `B7-filling-sourced` | mechanical | gas_equipment | 0 | 0 | fill |
| rec-00688 | `B7-filling-sourced` | meeting | gas_equipment | 0 | 0 | fill |
| rec-00689 | `B7-filling-sourced` | public-restroom | gas_equipment | 0 | 0 | fill |
| rec-00745 | `B8-internal-mass` | elec-mech-room | mass_accounting.additional_mass | — | 2 | fill |
| rec-00746 | `B8-internal-mass` | stair | mass_accounting.additional_mass | — | 2 | fill |
| rec-00747 | `B8-internal-mass` | stair | mass_accounting.additional_mass | — | 2 | fill |
| rec-00748 | `B8-internal-mass` | stair | mass_accounting.additional_mass | — | 2 | fill |
| rec-00749 | `B8-internal-mass` | stair | mass_accounting.additional_mass | — | 2 | fill |
| rec-00750 | `B8-internal-mass` | storage | mass_accounting.additional_mass | — | 2 | fill |
| rec-00751 | `B8-internal-mass` | storage | mass_accounting.additional_mass | — | 2 | fill |
| rec-00752 | `B8-internal-mass` | storage | mass_accounting.additional_mass | — | 2 | fill |
| rec-00753 | `B8-internal-mass` | storage | mass_accounting.additional_mass | — | 2 | fill |
| rec-00754 | `B8-internal-mass` | stair | mass_accounting.additional_mass | — | 2 | fill |
| rec-00755 | `B8-internal-mass` | stair | mass_accounting.additional_mass | — | 2 | fill |
| rec-00756 | `B8-internal-mass` | stair | mass_accounting.additional_mass | — | 2 | fill |
| rec-00757 | `B8-internal-mass` | stair | mass_accounting.additional_mass | — | 2 | fill |
| rec-00758 | `B8-internal-mass` | storage | mass_accounting.additional_mass | — | 2 | fill |
| rec-00759 | `B8-internal-mass` | storage | mass_accounting.additional_mass | — | 2 | fill |
| rec-00760 | `B8-internal-mass` | storage | mass_accounting.additional_mass | — | 2 | fill |
| rec-00761 | `B8-internal-mass` | storage | mass_accounting.additional_mass | — | 2 | fill |
| rec-00727 | `C3-building-service` | services.json#elevator | elevator | — | {"end_use": "elevator", "fractions": {"latent": 0.0, "lost": 0.0, "radiant": 0.5}, "metho… | add |
| rec-00728 | `C3-building-service` | services.json#exterior_lighting | exterior_lighting | — | {"control": "AstronomicalClock", "design_level_W": 16715.0, "end_use": "exterior_lighting… | add |
| rec-00691 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00692 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00693 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00694 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00695 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00696 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00697 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00698 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00699 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00700 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00701 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00702 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00703 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00704 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00705 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00706 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00707 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00708 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00709 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00710 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00711 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00712 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00713 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00714 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00715 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00716 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00717 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00718 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00719 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00720 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00721 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00722 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00723 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00724 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00725 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-00726 | `C5-water-use-gains` | laundry | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "LaundryRoom_SWH_Sch", "hot_supply_temperature_C": 60.0, "latent_fracti… | add |
| rec-00743 | `C10-building-wwr` | constructions | fenestration_defaults | — | {"all": {"E": 0.0313, "N": 0.1139, "S": 0.1524, "W": 0.0395, "roof": 0.0}, "conditioned":… | add |
| rec-00729 | `C10-program-wwr` | corridor | fenestration | — | {"E": 0.3125, "N": 0.0, "S": 0.2631, "W": 0.3954, "roof": null} | add |
| rec-00730 | `C10-program-wwr` | elec-mech-room | fenestration | — | {"E": null, "N": 0.0, "S": null, "W": null, "roof": null} | add |
| rec-00731 | `C10-program-wwr` | elevator-core | fenestration | — | {"E": null, "N": 0.0, "S": null, "W": null, "roof": null} | add |
| rec-00732 | `C10-program-wwr` | exercise | fenestration | — | {"E": null, "N": 0.1239, "S": null, "W": null, "roof": null} | add |
| rec-00733 | `C10-program-wwr` | guest-lounge | fenestration | — | {"E": null, "N": null, "S": 0.2232, "W": 0.0, "roof": null} | add |
| rec-00734 | `C10-program-wwr` | guest-room | fenestration | — | {"E": null, "N": 0.1495, "S": 0.1578, "W": 0.0, "roof": null} | add |
| rec-00735 | `C10-program-wwr` | laundry | fenestration | — | {"E": null, "N": 0.1238, "S": null, "W": null, "roof": null} | add |
| rec-00736 | `C10-program-wwr` | mechanical | fenestration | — | {"E": null, "N": null, "S": 0.0, "W": null, "roof": null} | add |
| rec-00737 | `C10-program-wwr` | meeting | fenestration | — | {"E": null, "N": null, "S": 0.1509, "W": null, "roof": null} | add |
| rec-00738 | `C10-program-wwr` | office | fenestration | — | {"E": null, "N": 0.1238, "S": null, "W": null, "roof": null} | add |
| rec-00739 | `C10-program-wwr` | public-restroom | fenestration | — | {"E": null, "N": null, "S": 0.0, "W": null, "roof": null} | add |
| rec-00740 | `C10-program-wwr` | staff-lounge | fenestration | — | {"E": null, "N": 0.1238, "S": null, "W": null, "roof": null} | add |
| rec-00741 | `C10-program-wwr` | stair | fenestration | — | {"E": 0.0, "N": 0.0, "S": null, "W": 0.0, "roof": null} | add |
| rec-00742 | `C10-program-wwr` | storage | fenestration | — | {"E": 0.0, "N": 0.0, "S": 0.0, "W": null, "roof": null} | add |

## doe-ref-1980-2004 · SmallOffice

| Row | Class | Target | Field | Atlas | DOE | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| rec-00781 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | Small Office Bldg Equip | Schedule:Compact BLDG_EQUIP_SCH | replace |
| rec-00782 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (lighting) | Office Bldg Light | Schedule:Compact BLDG_LIGHT_SCH | replace |
| rec-00783 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | Small Office Bldg Occ | Schedule:Compact BLDG_OCC_SCH | replace |
| rec-00785 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (cooling setpoint) | Small Office ClgSetp | Schedule:Compact CLGSETP_SCH | replace |
| rec-00786 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (heating setpoint) | Small Office HtgSetp | Schedule:Compact HTGSETP_SCH | replace |
| rec-00793 | `A10-infiltration-method` | constructions | infiltration.methods.doe_design_flow | fixed_source_reference_natural_ach | [["airchanges/hour", 0.36, "INFIL_QUARTER_ON_SCH"], ["airchanges/hour", 1.0, "ALWAYS_ON"]… | add |
| rec-00780 | `A10-infiltration-schedule` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (infiltration) | Office Bldg Light | Schedule:Compact ALWAYS_ON | add |
| rec-00787 | `A10-infiltration-schedule` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (infiltration) | Office Bldg Light | Schedule:Compact INFIL_QUARTER_ON_SCH | add |
| rec-00784 | `B1-hot-water-schedule` | — | schedule (hot-water flow) | — | Schedule:Compact BLDG_SWH_SCH | fill |
| rec-00794 | `B2-additional-lighting` | attic | additional_lighting | — | one lighting object per zone | leave (`R-NO-LIGHTING-SPLIT`) |
| rec-00796 | `B2-additional-lighting` | whole-building-sm-office | additional_lighting | — | 0 | fill |
| rec-00795 | `B3-unconditioned-equipment` | attic | electric_equipment | — | no ElectricEquipment in the complete DOE model: 0, constant 0 | fill |
| rec-00788 | `B7-filling-sourced` | whole-building-sm-office | gas_equipment | 0 | 0 | fill |
| rec-00790 | `C3-building-service` | services.json#exterior_lighting | exterior_lighting | — | {"control": "AstronomicalClock", "design_level_W": 2766.0, "end_use": "exterior_lighting"… | add |
| rec-00789 | `C5-water-use-gains` | whole-building-sm-office | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-00792 | `C10-building-wwr` | constructions | fenestration_defaults | — | {"all": {"E": 0.1981, "N": 0.1981, "S": 0.2444, "W": 0.1981, "roof": 0.0}, "conditioned":… | add |
| rec-00791 | `C10-program-wwr` | whole-building-sm-office | fenestration | — | {"E": 0.1981, "N": 0.1981, "S": 0.2444, "W": 0.1981, "roof": null} | add |

## doe-ref-1980-2004 · SuperMarket

| Row | Class | Target | Field | Atlas | DOE | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| rec-00843 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (gas) | — | Schedule:Compact BLDG_EQUIP_SCH | replace |
| rec-00844 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | — | Schedule:Compact BLDG_EQUIP_SCH | replace |
| rec-00847 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (hot-water flow) | SuperMarket Bldg Swh | Schedule:Compact BLDG_SWH_SCH | replace |
| rec-00845 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (lighting) | — | Schedule:Compact BLDG_LIGHT_SCH | replace |
| rec-00846 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | — | Schedule:Compact BLDG_OCC_SCH | replace |
| rec-00857 | `A5-explicitly-wrong` | produce | electric_equipment | 0.538196 | 5.38 | replace |
| rec-00851 | `A7-rounding` | deli | gas_equipment | 26.9087 | 26.9359 | keep (`R-ROUNDING`) |
| rec-00852 | `A7-rounding` | dry-storage | occupancy | 0.0359515 | 0.035881 | keep (`R-ROUNDING`) |
| rec-00853 | `A7-rounding` | dry-storage | lighting | 11.8403 | 11.9 | keep (`R-ROUNDING`) |
| rec-00855 | `A7-rounding` | office | lighting | 21.3125 | 21.36 | keep (`R-ROUNDING`) |
| rec-00900 | `A10-infiltration-method` | constructions | infiltration.methods.doe_design_flow | fixed_source_reference_natural_ach | [["flow/exteriorarea", 0.001133, "INFIL_HALF_ON_SCH"]] | add |
| rec-00849 | `A10-infiltration-schedule` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (infiltration) | — | Schedule:Compact INFIL_HALF_ON_SCH | add |
| rec-00859 | `A12-heat-fraction` | bakery | gas_equipment.thermal_effects.radiant | 0.2 | 0.5 | replace |
| rec-00860 | `A12-heat-fraction` | bakery | gas_equipment.thermal_effects.latent | 0.1 | 0 | replace |
| rec-00861 | `A12-heat-fraction` | bakery | gas_equipment.thermal_effects.lost | 0.7 | 0 | replace |
| rec-00862 | `A12-heat-fraction` | deli | gas_equipment.thermal_effects.radiant | 0.2 | 0.5 | replace |
| rec-00863 | `A12-heat-fraction` | deli | gas_equipment.thermal_effects.latent | 0.1 | 0 | replace |
| rec-00864 | `A12-heat-fraction` | deli | gas_equipment.thermal_effects.lost | 0.7 | 0 | replace |
| rec-00865 | `B1-hot-water` | corridor | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-00866 | `B1-hot-water` | dining | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-00867 | `B1-hot-water` | dry-storage | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-00868 | `B1-hot-water` | elec-mech-room | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-00869 | `B1-hot-water` | meeting | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-00870 | `B1-hot-water` | office | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-00871 | `B1-hot-water` | produce | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-00872 | `B1-hot-water` | restroom | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-00873 | `B1-hot-water` | sales | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-00874 | `B1-hot-water` | vestibule | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-00902 | `B2-additional-lighting` | bakery | additional_lighting | — | 0 | fill |
| rec-00903 | `B2-additional-lighting` | corridor | additional_lighting | — | one lighting object per zone | leave (`R-NO-LIGHTING-SPLIT`) |
| rec-00904 | `B2-additional-lighting` | deli | additional_lighting | — | 0 | fill |
| rec-00905 | `B2-additional-lighting` | dining | additional_lighting | — | one lighting object per zone | leave (`R-NO-LIGHTING-SPLIT`) |
| rec-00906 | `B2-additional-lighting` | dry-storage | additional_lighting | — | 0 | fill |
| rec-00907 | `B2-additional-lighting` | elec-mech-room | additional_lighting | — | one lighting object per zone | leave (`R-NO-LIGHTING-SPLIT`) |
| rec-00908 | `B2-additional-lighting` | meeting | additional_lighting | — | one lighting object per zone | leave (`R-NO-LIGHTING-SPLIT`) |
| rec-00909 | `B2-additional-lighting` | office | additional_lighting | — | 0 | fill |
| rec-00910 | `B2-additional-lighting` | produce | additional_lighting | — | 0 | fill |
| rec-00911 | `B2-additional-lighting` | restroom | additional_lighting | — | one lighting object per zone | leave (`R-NO-LIGHTING-SPLIT`) |
| rec-00912 | `B2-additional-lighting` | sales | additional_lighting | — | one lighting object per zone | leave (`R-NO-LIGHTING-SPLIT`) |
| rec-00913 | `B2-additional-lighting` | vestibule | additional_lighting | — | one lighting object per zone | leave (`R-NO-LIGHTING-SPLIT`) |
| rec-00854 | `B7-filling-sourced` | dry-storage | gas_equipment | 0 | 0 | fill |
| rec-00856 | `B7-filling-sourced` | office | gas_equipment | 0 | 0 | fill |
| rec-00858 | `B7-filling-sourced` | produce | gas_equipment | 0 | 0 | fill |
| rec-00901 | `B8-internal-mass` | corridor, dining, elec-mech-room, meeting, restroom, sales,… | mass_accounting.additional_mass | — | 2 | fill |
| rec-00877 | `C3-building-service` | services.json#exhaust_fan | exhaust_fan | — | {"end_use": "exhaust_fan", "fractions": {"latent": 0.0, "lost": 1.0, "radiant": 0.0}, "me… | add |
| rec-00878 | `C3-building-service` | services.json#exterior_lighting | exterior_lighting | — | {"control": "AstronomicalClock", "design_level_W": 16402.0, "end_use": "exterior_lighting… | add |
| rec-00848 | `C3-building-service-schedule` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | — | Schedule:Compact Deli_Exhaust_SCH | add |
| rec-00879 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 461.52, "end_use": "refrigeration_case", "f… | add |
| rec-00880 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 1442.25, "end_use": "refrigeration_case", "… | add |
| rec-00881 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 461.52, "end_use": "refrigeration_case", "f… | add |
| rec-00882 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 1442.25, "end_use": "refrigeration_case", "… | add |
| rec-00883 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 1442.25, "end_use": "refrigeration_case", "… | add |
| rec-00884 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 1442.25, "end_use": "refrigeration_case", "… | add |
| rec-00885 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 538.44, "end_use": "refrigeration_case", "f… | add |
| rec-00886 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 528.83, "end_use": "refrigeration_case", "f… | add |
| rec-00887 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 461.52, "end_use": "refrigeration_case", "f… | add |
| rec-00888 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 461.52, "end_use": "refrigeration_case", "f… | add |
| rec-00889 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 615.36, "end_use": "refrigeration_case", "f… | add |
| rec-00890 | `C4-refrigeration` | services.json#refrigeration_rack | refrigeration_rack | — | {"condenser_fan_W": 4500.0, "cop": 2.5, "end_use": "refrigeration_rack", "heat_rejection"… | add |
| rec-00891 | `C4-refrigeration` | services.json#refrigeration_rack | refrigeration_rack | — | {"condenser_fan_W": 4500.0, "cop": 1.3, "end_use": "refrigeration_rack", "heat_rejection"… | add |
| rec-00892 | `C4-refrigeration` | services.json#refrigeration_rack | refrigeration_rack | — | {"condenser_fan_W": 4500.0, "cop": 2.5, "end_use": "refrigeration_rack", "heat_rejection"… | add |
| rec-00893 | `C4-refrigeration` | services.json#refrigeration_rack | refrigeration_rack | — | {"condenser_fan_W": 4500.0, "cop": 1.3, "end_use": "refrigeration_rack", "heat_rejection"… | add |
| rec-00875 | `C5-water-use-gains` | bakery | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction": 0.… | add |
| rec-00876 | `C5-water-use-gains` | deli | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction": 0.… | add |
| rec-00899 | `C10-building-wwr` | constructions | fenestration_defaults | — | {"all": {"E": 0.0, "N": 0.0, "S": 0.3619, "W": 0.0, "roof": 0.0}, "conditioned": {"E": 0.… | add |
| rec-00894 | `C10-program-wwr` | bakery | fenestration | — | {"E": 0.0, "N": null, "S": 0.0, "W": null, "roof": 0.0} | add |
| rec-00895 | `C10-program-wwr` | deli | fenestration | — | {"E": 0.0, "N": null, "S": null, "W": null, "roof": 0.0} | add |
| rec-00896 | `C10-program-wwr` | dry-storage | fenestration | — | {"E": null, "N": 0.0, "S": null, "W": 0.0, "roof": 0.0} | add |
| rec-00897 | `C10-program-wwr` | office | fenestration | — | {"E": 0.0, "N": 0.0, "S": null, "W": null, "roof": 0.0} | add |
| rec-00898 | `C10-program-wwr` | produce | fenestration | — | {"E": null, "N": null, "S": 0.0, "W": 0.0, "roof": 0.0} | add |
| rec-00850 | `mixed-zone` | — | loads | — | Sales | leave (`R-MIXED-ZONE`) |

## doe-ref-1980-2004 · Warehouse

| Row | Class | Target | Field | Atlas | DOE | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| rec-00917 | `A3-no-atlas-counterpart` | — | schedule (cooling setpoint) | — | Schedule:Compact CLGSETP_FineStorage_SCH | replace |
| rec-00920 | `A3-no-atlas-counterpart` | — | schedule (heating setpoint) | — | Schedule:Compact HTGSETP_SCH | replace |
| rec-00914 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | — | Schedule:Compact BLDG_EQUIP_SCH | replace |
| rec-00915 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (lighting) | — | Schedule:Compact BLDG_LIGHT_SCH | replace |
| rec-00916 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | Warehouse Bldg Occ | Schedule:Compact BLDG_OCC_SCH | keep (`R-NEWER-DOCUMENTED`) |
| rec-00918 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (cooling setpoint) | Warehouse Cooling Setpoint | Schedule:Compact CLGSETP_SCH | replace |
| rec-00921 | `A3-upstream-edit` | office | occupancy schedule (occupancy) | Warehouse Bldg Occ | Schedule:Compact BLDG_OCC_SCH | keep (`R-NEWER-DOCUMENTED`) |
| rec-00919 | `A4-assignment` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (heating setpoint) | Warehouse HtgSetp | Schedule:Compact HTGSETP_FineStorage_SCH | replace |
| rec-00930 | `A10-infiltration-method` | constructions | infiltration.methods.doe_design_flow | fixed_source_reference_natural_ach | [["flow/exteriorarea", 0.001133, "ALWAYS_ON"]] | add |
| rec-00932 | `B2-additional-lighting` | bulk | additional_lighting | — | 0 | fill |
| rec-00933 | `B2-additional-lighting` | fine | additional_lighting | — | 0 | fill |
| rec-00934 | `B2-additional-lighting` | office | additional_lighting | — | 0 | fill |
| rec-00922 | `B7-filling-sourced` | bulk | gas_equipment | 0 | 0 | fill |
| rec-00923 | `B7-filling-sourced` | fine | gas_equipment | 0 | 0 | fill |
| rec-00924 | `B7-filling-sourced` | office | gas_equipment | 0 | 0 | fill |
| rec-00931 | `B8-internal-mass` | bulk | mass_accounting.additional_mass | — | 2 | fill |
| rec-00925 | `C3-building-service` | services.json#exterior_lighting | exterior_lighting | — | {"control": "AstronomicalClock", "design_level_W": 10958.0, "end_use": "exterior_lighting… | add |
| rec-00929 | `C10-building-wwr` | constructions | fenestration_defaults | — | {"all": {"E": 0.0, "N": 0.0, "S": 0.0286, "W": 0.0076, "roof": 0.0}, "conditioned": {"E":… | add |
| rec-00926 | `C10-program-wwr` | bulk | fenestration | — | {"E": 0.0, "N": 0.0, "S": null, "W": 0.0, "roof": 0.0} | add |
| rec-00927 | `C10-program-wwr` | fine | fenestration | — | {"E": 0.0, "N": 0.0, "S": 0.0, "W": 0.0, "roof": 0.0} | add |
| rec-00928 | `C10-program-wwr` | office | fenestration | — | {"E": 0.0, "N": 0.0, "S": 0.1009, "W": 0.1668, "roof": null} | add |

## doe-ref-pre-1980 · All building types

| Row | Class | Target | Field | Atlas | DOE | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| rec-01867 | `C1-holiday-calendar` | — | source_calendar.holidays | — | [["New Years Day", "January 1"], ["Veterans Day", "November 11"], ["Christmas", "December… | add |
| rec-01868 | `C2-daylight-saving` | — | source_calendar.daylight_saving | — | RunPeriodControl:DaylightSavingTime, not applied | add |
| rec-01869 | `C7-systems` | — | HVAC, outdoor air, zone mixing, water heaters | — | present in the DOE files | omit (`R-SYSTEMS-DEFERRED`) |
| rec-01873 | `C10-geometry` | — | plan geometry, shading, skylight placement | — | present in the DOE files | omit (`R-GEOMETRY-BEMGEN`) |
| rec-01870 | `C11-site-data` | — | ground temperatures, water mains, sizing, tariffs | — | present in the DOE files | omit (`R-SITE-DATA`) |
| rec-01871 | `C12-comfort-fields` | — | People comfort fields | — | present in the DOE files | omit (`R-COMFORT-ONLY`) |
| rec-01872 | `C13-replaceable-fraction` | — | Lights replaceable fraction | — | present in the DOE files | omit (`R-DAYLIGHTING-ONLY`) |

## doe-ref-pre-1980 · FullServiceRestaurant

| Row | Class | Target | Field | Atlas | DOE | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| rec-00943 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | FullServiceRestaurant Bldg Occ | Schedule:Compact BLDG_OCC_SCH | replace |
| rec-00945 | `A7-rounding` | dining | occupancy | 0.721182 | 0.719424 | keep (`R-ROUNDING`) |
| rec-00946 | `A7-rounding` | dining | lighting | 27.3403 | 27.38 | keep (`R-ROUNDING`) |
| rec-00948 | `A7-rounding` | kitchen | gas_equipment | 1194.8 | 1197.9 | keep (`R-ROUNDING`) |
| rec-00959 | `A10-infiltration-method` | constructions | infiltration.methods.doe_design_flow | fixed_source_reference_natural_ach | [["flow/exteriorarea", 0.001133, "INFIL_HALF_ON_SCH"]] | add |
| rec-00944 | `A10-infiltration-schedule` | — | schedule (infiltration) | — | Schedule:Compact INFIL_HALF_ON_SCH | add |
| rec-00960 | `B2-additional-lighting` | dining | additional_lighting | — | 0 | fill |
| rec-00961 | `B2-additional-lighting` | kitchen | additional_lighting | — | 0 | fill |
| rec-00947 | `B7-filling-sourced` | dining | gas_equipment | 0 | 0 | fill |
| rec-00950 | `C3-building-service` | services.json#exhaust_fan | exhaust_fan | — | {"end_use": "exhaust_fan", "fractions": {"latent": 0.0, "lost": 1.0, "radiant": 0.0}, "me… | add |
| rec-00951 | `C3-building-service` | services.json#exterior_lighting | exterior_lighting | — | {"control": "AstronomicalClock", "design_level_W": 5081.0, "end_use": "exterior_lighting"… | add |
| rec-00952 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 688.0, "end_use": "refrigeration_case", "fa… | add |
| rec-00953 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 734.0, "end_use": "refrigeration_case", "fa… | add |
| rec-00954 | `C4-refrigeration` | services.json#refrigeration_rack | refrigeration_rack | — | {"condenser_fan_W": 330.0, "cop": 1.5, "end_use": "refrigeration_rack", "heat_rejection":… | add |
| rec-00955 | `C4-refrigeration` | services.json#refrigeration_rack | refrigeration_rack | — | {"condenser_fan_W": 330.0, "cop": 3.0, "end_use": "refrigeration_rack", "heat_rejection":… | add |
| rec-00949 | `C5-water-use-gains` | kitchen | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction": 0.… | add |
| rec-00958 | `C10-building-wwr` | constructions | fenestration_defaults | — | {"all": {"E": 0.2022, "N": 0.0, "S": 0.28, "W": 0.2022, "roof": 0.0}, "conditioned": {"E"… | add |
| rec-00956 | `C10-program-wwr` | dining | fenestration | — | {"E": 0.278, "N": null, "S": 0.28, "W": 0.278, "roof": 0.0} | add |
| rec-00957 | `C10-program-wwr` | kitchen | fenestration | — | {"E": 0.0, "N": 0.0, "S": null, "W": 0.0, "roof": 0.0} | add |

## doe-ref-pre-1980 · Hospital

| Row | Class | Target | Field | Atlas | DOE | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| rec-00966 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | — | Schedule:Compact ADMIN_OCC_SCH | replace |
| rec-00970 | `A3-no-atlas-counterpart` | — | schedule (cooling setpoint) | — | Schedule:Compact Kitchen_CLGSETP_SCH | replace |
| rec-00973 | `A3-no-atlas-counterpart` | — | schedule (heating setpoint) | — | Schedule:Compact Kitchen_HTGSETP_SCH | replace |
| rec-00974 | `A3-no-atlas-counterpart` | — | schedule (cooling setpoint) | — | Schedule:Compact OR_CLGSETP_SCH | replace |
| rec-00962 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (cooling setpoint) | — | Schedule:Compact ADMIN_CLGSETP_SCH | replace |
| rec-00964 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (heating setpoint) | — | Schedule:Compact ADMIN_HTGSETP_SCH | replace |
| rec-00965 | `A4-assignment` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (lighting) | — | Schedule:Compact ADMIN_LIGHT_SCH | replace |
| rec-00975 | `A4-assignment` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (heating setpoint) | — | Schedule:Compact OR_HTGSETP_SCH | replace |
| rec-00976 | `A4-slot-assignment` | er-exam | cooling_setpoint_schedule_id schedule (cooling) | Hospital Critical HtgSetp | Schedule:Compact CRITICAL_CLGSETP_SCH | replace |
| rec-00977 | `A4-slot-assignment` | er-trauma | cooling_setpoint_schedule_id schedule (cooling) | Hospital Critical HtgSetp | Schedule:Compact CRITICAL_CLGSETP_SCH | replace |
| rec-00978 | `A4-slot-assignment` | er-triage | cooling_setpoint_schedule_id schedule (cooling) | Hospital Critical HtgSetp | Schedule:Compact CRITICAL_CLGSETP_SCH | replace |
| rec-00979 | `A4-slot-assignment` | icu-open | cooling_setpoint_schedule_id schedule (cooling) | Hospital Critical HtgSetp | Schedule:Compact CRITICAL_CLGSETP_SCH | replace |
| rec-00980 | `A4-slot-assignment` | icu-open | electric_equipment schedule (electric_equipment) | Hospital Admin Equipment | Schedule:Compact CRITICAL_EQUIP_SCH | replace |
| rec-00981 | `A4-slot-assignment` | icu-pat-rm | cooling_setpoint_schedule_id schedule (cooling) | Hospital Critical HtgSetp | Schedule:Compact CRITICAL_CLGSETP_SCH | replace |
| rec-00989 | `A5-existing-density` | er-nurse-stn | occupancy | 0.0672744 | 0.0143 | keep (`R-EXISTING-DENSITY`) |
| rec-00995 | `A5-existing-density` | er-triage | electric_equipment | 28.7396 | 29.05 | keep (`R-EXISTING-DENSITY`) |
| rec-00997 | `A5-existing-density` | icu-open | occupancy | 0.215278 | 0.0538 | keep (`R-EXISTING-DENSITY`) |
| rec-00999 | `A5-existing-density` | icu-nurse-stn | occupancy | 0.0538196 | 0.0143 | keep (`R-EXISTING-DENSITY`) |
| rec-01005 | `A5-existing-density` | lobby | occupancy | 0.0768543 | 0.0143 | keep (`R-EXISTING-DENSITY`) |
| rec-01006 | `A5-existing-density` | lobby | lighting | 11.0868 | 15.73 | keep (`R-EXISTING-DENSITY`) |
| rec-01009 | `A5-existing-density` | nurse-stn | occupancy | 0.0768543 | 0.0143 | keep (`R-EXISTING-DENSITY`) |
| rec-00983 | `A7-rounding` | corridor | occupancy | 0.0107639 | 0.0108 | keep (`R-ROUNDING`) |
| rec-00986 | `A7-rounding` | er-exam | occupancy | 0.215278 | 0.214998 | keep (`R-ROUNDING`) |
| rec-00987 | `A7-rounding` | er-exam | electric_equipment | 16.1459 | 16.04 | keep (`R-ROUNDING`) |
| rec-00990 | `A7-rounding` | er-nurse-stn | lighting | 17.8681 | 17.89 | keep (`R-ROUNDING`) |
| rec-00992 | `A7-rounding` | er-trauma | occupancy | 0.215278 | 0.214998 | keep (`R-ROUNDING`) |
| rec-00994 | `A7-rounding` | er-triage | occupancy | 0.215278 | 0.214998 | keep (`R-ROUNDING`) |
| rec-01000 | `A7-rounding` | icu-nurse-stn | lighting | 18.4063 | 18.45 | keep (`R-ROUNDING`) |
| rec-01003 | `A7-rounding` | lab | lighting | 22.6042 | 22.65 | keep (`R-ROUNDING`) |
| rec-01007 | `A7-rounding` | lobby | electric_equipment | 1.07639 | 1.08 | keep (`R-ROUNDING`) |
| rec-01014 | `A7-rounding` | phys-therapy | lighting | 27.0174 | 26.93 | keep (`R-ROUNDING`) |
| rec-01016 | `A7-rounding` | radiology | lighting | 23.7882 | 23.82 | keep (`R-ROUNDING`) |
| rec-00963 | `A9-design-days` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | — | Schedule:Compact ADMIN_EQUIP_SCH | replace |
| rec-00971 | `A9-design-days` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | Hospital Kitchen_Elec_Equip_SCH | Schedule:Compact Kitchen_Elec_Equip_SCH | replace |
| rec-01082 | `A10-infiltration-method` | constructions | infiltration.methods.doe_design_flow | fixed_source_reference_natural_ach | [["flow/exteriorwallarea", 0.001133, "INFIL_QUARTER_ON_SCH"]] | add |
| rec-00969 | `A10-infiltration-schedule` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (infiltration) | Hospital HVACOperationSchd | Schedule:Compact INFIL_QUARTER_ON_SCH | add |
| rec-01018 | `B1-hot-water` | basement | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-01019 | `B1-hot-water` | corridor | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-01020 | `B1-hot-water` | dining | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-01021 | `B1-hot-water` | er-nurse-stn | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-01022 | `B1-hot-water` | icu-nurse-stn | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-01023 | `B1-hot-water` | icu-open | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-01024 | `B1-hot-water` | icu-pat-rm | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-01025 | `B1-hot-water` | lobby | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-01026 | `B1-hot-water` | nurse-stn | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-01027 | `B1-hot-water` | office | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-00967 | `B1-hot-water-schedule` | — | schedule (hot-water flow) | — | Schedule:Compact BLDG_SWH_EXTD_SCH | fill |
| rec-00968 | `B1-hot-water-schedule` | — | schedule (hot-water flow) | — | Schedule:Compact BLDG_SWH_SCH | fill |
| rec-01083 | `B2-additional-lighting` | basement | additional_lighting | — | 0 | fill |
| rec-01084 | `B2-additional-lighting` | corridor | additional_lighting | — | 0 | fill |
| rec-01085 | `B2-additional-lighting` | dining | additional_lighting | — | 0 | fill |
| rec-01086 | `B2-additional-lighting` | er-exam | additional_lighting | — | 0 | fill |
| rec-01087 | `B2-additional-lighting` | er-nurse-stn | additional_lighting | — | 0 | fill |
| rec-01088 | `B2-additional-lighting` | er-trauma | additional_lighting | — | 0 | fill |
| rec-01089 | `B2-additional-lighting` | er-triage | additional_lighting | — | 0 | fill |
| rec-01090 | `B2-additional-lighting` | icu-nurse-stn | additional_lighting | — | 0 | fill |
| rec-01091 | `B2-additional-lighting` | icu-open | additional_lighting | — | 0 | fill |
| rec-01092 | `B2-additional-lighting` | icu-pat-rm | additional_lighting | — | 0 | fill |
| rec-01093 | `B2-additional-lighting` | kitchen | additional_lighting | — | 0 | fill |
| rec-01094 | `B2-additional-lighting` | lab | additional_lighting | — | 0 | fill |
| rec-01095 | `B2-additional-lighting` | lobby | additional_lighting | — | one lighting object per zone | leave (`R-NO-LIGHTING-SPLIT`) |
| rec-01096 | `B2-additional-lighting` | nurse-stn | additional_lighting | — | 0 | fill |
| rec-01097 | `B2-additional-lighting` | office | additional_lighting | — | 0 | fill |
| rec-01098 | `B2-additional-lighting` | or | additional_lighting | — | 0 | fill |
| rec-01099 | `B2-additional-lighting` | pat-room | additional_lighting | — | 0 | fill |
| rec-01100 | `B2-additional-lighting` | phys-therapy | additional_lighting | — | 0 | fill |
| rec-01101 | `B2-additional-lighting` | radiology | additional_lighting | — | 0 | fill |
| rec-00982 | `B7-filling-sourced` | basement | gas_equipment | 0 | 0 | fill |
| rec-00984 | `B7-filling-sourced` | corridor | gas_equipment | 0 | 0 | fill |
| rec-00985 | `B7-filling-sourced` | dining | gas_equipment | 0 | 0 | fill |
| rec-00988 | `B7-filling-sourced` | er-exam | gas_equipment | 0 | 0 | fill |
| rec-00991 | `B7-filling-sourced` | er-nurse-stn | gas_equipment | 0 | 0 | fill |
| rec-00993 | `B7-filling-sourced` | er-trauma | gas_equipment | 0 | 0 | fill |
| rec-00996 | `B7-filling-sourced` | er-triage | gas_equipment | 0 | 0 | fill |
| rec-00998 | `B7-filling-sourced` | icu-open | gas_equipment | 0 | 0 | fill |
| rec-01001 | `B7-filling-sourced` | icu-nurse-stn | gas_equipment | 0 | 0 | fill |
| rec-01002 | `B7-filling-sourced` | icu-pat-rm | gas_equipment | 0 | 0 | fill |
| rec-01004 | `B7-filling-sourced` | lab | gas_equipment | 0 | 0 | fill |
| rec-01008 | `B7-filling-sourced` | lobby | gas_equipment | 0 | 0 | fill |
| rec-01010 | `B7-filling-sourced` | nurse-stn | gas_equipment | 0 | 0 | fill |
| rec-01011 | `B7-filling-sourced` | or | gas_equipment | 0 | 0 | fill |
| rec-01012 | `B7-filling-sourced` | office | gas_equipment | 0 | 0 | fill |
| rec-01013 | `B7-filling-sourced` | pat-room | gas_equipment | 0 | 0 | fill |
| rec-01015 | `B7-filling-sourced` | phys-therapy | gas_equipment | 0 | 0 | fill |
| rec-01017 | `B7-filling-sourced` | radiology | gas_equipment | 0 | 0 | fill |
| rec-01058 | `C3-building-service` | services.json#exhaust_fan | exhaust_fan | — | {"end_use": "exhaust_fan", "fractions": {"latent": 0.0, "lost": 1.0, "radiant": 0.0}, "me… | add |
| rec-01059 | `C3-building-service` | services.json#exterior_lighting | exterior_lighting | — | {"control": "AstronomicalClock", "design_level_W": 20829.0, "end_use": "exterior_lighting… | add |
| rec-01060 | `C3-building-service` | services.json#elevator | elevator | — | {"design_level_W": 162962.637362637, "end_use": "elevator", "fuel": "Electricity", "name"… | add |
| rec-00972 | `C3-building-service-schedule` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | — | Schedule:Compact Kitchen_Exhaust_SCH | add |
| rec-01061 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 734.0, "end_use": "refrigeration_case", "fa… | add |
| rec-01062 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 886.5, "end_use": "refrigeration_case", "fa… | add |
| rec-01063 | `C4-refrigeration` | services.json#refrigeration_rack | refrigeration_rack | — | {"condenser_fan_W": 1000.0, "cop": 1.5, "end_use": "refrigeration_rack", "heat_rejection"… | add |
| rec-01064 | `C4-refrigeration` | services.json#refrigeration_rack | refrigeration_rack | — | {"condenser_fan_W": 1000.0, "cop": 3.0, "end_use": "refrigeration_rack", "heat_rejection"… | add |
| rec-01028 | `C5-water-use-gains` | er-exam | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-01029 | `C5-water-use-gains` | er-exam | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-01030 | `C5-water-use-gains` | er-trauma | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-01031 | `C5-water-use-gains` | er-trauma | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-01032 | `C5-water-use-gains` | er-triage | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-01033 | `C5-water-use-gains` | kitchen | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-01034 | `C5-water-use-gains` | lab | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction": 0.… | add |
| rec-01035 | `C5-water-use-gains` | lab | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction": 0.… | add |
| rec-01036 | `C5-water-use-gains` | or | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction": 0.… | add |
| rec-01037 | `C5-water-use-gains` | or | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction": 0.… | add |
| rec-01038 | `C5-water-use-gains` | or | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction": 0.… | add |
| rec-01039 | `C5-water-use-gains` | or | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction": 0.… | add |
| rec-01040 | `C5-water-use-gains` | pat-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-01041 | `C5-water-use-gains` | pat-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-01042 | `C5-water-use-gains` | pat-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-01043 | `C5-water-use-gains` | pat-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-01044 | `C5-water-use-gains` | pat-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-01045 | `C5-water-use-gains` | pat-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-01046 | `C5-water-use-gains` | pat-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-01047 | `C5-water-use-gains` | pat-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-01048 | `C5-water-use-gains` | pat-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-01049 | `C5-water-use-gains` | pat-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-01050 | `C5-water-use-gains` | pat-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-01051 | `C5-water-use-gains` | pat-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-01052 | `C5-water-use-gains` | pat-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-01053 | `C5-water-use-gains` | pat-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-01054 | `C5-water-use-gains` | pat-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-01055 | `C5-water-use-gains` | pat-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-01056 | `C5-water-use-gains` | phys-therapy | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction": 0.… | add |
| rec-01057 | `C5-water-use-gains` | radiology | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_EXTD_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction… | add |
| rec-01065 | `C6-humidity-setpoint` | er-exam | humidity setpoints | — | {"dehumidifying": 60.0, "humidifying": 40.0, "zone": "ER_Exam3_Mult4_Flr_1"} | add |
| rec-01066 | `C6-humidity-setpoint` | or | humidity setpoints | — | {"dehumidifying": 60.0, "humidifying": 40.0, "zone": "OR2_Mult5_Flr_2"} | add |
| rec-01081 | `C10-building-wwr` | constructions | fenestration_defaults | — | {"all": {"E": 0.1358, "N": 0.1244, "S": 0.1488, "W": 0.258, "roof": 0.0}, "conditioned": … | add |
| rec-01067 | `C10-program-wwr` | corridor | fenestration | — | {"E": null, "N": 0.0, "S": 0.0, "W": null, "roof": 0.0} | add |
| rec-01068 | `C10-program-wwr` | dining | fenestration | — | {"E": 0.0, "N": null, "S": 0.2749, "W": null, "roof": 0.0} | add |
| rec-01069 | `C10-program-wwr` | er-exam | fenestration | — | {"E": 0.0, "N": null, "S": 0.0, "W": null, "roof": null} | add |
| rec-01070 | `C10-program-wwr` | er-nurse-stn | fenestration | — | {"E": 0.2751, "N": null, "S": null, "W": null, "roof": null} | add |
| rec-01071 | `C10-program-wwr` | er-trauma | fenestration | — | {"E": 0.0, "N": 0.0, "S": 0.0, "W": null, "roof": null} | add |
| rec-01072 | `C10-program-wwr` | er-triage | fenestration | — | {"E": null, "N": 0.0, "S": null, "W": null, "roof": null} | add |
| rec-01073 | `C10-program-wwr` | icu-open | fenestration | — | {"E": null, "N": null, "S": 0.0, "W": 0.2748, "roof": null} | add |
| rec-01074 | `C10-program-wwr` | icu-pat-rm | fenestration | — | {"E": null, "N": 0.2513, "S": null, "W": 0.2514, "roof": null} | add |
| rec-01075 | `C10-program-wwr` | kitchen | fenestration | — | {"E": 0.0, "N": 0.0, "S": null, "W": null, "roof": 0.0} | add |
| rec-01076 | `C10-program-wwr` | lobby | fenestration | — | {"E": null, "N": 0.0, "S": 0.0, "W": 0.2751, "roof": null} | add |
| rec-01077 | `C10-program-wwr` | nurse-stn | fenestration | — | {"E": null, "N": 0.0, "S": 0.1527, "W": null, "roof": 0.0} | add |
| rec-01078 | `C10-program-wwr` | office | fenestration | — | {"E": null, "N": 0.2356, "S": 0.2379, "W": 0.2514, "roof": 0.0} | add |
| rec-01079 | `C10-program-wwr` | or | fenestration | — | {"E": 0.0, "N": 0.0, "S": null, "W": null, "roof": null} | add |
| rec-01080 | `C10-program-wwr` | pat-room | fenestration | — | {"E": 0.2513, "N": 0.2514, "S": 0.2514, "W": 0.2513, "roof": null} | add |

## doe-ref-pre-1980 · LargeHotel

| Row | Class | Target | Field | Atlas | DOE | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| rec-01102 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | LargeHotel Bldg Equip | Schedule:Compact BLDG_EQUIP_SCH | replace |
| rec-01103 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (lighting) | — | Schedule:Compact BLDG_LIGHT_SCH | replace |
| rec-01104 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | — | Schedule:Compact Common_Occ_Sch | replace |
| rec-01105 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | — | Schedule:Compact GuestRoom_Eqp_Sch | replace |
| rec-01106 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (lighting) | — | Schedule:Compact GuestRoom_Ltg_Sch_Base | replace |
| rec-01107 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | — | Schedule:Compact GuestRoom_Occ_Sch | replace |
| rec-01110 | `A4-slot-assignment` | mechanical | cooling_setpoint_schedule_id schedule (cooling) | LargeHotel ClgSetp | Schedule:Compact Corr_CLGSETP_SCH | replace |
| rec-01111 | `A4-slot-assignment` | mechanical | heating_setpoint_schedule_id schedule (heating) | LargeHotel HtgSetp | Schedule:Compact Corr_HTGSETP_SCH | replace |
| rec-01112 | `A4-slot-assignment` | storage | cooling_setpoint_schedule_id schedule (cooling) | LargeHotel ClgSetp | Schedule:Compact Corr_CLGSETP_SCH | replace |
| rec-01113 | `A4-slot-assignment` | storage | heating_setpoint_schedule_id schedule (heating) | LargeHotel HtgSetp | Schedule:Compact Corr_HTGSETP_SCH | replace |
| rec-01114 | `A7-rounding` | banquet | occupancy | 0.721182 | 0.719424 | keep (`R-ROUNDING`) |
| rec-01117 | `A7-rounding` | cafe | occupancy | 0.721182 | 0.719424 | keep (`R-ROUNDING`) |
| rec-01119 | `A7-rounding` | corridor2 | lighting | 13.132 | 13.11 | keep (`R-ROUNDING`) |
| rec-01121 | `A7-rounding` | corridor | lighting | 13.132 | 13.11 | keep (`R-ROUNDING`) |
| rec-01123 | `A7-rounding` | kitchen | lighting | 16.7917 | 16.83 | keep (`R-ROUNDING`) |
| rec-01124 | `A7-rounding` | laundry | lighting | 12.2709 | 12.23 | keep (`R-ROUNDING`) |
| rec-01125 | `A7-rounding` | lobby | occupancy | 0.322917 | 0.322581 | keep (`R-ROUNDING`) |
| rec-01126 | `A7-rounding` | lobby | lighting | 20.2362 | 20.28 | keep (`R-ROUNDING`) |
| rec-01128 | `A7-rounding` | mechanical | lighting | 8.61113 | 8.6 | keep (`R-ROUNDING`) |
| rec-01132 | `A7-rounding` | guest-room | lighting | 19.0521 | 19.09 | keep (`R-ROUNDING`) |
| rec-01133 | `A7-rounding` | guest-room | electric_equipment | 14.316 | 14.3 | keep (`R-ROUNDING`) |
| rec-01135 | `A7-rounding` | guest-room3 | lighting | 19.0521 | 19.09 | keep (`R-ROUNDING`) |
| rec-01136 | `A7-rounding` | guest-room3 | electric_equipment | 14.316 | 14.3 | keep (`R-ROUNDING`) |
| rec-01138 | `A7-rounding` | guest-room2 | lighting | 19.0521 | 19.09 | keep (`R-ROUNDING`) |
| rec-01139 | `A7-rounding` | guest-room2 | electric_equipment | 14.316 | 14.3 | keep (`R-ROUNDING`) |
| rec-01141 | `A7-rounding` | guest-room4 | lighting | 19.0521 | 19.09 | keep (`R-ROUNDING`) |
| rec-01142 | `A7-rounding` | guest-room4 | electric_equipment | 14.316 | 14.3 | keep (`R-ROUNDING`) |
| rec-01144 | `A7-rounding` | storage | lighting | 3.98265 | 3.96 | keep (`R-ROUNDING`) |
| rec-01182 | `A10-infiltration-method` | constructions | infiltration.methods.doe_design_flow | fixed_source_reference_natural_ach | [["flow/exteriorwallarea", 0.001133, "INFIL_QUARTER_ON_SCH"]] | add |
| rec-01108 | `A10-infiltration-schedule` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (infiltration) | — | Schedule:Compact INFIL_QUARTER_ON_SCH | add |
| rec-01146 | `B1-hot-water` | basement | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-01183 | `B2-additional-lighting` | banquet | additional_lighting | — | 0 | fill |
| rec-01184 | `B2-additional-lighting` | basement | additional_lighting | — | 0 | fill |
| rec-01185 | `B2-additional-lighting` | cafe | additional_lighting | — | 0 | fill |
| rec-01186 | `B2-additional-lighting` | corridor | additional_lighting | — | 0 | fill |
| rec-01187 | `B2-additional-lighting` | corridor2 | additional_lighting | — | 0 | fill |
| rec-01188 | `B2-additional-lighting` | guest-room | additional_lighting | — | 0 | fill |
| rec-01189 | `B2-additional-lighting` | guest-room2 | additional_lighting | — | 0 | fill |
| rec-01190 | `B2-additional-lighting` | guest-room3 | additional_lighting | — | 0 | fill |
| rec-01191 | `B2-additional-lighting` | guest-room4 | additional_lighting | — | 0 | fill |
| rec-01192 | `B2-additional-lighting` | kitchen | additional_lighting | — | 0 | fill |
| rec-01193 | `B2-additional-lighting` | laundry | additional_lighting | — | 0 | fill |
| rec-01194 | `B2-additional-lighting` | lobby | additional_lighting | — | 0 | fill |
| rec-01195 | `B2-additional-lighting` | mechanical | additional_lighting | — | 0 | fill |
| rec-01196 | `B2-additional-lighting` | retail | additional_lighting | — | 0 | fill |
| rec-01197 | `B2-additional-lighting` | retail2 | additional_lighting | — | 0 | fill |
| rec-01198 | `B2-additional-lighting` | storage | additional_lighting | — | 0 | fill |
| rec-01115 | `B7-filling-sourced` | banquet | gas_equipment | 0 | 0 | fill |
| rec-01116 | `B7-filling-sourced` | basement | gas_equipment | 0 | 0 | fill |
| rec-01118 | `B7-filling-sourced` | cafe | gas_equipment | 0 | 0 | fill |
| rec-01120 | `B7-filling-sourced` | corridor2 | gas_equipment | 0 | 0 | fill |
| rec-01122 | `B7-filling-sourced` | corridor | gas_equipment | 0 | 0 | fill |
| rec-01127 | `B7-filling-sourced` | lobby | gas_equipment | 0 | 0 | fill |
| rec-01129 | `B7-filling-sourced` | mechanical | gas_equipment | 0 | 0 | fill |
| rec-01130 | `B7-filling-sourced` | retail | gas_equipment | 0 | 0 | fill |
| rec-01131 | `B7-filling-sourced` | retail2 | gas_equipment | 0 | 0 | fill |
| rec-01134 | `B7-filling-sourced` | guest-room | gas_equipment | 0 | 0 | fill |
| rec-01137 | `B7-filling-sourced` | guest-room3 | gas_equipment | 0 | 0 | fill |
| rec-01140 | `B7-filling-sourced` | guest-room2 | gas_equipment | 0 | 0 | fill |
| rec-01143 | `B7-filling-sourced` | guest-room4 | gas_equipment | 0 | 0 | fill |
| rec-01145 | `B7-filling-sourced` | storage | gas_equipment | 0 | 0 | fill |
| rec-01158 | `C3-building-service` | services.json#exhaust_fan | exhaust_fan | — | {"end_use": "exhaust_fan", "fractions": {"latent": 0.0, "lost": 1.0, "radiant": 0.0}, "me… | add |
| rec-01159 | `C3-building-service` | services.json#exhaust_fan | exhaust_fan | — | {"end_use": "exhaust_fan", "fractions": {"latent": 0.0, "lost": 1.0, "radiant": 0.0}, "me… | add |
| rec-01160 | `C3-building-service` | services.json#exterior_lighting | exterior_lighting | — | {"control": "AstronomicalClock", "design_level_W": 27826.0, "end_use": "exterior_lighting… | add |
| rec-01161 | `C3-building-service` | services.json#elevator | elevator | — | {"design_level_W": 122221.978021978, "end_use": "elevator", "fuel": "Electricity", "name"… | add |
| rec-01109 | `C3-building-service-schedule` | — | schedule (plug) | — | Schedule:Compact Kitchen_Exhaust_SCH | add |
| rec-01162 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 367.0, "end_use": "refrigeration_case", "fa… | add |
| rec-01163 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 734.0, "end_use": "refrigeration_case", "fa… | add |
| rec-01164 | `C4-refrigeration` | services.json#refrigeration_rack | refrigeration_rack | — | {"condenser_fan_W": 350.0, "cop": 1.5, "end_use": "refrigeration_rack", "heat_rejection":… | add |
| rec-01165 | `C4-refrigeration` | services.json#refrigeration_rack | refrigeration_rack | — | {"condenser_fan_W": 350.0, "cop": 3.0, "end_use": "refrigeration_rack", "heat_rejection":… | add |
| rec-01147 | `C5-water-use-gains` | kitchen | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "Kitchen_SWH_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction":… | add |
| rec-01148 | `C5-water-use-gains` | laundry | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "LaundryRoom_SWH_Sch", "hot_supply_temperature_C": 60.0, "latent_fracti… | add |
| rec-01149 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01150 | `C5-water-use-gains` | guest-room3 | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01151 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01152 | `C5-water-use-gains` | guest-room3 | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01153 | `C5-water-use-gains` | guest-room2 | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01154 | `C5-water-use-gains` | guest-room4 | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01155 | `C5-water-use-gains` | guest-room2 | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01156 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01157 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01181 | `C10-building-wwr` | constructions | fenestration_defaults | — | {"all": {"E": 0.2448, "N": 0.2604, "S": 0.3667, "W": 0.2448, "roof": 0.0}, "conditioned":… | add |
| rec-01166 | `C10-program-wwr` | banquet | fenestration | — | {"E": null, "N": 0.3302, "S": null, "W": null, "roof": 0.0} | add |
| rec-01167 | `C10-program-wwr` | cafe | fenestration | — | {"E": 0.0, "N": null, "S": 0.5078, "W": null, "roof": 0.0} | add |
| rec-01168 | `C10-program-wwr` | corridor | fenestration | — | {"E": null, "N": 0.3302, "S": 0.3302, "W": null, "roof": 0.0} | add |
| rec-01169 | `C10-program-wwr` | corridor2 | fenestration | — | {"E": null, "N": 0.33, "S": 0.3299, "W": null, "roof": null} | add |
| rec-01170 | `C10-program-wwr` | guest-room | fenestration | — | {"E": 0.3299, "N": 0.33, "S": 0.33, "W": 0.3299, "roof": null} | add |
| rec-01171 | `C10-program-wwr` | guest-room2 | fenestration | — | {"E": null, "N": 0.33, "S": 0.3299, "W": null, "roof": null} | add |
| rec-01172 | `C10-program-wwr` | guest-room3 | fenestration | — | {"E": null, "N": 0.3302, "S": 0.3302, "W": 0.3302, "roof": 0.0} | add |
| rec-01173 | `C10-program-wwr` | guest-room4 | fenestration | — | {"E": null, "N": null, "S": 0.3302, "W": null, "roof": 0.0} | add |
| rec-01174 | `C10-program-wwr` | kitchen | fenestration | — | {"E": 0.3302, "N": 0.2154, "S": 0.3302, "W": null, "roof": 0.0} | add |
| rec-01175 | `C10-program-wwr` | laundry | fenestration | — | {"E": 0.0, "N": 0.0, "S": null, "W": null, "roof": null} | add |
| rec-01176 | `C10-program-wwr` | lobby | fenestration | — | {"E": null, "N": 0.0, "S": 0.5078, "W": 0.0, "roof": 0.0} | add |
| rec-01177 | `C10-program-wwr` | mechanical | fenestration | — | {"E": null, "N": 0.0, "S": null, "W": null, "roof": null} | add |
| rec-01178 | `C10-program-wwr` | retail | fenestration | — | {"E": null, "N": null, "S": 0.5078, "W": 0.0, "roof": 0.0} | add |
| rec-01179 | `C10-program-wwr` | retail2 | fenestration | — | {"E": null, "N": null, "S": null, "W": 0.0, "roof": null} | add |
| rec-01180 | `C10-program-wwr` | storage | fenestration | — | {"E": null, "N": 0.0, "S": null, "W": null, "roof": null} | add |

## doe-ref-pre-1980 · LargeOffice

| Row | Class | Target | Field | Atlas | DOE | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| rec-01199 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | Large Office Bldg Equip | Schedule:Compact BLDG_EQUIP_SCH | replace |
| rec-01200 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (lighting) | Large Office Bldg Light | Schedule:Compact BLDG_LIGHT_SCH | replace |
| rec-01201 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | Large Office Bldg Occ | Schedule:Compact BLDG_OCC_SCH | replace |
| rec-01203 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (cooling setpoint) | Large Office ClgSetp | Schedule:Compact CLGSETP_SCH | replace |
| rec-01204 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (heating setpoint) | Large Office HtgSetp | Schedule:Compact HTGSETP_SCH | replace |
| rec-01214 | `A10-infiltration-method` | constructions | infiltration.methods.doe_design_flow | fixed_source_reference_natural_ach | [["flow/exteriorarea", 0.001133, "INFIL_QUARTER_ON_SCH"]] | add |
| rec-01205 | `A10-infiltration-schedule` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (infiltration) | Large Office Bldg Equip | Schedule:Compact INFIL_QUARTER_ON_SCH | add |
| rec-01202 | `B1-hot-water-schedule` | — | schedule (hot-water flow) | — | Schedule:Compact BLDG_SWH_SCH | fill |
| rec-01216 | `B2-additional-lighting` | whole-building-lg-office | additional_lighting | — | 0 | fill |
| rec-01215 | `B3-unconditioned-equipment` | plenum | electric_equipment | — | no ElectricEquipment in the complete DOE model: 0, constant 0 | fill |
| rec-01206 | `B7-filling-sourced` | whole-building-lg-office | gas_equipment | 0 | 0 | fill |
| rec-01210 | `C3-building-service` | services.json#exterior_lighting | exterior_lighting | — | {"control": "AstronomicalClock", "design_level_W": 61595.0, "end_use": "exterior_lighting… | add |
| rec-01211 | `C3-building-service` | services.json#elevator | elevator | — | {"design_level_W": 244443.956043956, "end_use": "elevator", "fuel": "Electricity", "name"… | add |
| rec-01207 | `C5-water-use-gains` | whole-building-lg-office | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-01208 | `C5-water-use-gains` | whole-building-lg-office | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-01209 | `C5-water-use-gains` | whole-building-lg-office | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-01217 | `C8-basement-program` | whole-building-lg-office | program Basement_LargeOffice | WholeBuilding - Lg Office | {"electric_equipment": 10.76, "gas_equipment": 0.0, "lighting": 16.14, "occupancy": 0.026… | add |
| rec-01213 | `C10-building-wwr` | constructions | fenestration_defaults | — | {"all": {"E": 0.4017, "N": 0.4, "S": 0.4, "W": 0.4017, "roof": 0.0}, "conditioned": {"E":… | add |
| rec-01212 | `C10-program-wwr` | whole-building-lg-office | fenestration | — | {"E": 0.5813, "N": 0.5778, "S": 0.5778, "W": 0.5813, "roof": null} | add |

## doe-ref-pre-1980 · MediumOffice

| Row | Class | Target | Field | Atlas | DOE | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| rec-01219 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | Medium Office Bldg Equip | Schedule:Compact BLDG_EQUIP_SCH | replace |
| rec-01221 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | Medium Office Bldg Occ | Schedule:Compact BLDG_OCC_SCH | replace |
| rec-01223 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (cooling setpoint) | Medium Office ClgSetp | Schedule:Compact CLGSETP_SCH | replace |
| rec-01224 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (heating setpoint) | Medium Office HtgSetp | Schedule:Compact HTGSETP_SCH | replace |
| rec-01220 | `A4-assignment` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (lighting) | Office Bldg Light | Schedule:Compact BLDG_LIGHT_SCH | replace |
| rec-01234 | `A10-infiltration-method` | constructions | infiltration.methods.doe_design_flow | fixed_source_reference_natural_ach | [["flow/exteriorarea", 0.001133, "INFIL_QUARTER_ON_SCH"]] | add |
| rec-01225 | `A10-infiltration-schedule` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (infiltration) | Medium Office Bldg Equip | Schedule:Compact INFIL_QUARTER_ON_SCH | add |
| rec-01222 | `B1-hot-water-schedule` | — | schedule (hot-water flow) | — | Schedule:Compact BLDG_SWH_SCH | fill |
| rec-01236 | `B2-additional-lighting` | whole-building-md-office | additional_lighting | — | 0 | fill |
| rec-01235 | `B3-unconditioned-equipment` | plenum | electric_equipment | — | no ElectricEquipment in the complete DOE model: 0, constant 0 | fill |
| rec-01226 | `B7-filling-sourced` | whole-building-md-office | gas_equipment | 0 | 0 | fill |
| rec-01230 | `C3-building-service` | services.json#elevator | elevator | — | {"end_use": "elevator", "fractions": {"latent": 0.0, "lost": 0.0, "radiant": 0.5}, "metho… | add |
| rec-01231 | `C3-building-service` | services.json#exterior_lighting | exterior_lighting | — | {"control": "AstronomicalClock", "design_level_W": 17809.0, "end_use": "exterior_lighting… | add |
| rec-01218 | `C3-building-service-schedule` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | OfficeMedium HVACOperationSchd | Schedule:Compact BLDG_ELEVATORS | add |
| rec-01227 | `C5-water-use-gains` | whole-building-md-office | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-01228 | `C5-water-use-gains` | whole-building-md-office | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-01229 | `C5-water-use-gains` | whole-building-md-office | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-01233 | `C10-building-wwr` | constructions | fenestration_defaults | — | {"all": {"E": 0.3301, "N": 0.3301, "S": 0.3301, "W": 0.3301, "roof": 0.0}, "conditioned":… | add |
| rec-01232 | `C10-program-wwr` | whole-building-md-office | fenestration | — | {"E": 0.4768, "N": 0.4768, "S": 0.4768, "W": 0.4768, "roof": null} | add |

## doe-ref-pre-1980 · MidriseApartment

| Row | Class | Target | Field | Atlas | DOE | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| rec-01874 | `midrise-apartment` | — | all | — | not compared | leave (`R-NOT-COMPARED`) |

## doe-ref-pre-1980 · Outpatient

| Row | Class | Target | Field | Atlas | DOE | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| rec-01239 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (gas) | — | Schedule:Compact BLDG_EQUIP_SCH | replace |
| rec-01240 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | — | Schedule:Compact BLDG_EQUIP_SCH | replace |
| rec-01241 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (lighting) | — | Schedule:Compact BLDG_LIGHT_SCH | replace |
| rec-01242 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | — | Schedule:Compact BLDG_OCC_SCH | replace |
| rec-01247 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | Outpatient Radiology Equip | Schedule:Compact RADIOLOGY_EQUIP_SCH | replace |
| rec-01243 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (hot-water flow) | OutPatientHealthCare BLDG_SWH_SCH_Pre2004 | Schedule:Compact BLDG_SWH_SCH | replace |
| rec-01244 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (cooling setpoint) | — | Schedule:Compact CLGSETP_SCH | replace |
| rec-01245 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (heating setpoint) | — | Schedule:Compact HTGSETP_SCH | replace |
| rec-01237 | `A3-vintage-variant` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | OutPatientHealthCare BLDG_OA_SCH_Pre2004 | Schedule:Compact AHU-1_Fan_Sch | replace |
| rec-01391 | `A4-retag` | janitor | program Utility_Outpatient | Janitor | {"electric_equipment": 1.08, "gas_equipment": 0.0, "lighting": 10.8, "occupancy": 0.0} | add |
| rec-01269 | `A5-existing-density` | toilet | electric_equipment | 7.53474 | 4.31 | keep (`R-EXISTING-DENSITY`) |
| rec-01249 | `A7-rounding` | bio-hazard | lighting | 10.7639 | 10.8 | keep (`R-ROUNDING`) |
| rec-01250 | `A7-rounding` | bio-hazard | electric_equipment | 1.07639 | 1.08 | keep (`R-ROUNDING`) |
| rec-01254 | `A7-rounding` | office | occupancy | 0.0500522 | 0.05 | keep (`R-ROUNDING`) |
| rec-01255 | `A7-rounding` | office | lighting | 19.375 | 19.4 | keep (`R-ROUNDING`) |
| rec-01257 | `A7-rounding` | dressing-room | occupancy | 0.0500522 | 0.05 | keep (`R-ROUNDING`) |
| rec-01258 | `A7-rounding` | dressing-room | lighting | 19.375 | 19.4 | keep (`R-ROUNDING`) |
| rec-01262 | `A7-rounding` | hall | electric_equipment | 4.30556 | 4.31 | keep (`R-ROUNDING`) |
| rec-01264 | `A7-rounding` | it-room | occupancy | 0.0500522 | 0.05 | keep (`R-ROUNDING`) |
| rec-01265 | `A7-rounding` | it-room | lighting | 19.375 | 19.4 | keep (`R-ROUNDING`) |
| rec-01267 | `A7-rounding` | lobby | lighting | 10.7639 | 10.8 | keep (`R-ROUNDING`) |
| rec-01275 | `A7-rounding` | med-gas | lighting | 10.7639 | 10.8 | keep (`R-ROUNDING`) |
| rec-01276 | `A7-rounding` | med-gas | electric_equipment | 1.07639 | 1.08 | keep (`R-ROUNDING`) |
| rec-01279 | `A7-rounding` | janitor | lighting | 10.7639 | 10.8 | keep (`R-ROUNDING`) |
| rec-01281 | `A7-rounding` | pacu | lighting | 24.757 | 24.7 | keep (`R-ROUNDING`) |
| rec-01283 | `A7-rounding` | pre-op | lighting | 15.0695 | 15.1 | keep (`R-ROUNDING`) |
| rec-01285 | `A7-rounding` | procedure-room | lighting | 17.2223 | 17.2 | keep (`R-ROUNDING`) |
| rec-01287 | `A7-rounding` | reception | lighting | 10.7639 | 10.8 | keep (`R-ROUNDING`) |
| rec-01290 | `A7-rounding` | hall-infil | electric_equipment | 4.30556 | 4.31 | keep (`R-ROUNDING`) |
| rec-01292 | `A7-rounding` | conference | lighting | 19.375 | 19.4 | keep (`R-ROUNDING`) |
| rec-01294 | `A7-rounding` | exam | lighting | 17.2223 | 17.2 | keep (`R-ROUNDING`) |
| rec-01296 | `A7-rounding` | xray | electric_equipment | 13.9931 | 14.0206 | keep (`R-ROUNDING`) |
| rec-01298 | `A7-rounding` | physical-therapy | lighting | 17.2223 | 17.2 | keep (`R-ROUNDING`) |
| rec-01358 | `A10-infiltration-method` | constructions | infiltration.methods.doe_design_flow | fixed_source_reference_natural_ach | [["airchanges/hour", 1.0, "INFIL_SCH"], ["flow/exteriorwallarea", 0.001133, "INFIL_SCH"]] | add |
| rec-01246 | `A10-infiltration-schedule` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (infiltration) | OutPatientHealthCare BLDG_OA_SCH_Pre2004 | Schedule:Compact INFIL_SCH | add |
| rec-01302 | `A12-heat-fraction` | janitor | electric_equipment.thermal_effects.radiant | 0.3 | 0.5 | replace |
| rec-01303 | `A12-heat-fraction` | janitor | electric_equipment.thermal_effects.lost | 0.7 | 0 | replace |
| rec-01359 | `B2-additional-lighting` | anesthesia | additional_lighting | — | 0 | fill |
| rec-01360 | `B2-additional-lighting` | bio-hazard | additional_lighting | — | 0 | fill |
| rec-01361 | `B2-additional-lighting` | cafe | additional_lighting | — | 0 | fill |
| rec-01362 | `B2-additional-lighting` | clean-work | additional_lighting | — | 0 | fill |
| rec-01363 | `B2-additional-lighting` | conference | additional_lighting | — | 0 | fill |
| rec-01364 | `B2-additional-lighting` | dressing-room | additional_lighting | — | 0 | fill |
| rec-01365 | `B2-additional-lighting` | elec-mech-room | additional_lighting | — | 0 | fill |
| rec-01366 | `B2-additional-lighting` | elevator-pump-room | additional_lighting | — | 0 | fill |
| rec-01367 | `B2-additional-lighting` | exam | additional_lighting | — | 0 | fill |
| rec-01368 | `B2-additional-lighting` | hall-infil | additional_lighting | — | 0 | fill |
| rec-01369 | `B2-additional-lighting` | hall | additional_lighting | — | 0 | fill |
| rec-01370 | `B2-additional-lighting` | it-room | additional_lighting | — | 0 | fill |
| rec-01371 | `B2-additional-lighting` | janitor | additional_lighting | — | 0 | fill |
| rec-01372 | `B2-additional-lighting` | lobby | additional_lighting | — | 0 | fill |
| rec-01373 | `B2-additional-lighting` | locker-room | additional_lighting | — | 0 | fill |
| rec-01374 | `B2-additional-lighting` | lounge | additional_lighting | — | 0 | fill |
| rec-01375 | `B2-additional-lighting` | med-gas | additional_lighting | — | 0 | fill |
| rec-01376 | `B2-additional-lighting` | mri-control | additional_lighting | — | 0 | fill |
| rec-01377 | `B2-additional-lighting` | mri | additional_lighting | — | 0 | fill |
| rec-01378 | `B2-additional-lighting` | nurse-station | additional_lighting | — | 0 | fill |
| rec-01379 | `B2-additional-lighting` | office | additional_lighting | — | 0 | fill |
| rec-01380 | `B2-additional-lighting` | or | additional_lighting | — | 0 | fill |
| rec-01381 | `B2-additional-lighting` | pacu | additional_lighting | — | 0 | fill |
| rec-01382 | `B2-additional-lighting` | physical-therapy | additional_lighting | — | 0 | fill |
| rec-01383 | `B2-additional-lighting` | pre-op | additional_lighting | — | 0 | fill |
| rec-01384 | `B2-additional-lighting` | procedure-room | additional_lighting | — | 0 | fill |
| rec-01385 | `B2-additional-lighting` | reception | additional_lighting | — | 0 | fill |
| rec-01386 | `B2-additional-lighting` | soil-work | additional_lighting | — | 0 | fill |
| rec-01387 | `B2-additional-lighting` | stair | additional_lighting | — | 0 | fill |
| rec-01388 | `B2-additional-lighting` | toilet | additional_lighting | — | 0 | fill |
| rec-01389 | `B2-additional-lighting` | undeveloped | additional_lighting | — | 0 | fill |
| rec-01390 | `B2-additional-lighting` | xray | additional_lighting | — | 0 | fill |
| rec-01248 | `B7-filling-sourced` | anesthesia | gas_equipment | 0 | 0 | fill |
| rec-01251 | `B7-filling-sourced` | bio-hazard | gas_equipment | 0 | 0 | fill |
| rec-01252 | `B7-filling-sourced` | cafe | gas_equipment | 0 | 0 | fill |
| rec-01253 | `B7-filling-sourced` | clean-work | gas_equipment | 0 | 0 | fill |
| rec-01256 | `B7-filling-sourced` | office | gas_equipment | 0 | 0 | fill |
| rec-01259 | `B7-filling-sourced` | dressing-room | gas_equipment | 0 | 0 | fill |
| rec-01260 | `B7-filling-sourced` | elec-mech-room | gas_equipment | 0 | 0 | fill |
| rec-01261 | `B7-filling-sourced` | elevator-pump-room | gas_equipment | 0 | 0 | fill |
| rec-01263 | `B7-filling-sourced` | hall | gas_equipment | 0 | 0 | fill |
| rec-01266 | `B7-filling-sourced` | it-room | gas_equipment | 0 | 0 | fill |
| rec-01268 | `B7-filling-sourced` | lobby | gas_equipment | 0 | 0 | fill |
| rec-01270 | `B7-filling-sourced` | toilet | gas_equipment | 0 | 0 | fill |
| rec-01271 | `B7-filling-sourced` | locker-room | gas_equipment | 0 | 0 | fill |
| rec-01272 | `B7-filling-sourced` | lounge | gas_equipment | 0 | 0 | fill |
| rec-01273 | `B7-filling-sourced` | mri-control | gas_equipment | 0 | 0 | fill |
| rec-01274 | `B7-filling-sourced` | mri | gas_equipment | 0 | 0 | fill |
| rec-01277 | `B7-filling-sourced` | med-gas | gas_equipment | 0 | 0 | fill |
| rec-01278 | `B7-filling-sourced` | nurse-station | gas_equipment | 0 | 0 | fill |
| rec-01280 | `B7-filling-sourced` | janitor | gas_equipment | 0 | 0 | fill |
| rec-01282 | `B7-filling-sourced` | pacu | gas_equipment | 0 | 0 | fill |
| rec-01284 | `B7-filling-sourced` | pre-op | gas_equipment | 0 | 0 | fill |
| rec-01286 | `B7-filling-sourced` | procedure-room | gas_equipment | 0 | 0 | fill |
| rec-01288 | `B7-filling-sourced` | reception | gas_equipment | 0 | 0 | fill |
| rec-01289 | `B7-filling-sourced` | soil-work | gas_equipment | 0 | 0 | fill |
| rec-01291 | `B7-filling-sourced` | hall-infil | gas_equipment | 0 | 0 | fill |
| rec-01293 | `B7-filling-sourced` | conference | gas_equipment | 0 | 0 | fill |
| rec-01295 | `B7-filling-sourced` | exam | gas_equipment | 0 | 0 | fill |
| rec-01297 | `B7-filling-sourced` | xray | gas_equipment | 0 | 0 | fill |
| rec-01299 | `B7-filling-sourced` | physical-therapy | gas_equipment | 0 | 0 | fill |
| rec-01300 | `B7-filling-sourced` | undeveloped | gas_equipment | 0 | 0 | fill |
| rec-01301 | `B7-filling-sourced` | stair | gas_equipment | 0 | 0 | fill |
| rec-01319 | `C3-building-service` | services.json#elevator | elevator | — | {"end_use": "elevator", "fractions": {"latent": 0.0, "lost": 0.9, "radiant": 0.1}, "metho… | add |
| rec-01320 | `C3-building-service` | services.json#exhaust_fan | exhaust_fan | — | {"end_use": "exhaust_fan", "fractions": {"latent": 0.0, "lost": 1.0, "radiant": 0.0}, "me… | add |
| rec-01321 | `C3-building-service` | services.json#exhaust_fan | exhaust_fan | — | {"end_use": "exhaust_fan", "fractions": {"latent": 0.0, "lost": 1.0, "radiant": 0.0}, "me… | add |
| rec-01322 | `C3-building-service` | services.json#exhaust_fan | exhaust_fan | — | {"end_use": "exhaust_fan", "fractions": {"latent": 0.0, "lost": 1.0, "radiant": 0.0}, "me… | add |
| rec-01323 | `C3-building-service` | services.json#exhaust_fan | exhaust_fan | — | {"end_use": "exhaust_fan", "fractions": {"latent": 0.0, "lost": 1.0, "radiant": 0.0}, "me… | add |
| rec-01324 | `C3-building-service` | services.json#exhaust_fan | exhaust_fan | — | {"end_use": "exhaust_fan", "fractions": {"latent": 0.0, "lost": 1.0, "radiant": 0.0}, "me… | add |
| rec-01325 | `C3-building-service` | services.json#exhaust_fan | exhaust_fan | — | {"end_use": "exhaust_fan", "fractions": {"latent": 0.0, "lost": 1.0, "radiant": 0.0}, "me… | add |
| rec-01326 | `C3-building-service` | services.json#exhaust_fan | exhaust_fan | — | {"end_use": "exhaust_fan", "fractions": {"latent": 0.0, "lost": 1.0, "radiant": 0.0}, "me… | add |
| rec-01327 | `C3-building-service` | services.json#exhaust_fan | exhaust_fan | — | {"end_use": "exhaust_fan", "fractions": {"latent": 0.0, "lost": 1.0, "radiant": 0.0}, "me… | add |
| rec-01328 | `C3-building-service` | services.json#exhaust_fan | exhaust_fan | — | {"end_use": "exhaust_fan", "fractions": {"latent": 0.0, "lost": 1.0, "radiant": 0.0}, "me… | add |
| rec-01329 | `C3-building-service` | services.json#exhaust_fan | exhaust_fan | — | {"end_use": "exhaust_fan", "fractions": {"latent": 0.0, "lost": 1.0, "radiant": 0.0}, "me… | add |
| rec-01330 | `C3-building-service` | services.json#exterior_lighting | exterior_lighting | — | {"control": "AstronomicalClock", "design_level_W": 16951.0, "end_use": "exterior_lighting… | add |
| rec-01238 | `C3-building-service-schedule` | — | schedule (plug) | — | Schedule:Compact BLDG_ELEVATORS | add |
| rec-01304 | `C5-water-use-gains` | anesthesia | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-01305 | `C5-water-use-gains` | mri-control | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-01306 | `C5-water-use-gains` | mri | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-01307 | `C5-water-use-gains` | or | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-01308 | `C5-water-use-gains` | or | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-01309 | `C5-water-use-gains` | or | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-01310 | `C5-water-use-gains` | pacu | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-01311 | `C5-water-use-gains` | pre-op | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-01312 | `C5-water-use-gains` | pre-op | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-01313 | `C5-water-use-gains` | procedure-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-01314 | `C5-water-use-gains` | pacu | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-01315 | `C5-water-use-gains` | pacu | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-01316 | `C5-water-use-gains` | xray | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-01317 | `C5-water-use-gains` | physical-therapy | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-01318 | `C5-water-use-gains` | physical-therapy | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-01331 | `C6-humidity-setpoint` | or | humidity setpoints | — | {"dehumidifying": 60.0, "humidifying": 40.0, "zone": "Floor 1 Operating Room 1"} | add |
| rec-01357 | `C10-building-wwr` | constructions | fenestration_defaults | — | {"all": {"E": 0.1914, "N": 0.2052, "S": 0.2408, "W": 0.1288, "roof": 0.0}, "conditioned":… | add |
| rec-01332 | `C10-program-wwr` | anesthesia | fenestration | — | {"E": null, "N": null, "S": 0.2667, "W": null, "roof": null} | add |
| rec-01333 | `C10-program-wwr` | cafe | fenestration | — | {"E": null, "N": null, "S": 0.48, "W": null, "roof": null} | add |
| rec-01334 | `C10-program-wwr` | conference | fenestration | — | {"E": 0.2, "N": null, "S": 0.2571, "W": null, "roof": null} | add |
| rec-01335 | `C10-program-wwr` | dressing-room | fenestration | — | {"E": null, "N": 0.2778, "S": null, "W": null, "roof": 0.0} | add |
| rec-01336 | `C10-program-wwr` | elec-mech-room | fenestration | — | {"E": 0.2, "N": null, "S": null, "W": null, "roof": 0.0} | add |
| rec-01337 | `C10-program-wwr` | elevator-pump-room | fenestration | — | {"E": null, "N": 0.0, "S": null, "W": 0.0, "roof": null} | add |
| rec-01338 | `C10-program-wwr` | exam | fenestration | — | {"E": 0.256, "N": 0.2826, "S": 0.2492, "W": 0.24, "roof": 0.0} | add |
| rec-01339 | `C10-program-wwr` | hall-infil | fenestration | — | {"E": 0.1067, "N": 0.0, "S": null, "W": 0.0, "roof": 0.0} | add |
| rec-01340 | `C10-program-wwr` | hall | fenestration | — | {"E": null, "N": 0.0, "S": 0.0727, "W": 0.0, "roof": 0.0} | add |
| rec-01341 | `C10-program-wwr` | janitor | fenestration | — | {"E": null, "N": 0.1552, "S": null, "W": 0.0, "roof": 0.0} | add |
| rec-01342 | `C10-program-wwr` | lobby | fenestration | — | {"E": null, "N": null, "S": null, "W": 0.4364, "roof": null} | add |
| rec-01343 | `C10-program-wwr` | locker-room | fenestration | — | {"E": null, "N": 0.2727, "S": null, "W": null, "roof": 0.0} | add |
| rec-01344 | `C10-program-wwr` | lounge | fenestration | — | {"E": null, "N": 0.2609, "S": null, "W": null, "roof": 0.0} | add |
| rec-01345 | `C10-program-wwr` | med-gas | fenestration | — | {"E": 0.0, "N": 0.0, "S": null, "W": null, "roof": 0.0} | add |
| rec-01346 | `C10-program-wwr` | mri-control | fenestration | — | {"E": null, "N": 0.0, "S": null, "W": null, "roof": null} | add |
| rec-01347 | `C10-program-wwr` | office | fenestration | — | {"E": 0.237, "N": 0.27, "S": 0.1143, "W": null, "roof": 0.0} | add |
| rec-01348 | `C10-program-wwr` | or | fenestration | — | {"E": 0.2553, "N": null, "S": 0.24, "W": null, "roof": null} | add |
| rec-01349 | `C10-program-wwr` | pacu | fenestration | — | {"E": null, "N": null, "S": 0.2057, "W": 0.2, "roof": null} | add |
| rec-01350 | `C10-program-wwr` | physical-therapy | fenestration | — | {"E": 0.36, "N": null, "S": 0.3692, "W": null, "roof": 0.0} | add |
| rec-01351 | `C10-program-wwr` | pre-op | fenestration | — | {"E": null, "N": null, "S": null, "W": 0.0, "roof": null} | add |
| rec-01352 | `C10-program-wwr` | procedure-room | fenestration | — | {"E": null, "N": 0.3158, "S": null, "W": null, "roof": null} | add |
| rec-01353 | `C10-program-wwr` | reception | fenestration | — | {"E": null, "N": null, "S": 0.313, "W": 0.45, "roof": null} | add |
| rec-01354 | `C10-program-wwr` | stair | fenestration | — | {"E": 0.0178, "N": 0.1677, "S": 0.0174, "W": 0.0, "roof": 0.0} | add |
| rec-01355 | `C10-program-wwr` | toilet | fenestration | — | {"E": null, "N": 0.25, "S": null, "W": 0.0, "roof": 0.0} | add |
| rec-01356 | `C10-program-wwr` | undeveloped | fenestration | — | {"E": null, "N": null, "S": 0.322, "W": 0.3391, "roof": 0.0} | add |

## doe-ref-pre-1980 · PrimarySchool

| Row | Class | Target | Field | Atlas | DOE | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| rec-01392 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | PrimarySchool Bldg Equip | Schedule:Compact BLDG_EQUIP_SCH | replace |
| rec-01393 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (lighting) | — | Schedule:Compact BLDG_LIGHT_SCH | replace |
| rec-01394 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | PrimarySchool Bldg Occ | Schedule:Compact BLDG_OCC_SCH | replace |
| rec-01396 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | PrimarySchool Gym Occ | Schedule:Compact BLDG_OCC_SCH_Gym | replace |
| rec-01398 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (hot-water flow) | SchoolPrimary BLDG_SWH_SCH | Schedule:Compact BLDG_SWH_SCH | replace |
| rec-01399 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (cooling setpoint) | PrimarySchool ClgSetp | Schedule:Compact CLGSETP_SCH | replace |
| rec-01400 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (heating setpoint) | PrimarySchool HtgSetp | Schedule:Compact HTGSETP_SCH | replace |
| rec-01395 | `A4-assignment` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | PrimarySchool Cafeteria Occ | Schedule:Compact BLDG_OCC_SCH_Cafeteria | replace |
| rec-01397 | `A4-assignment` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | No attributed fixture draw (reporting equivalent) | Schedule:Compact BLDG_OCC_SCH_Offices | replace |
| rec-01402 | `A4-assignment` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | PrimarySchool Kitchen Equip | Schedule:Compact KITCHEN_ELEC_EQUIP_SCH | replace |
| rec-01404 | `A4-assignment` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (gas) | — | Schedule:Compact KITCHEN_GAS_EQUIP_SCH | replace |
| rec-01462 | `A4-retag` | classroom | program ComputerRoom_PrimarySchool | Classroom | {"electric_equipment": 20.0, "gas_equipment": 0.0, "lighting": 21.52, "occupancy": 0.3003} | add |
| rec-01463 | `A4-retag` | classroom | program Library_PrimarySchool | Classroom | {"electric_equipment": 15.0, "gas_equipment": 0.0, "lighting": 22.75, "occupancy": 0.2298… | add |
| rec-01411 | `A5-existing-density` | corridor | lighting | 9.68752 | 21.52 | keep (`R-EXISTING-DENSITY`) |
| rec-01420 | `A5-existing-density` | mechanical | occupancy | 0.0100104 | 0 | keep (`R-EXISTING-DENSITY`) |
| rec-01405 | `A7-rounding` | restroom | electric_equipment | 3.98265 | 4 | keep (`R-ROUNDING`) |
| rec-01407 | `A7-rounding` | cafeteria | occupancy | 0.71763 | 0.719424 | keep (`R-ROUNDING`) |
| rec-01409 | `A7-rounding` | classroom | electric_equipment | 14.9618 | 15 | keep (`R-ROUNDING`) |
| rec-01412 | `A7-rounding` | corridor | electric_equipment | 3.98265 | 4 | keep (`R-ROUNDING`) |
| rec-01414 | `A7-rounding` | gym | lighting | 11.5174 | 11.47 | keep (`R-ROUNDING`) |
| rec-01415 | `A7-rounding` | gym | electric_equipment | 4.9514 | 5 | keep (`R-ROUNDING`) |
| rec-01417 | `A7-rounding` | kitchen | lighting | 17.2223 | 17.2 | keep (`R-ROUNDING`) |
| rec-01418 | `A7-rounding` | lobby | electric_equipment | 3.98265 | 4 | keep (`R-ROUNDING`) |
| rec-01421 | `A7-rounding` | mechanical | lighting | 8.28821 | 8.26 | keep (`R-ROUNDING`) |
| rec-01422 | `A7-rounding` | mechanical | electric_equipment | 3.98265 | 4 | keep (`R-ROUNDING`) |
| rec-01424 | `A7-rounding` | office | occupancy | 0.0500522 | 0.05 | keep (`R-ROUNDING`) |
| rec-01425 | `A7-rounding` | office | electric_equipment | 10.7639 | 10.8 | keep (`R-ROUNDING`) |
| rec-01452 | `A10-infiltration-method` | constructions | infiltration.methods.doe_design_flow | fixed_source_reference_natural_ach | [["flow/exteriorwallarea", 0.001133, "INFIL_SCH"]] | add |
| rec-01401 | `A10-infiltration-schedule` | — | schedule (infiltration) | — | Schedule:Compact INFIL_SCH | add |
| rec-01427 | `B1-hot-water` | cafeteria | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-01428 | `B1-hot-water` | classroom | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-01429 | `B1-hot-water` | corridor | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-01430 | `B1-hot-water` | gym | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-01431 | `B1-hot-water` | lobby | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-01432 | `B1-hot-water` | mechanical | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-01433 | `B1-hot-water` | office | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-01453 | `B2-additional-lighting` | cafeteria | additional_lighting | — | 0 | fill |
| rec-01454 | `B2-additional-lighting` | classroom | additional_lighting | — | one lighting object per zone | leave (`R-NO-LIGHTING-SPLIT`) |
| rec-01455 | `B2-additional-lighting` | corridor | additional_lighting | — | one lighting object per zone | leave (`R-NO-LIGHTING-SPLIT`) |
| rec-01456 | `B2-additional-lighting` | gym | additional_lighting | — | 0 | fill |
| rec-01457 | `B2-additional-lighting` | kitchen | additional_lighting | — | 0 | fill |
| rec-01458 | `B2-additional-lighting` | lobby | additional_lighting | — | 0 | fill |
| rec-01459 | `B2-additional-lighting` | mechanical | additional_lighting | — | 0 | fill |
| rec-01460 | `B2-additional-lighting` | office | additional_lighting | — | 0 | fill |
| rec-01461 | `B2-additional-lighting` | restroom | additional_lighting | — | 0 | fill |
| rec-01406 | `B7-filling-sourced` | restroom | gas_equipment | 0 | 0 | fill |
| rec-01408 | `B7-filling-sourced` | cafeteria | gas_equipment | 0 | 0 | fill |
| rec-01410 | `B7-filling-sourced` | classroom | gas_equipment | 0 | 0 | fill |
| rec-01413 | `B7-filling-sourced` | corridor | gas_equipment | 0 | 0 | fill |
| rec-01416 | `B7-filling-sourced` | gym | gas_equipment | 0 | 0 | fill |
| rec-01419 | `B7-filling-sourced` | lobby | gas_equipment | 0 | 0 | fill |
| rec-01423 | `B7-filling-sourced` | mechanical | gas_equipment | 0 | 0 | fill |
| rec-01426 | `B7-filling-sourced` | office | gas_equipment | 0 | 0 | fill |
| rec-01436 | `C3-building-service` | services.json#exhaust_fan | exhaust_fan | — | {"end_use": "exhaust_fan", "fractions": {"latent": 0.0, "lost": 1.0, "radiant": 0.0}, "me… | add |
| rec-01437 | `C3-building-service` | services.json#exterior_lighting | exterior_lighting | — | {"control": "AstronomicalClock", "design_level_W": 10519.0, "end_use": "exterior_lighting… | add |
| rec-01403 | `C3-building-service-schedule` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | No attributed fixture draw (reporting equivalent) | Schedule:Compact Kitchen_Exhaust_SCH | add |
| rec-01438 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 734.0, "end_use": "refrigeration_case", "fa… | add |
| rec-01439 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 734.0, "end_use": "refrigeration_case", "fa… | add |
| rec-01440 | `C4-refrigeration` | services.json#refrigeration_rack | refrigeration_rack | — | {"condenser_fan_W": 350.0, "cop": 1.5, "end_use": "refrigeration_rack", "heat_rejection":… | add |
| rec-01441 | `C4-refrigeration` | services.json#refrigeration_rack | refrigeration_rack | — | {"condenser_fan_W": 350.0, "cop": 3.0, "end_use": "refrigeration_rack", "heat_rejection":… | add |
| rec-01434 | `C5-water-use-gains` | restroom | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-01435 | `C5-water-use-gains` | kitchen | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction": 0.… | add |
| rec-01451 | `C10-building-wwr` | constructions | fenestration_defaults | — | {"all": {"E": 0.35, "N": 0.35, "S": 0.35, "W": 0.35, "roof": 0.0}, "conditioned": {"E": 0… | add |
| rec-01442 | `C10-program-wwr` | cafeteria | fenestration | — | {"E": 0.35, "N": 0.35, "S": null, "W": null, "roof": 0.0} | add |
| rec-01443 | `C10-program-wwr` | classroom | fenestration | — | {"E": null, "N": 0.35, "S": 0.35, "W": 0.35, "roof": 0.0} | add |
| rec-01444 | `C10-program-wwr` | corridor | fenestration | — | {"E": null, "N": null, "S": null, "W": 0.35, "roof": 0.0} | add |
| rec-01445 | `C10-program-wwr` | gym | fenestration | — | {"E": 0.35, "N": null, "S": null, "W": null, "roof": 0.0} | add |
| rec-01446 | `C10-program-wwr` | kitchen | fenestration | — | {"E": 0.35, "N": null, "S": null, "W": null, "roof": 0.0} | add |
| rec-01447 | `C10-program-wwr` | lobby | fenestration | — | {"E": null, "N": null, "S": 0.35, "W": null, "roof": 0.0} | add |
| rec-01448 | `C10-program-wwr` | mechanical | fenestration | — | {"E": null, "N": null, "S": null, "W": null, "roof": 0.0} | add |
| rec-01449 | `C10-program-wwr` | office | fenestration | — | {"E": 0.35, "N": null, "S": 0.35, "W": null, "roof": 0.0} | add |
| rec-01450 | `C10-program-wwr` | restroom | fenestration | — | {"E": null, "N": null, "S": null, "W": 0.35, "roof": 0.0} | add |

## doe-ref-pre-1980 · QuickServiceRestaurant

| Row | Class | Target | Field | Atlas | DOE | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| rec-01464 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | QuickServiceRestaurant Bldg Occ | Schedule:Compact BLDG_OCC_SCH | replace |
| rec-01465 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (hot-water flow) | QuickServiceRestaurant Bldg Swh | Schedule:Compact BLDG_SWH_SCH | replace |
| rec-01467 | `A5-existing-density` | dining | occupancy | 0.753474 | 0.719424 | keep (`R-EXISTING-DENSITY`) |
| rec-01480 | `A10-infiltration-method` | constructions | infiltration.methods.doe_design_flow | fixed_source_reference_natural_ach | [["flow/exteriorarea", 0.001133, "INFIL_HALF_ON_SCH"]] | add |
| rec-01466 | `A10-infiltration-schedule` | — | schedule (infiltration) | — | Schedule:Compact INFIL_HALF_ON_SCH | add |
| rec-01469 | `A12-heat-fraction` | dining | lighting.thermal_effects.radiant | 0.37 | 0.7 | replace |
| rec-01481 | `B2-additional-lighting` | dining | additional_lighting | — | 0 | fill |
| rec-01482 | `B2-additional-lighting` | kitchen | additional_lighting | — | 0 | fill |
| rec-01468 | `B7-filling-sourced` | dining | gas_equipment | 0 | 0 | fill |
| rec-01471 | `C3-building-service` | services.json#exhaust_fan | exhaust_fan | — | {"end_use": "exhaust_fan", "fractions": {"latent": 0.0, "lost": 1.0, "radiant": 0.0}, "me… | add |
| rec-01472 | `C3-building-service` | services.json#exterior_lighting | exterior_lighting | — | {"control": "AstronomicalClock", "design_level_W": 2963.0, "end_use": "exterior_lighting"… | add |
| rec-01473 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 688.0, "end_use": "refrigeration_case", "fa… | add |
| rec-01474 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 734.0, "end_use": "refrigeration_case", "fa… | add |
| rec-01475 | `C4-refrigeration` | services.json#refrigeration_rack | refrigeration_rack | — | {"condenser_fan_W": 330.0, "cop": 1.5, "end_use": "refrigeration_rack", "heat_rejection":… | add |
| rec-01476 | `C4-refrigeration` | services.json#refrigeration_rack | refrigeration_rack | — | {"condenser_fan_W": 330.0, "cop": 3.0, "end_use": "refrigeration_rack", "heat_rejection":… | add |
| rec-01470 | `C5-water-use-gains` | kitchen | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction": 0.… | add |
| rec-01479 | `C10-building-wwr` | constructions | fenestration_defaults | — | {"all": {"E": 0.14, "N": 0.0, "S": 0.28, "W": 0.14, "roof": 0.0}, "conditioned": {"E": 0.… | add |
| rec-01477 | `C10-program-wwr` | dining | fenestration | — | {"E": 0.28, "N": null, "S": 0.28, "W": 0.28, "roof": 0.0} | add |
| rec-01478 | `C10-program-wwr` | kitchen | fenestration | — | {"E": 0.0, "N": 0.0, "S": null, "W": 0.0, "roof": 0.0} | add |

## doe-ref-pre-1980 · RetailStandalone

| Row | Class | Target | Field | Atlas | DOE | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| rec-01726 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | — | Schedule:Compact BLDG_EQUIP_SCH | replace |
| rec-01727 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (lighting) | — | Schedule:Compact BLDG_LIGHT_SCH | replace |
| rec-01728 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | — | Schedule:Compact BLDG_OCC_SCH | replace |
| rec-01729 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (cooling setpoint) | Retail ClgSetp | Schedule:Compact CLGSETP_SCH | replace |
| rec-01730 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (heating setpoint) | — | Schedule:Compact HTGSETP_SCH | replace |
| rec-01733 | `A7-rounding` | back-space | occupancy | 0.0358438 | 0.035881 | keep (`R-ROUNDING`) |
| rec-01734 | `A7-rounding` | back-space | lighting | 12.5938 | 12.55 | keep (`R-ROUNDING`) |
| rec-01745 | `A10-infiltration-method` | constructions | infiltration.methods.doe_design_flow | fixed_source_reference_natural_ach | [["airchanges/hour", 1.0, "INFIL_FRONT_SCH"], ["flow/exteriorarea", 0.001133, "INFIL_HALF… | add |
| rec-01731 | `A10-infiltration-schedule` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (infiltration) | Always On | Schedule:Compact INFIL_FRONT_SCH | add |
| rec-01732 | `A10-infiltration-schedule` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (infiltration) | Always On | Schedule:Compact INFIL_HALF_ON_SCH | add |
| rec-01747 | `B2-additional-lighting` | back-space | additional_lighting | — | 0 | fill |
| rec-01748 | `B2-additional-lighting` | entry | additional_lighting | — | 0 | fill |
| rec-01749 | `B2-additional-lighting` | point-of-sale | additional_lighting | — | 0 | fill |
| rec-01750 | `B2-additional-lighting` | retail | additional_lighting | — | 0 | fill |
| rec-01735 | `B7-filling-sourced` | back-space | gas_equipment | 0 | 0 | fill |
| rec-01736 | `B7-filling-sourced` | retail | gas_equipment | 0 | 0 | fill |
| rec-01737 | `B7-filling-sourced` | entry | gas_equipment | 0 | 0 | fill |
| rec-01738 | `B7-filling-sourced` | point-of-sale | gas_equipment | 0 | 0 | fill |
| rec-01746 | `B8-internal-mass` | entry | mass_accounting.additional_mass | — | 2 | fill |
| rec-01739 | `C3-building-service` | services.json#exterior_lighting | exterior_lighting | — | {"control": "AstronomicalClock", "design_level_W": 9995.0, "end_use": "exterior_lighting"… | add |
| rec-01744 | `C10-building-wwr` | constructions | fenestration_defaults | — | {"all": {"E": 0.0, "N": 0.0, "S": 0.2537, "W": 0.0, "roof": 0.0}, "conditioned": {"E": 0.… | add |
| rec-01740 | `C10-program-wwr` | back-space | fenestration | — | {"E": 0.0, "N": 0.0, "S": null, "W": 0.0, "roof": 0.0} | add |
| rec-01741 | `C10-program-wwr` | entry | fenestration | — | {"E": null, "N": null, "S": 0.3211, "W": null, "roof": 0.0} | add |
| rec-01742 | `C10-program-wwr` | point-of-sale | fenestration | — | {"E": null, "N": null, "S": 0.2484, "W": 0.0, "roof": 0.0} | add |
| rec-01743 | `C10-program-wwr` | retail | fenestration | — | {"E": 0.0, "N": null, "S": 0.2484, "W": 0.0, "roof": 0.0} | add |

## doe-ref-pre-1980 · RetailStripmall

| Row | Class | Target | Field | Atlas | DOE | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| rec-01751 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | — | Schedule:Compact BLDG_EQUIP_SCH | replace |
| rec-01752 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (lighting) | — | Schedule:Compact BLDG_LIGHT_SCH | replace |
| rec-01753 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | — | Schedule:Compact BLDG_OCC_SCH | replace |
| rec-01754 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (cooling setpoint) | — | Schedule:Compact CLGSETP_SCH | replace |
| rec-01755 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (heating setpoint) | — | Schedule:Compact HTGSETP_SCH | replace |
| rec-01757 | `A7-rounding` | strip-mall-type-1 | electric_equipment | 4.30556 | 4.3 | keep (`R-ROUNDING`) |
| rec-01759 | `A7-rounding` | strip-mall-type-3 | electric_equipment | 4.30556 | 4.3 | keep (`R-ROUNDING`) |
| rec-01761 | `A7-rounding` | strip-mall-type-2 | electric_equipment | 4.30556 | 4.3 | keep (`R-ROUNDING`) |
| rec-01768 | `A10-infiltration-method` | constructions | infiltration.methods.doe_design_flow | fixed_source_reference_natural_ach | [["flow/exteriorarea", 0.001133, "INFIL_HALF_ON_SCH"]] | add |
| rec-01756 | `A10-infiltration-schedule` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (infiltration) | — | Schedule:Compact INFIL_HALF_ON_SCH | add |
| rec-01769 | `B2-additional-lighting` | strip-mall-type-1 | additional_lighting | — | 0 | fill |
| rec-01770 | `B2-additional-lighting` | strip-mall-type-2 | additional_lighting | — | 0 | fill |
| rec-01771 | `B2-additional-lighting` | strip-mall-type-3 | additional_lighting | — | 0 | fill |
| rec-01758 | `B7-filling-sourced` | strip-mall-type-1 | gas_equipment | 0 | 0 | fill |
| rec-01760 | `B7-filling-sourced` | strip-mall-type-3 | gas_equipment | 0 | 0 | fill |
| rec-01762 | `B7-filling-sourced` | strip-mall-type-2 | gas_equipment | 0 | 0 | fill |
| rec-01763 | `C3-building-service` | services.json#exterior_lighting | exterior_lighting | — | {"control": "AstronomicalClock", "design_level_W": 13499.0, "end_use": "exterior_lighting… | add |
| rec-01767 | `C10-building-wwr` | constructions | fenestration_defaults | — | {"all": {"E": 0.0, "N": 0.0, "S": 0.2624, "W": 0.0, "roof": 0.0}, "conditioned": {"E": 0.… | add |
| rec-01764 | `C10-program-wwr` | strip-mall-type-1 | fenestration | — | {"E": null, "N": 0.0, "S": 0.2628, "W": 0.0, "roof": 0.0} | add |
| rec-01765 | `C10-program-wwr` | strip-mall-type-2 | fenestration | — | {"E": null, "N": 0.0, "S": 0.2623, "W": null, "roof": 0.0} | add |
| rec-01766 | `C10-program-wwr` | strip-mall-type-3 | fenestration | — | {"E": 0.0, "N": 0.0, "S": 0.2623, "W": null, "roof": 0.0} | add |

## doe-ref-pre-1980 · SecondarySchool

| Row | Class | Target | Field | Atlas | DOE | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| rec-01487 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | — | Schedule:Compact BLDG_EQUIP_SCH | replace |
| rec-01488 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (lighting) | — | Schedule:Compact BLDG_LIGHT_SCH | replace |
| rec-01489 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | — | Schedule:Compact BLDG_OCC_SCH | replace |
| rec-01490 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | SecondarySchool Auditorium Occ | Schedule:Compact BLDG_OCC_SCH_Auditorium | replace |
| rec-01493 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | SecondarySchool Gym Occ | Schedule:Compact BLDG_OCC_SCH_Gym | replace |
| rec-01494 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | SecondarySchool Office Occ | Schedule:Compact BLDG_OCC_SCH_Offices | replace |
| rec-01499 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | — | Schedule:Compact KITCHEN_ELEC_EQUIP_SCH | replace |
| rec-01501 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (gas) | — | Schedule:Compact KITCHEN_GAS_EQUIP_SCH | replace |
| rec-01495 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (hot-water flow) | SchoolSecondary BLDG_SWH_SCH | Schedule:Compact BLDG_SWH_SCH | replace |
| rec-01496 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (cooling setpoint) | — | Schedule:Compact CLGSETP_SCH | replace |
| rec-01497 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (heating setpoint) | — | Schedule:Compact HTGSETP_SCH | replace |
| rec-01502 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (hot-water flow) | — | Schedule:Compact Showers_SWH_SCH | replace |
| rec-01491 | `A4-assignment` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | — | Schedule:Compact BLDG_OCC_SCH_Cafeteria | replace |
| rec-01483 | `A4-slot-conflict` | classroom | schedule (occupancy) | — | {"BLDG_OCC_SCH": 5958.0, "BLDG_OCC_SCH_Extend": 954.0} | keep (`R-SLOT-CONFLICT`) |
| rec-01484 | `A4-slot-conflict` | lobby | schedule (cooling) | — | {"CLGSETP_SCH": 210.0, "CLGSETP_SCH_BathCorrMechKitchen": 210.0} | keep (`R-SLOT-CONFLICT`) |
| rec-01485 | `A4-slot-conflict` | lobby | schedule (heating) | — | {"HTGSETP_SCH": 210.0, "HTGSETP_SCH_BathCorrMechKitchen": 210.0} | keep (`R-SLOT-CONFLICT`) |
| rec-01492 | `A4-slot-minority` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | — | Schedule:Compact BLDG_OCC_SCH_Extend | leave (`R-SLOT-CONFLICT`) |
| rec-01506 | `A5-existing-density` | gym-audience | lighting | 11.4097 | 11.81 | keep (`R-EXISTING-DENSITY`) |
| rec-01514 | `A5-existing-density` | classroom | lighting | 21.5278 | 21.0273 | keep (`R-EXISTING-DENSITY`) |
| rec-01517 | `A5-existing-density` | corridor | occupancy | 0.100212 | 0.045714 | keep (`R-EXISTING-DENSITY`) |
| rec-01518 | `A5-existing-density` | corridor | lighting | 9.25696 | 9.64086 | keep (`R-EXISTING-DENSITY`) |
| rec-01524 | `A5-existing-density` | kitchen | occupancy | 0.166625 | 0.15 | keep (`R-EXISTING-DENSITY`) |
| rec-01503 | `A7-rounding` | auditorium | lighting | 12.0556 | 12.08 | keep (`R-ROUNDING`) |
| rec-01504 | `A7-rounding` | auditorium | electric_equipment | 4.9514 | 5 | keep (`R-ROUNDING`) |
| rec-01507 | `A7-rounding` | gym-audience | electric_equipment | 4.9514 | 5 | keep (`R-ROUNDING`) |
| rec-01509 | `A7-rounding` | restroom | lighting | 9.57988 | 9.6 | keep (`R-ROUNDING`) |
| rec-01510 | `A7-rounding` | restroom | electric_equipment | 3.98265 | 4 | keep (`R-ROUNDING`) |
| rec-01512 | `A7-rounding` | cafeteria | lighting | 14.4236 | 14.38 | keep (`R-ROUNDING`) |
| rec-01515 | `A7-rounding` | classroom | electric_equipment | 10.0104 | 10 | keep (`R-ROUNDING`) |
| rec-01519 | `A7-rounding` | corridor | electric_equipment | 3.98265 | 4 | keep (`R-ROUNDING`) |
| rec-01521 | `A7-rounding` | gym | lighting | 11.4097 | 11.38 | keep (`R-ROUNDING`) |
| rec-01522 | `A7-rounding` | gym | electric_equipment | 4.9514 | 5 | keep (`R-ROUNDING`) |
| rec-01525 | `A7-rounding` | kitchen | lighting | 16.7917 | 16.76 | keep (`R-ROUNDING`) |
| rec-01526 | `A7-rounding` | library | lighting | 16.3611 | 16.33 | keep (`R-ROUNDING`) |
| rec-01527 | `A7-rounding` | library | electric_equipment | 10.0104 | 10 | keep (`R-ROUNDING`) |
| rec-01529 | `A7-rounding` | lobby | lighting | 11.9479 | 12 | keep (`R-ROUNDING`) |
| rec-01530 | `A7-rounding` | lobby | electric_equipment | 3.98265 | 4 | keep (`R-ROUNDING`) |
| rec-01532 | `A7-rounding` | mechanical | occupancy | 0.0100104 | 0.01 | keep (`R-ROUNDING`) |
| rec-01533 | `A7-rounding` | mechanical | lighting | 8.07293 | 8.05 | keep (`R-ROUNDING`) |
| rec-01534 | `A7-rounding` | mechanical | electric_equipment | 3.98265 | 4 | keep (`R-ROUNDING`) |
| rec-01536 | `A7-rounding` | office | occupancy | 0.0500522 | 0.05 | keep (`R-ROUNDING`) |
| rec-01537 | `A7-rounding` | office | lighting | 20.1285 | 20.09 | keep (`R-ROUNDING`) |
| rec-01538 | `A7-rounding` | office | electric_equipment | 10.7639 | 10.8 | keep (`R-ROUNDING`) |
| rec-01572 | `A10-infiltration-method` | constructions | infiltration.methods.doe_design_flow | fixed_source_reference_natural_ach | [["airchanges/hour", 0.14, "INFIL_SCH"], ["flow/exteriorwallarea", 0.001133, "INFIL_SCH"]] | add |
| rec-01498 | `A10-infiltration-schedule` | — | schedule (infiltration) | — | Schedule:Compact INFIL_SCH | add |
| rec-01540 | `B1-hot-water` | auditorium | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-01541 | `B1-hot-water` | cafeteria | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-01542 | `B1-hot-water` | classroom | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-01543 | `B1-hot-water` | corridor | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-01544 | `B1-hot-water` | library | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-01545 | `B1-hot-water` | lobby | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-01546 | `B1-hot-water` | mechanical | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-01547 | `B1-hot-water` | office | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-01573 | `B2-additional-lighting` | auditorium | additional_lighting | — | 0 | fill |
| rec-01574 | `B2-additional-lighting` | cafeteria | additional_lighting | — | 0 | fill |
| rec-01575 | `B2-additional-lighting` | classroom | additional_lighting | — | one lighting object per zone | leave (`R-NO-LIGHTING-SPLIT`) |
| rec-01576 | `B2-additional-lighting` | corridor | additional_lighting | — | one lighting object per zone | leave (`R-NO-LIGHTING-SPLIT`) |
| rec-01577 | `B2-additional-lighting` | gym-audience | additional_lighting | — | one lighting object per zone | leave (`R-NO-LIGHTING-SPLIT`) |
| rec-01578 | `B2-additional-lighting` | gym | additional_lighting | — | 0 | fill |
| rec-01579 | `B2-additional-lighting` | kitchen | additional_lighting | — | 0 | fill |
| rec-01580 | `B2-additional-lighting` | library | additional_lighting | — | 0 | fill |
| rec-01581 | `B2-additional-lighting` | lobby | additional_lighting | — | 0 | fill |
| rec-01582 | `B2-additional-lighting` | mechanical | additional_lighting | — | 0 | fill |
| rec-01583 | `B2-additional-lighting` | office | additional_lighting | — | 0 | fill |
| rec-01584 | `B2-additional-lighting` | restroom | additional_lighting | — | 0 | fill |
| rec-01505 | `B7-filling-sourced` | auditorium | gas_equipment | 0 | 0 | fill |
| rec-01508 | `B7-filling-sourced` | gym-audience | gas_equipment | 0 | 0 | fill |
| rec-01511 | `B7-filling-sourced` | restroom | gas_equipment | 0 | 0 | fill |
| rec-01513 | `B7-filling-sourced` | cafeteria | gas_equipment | 0 | 0 | fill |
| rec-01516 | `B7-filling-sourced` | classroom | gas_equipment | 0 | 0 | fill |
| rec-01520 | `B7-filling-sourced` | corridor | gas_equipment | 0 | 0 | fill |
| rec-01523 | `B7-filling-sourced` | gym | gas_equipment | 0 | 0 | fill |
| rec-01528 | `B7-filling-sourced` | library | gas_equipment | 0 | 0 | fill |
| rec-01531 | `B7-filling-sourced` | lobby | gas_equipment | 0 | 0 | fill |
| rec-01535 | `B7-filling-sourced` | mechanical | gas_equipment | 0 | 0 | fill |
| rec-01539 | `B7-filling-sourced` | office | gas_equipment | 0 | 0 | fill |
| rec-01552 | `C3-building-service` | services.json#exhaust_fan | exhaust_fan | — | {"end_use": "exhaust_fan", "fractions": {"latent": 0.0, "lost": 1.0, "radiant": 0.0}, "me… | add |
| rec-01553 | `C3-building-service` | services.json#elevator | elevator | — | {"end_use": "elevator", "fractions": {"latent": 0.0, "lost": 0.0, "radiant": 0.5}, "metho… | add |
| rec-01554 | `C3-building-service` | services.json#exterior_lighting | exterior_lighting | — | {"control": "AstronomicalClock", "design_level_W": 21874.0, "end_use": "exterior_lighting… | add |
| rec-01486 | `C3-building-service-schedule` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | — | Schedule:Compact BLDG_ELEVATORS | add |
| rec-01500 | `C3-building-service-schedule` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | — | Schedule:Compact Kitchen_Exhaust_SCH | add |
| rec-01555 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 734.0, "end_use": "refrigeration_case", "fa… | add |
| rec-01556 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 734.0, "end_use": "refrigeration_case", "fa… | add |
| rec-01557 | `C4-refrigeration` | services.json#refrigeration_rack | refrigeration_rack | — | {"condenser_fan_W": 750.0, "cop": 1.5, "end_use": "refrigeration_rack", "heat_rejection":… | add |
| rec-01558 | `C4-refrigeration` | services.json#refrigeration_rack | refrigeration_rack | — | {"condenser_fan_W": 750.0, "cop": 3.0, "end_use": "refrigeration_rack", "heat_rejection":… | add |
| rec-01548 | `C5-water-use-gains` | restroom | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-01549 | `C5-water-use-gains` | restroom | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-01550 | `C5-water-use-gains` | gym | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "Showers_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction":… | add |
| rec-01551 | `C5-water-use-gains` | kitchen | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction": 0.… | add |
| rec-01571 | `C10-building-wwr` | constructions | fenestration_defaults | — | {"all": {"E": 0.3505, "N": 0.35, "S": 0.35, "W": 0.35, "roof": 0.0}, "conditioned": {"E":… | add |
| rec-01559 | `C10-program-wwr` | auditorium | fenestration | — | {"E": null, "N": 0.35, "S": null, "W": null, "roof": 0.0} | add |
| rec-01560 | `C10-program-wwr` | cafeteria | fenestration | — | {"E": 0.35, "N": 0.35, "S": null, "W": null, "roof": null} | add |
| rec-01561 | `C10-program-wwr` | classroom | fenestration | — | {"E": null, "N": 0.35, "S": 0.35, "W": 0.35, "roof": 0.0} | add |
| rec-01562 | `C10-program-wwr` | corridor | fenestration | — | {"E": null, "N": null, "S": null, "W": 0.35, "roof": 0.0} | add |
| rec-01563 | `C10-program-wwr` | gym-audience | fenestration | — | {"E": 0.35, "N": null, "S": 0.35, "W": null, "roof": 0.0} | add |
| rec-01564 | `C10-program-wwr` | gym | fenestration | — | {"E": null, "N": null, "S": null, "W": null, "roof": 0.0} | add |
| rec-01565 | `C10-program-wwr` | kitchen | fenestration | — | {"E": 0.35, "N": null, "S": null, "W": null, "roof": null} | add |
| rec-01566 | `C10-program-wwr` | library | fenestration | — | {"E": 0.3529, "N": 0.35, "S": null, "W": null, "roof": 0.0} | add |
| rec-01567 | `C10-program-wwr` | lobby | fenestration | — | {"E": null, "N": null, "S": 0.35, "W": null, "roof": 0.0} | add |
| rec-01568 | `C10-program-wwr` | mechanical | fenestration | — | {"E": null, "N": null, "S": null, "W": null, "roof": 0.0} | add |
| rec-01569 | `C10-program-wwr` | office | fenestration | — | {"E": 0.35, "N": null, "S": 0.35, "W": null, "roof": 0.0} | add |
| rec-01570 | `C10-program-wwr` | restroom | fenestration | — | {"E": 0.35, "N": 0.35, "S": null, "W": null, "roof": 0.0} | add |

## doe-ref-pre-1980 · SmallHotel

| Row | Class | Target | Field | Atlas | DOE | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| rec-01585 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | SmallHotel Bldg Equip | Schedule:Compact BLDG_EQUIP_SCH | replace |
| rec-01586 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (lighting) | SmallHotel Bldg Light | Schedule:Compact BLDG_LIGHT_SCH | replace |
| rec-01587 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | SmallHotel Bldg Occ | Schedule:Compact BLDG_OCC_SCH | replace |
| rec-01588 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (lighting) | SmallHotel StaffLounge Light | Schedule:Compact EmployeeLounge_Ltg_Sch | replace |
| rec-01589 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | SmallHotel StaffLounge Occ | Schedule:Compact EmployeeLounge_Occ_Sch | replace |
| rec-01590 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | SmallHotel GuestRoom Equip | Schedule:Compact GuestRoom_Eqp_Sch | replace |
| rec-01592 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | SmallHotel GuestRoom Occ | Schedule:Compact GuestRoom_Occ_Sch | replace |
| rec-01594 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | SmallHotel Office Equip | Schedule:Compact Office_Eqp_Sch | replace |
| rec-01595 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | SmallHotel Office Occ | Schedule:Compact Office_Occ_Sch | replace |
| rec-01591 | `A4-assignment` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (lighting) | — | Schedule:Compact GuestRoom_Ltg_Sch_Base | replace |
| rec-01596 | `A4-slot-assignment` | guest-lounge | electric_equipment schedule (electric_equipment) | SmallHotel Bldg Equip | Schedule:Compact EmployeeLounge_Eqp_Sch | replace |
| rec-01615 | `A5-existing-density` | laundry | occupancy | 0.107639 | 0.112444 | keep (`R-EXISTING-DENSITY`) |
| rec-01598 | `A5-folded-service` | elec-mech-room | electric_equipment | 2133.41 | 0 | replace |
| rec-01603 | `A7-rounding` | exercise | electric_equipment | 11.5174 | 11.5 | keep (`R-ROUNDING`) |
| rec-01605 | `A7-rounding` | guest-lounge | occupancy | 0.322917 | 0.324675 | keep (`R-ROUNDING`) |
| rec-01607 | `A7-rounding` | office | occupancy | 0.0768543 | 0.076666 | keep (`R-ROUNDING`) |
| rec-01608 | `A7-rounding` | office | electric_equipment | 12.9167 | 12.9 | keep (`R-ROUNDING`) |
| rec-01612 | `A7-rounding` | guest-room | occupancy | 0.0427327 | 0.043126 | keep (`R-ROUNDING`) |
| rec-01613 | `A7-rounding` | guest-room | electric_equipment | 14.316 | 14.3 | keep (`R-ROUNDING`) |
| rec-01616 | `A7-rounding` | laundry | electric_equipment | 21.8507 | 21.8754 | keep (`R-ROUNDING`) |
| rec-01618 | `A7-rounding` | meeting | occupancy | 0.538196 | 0.534759 | keep (`R-ROUNDING`) |
| rec-01619 | `A7-rounding` | meeting | electric_equipment | 12.9167 | 12.9 | keep (`R-ROUNDING`) |
| rec-01676 | `A10-infiltration-method` | constructions | infiltration.methods.doe_design_flow | fixed_source_reference_natural_ach | [["airchanges/hour", 1.0, "ALWAYS_ON"], ["flow/exteriorarea", 0.001133, "INFIL_HALF_ON_SC… | add |
| rec-01593 | `A10-infiltration-schedule` | — | schedule (infiltration) | — | Schedule:Compact INFIL_HALF_ON_SCH | add |
| rec-01622 | `A12-heat-fraction` | laundry | electric_equipment.thermal_effects.radiant | 0.5 | 0.2 | replace |
| rec-01694 | `B2-additional-lighting` | attic | additional_lighting | — | one lighting object per zone | leave (`R-NO-LIGHTING-SPLIT`) |
| rec-01696 | `B2-additional-lighting` | corridor | additional_lighting | — | 0 | fill |
| rec-01697 | `B2-additional-lighting` | elec-mech-room | additional_lighting | — | 0 | fill |
| rec-01698 | `B2-additional-lighting` | elevator-core | additional_lighting | — | 0 | fill |
| rec-01699 | `B2-additional-lighting` | exercise | additional_lighting | — | 0 | fill |
| rec-01700 | `B2-additional-lighting` | guest-lounge | additional_lighting | — | 0 | fill |
| rec-01701 | `B2-additional-lighting` | guest-room | additional_lighting | — | 0 | fill |
| rec-01702 | `B2-additional-lighting` | laundry | additional_lighting | — | 0 | fill |
| rec-01703 | `B2-additional-lighting` | mechanical | additional_lighting | — | 0 | fill |
| rec-01704 | `B2-additional-lighting` | meeting | additional_lighting | — | 0 | fill |
| rec-01705 | `B2-additional-lighting` | office | additional_lighting | — | 0 | fill |
| rec-01706 | `B2-additional-lighting` | public-restroom | additional_lighting | — | 0 | fill |
| rec-01707 | `B2-additional-lighting` | staff-lounge | additional_lighting | — | 0 | fill |
| rec-01708 | `B2-additional-lighting` | stair | additional_lighting | — | 0 | fill |
| rec-01709 | `B2-additional-lighting` | storage | additional_lighting | — | 0 | fill |
| rec-01695 | `B3-unconditioned-equipment` | attic | electric_equipment | — | no ElectricEquipment in the complete DOE model: 0, constant 0 | fill |
| rec-01710 | `B4-setpoints` | elec-mech-room | ["heating_setpoint_schedule_id", "cooling_setpoin… | — | no ZoneControl:Thermostat | keep (`R-UNCONTROLLED`) |
| rec-01711 | `B4-setpoints` | elevator-core | ["heating_setpoint_schedule_id", "cooling_setpoin… | — | no ZoneControl:Thermostat | keep (`R-UNCONTROLLED`) |
| rec-01600 | `B5-missing-density` | elevator-core | electric_equipment | — | 0 | fill |
| rec-01597 | `B7-filling-sourced` | corridor | gas_equipment | 0 | 0 | fill |
| rec-01599 | `B7-filling-sourced` | elec-mech-room | gas_equipment | 0 | 0 | fill |
| rec-01601 | `B7-filling-sourced` | elevator-core | gas_equipment | 0 | 0 | fill |
| rec-01602 | `B7-filling-sourced` | staff-lounge | gas_equipment | 0 | 0 | fill |
| rec-01604 | `B7-filling-sourced` | exercise | gas_equipment | 0 | 0 | fill |
| rec-01606 | `B7-filling-sourced` | guest-lounge | gas_equipment | 0 | 0 | fill |
| rec-01609 | `B7-filling-sourced` | office | gas_equipment | 0 | 0 | fill |
| rec-01610 | `B7-filling-sourced` | stair | gas_equipment | 0 | 0 | fill |
| rec-01611 | `B7-filling-sourced` | storage | gas_equipment | 0 | 0 | fill |
| rec-01614 | `B7-filling-sourced` | guest-room | gas_equipment | 0 | 0 | fill |
| rec-01617 | `B7-filling-sourced` | mechanical | gas_equipment | 0 | 0 | fill |
| rec-01620 | `B7-filling-sourced` | meeting | gas_equipment | 0 | 0 | fill |
| rec-01621 | `B7-filling-sourced` | public-restroom | gas_equipment | 0 | 0 | fill |
| rec-01677 | `B8-internal-mass` | elec-mech-room | mass_accounting.additional_mass | — | 2 | fill |
| rec-01678 | `B8-internal-mass` | stair | mass_accounting.additional_mass | — | 2 | fill |
| rec-01679 | `B8-internal-mass` | stair | mass_accounting.additional_mass | — | 2 | fill |
| rec-01680 | `B8-internal-mass` | stair | mass_accounting.additional_mass | — | 2 | fill |
| rec-01681 | `B8-internal-mass` | stair | mass_accounting.additional_mass | — | 2 | fill |
| rec-01682 | `B8-internal-mass` | storage | mass_accounting.additional_mass | — | 2 | fill |
| rec-01683 | `B8-internal-mass` | storage | mass_accounting.additional_mass | — | 2 | fill |
| rec-01684 | `B8-internal-mass` | storage | mass_accounting.additional_mass | — | 2 | fill |
| rec-01685 | `B8-internal-mass` | storage | mass_accounting.additional_mass | — | 2 | fill |
| rec-01686 | `B8-internal-mass` | stair | mass_accounting.additional_mass | — | 2 | fill |
| rec-01687 | `B8-internal-mass` | stair | mass_accounting.additional_mass | — | 2 | fill |
| rec-01688 | `B8-internal-mass` | stair | mass_accounting.additional_mass | — | 2 | fill |
| rec-01689 | `B8-internal-mass` | stair | mass_accounting.additional_mass | — | 2 | fill |
| rec-01690 | `B8-internal-mass` | storage | mass_accounting.additional_mass | — | 2 | fill |
| rec-01691 | `B8-internal-mass` | storage | mass_accounting.additional_mass | — | 2 | fill |
| rec-01692 | `B8-internal-mass` | storage | mass_accounting.additional_mass | — | 2 | fill |
| rec-01693 | `B8-internal-mass` | storage | mass_accounting.additional_mass | — | 2 | fill |
| rec-01659 | `C3-building-service` | services.json#elevator | elevator | — | {"end_use": "elevator", "fractions": {"latent": 0.0, "lost": 0.0, "radiant": 0.5}, "metho… | add |
| rec-01660 | `C3-building-service` | services.json#exterior_lighting | exterior_lighting | — | {"control": "AstronomicalClock", "design_level_W": 16715.0, "end_use": "exterior_lighting… | add |
| rec-01623 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01624 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01625 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01626 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01627 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01628 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01629 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01630 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01631 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01632 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01633 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01634 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01635 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01636 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01637 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01638 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01639 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01640 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01641 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01642 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01643 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01644 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01645 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01646 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01647 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01648 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01649 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01650 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01651 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01652 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01653 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01654 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01655 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01656 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01657 | `C5-water-use-gains` | guest-room | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "GuestRoom_SWH_Sch", "hot_supply_temperature_C": 43.3, "latent_fraction… | add |
| rec-01658 | `C5-water-use-gains` | laundry | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "LaundryRoom_SWH_Sch", "hot_supply_temperature_C": 60.0, "latent_fracti… | add |
| rec-01675 | `C10-building-wwr` | constructions | fenestration_defaults | — | {"all": {"E": 0.0313, "N": 0.1139, "S": 0.1524, "W": 0.0395, "roof": 0.0}, "conditioned":… | add |
| rec-01661 | `C10-program-wwr` | corridor | fenestration | — | {"E": 0.3125, "N": 0.0, "S": 0.2631, "W": 0.3954, "roof": null} | add |
| rec-01662 | `C10-program-wwr` | elec-mech-room | fenestration | — | {"E": null, "N": 0.0, "S": null, "W": null, "roof": null} | add |
| rec-01663 | `C10-program-wwr` | elevator-core | fenestration | — | {"E": null, "N": 0.0, "S": null, "W": null, "roof": null} | add |
| rec-01664 | `C10-program-wwr` | exercise | fenestration | — | {"E": null, "N": 0.1239, "S": null, "W": null, "roof": null} | add |
| rec-01665 | `C10-program-wwr` | guest-lounge | fenestration | — | {"E": null, "N": null, "S": 0.2232, "W": 0.0, "roof": null} | add |
| rec-01666 | `C10-program-wwr` | guest-room | fenestration | — | {"E": null, "N": 0.1495, "S": 0.1578, "W": 0.0, "roof": null} | add |
| rec-01667 | `C10-program-wwr` | laundry | fenestration | — | {"E": null, "N": 0.1238, "S": null, "W": null, "roof": null} | add |
| rec-01668 | `C10-program-wwr` | mechanical | fenestration | — | {"E": null, "N": null, "S": 0.0, "W": null, "roof": null} | add |
| rec-01669 | `C10-program-wwr` | meeting | fenestration | — | {"E": null, "N": null, "S": 0.1509, "W": null, "roof": null} | add |
| rec-01670 | `C10-program-wwr` | office | fenestration | — | {"E": null, "N": 0.1238, "S": null, "W": null, "roof": null} | add |
| rec-01671 | `C10-program-wwr` | public-restroom | fenestration | — | {"E": null, "N": null, "S": 0.0, "W": null, "roof": null} | add |
| rec-01672 | `C10-program-wwr` | staff-lounge | fenestration | — | {"E": null, "N": 0.1238, "S": null, "W": null, "roof": null} | add |
| rec-01673 | `C10-program-wwr` | stair | fenestration | — | {"E": 0.0, "N": 0.0, "S": null, "W": 0.0, "roof": null} | add |
| rec-01674 | `C10-program-wwr` | storage | fenestration | — | {"E": 0.0, "N": 0.0, "S": 0.0, "W": null, "roof": null} | add |

## doe-ref-pre-1980 · SmallOffice

| Row | Class | Target | Field | Atlas | DOE | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| rec-01712 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | Small Office Bldg Equip | Schedule:Compact BLDG_EQUIP_SCH | replace |
| rec-01713 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (lighting) | Office Bldg Light | Schedule:Compact BLDG_LIGHT_SCH | replace |
| rec-01714 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | Small Office Bldg Occ | Schedule:Compact BLDG_OCC_SCH | replace |
| rec-01716 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (cooling setpoint) | Small Office ClgSetp | Schedule:Compact CLGSETP_SCH | replace |
| rec-01717 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (heating setpoint) | Small Office HtgSetp | Schedule:Compact HTGSETP_SCH | replace |
| rec-01724 | `A10-infiltration-method` | constructions | infiltration.methods.doe_design_flow | fixed_source_reference_natural_ach | [["airchanges/hour", 0.36, "INFIL_QUARTER_ON_SCH"], ["flow/exteriorarea", 0.001133, "INFI… | add |
| rec-01718 | `A10-infiltration-schedule` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (infiltration) | Office Bldg Light | Schedule:Compact INFIL_QUARTER_ON_SCH | add |
| rec-01715 | `B1-hot-water-schedule` | — | schedule (hot-water flow) | — | Schedule:Compact BLDG_SWH_SCH | fill |
| rec-01725 | `B2-additional-lighting` | whole-building-sm-office | additional_lighting | — | 0 | fill |
| rec-01719 | `B7-filling-sourced` | whole-building-sm-office | gas_equipment | 0 | 0 | fill |
| rec-01721 | `C3-building-service` | services.json#exterior_lighting | exterior_lighting | — | {"control": "AstronomicalClock", "design_level_W": 2766.0, "end_use": "exterior_lighting"… | add |
| rec-01720 | `C5-water-use-gains` | whole-building-sm-office | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 43.3, "latent_fraction": 0.… | add |
| rec-01723 | `C10-building-wwr` | constructions | fenestration_defaults | — | {"all": {"E": 0.1981, "N": 0.1981, "S": 0.2444, "W": 0.1981, "roof": 0.0}, "conditioned":… | add |
| rec-01722 | `C10-program-wwr` | whole-building-sm-office | fenestration | — | {"E": 0.1981, "N": 0.1981, "S": 0.2444, "W": 0.1981, "roof": 0.0} | add |

## doe-ref-pre-1980 · SuperMarket

| Row | Class | Target | Field | Atlas | DOE | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| rec-01776 | `A1-holidays` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (hot-water flow) | SuperMarket Bldg Swh | Schedule:Compact BLDG_SWH_SCH | replace |
| rec-01774 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (lighting) | — | Schedule:Compact BLDG_LIGHT_SCH | replace |
| rec-01775 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | — | Schedule:Compact BLDG_OCC_SCH | replace |
| rec-01772 | `A4-assignment` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (gas) | — | Schedule:Compact BLDG_EQUIP_SCH | replace |
| rec-01773 | `A4-assignment` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | — | Schedule:Compact BLDG_EQUIP_SCH | replace |
| rec-01780 | `A5-existing-density` | bakery | lighting | 54.2501 | 29.94 | keep (`R-EXISTING-DENSITY`) |
| rec-01781 | `A5-existing-density` | deli | lighting | 54.2501 | 29.94 | keep (`R-EXISTING-DENSITY`) |
| rec-01784 | `A5-existing-density` | dry-storage | lighting | 8.28821 | 11.9 | keep (`R-EXISTING-DENSITY`) |
| rec-01786 | `A5-existing-density` | office | lighting | 31.2153 | 21.36 | keep (`R-EXISTING-DENSITY`) |
| rec-01788 | `A5-existing-density` | produce | lighting | 54.2501 | 29.94 | keep (`R-EXISTING-DENSITY`) |
| rec-01789 | `A5-explicitly-wrong` | produce | electric_equipment | 0.538196 | 5.38 | replace |
| rec-01782 | `A7-rounding` | deli | gas_equipment | 26.9087 | 26.9359 | keep (`R-ROUNDING`) |
| rec-01783 | `A7-rounding` | dry-storage | occupancy | 0.0359515 | 0.035881 | keep (`R-ROUNDING`) |
| rec-01832 | `A10-infiltration-method` | constructions | infiltration.methods.doe_design_flow | fixed_source_reference_natural_ach | [["flow/exteriorarea", 0.001133, "INFIL_HALF_ON_SCH"]] | add |
| rec-01778 | `A10-infiltration-schedule` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (infiltration) | — | Schedule:Compact INFIL_HALF_ON_SCH | add |
| rec-01791 | `A12-heat-fraction` | bakery | gas_equipment.thermal_effects.radiant | 0.2 | 0.5 | replace |
| rec-01792 | `A12-heat-fraction` | bakery | gas_equipment.thermal_effects.latent | 0.1 | 0 | replace |
| rec-01793 | `A12-heat-fraction` | bakery | gas_equipment.thermal_effects.lost | 0.7 | 0 | replace |
| rec-01794 | `A12-heat-fraction` | deli | gas_equipment.thermal_effects.radiant | 0.2 | 0.5 | replace |
| rec-01795 | `A12-heat-fraction` | deli | gas_equipment.thermal_effects.latent | 0.1 | 0 | replace |
| rec-01796 | `A12-heat-fraction` | deli | gas_equipment.thermal_effects.lost | 0.7 | 0 | replace |
| rec-01797 | `B1-hot-water` | corridor | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-01798 | `B1-hot-water` | dining | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-01799 | `B1-hot-water` | dry-storage | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-01800 | `B1-hot-water` | elec-mech-room | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-01801 | `B1-hot-water` | meeting | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-01802 | `B1-hot-water` | office | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-01803 | `B1-hot-water` | produce | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-01804 | `B1-hot-water` | restroom | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-01805 | `B1-hot-water` | sales | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-01806 | `B1-hot-water` | vestibule | service_water_heating_schedule_id | — | no draw: zero | fill |
| rec-01834 | `B2-additional-lighting` | bakery | additional_lighting | — | one lighting object per zone | leave (`R-NO-LIGHTING-SPLIT`) |
| rec-01835 | `B2-additional-lighting` | corridor | additional_lighting | — | one lighting object per zone | leave (`R-NO-LIGHTING-SPLIT`) |
| rec-01836 | `B2-additional-lighting` | deli | additional_lighting | — | one lighting object per zone | leave (`R-NO-LIGHTING-SPLIT`) |
| rec-01837 | `B2-additional-lighting` | dining | additional_lighting | — | one lighting object per zone | leave (`R-NO-LIGHTING-SPLIT`) |
| rec-01838 | `B2-additional-lighting` | dry-storage | additional_lighting | — | one lighting object per zone | leave (`R-NO-LIGHTING-SPLIT`) |
| rec-01839 | `B2-additional-lighting` | elec-mech-room | additional_lighting | — | one lighting object per zone | leave (`R-NO-LIGHTING-SPLIT`) |
| rec-01840 | `B2-additional-lighting` | meeting | additional_lighting | — | one lighting object per zone | leave (`R-NO-LIGHTING-SPLIT`) |
| rec-01841 | `B2-additional-lighting` | office | additional_lighting | — | one lighting object per zone | leave (`R-NO-LIGHTING-SPLIT`) |
| rec-01842 | `B2-additional-lighting` | produce | additional_lighting | — | one lighting object per zone | leave (`R-NO-LIGHTING-SPLIT`) |
| rec-01843 | `B2-additional-lighting` | restroom | additional_lighting | — | one lighting object per zone | leave (`R-NO-LIGHTING-SPLIT`) |
| rec-01844 | `B2-additional-lighting` | sales | additional_lighting | — | one lighting object per zone | leave (`R-NO-LIGHTING-SPLIT`) |
| rec-01845 | `B2-additional-lighting` | vestibule | additional_lighting | — | one lighting object per zone | leave (`R-NO-LIGHTING-SPLIT`) |
| rec-01785 | `B7-filling-sourced` | dry-storage | gas_equipment | 0 | 0 | fill |
| rec-01787 | `B7-filling-sourced` | office | gas_equipment | 0 | 0 | fill |
| rec-01790 | `B7-filling-sourced` | produce | gas_equipment | 0 | 0 | fill |
| rec-01833 | `B8-internal-mass` | corridor, dining, elec-mech-room, meeting, restroom, sales,… | mass_accounting.additional_mass | — | 2 | fill |
| rec-01809 | `C3-building-service` | services.json#exhaust_fan | exhaust_fan | — | {"end_use": "exhaust_fan", "fractions": {"latent": 0.0, "lost": 1.0, "radiant": 0.0}, "me… | add |
| rec-01810 | `C3-building-service` | services.json#exterior_lighting | exterior_lighting | — | {"control": "AstronomicalClock", "design_level_W": 16402.0, "end_use": "exterior_lighting… | add |
| rec-01777 | `C3-building-service-schedule` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | — | Schedule:Compact Deli_Exhaust_SCH | add |
| rec-01811 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 461.52, "end_use": "refrigeration_case", "f… | add |
| rec-01812 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 1442.25, "end_use": "refrigeration_case", "… | add |
| rec-01813 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 461.52, "end_use": "refrigeration_case", "f… | add |
| rec-01814 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 1442.25, "end_use": "refrigeration_case", "… | add |
| rec-01815 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 1442.25, "end_use": "refrigeration_case", "… | add |
| rec-01816 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 1442.25, "end_use": "refrigeration_case", "… | add |
| rec-01817 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 538.44, "end_use": "refrigeration_case", "f… | add |
| rec-01818 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 528.83, "end_use": "refrigeration_case", "f… | add |
| rec-01819 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 461.52, "end_use": "refrigeration_case", "f… | add |
| rec-01820 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 461.52, "end_use": "refrigeration_case", "f… | add |
| rec-01821 | `C4-refrigeration` | services.json#refrigeration_case | refrigeration_case | — | {"availability": "ALWAYS_ON", "capacity_W_m": 615.36, "end_use": "refrigeration_case", "f… | add |
| rec-01822 | `C4-refrigeration` | services.json#refrigeration_rack | refrigeration_rack | — | {"condenser_fan_W": 4500.0, "cop": 2.5, "end_use": "refrigeration_rack", "heat_rejection"… | add |
| rec-01823 | `C4-refrigeration` | services.json#refrigeration_rack | refrigeration_rack | — | {"condenser_fan_W": 4500.0, "cop": 1.3, "end_use": "refrigeration_rack", "heat_rejection"… | add |
| rec-01824 | `C4-refrigeration` | services.json#refrigeration_rack | refrigeration_rack | — | {"condenser_fan_W": 4500.0, "cop": 2.5, "end_use": "refrigeration_rack", "heat_rejection"… | add |
| rec-01825 | `C4-refrigeration` | services.json#refrigeration_rack | refrigeration_rack | — | {"condenser_fan_W": 4500.0, "cop": 1.3, "end_use": "refrigeration_rack", "heat_rejection"… | add |
| rec-01807 | `C5-water-use-gains` | bakery | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction": 0.… | add |
| rec-01808 | `C5-water-use-gains` | deli | hot_water.thermal_effects | zone_heat_gains excluded (ADR 0018) | {"flow_schedule": "BLDG_SWH_SCH", "hot_supply_temperature_C": 49.0, "latent_fraction": 0.… | add |
| rec-01831 | `C10-building-wwr` | constructions | fenestration_defaults | — | {"all": {"E": 0.0, "N": 0.0, "S": 0.3619, "W": 0.0, "roof": 0.0}, "conditioned": {"E": 0.… | add |
| rec-01826 | `C10-program-wwr` | bakery | fenestration | — | {"E": 0.0, "N": null, "S": 0.0, "W": null, "roof": 0.0} | add |
| rec-01827 | `C10-program-wwr` | deli | fenestration | — | {"E": 0.0, "N": null, "S": null, "W": null, "roof": 0.0} | add |
| rec-01828 | `C10-program-wwr` | dry-storage | fenestration | — | {"E": null, "N": 0.0, "S": null, "W": 0.0, "roof": 0.0} | add |
| rec-01829 | `C10-program-wwr` | office | fenestration | — | {"E": 0.0, "N": 0.0, "S": null, "W": null, "roof": 0.0} | add |
| rec-01830 | `C10-program-wwr` | produce | fenestration | — | {"E": null, "N": null, "S": 0.0, "W": 0.0, "roof": 0.0} | add |
| rec-01779 | `mixed-zone` | — | loads | — | Sales | leave (`R-MIXED-ZONE`) |

## doe-ref-pre-1980 · Warehouse

| Row | Class | Target | Field | Atlas | DOE | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| rec-01849 | `A3-no-atlas-counterpart` | — | schedule (cooling setpoint) | — | Schedule:Compact CLGSETP_FineStorage_SCH | replace |
| rec-01852 | `A3-no-atlas-counterpart` | — | schedule (heating setpoint) | — | Schedule:Compact HTGSETP_SCH | replace |
| rec-01846 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (plug) | — | Schedule:Compact BLDG_EQUIP_SCH | replace |
| rec-01847 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (lighting) | — | Schedule:Compact BLDG_LIGHT_SCH | replace |
| rec-01848 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (occupancy) | Warehouse Bldg Occ | Schedule:Compact BLDG_OCC_SCH | keep (`R-NEWER-DOCUMENTED`) |
| rec-01850 | `A3-upstream-edit` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (cooling setpoint) | Warehouse Cooling Setpoint | Schedule:Compact CLGSETP_SCH | replace |
| rec-01853 | `A3-upstream-edit` | office | occupancy schedule (occupancy) | Warehouse Bldg Occ | Schedule:Compact BLDG_OCC_SCH | keep (`R-NEWER-DOCUMENTED`) |
| rec-01851 | `A4-assignment` | s, c, h, e, d, u, l, e, s, ., j, s, o, n, #, d, o, e, -, r,… | schedule (heating setpoint) | Warehouse HtgSetp | Schedule:Compact HTGSETP_FineStorage_SCH | replace |
| rec-01862 | `A10-infiltration-method` | constructions | infiltration.methods.doe_design_flow | fixed_source_reference_natural_ach | [["flow/exteriorarea", 0.001133, "ALWAYS_ON"]] | add |
| rec-01864 | `B2-additional-lighting` | bulk | additional_lighting | — | 0 | fill |
| rec-01865 | `B2-additional-lighting` | fine | additional_lighting | — | 0 | fill |
| rec-01866 | `B2-additional-lighting` | office | additional_lighting | — | 0 | fill |
| rec-01854 | `B7-filling-sourced` | bulk | gas_equipment | 0 | 0 | fill |
| rec-01855 | `B7-filling-sourced` | fine | gas_equipment | 0 | 0 | fill |
| rec-01856 | `B7-filling-sourced` | office | gas_equipment | 0 | 0 | fill |
| rec-01863 | `B8-internal-mass` | bulk | mass_accounting.additional_mass | — | 2 | fill |
| rec-01857 | `C3-building-service` | services.json#exterior_lighting | exterior_lighting | — | {"control": "AstronomicalClock", "design_level_W": 10958.0, "end_use": "exterior_lighting… | add |
| rec-01861 | `C10-building-wwr` | constructions | fenestration_defaults | — | {"all": {"E": 0.0, "N": 0.0, "S": 0.0286, "W": 0.0076, "roof": 0.0}, "conditioned": {"E":… | add |
| rec-01858 | `C10-program-wwr` | bulk | fenestration | — | {"E": 0.0, "N": 0.0, "S": null, "W": 0.0, "roof": 0.0} | add |
| rec-01859 | `C10-program-wwr` | fine | fenestration | — | {"E": 0.0, "N": 0.0, "S": 0.0, "W": 0.0, "roof": 0.0} | add |
| rec-01860 | `C10-program-wwr` | office | fenestration | — | {"E": 0.0, "N": 0.0, "S": 0.1009, "W": 0.1668, "roof": null} | add |
