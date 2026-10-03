# v0.2.0 named typology coverage and unresolved inputs

Source-input coverage is complete for the named DOE Reference suite (16/16),
PNNL commercial prototype suite (16/16), and seven residential classes. Direct
DOE/PNNL generated-IDF equivalence is unverified. Coverage does not imply completed
simulation inputs or all published code editions/stock combinations.

Commercial inputs cover 17 types across five selected templates (83 combinations).
No tagged source spaces were excluded by the exact lookup. The two DOE Reference
templates have no HighriseApartment entry. Program rows remain independent of
climate; envelope inputs retain 22 source climate sets.

| Commercial type | Program rows |
| --- | ---: |
| FullServiceRestaurant | 14 |
| HighriseApartment | 18 |
| Hospital | 97 |
| LargeHotel | 83 |
| LargeOffice | 18 |
| MediumOffice | 10 |
| MidriseApartment | 24 |
| Outpatient | 162 |
| PrimarySchool | 51 |
| QuickServiceRestaurant | 14 |
| RetailStandalone | 22 |
| RetailStripmall | 15 |
| SecondarySchool | 60 |
| SmallHotel | 96 |
| SmallOffice | 9 |
| SuperMarket | 60 |
| Warehouse | 15 |

| Residential class | Source configurations |
| --- | ---: |
| HighriseApartment | 1 |
| ManufacturedHome | 3 |
| MidriseApartment | 1 |
| MultiFamily2To4 | 3 |
| MultiFamily5PlusLowRise | 6 |
| SingleFamilyAttached | 5 |
| SingleFamilyDetached | 22 |

The 41 residential configurations retain jointly selected energy options, exact
argument-bearing option references, source height/area/climate/vintage context,
and field provenance. There are 524 unmatched option instances, spanning 16
parameter/option pairs, and six flagged raw thermostat base overlaps. No replacement
options, exact area, hourly profiles, natural infiltration or HPXML defaults are
invented. Every recipe has simulation_ready=false and explicit runtime gaps.
The [machine-readable report](validation/coverage.json) lists expected sets,
per-template observed counts and unresolved-instance counts.

## Scientific limitations and their treatment

| Input or question | v0.2.0 treatment | Required resolution |
| --- | --- | --- |
| Final generated-model equivalence | Source-input comparison only; no EnergyPlus/OpenStudio run | Execute pinned generator/toolchain and compare IDF/scorecard inputs after overrides |
| Direct DOE/PNNL benchmarks | Tested official Medium Office links returned 404 | Locate an official working archive, pin bytes and verify redistribution terms |
| Existing building age versus code era | Explicit existing benchmark/code rule families | Model retrofit/deterioration/replacement states as separate variants |
| Legacy pre-1980 mass-floor U=0 | 16 normalized U-values null; original zero and reason retained | Inspect original model/generator to interpret source anomaly; do not choose a substitute silently |
| Final envelope assembly | Conditional U/SHGC/VT limits/targets and original predicates | Choose compatible assemblies, glazing fractions, thermal mass and films |
| Infiltration | Canonical program rate/basis null; ResStock argument evidence retained | Apply source model rules with explicit pressure, exposed area, units and schedule basis |
| HVAC efficiencies, fuel and terminals | Source system types/descriptors; conditional equipment rules; unresolved fields null | Resolve capacity, climate, fuel, subtype, control and generator-specific terminal defaults |
| Program area fractions and conditioned state | Explicit null; source names and benchmark multiplicity retained | Obtain them from the geometry atlas or evaluate the complete source model |
| Multiple HVAC services | Multiple mapping groups may include the same space | Select source-defined services; do not sum multiplicities across overlapping systems |
| Calendar/schedule export | Exact constant/hourly dated rules with design days | Choose year, holiday treatment, weather/design days, leap/DST policy and simulation adapter |
| Complete ResStock apartment variants | 41 source configurations plus standards apartment programs | Assemble complete HPXML/unit configurations including adjacency, appliances, defaults and schedules |
| ComStock release compatibility | Independent pinned options/generator and standards revisions | Pin a full ComStock run/environment before claiming exact generated-model compatibility |
| Gas, SWH, activity and secondary gains | Canonical gas load/activity/SWH schedules plus complete original program rows | Normalize secondary heat fractions, peak SWH flows, moisture, exhaust and other program-specific fields in later schema revisions |
| Refrigeration and additional typologies | All named types ingested; refrigeration conditional rule evidence retained | Resolve specialized generator process loads and equipment selections before simulation |

These are explicit boundaries of a source-input research release. A downstream
model builder must reject or deliberately resolve required nulls and conditional
inputs rather than treating them as zero, unconditional limits or completed
HVAC performance. Units in original evidence remain source-specific.
