# Build and verify the current catalogue

Local implementation branch: `feature/dto-json-v2`. No push, hosted workflow or
deployment is part of this change. Canonical research releases remain immutable.

## Reproduce locally

Python 3.12+ and Node 24 are the site CI baseline. Substitute `.venv/bin/python`
on Linux/macOS. Install the pinned site/browser dependencies and Chromium first.

```powershell
.venv/Scripts/python.exe -m pip install -r requirements-site.txt -r requirements-browser.txt
.venv/Scripts/python.exe -m playwright install chromium
.venv/Scripts/python.exe -m scripts.site
.venv/Scripts/python.exe -m mkdocs build --strict
.venv/Scripts/python.exe -m scripts.site_check
node --test tests/*.test.js
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe -m scripts.site_smoke --screenshots build/screenshots
.venv/Scripts/python.exe -m scripts.site_smoke --serve
```

Preview: <http://127.0.0.1:8765/archetype-atlas/>. Generation consumes verified
`data/definition-releases/v0.1.1` by default; `--definitions PATH` selects an
explicit compatible bundle. `--output PATH` selects a generated build directory.
An existing nonempty output must be marked by `site-manifest.json`.

Fresh checkouts retrieve the source locks before reproduction:

```console
python -m scripts.fetch
python -m scripts.fetch --lock sources/schedule-evidence-lock.json
python -m scripts.fetch --lock sources/water-evidence-lock.json
python -m scripts.fetch --lock sources/completion-evidence-lock.json
python -m scripts.fetch --lock sources/definition-evidence-lock.json
python -m scripts.definition_release --verify
python -m scripts.definition_release --reproduce
```

## Active output

The catalogue has two family gates and three object kinds. Programs, constructions
and HVAC systems link to designated schedules, materials, components and evidence.
Every object has lazy, bounded, checksum-verified JSON inspection and copying.
Programs offer raw or default-filled self-contained DTOs under the
[fixed connector contract](program-json-v2-contract.md). Other library objects
retain explicit unknowns; program defaults do not manufacture HVAC performance.

Schedules show unique daily step profiles, an annual day × hour heatmap, exact
tables and selected-day inspection. Rules use an explicit preview year and holiday
overrides; annual realizations retain their recorded year and cannot be remapped.
Unknown raw coverage remains a gap. Plotly cartesian 3.1.0 is served locally from
checksum-locked assets with its MIT notice.

The active generator starts a fresh tree. It does not import old curated pages,
release catalogues, downloads, generator/resolution interfaces, v1 delivery or
historical snapshots. No redirects or archive compatibility pages are emitted.
Current v2 finder delivery is generated afresh. Repository research tooling and
frozen input releases remain available for scientific verification.

## Implementation and checks

- `scripts/active_site.py`: fresh active build, called by `python -m scripts.site`.
- `scripts/object_site.py`: object pages and content-addressed JSON resources.
- `scripts/program_json.py`, `scripts/schedule_json.py`: program DTO conversion.
- `website/assets/object.js`: verified disclosure and accessible copy choices.
- `website/assets/schedule_core.js`, `schedule.js`: calendar semantics and plots.
- `website/assets.lock.json`: asset version, size and SHA-256 locks.
- `website/assets/site.css`, `fonts.css`, `fonts/`, `theme.js`, `website/overrides/`:
  the EnergyAtlas family UI of `design/ui-design-spec.md`, with self-hosted OFL fonts.
- `scripts/site_check.py`: links, fragments, assets, retirement, complete program
  exports and the 1,000,000,000-byte publication ceiling.
- `scripts/active_smoke.py`: Chromium gates, search, filters, copying, plots,
  mobile layout and no-JS catalogue fallback.
- `build/site-docs/`, `build/site/`: ignored generated documents and HTML.

Energy pages use a compact document shell. Evidence/coverage records use compact
HTML pages with the same JSON controls. Search indexes energy-object titles and
guide text without duplicating full provenance. JSON resources are limited to
16 MB decoded; both compressed and decoded sizes are checked before use.

The Pages workflow definition builds this current catalogue and no longer restores
historical query snapshots. Its existing deployment gate remains unchanged.
This branch has not run or deployed that workflow. Original work remains unlicensed
by user choice; upstream and dependency notices remain applicable.
