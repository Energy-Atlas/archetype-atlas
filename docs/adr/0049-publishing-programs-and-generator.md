# ADR 0049: Publishing generation parameters with the programs and the generator as its own release

Status: proposed (2026-10-29), for the user's review. It follows the user's direction of
2026-10-29: design publishing together with the program definitions; small generator
parameters may travel inside the programs; the generator, shipped from this repository
as a release alongside the source, takes those parameters and generates. Nothing here is
implemented yet. If accepted, it amends ADR 0036 (section 3), ADR 0046 (sections 3 and 8)
and ADR 0047 (section 5), as listed in section 9.

## 1. Context

- **The packaged recipes repeat the release.** `atlas_schedules/data/` holds 1,585 recipes
  (7.5 MB), a schedule table (0.5 MB), 186 shared services (0.8 MB) and 120 building
  configurations (0.5 MB). A commercial recipe repeats its release program's load values,
  units, heat fractions, occupancy density, schedule IDs and required services. Only a
  small part is generator-specific: for commercial recipes, the `configuration_id` and one
  mode per slot (median 229 bytes as JSON).
- **Two kinds of ID.** The 90.1 recipes (1,187 of them) are keyed by the frozen definition IDs of
  `data/definition-releases/v0.1.1` (`program-…`). The DOE Ref recipes (357) are keyed by release IDs. The
  41 ResStock dwellings also use definition IDs. The request accepts both
  (ADR 0046 section 6, decision 3).
- **Release 2.0.0 carries stale recipes.** Each folder's `generator.json` (ADR 0046
  section 2, decision 3) has the 2.x apartment recipes. The release is released and
  immutable, apart from the one recorded erratum (ADR 0046 section 11).
- **Why the recipes sit beside the programs.** ADR 0046 section 3, decision 2, kept the
  recipes out of the program files because program IDs hash the program's content: adding
  a recipe would have changed every program ID. ADR 0036 section 3 intended the recipe to
  be part of the program file.
- **The consumer export is closed.** The Program JSON 5.4.0 `source` object has
  `additionalProperties: false`. BEMGen pins exactly 5.4.0 and validates against an
  embedded copy of the schema (BEMGen D-172), so any new field in the export breaks it.
  BEMGen does not call the generator yet; a schedule generator is only a recorded
  requirement there (BEMGen D-134).
- **Generator 3.0.0 is not published.** The package is `3.0.0.dev0`, so its request
  contract can still change without a new major version.

## 2. Decision (proposed)

Publishing is split in three:

| Where | What | Size |
| --- | --- | --- |
| Each program record in the release | an optional `generation` block: the method and the parameters that cannot be derived from the program | about 230 bytes for a commercial program |
| Each template × building-type folder in the release | `generation.json` with that folder's building configurations, replacing `generator.json` | about 4 KB per configuration |
| The generator release | code, request and bundle schemas, and the generator-wide data: ComStock hours sampling (1.5 MB), ResStock characteristics and schedule tables (11 MB), weather (4.4 MB), notices, source locks | about 18 MB |

The generator reads a program by its release ID together with its folder's `generation.json`
and the release's `schedules.json` and `services.json`. From these it assembles the recipe
when loading, and applies the request. It ships no copy of release values.

## 3. The `generation` block

One block per program that the generator can generate, including the unconditioned
programs it counts as inactive today; programs it cannot generate (IECC, manufactured
housing) carry none, and the generator answers them with `unsupported_input`. The block holds only what the program does not
already state:

| `method` | Parameters | Everything else from |
| --- | --- | --- |
| `comstock_hours` | `configuration_id`; `modes` per slot (`hours`, `tstat`, `fixed`) | the program's loads, parameters and service citations |
| `fixed` | none | the program's schedules as source rules |
| `composition` | none | the mix file's members (`represented_area_m2`) |
| `resstock_unit` | the `resstock_unit` block of ADR 0047 (building type, height class, vintages, HVAC, hot water per person, source) | the request (zone, floor area, residents) |
| `resstock_dwelling` | the dwelling's source facts the record does not hold (installed appliances, thermostat, companions) | the dwelling record |

A commercial example:

```json
"generation": {
  "schema_version": "1.0.0",
  "method": "comstock_hours",
  "configuration_id": "primary_school__90_1_2019__reviewed",
  "modes": {"lighting": "hours", "electric_equipment": "hours", "occupancy": "hours",
            "activity": "hours", "heating_setpoint": "tstat", "cooling_setpoint": "tstat"}
}
```

Shared services get the same block on their `services.json` entry (configurations and
their schedules). Which recipe fields can be derived, and which must stay in the block, is
not settled by this table: stage P1 (section 7) settles it by requiring that the assembled
recipe equal today's packaged recipe for every program.

## 4. IDs and versions

- **The block is not part of the program's identity.** The program ID rule (ADR 0046
  section 8) hashes the program without `id`, `name` and `generation`. Adding or changing
  generation parameters then moves no ID and no citing file. `release_editor --check`
  enforces this as it enforces the rule today. This removes the reason for ADR 0046
  section 3, decision 2, and carries out ADR 0036 section 3.
- **The block has its own version** (`generation.schema_version`, starting at 1.0.0). The
  generator declares which versions it reads, together with the release format it reads
  (release 2.x).
- **Requests use release IDs only.** The 90.1 definition IDs are retired from requests, and
  `id-map.json` translates the old IDs for callers. Generator 3.0.0 is still unpublished,
  so this lands in 3.0.0 rather than in a 4.0.0.
- **The export is unchanged.** The block stays in release storage. Program JSON 5.4.0 is
  exported as it is, so BEMGen is unaffected. An export that carries `generation`
  (Program JSON 5.5.0) is made only when a consumer asks for it, for example when BEMGen
  takes up its schedule-generator requirement.
- **Each bundle records its inputs:** the generator version, the release version and
  manifest hash, the program ID, the generation block version and the seed.

## 5. Release vehicle

- **Data release 2.1.0**, a delta on 2.0.0 as ADR 0046 section 2 decision 1 provides for later minors:
  - adds the `generation` blocks and each folder's `generation.json`;
  - removes each folder's `generator.json`, which also retires the stale 2.x apartment recipes.

  Its `manifest.json` lists every file with its sha256, as today.
- **Generator 3.0.0**, released separately from the data and from the source tree.
- **GitHub releases, one tag namespace each:**
  - `v2.1.0` (data): the release folder as an archive, with `manifest.json` and a `SHA256SUMS` file;
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
- Callers that pass 90.1 definition IDs must translate them through `id-map.json`.

## 7. Migration stages

Each stage ends with its check passing. Nothing is deleted before stage P3.

1. **P1, assembler.** `programmes.load_recipe` assembles each recipe from the release
   program, its `generation` block, the folder's configuration, `schedules.json` and
   `services.json`. Check: for every packaged recipe, re-keyed by release ID through
   `id-map.json`, the assembled recipe equals the packaged one as JSON. The same check
   applies to services and configurations.
2. **P2, write 2.1.0.** Write the blocks and the `generation.json` files, and amend the ID rule. Checks:
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
   `SHA256SUMS`, then tag `v2.1.0` and `generator-v3.0.0`. Check: a clean install of the
   wheel against the extracted `v2.1.0` archive passes the smoke run.
5. **P5, documents.** The generator page, the amendments in section 9, and the changelog.

## 8. Alternatives considered

- **Keep the recipes beside the programs** (`generator.json`, the status quo). *Rejected:*
  the values are kept twice and can drift, and every value change needs both files
  rewritten.
- **Put the block in the program and hash it.** *Rejected:* every program ID and citing file
  would change again (11,537 IDs in `id-map.json` today) for no value change.
- **Ship release copies inside the generator package.** *Rejected:* about 9 MB duplicated, and
  the generator would pin its own copy of the release.
- **Add `generation` to the Program JSON export now** (5.5.0). *Deferred:* it breaks BEMGen's
  strict 5.4.0 reader, and no consumer needs it yet.

## 9. Amendments (if accepted)

- **ADR 0036 section 3:** the generation part of the recipe is the program's `generation`
  block; building configurations live in each folder's `generation.json`.
- **ADR 0046 section 3, decision 2:** superseded, since the block is outside the ID hash.
- **ADR 0046 section 8:** the program ID rule hashes the program without `id`, `name` and
  `generation`.
- **ADR 0047 section 5:** release 2.1.0 carries the ResStock apartment-unit parameters.

## 10. Recommendations to confirm

1. Requests take release IDs only, with `id-map.json` for translation (section 4).
2. Data and generator get separate GitHub releases and separate tags (section 5).
3. The Program JSON export stays at 5.4.0 until a consumer asks for `generation` (section 4).
