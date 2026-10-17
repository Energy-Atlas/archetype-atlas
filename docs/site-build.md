# Build and verify the current catalogue

The catalogue is built, verified and deployed by `.github/workflows/catalogue-site.yml`
(see [Release gate](#release-gate)). Canonical research releases remain immutable.

## Reproduce locally

Python 3.12+ and Node 24 are the site CI baseline. Substitute `.venv/bin/python`
on Linux/macOS. Install the pinned site/browser dependencies and Chromium first.

```powershell
.venv/Scripts/python.exe -m pip install -r requirements-site.txt -r requirements-browser.txt
.venv/Scripts/python.exe -m playwright install chromium
.venv/Scripts/python.exe -m scripts.site
.venv/Scripts/python.exe -m mkdocs build --strict
.venv/Scripts/python.exe -m scripts.site_check --require-construction
node --test tests/*.test.js
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe -m scripts.site_smoke --screenshots build/screenshots
.venv/Scripts/python.exe -m scripts.construction_site_smoke --screenshots build/screenshots/construction
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

### Local UI-only display preview

To review card styling without generating the research catalogue, run:

```console
python -m scripts.card_preview
python -m scripts.card_preview --serve
```

Open <http://127.0.0.1:8766/archetype-atlas/>. The strict MkDocs build uses
the current landing and catalogue overview generators, shared theme and hooks.
Finders are explicitly empty and guide pages are labelled typography specimens.
Only UI assets and preview pages are written under `build/card-preview/`;
no record pages, research packets, release bundles or deployment artifacts are
generated. Re-run the first command after editing styles or templates.
This display build does not replace the full publication checks below.

The catalogue has two family gates and three object kinds. Programs, constructions
and HVAC systems link to designated schedules, materials, components and evidence.
Every object has lazy, bounded, checksum-verified JSON inspection and copying.
Programs offer raw or default-filled self-contained DTOs under the
[v3 connector contract](program-json-v3-contract.md). Other library objects
retain explicit unknowns; program defaults do not manufacture HVAC performance.

Constructions provide separate detailed schema 2.1.0 and additive unified schema
1.2.0 exports for all 177 current sets / 3,320 supported contexts. Both named copy
buttons act directly without a chooser; preview mode does not change their
representation. Source-record copying is absent on construction definition pages.
Both include the same source mass-accounting contract 1.0.0.
See [construction release notes](release-notes-construction-v2.2.0.md) and
[shared mass release notes](release-notes-construction-mass-v1.0.0.md).

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
- `scripts/program_json_v3.py`, `scripts/schedule_json.py`: current program DTO conversion.
- `scripts/program_completeness.py`: reproduce the complete v3 export receipt.
- `website/assets/object.js`: verified disclosure and accessible copy choices.
- `website/assets/schedule_core.js`, `schedule.js`: calendar semantics and plots.
- `website/assets.lock.json`: asset version, size and SHA-256 locks.
- `website/assets/site.css`, `fonts.css`, `fonts/`, `theme.js`, `website/overrides/`:
  the EnergyAtlas family UI of `design/ui-design-spec.md`, with self-hosted OFL fonts.
- `scripts/site_check.py`: links, fragments, assets, retirement, complete program
  exports and the 1,000,000,000-byte publication ceiling.
- `scripts/active_smoke.py`: Chromium gates, search, filters, copying, plots,
  mobile layout and no-JS catalogue fallback.
- `scripts/construction_site_smoke.py`: separate detailed/unified preview and
  clipboard parity for Medium Office, Warehouse and residential examples, lazy
  loading, unsupported contexts and desktop/mobile themes.
- `build/site-docs/`, `build/site/`: ignored generated documents and HTML.

Energy pages use a compact document shell. Evidence/coverage records use compact
HTML pages with the same JSON controls. Search indexes energy-object titles and
guide text without duplicating full provenance. JSON resources are limited to
16 MB decoded; both compressed and decoded sizes are checked before use.

The Pages workflow definition builds this current catalogue and no longer restores
historical query snapshots. Original work remains unlicensed by user choice;
upstream and dependency notices remain applicable.

## Release gate

Every run of the catalogue workflow's build job verifies the presentation
contracts (delivery, query, program JSON, active-site and browser tests, Node
tests), generates the catalogue, builds it with `mkdocs build --strict`,
and passes `site_check` and the Chromium smoke test before it uploads the Pages
artifact. The same pipeline calls the reusable `validate.yml` research matrix.
Construction presentation tests run in the build job. Publication explicitly
requires `construction-site.json` through `site_check --require-construction`;
the default checker still permits small construction-free research fixtures.
Both construction copy representations are browser-checked before artifact upload.
Deployment requires both the build and research validation to succeed for the
same commit. It runs only on `main`, automatically for pushes or after a manual
dispatch with `deploy` set. The production environment also permits `main` only.
See [branch and publication policy](branch-policy.md).

Automatic runs cover every pull request targeting `main` and every push to
`main`. There are no path filters on these required checks, avoiding missing
checks on documentation changes and stale filters when a schema version changes.
Working-branch pushes do not start CI; use `gh workflow run catalogue-site.yml
--ref BRANCH` for a manual validation run. Its default `deploy=false` does not
publish; even `deploy=true` cannot publish from a working branch.

The frozen-release checks (evidence fetches, definition release verification
and byte reproduction, atlas, resolution, completion, water and water-reporting
release verification, their tests, and the historical research-site tests of
`test_site`, which read the fetched sources; about 11 minutes) run only when needed.
They are skipped only when every path changed since the previous pushed commit,
or since a pull request's base, is presentation-only:

- `website/`, `design/`, `docs/`, `mkdocs.yml`, and the top-level Markdown files;
- the site scripts `active_site`, `active_smoke`, `object_site`, `definition_site`,
  `site_check`, `site_smoke`, `site_assets`;
- the site tests `test_active_site`, `test_object_browser`, `test_html_delivery`,
  `test_site_delivery`, `test_search_index`, `test_definition_site`, and the Node
  tests.

Any other change (data, schemas, sources, requirements, other scripts or tests,
or the workflow itself), a new branch whose comparison with the default branch
cannot be made, and every manual dispatch run the full build-side checks.
Independently of that optimization, the reusable `validate.yml` research matrix
fetches the sources, verifies every frozen release, reproduces the v3 program
completeness receipt and runs the full Python suite on every pipeline run.
Artifact generation remains part of site CI pending roadmap item 5's discussion.

The research matrix additionally reproduces frozen construction base v2.0.0,
applicability v2.1.0, distribution v2.2.0 and additive unified release 1.1.0 with
their existing `--check` commands. Shared mass release 1.0.0 and its seven paired
examples are reproduced with `construction_mass_release --check --examples`.
Supporting profile 1.1.0 files and declared input hashes are verified by `construction_weighting.load_profiles()`; this does
not require the ignored native-recovery cache. Reproducing profiles with
`construction_weighting --check` is a separate maintenance check requiring the
previously recovered `build/equivalent-work/commercial-weights.json` and pinned
source/runtime retrieval for re-execution. These publication checks run on both
required platforms. No native source recovery or annual construction simulation
is introduced. Lighter artifact delivery remains deferred until BEMGen testing
is accepted; this change does not decouple generation from CI.

The immutable v2 base generator enumerates source license notices in filesystem
order when serializing its manifest. Use `python -m scripts.construction_base_reproduce
--quiet` for cross-platform reproduction. This check-only adapter supplies the
original lexical notice order, then runs the original generator with every
validation and exact byte comparison intact. It changes neither historical
generator hashes nor frozen artifacts; notice additions, removals or changed
bytes still fail reproduction.

Unified-fit and shared-mass byte reproduction uses the original producer,
**Windows x64 / CPython 3.14.7**. Python 3.12 changed floating-point
summation and Python 3.14 changed complex summation
([Python's documented changes](https://docs.python.org/3.14/library/functions.html#sum)). Earlier runtimes can produce
last-bit differences in full-precision error metrics; because recipe IDs hash
those metrics, the catalogue bytes can differ even when material layers match.
CI also confirmed a platform-math difference under Linux with the same Python
version. The protected Windows research job reproduces every unified and shared
mass byte under the pinned producer. Both required Linux/Python 3.11 and
Windows/Python 3.14 jobs run `python -m scripts.construction_delivery_validate`
over all 3,320 frozen pairs (6,640 self-contained documents): checksums, provenance
inputs, schemas, source equality, physical conservation and shared mass accounting.
Both retain the full consumer-test suite and all other research checks. Every
original producer byte comparison remains mandatory. Frozen data, historical
generator sources, reported errors and recipe IDs are preserved. Consumers do
not need to regenerate fit metrics or their hashed IDs when loading a release.
