# ADR 0022: Unified context-selected construction sets

Date: 2026-10-14. Status: design accepted in chat; steps 1–3 implemented for human review.

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
inherit the building default, never an invented zero construction.

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

Frozen v1.0.0 and Program JSON remain unchanged. The Medium Office and residential
review examples preserve selected physics/ACH and exact UTF-8/LF reproducibility.
These artifacts are for human review, not a newly published release. This phase
does not perform all-context release validation, source regeneration, site/CI,
publication, ground or system work. See [the contract](../construction-json-v2-contract.md)
and [review entry](../reviews/construction-set-v2-review.md).
