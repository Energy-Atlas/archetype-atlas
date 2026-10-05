# Schedules and conformance

Schedules are lazy resources under the [query contract](data-delivery-contract.md).
Keep the originating snapshot descriptor and view with every resolved field.
A `*_schedule_id` field may carry a `resource` descriptor; reviewed residential
`profile:*` fields do too. Fetch that descriptor directly. Do not infer a URL
from an ID or assume every schedule lives in the `schedule` record-type table.
Derived IDs are content identities, not canonical source schedule IDs.

Every payload has `schema_version: "1.0.0"`, `kind: "schedule"`, a
`representation`, and a `record`. Source rules also carry independent evidence.
Reviewed derived payload evidence is reachable through the owner's reviewed field
pointer. Payload values contain load shapes or desired temperatures, not geometry.

## Rules

`representation: "rules"` preserves the canonical source schedule record,
including `units`, `rules`, original schedule name and source order. Each rule
has `day_types` (pipe-separated selectors), `start_date` and `end_date` (source
date strings, using their month/day for recurring applicability), and `values`
(24 hourly values, or one constant value to repeat across all 24 hours). Hour index 0
covers [00:00,01:00); index 23 covers [23:00,24:00). Read the field names from
the payload; retain the entire rule rather than only its values.

For a concrete month/day and day selector, evaluate date applicability inclusively.
A range whose end precedes its start wraps the year boundary. Day selectors include
`Mon`, `Tue`, `Wed`, `Thu`, `Fri`, `Sat`, `Sun`, `Wkdy`, `Wknd`, `Default`,
`Hol`, `WntrDsn`, `SmrDsn`, and the source's `DummySmrDsn`. `Wkdy` means
Monday-Friday and `Wknd` Saturday-Sunday. Keep holidays and design days distinct
from weekdays. `DummySmrDsn` matches summer design days under the pinned source
generator interpretation. `Default` is fallback: choose the final matching
specific rule in source array order, otherwise the final applicable Default rule.
No matching specific/default rule means unknown; do not fill with zero or Sunday.

An annual expansion needs an explicit year, weekday alignment, local standard
time convention, holidays/special days and leap-year policy. The publication
does not choose those inputs. Preserve separate winter/summer design-day profiles
when the application supports them. A 8760 array alone cannot encode their
semantics. Document and expose any downstream inability to represent special days.
For a weekday-only inspection, see the site's existing schedule explorer and
[schedule mechanisms](schedule-methods.md).

## Constant

`representation: "constant"` has `record.value`, `record.units` and
`record.calendar_independent`. For example, a reviewed always-zero gas equipment
shape has value 0 and dimensionless units. Expand only as explicitly permitted by
`calendar_independent`; this is a reported resolution, not a general missing-data
fallback. Its magnitude remains the separate reviewed equipment-density field.

## Annual source series

`representation: "annual_series"` contains `record.metadata`, `record.column`,
`record.units` and `record.values` (8760 source hours). Metadata is preserved
verbatim, including source calendar/year, local standard time and interval
convention, realization inputs/seed, source revision and weather-station proxy
where applicable. Follow that metadata; do not treat array position as an arbitrary
new year or silently resample to 8784 hours. Nominal desired thermostat temperatures
are not sampled HVAC availability or runtime interruptions.

Residential profiles describe exact synthetic source fixtures, not population
samples or room movements. Proxy weather affects generator inputs; it is not a
weather file supplied for the consuming simulation. The three vacant fixtures'
zero occupancy does not imply zero refrigeration. Fixed backgrounds and explicitly
executed operational-zero variants remain separate evidence-backed fields.

## Fixed backgrounds

`representation: "fixed_profiles"` contains the selected source-background record:
`weekday_fractions` (24), `weekend_fractions` (24), `monthly_multipliers` (12),
`peak_divisor`, `unit`, `interval_convention`, `special_days`, `normalization`,
`temperature_dependent` and source `evidence`. Under the current selected variant:

```text
fraction = selected_day_fractions[hour] * monthly_multipliers[month - 1] / peak_divisor
```

Use Monday-Friday weekday and Saturday-Sunday weekend in local standard time.
The record states whether special-day overrides exist. This fixed variant has no
temperature feedback; do not reinterpret it as a stochastic or temperature-driven
appliance model. Annual expansion still requires the consumer's explicit calendar.

## Water semantics

`water_reporting` describes program attribution. `local_draw_status`,
`reporting_status`, `building_service_path_ids` and notes distinguish a known
absence, unknown allocation, a physical local draw and building-service attribution.
Its reporting peak flow/schedule must not become a physical zone draw automatically.

Follow a `water_service` ID for building-service flow scales and its equivalent
schedule, or a `water_draw` ID for actual draw-path evidence. Source and normalized
schedule shapes are both retained. For a selected physical path, multiplying its
equivalent peak flow by its equivalent dimensionless schedule conserves the
source rated-flow × source-fraction trajectory. Keep multiplicity, reference area,
normalization divisor and path membership explicit; avoid assigning the same
building-service path to several zones and counting it repeatedly. Do not invent
internal heat gains or heat fractions. The [hot-water guide](hot-water.md) and
[complete water reporting](../water-reporting/index.md) describe these boundaries.

## Executable conformance fixtures

Fetch [conformance.json](../delivery/v1/examples/conformance.json).
It contains `schema_version`, a pinned `manifest` descriptor and `cases` with
`name`, `request`, `response`. Resolve each request against **that manifest**,
bypassing latest, and compare the complete response structurally: field values,
null/status/unit, normalized query, ordered IDs, evidence/resource descriptors
and snapshot. JSON object member order is immaterial; array order is meaningful.
Floating-point calculations are unnecessary for query comparisons.

The current full publication includes:

| Case | Required behavior |
| --- | --- |
| `medium-office-source` | Exact source values; unknown gas; lazy schedule descriptors |
| `medium-office-reviewed` | Reviewed gas zero with constant schedule; infiltration remains unknown |
| `apartment-variants` | All three source variants remain separate |
| `climate-envelope` | Exact reported `ClimateZone 5` applicability |
| `climate-subzone-absent` | Zero matches for unreported `ClimateZone 5A`, without broadening to zone 5 |
| `no-match` | Successful zero-match response |
| `water-attribution` | Reporting attribution remains separate from physical paths |
| `residential-profile` | Exact fixture context and lazy annual-series descriptor |

The same requests and results are published as
`examples/<case>.request.json` and `examples/<case>.response.json`.
`examples/manifest-reference.json` is a standalone descriptor for CLI or other
test harnesses. These example URLs represent the current publication; preserve
the pinned manifest and fixture contents when reproducing an older test run.

A compatible reader should additionally test: unknown type/field/filter;
invalid/nonfinite/duplicate-member JSON; unsupported schema major; missing/corrupt
resources; descriptor traversal/redirects; source versus reviewed zero; exact
case/variant selectors; boolean-versus-number equality; cached repeat queries;
all four schedule representations; and failure instead of partial results.
Fetching only scalar fields must not request schedules or evidence. An ID lookup
must skip packets whose advertised IDs cannot match.

The optional repository reference CLI is:

```text
python -m scripts.query_client --root <delivery-root> --request request.json
python -m scripts.query_client --root <delivery-root> --manifest manifest-reference.json --request request.json
python -m scripts.query_client --root <delivery-root> --manifest manifest-reference.json --resource resource-reference.json
```

Each successful operation writes one JSON object to stdout. The public schemas,
algorithm and fixtures suffice to implement an independent reader in another
language; Python is not a consumer dependency.
