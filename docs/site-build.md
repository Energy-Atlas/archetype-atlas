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

Raw source downloads are not needed to build the site. Its release loader checks
the frozen contracts and manifests. The full scientific unittest suite does
require the atlas' locked raw-source retrieval; run scripts.fetch first in a
fresh checkout.

The snapshot ZIP retains every frozen file byte-for-byte, including Markdown,
manifest and notices. JSON tables also have direct downloads and generated CSV.
CSV nulls are literal null; source strings such as None remain strings.
Nested values are JSON text. CSV is an inspection export, not a schema substitute.

Schedule controls inspect a month/day and an explicitly chosen day type, using
the leap-year date picker solely for date validation. They are not an annual
calendar. Step curves, matched-rule evidence, exact tables, CSV and PNG export
are available. Thermostat overlaps are reported without altering source values.
An overlay does not change canonical program assignments.

## GitHub Pages

.github/workflows/catalogue-site.yml builds on feature-branch pushes and pull
requests. It verifies releases, Python presentation tests, browser/Python schedule
parity, a strict MkDocs build, all links and browser interactions. It uploads the
tested static artifact and verification screenshots.

Only a push to the designated publisher branch feat/catalogue-site or the
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
