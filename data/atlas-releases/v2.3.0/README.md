# Energy Archetype Atlas release 2.3.0 (data corrections and generation coverage, delta on 2.2.0)

A delta release (ADR 0036 section 2, ADR 0059): this folder holds only its own files, and a
reader resolves every other path in `../v2.2.0/`, `../v2.1.0/` and then `../v2.0.0/`, whose
manifest hashes the chain of `manifest.json` files records. `removed` lists the 2.2.0 paths
this release drops: the old names of the records whose IDs move.

- Record corrections (ADR 0053): the unified `InternalMass` of eight DOE Ref building-scope
  construction sets counts their whole additional-mass inventory; the 90.1 small-hotel
  elevator takes the PNNL prototype value, and its support mixes follow; every unknown
  commercial load carries its reason, and the ADR 0016 accepted absence is a stored filling;
  same-named records take the name of their source distinction. Program and set IDs follow
  their rules: 1,550 programs and 12 construction sets have new IDs, and every citing file
  follows, `generation.json` and `definition-map.json` included.
- `id-map-2.3.0.json`: every 2.2.0 ID that moves, mapped to its 2.3.0 ID (`ids`). The
  2.0.0 `id-map.json` keeps the map into 2.0.0.
- `<family>/<template>/<building type>/generation.json` of the IECC commercial and detailed
  office folders (ADR 0055), new, and of the 2.2.0 folders whose programs moved.
- `LICENSE` is the MIT License for code and `LICENSE-DATA` the CC BY 4.0 legal code for data
  and documentation; attribute as "Archetype Atlas, Energy-Atlas" with the release number.

Exports of this release follow new contracts (ADR 0054): Program JSON 6.0.0, detailed
constructions 5.0.0, unified constructions 4.0.0, source-model constructions 2.0.0 and
building services 1.0.1, naming `atlas-release-2.3.0`. The generator (`atlas-schedules`
4.1.0) reads it. Resolve the chain with `python -m scripts.atlas_delta`
(`scripts.atlas_delta.files('2.3.0')`); verify with `--verify`, rebuild and compare with
`--check`. Upstream notices are in 2.0.0's `notices/`.
