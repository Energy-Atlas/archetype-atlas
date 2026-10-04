# Schedule mechanisms and next generator design

The accepted direction is to provide upstream parametric schedule mechanisms
with explicit inputs, seeds, source revisions and parity checks. Fixed annual
realizations remain useful evidence. The interface and meaning of "mimic" will
be defined in the next design discussion; a general generator library is not
yet delivered. Full or near-full preprogrammed data coverage now explicitly
precedes generator shipping. Deterministic archetypes remain the atlas baseline.

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
fractional schedules are not supplied. Supplement v0.3.0 supplies a user-selected
fixed fractional alternative for their refrigeration background loads, with
monthly multipliers and no temperature feedback. Their other skipped end uses
are still unresolved; no new upstream full-model execution is claimed.

## HVAC unavailable-day options

**Excluded from the current schedule release by user decision.** Use nominal
desired-temperature profiles without sampled equipment interruptions. The
following raw source options remain archived evidence, not pending release work.

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
These are ten raw option cases. Fixture 143851 also selects no cooling equipment
and no cooling partial conditioning; its three cooling-unavailable days have no
selected cooler to disable. The other nine fixtures select equipment affected
by their unavailable-day options. Full model control application remains separate.

## Location variants

Future weather-derived elements will use the
[DOE technical report location set](https://docs.nlr.gov/docs/fy11osti/46861.pdf), Table 2:
Miami, Houston, Phoenix, Atlanta, Los Angeles, Las Vegas, San Francisco, Baltimore,
Albuquerque, Seattle, Chicago, Denver/Boulder, Minneapolis, Helena, Duluth and Fairbanks.
Retain both coastal and inland 3B cases. Exact EPW files still require a separate
locked binding. Current fixture station proxies remain their original variants.
The report distinguishes representative city from weather-file location: 5B
uses Denver/Boulder; 5A uses Chicago/Chicago-O'Hare. The source PDF is SHA-256
locked; a historical HTML receipt is retained but is not a current build dependency.

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

Supplement v0.3.0 adopts user-approved zero gas-equipment schedules and densities
for the exact 713 clean-recipe programs. This does not classify their buildings
as all-electric or zero gas HVAC/water heating. Original source nulls remain
visible beside the explicit opt-in zero. There are 523 active non-cavity gaps:
485 local water and 38 thermostat schedules.

Select both the always-zero fraction and 0 W/m2 density as the resolved variant.
This applies to program equipment in the clean source recipe; custom/direct
equipment needs its own variant. Gas heating and gas water-heating fuel remain
independent inputs. Each program page shows the original null, explicit zero
and its source/code evidence. See [coverage and remaining gaps](coverage.md).

## Fixed backgrounds and coverage-first delivery

Full or near-full deterministic data coverage precedes shipping any parametric
generator. The three zero-occupant dwelling fixtures are 165449 and 447245
(detached single-family) and 494980 (low-rise multifamily dwelling unit).
All have refrigerators; only the two detached fixtures have freezers. Fixed
source hourly fractions and monthly multipliers supply their refrigeration
shapes without temperature feedback. The apartment freezer is zero. These are
clearly labelled defaults, not stochastic execution or inferred lighting/plug use.
Entry pages provide daily/annual plots and the canonical tables with provenance.

Current profile download links may reuse byte-identical historical assets.
Use the complete supplement snapshot ZIP for the canonical manifest inventory;
the public `profile-download-map.json` records shared download URLs.

## Hot-water equivalent and availability controls

The [Medium Office pilot](hot-water.md) attaches a conserved fixture-draw
equivalent to its existing office program, without creating a new restroom
program. Its normalized fractions and compatible peak-flow scaling preserve
source demand. All rule dates, selectors, design days and source order remain.
This office already has a source water curve, so the pilot closes zero gaps.
Extension to the remaining programs requires explicit serving/allocation evidence
and conservation checks; no generic occupancy shape fills the 495 source nulls.

HVAC unavailable days are separate from vacancy. All ten affected fixtures have
`Vacancy Status=Occupied` and 1-5 occupants. The source cites RECS and sampling
dependencies on poverty level, building type, tenure and cooling unavailability;
its controls use `No Space Heating`/`No Space Cooling`, while vacancy is separate.
EIA describes the underlying survey's inability-to-use questions as broken
equipment households could not afford to fix or unaffordable energy
([EIA explanation](https://www.eia.gov/todayinenergy/detail.php?id=51979)).
Availability overlays are excluded from this release. Nominal thermostat
profiles are the requested baseline; archived source options remain traceable.
