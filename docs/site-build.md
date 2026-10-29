# Build and verify the current catalogue

The catalogue is built, verified and deployed by `.github/workflows/catalogue-site.yml`
(see [Release gate](#release-gate)). It shows the **latest release** under
`data/atlas-releases` ([ADR 0043](adr/0043-suite-based-site.md), after
[ADR 0036](adr/0036-suite-based-release-storage.md) section 10). Releases remain immutable.

## Reproduce locally

Python 3.12+ and Node 24 are the site CI baseline. Substitute `.venv/bin/python`
on Linux/macOS. Install the pinned site and browser dependencies and Chromium first.

```powershell
.venv/Scripts/python.exe -m pip install -r requirements-site.txt -r requirements-browser.txt
.venv/Scripts/python.exe -m playwright install chromium
.venv/Scripts/python.exe -m scripts.suite_site
.venv/Scripts/python.exe -m mkdocs build --strict
.venv/Scripts/python.exe -m scripts.site_check --require-complete
node --test tests/*.test.js
.venv/Scripts/python.exe -m unittest tests.test_suite_site -v
.venv/Scripts/python.exe -m scripts.site_smoke --screenshots build/screenshots
.venv/Scripts/python.exe -m scripts.site_smoke --serve
```

Preview: <http://127.0.0.1:8765/archetype-atlas/>. `--release 1.4.0` picks a release
other than the newest; `--only REGEX` builds a partial preview of the matching
folders (for example `--only 90-1-2019/medium-office`), which `site_check
--require-complete` refuses to publish. `--output PATH` selects a generated build
directory; an existing nonempty output must be marked by `site-manifest.json`.
`site_smoke --channel chrome` (or `msedge`) uses an installed browser instead of
Playwright's Chromium. Generation exports every program and construction context in
worker processes (`--jobs`, default the CPU count up to 6; each holds the resolved
release, about 2 GB).

## What is generated

`python -m scripts.suite_site` reads one release through
`scripts.atlas_exports.Release` and writes the MkDocs input tree `build/site-docs/`:

| Output | Content |
| --- | --- |
| `catalogue/<family>/<template>/<type>/programs/<name>/` | One page per program (source, department, general, dwelling): every field of the record, fillings in place, the schedules it uses and the evidence it cites, and the source and filled exports. |
| `catalogue/<family>/<template>/<type>/constructions/<name>/` | One page per construction set: its contexts with their exports, the fields shared by every context once, each context's own fields and components, the assemblies and materials it uses. |
| `catalogue/<family>/<template>/<type>/` | One folder page per template × building type: programs, mixes and their members, construction sets, services, systems, components and water-reporting records with their schedules and evidence. |
| `catalogue/<family>/<template>/template-library/` | The template library: assemblies, materials and performance rules. |
| `catalogue/glossary/` | The evidence glossary: rule notes, unresolved reasons, interpretations, transformations, source files. |
| `view/` and `view-index.json` | The viewer for any ID (`view/?id=…`): its page and anchor, or its own JSON. |
| `store/<sha256>.json.gz` | The one content-addressed JSON store: every export, every schedule and the viewer packets. |
| `site-manifest.json` | Release, input digest, counts, and every page and export. |

Page URLs drop the content hash of the record ID, so an edited record keeps its URL;
two records that would share a URL keep their hash. Pages read completely without
JavaScript; `website/assets/suite.js` adds the `?version=` and context switches and
verified copying, `website/assets/view.js` the viewer. Plots are inline SVG drawn at
build time. Search indexes each suite page once, by its name, ID, template, building
type and kind (`website/hooks/search_index.py`).

## Implementation and checks

- `scripts/suite_site.py`: the generator and the input digest.
- `scripts/site_release.py`: the release index the pages need (newest release, folders,
  schedules, library, evidence), over `atlas_exports.Release`.
- `scripts/site_render.py`, `scripts/site_pages.py`: the generic record renderer and the
  page layouts. Record fields the renderer does not know render generically, so a new
  optional block of a later Program JSON minor needs no site change.
- `scripts/site_store.py`: gzip, SHA-256 and descriptors (ADR 0011 transport).
- `scripts/site_check.py`: links and fragments, store checksums and descriptors, a page
  and exports for every program and construction set of the release, retired routes,
  search entries, viewer packets, the input digest and the 1,000,000,000-byte ceiling.
- `scripts/site_smoke.py`: Chromium checks of the version and context switches,
  verified copy and download, annual schedule plots, the viewer, search, the 404 page,
  reading without JavaScript and phone width.
- `tests/test_suite_site.py`, `tests/suite.test.js`: unit tests of the modules above.
- `website/assets/site.css`, `fonts.css`, `fonts/`, `theme.js`, `website/overrides/`:
  the EnergyAtlas family UI of `design/ui-design-spec.md`, with self-hosted OFL fonts.
- `build/site-docs/`, `build/site/`: ignored generated documents and HTML.

The definition-release catalogue (`scripts/active_site.py`, `definition_site`,
`object_site`, `construction_site`, `query_v2` and their browser scripts) was retired
with ADR 0043; it remains in the repository history.

## Release gate

Every run of the catalogue workflow's build job runs the site unit and Node tests,
computes the input digest (`python -m scripts.suite_site --digest`: the release
manifest, the scripts the generator and the MkDocs hooks import, `website/`, `schemas/`,
`mkdocs.yml`, the site requirements and the policy files those scripts read) and restores
`build/site-docs` and the built `build/site` from the Actions cache under that digest, or
generates and builds them with `mkdocs build --strict`. Either way it then passes `site_check --require-complete` (which
also rejects a cached tree whose recorded digest differs from the checkout) and the
Chromium smoke test before it uploads the Pages artifact. The same pipeline calls the
reusable `validate.yml` research jobs. Deployment requires both the build and research
validation to succeed for the same commit. It runs only on `main`, automatically for
pushes or after a manual dispatch with `deploy` set. The production environment also
permits `main` only. See [branch and publication policy](branch-policy.md).

Automatic runs cover every pull request targeting `main`, every push to `main`, and a
weekly run (Monday 06:17 UTC). There are no path filters on the required checks, so a
documentation-only change still reports them. Working-branch pushes do not start CI; use
`gh workflow run catalogue-site.yml --ref BRANCH` for a manual validation run. Its default
`deploy=false` does not publish; even `deploy=true` cannot publish from a working branch.

The reusable `validate.yml` research workflow runs these jobs in parallel:

- `release` (Linux): verifies release 2.0.0 against its checksums and the in-place edits,
  rebuilds the 2.1.0 delta from its pinned inputs (`atlas_delta --check`), checks the
  export schemas, the reconciliation page and the daylighting rules, validates,
  reproduces and compares the source pipeline, and runs the security audit;
- `unit-tests (atlas)`, `unit-tests (schedules-commercial)` and `unit-tests (schedules-rest)`
  (Linux, Python 3.11): the Python suite in three shards (`python -m scripts.ci_tests
  --shard NAME`; the shards partition `unittest discover -s tests`; the two schedules
  shards split `tests/schedules` into the ComStock answer-key modules and the rest, about
  half the time each);
- `schedules` (Linux): generates the packaged catalogue (`smoke_catalogue`): every
  programme and service variant on a push to `main`, weekly and manually; on a pull
  request a deterministic sample of two recipes per family (kind × template × building
  type) and two configurations per service (`--sample 2`, about a quarter of the time);
- `package` (Linux): builds the `atlas-schedules` wheel, installs it in a clean virtual
  environment and generates the quick-start example from outside the checkout with the
  console script and `python -m atlas_schedules` (ADR 0049);
- `windows-tests (atlas)`, `windows-tests (schedules-commercial)` and
  `windows-tests (schedules-rest)` (Windows, Python 3.14): the same shards, and the
  release checksums on that platform.

The required `research / atlas (ubuntu-latest, 3.11)` check passes only when every Linux
job passes, and `research / atlas (windows-latest, 3.14)` only when every Windows shard
passes. A push to `main` runs `release`, `package` and the full `schedules` smoke, and
skips the unit shards: branch protection admits only pull requests whose checks passed
against an up-to-date `main`, so the merge commit's tree was already tested; the gates then
accept the skipped jobs. The weekly and manual runs run every job. A pipeline run takes
about as long as its slowest job rather than the sum of all checks.

Measured on pull request #32 (2026-10-29, before this shape): `build` 19 to 34 min on a
cache miss (catalogue generation 10 to 17 min, MkDocs 7 to 13 min; a hit skips both),
`schedules` 11 min, unit shards 5.5 min (atlas) and 9 to 11.5 min (schedules, both
platforms), `release` 2.4 min. The build job's dependency step (pip and the Playwright
Chromium) takes 0.6 min and is kept on cache hits too: `site_smoke` needs Chromium on every
tree. A separate workflow, `atlas-schedules-release.yml`, runs only for tags
`atlas-schedules-v*` and attaches the wheel to that tag's GitHub release.

The research workflow additionally reproduces frozen construction base v2.0.0,
applicability v2.1.0, distribution v2.2.0 and additive unified release 1.1.0 with
their existing `--check` commands. Shared mass release 1.0.0 and its seven paired
examples are reproduced with `construction_mass_release --check --examples`.
Supporting profile 1.1.0 files and declared input hashes are verified by `construction_weighting.load_profiles()`; this does
not require the ignored native-recovery cache. Reproducing profiles with
`construction_weighting --check` is a separate maintenance check requiring the
previously recovered `build/equivalent-work/commercial-weights.json` and pinned
source/runtime retrieval for re-execution. The base, applicability, distribution
and profile checks run on Linux; the unified and shared-mass byte reproductions
run on the pinned Windows producer. No native source recovery or annual
construction simulation is introduced.

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
The full Python suite and the other research checks run on Linux only. Every
original producer byte comparison remains mandatory. Frozen data, historical
generator sources, reported errors and recipe IDs are preserved. Consumers do
not need to regenerate fit metrics or their hashed IDs when loading a release.

## Combined foundation publication checks

The foundation candidate adds explicit gates without changing required job names,
automatic events or main-only deployment. The pinned Windows x64 / CPython 3.14.7
producer runs `python -m scripts.construction_foundation_release --check --examples`
to reproduce the combined freeze and its paired examples exactly. Both required
matrix platforms run `python -m scripts.validate_construction_foundation --all`
over all 3,320 pairs from the frozen extension, alongside the older mass-complete
consumer validator. Consumers do not refit ordinary foundation interfaces when
loading the frozen delivery.

Both platforms also verify the frozen source execution/airflow and native-smoke
receipts:

```console
python -m scripts.recover_construction_foundations --check
python -m scripts.construction_foundation_airflow --check
python -m scripts.construction_foundation_smoke
```

These commands verify committed records and declared hashes/source probes. They
must not invoke `--recover`, native-smoke `--run`, runtime downloads or annual
simulation. Actual native extraction and EnergyPlus execution remain separate,
explicit maintenance operations. A local handover packet or ignored recovery cache is
not a build input. The site no longer serves the frozen combined delivery: its
construction exports come from the newest atlas release (ADR 0043). See the
[release notes](release-notes-construction-foundation-v1.0.0.md) for migration and
remaining publication gates.
