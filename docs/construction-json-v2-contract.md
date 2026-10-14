# Construction-set JSON 2: unified, context-selected export

Status: implementation for review; no site integration or publication.

One `construction_set` describes the above-ground construction component types
for a selected source variant. Commercial and residential exports share the same
header, `source`, `components`, `infiltration`, resource tables and `metadata`.
Program JSON v3/v4 provides the header/source naming conventions. Its source
climate and vintage status objects retain their meanings; `kind` and construction
scope values are specific to this contract. Program JSON itself is unchanged.

## Selection and assignment boundary

Catalogue filters select the source definition, climate and reference variant
before export. The consumer JSON records the exact selection in `source`, not a
generic `required_bindings` list. `components` groups all supported component
types together. A building's exterior/interior walls are different component
entries in the same set, not separate sets. The schema controls component types,
surface/space conditions, precedence, geometry conventions and ambiguity policy.
There is no `deferred_scope` field.

BEMGen owns the future BEM-to-IDF translator. It supplies actual geometry,
evaluates the declared assignment/geometry rules, and instantiates materials and
surfaces. This work does not implement that translator, BEM matching, geometry,
IDF generation, systems, ground heat transfer, site filters or publication.

## Objects

`source` retains the original construction definition ID, definition release,
building type, template, source family, climate, vintage and evidence. Source
fixture and selected reference IDs remain explicit. The exported `id` identifies
the resolved context; source IDs and assembly/material/evidence IDs are preserved.

`components` has a fixed schema-controlled type census. Each entry contains an
explicit disposition and assignment rules. Rules reference assemblies and carry
surface type, optional adjacency/space/window-operation conditions, original
source surface identities, provenance and structured geometry instructions.
The commercial source-first climate/property ordering is resolved at export.
Space-specific source sets identified by the selected reference's source queries
are embedded as overrides; compatibility-only lookups are not promoted to active
overrides. Absent space overrides inherit the building default. Partial source
space sets retain `scope: space_type`; they are not mislabeled complete buildings.
Component target constants explicitly identify BEM surface type and boundary
conditions, or internal-mass/shading object type. The source Attic floor selector
may reference a preserved legacy roof-role recipe; this specific source override
does not change the floor target or permit arbitrary cross-role assignment.

Residential multiple wall/window recipes remain separate assignment variants
inside one component type. Source element IDs and adjacency conditions are
preserved, including parent-wall adjacency for windows/doors. BEMGen must use an
explicit assignment identity or a unique compatible rule. It must reject an
ambiguous or unsupported assignment rather than picking an arbitrary source
surface. This is a schema policy, not an Atlas geometry or nearest-recipe guess.

`geometry` declares component-specific operations: actual surface area, paired
surface layer reversal, source roof pitch applicability, overhang dimensions,
partition CFA scaling and ordinary interstory floor/ceiling scaling. SI values
and source formulas are retained. These fields are instructions for BEMGen,
not missing source physics or separately selectable construction sets.
`source_reference_reversed` describes the original source assignment; the
selected layer list is already recovered and must not be reversed again solely
because this evidence flag is true. Paired adjacent surfaces use the declared
reversal policy.

`infiltration` contains the selected fixed natural ACH in `1/s`, source method,
reference identity and evidence. It is not recalculated for consumer geometry or
zoning. Mechanical air requirements and equipment remain separate.

`assemblies`, `materials`, `evidence` contain the selected resource/provenance
closure. Physics, source conditions and targets are copied from frozen v1; no
native source rerun or new numerical defaults occur. Assignment conditions move
out of legacy assembly bindings into component rules. `metadata` holds selection
decisions, source/implementation hashes and registered source file descriptors.

## Migration and review artifacts

Frozen construction v1.0.0, source recovery inputs, fixed ACH and Program JSON
are immutable inputs. The v2 exporter accepts every commercial package and
residential enclosure ID through one API; explicit unsupported source climates
remain errors. A compact index lists all 224 source definitions and their
supported contexts. It does not duplicate physics across every climate.

`docs/examples/construction-json-v2/medium-office.json` and `residential.json`
are complete self-contained review examples, not truncated illustrations.
`review-manifest.json` locks their bytes, schema and index. Run
`python -m scripts.construction_set_export --examples --check` to compare exact
UTF-8/LF bytes; omit `--check` to regenerate. Use `--construction-id`,
`--climate-zone`, optional `--reference-id` and `--output` for another selection.

Focused migration tests establish the schema/export behavior and unchanged
selected physics. This stage ends at human review; all-context release checks,
site integration, BEMGen handoff and publication remain subsequent work.
