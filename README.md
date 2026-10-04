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
across seven classes: detached, attached, 2–4-unit multifamily, low-rise 5+-unit
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

The separately versioned [resolution supplement](data/resolution-releases/v0.3.0/manifest.json)
adds actual upstream annual profiles and selective, evidence-gated assumptions.
It contains 38 stochastic residential runs, three explicit zero-occupant skips,
and 41 nominal thermostat profiles. All annual outputs reproduce byte-for-byte.
Weather is an explicitly labelled station proxy; unavailable-day overrides,
EV and other non-exported end uses remain unresolved. Four all-electric dwelling
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

## Research catalogue site

Browse the [published catalogue](https://energy-atlas.github.io/archetype-atlas/).
The profile/resolution extension is maintained on `feat/schedule-resolution`;
the research branches remain unmerged.

The MkDocs catalogue presents frozen v0.1.0 and v0.2.0 through building, program,
vintage/template, climate, system, source and status views. Entry pages include
parameters, field provenance, exact downloads and interactive daily schedule
inspection. Residential runtime gaps and conditional source rules remain explicit.

See the [site build and verification guide](docs/site-build.md) for reproducible
commands, preview, dependency pins and the GitHub Pages workflow.
Generated HTML is an inspection view; canonical research data is unchanged.
The [publication record](docs/site-publication.md) identifies the tested commit
and deployment evidence.
