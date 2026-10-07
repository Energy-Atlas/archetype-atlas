# Element definitions and selective delivery v2

Start in the [catalogue](../catalogue.md): **Residential** or **Non Residential**,
then **Programs**, **Constructions** or **HVAC systems**. Supporting schedules,
materials, components, services, compositions and provenance are referenced
resources. Historical catalogues and [v1 delivery](data-delivery.md) retain their
contracts and URLs.

## Library semantics

The atlas supplies model-independent definitions. Geometry, assignment, serving
graphs and capacity sizing belong to the consumer. HVAC performance stays fixed
as a library definition; capacity-band rules stay conditional until their actual
rating context is known. A seasonal efficiency rating is not operating COP.
Source technology labels cannot establish fan performance, curves or controls.

Each physical parameter carries `value`, `unit`, `status`, `evidence_id` and
`required_inputs`. Null is unknown, never zero. Known values have status `known`;
other statuses are `unknown`, `not_reported`, `not_applicable` or `requires_input`.
Canonical definitions use SI physical values. Air-change requirements may retain
the explicit conventional rate unit `1/h`; divide by 3600 for `1/s`.
AFUE remains AFUE; EER/SEER/SEER2 are converted from Btu/(W*h) to W/W while
retaining metric names. Original values, units and transformations remain in
provenance. ACH50 retains 50 Pa and requires an explicit pressure-to-natural
infiltration model before it can supply natural infiltration.

`evidence_view` is `source` or `reviewed`. `derivation` is independently
`reported`, `normalized`, `composed` or `assumed`. Reviewed records identify their
source definition; reviewed queries replace that source record where an overlay
exists. Assumptions are limited to four versioned internal/ground construction
fallbacks. They apply building-wide only when a source role cannot be resolved.

Programs have loads with `quantity`, `basis`, `demand_id`, `schedule_id` and scope.
The basis is `floor_area`, `dwelling_unit`, `person` or `absolute`; apply the
corresponding area, dwelling count or person count exactly once. For example,
W/m2 times m2 yields W; m3/s/dwelling times dwelling count yields m3/s. Alternate
unit descriptions of the same demand are not additional demand. Adding approved
program mixes or isolated equipment adds distinct physical demands. A shared
service can be hosted in a mechanical/core zone once: beneficiary references and
reporting allocations do not instantiate more demand.

Finest, Intermediate and Coarse correspond to `SourcePrograms`, `DepartmentMixes`
and `GeneralMix`. `available_details` includes unchanged leaves which belong in
an intermediate/coarse selection. Unsupported modes are absent. Recipes retain
members, unrounded represented areas and weights; attic/basement variants never
enter denominators. Mixed density is sum(w*d); its schedule conserves
sum(w*d*s(t)), with unknown members propagated. Thermal effects retain source
component trajectories. Setpoints use the documented pointwise approximation.
Whole-dwelling ResStock programs require no room-area mixture; unresolved load
magnitudes remain unknown despite complete determined profiles.

Constructions retain ordered materials, target versus achieved layer adjustments,
conditioning categories, applicability and geometry-dependent F/C ground models.
Their scoped air requirements distinguish infiltration, outdoor ventilation and
minimum total supply. A Residential conditioning category can apply to a hotel;
it is independent of the Residential browsing gate. Compare corresponding known
element properties; matching names or a shared building package do not establish
physical identity. Unknown properties prevent a claim of full identity. Similarity
requires explicit property tolerances; there is no universal distance score.

Schedule rules retain dates, selectors, source order and design-day semantics.
Annual realizations retain year, seed, interval convention and weather context.
Residential realizations are the existing 2007 schedule-only outputs, with nominal
setpoint and proxy-weather limitations. Do not transplant an annual array to a
different calendar silently. No generator inputs or execution API are supplied.
A future optional program recipe can coordinate stochastic residential channels
with a shared seed without making generators a fourth primary kind.

## Resolve one pinned snapshot

The delivery root is [delivery/v2](../delivery/v2/latest.json). Fetch `latest.json`
once per session. Its `manifest` descriptor has a relative `href`, SHA-256 and
encoded `size_bytes`. Verify these bytes before interpreting JSON. All relative
resource hrefs resolve against the delivery root, not the referring document.
Retain that exact manifest descriptor to reproduce the session later.

The manifest has `record_types` for exactly `program`, `construction` and
`hvac_system`, each with `index`, allowed `fields`, `filter_fields` and count.
An index contains natural-context routes, scalar `selectors`, exact `record_ids`
and packet descriptors. Skip incompatible routes; fetch only candidate packets.
Packets are gzip JSON with at most 131,072 decoded bytes. Verify encoded size and
hash, then enforce `decoded_size_bytes` during bounded decompression. Supporting
resource indexes and resources have a separate 16 MiB decoded transport ceiling.
Wire artifacts use schema version `2.0.0`; definition records use schema `1.0.0`.
The manifest's `schema` descriptor supplies the [wire schema](../delivery/v2/latest.json).

Filters are exact scalar AND matches; `gate` tests membership and program `detail`
tests `available_details`. Search is a catalogue presentation feature. Unknown
filter or projected field names fail; zero matches return an empty list and
multiple matches remain multiple. No nearest-vintage fallback occurs. Source is
the default view. Project only needed fields, keeping supporting evidence lazy.

The repository reference client implements this contract:

```python
from scripts.query_v2 import QueryClient

root = 'https://energy-atlas.github.io/archetype-atlas/delivery/v2/'
client = QueryClient(root)
pin = client.manifest_ref
result = client.query('program',
    {'building_type': 'MediumOffice', 'template': '90.1-2019'},
    ['name', 'loads', 'parameters', 'required_inputs'])
# Save pin with the experiment. Reopen with QueryClient(root, manifest_ref=pin).
print(result['snapshot_id'], result['match_count'])
schedule_id = result['records'][0]['fields']['loads'][0]['schedule_id']
if schedule_id:
    schedule = client.resource(schedule_id)['record']
```

Equivalent construction/HVAC queries use `construction` / `hvac_system` and the
manifest's declared fields. Common filters include `id`, `building_type`,
`template`, `source_family`, `climate`, `derivation`, `role`, `representation` and
`system_type` where that kind exposes them. A null climate means unreported or
not differentiated; it is not every climate. Climate sets remain exact source
selectors, not inferred individual climate zones.

Responses contain `schema_version`, `kind: response`, `snapshot_id`, `manifest`,
`record_type`, `requested_view`, `match_count` and sorted `records`. Each result
has `id`, projected `fields`, `evidence_view` and `derivation`. Lazy primary
fields such as `air_exchange` carry `resource_id` and a direct `resource`
descriptor. Supporting table indexes map IDs to descriptors; `resource(id)`
resolves one resource, and clients may fetch a direct descriptor without scanning
indexes. Cache verified resources within the pinned session.

Transport errors fail closed for unsupported schemas, invalid requests, unsafe
references, missing resources, checksum mismatches and oversized decompression.
The Python reference client raises `QueryError` with a stable `code`; exceptions
are not successful response DTOs. Consumers must validate the published wire
schema plus their required physical capabilities before applying any definition.

## Coverage and reproducibility

Definition release v0.1.0 contains 1,885 programs, 3,798 constructions and 1,046
HVAC system definitions (including reviewed/composed variants). Another 140
ancillary descriptors are supporting equipment. These counts are not complete
simulation-ready models. Missing commercial infiltration, unresolved HVAC
assignment/performance, ambiguous assemblies and residential load magnitudes
remain explicit. Freeze manifests pin schemas, policies, source locks and notices.

```console
python -m scripts.definition_release --verify
python -m scripts.definition_release --reproduce
```

V1 and v2 retain every advertised immutable snapshot independently. Publisher
history archives are for deployment retention, not ordinary consumer queries.
Encoded gzip reproducibility requires the pinned Python/zlib runtime; other
runtimes must reproduce the same decoded graph and validate their own descriptors.
