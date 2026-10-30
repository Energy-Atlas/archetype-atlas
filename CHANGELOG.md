# Changelog

## Zoning recommendations: a robust headline across orientations — 2026-10-29

- **The rule** (ADR 0050 section 6, open item 10 of the LOD study, approved by the owner):
  for each prototype × climate zone × vintage the robust zoning is the coarsest (fewest
  modelled zones) that meets the threshold at both orientations by the writer's own
  per-zoning verdicts; ties go to a zoning both orientations recommend, else to the first
  in the study's zoning order, and are named. Beside it: the worse of the two
  orientations' errors and the cost ratios of that zoning over the pair's timed sites.
  Where none meets at both, the pair says so and names each orientation's own pick. The
  data file lists every kept zoning per cell, so the full rule applies, nothing is
  recomputed, and the writer's files are unchanged. Drop 2: 109 of 132 cell pairs.
- **Pages** (`scripts/lod_site.py`): a "Robust across orientations" section opens every
  prototype page (one row per climate zone × vintage, a header fact); the overview's
  prototype table, paragraph and tally carry the pair counts; the method page explains
  the rule, what the data allows and the limits; the catalogue program fact names the
  robust picks of the program's cell pairs; each prototype's JSON slice carries a labelled
  `robust` block; the manifest records `cell_pairs` and `robust_pairs`. The orientation
  filter leaves rows marked `data-across="orientation"` visible (`suite.js`); `site.css`
  aligns the new table. `tests/test_lod_site.py`: 16 new tests (35 in all).

## CI workload pass 3: pull requests build a sampled catalogue site — 2026-10-29

- **`suite_site --sample N`** builds the site-wide pages and at most N folders of every
  family × template, chosen by a fixed rule (`sample_folders`: the folder whose programs
  span the most modes, then the cheapest in programs and construction contexts, then the
  first path); `site-manifest.json` records `partial` and the `sample`. For release 2.1.0,
  `--sample 1` is 21 of 255 folders: `retail-standalone` of every non-residential
  template, `multifamily` of every IECC residential template, the manufactured-housing
  folders and ResStock's `highrise-apartment`.
- **`site_check` on a sample** runs every check within the sampled folders and the
  site-wide pages and excuses only a link into a folder the sample left out;
  `--require-complete` refuses a sample as it refuses `--only`. `site_smoke` searches
  the picked program by the last hyphen-separated piece of its ID (`mixed.f21a21`), one
  index token carrying the hash, which matches that page alone: a slug such as
  `sales-mixed` ties with the same program of every other template and the result list
  shows ten, and the full ID matches every page sharing a template or mode token.
- **The catalogue workflow's `build` job** generates, builds strictly and verifies the
  sample on a pull request, with no cache and no Pages artifact; a push to `main`, the
  weekly run and a manual run build, cache, verify and publish the full site as before.
  Required check names are unchanged. Measured on pull request #36 before this pass:
  `build` 32.8 min on a cache miss (generation 16.8 min, MkDocs 11.9 min, checks 2.7
  min); the sampled build of pull request #37: 5.1 min (generation 1.3 min, MkDocs 1.7
  min, checks 0.8 min), so a pull request's checks finish with the research jobs.

## Zoning recommendations drop 2: the serial costs and the completed study — 2026-10-29

- **Data drop 2** (ADR 0050 section 5): the consolidated files of BEMGen `38ff521`
  (D-200 to D-203) replace drop 1 in place. `lod-recommendations.json` (schema 1.1.0)
  keeps R3's 264 cells and recommendations and adds the R5 serial costs, a `cost` object
  on the 12 timed references and 206 timed test sites and a `timing` block (gate verdict,
  repeat check, medians by zoning and prototype); `lod-recommendations-ht.json` carries
  the zoning of its 24 failed small-hotel sites; `provenance.json` records the four
  BEMGen builds, every stage's suite, run and gate verdict, the report and methodology
  paths and nothing pending. The schema copy is 1.1.0 and the loader accepts both
  versions.
- **Pages**: cost columns (CPU, wall and memory ratio to the reference; "not timed" for
  the medium office, the primary school and every cell outside the 12 timed ones) in the
  summary tables and the timed cells' zoning tables; a cost section on the overview with
  the writer's medians by prototype and by zoning; the status says every stage is
  complete and links the report, methodology, run plan and results; the method page gains
  the cost protocol, the reading cautions of the report and D-201's wording for the
  failed sites.

## Zoning recommendations of the geometric LOD study on the site — 2026-10-29

- **Data drop 1** (ADR 0050): `data/lod-recommendations/v1/` holds BEMGen's
  `lod-recommendations.json` of the R3 main matrix (264 cells: 11 prototypes × 6 climate
  zones × 90.1-2007 and 90.1-2019 × 0° and 45°), `lod-recommendations-ht.json` of the R4
  heat-transfer sub-study (22 cells) and `provenance.json` (BEMGen `b29931c`, D-193, the
  suite and run IDs, atlas inputs 2.0.0 at `96a2e928`, the threshold, digests). The
  schema is copied to `schemas/lod-recommendations-v1.schema.json` and
  `tests/test_lod_site.py` validates the files against it. A consolidated drop after the
  R5 timing pass and the R6 report replaces the files in place.
- **Site section "Zoning recommendations"** (`scripts/lod_site.py`, generated with the
  suite pages): an overview, one page per prototype (climate zone × vintage × orientation
  rows with the reference's annual sensible heating and cooling, the recommended zoning,
  its annual errors, CV(RMSE), NMBE and conditioned-area change, then every zoning of
  every cell and the atlas programs used), the heat-transfer sub-study and a method and
  caveats page. Program pages the study used link to their prototype's page. The drop
  joins the site's cache digest; `site_check` requires the pages.

## Atlas release 2.1.0: the open licence and the generator 3.0.0 recipes — 2026-10-29

Release 2.1.0 is a delta on 2.0.0 (ADR 0046 section 12; `scripts/atlas_delta.py`, `--write`,
`--check`, `--verify`), status `released`, with ten files and the manifest:
- `LICENSE`: the open-licence text (ADR 0048);
- `generator.json` of the eight apartment folders: the 38 apartment-unit recipes are the
  generator 3.0.0 ResStock multifamily unit recipes (ADR 0047), as the `atlas-schedules` 3.0.0
  package ships them; 1,506 other recipes unchanged;
- `manifest.json`: `base_release` 2.0.0 with its manifest digest; `generator` names the
  generator version, package, wheel and tag (ADR 0049); pinned inputs.

Every ID is 2.0.0's. `atlas_exports.Release` defaults to the newest release in the tree, the
export schemas admit `atlas-release-2.1.0`, the site shows 2.1.0, and CI runs
`atlas_delta --check` beside the 2.0.0 checks. Release notes:
`docs/release-notes-atlas-v2.1.0.md`.

## The atlas-schedules package and a lighter pull-request CI — 2026-10-29

- **`atlas-schedules` 3.0.0 as a pip package** (ADR 0049): `pyproject.toml` builds the
  `atlas_schedules` package with its recipes, tables, notices and request schema; the
  console script `atlas-schedules` runs the same command as `python -m atlas_schedules`.
  The package version is `atlas_schedules.__version__` (now `3.0.0`, no longer
  `3.0.0.dev0`), which every bundle names as `generator_version`. A tag
  `atlas-schedules-vX.Y.Z` builds the wheel and attaches it to that tag's GitHub release
  (`.github/workflows/atlas-schedules-release.yml`); the package is not on PyPI.
  `requirements-dev.txt` pins `build`. Generator 3.0.0's packaged recipes were built
  from atlas release 2.0.0 and are carried by release 2.1.0.
- **CI workload pass 2.** The schedules unit shard is split in two (`scripts/ci_tests.py`),
  the catalogue smoke generates a deterministic sample of two recipes per family and two
  configurations per service on pull requests (`smoke_catalogue --sample 2`; the full
  catalogue runs on pushes to `main`, weekly and manually), and a `package` job builds
  the wheel, installs it in a clean environment and generates the quick-start example.
  Required check names are unchanged.
- Plan `docs/superpowers/plans/2026-10-29-public-release-stages.md` records the public
  release stages (atlas A1 to A3, BEMGen B1 to B3, LOD study C1 to C4).

## Open licences for original work — 2026-10-29

- Original code is now MIT-licensed and original data and documentation CC BY 4.0 (ADR 0048).
  The grants cover earlier releases, including 2.0.0, whose packaged `LICENSE` keeps its old text.
  Upstream material keeps its own terms and notices.

## Generator 3.0.0: ResStock apartment units and source-magnitude binding — 2026-10-28

Breaking (ADR 0047; user decisions O15 to O21):
- **Apartment units are ResStock multifamily units.** Each unit draws its ResStock housing
  characteristics (a port of the sampler over 67 pinned tables, conditioned on climate zone ×
  programme: the request's climate zone, or one drawn from its state, with every state in the
  zone pooled; the floor area and residents; and the programme's building type, height, era and
  HVAC, dropped only in Alaska, where no apartment has the prototype HVAC). It then takes every internal load's annual energy from the ported
  OpenStudio-HPXML equations, its schedules from the ResStock generator, and its thermostat
  from the same draw. Hot water is the prototype's 66.33 L per design person per day × the
  unit's residents, timed by the unit's own fixture events. The 38 apartment recipes are
  rewritten by `scripts/build_apartment_units.py`; the prototype apartment path is removed.
- **Commercial loads bind their source magnitude.** Lighting, plug and gas densities and
  shared-water peak flows are the amplitudes; annual energy and volume follow the sampled
  hours, as in ComStock. ResStock dwellings keep their annual totals.
- **Request and bundle schema 3.0.0**: `residents: "resstock"`, `location.climate_zone` and
  `location.weather_id`; apartment units need `extent.floor_area`.

Validation: the annual equations match the pinned Ruby for 240 units × 21 end uses within
1e-9 (`docs/validation/resstock-annual-equivalence.json`); the measure arguments match all
5,867 recovered Ruby inputs; the sampler matches rejection sampling. Release 2.0.0 keeps
its 2.x apartment recipes in `generator.json`; the next release carries the new ones.

## Construction exports no longer follow the hash seed — 2026-10-28

- `ConstructionSuite.export` merged the shared and per-context fields through a set, so the order of
  a document's top-level fields, and with it the exported bytes, changed with `PYTHONHASHSEED`. The
  values were always equal. It now keeps the stored order; a test exports the IECC 2021 sets under
  three seeds and compares the bytes. Found by BEMGen's byte-for-byte fixture check (its D-173).

## BEMGen's 2.0.0 report: schema fixes and the IECC ground-floor erratum — 2026-10-28

- Shared mass-accounting contract 1.1.0 (`schemas/construction-mass-accounting-v1.1.schema.json`):
  1.0.0 with the optional `evidence_id` on additional-mass entries that constructions 4.1.0 / 3.1.0
  embed, now derived from them so the two cannot drift.
- Program JSON 5.4.0: the daylighting description says the fractions are applied as given.
- Release 2.0.0 corrected in place (user decision, ADR 0046 section 11): the IECC adiabatic
  F-factor slabs with no exposed perimeter move from `InteriorFloor` to the `GroundFloor` building
  default in 30 construction sets, leaving the interior floor capacity budgets (zero capacity).
  Their new set IDs are in `id-map.json`.

## Atlas release 2.0.0 released (milestone B) — 2026-10-28

Release 2.0.0 is declared released after milestone B (ADR 0046 sections 8 to 10).
`scripts/release_editor.py` edits it in place:
- every commercial content-hashed ID re-derived under interpreter-independent rules (11,507 in
  `id-map.json`; 57 near-identical fitted assemblies merged);
- the PNNL 90.1 prototype constructions recorded as `alternates` where they differ from
  openstudio-standards by more than 1% (`scripts/construction_alternates.py`, detailed
  constructions 4.3.0).

The openstudio-standards daylighting rules are pinned and the 90.1 daylighting records checked
against them (`docs/reviews/daylighting-rules-90-1.md`). CI runs `release_editor --check` and the
daylighting review.

## Frozen folders retired (X1.3) — 2026-10-27

Release 2.0.0 is the only release in the tree (ADR 0046 section 7). Releases 1.0.0 to
1.6.0, the v0.x, definition, resolution, completion, water and construction releases and
their inputs (about 2.45 GB) are removed, with the 80 scripts and 68 test modules that
wrote, verified or investigated them. They stay readable at the tag
`frozen-data-2026-10-27`. `atlas_exports` reads 2.0.0 by default; `atlas_snapshot` is a
reader. CI keeps the three required checks: Linux unit tests, release and smoke jobs; the
unit tests on Windows with Python 3.14; the site build. The README describes release
2.0.0.

## Atlas release 2.0.0 candidate: DOE Ref recipes and plain daylighting (X1.2) — 2026-10-27

The DOE Ref generator recipes are rebuilt from release 2.0.0 under release IDs
(`scripts/build_reference_recipes.py`, ADR 0046 section 6), with the People topology from
the DOE file zones. They replace 786 packaged files built from the frozen definitions.
The generator request accepts release IDs. The answer-key cases of the replaced recipes
are listed in `tests/answer_keys/retired-doe-ref.json` and skipped. Release 2.0.0 drops
`lighting_controls.geometry_dependent`, so the daylighting fractions are plain values
(user decision L-1), and its DOE Ref folders gain `generator.json`.

## Atlas release 2.0.0 candidate: self-contained (X1.1) — 2026-10-27

Release 2.0.0 now reads and exports with no frozen folder present: `exporter-inputs.json`
carries the capped-delivery IDs and the programs with no setpoint schedules, and readers
verify the files alone (ADR 0046 section 5). Exports are unchanged.

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

## Atlas release 2.0.0 candidate (full snapshot, phase 1) — 2026-10-27

A full snapshot of release 1.6.0 that ends the delta chain (ADR 0046, stage X1 phase 1):
same values, indented JSON one record per line (439 → 337 MB), and the generator
recipes of 610 90.1 programs in each folder's `generator.json`. The folder is built by
`python -m scripts.atlas_snapshot` and not committed until the 1.x deltas and frozen
folders retire (phase 2). See the [release notes](docs/release-notes-atlas-v2.0.0.md).

## Atlas release 1.6.0 candidate (IECC unified constructions) — 2026-10-27

Add, as a delta on 1.0.0 that holds release 1.5.0 (ADR 0045, stage U): building-level
equivalent (unified) constructions for all 1,824 IECC commercial contexts, weighted by
the net surface areas of the source IDFs and computed with the existing equivalence
physics. F- and C-factor ground constructions keep their native assemblies; adiabatic
core floors that PNNL gives an F-factor construction are left out of the fits and
listed. See the [release notes](docs/release-notes-atlas-v1.6.0.md).

## Atlas release 1.5.0 candidate (lighting controls, plenums) — 2026-10-27

Add, as a delta on 1.0.0 that holds release 1.4.0 (ADR 0044):
- **Lighting controls (stage L):** every commercial program records the daylighting
  controls of its source model zones: controlled floor and lighting-power fractions,
  setpoint, control type and minimum fractions, by climate where they differ. IECC
  and 90.1 values come from the PNNL prototypes (195 programs with controls); DOE Ref
  programs record a source zero. Occupancy-sensor credits stay in the schedules.
- **Plenums (stage G1):** the 90 spaces ADR 0039 left unmapped take the Any/Plenum
  row, adding plenum programs to 19 folders.
- **Contracts:** Program JSON 5.4.0 for every program of the release.

Answer-key tests compare control fractions with the IDFs when they are present. See
the [release and migration notes](docs/release-notes-atlas-v1.5.0.md).

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
