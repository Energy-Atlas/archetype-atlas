# Schedule mechanisms and next generator design

The accepted direction is to provide upstream parametric schedule mechanisms
with explicit inputs, seeds, source revisions and parity checks. Fixed annual
realizations remain useful evidence. The interface and meaning of "mimic" will
be defined in the next design discussion; a general generator library is not
yet delivered. Deterministic experimental archetypes remain the atlas baseline.

## ResStock and ComStock

ResStock's [ScheduleGenerator](https://github.com/NatLabRockies/ResStock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/BuildResidentialScheduleFile/resources/schedules.rb)
uses time-dependent occupant-activity Markov chains, ATUS behavior data,
RBSA appliance samples and Aquacraft/AWWA hot-water events. The adjacent
[resource description](https://github.com/NatLabRockies/ResStock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/BuildResidentialScheduleFile/resources/README.md)
documents the basis and required probability/data tables. Profiles represent
synthetic dwelling behavior, not room-level movements or measured histories.

ComStock samples building-level operating parameters; its
[pinned documentation](https://github.com/NatLabRockies/ComStock/blob/3c103063c0debb177a200dd1df8406b8d0f8d515/documentation/reference_doc/4_3_occupancy.tex)
describes weekday/weekend start times and durations derived from AMI evidence.
Standards [parametric schedule formulas](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/lib/openstudio-standards/schedules/parametric.rb)
then shift/stretch/compress prototype rules to those selected hours. This is
different from the ResStock activity model. Preserve each source mechanism.

## Three zero-occupant fixtures

Source fixtures 165449, 494980 and 447245 currently have occupancy-zero and nominal
thermostat columns. The upstream stochastic measure skips them. The source
[default schedule table](https://github.com/NatLabRockies/ResStock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/HPXMLtoOpenStudio/resources/data/default_schedules.csv)
contains fixed lighting/plug/appliance shapes and refrigerator/freezer shapes
and temperature coefficients. All three have a selected refrigerator; two have
a selected freezer. Refrigerator defaults may use temperature coefficients when
fractional schedules are not supplied. Retrieved recipes are available, but no
record-level background annual profiles have been assigned or executed here.

## HVAC unavailable-day options

These affect residential dwelling HVAC, not commercial room programs. The other
31 source fixtures specify Never/Never. Exact placement remains unexecuted in
the schedule-only runner; nominal thermostats remain visible.

| Fixture | Dwelling class | Heating unavailable | Cooling unavailable |
| --- | --- | --- | --- |
| 452189 | Detached single-family | 3 days | 3 days |
| 143851 | 5+-unit low-rise multifamily | Never | 3 days |
| 342177 | Attached single-family | Never | 1 month |
| 428680 | 5+-unit low-rise multifamily | 1 day | 1 day |
| 449307 | Midrise apartment | 1 month | 2 weeks |
| 66378 | Detached single-family | Year round | Year round |
| 121706 | 5+-unit low-rise multifamily | 2 weeks | 2 weeks |
| 461465 | Detached single-family | 1 week | Never |
| 290025 | Detached single-family | 3 months | 3 months |
| 149911 | 2–4-unit multifamily | Never | 1 week |

[Post-HPXML source logic](https://github.com/NatLabRockies/ResStock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/measures/ResStockArgumentsPostHPXML/measure.rb)
uses weather-defined seasons and a seeded start day for consecutive equipment-
unavailable periods. Desired temperatures are distinct from availability.

## Location variants

Future weather-derived elements will use the
[DOE reference location set](https://www.energy.gov/cmei/buildings/new-construction-commercial-reference-buildings-archive):
Miami, Houston, Phoenix, Atlanta, Los Angeles, Las Vegas, San Francisco, Baltimore,
Albuquerque, Seattle, Chicago, Boulder, Minneapolis, Helena, Duluth and Fairbanks.
Retain both coastal and inland 3B cases. Exact EPW files still require a separate
locked binding. Current fixture station proxies remain their original variants.

Cache fan-season months, lighting location/solar inputs and HVAC seasons per
location and algorithm revision. Core occupant transitions do not require EPW.
Temperature-dependent appliance defaults may also require appliance-location
temperature; outdoor weather alone does not supply that modeled temperature.

## Zero resolution boundaries

Supplement v0.2.0 adds zero lighting for ten ceiling plenums and zero routine
occupancy for six exact Large Office data-centre programs. Neighboring office
occupants, positive lighting/equipment and thermostats are preserved. Maintenance
is outside this adopted baseline. Attic/plenum/basement records remain archived
but are excluded from the active gap assessment.

Blank gas density means the generic recipe adds no gas equipment in a clean
model. It does not prove a complete building has no gas use. Similarly, absent
local water allocation does not disable a central water loop. These component
boundaries explain why the broader gas/water source nulls remain visible.
