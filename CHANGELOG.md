# Changelog

## Suite-based site — 2026-10-27

Replace the definition-release catalogue with the suite-based site of ADR 0036 section 10
([ADR 0043](docs/adr/0043-suite-based-site.md)). `python -m scripts.suite_site` reads the
newest release under `data/atlas-releases` through `atlas_exports.Release`:
- one page per program and per construction set, with schedules, loads, fillings and
  evidence anchored in place, `?version=` and context switches in the query string;
- one page per template × building type folder (mixes, services, systems, water) and per
  template library, an evidence glossary and the `view/?id=` viewer;
- one content-addressed JSON store (`store/`) replacing `json/` and `delivery/v2`.

Search indexes each suite page once. New `site_check` and Chromium `site_smoke` gates;
CI caches the generated tree under an input digest. The old generators (`active_site`,
`definition_site`, `object_site`, `construction_site`, `query_v2` and their helpers,
browser scripts and tests) are retired. Old record URLs return the 404 page. No
deployment is claimed.

## Atlas release 1.4.0 candidate (residential families) — 2026-10-26

Add the residential tree of ADR 0038 as a delta on 1.0.0 that holds release 1.3.0
(and so 1.1.0 and 1.2.0) unchanged:
- **ResStock (S12a):** the 41 SDR fixture dwellings, one program each with its
  annual series and fillings, and one construction set of one context. Every value
  equals its frozen source; exports equal the frozen exporters' documents.
- **IECC residential (S12, ADR 0041):** editions 2006 to 2024, single-family and
  per-unit multifamily, one program per appliance fuel, entries with `applies_with`
  for foundation, climate code and heating system; 14 construction sets with 1,036
  climate × foundation contexts. Extracted offline from 4,144 pinned models.
- **Manufactured housing (S13, ADR 0042):** HUD Code and DOE Final Rule 2022
  (tier 1 and 2), single- and multi-section; contexts per location with the five 3A
  cities as sub-contexts. Gap: no existing-building category.
- **Contracts:** Program JSON 5.3.0 (additive minor for dwellings) and source model
  constructions 1.0.0; `idf_schedules` reads Schedule:Year, Week and Day objects.

Answer-key tests compare every IECC edition in 4A and 1AWH and every
manufactured-housing location under the HUD Code with the IDFs when they are present.
No hosted check or deployment is claimed. See the
[release and migration notes](docs/release-notes-atlas-v1.4.0.md).

## Atlas release 1.3.0 candidate (IECC commercial prototypes) — 2026-10-26

Add the IECC commercial prototype family (ADR 0040). It covers 16 PNNL building types in
the IECC 2006, 2009, 2012, 2015, 2018 and 2021 editions, in 96 folders under
`commercial/iecc-<year>/`.
- Values are extracted offline from the pinned PNNL IDFs into six definition inputs.
  Each IDF is checked against its archive record, and every schedule conversion over
  the full year.
- 1,134 programs and mixes. Zones map to standards space types through one lookup
  table with a reasoned alias table. Absent objects are source zeros, and the 2021
  lighting that differs by climate is stored as `value_by_climate`.
- 1,077 building services and hot-water draws with zone gains.
- 96 detailed construction sets of 19 contexts, with the IDF design-flow infiltration
  and the whole-building window ratios. The unified representation is deferred.
- Additive exports Program JSON 5.2.0 and detailed constructions 4.2.0.
- Answer-key tests compare the release with the IDFs in Buffalo, Miami and Fairbanks.
- An evidence-only report compares IECC with 90.1.
- The delta `data/atlas-releases/v1.3.0` holds releases 1.1.0 and 1.2.0 unchanged.

No frozen release or existing record changes. See the
[release and migration notes](docs/release-notes-atlas-v1.3.0.md) and the agent
decisions in ADR 0040.

## Atlas release 1.2.0 candidate (construction-only programs) — 2026-10-26

Add programs to the 51 template × building-type folders that had construction sets
only (ADR 0039). The new types are college, courthouse, laboratory, data centres,
detailed offices, the generic office, and tall buildings.
- 819 source programs, 39 general mixes, 193 HVAC systems and 99 hot-water services.
  They are built offline from pinned openstudio-standards sources by the existing
  builder, definition, composition and resolution code.
- User-approved fillings follow the resolution policy's rules.
- Courthouse design days and one Courthouse holiday rule are completed in the filled
  export. The generic office's hot water is a per-area estimate from the large
  detailed office, recorded as a research assumption.
- The delta `data/atlas-releases/v1.2.0` holds release 1.1.0's changes unchanged.
- Release 1.2.0 also records the residential storage decisions (ADR 0038).

No frozen release or existing record changes. See the
[release and migration notes](docs/release-notes-atlas-v1.2.0.md).

## Atlas release 1.1.0 candidate (DOE reference reconciliation) — 2026-10-25

Reconcile the DOE Ref templates with the pinned DOE v1.4_7.2 post-1980 and
pre-1980 models (ADR 0037). A 1,874-row register records every difference and its
decision, and a generated site page publishes it. The delta release
`data/atlas-releases/v1.1.0` (504 files, 371 deletions on 1.0.0) applies the register.
It sets DOE schedules on 920 program slots and DOE densities and heat fractions where
they differ. It adds four DOE zone-group programs and recomposes the mixes, adds
hot-water zone gains and 158 building services, and puts the DOE infiltration method,
internal-mass fills, window ratios and the source calendar beside the existing data.
The 90.1 templates are unchanged.

Add the additive exports Program JSON 5.1.0, constructions 4.1.0 / 3.1.0 and building
services 1.0.0. Answer-key tests compare the release with the extracted DOE values.
With the IDFs present, they also compare every program slot with the DOE schedules.
No hosted check or deployment is claimed. See the
[release and migration notes](docs/release-notes-atlas-v1.1.0.md) and the
[BEMGen handoff](docs/bemgen-handoff-doe-reconciliation.md).

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
