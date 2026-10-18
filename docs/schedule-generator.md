# Schedule generator

`atlas_schedules` turns a request (programmes, extents, a seed) into 8,760-hour
schedules for 2007 (non-leap, local standard time, hour `[h, h+1)`), with the
annual load targets bound to each generated shape. It is a readable port of the
upstream schedule code ([ADR 0035](adr/0035-readable-generator-restructure.md)):

- **ComStock / openstudio-standards 0.8.6**: hours of operation inferred from
  People-weighted occupancy, schedules rewritten relative to those hours, new
  hours sampled from ComStock v33 tables, base-to-peak ratios for lighting and
  plug loads;
- **ResStock / OpenStudio-HPXML `schedules.rb`** (revision dd25369): Markov
  occupant activities, occupancy-driven shapes, appliance and hot-water events.

Generation needs Python 3.11+, numpy and jsonschema (`requirements.txt`). No
OpenStudio, Ruby or network access is needed at run time.

## Quick start

```bash
python -m atlas_schedules docs/examples/schedule-generator/office-and-retail.json -o bundle.json
```

```python
from atlas_schedules import generate
bundle = generate(request)   # request: dict following schema 2.0.0
```

Example requests live in `docs/examples/schedule-generator/`.

## Request (schema 2.0.0)

The schema is `atlas_schedules/schemas/request-v2.schema.json`.

| Field | Meaning |
|---|---|
| `seed` | Unsigned 64-bit master seed. The same request always gives the same bundle. |
| `instances[]` | Programme instances and shared services, in order. |
| `mixture` | Optional: combine instances into one result. |

Every instance has a unique `key`. Keys cannot contain `/`, which is reserved
for owners the generator derives.

A **programme instance** has a `program_id` (a recipe in
`atlas_schedules/data/recipes/`). It can also have the following fields:

- `extent`: the amount of each basis it represents. The bases are
  `floor_area` (m²), `dwelling_unit`, `person` and `absolute`.
- `multiplicity`: identical copies this instance stands for (default 1). It
  multiplies the instance's extent in a mixture.
- `operating_group`: commercial instances in one group share one sampled set of
  operating hours. Without it, each instance is its own group.
- `residents` and `location` (`state`, `latitude`, `longitude`,
  `utc_offset`): for apartment units. `residents` counts the people in one
  dwelling unit, not a building, and ranges 0–11. ResStock samples 0–9
  occupants plus "10+", which it runs as 11, so larger households are outside
  the occupant model's data. Model a larger building as more unit instances;
  commercial occupancy comes from the definitions and floor area instead. A
  unit with 0 residents keeps its fixed rules. An apartment unit with `extent.floor_area` also gets a caller-water
  owner, `<key>/water`.
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
  carrier, fuel, host), the mixed annual target per result-basis unit is the
  sum of `weight × extent × multiplicity × target / denominator`. A 400 m²
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
  lists its schedule ids and its controls. Its `loads` record the annual total
  per basis unit and the fitted amplitude, so `amplitude × Σ values × s` equals
  the annual total. `s` is 1 for power (W → Wh) and 3600 for volume flow
  (m³/s → m³).
- `mixture`: the mixed owner, if requested.
- `operating_groups`: the sampled ComStock parameters per group.
- `unit_seeds`: the residential seed chain.

Annual targets come from the original source shape before any transform, so
sampling moves energy in time without changing the annual total.

## Programmes and families

| Kind | Programmes | Kernel |
|---|---|---|
| `commercial` | 1,397 across 15 ComStock building types: Small, Medium and Large Office, Warehouse, Retail (standalone and strip mall), Full- and Quick-Service Restaurant, Supermarket, Primary and Secondary School, Small and Large Hotel, Hospital, Outpatient. Each has source and reviewed views of every template. | ComStock transform |
| `residential` | 41 ResStock dwellings | ResStock activity and events |
| `apartment_unit` | 40 apartment dwelling units | ResStock unit occupancy and lighting, plus caller-unit water |
| `fixed` | 44 apartment common areas | source rules unchanged |
| `composition` | 378 source parents (Retail, Strip Mall, Warehouse, Supermarket, schools, hotels, Hospital, Outpatient) | members mixed by area |

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

- **ComStock kernel**: every slot matches the native output for 11 controlled
  cases, 926 programme cases (Medium and Small Office, Warehouse, Retail and
  both restaurant families), 40 restaurant water cases and the Stripmall pilot.
- **Packaged recipes**: the same 926 native cases, rebuilt from the packaged
  recipe, its configuration and (for Medium Office water) its linked service,
  match the native output (`tests/schedules/test_recipes_native.py`). All 15
  commercial families are built by `scripts/build_family_recipes.py` from the
  frozen definitions and prototype geometry, and `--check` reproduces every
  recipe and service. Heat-gain fractions are carried wherever the definitions
  know them all.
- **New families**: 8 native 90.1-2013 pilots (source and reviewed views of
  Large Office, Large Hotel, Hospital and Outpatient) check the People topology
  per space and every shared water service. Small Hotel, the schools and
  Supermarket use the same builder and kernel without a pilot of their own. No
  new family has a native key for its programme slots yet.
- **ComStock sampling**: 6,660 native `tsv_sampling.py` draws.
- **ResStock (R1)**: 57 native units (channels, occupant types, offsets), plus
  8,250 raw Ruby draws.
- **Orchestration**: 121 single-programme cases, both A5 case-matrix requests
  (365 owners) and four mixture scenarios match the frozen v0.8.0 generator.
  Office and Warehouse owners are excluded. They were rebuilt after those keys
  were captured, with new configurations and water as linked services, so the
  native keys check them instead.

An upstream detail is kept only when dropping it breaks an answer key. Each such
detail names its answer key in its docstring.

`python -m scripts.smoke_catalogue` generates every programme, composition parent
and service variant once (`docs/validation/generator-catalogue-smoke.json`).
One upstream outcome is reported rather than generated. ComStock's base-to-peak
measures clear any day whose values are all equal: the scale is 0/0 and
OpenStudio rejects the NaN values. Dropping this breaks 287 native family checks.
Large Office data-centre plug loads are flat, so they become zero whenever a
weekday ratio is sampled. Their positive annual target then cannot bind, and
those 16 programmes raise `zero_generated_integral`.

## Adding a family

1. Capture a native answer key with OpenStudio 3.10 (`scripts/capture/`).
2. Build recipes from the frozen definitions and the family's source inventory.
3. Add an answer-key test, then extend this page.
