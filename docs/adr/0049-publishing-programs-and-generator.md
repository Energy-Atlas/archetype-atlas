# ADR 0049: Publishing generation parameters with the programs and the generator as its own release

Status: accepted (2026-10-29). It follows the user's direction of 2026-10-29: design
publishing together with the program definitions; small generator parameters may travel
inside the programs; the generator, shipped from this repository as a release alongside
the source, takes those parameters and generates. The user accepted the review's three
amended recommendations (section 10) on 2026-10-29. It amends ADR 0036 (section 3),
ADR 0046 (sections 2, 3, 6 and 8) and ADR 0047 (section 5), as listed in section 9.

## 1. Context

- **The packaged recipes repeat the release.** `atlas_schedules/data/` held 1,585 recipes
  (7.5 MB), a schedule table (0.5 MB), 186 shared services (0.8 MB) and 120 building
  configurations (0.5 MB). A commercial recipe repeats its release program's load values,
  units, heat fractions, occupancy density, schedules and required services. Only a
  small part is generator-specific: for a commercial recipe, its building configuration.
- **Two kinds of ID.** The packaged recipes were keyed by:
  - definition IDs (`program-…`), for 1,187 90.1 recipes and the 41 ResStock dwellings;
  - release IDs, for the 357 DOE Ref recipes.

  Only `generator.json` and the dwellings' `source_id` link a definition ID to its release
  program. `id-map.json` holds no definition ID: it maps release IDs as first committed to
  their re-derived values (ADR 0046 section 8). The 90.1 services and schedules are keyed by
  definition IDs (`service-…`, `schedule-…`) as well.
- **One release program, two recipes.** ADR 0036 section 4 retired the source/reviewed
  twins: a release program is one record, with its fillings inline. The recipes kept both:
  577 of the 967 programs with recipes have a source and a reviewed recipe, the reviewed one
  with its own building configuration (`…__reviewed`). The reviewed recipe is the source rule
  applied to the filled record. The two consumer exports call these views `source` and `filled`.
- **Tables are per folder.** Each template × building-type folder has its own
  `schedules.json` (schedules by release ID, with a shared `days` table) and `services.json`.
  83 folders have a `generator.json`: 17 per 90.1 template, 16 per DOE Ref vintage.
- **Release 2.0.0 carries stale recipes.** `generator.json` (ADR 0046 section 2, decision 3)
  has the 2.x apartment recipes. The release is released and immutable, apart from the one
  recorded erratum (ADR 0046 section 11), which was made in place to avoid writing the delta
  reader a 2.0.1 would need. No 2.x delta reader exists.
- **Why the recipes sit beside the programs.** ADR 0046 section 3, decision 2, kept the
  recipes out of the program files because program IDs hash the program's content: adding
  a recipe would have changed every program ID. ADR 0036 section 3 intended the recipe to
  be part of the program file.
- **The consumer export is closed.** The Program JSON 5.4.0 `source` object has
  `additionalProperties: false`, and its `release` field is an enum of `atlas-release-1.5.0`,
  `-1.6.0` and `-2.0.0`. BEMGen pins exactly 5.4.0 and validates against an embedded copy of the
  schema (BEMGen D-172), so a new field or a new release label in the export breaks it.
  BEMGen does not call the generator yet; a schedule generator is only a recorded
  requirement there (BEMGen D-134).
- **Generator 3.0.0 is not published.** The package is `3.0.0.dev0`, so its request
  contract can still change without a new major version.

## 2. Decision

Publishing is split in three:

| Where | What |
| --- | --- |
| Each program record in the resolved release | an optional `generation` block: the method and, per view, the parameters the record cannot give |
| Each folder's `generation.json` in release 2.1.0 | the folder's program blocks, its services' blocks and its building configurations |
| The generator release | code, the request schema, and the generator-wide data: ComStock hours sampling, ResStock characteristics and schedule tables, weather, notices, source locks |

The generator reads a program by its release ID and view, with the folder's
`schedules.json`, `services.json` and `generation.json`. From these it assembles the
recipe when loading (`atlas_schedules.programmes.assemble`), and applies the request. It
ships no copy of release values.

## 3. The `generation` block

One block per program the generator can generate, including the unconditioned programs it
counts as inactive. Programs it cannot generate (IECC, manufactured housing, plenums, the
construction-only programs, the DOE Ref types without a sampling building type) carry none,
and the generator answers them with `unsupported_input`. The block holds only what the
program does not already state, per view (`source`, and `filled` where the filled program
generates differently or carried a reviewed recipe):

| `method` | Programs | Parameters per view | Everything else from |
| --- | --- | --- | --- |
| `comstock_hours` | 734 | `configuration_id` | the program's loads, parameters and service citations; slot modes by rule (setpoints by thermostat, the rest by hours) |
| `composition` | 191 | none | the mix's members (`represented_area_m2`); a member takes its parent's view where it has one, else source |
| `fixed` | 22 | none | the program's loads and schedules as source rules |
| `resstock_unit` | 20 | `resstock_unit` (ADR 0047: building type, height class, vintages, HVAC, hot water per person, source) | the program's hot water and its service; the request (zone, floor area, residents) |
| `resstock_dwelling` | 41 | the dwelling's executed OpenStudio-HPXML inputs: slots, demands with annual totals, controls, companions, installed appliances, thermostat arguments | the dwelling record |

A commercial example:

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

A service's block lists the configurations it runs under; its volume, schedule, target
temperature and fractions come from its `services.json` entry. A configuration holds the
sampling building type, its People (release schedule, design people) and rule-day inversion.

Stage P1 (section 7) settled the table: every packaged recipe, service and configuration,
re-keyed by release ID, equals the assembled one as JSON, schedules compared by their rules.
Two exceptions are stated:

- 12 hotel corridor compositions that no release program holds are retired. The department
  and general corridor mixes of both hotels share the one recipe that remains.
- 36 90.1 apartment-building `fixed` recipes now carry the release values. Their legacy form
  dropped the known heat fractions of their loads (radiant 0.6 for corridor lighting, for
  example) and kept a zero-density occupancy slot; the DOE Ref rule, which the release values
  follow, keeps the fractions and leaves zero loads out.

## 4. IDs, views and versions

- **The block is not part of the program's identity.** The program ID rule (ADR 0046
  section 8) hashes the program without `id`, `name` and `generation`. Adding or changing
  generation parameters then moves no ID and no citing file. `release_editor --check`
  enforces this as it enforces the rule today. The residential tree keeps its own IDs, so a
  block moves none there either. This removes the reason for ADR 0046 section 3, decision 2,
  and carries out ADR 0036 section 3.
- **The block has its own version** (`generation.schema_version`, starting at 1.0.0). The
  generator declares which versions it reads, together with the release format it reads
  (release 2.x, `atlas_schedules.release.READS`).
- **Requests take release IDs and a view.** A program instance names its release program
  (`program_id`) and optionally `values`: `source` or `filled`. The default is `filled` where
  the block has that view, else `source`. A service instance names its release service. The
  definition IDs are retired from requests; release 2.1.0's `definition-map.json` maps each
  definition program ID to its release program and view, and each definition service ID to
  its release service. Generator 3.0.0 is still unpublished, so this lands in 3.0.0 rather
  than in a 4.0.0.
- **The export is unchanged.** The blocks stay in release storage. Program JSON 5.4.0 is
  exported from 2.0.0 as it is, still labelled `atlas-release-2.0.0`, because 2.1.0 changes no
  exported value; BEMGen is unaffected. An export that carries `generation` and the 2.1.0
  label (Program JSON 5.5.0) is made only when a consumer asks for it, for example when
  BEMGen takes up its schedule-generator requirement. The site keeps reading 2.0.0.
- **Each bundle records its inputs:** the generator version, the release version and
  manifest hash, and per owner the program ID, its view, the generation block version and
  the seeds.

## 5. Release vehicle

- **Data release 2.1.0**, a delta on 2.0.0 as ADR 0046 section 2 decision 1 provides for later
  minors. Its folder holds only its own files:
  - each folder's `generation.json`;
  - `definition-map.json`;
  - `manifest.json`: the base release with its manifest hash, every own file with its sha256,
    and the base files it retires (each folder's `generator.json`, which also retires the
    stale 2.x apartment recipes).

  A path resolves to the delta's file, else the base's unless retired
  (`atlas_schedules.release.Release`). A program record reads with its folder's block as
  `generation`.
- **Generator 3.0.0**, released separately from the data and from the source tree. It reads
  releases from a folder that holds the release folders side by side: `set_releases()`, else
  `ATLAS_RELEASES`, else the source tree's `data/atlas-releases`.
- **GitHub releases, one tag namespace each:**
  - `v2.1.0` (data): one archive holding `v2.0.0/` and `v2.1.0/` as they sit in the repository,
    with a `SHA256SUMS` file;
  - `generator-v3.0.0`: a wheel and an sdist that include the generator-wide data, with `SHA256SUMS`.

  This closes generator open item O4 (release build and checksum manifest).
- **Licences.** The generator archives carry ADR 0048's licences for original work and
  the upstream notices (ComStock, ResStock, OpenStudio-HPXML, TMY3) in their packaged
  `notices/`.

## 6. Consequences

- One source of truth: a program's values live once, in its program record. The generator
  cannot drift from the release, because it holds no copy of release values.
- The generator package shrinks by the recipes, schedules, services and configurations,
  about 9 MB. It needs a release on disk, either the source tree or the `v2.1.0` archive,
  to generate anything.
- A change to generation parameters is a data release, not a generator release. A change
  to generation logic is a generator release, and its tests run against the latest data
  release.
- Callers that passed definition IDs translate them through `definition-map.json` and name
  the view.

## 7. Migration stages

Each stage ends with its check passing. Nothing is deleted before stage P3.

1. **P1, assembler.** `programmes.assemble` builds each recipe from the release program, its
   `generation` block, the folder's configuration, `schedules.json` and `services.json`.
   `scripts/release_2_1_0.py --check` derives the blocks from the packaged copies and checks
   the equivalence of section 3 for recipes, services and configurations.
2. **P2, write 2.1.0.** Write the blocks, the `generation.json` files and `definition-map.json`,
   and amend the ID rule. Checks:
   - `release_editor --check` passes;
   - no program ID changes;
   - the P1 equivalence still holds when reading 2.1.0.
3. **P3, switch.** The generator reads the release, and the packaged recipes, schedules,
   services and configurations are deleted. Checks:
   - the schedules suite, the answer keys and `test_reference_recipes` pass unchanged;
   - the catalogue smoke run has no failures.

   `build_reference_recipes` and `build_apartment_units` write `generation` blocks instead
   of recipe files.
4. **P4, publish.** Set `__version__` to 3.0.0. Build the wheel, sdist and data archive with
   `SHA256SUMS`. Check: a clean install of the wheel against the extracted `v2.1.0` archive
   passes the smoke run. Tagging `v2.1.0` and `generator-v3.0.0` waits for the user's approval.
5. **P5, documents.** The generator page, the amendments in section 9, and the changelog.

## 8. Alternatives considered

- **Keep the recipes beside the programs** (`generator.json`, the status quo). *Rejected:*
  the values are kept twice and can drift, and every value change needs both files
  rewritten.
- **Put the block in the program and hash it.** *Rejected:* every program ID and citing file
  would change again (11,537 IDs in `id-map.json` today) for no value change.
- **Ship release copies inside the generator package.** *Rejected:* about 9 MB duplicated, and
  the generator would pin its own copy of the release.
- **Store the 2.1.0 program files whole, with their blocks.** *Rejected:* about 1,000 program
  files copied into git again for a few hundred bytes each; the delta keeps them once.
- **Translate definition IDs through `id-map.json`.** *Rejected:* it maps release IDs only, and
  one release ID stands for two recipes; a separate map names the view.
- **Add `generation` to the Program JSON export now** (5.5.0). *Deferred:* it breaks BEMGen's
  strict 5.4.0 reader, and no consumer needs it yet.

## 9. Amendments

- **ADR 0036 section 3:** the generation part of the recipe is the program's `generation`
  block; building configurations live in each folder's `generation.json`.
- **ADR 0046 section 2, decision 3, and section 6:** release 2.1.0 retires `generator.json`.
- **ADR 0046 section 3, decision 2:** superseded, since the block is outside the ID hash.
- **ADR 0046 section 6, decision 3:** requests take release IDs only, with a view.
- **ADR 0046 section 8:** the program ID rule hashes the program without `id`, `name` and
  `generation`.
- **ADR 0047 section 5:** release 2.1.0 carries the ResStock apartment-unit parameters.

## 10. Recommendations confirmed (user, 2026-10-29)

1. Requests take a release ID and a view (`values`: `source` or `filled`, default `filled`
   where it exists); `definition-map.json` translates the definition IDs (section 4).
2. Data and generator get separate GitHub releases and tags: `v2.1.0` (one archive with the
   2.0.0 base and the 2.1.0 delta) and `generator-v3.0.0`, each with `SHA256SUMS` (section 5).
3. The Program JSON export stays at 5.4.0, read from 2.0.0 and labelled `atlas-release-2.0.0`,
   until a consumer asks for `generation` (section 4).
