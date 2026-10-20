# ADR 0022: Unified context-selected construction sets

Date: 2026-10-14. Status: both examples accepted; complete migration frozen as v2.0.0 on the feature branch.

## Decision

Replace the consumer distinction between commercial packages and residential
enclosures with one versioned `construction_set` interface. Catalogue selection
resolves climate/source reference before export; selection is recorded using
Program JSON v3/v4's header and `source` naming and climate/vintage conventions.
The one set contains all source-supported component types. Exterior and interior
walls are component entries, not separately selected construction sets.

Do not export a generic `required_bindings` list or `deferred_scope` field.
Declare schema-controlled component targets, scoped assignment conditions,
precedence/ambiguity policy and geometry conventions on component rules. Retain
source-specific residential pitch, area scaling, adjacency and shading conditions
and source-selected commercial space overrides within the building set.
BEMGen's separate worker owns BEM matching, geometry interpretation and IDF
translation. Atlas supplies the contract and source-backed data.

Preserve original source/assembly/material/provenance identities and exact
physics, targets and fixed natural ACH. Resolved set IDs distinguish selected
climate/reference contexts. Partial source space definitions remain explicitly
scoped and available through the same API; they are not renamed complete building
sets. Generic reference forms remain distinct. Source compatibility-only Office
lookups are not promoted into building overrides. Source-absent space overrides
use the next applicable source scope in the declared hierarchy, ultimately
inheriting the building default; an absent override never implies a zero construction.

The source Attic `interior_floors` selector legitimately uses the legacy
`ExteriorRoof` property role with `Attic and Other` type. Validate this specific
source selector-to-component mapping without changing the preserved assembly
role or allowing arbitrary roof-to-floor assignment. Source recipe labels and
consumer component targets are separate semantics.

## Implementation and review boundary

Construction JSON 2.0.0 is a self-contained selected export with central resource
tables, complete component type census, exact source metadata and provenance.
A compact index exposes all 224 source definitions without duplicating the
library over climates. The schema is standalone; conditional scope checks and
component target constants are included. Focused validation protects all source
geometry conventions, material physics, references and provenance closure.

Frozen v1.0.0 and Program JSON remain unchanged. Both examples were accepted,
authorizing full migration checks and the feature-branch v2.0.0 freeze. The
normalized catalogue retains 224 definitions, 4,798 supported contexts, all
4,868 assemblies, 858 materials and 8,014 evidence records. All 17,564 distinct
source-selector alternatives are exercised; story and space overrides retain
source scope/order. Source hierarchy is backed by checksum-pinned OpenStudio
3.10 documentation, not an Atlas-invented precedence.

Shared tables avoid repeating full resource/provenance closures in every context.
Frozen hydration reproduces each selected standalone document. Every resource
receives schema, physical, layer/material and provenance checks, including the
1,439 independent source-table recipes outside recovered prototype mappings.
Those recipes are explicitly distinguished from context-selectable candidates;
no prototype applicability is guessed. The 5,092-identity completeness
denominator remains all source definitions plus all above-ground assemblies.

Fresh technical review produced regressions for receipt/assignment consistency,
direct/policy/repeated-story hydration and immutable v1 catalogue verification.
Repairs preserve source semantics and ordering. Exact-byte regeneration protects
the feature-branch freeze and its licenses, schemas, index, examples and manifest.
Site/CI, publication, translator, ground and system work remain deferred. See
[the contract](../construction-json-v2-contract.md) and
[review entry](../reviews/construction-set-v2-review.md).

## Local site projection

The user subsequently authorized local site integration only. Construction
finders now select source construction sets and carry full climate/building
filters into a record page. Exact source references remain explicit where
ambiguous. The page loads a checksum-verified per-definition transport packet
containing all supported contexts and shared dependencies; browser hydration
produces the frozen self-contained consumer JSON 2.0.0. The transport's private
schema 1.0.0 is not an alternate simulation contract. All assembly/material/proof
resources are separately accessible, including source-table-only assemblies
without invented prototype mappings. Partial space scopes retain their identity.

No construction science, consumer schema, source geometry or BEMGen translation
changes. A local cache path fingerprints program presentation dependencies and
reuses unchanged v3 pages; raw definition JSON remains separately available.
Production publication, ground and system completion remain deferred. See the
[local implementation record](../superpowers/plans/2026-10-14-construction-site-integration.md).
