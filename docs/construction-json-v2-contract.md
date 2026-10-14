# Construction-set JSON 2: unified, context-selected export

Status: both examples accepted 2026-10-14; v2.0.0 frozen on the feature branch.
Site integration and publication remain pending.

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
Space-specific and story-specific sets identified by the selected reference's
source queries are embedded as overrides; compatibility-only lookups are not
promoted to active overrides. The source hierarchy is space type, story, then
building default; original story IDs remain explicit, without guessed floor
indices. The pinned OpenStudio 3.10 documentation and its checksum are retained
in the source lock and evidence. Absent space overrides inherit the next
applicable source default. Partial source
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
closure, including every supported source-selector alternative, rather than
only the source-first selected assembly. Physics, source conditions and targets
are copied from frozen v1; no native source rerun or new numerical defaults occur.
Assignment conditions move
out of legacy assembly bindings into component rules. `metadata` holds selection
decisions, source/implementation hashes and registered source file descriptors.
`candidate_element_ids` lists alternatives supported in the selected property
climate group. An explicit `--variant source-definition-id/selector=assembly-id`
retains the source selector's semantics and scope order. Validation requires
the selection receipt and actual component assignments to agree.

## Frozen migration and reproduction

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

The normalized release lives in `data/construction-releases/v2.0.0/`. Its
`catalogue.json` is the header containing 224 source definitions, 4,798 resolved
contexts and common metadata. Shared `component_configurations.json`,
`selector_receipts.json`, `assemblies.json`, `materials.json` and `evidence.json`
complete the catalogue. `load_release()` verifies manifest file checksums and
reconstructs the catalogue; the freeze checks its full schema. The raw header
alone is not the self-contained catalogue described by that schema. Selected consumer
documents remain self-contained and use the separate construction-set schema.

Coverage is 5,092/5,092 source identities: 224 definitions plus 4,868 assemblies.
All 4,751 commercial and 47 residential supported climate/reference contexts
validate, and all 17,564 distinct source-definition/selector/assembly choices
are checked in a supported context. There are 858 materials and 8,014 evidence
records. Source equality covers every v1 assembly/material/original evidence
record and every selected fixed ACH; v1 catalogue bytes are checked against its
immutable manifest before they can become the migration baseline.

Of the assemblies, 3,429 are supported selector candidates or residential
component recipes. The other 1,439 are independent, fully recovered source-table
recipes outside the prototype caller's selected climate groups/categories.
They include semiheated, residential, nonresidential and adiabatic recipes. Their
physics, material/layer graph and provenance validate, and their IDs are listed
in the release metadata/receipt. They are not promoted into invented prototype
contexts or counted as selectable alternatives for those contexts.

Run `python -m scripts.construction_set_release` to freeze the normalized release,
or `--check` to regenerate in memory and compare every output's exact UTF-8/LF
bytes. Both validate all contexts and all resources without native recovery,
program generation, site or CI. Identical resource-schema blocks are checked
once by content, while every context's assignment/dependency checks still run.

To export using the frozen v2 tables alone, run
`python -m scripts.construction_set_release --context-id ID --output selected.json`.
Optional `--variant` choices use the same source-supported candidates as the
standalone exporter. Frozen hydration reproduces every default standalone
document, with direct, policy-backed and repeated-story variant regressions.
The release includes its index, both schemas, examples, completeness receipt,
README, source lock, licenses and SHA-256 manifest. Site integration, BEMGen
handoff and protected-main publication remain subsequent work.
