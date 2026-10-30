# ADR 0051: Generation parameters in the release; generator 4.0.0 reads a release

Status: accepted (2026-10-29, user decisions 1 to 7 in section 2; shipped 2026-10-30 as data
release 2.2.0 and generator 4.0.0). It supersedes the unmerged publishing design of the branch
`codex/publishing-design` (its ADR text carried the number 0049, which
[ADR 0049](0049-atlas-schedules-packaging.md) took on `main`; that text never merged and its
number is not reused). It amends [ADR 0036](0036-suite-based-release-storage.md) section 3,
[ADR 0046](0046-release-2-0-0.md) sections 2, 3, 6, 8 and 12, [ADR 0047](0047-resstock-apartment-units-and-source-magnitudes.md)
section 5 and [ADR 0049](0049-atlas-schedules-packaging.md) sections 2 and 4 (section 10).

## 1. Context

- **The packaged recipes repeated the release.** Generator 3.0.0 shipped 1,585 recipes (7.1 MB),
  a schedule table (0.5 MB), 186 shared services (0.8 MB) and 120 building configurations
  (0.4 MB) in `atlas_schedules/data/`. A commercial recipe repeats its release program's load
  values, units, heat fractions, occupancy density, schedules and required services. Only a
  small part is generator-specific: for a commercial recipe, its building configuration.
- **Two kinds of ID.** The packaged recipes were keyed by definition IDs (`program-…`) for
  1,187 90.1 recipes and the 41 ResStock dwellings, and by release IDs for the 357 DOE Ref
  recipes. Only `generator.json` and the dwellings' `source_id` linked a definition ID to its
  release program; `id-map.json` holds no definition ID (ADR 0046 section 8). The 90.1 services
  and schedules were keyed by definition IDs (`service-…`, `schedule-…`) as well.
- **One release program, two recipes.** ADR 0036 section 4 retired the source/reviewed twins: a
  release program is one record with its fillings inline. The recipes kept both: 577 of the 967
  programs with recipes had a source and a reviewed recipe, the reviewed one with its own
  building configuration (`…__reviewed`). The two consumer exports call these views `source`
  and `filled`.
- **Release 2.1.0 carried the recipes beside the programs** in each folder's `generator.json`
  (83 folders; ADR 0046 sections 2 and 12), because program IDs hash the program's content and a
  recipe inside the program file would have moved every ID (ADR 0046 section 3, decision 2).
  Release 2.1.0's manifest pinned the generator 3.0.0 wheel and the packaged recipes' digest.
- **The consumer export is closed.** Program JSON 5.4.0's `source.release` was an enum of four
  labels (1.5.0 to 2.1.0). BEMGen validates against an embedded copy of the schema and rejects
  an unknown label (BEMGen D-198); BEMGen 1.6.0 pins generator 3.0.0 and bundle schema 3.0.0.
- **The parked design.** Branch `codex/publishing-design` (commits 85936c4b to 15a1456a, built
  on `main` before pull requests #32 to #38) implemented this design as release 2.1.0 and
  generator 3.0.0 before `main` shipped a different 2.1.0 (the apartment recipes) and the
  setuptools package (ADR 0049). Its stages P1 to P5 are rebuilt here on `main` as 2.2.0 and
  4.0.0; its two gate exceptions (section 3) stand.

## 2. Decisions (user, 2026-10-29)

1. **This ADR, number 0051**, records the design; 0049 stays the packaging ADR.
2. **Data release 2.2.0, a delta on 2.1.0** through `scripts/atlas_delta.py` (the mechanism 2.1.0
   used; `--check` and `--verify` pass; the manifest pins the writer's hash). It adds each
   generated folder's `generation.json` (the parked P2 content, re-derived on top of 2.1.0's
   apartment-unit recipes, so 2.1.0's eight ResStock apartment folders are covered) and
   `definition-map.json`, and removes the `generator.json` files (`removed` in the manifest).
   Program IDs are unchanged: the ID rule leaves `generation` out. Exports stay Program JSON
   5.4.0 with `source.release` `atlas-release-2.2.0`; the 5.4.0 schema admits the label by a
   pattern, a 5.4.x widening (section 5).
3. **Generator 4.0.0**, breaking: request schema 4.0.0 takes release program IDs and
   `values: source | filled`; a `program-…` or `service-…` ID is refused with a message naming
   `atlas-schedules translate`. The bundle keeps its content and gains its release provenance
   (section 4). Reproducibility: the same request on the same release gives the same bundle as
   generator 3.0.0 for every recipe the gate proved equivalent; the check is a test with an
   answer key (section 7).
4. **Install UX.** `pip install <wheel>` alone works: the wheel bundles the generator view of
   release 2.2.0 (section 6); `ATLAS_RELEASES` or `--release-dir` points at a release on disk,
   resolving deltas over their bases; `atlas-schedules --version` prints the generator and the
   release it reads.
5. **Releases and checksums.** Tags `v2.2.0` (data) and `atlas-schedules-v4.0.0` (generator).
   The wheel workflow attaches the wheel, the sdist and `SHA256SUMS.txt`; a `v*` workflow
   attaches `atlas-release-<version>.zip` (the release folder with its bases) and
   `SHA256SUMS.txt`. Builds are reproducible (`SOURCE_DATE_EPOCH`, sorted entries). The
   `package` CI job stays green and pull-request CI stays light.
6. **Tests**: package data coverage, delta release tests (`test_release_2_2_0`), schema checks,
   the site reading 2.2.0, the sampled catalogue smoke, `release_editor --check`,
   `build_apartment_units --check`, `build_reference_recipes --check`, and the full local suite
   before the pull request.
7. **Documents**: this ADR; amendments in 0036, 0046, 0047 and 0049; the generator guide's
   4.0.0 quick start; release notes 2.2.0; README install and verify; CHANGELOG.

## 3. The `generation` block

One block per program the generator can generate, including the unconditioned programs it
counts as inactive. Programs it cannot generate (IECC, manufactured housing, plenums without
loads, the construction-only programs, the DOE Ref types without a sampling building type)
carry none, and the generator answers them with `unsupported_input`. The block holds only what
the program does not already state, per view (`source`, and `filled` where the filled program
generates differently or carried a reviewed recipe):

| `method` | Programs | Parameters per view | Everything else from |
| --- | --- | --- | --- |
| `comstock_hours` | 734 | `configuration_id` | the program's loads, parameters and service citations; slot modes by rule (setpoints by thermostat, the rest by hours) |
| `composition` | 191 | none | the mix's members (`represented_area_m2`); a member takes its parent's view where it has one, else source |
| `fixed` | 22 | none | the program's loads and schedules as source rules |
| `resstock_unit` | 20 | `resstock_unit` (ADR 0047: building type, height class, vintages, HVAC, hot water per person, source) | the program's hot water and its service; the request (zone, floor area, residents) |
| `resstock_dwelling` | 41 | the dwelling's executed OpenStudio-HPXML inputs: slots, demands with annual totals, controls, companions, installed appliances, thermostat arguments | the dwelling record |

1,008 programs carry blocks, 1,585 program views in 90 folders (83 commercial, 7 ResStock
dwelling folders). A commercial example:

```json
"generation": {
  "schema_version": "1.0.0",
  "method": "comstock_hours",
  "views": {
    "filled": {"configuration_id": "primary_school__90_1_2019__reviewed"},
    "source": {"configuration_id": "primary_school__90_1_2019__source"}
  }
}
```

A service's block lists the configurations it runs under (186 services); its volume, schedule,
target temperature and fractions come from its `services.json` entry. A configuration (120)
holds the sampling building type, its People (release schedule, design people) and rule-day
inversion. `definition-map.json` maps 1,216 definition program IDs to their release program and
view and 150 definition service IDs to their release service, and lists 12 retired IDs.

**The gate** (`scripts/derive_generation_blocks.py`, section 7): every packaged recipe,
service and configuration of generator 3.0.0, re-keyed by release ID, equals the one assembled
from the release (`atlas_schedules.programmes.assemble`) as JSON, schedules compared by their
rules. Two exceptions are stated:

- 12 hotel corridor compositions that no release program holds are retired (the department
  and general corridor mixes of both hotels share the one recipe that remains).
- 36 90.1 apartment-building `fixed` recipes now carry the release values. Their legacy form
  dropped the known heat fractions of their loads (radiant 0.6 for corridor lighting, for
  example) and kept a zero-density occupancy slot; the DOE Ref rule, which the release values
  follow, keeps the fractions and leaves zero loads out.

## 4. IDs, views and versions

- **The block is not part of the program's identity.** The program ID rule (ADR 0046 section 8)
  hashes the program without `id`, `name` and `generation`
  (`scripts.atlas_programs.program_id`, `scripts.release_editor` `UNHASHED`). Adding or changing
  generation parameters moves no ID and no citing file; `release_editor --check` reads release
  2.2.0 and requires every program read with its block to keep its ID (1,008 programs). This
  removes the reason for ADR 0046 section 3, decision 2, and carries out ADR 0036 section 3.
- **The block has its own version** (`generation.schema_version` 1.0.0, also in the release
  manifest's `generation` block). The generator declares what it reads: release major 2,
  generation major 1 (`atlas_schedules.release.READS`).
- **Requests take release IDs and a view** (request schema 4.0.0,
  `atlas_schedules/schemas/request-v4.schema.json`). A program instance names its release
  program (`program_id`) and optionally `values`: `source` or `filled`; the default is `filled`
  where the block has that view, else `source`. A service instance names its release service.
  Definition IDs are refused: `atlas-schedules translate request.json`
  (`atlas_schedules.release.translate`) rewrites a 3.0.0 request through the release's
  `definition-map.json`, raising `schema_version` to 4.0.0.
- **The bundle is schema 4.0.0** (agent decision): its content is generator 3.0.0's, and it
  gains `release` (`version`, `manifest_sha256`, `generation_schema_version`) at the top level
  and `values` on every owner (the programme view; `null` for services, caller water and
  mixtures). A 3.0.0 reader that only indexes the fields it knows reads it unchanged.
- **The export is unchanged in form.** The blocks stay in release storage; Program JSON 5.4.0
  exports from 2.2.0 carry no `generation` and are 2.1.0's apart from `source.release`.

## 5. Export schema: a release pattern

Program JSON 5.4.0's `source.release` is `{"type": "string", "pattern":
"^atlas-release-\d+\.\d+\.\d+$"}` instead of the enum of labels (`scripts.atlas_exports
RELEASE_LABEL`). The schema's own version stays 5.4.0 (`schema_version` is a constant), so the
change had to be compatible as a 5.4.x revision: every document the enum admitted still
validates, and the 2.2.0 label and later labels validate without a schema edit. A consumer
that embeds its own copy of the 5.4.0 schema (BEMGen D-198) refreshes the copy once and then
needs no change per data release. The older contracts keep their enums and gain the label:
Program JSON 5.1.0 and 5.2.0, building services 1.0.0 and source model constructions 1.0.0.

## 6. Release vehicles

- **Data release 2.2.0** (`data/atlas-releases/v2.2.0`): a delta on 2.1.0 (which is a delta on
  2.0.0). Its folder holds its own files only: 90 `generation.json`, `definition-map.json`,
  `LICENSE`, `README.md` and `manifest.json` (`base_release` 2.1.0 with its manifest hash;
  `removed`: the 83 `generator.json` paths, which are also the eight 2.1.0 rewrote; `generation`
  1.0.0; `generator` 4.0.0; `input_sha256`: the licence, the base manifest and the writer;
  `counts.generation`). `atlas_delta.files('2.2.0')` resolves the chain; `atlas_exports.Release`
  defaults to 2.2.0 and the site shows it.
- **Release 2.1.0's manifest, in place.** Its `input_sha256` pinned `atlas_schedules/data/recipes`
  and the version constant, which left the tree. ADR 0046 section 7's rule for releases whose
  inputs left applies: the manifest now pins the licence and the base manifest only, records the
  edit under `edited_by`, keeps `generator` (3.0.0, the recipes' digest) as history, and
  `--check --release 2.1.0` rebuilds the licence, the README and the manifest around the
  `generator.json` files, which are kept as written (commit 77ebad7e) and verified by checksum.
  No published asset goes stale: the GitHub release `v2.1.0` had no data archive.
- **Generator 4.0.0** (`atlas-schedules` 4.0.0, ADR 0049's package). It reads a release from,
  in order: `set_releases()` or `--release-dir`; `ATLAS_RELEASES`; the source tree's
  `data/atlas-releases` when the package runs from a checkout; the generator view the wheel
  bundles. Each may be a folder of release folders (`v2.0.0/`, `v2.1.0/`, `v2.2.0/`), one release
  folder, or a view. The newest major-2 release with generation blocks is read.
- **The generator view** (`atlas_schedules/data/atlas-release/`, `scripts/build_generator_view.py`;
  agent decision): per generated folder, exactly the files the assembler reads
  (`generation.json`, `schedules.json`, `services.json`, the program records with blocks and
  their composition members) packed as one JSON file per folder, plus `definition-map.json`
  and an `index.json` naming the release, its manifest hash and the base chain. A bundle from
  the view equals a bundle from the release tree (`tests/test_package.py`,
  `build_release_assets --check-install`), because the records are the same documents and the
  provenance the same hash. The view is built before `python -m build` and is not committed:
  one source of truth in `data/atlas-releases`, 15.8 MB of JSON that compresses in the wheel.
  *Alternative:* commit the view. *Reason:* it duplicates 1,100 release files in git for no
  value change. *Alternative:* no view, `ATLAS_RELEASES` required. *Reason:* decision 4.
- **Wheel size.** The 4.0.0 wheel is 9.7 MB (3.0.0: 10.2 MB). The view (12.3 MB of JSON; program
  records cut to the fields the assembler reads, `build_generator_view.KEEP`) compresses to
  1.3 MB; 7.4 MB is the ResStock tables, chiefly the characteristics shards (6 MB gzip,
  incompressible), 0.8 MB the weather and 0.1 MB the code. The wheel cannot go well under 10 MB
  while it carries the characteristics shards, which generator 3.0.0 carried too.
- **GitHub releases**, one tag namespace each: `v2.2.0` with `atlas-release-2.2.0.zip`
  (`v2.0.0/`, `v2.1.0/`, `v2.2.0/` as they sit in the tree, sorted entries, 1980-01-01 times) and
  `SHA256SUMS.txt`; `atlas-schedules-v4.0.0` with the wheel, the sdist and `SHA256SUMS.txt`
  (`.github/workflows/atlas-data-release.yml`, `atlas-schedules-release.yml`;
  `scripts/build_release_assets.py`, `SOURCE_DATE_EPOCH` at the commit time). `sha256sum -c
  SHA256SUMS.txt` verifies a download.

## 7. Migration stages, as run

1. **P1, assembler and gate.** `atlas_schedules/release.py` (release stores and the delta
   resolution), `programmes.assemble`, `assemble_service` and `assemble_configuration`;
   `scripts/derive_generation_blocks.py` derived the blocks from the 3.0.0 packaged copies over
   resolved 2.1.0 and ran the gate: 1,585 program views (1,156 commercial, 310 composition, 40
   fixed, 38 apartment units, 41 dwellings), 186 services and 120 configurations equal (206 service IDs
   mapped, the apartment units' water services among them);
   36 legacy fixed forms and 12 orphans as stated. The derived files equal the parked P2 files
   apart from the apartment blocks' provenance paths, which `build_apartment_units` then wrote
   in its own form.
2. **P2, release 2.2.0.** `atlas_delta --write --release 2.1.0` (the manifest erratum) and
   `--write` (2.2.0); `build_apartment_units --check` (20 blocks) and `build_reference_recipes
   --check` (32 folders, 357 programs, from the DOE v1.4_7.2 files) pass; `release_editor
   --check` passes.
3. **P3, the switch.** Generator 4.0.0 reads the release; the packaged recipes, services,
   configurations and schedule table (1,892 files) and `scripts/recipe_shapes.py` left the tree,
   with the derivation script and the capture script, which are readable at commit `85b3bb58`
   (stages P1 and P2). The schedules suite, its answer keys and `test_reference_recipes` pass
   unchanged apart from IDs; the catalogue smoke has no failures.
4. **Equivalence key.** `tests/answer_keys/orchestration/generator-3-0-0-bundles.json.gz` holds
   266 generator 3.0.0 bundles (100 commercial, 20 fixed, 31 composition, 38 apartment units,
   41 dwellings, 32 service variants, the 4 examples; seed 42), captured by
   `scripts/capture/generator_3_0_0_bundles.py` (commit `85b3bb58`) from the packaged recipes
   under generator 3.0.0.
   `tests/schedules/test_generator_3_0_0_equivalence.py` translates each request and requires
   every owner's loads, controls, extent, generation record and every schedule's unit, sum,
   maximum and every 37th hour to agree within 1e-9; the three retired compositions in the
   sample are refused with the translation message. 263 cases agree. The assembler keeps 3.0.0's
   dict orders (companions, modes, caller-water controls sorted by key, as the packaged files
   stored them), so a 4.0.0 bundle differs from 3.0.0's only in the versions, `release`, the
   owners' `values`, and the IDs (release IDs in place of definition IDs, also inside composition
   member and water owner keys).
5. **P4, publish.** `__version__` 4.0.0; the wheel, sdist and data archive built with
   `SHA256SUMS.txt`, each twice with the same hashes (the wheel and sdist are each built from the
   tree, not the wheel from the unpacked sdist, and the sdist's tar is normalised to the commit
   time, because setuptools keeps the checkout's file times); `--check-install` in a fresh venv
   against the bundled view and the extracted archive, same bundle from both, the sampled smoke
   passing under each. Tags after the merge (section 2, decision 5).
6. **P5, documents.**

## 8. Consequences, and what a consumer changes

- One source of truth: a program's values live once, in its program record; the generator
  cannot drift from the release. A change to generation parameters is a data release; a change
  to generation logic is a generator release, tested against the newest data release.
- The generator needs a release: bundled in the wheel, or on disk through `ATLAS_RELEASES`.
- **BEMGen (1.6.0 pins generator 3.0.0, bundle 3.0.0, Program JSON 5.4.0 with the enum copy):**
  1. request shape: `schema_version` `"4.0.0"`; `program_id` and `service_id` release IDs
     (`90-1-2013.medium-office.source.whole-building-md-office.672bf4`,
     `90-1-2013.medium-office.main.87f1fd`), `service_links` keyed by release service IDs, and
     optionally `values`; a stored 3.0.0 request converts once with `atlas-schedules translate`;
  2. pins: generator `4.0.0` (wheel `atlas_schedules-4.0.0-py3-none-any.whl` on
     `atlas-schedules-v4.0.0`), bundle `schema_version` `"4.0.0"`, data release `2.2.0`
     (`bundle.release.version`, `manifest_sha256`
     `67e73e55861a9b9c88d4a745ee883ec73ad859c5a8d14ac86be3b3409ce7ece4`);
  3. the embedded Program JSON 5.4.0 schema: refresh the copy (`source.release` is a pattern) or
     admit `atlas-release-2.2.0`; exports from 2.2.0 differ from 2.1.0's in that label only;
  4. bundle fields added: `release` and each owner's `values`; everything else as 3.0.0.

## 9. Alternatives considered

- **Keep the recipes beside the programs** (`generator.json`). *Rejected:* the values are kept
  twice and can drift, and every value change needs both files rewritten.
- **Put the block in the program and hash it.** *Rejected:* every program ID and citing file
  would change again for no value change.
- **Ship release copies inside the generator package.** *Rejected* for whole copies (about
  9 MB duplicated, a pinned private copy); *taken* as the generator view of one named release,
  verified equal to the tree, because decision 4 needs `pip install` alone to work.
- **Store the 2.2.0 program files whole, with their blocks.** *Rejected:* about 1,000 program
  files copied into git again for a few hundred bytes each; the delta keeps them once.
- **Translate definition IDs through `id-map.json`.** *Rejected:* it maps release IDs only, and
  one release ID stands for two recipes; `definition-map.json` names the view.
- **Keep the bundle at schema 3.0.0 with the new fields.** *Rejected:* a strict 3.0.0 reader
  would break on the added fields while the label said nothing changed; the request already
  breaks, and the consumer re-pins both together.
- **Add `generation` to the Program JSON export (5.5.0).** *Deferred:* no consumer needs it.

## 10. Amendments

- **ADR 0036 section 3:** the generation part of the recipe is the program's `generation`
  block; building configurations live in each folder's `generation.json`.
- **ADR 0046 section 2, decision 3, section 6 item 3 and section 12:** release 2.2.0 removes
  `generator.json`; 2.1.0's manifest is edited in place (section 6).
- **ADR 0046 section 3, decision 2:** superseded, since the block is outside the ID hash.
- **ADR 0046 section 6, decision 3:** requests take release IDs only, with a view.
- **ADR 0046 section 8:** the program ID rule hashes the program without `id`, `name` and
  `generation`.
- **ADR 0047 section 5:** release 2.2.0 carries the ResStock apartment-unit parameters as
  `resstock_unit` blocks.
- **ADR 0049 section 2 (decision 1) and section 4:** the package ships the generator view of a
  release instead of recipes; the pairing table gains generator 4.0.0 on data release 2.2.0.
