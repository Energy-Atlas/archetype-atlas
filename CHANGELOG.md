# Changelog

## Resolution supplement v0.2.0 — 2026-10-04

Add ten user-reviewed ceiling-plenum lighting zeros and six Large Office data-
centre routine occupancy zeros. Schema 0.2.0 adds `reviewed_no_lighting`;
693 resolutions cover 86 records, with 1,270 commercial fields unresolved.
Atlas releases and resolution v0.1.0 remain immutable. Existing annual execution
artifacts are reused byte-for-byte. Catalogue pages use the latest overlay and
retain older supplement downloads.

Document ResStock generator shipping as an accepted future direction, ComStock's
distinct operating-hours transformation, upstream fixed background defaults,
component-scoped gas/water absence, ten residential HVAC-unavailability fixtures
and DOE's sixteen reference locations. Twenty primary references are SHA-256
locked for reproducible inspection; generator interface design remains deferred.
The current evidence lock uses the stable DOE technical report for locations;
the original HTML receipt is retained historically after hosted CI demonstrated
delivery-dependent page bytes. Preserve Denver/Boulder and Chicago/O'Hare city/
weather distinctions. All frozen release hashes remain unchanged.

## v0.2.0 — 2026-10-02

Complete named typology coverage: DOE 16/16 and PNNL 16/16 through pinned
Standards inputs, 83 selected commercial combinations and 41 residential source
configurations across seven classes. Schema 0.2.0 adds residential_archetypes
and specialized_rules, including 569 conditional refrigeration/generator records.
The lock expands to 160 files without changing revisions. Exact option links,
unmatched selections, thermostat base overlaps and runtime gaps are explicit.
The frozen v0.1.0 snapshot remains unchanged and independently verifiable.

## v0.1.0 — 2026-10-02

First normalized source-input research release. Schema 0.1.0 has deterministic
programs, typed schedule rules, conditional envelope/equipment records, source
HVAC descriptors, building/program/system mappings, ComStock/ResStock option
evidence, and field-level provenance. Nine typologies and five templates cover
43 combinations, including multifamily programs.

Sources are pinned to three full repository commits and 91 blob checksums.
Medium Office was validated before expansion. Validation includes schema,
physical/schedule bounds, deadbands, foreign keys, provenance, source comparisons,
security scanning, offline byte reproduction, and immutable release checksums.

Sixteen invalid legacy U=0 source values are withheld as null with evidence.
Direct DOE/PNNL IDF/scorecard comparison remains unresolved after failed linked
downloads. Original work remains unlicensed by user choice; upstream notices
are retained. See `docs/coverage.md` for unresolved simulation inputs.

Migration: none; this is the initial schema. Later breaking schema changes will
carry explicit migration notes and preserve this release snapshot.
