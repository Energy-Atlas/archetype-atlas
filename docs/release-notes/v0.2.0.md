# v0.2.0 — complete named typology coverage

Expands from nine commercial types to the 17-type union of the DOE Reference
and PNNL commercial suites: 16/16 in each, across five selected templates (83
combinations). Adds schools, healthcare, warehouse, small/large office and
supermarket programs, schedules and HVAC maps. No tagged source spaces were
excluded by the exact program lookup.

Adds 41 deterministic ResStock configurations across seven residential classes:
single-family detached/attached, 2–4-unit multifamily, low-, mid- and high-rise
5+-unit multifamily and manufactured/mobile homes. Adds 569 conditional
refrigeration records. The lock expands from 91 to 160 files at unchanged revisions.

Schema 0.2.0 adds residential_archetypes and specialized_rules. Consumers must
accept these tables, expanded vocabularies and provenance targets. Existing field
meanings/IDs are retained. v0.1.0 remains unchanged and independently verifiable.
See ADR 0002 for source-dependent residential semantics and migration guidance.

Source fidelity remains distinct from readiness: 524 residential option instances
are unmatched against the pinned lookup, six thermostat base overlaps are flagged,
exact dwelling area is unknown and runtime defaults/schedules are unexecuted.
Refrigeration values retain source units and predicates. Direct DOE/PNNL IDF
comparison and generated-model simulation validation remain unresolved. No claim
of all code editions, all stock combinations or national representativeness.

Validation includes schema, physical/schedule/provenance relationships, named
typology coverage, independent source comparison and offline byte reproduction.
Final review and verification are recorded in docs/review-v0.2.0.md and
docs/validation/verification-v0.2.0.json.
