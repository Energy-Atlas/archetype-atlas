# Building Energy Archetype Atlas

Deterministic building-energy semantics for research on geometric and thermal
zoning levels of detail in urban building energy modeling. The governing
specification is [the research brief](docs/AGENT_RESEARCH_BRIEF.md).

The atlas separates program loads and schedules, envelope components, HVAC
definitions, building/program assignments, and field-level provenance. Geometry,
weather files, stock prevalence, and simulation results belong to other workflows.

Sources: ComStock, ResStock, OpenStudio Standards, DOE Commercial Reference
Buildings, DOE/PNNL Prototype Building Models (ASHRAE 90.1 and IECC, commercial
and residential) and the PNNL manufactured-housing models. Source interpretations
and coverage are recorded under `docs/` and `sources/`.

## Release 2.0.0

**Atlas release 2.0.0** (`data/atlas-releases/v2.0.0`, status `released`) is the
only release in the tree ([ADR 0046](docs/adr/0046-release-2-0-0.md),
[release notes](docs/release-notes-atlas-v2.0.0.md)). It is a full snapshot: open
the folder alone, with no base release to resolve. It holds:
- the commercial programs, mixes, services, systems and water of the 90.1, DOE Ref
  and IECC templates, with lighting controls;
- the residential tree (ResStock dwellings, IECC residential and manufactured-housing
  prototypes);
- detailed and unified construction sets;
- the generator recipes of the 90.1 and DOE Ref programs in each folder's
  `generator.json`;
- the PNNL prototype constructions of the 90.1 templates where they differ from
  openstudio-standards, as `alternates` (detailed constructions 4.3.0);
- the evidence tree and upstream notices.

```console
python -m scripts.atlas_snapshot --verify                 # every file against the manifest
python -m scripts.release_editor --check                  # IDs follow their rules (id-map.json lists the changes)
python -m scripts.atlas_exports --program ID --version filled
python -m scripts.atlas_exports --construction SET --context KEY --representation detailed
```

Exports are Program JSON 5.4.0, detailed constructions 4.x and unified
constructions 3.x; the [consumer contracts](docs/consumer-contracts-release-1.0.0.md)
and later release notes describe them. BEMGen's updates for 2.0.0 are listed in
[bemgen-handoff-release-2-0-0.md](docs/bemgen-handoff-release-2-0-0.md).

## Earlier releases

Releases 1.0.0 to 1.6.0 were deltas on 1.0.0. Before them came the source-input
releases v0.1.0 and v0.2.0, the resolution, completion and water-reporting
supplements, the definition release v0.1.1, and the construction releases (detailed
2.x, unified 1.x, shared mass and combined foundation). They left the tree in stage
X1.3 (ADR 0046 section 7). The tag `frozen-data-2026-10-27` keeps them with their
builders, so each can still be verified or rebuilt there. Their release notes and
ADRs stay under `docs/`.

## Research catalogue site

The [site](https://energy-atlas.github.io/archetype-atlas/) shows the latest release
under `data/atlas-releases` ([ADR 0043](docs/adr/0043-suite-based-site.md)):
- one page per program and per construction set, with its schedules, loads,
  fillings and evidence in place;
- one page per template × building type folder;
- a `view/?id=` viewer for any ID;
- one content-addressed JSON store holding every source and filled export.

Pages read without JavaScript; `?version=` and context switches narrow them. The
[site build guide](docs/site-build.md) gives the local build, checks and preview.

## Schedule generator

The offline [schedule generator](docs/schedule-generator.md) (`atlas_schedules`)
turns programmes, extents and a seed into 8,760-hour schedules, with each annual
load target bound to its generated shape. It is a readable port of ComStock /
openstudio-standards 0.8.6 hours-of-operation sampling and of OpenStudio-HPXML's
ResStock occupant model ([ADR 0035](docs/adr/0035-readable-generator-restructure.md)).
- **90.1 recipes:** built from the frozen definitions.
- **DOE Ref recipes:** written from release 2.0.0 under release IDs
  (`python -m scripts.build_reference_recipes`).
- **Validation:** native OpenStudio / Ruby answer keys in `tests/answer_keys/` check
  it to 1e-6.
- **Catalogue smoke:** `python -m scripts.smoke_catalogue` generates every packaged
  recipe and service.

## Source pipeline

The canonical source-input tables under `data/processed/` still rebuild from pinned
downloads:

```console
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe -m scripts.fetch
.venv/Scripts/python.exe -m scripts.build
.venv/Scripts/python.exe -m scripts.validate
.venv/Scripts/python.exe -m scripts.reproduce
.venv/Scripts/python.exe -m scripts.coverage
```

On macOS/Linux use `.venv/bin/python`. [The reproduction guide](docs/reproducibility.md)
covers source comparisons, tests and the Git security audit. Do not read historical
code templates as calibrated existing-stock buildings. Residential configurations are
public modeled-input fixtures, not population representatives.

Layout:

| Path | Holds |
| --- | --- |
| `schemas/` | contracts |
| `sources/` | pinned retrieval and selection |
| `scripts/` | reproducible tooling |
| `atlas_schedules/` | the schedule generator |
| `tests/` | validation regressions |
| `data/raw/` | immutable local downloads |
| `data/processed/` | canonical source tables |
| `data/program-inputs/`, `data/system-inputs/`, `data/reconciliation/` | release inputs |
| `data/atlas-releases/` | the release |

## Licence

Original code is licensed under the MIT License. Original data and documentation,
including the release folders, are licensed under CC BY 4.0; attribute as "Archetype
Atlas, Energy-Atlas" with the release number (ADR 0048). Extracted upstream data
retains its original terms and notices. See `LICENSE`, `sources/licenses/` and each
release's `notices/`.
