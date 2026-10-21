# Changelog

## Foundation/ground publication candidate — 2026-10-19

Prepare combined construction delivery 1.0.0, detailed schema 3.0.0 and unified
schema 2.0.0: 177 suites / 3,320 contexts, with 3,308 executable contact cases and
12 source-supported no-contact cases. Reuse component/assignment and provenance
structures for four foundation roles. Preserve native F/C, layered-ground and Kiva
methods, single parameter ownership and 20 narrow unified native exceptions.
Above-ground recipes, fixed ACH, shared mass, program/schedule outputs and earlier
frozen releases are unchanged.

Update the browser harness to compare current preview/copy exports and selected
foundation summaries, and add combined frozen-output/recovery-receipt checks to
the existing publication pipeline. Native recovery and engine execution remain
opt-in. Document recipe-versus-instance scope, explicit geometry operands and
source-policy initialization, with required BEMGen v7 tests.

This is a local publication candidate; no hosted checks or deployment are claimed.
BEMGen acceptance remains pending. Systems and schedule-generator packaging are
outside this milestone; lighter artifact delivery remains deferred. See the
[release and migration notes](docs/release-notes-construction-foundation-v1.0.0.md).

## Construction publication candidate — 2026-10-15

Prepare detailed distribution v2.2.0 (consumer schema 2.0.0) and additive unified
construction 1.1.0 for publication: 177 complete sets, 3,320 supported contexts,
embedded space rules, explicit generic hotel applicability, fixed reference ACH,
precomputed construction shares and mass budgets. Retain detailed source physics,
all fitting errors and accepted approximation flags. Both construction copy
actions are direct; other object copy behavior is unchanged.

Add required construction presence, frozen-release reproduction and separate
construction browser checks to the existing publication pipeline. No deployment
or remote check run is claimed. [Release notes](docs/release-notes-construction-v2.2.0.md)
record contract versions, migration, consumer inputs and deferred ground/systems.

## Site UI and release gate — 2026-10-07

Restyle the catalogue site into the EnergyAtlas family design
(`design/ui-design-spec.md`): the wiki palette with contrast-adjusted tokens,
self-hosted Geist, Geist Mono and Cormorant Garamond with their OFL notices,
system-preference light and dark themes, framed columns, technical tables,
square controls, breadcrumbs, a restrained landing hero with section grids, and
themed record pages and schedule charts. No data, schema or release changes.

The catalogue workflow now verifies the frozen releases only when a
release-relevant path changes ([release gate](docs/site-build.md#release-gate));
presentation checks still gate every deployment, and `validate.yml` still
verifies every release on every push.

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
