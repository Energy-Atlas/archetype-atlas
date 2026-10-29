# Energy Archetype Atlas release 2.1.0 (generation parameters, delta on 2.0.0)

A delta on release 2.0.0 (ADR 0049): this folder holds only its own files, and a reader
resolves every other path in `../v2.0.0/`, whose manifest hash `manifest.json` records.
It adds the stochastic schedule generator's parameters to the programs and retires each
folder's `generator.json`; no program, schedule, service or construction value changes, and
no ID moves (the program ID rule leaves `generation` out).

- `<family>/<template>/<building type>/generation.json`: the folder's program `generation`
  blocks (method and, per view, the parameters the record cannot give), its services'
  blocks and its building configurations. A program reads with its block as `generation`.
- `definition-map.json`: each definition program ID the generator took before this release,
  with its release program and view (`values`), and each definition service ID with its
  release service.

The generator (`atlas_schedules`, generator 3.0.0) reads this release beside its base.
Program JSON exports stay those of 2.0.0. Write and check with
`python -m scripts.release_2_1_0 [--check]`. Upstream notices are in `../v2.0.0/notices/`;
original Atlas data is CC BY 4.0 (see `LICENSE`).
