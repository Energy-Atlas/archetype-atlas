# Reproducing and validating the atlas

Use Python 3.11+; the local run used Python 3.14 on Windows with a clean virtual
environment and `requirements.txt`. CI defines Linux 3.11 and Windows 3.14 jobs;
remote CI execution is not claimed until the repository is pushed and jobs run.
Public HTTPS downloads need no credentials, so `.env.example` declares no API keys.

## Setup and source retrieval

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe -m scripts.fetch
.venv/Scripts/python.exe -m scripts.fetch --verify-only
```

On macOS/Linux replace `.venv/Scripts/python.exe` with `.venv/bin/python`.
`fetch` reads only pinned raw URLs in `sources/lock.json`, bounds download size,
verifies byte count and SHA-256 before installing a cache blob, and rejects
credential-bearing or unsafe paths/URLs. Existing blobs are verified and never
silently refreshed. A checksum mismatch requires investigation and a separately
versioned source update, not deleting/overwriting the lock to make a test pass.

All locked blobs must be present for building. To test a fresh download cache,
use `fetch --cache-root build/fresh-raw`, then
`build --raw-root build/fresh-raw --output build/fresh-atlas`.
Source license notices are tracked under `sources/licenses/`.

## Pilot, full build and checks

```powershell
.venv/Scripts/python.exe -m scripts.build --pilot --output data/interim/medium-office-pilot
.venv/Scripts/python.exe -m scripts.validate data/interim/medium-office-pilot
.venv/Scripts/python.exe -m scripts.build
.venv/Scripts/python.exe -m scripts.validate
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe -m scripts.compare
.venv/Scripts/python.exe -m scripts.reproduce
```

`build` is offline and deterministic once dependencies and raw blobs are available.
It validates before writing outputs. Canonical JSON tables and metadata use LF
newlines, fixed source extraction dates and sorted stable IDs. The source lock
records first retrieval; rebuilds do not inject wall-clock timestamps into data.
Combined JSON and CSV exports are generated locally and ignored in Git.

`compare` writes `docs/validation/source-comparison.json`, explicitly distinguishing
locked source-input comparisons from external scorecard or simulated-model
validation. `reproduce` rebuilds in a temporary directory and compares every
canonical table byte. Tests exercise real parsing and adversarial mutations;
they require the raw cache and do not make network calls themselves.

## Releases and Git

The v0.1.0 and v0.2.0 snapshots are immutable. Verify each with:

```powershell
.venv/Scripts/python.exe -m scripts.release --verify
.venv/Scripts/python.exe -m scripts.release --verify --target data/releases/v0.1.0
```

The release includes canonical tables, metadata, schema, source lock/selection,
license notices, README, supporting scientific documentation, release notes and
a SHA-256/size/count manifest with the generating Git commit. Release creation
enforces independent source comparison and full canonical byte reproduction.
It also requires named typology and per-template coverage. Run
`python -m scripts.coverage` for the machine-readable coverage report.
Before
freezing a new version, update the schema/version constants, target/date,
selection, tests and release notes in a focused commit, rebuild, run all checks
and independently review the scientific changes. `release` refuses to overwrite
an existing target. Schema changes require clear migration guidance.

Before every commit inspect the staged diff and run:

```powershell
git diff --cached --check
.venv/Scripts/python.exe -m scripts.audit --staged
```

The audit flags credential files and common token/private-key/credential-URL
patterns without echoing secret values. It complements human/agent staged-diff
inspection; it is not a guarantee that arbitrary secrets or private data cannot
exist. Commits use a neutral automated identity, Conventional Commits, and truthful
`Agent-Model` trailers. The exact runtime model identifier was unavailable; this
is recorded instead of inventing a provider-specific identifier. Tags are local
until an explicit publication workflow is requested.
