# ADR 0002: named typology coverage and residential configurations

Status: accepted under the autonomous research brief and user extension request.

Schema 0.2.0 adds residential_archetypes and specialized_rules. Commercial
selection expands through exact pinned prototype_inputs entries. DOE Reference
and PNNL suite membership is separately enumerated: their 16-type lists differ
(Supermarket versus Highrise Apartment). There are 17 commercial types and 83
template/type combinations across the original five commercial templates.

ResStock semantics depend on jointly selected geometry, adjacency, envelope,
HVAC, appliances and schedule arguments. Independently crossing options would
discard those dependencies. Retain all 41 records of the pinned public SDR
minimal modeled-input fixture. Source IDs identify fixture rows, not real street
addresses. Export lookup-defined energy parameters and limited physical/climate
context; exclude unrelated demographic, income and survey geography columns.

The explicit source height crosswalk assigns 5+ units/1–3 stories to low-rise,
4–7 stories to midrise and 8+ stories to highrise. These are source classifications,
not universal architectural definitions. Standards apartment programs and
ResStock dwelling recipes retain distinct source families.

Every exact argument-bearing option has a reference and TSV line provenance.
Unknown labels are separately retained, never reclassified as null or no-op.
Exact non-argument options are separately enumerated. Fixture and lookup at the
same repository revision have 16 unmatched parameter/option pairs (524 instances),
including None, Occupied and shared-equipment labels. This is compatibility
uncertainty, not authorization to invent replacements.

Occupants and base thermostat temperatures are direct deterministic values.
Thermostat bases precede offsets, unavailable days and seasonal execution. Six
overlaps are explicitly flagged; all configurations have simulation_ready=false.
Floor area is a bin: exact SI area and densities remain null. Schedule profiles,
HPXML defaults, geometry-dependent assembly and sizing require a validated
generator integration.

Refrigeration rules retain complete compressor/condenser/system/walk-in rows
and conditions in source_attributes. Numeric units are not uniformly labeled:
these are evidence, not normalized installed loads. Healthcare and other process
adjustments may require generator routines beyond canonical program load rows.

Migration: consumers must accept two new tables, expanded type/template
vocabularies and provenance targets. Existing field meanings and IDs are retained.
Version-specific inventories let v0.1.0 verify against its frozen contract.
Coverage audits check named classes and every selected commercial combination;
they do not certify simulation readiness, every code edition or stock combination.
