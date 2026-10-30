# Energy Archetype Atlas release 2.2.0 (generation parameters, delta on 2.1.0)

A delta release (ADR 0036 section 2, ADR 0051): this folder holds only its own files, and a
reader resolves every other path in `../v2.1.0/` and then `../v2.0.0/`, whose manifest hashes
the chain of `manifest.json` files records. It publishes the stochastic schedule generator's
parameters with the programs and removes each folder's `generator.json`; no program,
schedule, service or construction value changes, and no ID moves (the program ID rule leaves
`generation` out).

- `<family>/<template>/<building type>/generation.json`: the folder's program `generation`
  blocks (method and, per view, the parameters the record cannot give), its services'
  blocks and its building configurations. A program reads with its block as `generation`.
- `definition-map.json`: each definition program ID generator 3.0.0 took, with its release
  program and view (`values`), and each definition service ID with its release service.

The generator (`atlas-schedules` 4.0.0 on, ADR 0051) assembles its recipes from this release;
Program JSON 5.4.0 exports name `atlas-release-2.2.0`. Resolve the chain with
`python -m scripts.atlas_delta` (`scripts.atlas_delta.files('2.2.0')`); verify with `--verify`,
rebuild and compare with `--check`. Upstream notices are in 2.0.0's `notices/`; original Atlas
data is CC BY 4.0 (see `LICENSE`).
