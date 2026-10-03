# Changelog

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
