# ADR 0049: The atlas-schedules package and its versioning

Status: accepted (2026-10-29, user decisions: package `atlas_schedules` for pip, publish the
wheel on the GitHub release only, no PyPI).

## 1. Context

- The schedule generator (`atlas_schedules`, ADR 0035, ADR 0047) is an optional add-on to the
  atlas data: a consumer such as BEMGen needs it installed, with its recipes, pinned tables
  and request schema, and needs to know which atlas data release its recipes came from.
- Until now the generator ran only from a checkout (`python -m atlas_schedules`), with
  `requirements.txt` pinning numpy and jsonschema for this repository's own CI.
- The generator version (`atlas_schedules.__version__`, 3.0.0 since ADR 0047) and the data
  release version (2.0.0, ADR 0046) move for different reasons: a generator release changes
  the port, its kernels or its request schema; a data release changes the atlas records.

## 2. Decisions

1. **One package, `atlas-schedules`**, built from `pyproject.toml` with setuptools: the
   `atlas_schedules` package and its data (`data/`: recipes, configurations, services,
   schedules, sampling and characteristics tables, weather, upstream notices; `schemas/`:
   the request schema). *Amended by [ADR 0051](0051-generation-parameters-in-the-release.md)
   (generator 4.0.0):* the recipes, configurations, services and schedule table are replaced by
   the generator view of one data release (`data/atlas-release/`, built before the wheel). Runtime dependencies are numpy and jsonschema with lower bounds;
   `requires-python >= 3.11`. The console script `atlas-schedules` runs the same `main` as
   `python -m atlas_schedules`, which keeps working.
2. **The package version is the generator version.** `pyproject.toml` reads
   `atlas_schedules.__version__`; `tests/test_package.py` requires it to be a release
   version (`X.Y.Z`, no dev suffix on `main`), and every bundle names it as
   `generator_version`. The request and bundle schema version (3.0.0) is separate and only
   moves with the request contract (ADR 0047 item 10).
3. **Published on GitHub releases, not PyPI.** A tag `atlas-schedules-vX.Y.Z` runs
   `.github/workflows/atlas-schedules-release.yml`, which requires the tag to name the
   package version, builds the wheel and sdist, installs the wheel in a clean environment,
   generates the quick-start example, and attaches both files to the GitHub release of
   that tag (creating it if needed). Consumers install the wheel from the release asset
   URL. The validation workflow's `package` job builds and installs the wheel on every
   pull request, so a tag never discovers a packaging fault first.
4. **Generator and data releases are versioned separately and paired explicitly.** Each
   data release's manifest names the generator version its `generator.json` recipes were
   written with, and the wheel that carries them (`generator` field, from release 2.1.0).
   Each generator release's notes name the data release its packaged recipes were built
   from. The pairing table lives in this ADR:

   | Generator (`atlas-schedules`) | Packaged recipes built from | Data release carrying the same recipes |
   | --- | --- | --- |
   | 3.0.0 | atlas release 2.0.0 programs (ADR 0046 section 6, ADR 0047 section 3) | 2.1.0 |
   | 4.0.0 | none packaged: recipes assembled from the release read; the wheel bundles the generator view of 2.2.0 (ADR 0051) | 2.2.0 |

   A generator minor or patch that leaves the recipes unchanged pairs with the same data
   release; a data release that rewrites recipes names the generator version that wrote
   them. A request names programs by their release ID or definition ID, so a bundle is
   reproducible from the generator version and the request alone.
5. **Building is a development dependency.** `requirements-dev.txt` pins `build`; the
   runtime pins in `requirements.txt` are unchanged.

## 3. Agent decisions

- **setuptools, static version.** `attr = "atlas_schedules.__version__"` is read
  statically from a literal, so building needs no numpy. *Alternative:* a separate
  `VERSION` file. *Reason:* one constant, already read by the generator.
- **The package README is the generator guide** (`docs/schedule-generator.md`), so the
  wheel's metadata describes the generator rather than the atlas. Its relative links
  resolve on GitHub, not on the metadata page; the project URLs point at the guide.
- **No sdist-only files.** `include-package-data` is off and the data globs are explicit
  (`data/**/*.json`, `data/**/*.gz`, `schemas/*.json`); a test fails if a file under
  `data/` or `schemas/` matches no glob.
- **No PyPI name reservation.** The owner chose GitHub releases only; the name stays
  free until that changes.

## 4. Consequences

- `pip install <wheel URL>` gives `atlas-schedules`, `python -m atlas_schedules` and
  `from atlas_schedules import generate` outside a checkout; no OpenStudio, Ruby or
  network access at run time.
- The 3.0.0 wheel was about 10 MB (2,113 files), most of it recipes and the gzip
  characteristics shards; the 4.0.0 wheel bundles the generator view instead (ADR 0051
  section 6).
- Changing `__version__` is a release act: bump it, update the CHANGELOG, tag
  `atlas-schedules-v<version>` on `main` after the pull request merges.
- Release 2.1.0 is the first data release to name its generator version and wheel
  (ADR 0046's delta rules; CHANGELOG); release 2.2.0 names generator 4.0.0 as the first that
  reads it (ADR 0051).

## 5. Amendments

- 2026-10-29: **Checksums are attached from 3.0.0 on.** Each generator release carries
  `SHA256SUMS.txt` (`sha256sum` format) for its wheel and sdist, verified with
  `sha256sum -c SHA256SUMS.txt`. For 3.0.0 the file was computed from the attached assets
  and checked against an independent `python -m build` of the tag in a clean venv: the
  wheel's 2,111 package files and the sdist's 2,164 are byte-identical to the published
  ones; only the archive timestamps and the line endings of the generated metadata files
  (`METADATA`, `PKG-INFO`, `setup.cfg`, written with the build host's newline) differ, so
  a rebuild reproduces the contents, not the archive hash. From 4.0.0 on the workflows emit the
  file (`scripts/build_release_assets.py`, ADR 0051 section 6), and the wheel and sdist
  are built reproducibly, so a rebuild of the commit gives the same hashes.
