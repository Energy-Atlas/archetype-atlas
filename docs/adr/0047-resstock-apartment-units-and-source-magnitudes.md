# ADR 0047: ResStock apartment units and source-magnitude binding (generator 3.0.0)

Status: accepted for generator 3.0.0 (2026-10-28). The choices are user decisions O15 to
O21 (plan `docs/superpowers/plans/2026-10-17-generator-restructure.md`, sections 7 and 8;
ledger rulings 181 to 191). Choices the plan left open are agent decisions, listed in
section 6. Amends ADR 0021, ADR 0022, ADR 0023, ADR 0027 and ADR 0029 (section 7).

## 1. Context

- **Two upstream bindings.** ComStock fixes a load's rating (W/m², or a peak flow) and
  rewrites only schedule values, so a load's annual energy follows the sampled hours.
  OpenStudio-HPXML fixes a dwelling's annual energy per end use and fits the design level
  to the generated schedule (`calc_design_level_from_annual_kwh`,
  `calc_peak_flow_from_daily_gpm`).
- **Generator 2.x held every annual total.** It fixed each load's annual total from the
  source magnitude on the original shape, then fitted the amplitude to the sampled shape.
  A catalogue scan (seeds 42 and 51, 5,778 loads) put the peak above the installed rating
  in 53 % of lighting, 45 % of plug-load, 23 % of gas-equipment and 27 % of shared-water
  cases (up to 1.46× power and 2.11× flow), and cancelled the annual spread ComStock's
  hours sampling produces.
- **Apartment units were hybrids.** An apartment unit took the prototype's plug, lighting
  and hot-water densities on ResStock occupancy and lighting timing. In a 40-unit test
  (90.1-2007 high-rise, 80 m², Hickory NC) the prototype schedule drew 30 % of a
  one-resident unit's hot water while the unit was empty.

## 2. Decisions (user)

1. **Commercial loads bind their source magnitude (O15).** Lighting, plug loads, gas
   equipment and shared hot-water services keep their density or peak flow as the
   amplitude; the annual total is `amplitude × Σ generated values × s`, an output of the
   draw. Fixed programmes bind the same way (their shapes are the source rules, so their
   totals are unchanged).
2. **ResStock dwellings keep their annual totals (O17).** No residential fixed rating.
3. **Apartment units are ResStock multifamily units (O16, O21).** Every internal load of a
   unit (lighting, plug loads, television, appliances, refrigeration, fuel loads, ceiling
   fans) takes ResStock's value and schedule from one draw per unit. The lamp mix is
   sampled from ResStock's multifamily options. This replaces the prototype's lumped plug
   density and additional lighting.
4. **Method: port both parts (O21).** ResStock's housing-characteristics sampler for the
   apartment closure, and the OpenStudio-HPXML annual equations, validated against the
   pinned Ruby rather than drawn from a record pool.
5. **Controls as upstream (O18).** Commercial setpoints and activity stay
   hours-transformed. An apartment unit takes the thermostat options of its own draw
   (setpoints, setback size and period) and ResStock's constant activity. Setpoints depend
   on climate zone, building type, HVAC type and tenure, not on the occupancy draw.
6. **Apartment hot water (O19, O20).** Volumes are not borrowed from ResStock fixtures or
   appliances. A unit's annual volume is the prototype's volume per design person × the
   unit's residents (P2), timed by the unit's own ResStock fixture events, with the peak
   fitted to the draw. The per-person figure pairs two fields of the same
   openstudio-standards space type: the per-apartment peak flow on the prototype schedule
   (4,592 full-load hours) over the design occupants, 66.33 L/person·day at 60 °C for
   every template and both DOE Ref vintages.
7. **Sampler conditioning: climate zone × programme.** The IECC 2004 climate zone from the
   request, or drawn from the request's state; every state in the zone is pooled, chosen by
   its share of the zone's matching units (county and PUMA summed out within each cell); the unit's floor-area bin; the template's era
   (`Vintage`); the prototype's building type, height class and HVAC (heating fuel,
   heating type, cooling type, shared system, zonal electric heating). Residents in two
   modes: the caller's count, on which the draw is conditioned, or `"resstock"`, which
   draws them, vacancy included. Where the zone has no unit with the prototype HVAC (only
   Alaska's 7AK and 8AK: no 5+ unit apartment there has central AC or a ducted heat pump),
   the HVAC condition is dropped and `generation.relaxation` records `hvac`; otherwise
   `none`. Of 666 state × zone × programme cells, 654 match fully and 12 (Alaska) drop the
   HVAC.
8. **Accepted gaps.** Common laundry: ResStock gives in-unit appliances or none, so shared
   laundry rooms are not represented. Gas loads in units are kept as sampled.
9. **Commercial daylighting and density.** The ADR 0044 daylighting controls stay as
   programme records; lighting density is the template's code value.
10. **Versioning and delivery.** Request and bundle schema 3.0.0 (2.0.0 requests are no
    longer accepted); one branch and one pull request.

## 3. Method

- **Pins.** `sources/resstock-characteristics-lock.json`: 185 files at ResStock revision
  dd25369f (67 characteristic tables, 102 option tables, `options_lookup.tsv`, the
  OpenStudio-HPXML and ResStock measure sources, the licence), each equal to the pinned
  commit archive member apart from line endings.
- **Tables.** `scripts/build_resstock_characteristics.py` keeps the multifamily rows and
  writes per-state shards (`atlas_schedules/data/residential/characteristics/`, 6 MB
  gzip; `--check`).
- **Sampler.** `atlas_schedules/residential/characteristics.py`: an exact posterior over
  climate zone, county-and-PUMA cell, ACS building type and vintage, with the household
  (vacancy, tenure, income, bedrooms) and HVAC likelihoods summed out; hidden variables
  drawn from their exact conditionals, the rest forward in dependency order. Its own PCG64
  stream (`SeedSequence([unit_seed, 0x52455343])`) leaves the schedule streams unchanged.
- **Arguments and equations.** `residential/arguments.py` maps the draw to measure
  arguments and option properties; `residential/annual.py` ports the annual equations
  (RECS 2020 equivalent bedrooms, appliance cycles, plug-load, television and lighting
  regressions, usage multipliers).
- **Unit.** `residential/apartment.py` runs the ResStock schedule generator for the unit's
  residents and installed appliances, fits each load's design level to its schedule
  (`W/dwelling`, basis `dwelling_unit`) and gives the water owner `m3/s/dwelling`.
- **Recipes.** `scripts/build_apartment_units.py` writes the 38 apartment-unit recipes
  from release 2.0.0: Midrise (4 stories, 31 apartments) as
  `Multi-Family with 5+ Units, 4-7 Stories` with a gas furnace and central AC; Highrise (10
  stories, 79 apartments) as `8+ Stories` with a ducted heat pump; eras 90.1-2007 2000s,
  90.1-2013 and 2019 2010s, DOE Ref Pre-1980 up to the 1970s and 1980-2004 the 1980s to
  2000s. Each recipe's `resstock_unit.source` names the geometry, systems and recipe it
  came from.

## 4. Validation

- Sampler: matches an independent rejection sampler on two conditionings.
- Arguments: 5,867 of 5,867 argument values of 41 recovered ResStock records equal the
  Ruby inputs.
- Annual equations: 240 sampled units in 12 states, 21 end uses, all within 1e-9 relative
  of the pinned Ruby methods under OpenStudio 3.10.0
  (`docs/validation/resstock-annual-equivalence.json`; answer key
  `tests/answer_keys/resstock-annual.json`).
- Hot water: 0.6 % of a one-resident unit's water falls in hours the unit is empty, against
  30 % under the prototype schedule; the residue is upstream fixture events that outlast a
  departure.
- Commercial binding: every legacy and native case keeps its shapes; the legacy totals
  now differ by exactly the ratio of source to fitted amplitude
  (`tests/schedules/helpers.py`, `assert_binding`).
- Before and after (`docs/validation/generator-3-0-0-before-after.md`, every 10th
  commercial recipe at seeds 42 and 51): annual lighting is 0.79 / 0.84 / 1.14 × the 2.x
  total (p05 / median / p95) and plug loads 0.75 / 0.91 / 1.36 ×; under 2.x the peak
  exceeded the rating in 62 % of lighting and 45 % of plug loads. 80 m² apartment units in
  climate zone 4A (Hickory NC, every 4A state pooled) use a median 2,790 to 4,390 kWh/yr of
  electricity for 1 to 4 residents (Midrise) and 3,000 to 5,050 kWh/yr (Highrise), against
  4,040 and 3,680 kWh/yr under the 2.x prototype densities.
- Climate zone × programme: of 666 state × zone × programme cells, 654 match every
  programme condition and the 12 Alaska cells drop the HVAC.
- Schedules suite (92 tests) on Python 3.14 and 3.11; catalogue smoke with no failures.

## 5. Consequences

- A commercial load's annual energy varies with the sampled hours, and its peak is the
  rating × the sampled schedule's largest fraction, as in ComStock.
- Mixtures weight member shapes by `factor × amplitude`, now the source magnitudes; the
  mixed annual total is still the scaled sum of member totals.
- An apartment unit needs a floor area and a location; its loads are per dwelling unit.
- Release 2.0.0's `generator.json` keeps the 2.x apartment recipes; the next release
  carries the ResStock unit recipes.

## 6. Agent decisions

- A unit's exterior and garage lighting are left to the building: the prototype's
  exterior lighting covers the site, and a unit has no garage.
- Pools are not modelled in units: the closure has no pool heater or pump
  characteristics.
- A unit without `location.weather_id` takes the nearest packaged TMY3 station in its
  state for ceiling-fan months.
- Fixture events that outlast a departure stay as upstream.
- ResStock has no water-loop heat pump, so the high-rise water-to-air heat pumps on a
  shared loop become a unit's ducted heat pump with no shared system.
- A caller resident count with no ResStock match in its floor-area bin fails; residents
  and floor area are never relaxed.

## 7. Amendments

- **ADR 0021** (commercial transform): effective amplitudes fitted to fixed annual
  targets give way to source magnitudes; annual energy and volume are outputs of each
  draw.
- **ADR 0022** (generator recipes): `apartment_unit` recipes carry `resstock_unit` and
  `caller_water` only; the prototype slots, demands, controls and `unit_timing` are gone.
- **ADR 0023** (mixtures): member targets are their generated totals, so the mixed target
  is the scaled sum of generated totals rather than of original targets.
- **ADR 0027** (shared services): a service's per-area peak flow binds the sampled
  schedule; its original per-area annual volume is no longer held.
- **ADR 0029** (caller-unit fixed DHW): apartment water is P2 per resident with the unit's
  fixture timing, not the prototype density × floor area on the prototype schedule.
