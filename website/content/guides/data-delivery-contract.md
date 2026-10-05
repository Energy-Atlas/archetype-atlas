# Query contract v1

This page is normative for the generic static resolver. The publication root is
`https://energy-atlas.github.io/archetype-atlas/delivery/v1/`.
The [overview](data-delivery.md) describes selection and scientific boundaries;
[schedules](data-delivery-schedules.md) describes lazy payload interpretation.

## Wire definitions

Use JSON Schema Draft 2020-12:

- [Request schema](../delivery/v1/schemas/query-request.schema.json)
- [Artifact schema](../delivery/v1/schemas/query-artifact.schema.json)
- [Result and error schema](../delivery/v1/schemas/query-response.schema.json)

Those friendly URLs describe the current contract. Each immutable manifest also
advertises hash-bound schema descriptors for its snapshot. Bootstrap with the v1
artifact definition, then verify those descriptors. Schema version `1.0.0` is
independent of underlying scientific release versions. Reject unsupported major
versions; validate supported minor versions against the schema you implement.
Fail closed on unknown structures until your reader supports them.

All JSON is UTF-8, with finite numbers and unique object member names. Generated
JSON is serialized with keys sorted recursively, no whitespace between tokens,
unescaped Unicode and one final LF. Array order is preserved. Resource hashes
are over downloaded bytes, not reserialized objects. If checking the snapshot's
self-derived identity, SHA-256 the manifest **without** its `snapshot_id` member
using that serialization. The checked manifest descriptor binds its exact bytes
even when a language cannot reproduce this canonical serialization.

A descriptor is:

```json
{
  "href": "resources/<64-lowercase-hex-digest>.json.gz",
  "sha256": "<64-lowercase-hex-digest>",
  "size_bytes": 1234,
  "encoding": "gzip",
  "decoded_size_bytes": 8192
}
```

The digest and sizes above are placeholders. For plain files omit **both**
`encoding` and `decoded_size_bytes`. `encoding` is a file encoding declared by
the descriptor, independent of HTTP `Content-Encoding`. `.json.gz` downloads are
ordinary gzip files; hash and count those file bytes, then decompress. If an HTTP
stack automatically decodes HTTP content encoding, disable that behavior when
necessary to obtain the advertised file bytes. Enforce both sizes, bound decoding,
and parse JSON only after verification. Never decompress before verifying SHA-256.

Every href is a literal relative path under the publication root. Reject absolute
paths, leading slash, empty segments, `.`/`..`, backslashes, colon, query/fragment,
percent escapes, controls and spaces. Reject symlink escapes for local reads and
redirects outside the same HTTPS origin and root prefix. HTTPS is required for
remote production reads. HTTP loopback is acceptable for fixture tests.

Latest is at most 64 KiB. The reference consumer limits ordinary JSON resources
to 16,000,000 bytes both encoded and decoded. Every packet is additionally bounded
by the manifest's `max_packet_bytes` (currently 131072) after decoding. A publisher
retention archive has a separate 100 MB transport / 500 MB expanded ceiling and
is never fetched by ordinary consumers.

## Request

Required members: `record_type` (string), `fields` (nonempty array of unique field
names). Optional `where` is an object of exact scalar equality predicates;
optional `view` is `source` (default) or `reviewed`. No extra members are allowed.
There are no ranges, lists, wildcards, OR, SQL, sort directives or implicit defaults.

Look up the type in manifest `record_types`. Every projected field must be in
its `fields`; every predicate must be in `filter_fields`. `id` is a predicate,
not a projectable field: result records always carry IDs. Predicate values may
be string, finite number, boolean or null. All predicates are ANDed. Strings
are case-sensitive and never trimmed or aliased. Numbers compare numerically;
booleans are distinct from numbers. Null matches an explicitly present null;
a field absent from a record does not match null.

`source` evaluates original fields. `reviewed` first overlays that exact record's
reviewed fields onto source fields, then evaluates predicates and projections.
Fields with no reviewed resolution keep their source values. Group selectors
are stable source context, not alternative definitions of identity.

## Resolution algorithm

1. GET `latest.json`, validate `kind: "latest"` and supported schema. It contains
   `snapshot_id` and `manifest`. Alternatively use a previously saved manifest
   descriptor directly, bypassing latest. Its resource remains pinned.
2. Verify/fetch the manifest, validate `kind: "manifest"`, and require its
   `snapshot_id` equal latest's ID when latest was used. Retain this descriptor
   for the entire operation. Never mix a later manifest into a lazy fetch.
3. Validate the request and advertised field/filter vocabulary. Fetch and verify
   only the requested type's `index`; require its `record_type` equal the request.
4. Each index route contains `selectors`, `record_ids` and `packets`. Skip a route
   if a supplied predicate conflicts with one of its context selectors, or if a
   supplied `id` is absent from `record_ids`. Missing predicates do not prune it.
5. Fetch only remaining packet descriptors, deduplicating identical descriptors.
   Verify their byte bounds, schema, `kind: "packet"` and `record_type`. Packets
   contain `records`, each with `id`, `fields`, `reviewed` and `evidence`.
   Duplicate record IDs within the selected packet set are an artifact error.
6. Construct the requested view per record. Evaluate every predicate against the
   record ID or field `value`. Project only requested fields. A field advertised
   by the type but absent on a matching record yields
   `{"value":null,"unit":null,"status":"not_reported","evidence_pointer":null}`.
7. Sort matches by exact ID ascending. Return the response below. Preserve all
   matches; do not select, merge or interpolate a variant. Fetch each projected
   field's optional `resource`, or a record's `evidence`, only when needed.

Cache by the full descriptor (href, digest, sizes and encoding), not href alone.
Verify before caching. A cache hit must return the same immutable content without
another request. Changing latest invalidates the active manifest selection, not
already verified content-addressed cache entries. If any requested packet fails,
return an error rather than a partial successful result.

## Response

```json
{
  "schema_version": "1.0.0",
  "snapshot_id": "<64-lowercase-hex-digest>",
  "record_type": "program",
  "view": "source",
  "query": {"record_type":"program","where":{},"fields":["lighting_W_m2"],"view":"source"},
  "match_count": 1,
  "records": [{
    "id": "<selected-record-id>",
    "fields": {
      "lighting_W_m2": {
        "value": 8.82640654170197,
        "unit": "W/m2",
        "status": "source",
        "evidence_pointer": "/provenance/fields/lighting_W_m2"
      }
    },
    "evidence": {"href":"resources/<digest>.json.gz","sha256":"<digest>",
                 "size_bytes":1234,"encoding":"gzip","decoded_size_bytes":8192}
  }]
}
```

IDs/digests/sizes above are placeholders. `query` echoes the request normalized
with both defaults (`where: {}`, `view: "source"`). `match_count` equals array
length. Zero matches is a successful result with `records: []`. Multiple matches
is a successful result requiring selection at the application layer.

Each field carries `value`, `unit`, `status`, `evidence_pointer`, and optionally
`resource`. Structured original rule/option values remain JSON rather than being
coerced to numbers. Status `unknown` indicates an original null; `reviewed`
indicates an explicit resolution, including a reviewed zero. `not_reported`
indicates no such field on this record in this view.

Fetch the record evidence descriptor to interpret `evidence_pointer` as a JSON
Pointer relative to that evidence object (`~0` escapes `~`, `~1` escapes `/`).
Source pointers resolve into `provenance.fields`; derived context and reporting
pointers resolve into `record`; reviewed pointers resolve into `resolutions`.
Evidence retains the complete original record, field transformations, original
units/values, extraction dates, interpretation notes and source files/revisions/
checksums. Reviewed resolutions include their own evidence. A schedule's optional
evidence descriptor traces that schedule independently of the owning program.

## Errors

```json
{"schema_version":"1.0.0","error":{"code":"unknown_filter","message":"Unknown or non-scalar filter: climate_zone"}}
```

Message text is diagnostic and may change; codes are stable:

| Code | Meaning |
| --- | --- |
| `invalid_request` | Invalid request shape, duplicate/nonfinite JSON, or unreadable request input |
| `unknown_record_type` | Type not advertised |
| `unknown_field` | Projected field not advertised |
| `unknown_filter` | Predicate not advertised as scalar |
| `unsupported_schema` | Unsupported schema major |
| `unsafe_reference` | Unsafe path, root or redirect |
| `fetch_failed` | Network or local resource unavailable |
| `integrity_error` | Hash, file size, snapshot identity or declared decoding mismatch |
| `invalid_artifact` | Invalid JSON/schema/kind, duplicate ID or byte bound |

The reference CLI emits error JSON and exits 2. Other languages should use
equivalent structured errors. Retrying transport failures is an application policy;
do not replace failure with zero, another template, or a different snapshot.

## Publication and future service

Publishers verify frozen inputs, generate deterministic files, check transitive
hashes/schema/counts/size, and publish them with MkDocs. `latest.history` describes
a publisher-only ZIP retaining all immutable resources and manifests. A clean
publisher must restore and verify that archive before replacement publication;
missing initial v1 latest is allowed only on first publication. Corrupt or missing
history on an established delivery is fatal. Consumers need only latest, manifest,
the requested index/packets and optional resources.

When a backend exists, its adapter can accept this request and produce this
response with the same snapshot, null, variant and provenance rules. A new
transport must not change those semantics. Breaking contracts use a new major
root; existing v1 URLs and pinned snapshots remain available.
