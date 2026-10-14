# Construction ACH: recovered reference geometry and climate proposals

Recovery date: 2026-10-13. Decisions accepted: 2026-10-14. Scope: above-ground construction only.
Ground/foundation and systems delivery remain deferred. These are source evidence
and proposals; they do not certify the construction release as 100% ready.
F1, F2, F3 and G1 were explicitly accepted below. Blank comments on other
review items remain unanswered, including all deferred H/X system items.

## Accepted basis

Ship a fixed catalogue natural ACH for each construction/climate/reference
variant. Derive it from source archetype reference geometry, then reuse the
selected constant across consumer geometry and zoning variants. Reference form
is derivation evidence; it does not require selecting a program JSON. Separate
construction elements can share the same physical recipes across reference forms.
Keep ASHRAE climate labels/groups as applicability, with no station/location axis.

## What has been recovered

The [geometry evidence](../../data/construction-inputs/geometry-v1.json) contains
41 residential fixtures, 129 commercial reference cases and dispositions for
all 183 construction packages. Source revisions, file/archive hashes, native
values, units, transformations and extraction notes accompany the recovery.
The [candidate climate evidence](../../data/construction-inputs/climate-factor-candidates-v1.json)
contains 42 reference-forcing calculations across two source map editions.

| Field or relationship | Coverage and interpretation |
| --- | --- |
| Residential conditioned floor area and volume | 41/41; execute source argument/default rules, rather than borrow a program-load scalar |
| Residential infiltration height and test volume | 41/41; retain the source pressure boundary, including foundation adjacency where its geometry affects the leakage reference |
| Residential pressure-test normalization and exterior fraction | 41/41; 25 detached/manufactured cases have fraction 1; 16 attached cases have source fractions 0.1818–0.89567 |
| Residential terrain, shielding and attached walls | 41/41 source/default recovery; neighbor distances retained, unreported neighbor heights remain null |
| Commercial geometry, space volume, exterior areas, vertical extent and multipliers | 129/129 source reference cases; retain space scopes and apply multipliers once |
| Commercial terrain | 129/129; 69 explicit City, nine explicit Suburbs, 51 pinned SDK Suburbs defaults |
| Commercial construction-package reference match | 182/183; one exact space scope is not instantiated in its pinned model, recorded separately below |
| Generic Any/Office mapping | All 15 packages have reference matches, with source scope and compatibility/default distinctions retained |
| Released constant natural ACH | Still pending climate/conversion decisions and commercial leakage-path recovery |

Medium Office / 90.1-2019 has 4,982.186 m² represented floor area, a source
height span of 11.8872 m and explicit City terrain. Its 19,741.413 m³ all-space
volume includes plenums; it is not silently used as a conditioned-volume
denominator. The residential fixture in a 15-storey building has one conditioned
dwelling storey, an 8 ft (2.4384 m) infiltration height and exterior fraction
0.1818. Building storey count is not substituted for dwelling leakage height.

Foundation dimensions were examined only where needed to preserve the source
pressure boundary. No ground heat-transfer model, foundation contract, HVAC,
water-heater model or program export was generated. The source annual-average
residential helper does not require the unreported neighbor heights; those
nulls are not asserted to be zero.

## Generic commercial mappings

Each of the five Office packages has six source compatibility references:
SmallOffice, MediumOffice, LargeOffice and their three Detailed forms. Specific
whole-building construction defaults remain distinct from the compatibility
lookup. There is no arbitrary choice of Medium Office or averaging of forms.

The ten Any packages describe **Attic or Plenum** space sets. Reference forms
are found through those source space scopes, not every program in a building.

| Template | Any Attic references | Any Plenum references | Office compatibility references |
| --- | ---: | ---: | ---: |
| DOE Ref Pre-1980 | 2 | 2 | 6 |
| DOE Ref 1980-2004 | 5 | 2 | 6 |
| 90.1-2007 | 4 | 3 | 6 |
| 90.1-2013 | 4 | 3 | 6 |
| 90.1-2019 | 4 | 3 | 6 |

The receipt retains the exact reference IDs and source lookup contexts. SmallHotel
story overrides are evaluated from the source's exterior-space residential area
fraction and retain their affected spaces. Referencing geometry does not assert
that every reference space uses a generic package as its default.

## F1 — Reference climate map and resolution

**Gap/reason:** An ASHRAE climate label does not uniquely define a weather/shielding
factor. The pinned standards source supplies both 169-2006 and 169-2013 reference
maps. Those maps can yield materially different factors at the same label.

**Proposal:** Use the pinned **169-2013 reference map consistently across the
catalogue**, including legacy/code vintages, as an explicit experimental reference
forcing choice. Keep original stock/code identities. Resolve ACH by full ASHRAE
labels such as 3A/3B/3C, while sharing assemblies that the source groups together.
This avoids introducing a weather-map change when comparing construction vintages.
Weather source paths/checksums remain provenance, not catalogue location choices.

**Alternative:** Use the 2006 map for selected older references and 2013 for newer
ones. This preserves separate reference conventions, but changes derived ACH
because of forcing as well as construction. A group average would instead require
an explicit subzone weighting policy; no population weights or A/B/C average is
proposed.

The following are **candidate residential WSF values**, dimensionless and rounded
by the pinned helper. They are not commercial factors or released ACH:

| ASHRAE label | 2006 map WSF | Proposed 2013 map WSF |
| --- | ---: | ---: |
| 0A | 0.37 | 0.37 |
| 0B | 0.43 | 0.43 |
| 1A | 0.41 | 0.42 |
| 1B | 0.47 | 0.38 |
| 2A | 0.42 | 0.38 |
| 2B | 0.43 | 0.45 |
| 3A | 0.46 | 0.46 |
| 3B | 0.48 | 0.48 |
| 3C | 0.60 | 0.40 |
| 4A | 0.50 | 0.57 |
| 4B | 0.54 | 0.54 |
| 4C | 0.55 | 0.56 |
| 5A | 0.60 | 0.65 |
| 5B | 0.56 | 0.60 |
| 5C | 0.58 | 0.57 |
| 6A | 0.61 | 0.70 |
| 6B | 0.63 | 0.71 |
| 7A / 7B | 0.70 | 0.65 |
| 8A / 8B | 0.70 | 0.70 |

For unchanged residential reference geometry/leakage, changing map edition
changes the candidate scalar in direct proportion to WSF: 3C changes by −33.3%,
4A by +14.0%. Source 7A/7B and 8A/8B aliases use identical reference forcing;
retain the original source labels without inventing different factors.

**Your comments / answer:**

<!-- comments:ACH-F1:begin -->
2026-10-14: Use one 2013 reference map (accepted).
<!-- comments:ACH-F1:end -->

## F2 — Residential constant conversion

**Gap/reason:** ACH50 is a pressure test. A source-derived constant needs an
explicit natural-infiltration convention; a universal ACH50/20 divisor is not
source recovery.

**Proposal:** Use the pinned source annual-average natural ACH helper:
pressure-normalize to ACH50, calculate SLA and normalized leakage using the
recovered pressure-boundary height/volume, apply F1's WSF, then apply the source
exterior fraction. Store the result in SI (1/s) with an inspection ACH (1/h).
The evidence already retains the coefficient per unit WSF for all 41 fixtures;
it is a sensitivity calculation, not an adopted natural ACH value.

This helper uses a standardized weather/shielding convention. Its fallback WSF
calculation includes 22°C indoor temperature, one-storey/flue reference shielding
and its other pinned constants. The scalar helper does **not** use each fixture's
individual terrain/shielding/neighbor distances as the dynamic AIM-2 model does.
Those source fields remain evidence. Adoption therefore selects the source's
annual-average convention, not a claim of literal hourly AIM-2 flow or annual
heating/cooling-energy parity. Recovering a dynamic-flow annual mean is an
alternative requiring additional source operands and an indoor-temperature policy.

**Your comments / answer:**

<!-- comments:ACH-F2:begin -->
2026-10-14: Source annual-average helper (accepted).
<!-- comments:ACH-F2:end -->

## F3 — Commercial climate factors and operating reference

**Gap/reason:** The pinned commercial generator uses NIST temperature/wind
correlations, building-type inference and separate system-on/off coefficients.
Its factor is not the residential WSF and is not one universal multiplier for
every commercial form. Door-opening additions also depend on operation.

**Proposal:** Recover the source commercial leakage path and coefficients, then
derive a constant passive-envelope reference with **22°C indoor temperature and
the system-off correlation throughout the year**, using F1 forcing and source
geometry/terrain. Exclude mechanical pressurization and operational door-opening
additions from this construction scalar; retain their evidence for later scope
discussion. This is a proposed definition, not an assertion that all source
buildings actually operate in that state. Retain the source inferred correlation
type and any source surrogate mapping explicitly.

For the source form `a + b*abs(T_inside-T_outside) + d*wind²`, evaluate the actual
source/EnergyPlus wind-height convention before averaging. Use the source
surface-area normalization, geometry multipliers and eligible volume consistently.
Do not use the all-space volume above as a conditioned-volume default. Validate
Medium Office before expansion. The source's climate-0-to-1 correlation fallback
must be labelled as source fallback if used; no new climate-0 fit is proposed.

For example, Medium Office's source no-air-barrier system-off CZ4 coefficients
are a=0, b=0.0174 and d=0.0341. Proposed 2013 4A forcing has mean
abs(22°C−outdoor)=10.93 K and mean weather-file wind²=30.16 m²/s². These are
recovered diagnostic operands. The weather-file wind moment is **not** yet a
zone-height wind factor, so no commercial natural ACH is reported from them.
The source air-barrier/leakage selection still needs to be traced per variant;
these example coefficients are not assigned universally.

The [NIST implementation guide](https://www.nist.gov/publications/implementing-nist-infiltration-correlations-0)
documents the commercial correlation implementation. The executable evidence
uses the pinned standards source and its coefficient JSON, rather than updating
physics to an unpinned current source.

**Your comments / answer:**

<!-- comments:ACH-F3:begin -->
2026-10-14: Passive-envelope reference (accepted).
<!-- comments:ACH-F3:end -->

## G1 — SmallHotel 2019 generic GuestRoom reference

**Gap/reason:** `construction-1d0774872c8801caa0afdd44` exists in the source set
table, but its exact GuestRoom space type is absent from the pinned reference
model. That model uses GuestRoom123Occ/Vac and GuestRoom4Occ/Vac. The recovery
records `source_scope_not_instantiated`, with the whole SmallHotel reference
retained as an unassigned candidate. It is not silently equivalent to any room.

**Proposal:** Keep the generic assembly set and use the same whole-SmallHotel
enclosure reference for its **package-level** leakage benchmark, explicitly
recording that its room scope was not instantiated. Do not invent a GuestRoom
area, volume or program assignment, and do not merge it with a more specific
guest-room construction. If package leakage must instead be room-specific, this
case needs a separately agreed room-reference geometry and remains open.

**Your comments / answer:**

<!-- comments:ACH-G1:begin -->
2026-10-14: Use whole SmallHotel reference (accepted).
<!-- comments:ACH-G1:end -->

## Verification and next work

Native recovery executed all 41 residential and 129 commercial cases. Derived
runtime geometry is reported at nine significant digits to remove floating-point
area-sum noise; literal source construction-set parameters are not rounded. Focused
tests check SI conversion, apartment versus building height, exposure bounds,
template/space-scope mapping, residential hotel overrides, terrain preservation,
and incomplete/orphan evidence rejection. Eight focused tests pass. Independent review found three issues
in the first pass; all were repaired and their regression tests passed. Replayed
all 41 residential fixtures, five commercial pilots (including Medium Office,
SmallHotel overrides and a supertall case), and all 42 climate candidates. Source
file and script hashes are checked separately from the numeric replay.

These four reference decisions are now settled. Remaining above-ground work includes residential assembly translation, omitted
door/skylight/window selector closure, the final construction schema/exporter,
and the complete ready-export receipt. The original recovery pass did not regenerate
program JSON, frozen releases, the site or full CI.

## Adopted calculation boundary (2026-10-14)

The commercial prototype entry point calls NIST infiltration without overriding
its defaults: 13.8 m³/h/m² at 75 Pa, 5-sided area normalization, pressure exponent
0.65, no air barrier. The defaults apply through this pinned generator path;
they do not assert that every existing building or code vintage has identical
measured leakage. Source building-type surrogates remain explicit. Missing
system-off coefficient fields use the corresponding system-on field, including
the constant term, as the executable source does. Climate 0 uses climate-1
coefficients while retaining climate-0 forcing.

Commercial reference ACH divides summed passive volume flow by the **whole
source enclosure air volume**, with source multipliers and interior/plenum
spaces included. This is an enclosure benchmark, not a conditioned-volume
assertion. The source normalization areas are unmultiplied as in its NIST
method; final summed volume flow and enclosure volume use space multipliers.
The reference holds every source space at 22°C and sets the off schedule to one.
Operating door additions and mechanical pressurization remain excluded.

The calculation averages nonnegative correlation volume flow over equally
weighted hourly samples in the pinned reference EPW. Temperature and wind use
the source terrain and zone-centroid height rules, with EnergyPlus 25.1 defaults
for weather-station sensors (wind 10 m, temperature 1.5 m), wind profile and
temperature lapse rate. This does not claim parity with timestep-interpolated
weather, dynamic indoor temperatures, AIM-2 airflow or annual energy.
The [pinned engine source](https://github.com/NatLabRockies/EnergyPlus/tree/1c11a3d85f8a3e4ff9918dfe1f6b0e7ec1fd701c/src/EnergyPlus)
and its checksum lock identify the algorithms used.

Residential results retain each fixture's original climate applicability.
Source labels `7AK` and `8AK` retain their identity; the adopted source map has
identical 7A/7B and 8A/8B forcing respectively. Both aliases are recorded without
inventing a moisture class. This does not introduce a station/location axis.

Pilot derivation: Medium Office / 90.1-2019 / 4A is 0.139696 ACH with
19,741.413384 m³ reference enclosed volume. Residential `source_building_101526`
/ 5A is 0.671608 ACH. The 15-storey-building apartment fixture
`residential_archetype-3432edeeb8c2e19f2a8b` / 4C is 0.104994 ACH, using its
one-storey dwelling pressure boundary and recovered exterior fraction.

The commercial supplement keeps the accepted `geometry-v1` volume operands.
Two LargeOffice basement SDK replays differed by 0.021547 m³ (0.00113%) from
those operands despite unchanged pinned source files. The precise cause is
unverified. Recovery compares observed volumes with the pinned operands and
rejects relative disagreement above 0.002%; it does not change the reference
denominator or round away the disagreement. The full source surface census has
no nonhorizontal polygons with more than four vertices. Future such surfaces
are rejected pending translated-engine centroid recovery, rather than assuming
that preprocessing leaves their centroid height unchanged.

## Completed derivation and focused validation

The [fixed-ACH evidence](../../data/construction-inputs/fixed-ach-v1.json) contains
41 residential constants in their source fixture climates, 2,709 commercial
reference/climate benchmarks (129 forms × 21 full labels), and 183 resolved
package reference mappings. The [commercial geometry supplement](../../data/construction-inputs/commercial-ach-geometry-v1.json)
retains source normalization areas, exterior-area operands, centroid heights,
volumes/multipliers, terrain and native NIST operands. Package mappings do not
choose or average different reference forms, and the benchmarks do not create
new assembly/climate applicability.

Reproduction uses the existing locked Standards/ResStock/OpenStudio inputs and
the additional checksum-locked engine source files:

```powershell
.venv/Scripts/python.exe -m scripts.derive_construction_ach --recover --pilot
.venv/Scripts/python.exe -m scripts.derive_construction_ach --recover
.venv/Scripts/python.exe -m scripts.derive_construction_ach --check
.venv/Scripts/python.exe -m unittest tests.test_construction_ach tests.test_construction_geometry_recovery
```

`--check` reuses the verified native supplement and checks deterministic output
without running all source models again. Changed Python/Ruby derivation inputs
or geometry/source/weather files fail the checks. `--recover` runs the geometry
and NIST source methods only, with no HVAC sizing or ground heat-transfer solver.

Nineteen focused tests pass. A fresh full native recovery and deterministic
derivation check pass. Focused native replay matches Medium Office, Large Office,
SmallHotel and a supertall reference. All 41 residential constants match direct
calls to the pinned annual-average helper using the adopted WSF within the
declared reference-geometry precision. Independent review verified full census,
mapping, source operands and unit/physical consistency after both reproducibility
findings were repaired. The final above-ground consumer release remains pending.
