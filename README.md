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
are recorded under `docs/` and `sources/`; the catalogue site's
[coverage page](https://energy-atlas.github.io/archetype-atlas/coverage/) counts what the
current release covers, generated from it.

## Release 2.5.0

**Atlas release 2.5.0** (`data/atlas-releases/v2.5.0`, status `released`) is a delta on 2.4.0
([ADR 0064](docs/adr/0064-release-2-5-0.md),
[release notes](docs/release-notes-atlas-v2.5.0.md)). It decides each setpoint side from the source
equipment ([ADR 0063](docs/adr/0063-conditioning-sides-and-per-side-mixes.md)):
- a 90.1 or DOE Ref source program whose prototype HVAC map serves no heating or no cooling has that
  setpoint side as an explicit null, with `parameters.conditioning` and evidence citing the systems
  and the replaced schedule (72 programs: the warehouse bulk storage, the stand-alone retail entry
  and the small-hotel stairs and mechanical room are heated only; the 90.1 small-hotel storage and
  laundry, the 90.1 midrise corridors, the DOE Ref outpatient support rooms and the courthouse
  parking are unconditioned; the data centres have no heating side);
- every mix averages each setpoint side over the members that have it and records
  `composition.setpoint_coverage` (69 mixes have a coverage below 1; the 90.1-2019 warehouse
  storage mix cools at 26.7 degC with cooling coverage 0.303, not at 42.9 degC);
- the ID moves that follow (518 programs: all 446 mixes and 72 source programs), mapped in
  `id-map-2.5.0.json`.

Its exports follow Program JSON 6.2.0 (ADR 0063: the null status `not_conditioned` and
`controls.setpoint_coverage`); the construction and building-services contracts are unchanged,
naming `atlas-release-2.5.0`. `atlas-schedules` 4.1.2 bundles it. The `v2.5.0` GitHub release
carries `atlas-release-2.5.0.zip` (the `v2.0.0/` to `v2.5.0/` folders),
`atlas-release-2.5.0.manifest.json`, `id-map-2.5.0.json`, the `atlas-schedules` 4.1.2 wheel and
`SHA256SUMS.txt`.

```console
python -m scripts.atlas_delta --verify                    # the delta against its manifest and base
python -m scripts.atlas_delta --check                     # rebuild 2.5.0 from its inputs; every block assembles
python -m scripts.conditioning_sides --check              # rebuild the conditioning-side input from the pinned sources
python -m scripts.atlas_exports --program ID --version filled    # exports 2.5.0 by default
```

**Atlas release 2.4.0** (`data/atlas-releases/v2.4.0`, status `released`) is a delta on 2.3.0
([ADR 0062](docs/adr/0062-release-2-4-0.md),
[release notes](docs/release-notes-atlas-v2.4.0.md)). It carries the PNNL prototype corrections of
[ADR 0060](docs/adr/0060-release-2-4-0-pnnl-prototype-corrections.md):
- `lighting_controls.unoccupied_lighting_cap` on every known lighting-controls block: PNNL's
  90.1-2019 per-zone EMS rule (occupant count 0 and lighting at least 0.02 W/ft², lights set to
  0.02 W/ft²) on 19 programs, and an explicit null with its reason on the 1,875 others;
- the PNNL lighting power of the 11 90.1 whole-building office programs (90.1-2007, 2013, 2019);
  the other PNNL against openstudio-standards differences are listed for the owner in
  [`docs/reviews/lighting-power-pnnl-vs-90-1.md`](docs/reviews/lighting-power-pnnl-vs-90-1.md);
- the PNNL 90.1 elevators and kitchen reach-ins as 84 building services of 36 folders;
- the ID moves that follow (2,301 programs, no construction set), mapped in `id-map-2.4.0.json`.

Its exports follow Program JSON 6.1.0 ([ADR 0061](docs/adr/0061-program-json-6-1-0-unoccupied-lighting-cap.md));
the construction and building-services contracts are 2.3.0's, naming `atlas-release-2.4.0`.
`atlas-schedules` 4.1.1 bundles it. The `v2.4.0` GitHub release carries `atlas-release-2.4.0.zip`
(the `v2.0.0/` to `v2.4.0/` folders), `atlas-release-2.4.0.manifest.json`, `id-map-2.4.0.json` and
`SHA256SUMS.txt`.

**Atlas release 2.3.0** (`data/atlas-releases/v2.3.0`, status `released`) is a delta on 2.2.0
([ADR 0059](docs/adr/0059-release-2-3-0.md),
[release notes](docs/release-notes-atlas-v2.3.0.md)). It carries:
- the record corrections of [ADR 0053](docs/adr/0053-release-2-3-0-data-corrections.md): the DOE Ref
  unified internal mass, the 90.1 small-hotel elevator from PNNL, stored accepted absences and
  distinguishing names;
- the ID moves that follow from them (1,550 programs and 12 construction sets), mapped in
  `id-map-2.3.0.json`;
- the generation blocks of the 84 IECC commercial and 15 detailed office folders
  ([ADR 0055](docs/adr/0055-generation-for-iecc-and-detailed-offices.md));
- the MIT `LICENSE` and the CC BY 4.0 `LICENSE-DATA`.

Its exports follow Program JSON 6.0.0, detailed constructions 5.0.0, unified constructions 4.0.0,
source-model constructions 2.0.0 and building services 1.0.1
([ADR 0054](docs/adr/0054-release-2-3-0-export-contracts.md)), naming `atlas-release-2.3.0`.
`atlas-schedules` 4.1.0 reads it. The `v2.3.0` GitHub release carries `atlas-release-2.3.0.zip`
(the `v2.0.0/` to `v2.3.0/` folders) and `SHA256SUMS.txt`.

```console
python -m scripts.atlas_delta --check --release 2.3.0     # rebuild 2.3.0 from its inputs; every block assembles
```

**Atlas release 2.2.0** (`data/atlas-releases/v2.2.0`, status `released`) is a delta on
2.1.0, itself a delta on the 2.0.0 snapshot
([ADR 0051](docs/adr/0051-generation-parameters-in-the-release.md),
[release notes](docs/release-notes-atlas-v2.2.0.md)): it publishes the schedule
generator's parameters with the programs (each generated folder's `generation.json` and
`definition-map.json`) and removes the folders' `generator.json`. No program, schedule,
service or construction value changes and every ID is 2.0.0's; Program JSON 5.4.0 exports
name `atlas-release-2.2.0`. The `v2.2.0` GitHub release carries `atlas-release-2.2.0.zip`
(the `v2.0.0/`, `v2.1.0/` and `v2.2.0/` folders) and `SHA256SUMS.txt`.

```console
python -m scripts.atlas_delta --check --release 2.2.0     # rebuild 2.2.0 around its files; every block assembles
sha256sum -c SHA256SUMS.txt                               # a downloaded release asset
```

**Atlas release 2.1.0** (`data/atlas-releases/v2.1.0`) is the first delta
([ADR 0046 section 12](docs/adr/0046-release-2-0-0.md),
[release notes](docs/release-notes-atlas-v2.1.0.md)): the open-licence `LICENSE` and the
generator 3.0.0 apartment-unit recipes in the eight apartment folders' `generator.json`.

**Atlas release 2.0.0** (`data/atlas-releases/v2.0.0`, status `released`) is the base
([ADR 0046](docs/adr/0046-release-2-0-0.md),
[release notes](docs/release-notes-atlas-v2.0.0.md)). It is a full snapshot: open
the folder alone, with no base release to resolve. It holds:
- the commercial programs, mixes, services, systems and water of the 90.1, DOE Ref
  and IECC templates, with lighting controls;
- the residential tree (ResStock dwellings, IECC residential and manufactured-housing
  prototypes);
- detailed and unified construction sets;
- the generator recipes of the 90.1 and DOE Ref programs in each folder's
  `generator.json` (replaced by 2.2.0's `generation.json` blocks);
- the PNNL prototype constructions of the 90.1 templates where they differ from
  openstudio-standards, as `alternates` (detailed constructions 4.3.0);
- the evidence tree and upstream notices.

```console
python -m scripts.atlas_snapshot --verify                 # every file against the manifest
python -m scripts.release_editor --check                  # IDs follow their rules (id-map.json lists the changes)
python -m scripts.atlas_exports --release 2.0.0 --program ID --version filled
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
- one content-addressed JSON store holding every source and filled export;
- the geometric LOD study's zoning recommendations per prototype, climate zone,
  vintage and orientation, from `data/lod-recommendations/v1`
  ([ADR 0050](docs/adr/0050-zoning-recommendations-site.md)).

Pages read without JavaScript; `?version=` and context switches narrow them. The
[site build guide](docs/site-build.md) gives the local build, checks and preview.

## Schedule generator

The offline [schedule generator](docs/schedule-generator.md) (`atlas_schedules`)
turns programmes, extents and a seed into 8,760-hour schedules, with each annual
load target bound to its generated shape. It is a readable port of ComStock /
openstudio-standards 0.8.6 hours-of-operation sampling and of OpenStudio-HPXML's
ResStock occupant model ([ADR 0035](docs/adr/0035-readable-generator-restructure.md)).

Generator 4.1.2 assembles its recipes from an atlas data release
([ADR 0051](docs/adr/0051-generation-parameters-in-the-release.md)): requests name
programs by release ID with a `values` view. Install it as the `atlas-schedules` package
from the wheel attached to its GitHub release
([ADR 0049](docs/adr/0049-atlas-schedules-packaging.md); Python 3.11+, numpy and
jsonschema; not on PyPI), and verify the download:

```console
curl -LO https://github.com/Energy-Atlas/archetype-atlas/releases/download/atlas-schedules-v4.1.2/atlas_schedules-4.1.2-py3-none-any.whl
curl -LO https://github.com/Energy-Atlas/archetype-atlas/releases/download/atlas-schedules-v4.1.2/SHA256SUMS.txt
sha256sum -c SHA256SUMS.txt --ignore-missing
pip install atlas_schedules-4.1.2-py3-none-any.whl
atlas-schedules --version                          # the generator and the release it reads
atlas-schedules request.json -o bundle.json
atlas-schedules translate old-request.json         # a 3.0.0 request's definition IDs as release IDs
```

The wheel bundles the generator view of release 2.5.0 (4.1.2 is 4.1.0's code with that view,
[ADR 0064](docs/adr/0064-release-2-5-0.md)); `ATLAS_RELEASES` or
`--release-dir` reads a release on disk instead. From a checkout, `python -m pip
install -r requirements.txt` and `python -m atlas_schedules request.json` run the
same code against `data/atlas-releases`; `python -m scripts.build_generator_view`
then `python -m build` (pinned in `requirements-dev.txt`) build the wheel.
- **Generation blocks:** each generated folder's `generation.json`; the DOE Ref and
  apartment blocks were written for release 2.2.0 from the release
  (`python -m scripts.build_reference_recipes`, `scripts.build_apartment_units`), and the
  IECC commercial and detailed office blocks of release 2.3.0 are derived by
  `python -m scripts.build_zone_recipes` ([ADR 0055](docs/adr/0055-generation-for-iecc-and-detailed-offices.md)).
- **Schemas:** `generation.json`, the bundle and the release records have JSON Schemas,
  versioned by [docs/schema-versioning.md](docs/schema-versioning.md)
  ([ADR 0056](docs/adr/0056-release-record-schemas-and-versioning.md);
  `python -m scripts.release_schemas`, `scripts.schema_revisions --check`).
- **Validation:** native OpenStudio / Ruby answer keys in `tests/answer_keys/` check
  it to 1e-6; a generator 3.0.0 answer key checks the assembled recipes reproduce its
  bundles.
- **Catalogue smoke:** `python -m scripts.smoke_catalogue` generates every programme
  view and service of the release.

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

Original work in this repository is licensed in two parts (ADR 0048; the files split at
release 2.3.0, ADR 0059):

- **Code**, under the MIT License in [`LICENSE`](LICENSE): the Python packages and
  scripts, tests, JSON schemas, and the site and build tooling.
- **Data and documentation**, under Creative Commons Attribution 4.0 International
  (CC BY 4.0) in [`LICENSE-DATA`](LICENSE-DATA): the release folders under `data/`, the
  program, system and reconciliation inputs, `docs/`, `website/content/` and the
  generated site. Attribute as "Archetype Atlas, Energy-Atlas" with the release number.

These grants also cover the releases published before the split, including 2.0.0,
whose packaged `LICENSE` predates them, and 2.1.0 and 2.2.0, whose packaged `LICENSE`
states both parts in one file.

Third-party material is excluded and keeps its upstream licence: extracted or derived
DOE, PNNL, OpenStudio, ComStock, ResStock, ACS, ATUS, EnergyPlus and weather data, and
ported upstream code. See `sources/licenses/`, the source manifests and each release's
`notices/` for terms and attribution. This atlas is not an official OpenStudio(R), DOE,
PNNL, ComStock or ResStock product.

To cite the atlas, use `CITATION.cff` (GitHub's *Cite this repository*) and name the
release you used.
