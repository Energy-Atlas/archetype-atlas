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

A **programme instance** has a `key` and a `program_id` (a recipe in
`atlas_schedules/data/recipes/`). It can also have the following fields:

- `extent`: the amount of each basis it represents. The bases are
  `floor_area` (m²), `dwelling_unit`, `person` and `absolute`.
- `multiplicity`.
- `operating_group`: commercial instances in one group share one sampled set of
  operating hours. Without it, each instance is its own group.
- `residents` and `location` (`state`, `latitude`, `longitude`, `utc_offset`):
  for apartment units. A unit with 0 residents keeps its fixed rules.
- `reference_location`: for ResStock dwellings, one of the 16 DOE Commercial
  Reference climate cases (`1A` ... `8`, NREL/TP-5500-46861 Table 2). It
  replaces the dwelling's own location and TMY3 weather with the case's
  representative city (`atlas_schedules/data/weather/reference-locations.json`;
  5B uses Boulder as a labelled proxy).
- `service_links`: maps each required shared-service id to a service instance.
- `composition_basis`: for composition parents. `reference_area` keeps the
  members' source areas; `caller_area` shares the parent's `extent.floor_area`.

A **shared service** instance has `service_id`, `configuration_id` (whose hours
it follows), `physical_id` and an `extent`. It is counted once, whole, in a
mixture.

A **mixture** has these fields:

- `members` (`instance`, `weight`). Weights sum to 1.
- `services`: shared services listed explicitly.
- `result_basis` and `denominator`.

For each load (quantity, carrier, fuel, host), the mixed annual target is the sum
of `weight × extent × multiplicity × target / denominator`. The mixed shape is
the amplitude-weighted sum of the member shapes. People heat is density ×
occupancy × activity. Heating and cooling setpoints are weight-averaged.

## Bundle

- `schedules`: `schedule:<key>:<slot>` → `{unit, values[8760]}`.
- `owners[]`: one per instance, plus each apartment unit's caller-water owner
  (`<key>/water`) and each composition member (`source-member/...`). Each owner
  lists its schedule ids and its controls. Its `loads` record the annual total
  per basis unit and the fitted amplitude, so `amplitude × Σ values` equals the
  annual total.
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

The 135 configurations in `atlas_schedules/data/configurations/` carry each
building's People inventory (prototype geometry floor area × definition density)
and its sampling building type. A building where residential spaces (guest
rooms, patient rooms, apartments) hold most of the people uses the inverted
rule-day convention for hours of operation.

The 176 shared hot-water services (one per family, template and fixture) are in
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

- **ComStock kernel**: every slot of 11 controlled cases, 926 family programme
  cases, 40 restaurant water cases and the Stripmall pilot match the native
  output.
- **ComStock sampling**: 6,660 native `tsv_sampling.py` draws.
- **ResStock (R1)**: 57 native units (channels, occupant types, offsets), plus
  8,250 raw Ruby draws.
- **Orchestration**: every programme, both A5 case-matrix requests (463 owners)
  and six mixture scenarios match the frozen v0.8.0 generator.

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
