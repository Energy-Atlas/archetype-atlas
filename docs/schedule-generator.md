# Schedule generator

`atlas_schedules` turns a request (programmes, extents, a seed) into 8,760-hour
schedules for 2007 (non-leap, local standard time, hour `[h, h+1)`), with each
load bound to its generated shape as its upstream binds it
([ADR 0047](adr/0047-resstock-apartment-units-and-source-magnitudes.md)). It is a
readable port of the upstream schedule code
([ADR 0035](adr/0035-readable-generator-restructure.md)):

- **ComStock / openstudio-standards 0.8.6**: hours of operation inferred from
  People-weighted occupancy, schedules rewritten relative to those hours, new
  hours sampled from ComStock v33 tables, base-to-peak ratios for lighting and
  plug loads;
- **ResStock / OpenStudio-HPXML `schedules.rb`** (revision dd25369): Markov
  occupant activities, occupancy-driven shapes, appliance and hot-water events;
- **ResStock housing characteristics and OpenStudio-HPXML annual equations**
  (revision dd25369f): each apartment unit is drawn as a ResStock multifamily
  unit, with its appliances, lamp mix, thermostat and annual energy per end use.

Generation needs Python 3.11+, numpy and jsonschema. No OpenStudio, Ruby or
network access is needed at run time.

## Quick start

Install the `atlas-schedules` wheel attached to its GitHub release
([ADR 0049](adr/0049-atlas-schedules-packaging.md); the package is not on PyPI;
the generator version is the package version, 3.0.0):

```bash
pip install https://github.com/Energy-Atlas/archetype-atlas/releases/download/atlas-schedules-v3.0.0/atlas_schedules-3.0.0-py3-none-any.whl
atlas-schedules office-and-retail.json -o bundle.json
```

From a checkout, with `requirements.txt` installed, `python -m atlas_schedules`
runs the same command:

```bash
python -m atlas_schedules docs/examples/schedule-generator/office-and-retail.json -o bundle.json
```

```python
from atlas_schedules import generate
bundle = generate(request)   # request: dict following schema 3.0.0
```

Example requests live in `docs/examples/schedule-generator/`. Each bundle
records its `generator_version`; the packaged recipes of generator 3.0.0 were
built from atlas release 2.0.0 and are carried by release 2.1.0 (ADR 0049).
To build the wheel from a checkout: `pip install -r requirements-dev.txt` and
`python -m build`.

## Request (schema 3.0.0)

The schema is `atlas_schedules/schemas/request-v3.schema.json`.

| Field | Meaning |
|---|---|
| `seed` | Unsigned 64-bit master seed. The same request always gives the same bundle. |
| `occupancy` | Optional residential occupant-type mix: `{"mix": "state" \| "national", "window": "2003-2019" \| "2022-2024"}`. Default state, 2003-2019; see [Residential occupant types](#residential-occupant-types). |
| `instances[]` | Programme instances and shared services, in order. |
| `mixture` | Optional: combine instances into one result. |

Every instance has a unique `key`. Keys cannot contain `/`, which is reserved
for owners the generator derives.

A **programme instance** has a `program_id` (a recipe in
`atlas_schedules/data/recipes/`): a definition program ID (`program-…`) or, for
the DOE Ref recipes, an atlas release program ID such as
`doe-ref-pre-1980.retail-standalone.source.entry.955efc`. It can also have the
following fields:

- `extent`: the amount of each basis it represents. The bases are
  `floor_area` (m²), `dwelling_unit`, `person` and `absolute`.
- `multiplicity`: identical copies this instance stands for (default 1). It
  multiplies the instance's extent in a mixture.
- `operating_group`: commercial instances in one group share one sampled set of
  operating hours. Without it, each instance is its own group.
- `residents`, `location` and `extent.floor_area`: for apartment units, all
  three required. `residents` counts the people in one dwelling unit, not a
  building: 0–11, or `"resstock"` to draw them from ResStock, vacancy
  included. ResStock samples 0–9 occupants plus "10+", which it runs as 11, so
  larger households are outside the occupant model's data. Model a larger
  building as more unit instances; commercial occupancy comes from the
  definitions and floor area instead. `location` has `state`, `latitude`,
  `longitude` and `utc_offset`, and optionally the IECC 2004 `climate_zone`
  (otherwise drawn within the state) and a packaged TMY3 `weather_id`
  (otherwise the nearest station in the state). Every apartment unit also gets
  a water owner, `<key>/water`; see [Apartment units](#apartment-units).
- `reference_location`: for ResStock dwellings and apartment units, one of the
  16 DOE Commercial Reference climate cases (`1A` ... `8`, NREL/TP-5500-46861
  Table 2). It takes precedence over `location` and over the dwelling's own
  location and TMY3 weather. It uses the case's representative city
  (`atlas_schedules/data/weather/reference-locations.json`; 5B uses Boulder as
  a labelled proxy).
- `service_links`: required when the programme needs shared services (its
  recipe's `required_services`; for a composition parent, the union of its
  members'). Map each such service id to the key of a shared-service instance
  of that service. Missing or extra links are rejected rather than dropping
  the water load.
- `composition_basis`: for composition parents. `reference_area` keeps the
  members' source areas; `caller_area` shares the parent's `extent.floor_area`.

A **shared service** instance has `service_id`, `configuration_id` (whose hours
it follows), `physical_id` and an `extent`. It is counted once, whole, in a
mixture.

A **mixture** has these fields:

- `members` (`instance`, `weight`).
- `services`: shared-service instances listed explicitly.
- `result_basis` and `denominator`. They go together.

There are two kinds of mixture ([ADR 0023](adr/0023-generated-constituents-and-physical-mixtures.md)):

- **Physical** (with a denominator). Each member gives its real `extent`, and
  `weight` is a participation multiplier, normally 1. For each load (quantity,
  carrier, fuel, host), the mixed annual total per result-basis unit is the
  sum of `weight × extent × multiplicity × total / denominator` over the
  members' generated totals. A 400 m²
  office and a 100 m² shop with weight 1 each and a denominator of 500 give the
  building's per-m² totals (`office-and-retail.json`). Shared services, whether
  listed, linked through `service_links` or apartment caller water, are counted
  once, whole, as `extent / denominator`. A composition parent joins only with
  `composition_basis: caller_area`.
- **Share** (no denominator, no extents). Weights are shares that must sum to
  1, and the result is the weighted average per source basis unit. Shared
  services need a denominator, so they cannot join.

In both, the mixed shape is the amplitude-weighted sum of the member shapes,
people heat is density × occupancy × activity, and heating and cooling
setpoints are weight-averaged.

## Bundle

- `schedules`: `schedule:<key>:<slot>` → `{unit, values[8760]}`.
- `owners[]`: one per instance, plus each apartment unit's caller-water owner
  (`<key>/water`) and each composition member (`source-member/...`). Each owner
  lists its schedule ids and its controls. Its `loads` record the amplitude and
  the annual total per basis unit, with `amplitude × Σ values × s` equal to the
  annual total. `s` is 1 for power (W → Wh) and 3600 for volume flow
  (m³/s → m³). Apartment-unit owners also record their ResStock draw under
  `generation` (`characteristics`, `residents`, `relaxation`, `weather_id`).
- `mixture`: the mixed owner, if requested.
- `operating_groups`: the sampled ComStock parameters per group.
- `unit_seeds`: the residential seed chain.

Two bindings, as upstream (ADR 0047):

- **Source magnitude** (commercial and fixed programmes, shared services): the
  amplitude is the source density or peak flow, and the annual total follows
  the sampled schedule, as in ComStock.
- **Annual** (ResStock dwellings and apartment units): the annual total per end
  use is fixed by ResStock, and the amplitude is the design level that makes
  the generated schedule integrate to it, as OpenStudio-HPXML does.

## Programmes and families

| Kind | Programmes | Kernel |
|---|---|---|
| `commercial` | 1,156 across 15 ComStock building types: Small, Medium and Large Office, Warehouse, Retail (standalone and strip mall), Full- and Quick-Service Restaurant, Supermarket, Primary and Secondary School, Small and Large Hotel, Hospital, Outpatient. Each has source and reviewed views of every template. | ComStock transform |
| `residential` | 41 ResStock dwellings | ResStock activity and events |
| `apartment_unit` | 38 apartment dwelling units (90.1 Midrise and Highrise, DOE Ref Midrise) | ResStock multifamily unit, plus its water |
| `fixed` | 40 apartment common areas | source rules unchanged |
| `composition` | 310 source parents (Retail, Strip Mall, Warehouse, Supermarket, schools, hotels, Hospital, Outpatient) | members mixed by area |

The 150 configurations in `atlas_schedules/data/configurations/` (15 families ×
5 templates × source and reviewed views) carry each
building's People inventory (prototype geometry floor area × definition density)
and its sampling building type. A building where residential spaces (guest
rooms, patient rooms, apartments) hold most of the people uses the inverted
rule-day convention for hours of operation.

The 186 shared hot-water services (one per family, template and fixture) are in
`atlas_schedules/data/services/`.

Each recipe's `source` block names its frozen definition record
(`data/definition-releases/v0.1.1/...`). Rule sets are shared in
`atlas_schedules/data/schedules.json`. Upstream licence notices are in
`atlas_schedules/data/notices/`.

## Apartment units

An apartment unit is a ResStock multifamily unit
([ADR 0047](adr/0047-resstock-apartment-units-and-source-magnitudes.md)). For
each unit, from its own seed:

1. **Characteristics.** The ResStock housing characteristics are drawn
   (`residential/characteristics.py`, tables in
   `atlas_schedules/data/residential/characteristics/`), conditioned exactly on
   climate zone × programme: the request's climate zone (or one drawn from its
   state), pooling every state in that zone, the unit's floor-area bin and
   residents, and the programme's `resstock_unit` block: building type, height
   class, construction era and the prototype's HVAC. Midrise programmes are
   `Multi-Family with 5+ Units, 4-7 Stories` with a gas furnace and central AC;
   Highrise programmes are `8+ Stories` with a ducted heat pump. Pooled this way,
   every climate zone has a matching unit except Alaska's 7AK and 8AK, where no
   5+ unit apartment has central AC or a ducted heat pump; there the HVAC
   condition is dropped. `generation.relaxation` records `none` or `hvac`, and
   `characteristics.State` the state the unit was drawn from.
2. **Annual energy.** The OpenStudio-HPXML annual equations
   (`residential/annual.py`) give each end use's energy from the draw, the
   residents and the unit's floor area: lighting from the sampled lamp mix,
   plug loads, television, appliances, refrigeration, fuel loads and ceiling
   fans. Exterior and garage lighting are left to the building, and pools are
   not modelled.
3. **Schedules and controls.** The ResStock schedule generator runs for the
   unit's residents and installed appliances. Each load's design level is fitted
   to its schedule (`W/dwelling`). The thermostat comes from the same draw;
   activity is ResStock's constant.
4. **Water.** The `<key>/water` owner draws the prototype's volume per design
   person × the unit's residents (66.33 L/person·day at 60 °C for every
   programme), timed by the unit's own fixture events, with the peak fitted
   (`m3/s/dwelling`). The building's water service heats it.

Not covered: shared laundry rooms (ResStock gives in-unit appliances or none);
a unit's own pool; water-loop heat pumps, which ResStock has no option for.
`scripts/build_apartment_units.py` writes the recipes from release 2.0.0's prototype
recipes; release 2.1.0 carries them in its `generator.json` files.

## Residential occupant types

ResStock gives every resident one of four occupant types (mostly home, early
regular worker, mostly away, regular worker), drawn from one national share
vector (0.381, 0.297, 0.165, 0.157). The generator localises only that mix,
by composition. The chains, durations and events stay ResStock's (plan
section 7, O14).

- **Cells.** Each ATUS weekday diary is scored under ResStock's four weekday
  chains, with the national shares as the prior. The resulting type
  probabilities are averaged per cell of age band (15-24, 25-44, 45-64, 65+)
  × employed × enrolled in school, with sparse cells shrunk toward their
  parents. This reproduces the national shares within 0.8 points
  (2003-2019).
- **State mix.** The dwelling's state weights the cells by its household
  population from ACS PUMS 2024. Residents under 15, absent from ATUS, keep
  the national shares. States differ by a few points; Florida, for example,
  is more home-based.
- **Window.** `2003-2019` (default, pre-COVID) or `2022-2024`, which is
  markedly more home-based (mostly home about 0.47).
- **`"mix": "national"`** reproduces ResStock exactly; the native and legacy
  answer keys use it.
- **Provenance.** Each residential owner records its
  `occupant_type_probabilities`. The tables are
  `atlas_schedules/data/residential/occupancy-mix.json`, rebuilt by
  `python -m scripts.derive_occupancy_mix` from the inputs pinned in
  `sources/occupancy-mix-lock.json` (ATUS 2003-2024 and ACS 2024 PUMS,
  public domain; see `sources/licenses/`).
- **Not covered:**
  - finer than state (county or PUMA) and custom resident compositions;
  - weekend diaries, whose type labels do not match the weekday ones.

  These are later work, under evidence in the decomposition study
  (outside the repository).

## Residential random streams

ResStock dwellings draw from seven numpy PCG64 streams per unit, spawned from
the unit seed (`SeedSequence(unit_seed).spawn(7)`). This is mode R2.

The port also keeps R1, a replay of Ruby 3.2.2's Mersenne Twister streams as
OpenStudio-HPXML draws them. R1 lets native captures and the frozen legacy
generator be checked draw for draw. It is validation-only:
`generate(document, residential_rng="ruby_mt")`. Requests cannot select it.

R1 was retired from requests because a pre-registered study found R2
statistically equivalent. Nine configurations (Anchorage, Hickory and San Jose
dwellings with 1, 2 and 4 residents; 500–1,000 units per mode) passed all 68
checks each. The worst unit-permutation z was 2.44 against a limit of 4, and
the worst mean effect was 0.20 SD against a limit of 0.25. The criteria and per-configuration
results are in [residential-rng-equivalence.md](validation/residential-rng-equivalence.md).

## Validation

Tests compare the generator with native answer keys (`tests/answer_keys/`)
captured from real OpenStudio 3.10 / Ruby 3.2.2 runs. Fractions must agree within
1e-6, annual totals within 0.01 %, and discrete outcomes exactly.
[tests/answer_keys/README.md](../tests/answer_keys/README.md) lists every key with its
source, test and extractor.

- **ComStock kernel**: every slot matches the native output for 11 controlled
  cases, 926 programme cases (Medium and Small Office, Warehouse, Retail and
  both restaurant families), 40 restaurant water cases and the Stripmall pilot.
- **Packaged recipes**: the same 926 native cases, rebuilt from the packaged
  recipe, its configuration and (for Medium Office water) its linked service,
  match the native output (`tests/schedules/test_recipes_native.py`). The 90.1
  recipes of the 15 commercial families were built by
  `scripts/build_family_recipes.py` from the frozen definitions and prototype
  geometry. The DOE Ref recipes are written from atlas release 2.0.0 under
  release IDs by `scripts/build_reference_recipes.py` (ADR 0046 section 6),
  with the People topology from the DOE file zones; the native and legacy cases
  of the DOE Ref recipes they replaced are skipped
  (`tests/answer_keys/retired-doe-ref.json`). Heat-gain fractions are carried
  wherever the source knows them all.
- **Newer families**: 534 native cases cover Large Office, Large and Small
  Hotel, Hospital, Outpatient, Primary and Secondary School, Supermarket and
  Strip Mall. Each family uses one template (varied across families), both
  views and seeds 42 and 51. Every packaged programme slot and every shared
  water service of those configurations matches (2,834 slots;
  `tests/schedules/test_family_programmes_native.py`, captured by
  `scripts/capture/commercial_families.py`). Eight further 90.1-2013 pilots
  check the People topology per space against real prototype geometry.
- **Residential-dominant hours**: native totals on real prototype geometry
  confirm every packaged configuration's dominance decision and
  dominant-group people, for all 150. None is residential-dominant; Small
  Hotel comes closest at 44–47 % residential. The inverted rule-day path is
  checked on 20 native cases: guest- and patient-room carriers, and crafted
  rule sets that stress which day profile stays the uninverted default.
  These are weekends more frequent than any weekday profile, a near tie, one
  profile per weekday, and default-only. All match exactly
  (`tests/schedules/test_residential_dominance_native.py`).
- **ComStock sampling**: 6,660 native `tsv_sampling.py` draws.
- **ResStock (R1)**: 57 native units (channels, occupant types, offsets), plus
  8,250 raw Ruby draws.
- **ResStock apartment units**: the sampler matches an independent rejection
  sampler; 5,867 of 5,867 measure arguments of 41 recovered records equal the
  Ruby inputs; 240 sampled units in 12 states match the pinned Ruby annual
  equations within 1e-9 for all 21 end uses
  (`docs/validation/resstock-annual-equivalence.json`).
- **Orchestration**: 121 single-programme cases, both A5 case-matrix requests
  (365 owners) and four mixture scenarios match the frozen v0.8.0 generator's
  shapes. Its commercial loads held annual totals, so their totals are checked
  through the shape integral instead (`assert_binding`). Apartment units,
  Office and Warehouse owners are excluded. They were rebuilt after those keys
  were captured, with new configurations and water as linked services, so the
  native keys check them instead.

An upstream detail is kept only when dropping it breaks an answer key. Each such
detail names its answer key in its docstring. There is one deliberate
exception, described next.

`python -m scripts.smoke_catalogue` generates every programme, composition parent
and service variant once (`docs/validation/generator-catalogue-smoke.json`).
### Deviation from native ComStock: flat days under base-to-peak

ComStock's base-to-peak measures leave a one-value day unaltered. The hours
transform turns a constant day into two equal points, though, and for those
the measure's scale is 0/0. OpenStudio rejects the NaN values with only a
warning, and the day is silently cleared to 0. In ComStock this zeroes
data-centre plug loads all year, which contradicts its reference
documentation (section 4.6.3 keeps data-centre IT equipment constant). It also
zeroes flat weekend days of plain-template offices and schools. Upstream has
not fixed it (checked against `main`, 2026-10-18).

The generator follows the documented method instead: a day whose values are
all equal, with any number of points, is left unchanged, as a one-value day
is. Consequences:

- Large Office data-centre programmes generate; they no longer raise
  `zero_generated_integral`.
- Weekend lighting and plug loads in offices (Sunday) and schools (Saturday
  and Sunday) keep their flat level; they are no longer moved onto weekdays.
- Energy for those loads is higher than native or published ComStock. A
  data-centre Large Office uses about 8 kWh/ft² per year more.
- Covering flat weekend days extends the documented one-value rule; no
  document states it for them.
- The atlas data-centre schedule is the plain 90.1 `DataCenter_EQUIP_SCH`
  (monthly steps, mean 0.625), not ComStock's constant 1.0 `ALWAYS_ON`, so it
  will not equal ComStock's data-centre load either way.

`generate(document, flat_days="native")` reproduces ComStock for the native
answer keys; requests cannot select it. Evidence:
`C:/Users/cl2749/comstock-bpr-investigation/REPORT.md` (outside this repository)
and plan section 7 (O2).

### Deviation from upstream ResStock: southern hemisphere

OpenStudio-HPXML models the United States only, and its empirical monthly
terms follow northern seasons. For a dwelling or apartment unit at a negative
latitude, the generator takes those terms from the month six months away
(`atlas_schedules/residential/seasons.py`). The affected terms:
- the lighting, plug-load, TV and appliance monthly multipliers;
- the refrigerator, freezer and exterior-lighting background multipliers;
- the lighting equation's extra hour, which gives summer sunsets in
  daylight-saving clock time;
- the month term of the evening-peak width.

Astronomical sunset already follows the real latitude. Northern results are
unchanged. Not covered:
- the monthly time shifts still need a US state code;
- thermostat seasons are not shifted;
- latitudes beyond the polar circles have no defined sunset, and the
  generator rejects them.

## Adding a family

1. Capture a native answer key with OpenStudio 3.10 (`scripts/capture/`).
2. Build recipes from the frozen definitions and the family's source inventory.
3. Add an answer-key test, then extend this page.
