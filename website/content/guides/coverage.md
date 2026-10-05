# Schedule coverage and remaining gaps

Supplement **v0.4.0** and commercial-completion **v0.1.0** cover the atlas's named
**16 DOE Reference types, 16 PNNL types and seven residential classes**. These
are source-input archetypes: 83 commercial type/template combinations, 768
program records and 41 dwelling configurations, rather than every stock variant.

Attic, plenum and basement records are excluded from the active milestone.
For **734 active programs**, **4,859 of 5,138 schedule fields are supplied (94.6%)**.
Occupancy, lighting, electric/gas equipment and thermostat applicability are
resolved within the reviewed source recipe. **279 fields remain unknown**, all
concerning program allocation of fixture/service-water demand.

| Building type | Remaining program-water assignments |
| --- | ---: |
| Full-service restaurant | 3 |
| Hospital | 47 |
| Large hotel | 27 |
| Primary school | 41 |
| Standalone retail | 11 |
| Secondary school | 43 |
| Small hotel | 48 |
| Supermarket | 50 |
| Warehouse | 9 |
| **Total** | **279** |

The [fixture catalogue](../commercial-completion/index.md) preserves **217 draw
paths, 28 schedule recipes and 59 unallocated building-service paths**. The source
does not identify beneficiaries for some lumped main, booster and laundry draws.
A heater's room is insufficient allocation evidence. These services block
unsupported program zeros. **206 source-complete no-draw cases** now have explicit
zeros; positive assigned paths retain conserved source and peak-normalized curves.

To fill the remaining 279 assignments, inspect generated water-use equipment,
space connections and service mappings. Where those still give no beneficiary,
publish a separate, documented allocation variant with supported area/use weights
summing to one. Do not distribute a shared draw by silently substituting occupancy
or by applying it to every room. [Hot-water methods](hot-water.md) describe scaling.

## Residential profiles

All **574 assessed profile fields (41 configurations × 14 columns)** are supplied.
Dwelling exterior lighting is also supplied for **41/41** configurations: **38
fixed positive profiles and three reviewed vacant-use zeros**. This does not
establish shared/common-area exterior lighting for multifamily buildings.

Refrigeration is a separate upstream appliance modeling path. Missing stochastic
columns alone do not imply absence. Selected-equipment evidence yields **40
refrigerator defaults, 19 freezer defaults and 23 absent-appliance zeros**. Fixed
fractions include source monthly multipliers and no temperature feedback. The
three vacant fixtures also have **25 reviewed operational zeros** for skipped
foreground loads, verified against upstream zero-occupant behavior. Their selected
refrigerators and freezers remain active background loads.

## Reviewed controls and scope

Eight executed source-phase cases support inactive conditioning for **19 exact
Small Hotel electrical/core and Highrise Apartment corridor programs**, resolving
38 missing thermostat fields. Dedicated generated zones have no active equipment,
air loops, ideal loads or setpoint schedules. Evidence is limited to the inspected
pre-sizing phases at climate 4A; passive heat transfer and later custom model
modifications are outside this result. No extreme-temperature placeholders are used.

The existing **713 program gas-equipment zeros** remain opt-in recipe resolutions.
They concern space equipment, not gas HVAC or gas water heating. Source nulls
remain unchanged and visible on every program page.

Sampled HVAC equipment-unavailability overlays, complete load magnitudes and
full-model control application are excluded. Reference-city fan/lighting variants,
shared residential services and direct DOE/PNNL model equivalence remain separate
evidence tasks. Shipping parametric generators follows deterministic data coverage.
No full-stock or simulation-readiness claim is made.

[Per-record machine-readable gap inventory](../schedule-coverage.json) identifies
every remaining field, record, template and scope decision.
