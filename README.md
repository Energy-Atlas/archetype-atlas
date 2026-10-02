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

Status: first release under development. Python 3.11+ is the intended runtime.
See `docs/reproducibility.md` for the final workflow and release checks.

Original code and documentation are unlicensed at the user's request; no general
permission to reuse them is granted by this repository. Extracted upstream data
retains its original terms and notices. See `LICENSE` and `sources/licenses/`.
