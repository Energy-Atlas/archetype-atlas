# Building Energy Archetype Atlas

Deterministic building-energy semantics for research on geometric and thermal
zoning levels of detail in urban building energy modeling. The governing
specification is [the research brief](docs/AGENT_RESEARCH_BRIEF.md).

The atlas separates program loads and schedules, envelope components, HVAC
definitions, building/program assignments, and field-level provenance. Geometry,
weather files, stock prevalence, and simulation results belong to other workflows.

Sources: ComStock, ResStock, OpenStudio Standards, DOE Commercial Reference
Buildings, and DOE/PNNL Prototype Building Models. Source interpretations and
coverage will be recorded under `docs/` and `sources/`.

Layout: `schemas/` contracts; `sources/` pinned retrieval and selection;
`scripts/` reproducible tooling; `tests/` validation regressions; `data/raw/`
immutable local downloads; `data/interim/` intermediate diagnostics;
`data/processed/` canonical tables; `data/releases/` versioned snapshots.

Release: **v0.2.0**, schema **0.2.0**, dated 2026-10-02. The 17 commercial types
in the union of the DOE Reference and PNNL commercial suites cover 83 selected
building/template combinations. There are 41 residential source configurations
across seven classes: detached, attached, 2â€“4-unit multifamily, low-rise 5+-unit
multifamily, midrise apartment, highrise apartment and manufactured/mobile homes.
This is complete named typology coverage at source-input level; simulation-ready
parameter completeness remains unresolved. Five commercial templates are selected,
not every published code edition. [Machine-readable coverage](docs/validation/coverage.json)
reports expected sets, observed records and unresolved inputs.

The [finite water pilot](data/water-releases/v0.1.0/water-equivalent.json) attaches
a source-conserving fixture draw equivalent to the existing Medium Office
90.1-2013 office program. [ADR 0007](docs/adr/0007-program-water-equivalents.md)
defines its semantics and excludes sampled HVAC unavailability from the schedule
release. [Schedule coverage](docs/validation/schedule-coverage.json) inventories
523 active commercial schedule gaps and 101 residential gaps across 14 assessed
columns; EV/exterior lighting and specialized uses are listed separately.
Near-full deterministic coverage remains the prerequisite to generator delivery.

| Canonical table | Records |
| --- | ---: |
| programs | 768 |
| schedules | 569 |
| envelope_components | 2,451 |
| systems | 1,145 |
| mappings | 1,707 |
| efficiency_rules | 707 |
| residential_options | 692 |
| commercial_options | 227 |
| provenance | 8,876 |
| source_files | 160 |
| residential_archetypes | 41 |
| specialized_rules | 569 |

Templates: DOE Ref Pre-1980, DOE Ref 1980-2004, 90.1-2007, 90.1-2013 and
90.1-2019, interpreted as OpenStudio Standards inputs. Weather remains external;
program rows are not duplicated by climate. See [coverage and gaps](docs/coverage.md),
[source inventory](docs/source_inventory.md) and [schema guide](docs/schema.md).

Python 3.11+ and pinned dependencies reproduce the atlas:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe -m scripts.fetch
.venv/Scripts/python.exe -m scripts.build
.venv/Scripts/python.exe -m scripts.validate
.venv/Scripts/python.exe -m scripts.reproduce
.venv/Scripts/python.exe -m scripts.coverage
.venv/Scripts/python.exe -m scripts.release --verify
```

On macOS/Linux use `.venv/bin/python`. [The reproduction guide](docs/reproducibility.md)
includes the pilot, source comparisons, tests, release freezing and Git security
audit. JSON tables under `data/processed/` are canonical; combined `atlas.json`
and CSV views are local generated conveniences. The frozen release under
`data/releases/v0.2.0/` includes its own schema, source lock, selection and notices.

The source input tables do not apply Ruby generation overrides, HVAC sizing,
daylight/occupancy controls, or model defaults. Infiltration, system COP/fuel/
terminal resolution, mapping area fractions and conditioned state need downstream
resolution. Sixteen invalid legacy source U-values are withheld as null with
the original zeros retained. Direct DOE/PNNL IDF/scorecard comparison is unresolved
because the tested official package links returned 404; pinned source-input
comparison is separately recorded. Do not interpret historical code templates
as calibrated existing-stock buildings.

Original code and documentation are unlicensed at the user's request; no general
permission to reuse them is granted by this repository. Extracted upstream data
retains its original terms and notices. See `LICENSE` and `sources/licenses/`.

Residential configurations are public modeled-input fixtures, not population
representatives. Exact lookup matches reference measure arguments; 524 unmatched
option instances (16 distinct pairs) remain explicit. Six raw thermostat base
overlaps are flagged before offsets/seasonal controls. Area is a source bin,
so exact SI area and densities remain null. HPXML defaults and annual profiles
were not executed or invented in that frozen source snapshot. Both original
atlas releases remain unchanged and verifiable.

The separately versioned [resolution supplement](data/resolution-releases/v0.4.0/manifest.json)
adds actual upstream annual profiles and selective, evidence-gated assumptions.
It contains 38 stochastic residential runs, three explicit zero-occupant skips,
and 41 nominal thermostat profiles. All annual outputs reproduce byte-for-byte.
Weather is an explicitly labelled station proxy; sampled HVAC unavailability
and complete load magnitudes are excluded from the schedule milestone. Four all-electric dwelling
configurations have zero gas equipment; reviewed cavity/core assumptions and
explicit source-zero magnitudes are documented in
[ADR 0004](docs/adr/0004-selective-resolution.md). No blanket null-to-zero rule applies.
Supplement v0.2.0 adds ten reviewed plenum lighting zeros and six data-centre
occupancy zeros; frozen v0.1.0 remains verifiable. The
[source review](docs/schedule-source-review.md) answers remaining recipe and
availability questions. [ADR 0005](docs/adr/0005-parametric-schedule-generators.md)
records the future parametric generator and DOE reference-location direction.
See [generation instructions](docs/residential-generation.md) and verify with
`python -m scripts.resolve --verify`.

Supplement v0.3.0 adds approved gas-equipment zero schedules and densities for
713 programs, five fixed refrigeration background shapes for three zero-occupant
dwelling fixtures, and one explicitly absent freezer zero. It has 2,125 resolutions
and leaves 523 active non-cavity schedule gaps: 485 water and 38 thermostats.
[ADR 0006](docs/adr/0006-deterministic-coverage-release.md) prioritizes near-full
deterministic coverage before generator shipping and proposes a source-conserving
program-level hot-water allocation equivalent. This is an incremental supplement,
not a claim of complete schedule coverage.

Supplement **v0.4.0** supplies all **574 assessed residential profile fields**,
plus exterior lighting for all 41 dwelling fixtures. Refrigeration defaults are
selected-equipment variants, rather than zeros inferred from absent stochastic
columns. Eight executed commercial source-phase cases resolve inactive controls
for 19 exact programs. The associated
[commercial-completion bundle](data/completion-releases/v0.1.0/manifest.json)
preserves 217 fixture paths, conserved source/normalized curves and source evidence.
It closes 206 water absences and retains **279 unsupported program allocations**;
active commercial schedule coverage is **4,859/5,138 (94.6%)**.
See [ADR 0008](docs/adr/0008-reviewed-schedule-completion.md) and
[release notes](docs/release-notes-v0.4.0.md). Both new bundles reproduced byte-for-byte.

The optional [water-reporting v0.1.0 bundle](data/water-reporting-releases/v0.1.0/manifest.json)
supplies **5,138/5,138 operational commercial schedule fields**, preserving the
**279 source-only water allocation gaps**. All 217 fixture paths are assigned
once through source relationships, labeled design-occupant/process allocations,
or retained shared hospital services. Every active program has a reporting curve;
unknown local fixture assignment remains explicit. This does not establish full
simulation readiness. [ADR 0009](docs/adr/0009-complete-water-reporting-variant.md)
documents the distinction. Reproduce/verify with `python -m scripts.water_reporting --verify`.

## Research catalogue site

The local `feature/dto-json-v2` implementation replaces the active site with the
Residential / Non Residential object catalogue. Program, construction and HVAC
pages link to inspectable nested objects. Programs copy self-contained raw or
default-filled JSON, including their schedules, under the
[connector contract](docs/program-json-v2-contract.md). Schedules have unique day
step plots and annual heatmaps. Source unknowns remain explicit.

The [site build guide](docs/site-build.md) provides local verification and preview
commands. Superseded pages, historical URLs and versioned downloads are removed
from the generated site. Frozen research inputs remain immutable in this repository.
This implementation has not been pushed or deployed; the
[published site](https://energy-atlas.github.io/archetype-atlas/) reflects its last
deployment. [Execution findings](docs/reviews/dto-json-v2-execution-log.md) record
local decisions and checks.

## Element definition library and catalogue v2

The [catalogue](https://energy-atlas.github.io/archetype-atlas/catalogue/)
starts with Residential / Non Residential, then Programs / Constructions / HVAC
systems. [The contract](docs/definition-contract.md) describes load bases, scoped
air requirements, component comparison, fixed conditional HVAC ratings and lazy,
manifest-pinned current delivery. Legacy v1 publication is retired.

Canonical definitions: `data/definition-releases/v0.1.1/` (schema 1.0.0).
[Coverage](docs/reviews/catalogue-definition-coverage.md) separates supported
inputs from unknowns; definitions are not automatically simulation-ready models.
[Execution findings](docs/reviews/catalogue-execution-log.md) record decisions.

```console
python -m scripts.definitions --scope pilot --output build/definitions-pilot
python -m scripts.definitions --scope full --output build/definitions-full
python -m scripts.definition_release --verify
python -m scripts.definition_release --reproduce
python -m scripts.query_v2 --input data/definition-releases/v0.1.1 --output build/delivery-v2
```

The library does not size consumer models. Residential definitions reuse existing
determined profiles; stochastic generators remain deferred. Unknown load
magnitudes, infiltration and HVAC details remain explicit. Only the documented
internal/ground construction fallbacks introduce generic construction assumptions.
The explicitly selected program copy defaults are separately recorded and never
replace source evidence.
