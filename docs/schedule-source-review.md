# Schedule source review — 2026-10-04

This is the historical source review underlying the initial overlays. Current
coverage and later executed decisions are in
[v0.4.0 release notes](release-notes-v0.4.0.md); source nulls remain unchanged.

This review addresses the user's follow-up annotations. The scientific decisions
are in [ADR 0005](adr/0005-parametric-schedule-generators.md). Source facts are
separate from adopted experimental zeros. The immutable atlas v0.2.0 and
resolution supplement v0.1.0 are retained. New supplement v0.2.0 adds sixteen
approved zero profiles; its schema adds `reviewed_no_lighting`.

## Gas-equipment verdict

All 713 missing gas schedules also lack gas-equipment density and additional gas
schedule. Excluding attic/plenum/basement rows leaves 679. All 679 have an electric
equipment schedule; 563 have positive electric density, 107 report zero, nine
have unknown density. These span all 17 commercial types and all five templates.
They include offices, corridors, lobbies, mechanical/support rooms, apartment
units and dining areas. The shared pattern is an absent generic gas component,
not a proved all-electric building.

In pinned `Standards.SpaceType.rb#space_type_apply_internal_loads`, blank gas
density converts to zero; the generic recipe creates no GasEquipment for that
component. The routine explicitly does not alter directly assigned space loads.
Prototype customizations and prior model objects can still supply gas loads.
Electric equipment schedules are not an exhaustive inventory of all fuel uses.

Verdict: **zero generic gas-equipment addition in a clean application of this
recipe is supported**. **Whole-program/building gas absence is unverified**.
These 713 source schedule fields remain unresolved in the present overlay;
they must not imply all-electric buildings. Future component-scoped extraction
can encode the recipe's absence once its application boundary is explicit.
The four separately demonstrated all-electric residential configurations remain
resolved. Positive kitchen/laundry/bakery/deli/medical gas loads are retained.

## Local water demand

All 495 unresolved local water schedules lack peak flow and flow per area as
well as other water fields. None has an exact building-type/space-type match in
the pinned `typical_water_use_equipment.json` source table. `create_typical.rb`
adds no local WaterUseEquipment when the match is empty. This establishes
**no local demand assigned by that recipe**, not absence of real plumbing or a
building service-water loop. Another generator path can allocate demand elsewhere.

Examples: restaurant dining versus kitchen; school classrooms/cafeteria versus
restrooms/kitchen; hotel corridor/office versus guestrooms/laundry/kitchen;
apartment corridor/office versus dwelling unit; supermarket sales/restroom versus
bakery/deli. In particular, lack of local source demand for a supermarket
restroom does not imply that a real restroom has no fixtures.

The existing 29 reviewed local demand zeros remain valid with this bounded
meaning. The 495 additional source nulls are retained pending component-scoped
application; agreement with the recipe interpretation does not establish a
complete model's water-demand inventory.

## Fixed defaults for three zero-occupant fixtures

| Source fixture | Atlas suffix | Class | Reported background equipment |
| --- | --- | --- | --- |
| 165449 | `08a27444abac71d3b335` | Detached single-family | Refrigerator EF 17.6; freezer EF 12 |
| 494980 | `28457c00121833f065f2` | 5+-unit low-rise multifamily | Refrigerator EF 17.6; freezer absent |
| 447245 | `aa1f864c610bf3d98e2e` | Detached single-family | Refrigerator EF 19.9; freezer EF 12 |

Their current exported annual columns are occupancy zero plus nominal heating/
cooling setpoints. The stochastic measure explicitly skips zero occupants.
The newly locked upstream `default_schedules.csv` supplies weekday/weekend and
monthly default shapes for refrigerators, freezers, lighting, plug loads and
other end uses. These are standardized source defaults, not measured histories
of the fixture records. Refrigerator/freezer day shapes are not constant one.
Default refrigerator logic additionally distinguishes supplied fractional shapes
from temperature-dependent coefficient schedules; when no fractions are supplied,
the latter can be selected. Do not silently substitute a fixed daily vector.

Thus source recipes are available and retrieved; record-level background annual
profiles have not been executed or assigned. A future generator interface should
carry upstream conditional defaults and temperature inputs. Installed background
equipment can operate with zero occupants, but occupancy alone does not establish
lighting/appliance usage or magnitudes. Magnitude reconstruction remains outside
this round's scope, as requested.

## Approved zero profiles and excluded spaces

Ten lighting gaps are Medium Office and Large Office ceiling plenums, five
templates each. The load-application routine skips plenums. The user approves
zero modeled lighting for these ten IDs. Six occupancy gaps are the exact
`OfficeLarge Data Center` and `OfficeLarge Main Data Center` source programs,
each across 90.1-2007, 2013 and 2019. The people routine creates no People for blank
density, and the user approves zero routine modeled occupancy. This does not
apply to actual office/staff rooms in data-centre buildings. Their positive
lighting/equipment and thermostat schedules remain present.

Attics, ceiling plenums and basements are excluded from the active gap assessment
by explicit source-space-type selection. Records remain in archival downloads;
their exclusion is not a zero assumption for every end use.

## HVAC unavailable-day cases

Only these ten residential source fixtures have a non-`Never` option. This is
dwelling HVAC availability, not commercial program or room schedules. The other
31 fixtures specify `Never` for both heating and cooling. The full record ID is
`residential_archetype-` plus the suffix below.

| Fixture | Atlas suffix | Class | Heating unavailable | Cooling unavailable |
| --- | --- | --- | --- | --- |
| 452189 | `06edaac3a928a261e3ca` | Detached single-family | 3 days | 3 days |
| 143851 | `16b2dae7d144a14640bf` | 5+-unit low-rise multifamily | Never | 3 days |
| 342177 | `48b913daef16e4a0d395` | Attached single-family | Never | 1 month |
| 428680 | `579950323e90f744b1ad` | 5+-unit low-rise multifamily | 1 day | 1 day |
| 449307 | `6304c2e6e1f5a94661a4` | Midrise apartment | 1 month | 2 weeks |
| 66378 | `6c882dbfcd92f9047b4b` | Detached single-family | Year round | Year round |
| 121706 | `74d83a7105b6797f301c` | 5+-unit low-rise multifamily | 2 weeks | 2 weeks |
| 461465 | `a3d3772f8a0380587cd9` | Detached single-family | 1 week | Never |
| 290025 | `b782a597642c3b89c217` | Detached single-family | 3 months | 3 months |
| 149911 | `c167523c69dac59ce636` | 2–4-unit multifamily | Never | 1 week |

`ResStockArgumentsPostHPXML` determines seasons from weather, chooses a seeded
start day and adds a consecutive unavailable period to HPXML header columns
`No Space Heating` / `No Space Cooling`. With no season it falls back to Dec–Feb
for heating or Jun–Aug for cooling. Year-round is Jan 1–Dec 31. These are source
options; exact placed dates have not been executed in the current schedule-only
runner. A 3-day unavailable period would suppress equipment availability during
those selected days even though the nominal desired-temperature curve remains.
The year-round fixture can retain nominal thermostat profiles while its
equipment is unavailable all year. These are ten raw option cases, rather than
ten confirmed active overrides: fixture 143851 also selects `HVAC Cooling
Efficiency=None` and no cooling partial conditioning. Its three cooling-
unavailable days have no selected cooler to disable. The other nine fixtures
select equipment affected by their unavailable-day options. Full model control
application remains separate from this source-option inventory.

This applicability clarification was added after freezing supplement v0.2.0.
The frozen review remains its dated archival text; its source fixture values and
annual profiles are unchanged.

## DOE reference locations for the next generator design

Use Table 2 of the official [DOE technical report](https://docs.nlr.gov/docs/fy11osti/46861.pdf),
NREL/TP-5500-46861 (February 2011), printed page 7 / PDF page 16. The stable PDF
is SHA-256 locked. The [DOE archive listing](https://www.energy.gov/cmei/buildings/new-construction-commercial-reference-buildings-archive)
uses weather-location names; preserve the distinction from representative cities:

| Climate case | Representative location |
| --- | --- |
| 1A | Miami, FL |
| 2A | Houston, TX |
| 2B | Phoenix, AZ |
| 3A | Atlanta, GA |
| 3B coastal | Los Angeles, CA |
| 3B inland | Las Vegas, NV |
| 3C | San Francisco, CA |
| 4A | Baltimore, MD |
| 4B | Albuquerque, NM |
| 4C | Seattle, WA |
| 5A | Chicago, IL; source weather Chicago-O'Hare |
| 5B | Denver, CO; source weather Boulder |
| 6A | Minneapolis, MN |
| 6B | Helena, MT |
| 7 | Duluth, MN |
| 8 | Fairbanks, AK |

This is 16 location cases, with two 3B variants. Exact EPW station/file choices
are a separate source binding and remain to be pinned; city names alone do not
identify a weather file. Only dependent elements need location variants:
ceiling-fan season (monthly mean outdoors above 63°F / 17.22°C), lighting solar/
location inputs, and unavailable-day season placement. Occupant activity-chain
probabilities do not require EPW weather. Appliance-location temperature is a
separate dependency of some fixed refrigerator defaults.

Hosted CI demonstrated that the HTML page's bytes differ across delivery
environments. Its original local receipt remains in the frozen supplement and
the active lock's historical receipts. It is not a current build dependency.
Evidence lock version 2 uses the stable technical report; fresh retrieval through
the official OSTI redirect and direct report host gave identical PDF SHA-256
`39520427c39c4a424d8b0d072c47d5bfdc248631632e880501866aae6b0d131a`.
The frozen v0.2.0 atlas, profiles, supplement and original receipt are unchanged.

## Reproduction and remaining gaps

Retrieve/verify primary references with
`python -m scripts.fetch --lock sources/schedule-evidence-lock.json`.
Use `--verify-only` to check cached hashes offline. Relevant pinned paths and
method links appear in ADR 0005; original units and semantics remain in sources.

Supplement v0.2.0 has 693 resolutions and 1,270 unresolved commercial fields:
713 gas, 495 water, 24 electric equipment, 19 heating and 19 cooling setpoint
schedules. Scope exclusion removes the 24 electric-equipment gaps and 34 gas /
10 water gaps, leaving 679 gas, 485 water and 38 thermostat fields (1,202 total)
in the active non-cavity assessment. No lighting or occupancy gaps remain.
At v0.2.0, generator shipping, zero-occupant default application, unavailable-day
placement and exact DOE EPW bindings were pending; source fixture outputs
remain available. Non-exported EV and other controls retain their documented gaps.

## Subsequent deterministic-coverage decisions: supplement v0.3.0

The user's next annotation review explicitly approves program gas-equipment
zeros for the 713 clean-recipe cases. Supplement v0.3.0 contains matching zero
fractional schedules and 0 W/m2 densities, with the source nulls retained in the
base atlas. Existing positive/custom loads block the rule. This makes no
whole-building all-electric claim and does not remove gas heating or water heating.

The three zero-occupant cases are fixture 165449 and 447245 detached dwellings,
and fixture 494980 a low-rise multifamily dwelling unit. All three select
refrigerators; the two detached fixtures also select freezers. The apartment's
freezer is explicitly absent and resolved to zero. Shared fixed source-default
weekday/weekend fractions and monthly multipliers provide five refrigeration
profiles, normalized to a maximum of one, without temperature feedback. These
are preprogrammed shapes, not newly executed stochastic/full-model profiles.
Other zero-occupant lighting/plug/water uses remain separately unresolved.

The supplement has 2,125 resolution rows for 754 records and leaves 557
commercial schedule fields unresolved: 495 local water, 24 cavity electric
equipment, 19 heating and 19 cooling. Excluding attic/plenum/basement programs
leaves 523 active gaps: 485 local water and 38 thermostat schedules.

All ten unavailable-day cases above have `Vacancy Status=Occupied` and 1-5
occupants. Vacancy is a separate control from `No Space Heating` and
`No Space Cooling`, as shown by the pinned
[argument definitions](https://github.com/NatLabRockies/ResStock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/measures/ResStockArguments/measure.rb)
and [unavailable-period applicability table](https://github.com/NatLabRockies/ResStock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/HPXMLtoOpenStudio/resources/data/unavailable_periods.csv).
Heating/cooling unavailable-day source documentation cites 2020 RECS; its
sampling dependencies concern poverty level, building type, tenure (cooling),
and cooling unavailability (heating), not vacancy. EIA describes the underlying
survey's inability-to-use questions as broken equipment that households could
not afford to repair or unaffordable energy
([EIA explanation](https://www.eia.gov/todayinenergy/detail.php?id=51979)).
This explains the source context; individual atlas fixtures are synthetic and
do not identify an actual household or a specific outage cause.

Active evidence lock version 3 adds ten pinned primary blobs for these controls
and sampling definitions. Old frozen locks remain unchanged. See
[ADR 0006](adr/0006-deterministic-coverage-release.md) for release sequencing,
fixed shape semantics and the proposed program-level hot-water allocation
equivalent. Generator shipping follows near-full deterministic coverage.

## Current program-water pilot and release exclusions

The user now excludes HVAC equipment-unavailability from the schedule release.
This is a nominal desired-temperature baseline without sampled repair/affordability
interruptions. The raw options and historical notes above remain source evidence;
unexecuted interruption placement is no longer pending coverage work.

The [water pilot](../data/water-releases/v0.1.0/water-equivalent.json) attaches
to the existing MediumOffice / 90.1-2013 office program. Locked prototype inputs
and source code establish its per-space-type water path, and the pinned OSM tags
match 15 distinct office spaces. No new restroom program is invented. The source
curve's maximum is 0.57; normalized fractions and compatible peak-flow scaling
conserve fixture draw for all retained rules. Physical fixture locations remain
unspecified: the heater location is not a demand-location mapping. This supplies
a reviewed equivalent of an already known curve, so it closes zero missing fields.

Gas zeros remain program equipment resolutions with the source nulls preserved;
they do not zero gas heating, gas water heating, custom/direct equipment or imply
whole-building electrification. Both density (0 W/m2) and fraction (always zero)
must be selected deliberately as the resolved variant. The MkDocs schedule methods
and program pages display this scope alongside the original evidence.

See [ADR 0007](adr/0007-program-water-equivalents.md) for water semantics and the
[per-record coverage inventory](validation/schedule-coverage.json) for denominators,
remaining commercial and residential gaps, and the current release exclusions.
