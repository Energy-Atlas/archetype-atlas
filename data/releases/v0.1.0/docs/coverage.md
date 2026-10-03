# v0.1.0 coverage and unresolved inputs

The first release contains deterministic source inputs from OpenStudio Standards
and explicit ComStock/ResStock option evidence. It covers energy semantics at
source program resolution, without national prevalence weighting.

| Prototype building type | Program rows across selected templates |
| --- | ---: |
| MediumOffice | 10 |
| RetailStandalone | 22 |
| RetailStripmall | 15 |
| SmallHotel | 96 |
| LargeHotel | 83 |
| QuickServiceRestaurant | 14 |
| FullServiceRestaurant | 14 |
| MidriseApartment | 24 |
| HighriseApartment | 18 |

The five template families provide 43 building/template combinations. High-rise
apartment is absent in the two DOE reference selections. Program rows include
source plenum/support programs where tagged, rather than silently discarding
their semantics. There are 22 envelope climate-zone sets (some thermal-only,
some moisture-specific), all retained without invented moisture-zone duplication.
No source-tagged space was excluded by the exact program lookup in this selection.

## Scientific limitations and their treatment

| Input or question | v0.1.0 treatment | Required resolution |
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
| Complete ResStock apartment variants | Deterministic dwelling options plus standards apartment programs | Assemble complete HPXML/unit configurations including adjacency, appliances, defaults and schedules |
| ComStock release compatibility | Independent pinned options/generator and standards revisions | Pin a full ComStock run/environment before claiming exact generated-model compatibility |
| Gas, SWH, activity and secondary gains | Canonical gas load/activity/SWH schedules plus complete original program rows | Normalize secondary heat fractions, peak SWH flows, moisture, exhaust and other program-specific fields in later schema revisions |
| Refrigeration and additional typologies | Supermarket, schools, health care, warehouses and large office inventoried but not ingested | Add their program/system/end-use-specific schema coverage before simulation |

These are explicit boundaries of a source-input research release. A downstream
model builder must reject or deliberately resolve required nulls and conditional
inputs rather than treating them as zero, unconditional limits or completed
HVAC performance. Units in original evidence remain source-specific.

## Prioritized next releases

1. Recover direct DOE/PNNL IDFs/scorecards and validate generated Medium Office
   and apartment models with pinned OpenStudio/EnergyPlus versions.
2. Resolve constructions, infiltration, conditioned states, thermostat/system
   overrides and capacity-dependent HVAC performance in a simulation adapter.
3. Assemble a small number of fully specified ResStock multifamily variants;
   retain deterministic enumeration and full component-level source provenance.
4. Add supermarket refrigeration and large office/high-rise commercial programs,
   followed by schools/health care, then retrofit and schedule variants.
