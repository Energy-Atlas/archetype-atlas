# ADR 0005: Preserve parametric upstream schedule mechanisms

Date: 2026-10-04. Status: accepted direction; implementation contract deferred to
the next design discussion. This decision follows the user's annotation review.

## Decision

Subsequent release-order decision: deliver full or near-full deterministic data
coverage before shipping either parametric generator. Fixed schedule tables are
the priority for the present release; see [ADR 0006](0006-deterministic-coverage-release.md).

The atlas should provide the ResStock parametric schedule-generation mechanism,
with its source data, alongside enumerable deterministic archetypes. A library
of fixed seeded annual realizations alone is not the intended final interface.
Preserve seeds and explicit inputs so any chosen realization remains reproducible.
The current executed fixtures remain evidence and regression examples.

Apply the same principle to ComStock's own mechanism. Do not substitute ResStock's
occupant Markov model for ComStock's operating-hours sampling and parametric
schedule transformation. Population prevalence remains optional source evidence;
the atlas's experimental baseline remains deterministic, as required by the brief.

The next discussion will define what "mimic" means: upstream wrapper versus
redistribution versus reimplementation, runtime/API, parameter boundaries,
stochastic seed streams, calibration-data dependencies, versioned parity tests,
license notices, and day/calendar/control semantics. This round does not select
those architectural details or claim a generator library has been delivered.

## ResStock reference implementation

Pinned revision: `dd25369f41a83a0767aefeeac0b6f8a0b0edd649`.

- [Measure and zero-occupant skip](https://github.com/NatLabRockies/ResStock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/BuildResidentialScheduleFile/measure.rb).
- [ScheduleGenerator](https://github.com/NatLabRockies/ResStock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/BuildResidentialScheduleFile/resources/schedules.rb).
- [Method and resource inventory](https://github.com/NatLabRockies/ResStock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/BuildResidentialScheduleFile/resources/README.md).
- The adjacent `weekday/`, `weekend/`, consumption/duration distributions,
  hot-water draw tables and constants are part of the generator, not optional
  replacements with guessed distributions. The existing runtime lock covers
  the retrieved source subset and its upstream resource blobs.
- [Post-HPXML controls](https://github.com/NatLabRockies/ResStock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/measures/ResStockArgumentsPostHPXML/measure.rb).
- [Default schedules](https://github.com/NatLabRockies/ResStock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/HPXMLtoOpenStudio/resources/data/default_schedules.csv)
  and [conditional defaults logic](https://github.com/NatLabRockies/ResStock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/HPXMLtoOpenStudio/resources/defaults.rb)
  cover loads outside the stochastic export; their application conditions matter.

The model uses time-dependent occupant-activity transition probabilities derived
from ATUS, weekday/weekend behavior clusters, appliance power/duration samples
from NEEA RBSA, and Aquacraft/AWWA hot-water event data. Appliance/water events are
derived from activities. Household profiles combine occupants and end-use events.
This is synthetic dwelling-level behavior, not room movement or measured histories.

## ComStock reference implementation

Pinned revision: `3c103063c0debb177a200dd1df8406b8d0f8d515`.

- [Hours and occupancy source documentation](https://github.com/NatLabRockies/ComStock/blob/3c103063c0debb177a200dd1df8406b8d0f8d515/documentation/reference_doc/4_3_occupancy.tex).
- [Typical-building measure](https://github.com/NatLabRockies/ComStock/blob/3c103063c0debb177a200dd1df8406b8d0f8d515/resources/measures/create_typical_building_from_model/measure.rb)
  passes weekday/weekend start and duration inputs to Standards.
- [Option bindings](https://github.com/NatLabRockies/ComStock/blob/3c103063c0debb177a200dd1df8406b8d0f8d515/resources/options_lookup.tsv),
  [occupancy fraction adjustment](https://github.com/NatLabRockies/ComStock/blob/3c103063c0debb177a200dd1df8406b8d0f8d515/resources/measures/adjust_occupancy_schedule/measure.rb),
  and separate lighting/equipment base-to-peak measures supply other transformations.
- At Standards revision `c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907`,
  [create_typical.rb](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/lib/openstudio-standards/create_typical/create_typical.rb)
  sets up and applies
  [parametric schedule formulas](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/lib/openstudio-standards/schedules/parametric.rb).

ComStock is stochastic in selecting building-level inputs. In the inspected
workflow, schedules are then shifted/stretched/compressed from prototype rules
to those operating hours; this is not the ResStock activity-chain generator.
Hours distributions were derived from one year of AMI data for 6,070 buildings
across eight utilities. Weekday/weekend selections are independent; the source
uses national distributions combined across seasons/utilities. Given selected
inputs, the inspected schedule transformation is deterministic.
Commercial runtime parity has not been executed. The atlas Standards revision
is independently selected source evidence; it must not be assumed to be
ComStock's exact runtime dependency. The next design must pin the actual
commercial dependency bindings and test the effects of operating-hour inputs.

## Reference-location boundary

Future weather/location-derived schedule elements will be parameterized at the
DOE Commercial Reference Building representative locations, rather than every
county. Use the explicit DOE set of 16 location cases; preserve both coastal
Los Angeles and inland Las Vegas under 3B. This is not interchangeable with a
PNNL or a newer ASHRAE climate-zone set. Do not arbitrarily choose between them.
The original technical report's Table 2 distinguishes representative city from
weather-file location: 5B is Denver/Boulder; 5A is Chicago/Chicago-O'Hare.

Cache ceiling-fan operating months, solar/location lighting inputs and heating/
cooling season inputs per location, source EPW, calendar, algorithm revision and
checksum. Preserve source seeds and unavailable-period selection rules. Core
occupant transitions do not need weather. Temperature-dependent refrigerator
defaults can require a modeled appliance-location temperature; outdoor EPW alone
does not resolve that input. Current county station-proxy fixtures remain their
original variants; no relabeling or silent replacement.

Exact weather-file/station bindings and the generator interface are pending the
next design round. The chosen location list and current availability cases are
documented in [source review](../schedule-source-review.md).

## Current approved resolutions

Supplement v0.2.0 adds lighting zero for exactly ten Medium/Large Office ceiling
plenums, and routine modeled occupancy zero for exactly six Large Office data-
centre/main-data-centre programs in 90.1-2007/2013/2019. Maintenance is excluded
from this explicit variant. Positive loads or existing schedules block these
rules. Neighboring offices, equipment, lighting and conditioning stay separate.

At the v0.2.0 decision, gas and water recipe absence were documented as
component-level evidence. The subsequent user-approved gas rule in ADR 0006
adopts zero for the exact 713 reviewed program records. Existing local water zeros
remain local demand only. Attic/plenum/basement records are excluded from the
active gap assessment, but remain in the immutable atlas and explicit supplement.

Supporting primary blobs are retrieved immutably using SHA-256 checksums in
`sources/schedule-evidence-lock.json`. Run
`python -m scripts.fetch --lock sources/schedule-evidence-lock.json` to retrieve;
add `--verify-only` for offline verification. Source notices remain applicable.

Source clarification after freezing v0.2.0: the DOE HTML snapshot varies across
delivery environments and is retained as an informational historical receipt.
Active evidence lock version 2 pins the stable official technical report
NREL/TP-5500-46861, DOI 10.2172/1009264, Table 2. No frozen source hash is changed.
