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

Release: **v0.1.0**, schema **0.1.0**, dated 2026-10-02. Nine building types and
five templates cover 43 building/template combinations, including mid/high-rise
apartments. This is a source-input research atlas; unresolved inputs are explicit.

| Canonical table | Records | Meaning |
| --- | ---: | --- |
| programs | 296 | Deterministic program loads, ventilation components and schedule IDs |
| schedules | 319 | Full dated source rules, design days and typed units |
| envelope_components | 2,451 | Conditional assembly limits/targets by climate set and template |
| systems | 788 | Source HVAC descriptors and schedule references |
| mappings | 941 | Source program/system assignments and benchmark multiplicity |
| efficiency_rules | 707 | Capacity/fuel/subtype-dependent equipment rating rules |
| residential_options | 139 | Explicit ResStock dwelling option/measure evidence |
| commercial_options | 227 | Explicit ComStock option/measure evidence |
| provenance | 5,868 | Field origins, original values/units and transformations |

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
.venv/Scripts/python.exe -m scripts.release --verify
```

On macOS/Linux use `.venv/bin/python`. [The reproduction guide](docs/reproducibility.md)
includes the pilot, source comparisons, tests, release freezing and Git security
audit. JSON tables under `data/processed/` are canonical; combined `atlas.json`
and CSV views are local generated conveniences. The frozen release under
`data/releases/v0.1.0/` includes its own schema, source lock, selection and notices.

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
