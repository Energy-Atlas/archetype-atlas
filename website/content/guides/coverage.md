# Gap to a near-complete schedule release

All **16 DOE Reference types, 16 PNNL commercial types and seven residential
classes** have named source-input coverage. The atlas includes 83 commercial
type/template combinations, 768 program records and 41 dwelling configurations.
This establishes typology coverage, not every schedule or every stock variant.

The current schedule assessment applies supplement **v0.3.0**. Attic, plenum and
basement programs are excluded from the active milestone, leaving **734 programs**.
Seven schedule fields per program give **5,138 assessed fields**; **4,615 are
supplied** by source references or explicit resolutions (**89.8%**).

| Remaining commercial field | Gaps |
| --- | ---: |
| Fixture/service-water draw schedule | 485 |
| Heating setpoint schedule | 19 |
| Cooling setpoint schedule | 19 |
| Occupancy, lighting, electric and gas equipment schedules | 0 |
| **Total** | **523** |

Most remaining commercial fields are water assignments. The Medium Office
[water-equivalent pilot](hot-water.md) validates allocation and conservation of
an already supplied source schedule; it does not reduce these 485 gaps.

## Residential profiles

For 41 configurations, 14 explicitly assessed columns give **574 profile fields**.
Current executed profiles and explicit resolutions supply **473 (82.4%)**;
**101 column/record pairs** still lack a supplied profile. These counts are fields,
not households, buildings or missing generators.

| Remaining residential column | Gaps |
| --- | ---: |
| Refrigerator | 38 |
| Freezer | 38 |
| Interior lighting, other plugs, TV plugs, cooking and fixture water | 3 each |
| Clothes washer, clothes dryer, dishwasher and their two appliance-water columns | 2 each |

The refrigeration gaps include source-selected absences that can support future
reviewed zeros; they are not all positive appliance needs. The three zero-occupant
records have fixed refrigerator defaults, two fixed freezer defaults and one
freezer zero, but occupancy zero does not justify zeroing every other end use.
Occupancy, nominal heating/cooling setpoints and ceiling-fan columns are supplied
for all 41 configurations.

Additional end uses need a separate applicability review: EV and exterior lighting
have no exported columns for any configuration. **Two** fixtures select EV chargers;
**39** explicitly select none. Exterior-lighting applicability and other specialized
uses, such as pools/spas and ventilation controls, are not covered by the 14-column
denominator. These boundaries prevent a claim of complete residential schedules.

## Scope and release order

**HVAC equipment-unavailability overlays are excluded** by user decision. Nominal
desired-temperature schedules are the baseline. Archived unavailability options
remain traceable; missing placement of interruptions is no longer a release gap.
Complete magnitudes and full-model control application are also outside this
schedule milestone. Reference-location fan/lighting variants and direct generated
DOE/PNNL model equivalence remain separate evidence tasks.

Near-full deterministic coverage precedes shipping ResStock or ComStock parametric
generators. No numeric milestone threshold has been asserted. Close the active
schedule assignments and selected residential end uses, or explicitly classify
their applicability, before claiming that milestone.

[Machine-readable per-record gap inventory](../schedule-coverage.json) includes
the exact fields, record IDs, building types, templates and release-scope policy.
Its counts describe the supplied atlas configurations, not all possible climates,
code editions, equipment selections or existing-stock combinations.
