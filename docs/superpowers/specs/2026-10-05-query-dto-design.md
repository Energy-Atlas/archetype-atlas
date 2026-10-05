# Generic query delivery design

Status: approved conversational design, autonomous implementation authorized.

## Intent

Other software retrieves a few requested energy fields in bounded source contexts
without downloading the archive. No data ships inside BEMGen. No backend exists
now. Preserve a transport-independent exact-filter/projected-result contract for a
later online database. See ADR 0011 for scientific and publication boundaries.

## Contract

Schema version 1.0.0. Latest points to a manifest with snapshot ID, dependency
hashes, record-type field catalogues and routing indexes. Every advertised resource
has a relative path, SHA-256 and byte count. A route contains its exact grouping
selectors and one or more bounded packet descriptors. IDs and scalar selectors are
stable in a snapshot. Sorting, compact UTF-8 JSON and file names are deterministic.

Request: record_type, nonempty fields, optional where (scalar equality) and view
(source default, reviewed opt-in). Response: schema_version, snapshot_id,
record_type, view, query, match_count and ordered records. Each projected field has
value, unit, status and evidence reference. Field absence differs from reported
null. Missing filters or fields are invalid, not ignored. Results never pick a
variant or infer climatic applicability. Lazy resources carry schedules, raw
record/provenance/source-file details and original annual profile metadata.

## Implementation

Python generator consumes verified frozen inputs, emits publication into ignored
build directories, validates contracts and reproducibility. Python reference
resolver supports filesystem and HTTPS roots, verifies referenced bytes before
parsing and performs no hidden network retries/fallbacks. A caller can reuse a
verified in-memory resource cache. Reference CLI writes requested result JSON and
can retrieve referenced resources explicitly. No backend or giant SDK.

Integrate the machine files in the existing site generator and workflow. Publish
three self-contained guide pages: overview, normative wire contract, and runnable
examples/conformance vectors. Include JSON Schemas and examples as direct static
downloads. Document all DTO fields, URI resolution, routing/filter logic, errors,
source/reviewed modes, lazy data, calendars, water semantics and backend migration.

## Verification and finish

Medium Office pilot first; full canonical record coverage next. Test invalid DTOs,
hash tampering, oversized routes, path escape, variant ambiguity, zeros/nulls,
calendar/rule preservation, optional resolutions, water separation, local/HTTP
parity, lazy downloads, deterministic output and schemas. Run the repository
suite, frozen-release checks, MkDocs strict build, link and browser checks. Run the
staged audit before every logical commit; use neutral automated author and an
Agent-Model trailer recording unavailable exact runtime details. Push and publish
the authorized feature branch without merging main. Produce ignored Markdown
handover and one-paragraph covering message with tested public URLs.
