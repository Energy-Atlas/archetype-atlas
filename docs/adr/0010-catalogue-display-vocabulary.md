# ADR 0010: Controlled catalogue display vocabulary

Status: accepted under the user-approved naming follow-up on 2026-10-05.

## Decision

Keep canonical atlas records and frozen releases unchanged. Maintain the
presentation vocabulary in `scripts/catalogue_names.py`, with explicit maps for
the 22 building codes and 108 program codes found in v0.2.0. Those maps cover
v0.1.0 as well. Unreviewed future values fall back to their reported strings.

Apply the maps consistently to record titles, catalogue facets, mapping program
references, and shared schedule building/template contexts. Keep numbered source
program identities distinguishable. Align the abbreviation pairs
`nursestation`/`nursestn` and `physicaltherapy`/`phystherapy` under Nurse station
and Physical therapy respectively; these pairs occur in different building
types, with no same-building/template title collisions. Preserve the existing
`office` and `apartment_unit` program
groupings but qualify record titles for basement/other-floor and top-floor NS/WE
variants. Source strings, variants, IDs and provenance remain in record packets.

Preserve historical raw-code filter queries with `facet_aliases`, old category
addresses with the existing generated alias pages, and raw-code text searches
with flat `search_aliases`. Building aliases are attached to records with that
building facet; shared schedules retain paired readable referenced contexts.
Attaching a referenced building alias to a schedule's own “Shared / not assigned”
facet would produce an ambiguous alias target and is intentionally avoided.

## Scientific interpretation

Display alignment does not equate code/prototype rules with DOE existing-stock
benchmarks, or commercial apartment common areas with ResStock dwellings.
Source descriptions `Office`, `Any`, and “Multi-Family with 5+ Units” are too
coarse to be global aliases for specific building categories. Numeric hotel
suffixes and the `Hall_infil` qualifier retain source meaning without inventing
floor assignments or missing infiltration values.

## Validation

Regressions cover complete vocabulary coverage, distinct numbered categories,
source-preserving catalogue generation, variant title distinctions, mapping
reference consistency, historical filters/searches/category addresses, building
detail joins, and exact shared schedule building/template pairs.
