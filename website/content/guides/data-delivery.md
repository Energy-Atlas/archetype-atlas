# Data delivery for software

The atlas publishes a generic, versioned JSON read interface. Software fetches a
small manifest, a record-type index and the packets relevant to its selection;
schedules and provenance are fetched only when needed. Canonical archives remain
whole. There is no query server, database, authentication or bundled atlas library.

The publication root is
`https://energy-atlas.github.io/archetype-atlas/delivery/v1/`.
All resource `href` values resolve against **this root**, including references
inside manifests, packets, schedules and evidence. They do not resolve against
the URL of the referring file.

Start with [latest.json](../delivery/v1/latest.json), then follow its `manifest`
descriptor. The [query contract](data-delivery-contract.md) defines the complete
resolution algorithm and errors. [Schedules and conformance](data-delivery-schedules.md)
defines schedule interpretation and executable fixtures. These three pages and
their linked schemas are the consumer contract; repository source code is optional.

## Select values, not a library

For an office program, use this request in your local resolver:

```json
{
  "record_type": "program",
  "where": {
    "building_type": "MediumOffice",
    "program": "office",
    "template": "90.1-2013",
    "source_family": "code_prototype_rules"
  },
  "fields": ["people_per_m2", "lighting_W_m2", "electric_equipment_W_m2",
             "ventilation_m3_s_m2", "gas_equipment_W_m2"],
  "view": "source"
}
```

This source record reports 0.05381955208354861 person/m2, 8.82640654170197 W/m2
lighting, 8.072932812532292 W/m2 electric equipment and 0.0004318 m3/s/m2
ventilation. Gas equipment is unknown (`null`). A reviewed view explicitly
resolves gas equipment to 0 W/m2 for this exact recipe, with evidence; it does
not resolve infiltration or declare the building all-electric.

A static URL such as `latest.json?program=office` does not execute a query.
The consumer performs exact matching and projection after downloading a bounded
superset. Packets contain several related records and their scalar fields,
bounded to 128 KiB of decoded JSON each. Indices carry record IDs for direct
lookups. A query with weak filters may need many packets; use source family,
building type, template and exact IDs whenever available. Requesting four fields
instead of five changes the local response, not the published packet inventory.

## Discover the vocabulary

The manifest lists `record_types`. Each entry advertises `record_count`,
projectable `fields`, scalar `filter_fields` and an `index` descriptor. Discover
these lists before constructing selectors. The current full publication contains:

| Record type | Meaning |
| --- | --- |
| `program` | Space-use loads, ventilation and schedule references |
| `schedule` | Source rule records; programs also reference lazy schedule payloads |
| `envelope_component` | Construction requirements with explicit climate-set applicability |
| `system` | Source system descriptions; applicability may be unknown |
| `mapping` | Source mappings between categories and models |
| `efficiency_rule` | Conditional source efficiency rules |
| `residential_option`, `commercial_option` | Stock option arguments, not assumed complete models |
| `residential_archetype` | Exact residential source fixtures and optional reviewed profiles |
| `specialized_rule` | Source-specific rules and applicability |
| `water_reporting` | Program-level water attribution and known/unknown allocation |
| `water_service` | Building-service paths, flow scales and normalized schedules |
| `water_draw` | Physical draw-path evidence and conservation details |

IDs identify source variants within a record type. Labels alone need not be
unique: the apartment conformance example returns three variants. Return every
match; the application must require an explicit selection when it needs one.
Never combine or select the first variant silently.

Climate applicability belongs to the record that actually reports it.
`program` has no climate-zone filter in this release. Query an envelope separately
with `climate_zone_set: "ClimateZone 5"` for that reported grouping. A request
for `ClimateZone 5A` does not match `ClimateZone 5` or `ClimateZone 5B`;
the v1 example intentionally returns no matches for that unreported subzone.
Stock residential fixtures expose `reported_climate_zone`
and `stock_vintage` from source context. These labels describe that fixture;
they are not population weights or permission to reuse its profile in any climate.
Code template and stock vintage are separate concepts. Systems without a reported
climate linkage must remain unspecified until the consuming project supplies one.

## Preserve meaning at the application boundary

Numeric operational fields have explicit SI units. For example, multiply m3/s/m2
or m3/s/person by 3600 only when an application needs m3/h/m2 or m3/h/person.
Air changes per hour (`1/h`) already use hours. W/m2 and Celsius remain unchanged.
Check each field's `unit`; a null unit means no normalized unit was supplied,
not that an arbitrary source option or nested argument is an SI number.

`null` is unknown or not reported. It is never an implicit zero. Reviewed values
are opt-in resolutions tied to the original evidence. Field status distinguishes
`source`, `unknown`, `reviewed` and `not_reported`. Record availability does not
mean simulation readiness: geometry, population weights, activity assumptions,
missing infiltration, system choices and annual calendars belong to the consumer.
Water attribution is not automatically a physical zone fixture or heat gain.

## Updating and reproducing

Resolve latest once at the start of an operation and retain that manifest
descriptor. Use one snapshot for all queries and lazy resources in that operation.
Save the manifest descriptor, snapshot ID, request and selected IDs with your
model. Hash-verified immutable resources can be cached across sessions. Check
latest when the user requests an update or starts a new operation; never silently
change values midway through a model build. Offline operation requires those
resources already be cached; a missing resource is an explicit failure.

Existing snapshot and content-addressed resource URLs are retained on publication.
The current exporter pins atlas v0.2.0, resolution v0.4.0, commercial-completion
v0.1.0 and water-reporting v0.1.0 by manifest SHA-256. A new scientific release
produces a new snapshot without changing old model inputs. A future online
service can accept the same request DTO and return the same result DTO; only
the transport adapter changes. No service endpoint is promised today.

The manifest's `notices` contains original-work and upstream license notices.
Original atlas code and documentation are unlicensed by owner choice; upstream
data keeps its own terms. Refer to [sources and licensing](../sources.md).
