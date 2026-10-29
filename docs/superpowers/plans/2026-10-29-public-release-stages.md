# Plan: public release stages (2026-10-29)

Status: accepted for unsupervised running (owner, 2026-10-29). Stages A are this
repository; B are BEMGen; C are the zoning-LOD study. Each stage is one pull request
unless noted.

| Stage | Repository | Scope | Done when |
| --- | --- | --- | --- |
| A1 | archetype-atlas | CI workload pass 2 (schedules shard split, sampled catalogue smoke on pull requests, package job) and the `atlas-schedules` wheel: `pyproject.toml`, console script, tag-triggered release workflow, ADR 0049, docs | PR merged; wheel installs in a clean venv and runs the quick start |
| A2 | archetype-atlas | Release 2.1.0, a delta on 2.0.0 (ADR 0046): the open-licence `LICENSE`, the generator 3.0.0 apartment-unit recipes in `generator.json`, manifest fields naming the generator version and wheel; status `released`; site shows 2.1.0 | Tags `v2.1.0` and `atlas-schedules-v3.0.0`, GitHub releases with notes and the wheel attached, `pip install` from the release URL verified |
| A3 | archetype-atlas | Site page for `lod-recommendations.json` (per program × climate zone × vintage; schema v1 in BEMGen `scripts/lod-study/schemas/`) | Page built from the file, checked by `site_check` and the site tests |
| B1 | BEMGen | Coplanar merge | Merged with its tests |
| B2 | BEMGen | Schedule Draw component (reads `atlas-schedules` bundles) | Component in the toolbar with an example |
| B3 | BEMGen | Release 1.6.0 | Tag, release files, docs site |
| C1 | LOD study | R3 main runs | Results committed |
| C2 | LOD study | R4 IWHT/FHT | Results committed |
| C3 | LOD study | R5 serial timing | Results committed |
| C4 | LOD study | R6 report | Report drafted |

Dependencies: A1 → A2 → A3; A1 → B2 (the wheel); B1 → B2 → B3; A2 and B3 → C1 → C2 →
C3 → C4; A3 reads C4's `lod-recommendations.json`.
