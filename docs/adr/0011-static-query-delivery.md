# ADR 0011: Generic static query delivery

Date: 2026-10-05. Status: accepted by the user's delivery design and autonomous
implementation authorization. Work remains on `feature/query-dto`; no main merge.

## Decision

Publish a generated machine interface alongside MkDocs. Keep canonical tables and
all frozen archives unchanged. The interface is generic to energy-data consumers;
BEMGen implements its own conversion to presets and units. There is no online
database or query backend. A future service may implement the same exact-filter,
field-projection request and response without changing scientific semantics.

Expose a small mutable `delivery/v1/latest.json` pointer to a checksum-bound
snapshot manifest. Route by natural table context (building/template/source family
where present), splitting oversized groups deterministically. Store schedules,
annual series and field evidence as independently referenced resources. No climate
Cartesian expansion, per-request-variable shards, stock-variant merging, or annual
calendar compilation is introduced. Exact climate-set filters retain the source
classification; a climate-independent program has no climate filter.

Requests select one record type, exact scalar filters, an explicit field list and
`source` or `reviewed` view. Source is the default. Results retain IDs, units,
unknown versus zero, evidence and snapshot identity. Multiple matches are returned;
zero matches are explicit. Unknown filters/fields, invalid DTOs, unsupported
schema majors, path escapes and corrupt downloads fail closed. The static resolver
fetches a bounded superset and projects locally; query parameters on static URLs
do not execute queries. No SQL, authentication, service deployment or BEMGen API.

Reviewed resolutions remain optional and evidence-backed; source field values stay
available. Commercial water attribution and services are separate record types,
never automatic physical zone loads. Annual residential profiles preserve their
original calendar, seed and proxy-weather metadata. Schedule rules preserve order,
dates, day selectors and design days. Raw details and provenance are lazy resources
and retain original units. Payload completeness is not simulation readiness.

Content hashes identify snapshots and resources. Resolve latest once per operation,
then use that immutable manifest and cache verified bytes. Build and publication
verify all references, schemas, source fidelity and deterministic output. Publishers
must retain advertised snapshot URLs when adding releases; material changes to the
projection need a new contract version and retained export implementation. Current
v1 exposes atlas v0.2.0, resolution v0.4.0, commercial-completion v0.1.0 and optional
water-reporting v0.1.0 under one dependency-locked snapshot.

## Trade-offs

Natural groups cost a few extra scalar values per download but avoid a backend and
millions of precomputed condition/field combinations. Per-field series are larger
and fetched only on demand. Consumers port a short normative resolution algorithm;
the Python implementation is a reference, not a required runtime dependency.

Original work stays unlicensed; upstream notices travel with the delivery. The
owner explicitly authorized publication. No permission to relabel the delivery as
MIT follows from BEMGen's license.

## Transport and publication bounds

Large JSON resources use deterministic gzip files with explicitly declared encoded
and decoded sizes. SHA-256 binds the encoded file; consumers verify before bounded
decompression. Packets remain at most 131072 decoded bytes. This substantially
reduces static-host storage without changing the generic JSON model.

Clean publishers restore a checksum-bound retention ZIP before rebuilding, so old
snapshot URLs survive later publications. It is publisher-only, never a query
download. Schema files and license notices are content-addressed too. Examples
are current conformance fixtures with an explicit pinned manifest descriptor.

Catalogue HTML displays repeated original arrays/objects once per record page,
linking every repeated field to that same complete source value. The field's own
locator, units and transformation remain independent. This presentation reduction
fits the existing static-host limit; canonical archives and scientific values stay
byte-identical.

The Material theme prunes inactive navigation branches from individual pages;
top-level links still lead to each guide group, whose active branch lists its
pages. This removes repeated navigation markup across thousands of record pages
while retaining navigation and the no-JavaScript documentation.
The existing HTML delivery hook also collapses redundant blank lines outside
literal regions; scripts, code, source JSON, inline spacing and license comments
retain their content.
