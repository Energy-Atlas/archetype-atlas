# Build and verify the catalogue

The implementation is on feat/catalogue-site, based on the complete v0.2.0
release. Presentation code is separate from canonical research data.

## Reproduce locally

Python 3.12+ and Node 24 are the CI baseline. Commands below use Windows paths;
on Linux/macOS substitute .venv/bin/python.

```powershell
.venv/Scripts/python.exe -m pip install -r requirements-site.txt -r requirements-browser.txt
.venv/Scripts/python.exe -m playwright install chromium
.venv/Scripts/python.exe -m scripts.site
.venv/Scripts/python.exe -m mkdocs build --strict
.venv/Scripts/python.exe -m scripts.site_check
node --test tests/site_core.test.js tests/site_parity.test.js
.venv/Scripts/python.exe -m scripts.site_smoke --screenshots build/screenshots
.venv/Scripts/python.exe -m scripts.site_smoke --serve
```

The preview is at <http://127.0.0.1:8765/archetype-atlas/>.
Alternatively use MkDocs' development server after generation.

The generator defaults to both frozen releases, v0.1.0 and v0.2.0.
Repeat --release PATH to select explicit snapshots. Semantic version order
determines the home-page release. Every release keeps its own catalogue, record
URLs, browser payloads and downloads. Updating the latest sidebar link is an
explicit mkdocs.yml change when a new data release is published.

For the representative pilot:

```powershell
.venv/Scripts/python.exe -m scripts.site --pilot --release data/releases/v0.2.0
.venv/Scripts/python.exe -m mkdocs build --strict
.venv/Scripts/python.exe -m scripts.site_smoke
```

Regenerate without --pilot before release. Pilot status is displayed on the
home page and recorded in site-manifest.json.

## Files and boundaries

- website/content/: reader guides, edited by hand.
- website/assets/: filters, schedule inspection, plots and styling.
- website/assets.lock.json: Plotly assets pinned to version, size and SHA-256.
- scripts/site.py: manifest verification and deterministic document generation.
- scripts/site_assets.py: locked retrieval, rejecting corrupt cached assets.
- scripts/site_check.py: all generated internal URLs, fragments and assets.
- scripts/site_smoke.py: browser tests and project-subpath preview server.
- build/site-docs/ and build/site/: ignored generated documents and HTML.

The release loader checks frozen contracts, manifests and source reproduction.
A fresh checkout must retrieve the base, schedule, water and completion locks
before validation or site generation:

```powershell
python -m scripts.fetch
python -m scripts.fetch --lock sources/schedule-evidence-lock.json
python -m scripts.fetch --lock sources/water-evidence-lock.json
python -m scripts.fetch --lock sources/completion-evidence-lock.json
python -m scripts.commercial_completion --verify
python -m scripts.resolve --verify
python -m scripts.water_reporting --verify
```

The snapshot ZIP retains every frozen file byte-for-byte, including Markdown,
manifest and notices. JSON tables also have direct downloads and generated CSV.
CSV nulls are literal null; source strings such as None remain strings.
Nested values are JSON text. CSV is an inspection export, not a schema substitute.

The selected default supplement is v0.4.0, paired with commercial-completion
v0.1.0. New supplement canonical tables are supplied inside their complete ZIP;
large tables are not duplicated as direct files. Historical direct URLs and
byte-identical profiles are retained. The commercial browser `catalogue.json`
is compact presentation JSON; use its ZIP for exact manifest hashes. Fixture
pages provide source and normalized plots and attach only supported beneficiaries
to existing programs. Excluded end uses are removed from active presentations;
immutable upstream and historical snapshots retain their provenance.

The separately frozen water-reporting v0.1.0 variant adds attributed-volume
plots and service links to every active program. Its canonical download and
snapshot are under `water-reporting/v0.1.0/`; original local unknowns and source
curves remain visible. `schedule-coverage.json` reports source-only gaps and
operational variant availability separately. Catalogue names come from the
controlled `scripts/catalogue_names.py` vocabulary; canonical source codes and
old browsing aliases remain available.

Schedule controls inspect a month/day and an explicitly chosen day type, using
the leap-year date picker solely for date validation. They are not an annual
calendar. Step curves, matched-rule evidence, exact tables, CSV and PNG export
are available. Thermostat overlaps are reported without altering source values.
An overlay does not change canonical program assignments.

## Optional source-phase control reproduction

Use the locked Windows OpenStudio executable and source archive from
`sources/commercial-runtime-lock.json`:

```powershell
python -m scripts.commercial_completion --inspect-controls --runtime-cache build/cc --openstudio build/runtime/openstudio-windows/OpenStudio-3.10.0+86d7e215a1-Windows/bin/openstudio.exe
```

The short cache path avoids Windows MAX_PATH failures from nested upstream
standards filenames. In a deeply nested checkout, select a shorter absolute
`--runtime-cache` location. Archive/file checksums and the eight-case receipt
remain required. Frozen recipe snapshots preserve their original code; this
current CLI adds cache-path configuration without altering canonical data.

## GitHub Pages delivery

.github/workflows/catalogue-site.yml builds on feature-branch pushes and pull
requests. It verifies releases, Python presentation tests, browser/Python schedule
parity, a strict MkDocs build, all links and browser interactions. It uploads the
tested static artifact and verification screenshots.

Only a push to the designated publisher branches feat/catalogue-site or
feat/schedule-resolution, or the
repository's actual default branch, or a workflow dispatch with deploy=true,
deploys that artifact. Other feature branches build without publication.
The publisher branch permits autonomous initial hosting without merging the
research branches. The site uses the project prefix /archetype-atlas/.
The workflow has read-only contents access; only its deployment job receives
Pages write and OIDC permissions. Actions are pinned to full commit revisions.

GitHub Pages uses GitHub Actions as its build source. Initial activation uses
existing repository-administration authorization outside the workflow; the
workflow does not grant itself repository-administration permissions.
This implementation leaves research branches unmerged.

## Dependencies and licensing

Site and browser Python dependencies are pinned separately. Plotly is retrieved
only during generation; runtime scripts and plots use local assets and its MIT
notice is distributed. System fonts avoid a remote font dependency.
MkDocs and Material retain their package license notices. Original site code
and documentation remain unlicensed under the repository's existing notice.
# Publication size

The HTML delivery hook removes template indentation after newlines outside
literal `pre`, `code`, `textarea`, `script`, `style`, SVG and MathML regions.
Links, attributes, source values and literal text remain intact. This reduces
repeated theme formatting across the catalogue while keeping the built artifact
below the selected 1,000,000,000-byte publication ceiling. The strict build,
whole-site link check and browser suite run against that delivered HTML.

The global documentation search indexes record titles and the full text of
guides. The catalogue's own
filters/query retain the full record metadata used by its axes. This avoids
duplicating lengthy provenance and source-code excerpts in a second full-text
index. Generated catalogue JSON uses compact serialization without changing
values; frozen download files and complete snapshots retain their exact bytes.
Current identical residential profile downloads reuse historical URLs, with an
explicit download map; complete snapshot ZIPs retain each manifest inventory.


## Definition catalogue and independent delivery majors

`python -m scripts.site` consumes verified `data/definition-releases/v0.1.1`
by default. The Python generator's optional `definition_release` argument keeps
legacy fixture builds available. The new catalogue exposes exactly two entry
gates and three kinds. Metadata drives facets; evidence, schedules and components
are verified and decompressed only when requested. No backend is required.

Before publication restore both majors independently:

```console
python -m scripts.query_history --restore https://energy-atlas.github.io/archetype-atlas/delivery/v1/ --target build/query-history
python -m scripts.query_history --major 2 --restore https://energy-atlas.github.io/archetype-atlas/delivery/v2/ --target build/query-history-v2
```

Only the first v2 publication may use the explicit workflow input
`bootstrap_definition_delivery`. Missing established history blocks publication;
invalid archives never fall back to a bootstrap. The `deploy` workflow dispatch
publishes the verified feature-branch artifact without merging main. Both majors
retain previously advertised manifests/resources, with publisher-only archives.

Archived detail pages and new definition pages use a compact document shell:
original article content, literal data, charts and verified resource controls are
retained, with Home/Catalogue/Downloads links. Repeated global navigation markup
is omitted from these pages to meet the unchanged 1 GB publication ceiling.
Top-level catalogue and guide pages retain the full navigation/search shell.
Frozen definition files have Git text normalization disabled so their exact
manifest hashes survive Windows/Linux checkout.
