# Energy Archetype Atlas release 2.5.0 (conditioning sides and per-side mixes, delta on 2.4.0)

A delta release (ADR 0036 section 2, ADR 0064): this folder holds only its own files, and a
reader resolves every other path in `../v2.4.0/`, `../v2.3.0/`, `../v2.2.0/`, `../v2.1.0/` and
then `../v2.0.0/`, whose manifest hashes the chain of `manifest.json` files records. `removed`
lists the 2.4.0 paths this release drops: the old names of the programs whose IDs move.

- Conditioning sides (ADR 0063 section 1): a 90.1 or DOE Ref source program whose source HVAC
  equipment (the openstudio-standards prototype HVAC map, each system type read as its builder
  makes it) serves no heating or no cooling has that setpoint side as an explicit null, and
  `parameters.conditioning` states both sides, citing the systems, the spaces and the replaced
  schedule, which stays in the folder's `schedules.json`. The warehouse bulk storage, the
  stand-alone retail entry and the small-hotel stairs and mechanical room are heated only; the
  90.1 small-hotel storage and laundry are unconditioned (the DOE Ref storage is heated only).
- Per-side mixes (section 2, amending ADR 0012): every mix records
  `composition.setpoint_coverage`, the represented-area share of its members with each side,
  and each side is mixed over the members that have it with the weights renormalised; a side
  no member has is a known null. `warehouse.department.storage-mixed` now cools at the fine
  storage setpoint with cooling coverage 0.303 (90.1), where 2.4.0 averaged 50 degC in.
- `id-map-2.5.0.json`: every 2.4.0 ID that moves, mapped to its 2.5.0 ID (`ids`). The earlier
  maps keep the earlier moves.
- Citing files follow the new IDs: `generation.json`, `services.json`,
  `definition-map.json` and `exporter-inputs.json`.
- `LICENSE` is the MIT License for code and `LICENSE-DATA` the CC BY 4.0 legal code for data
  and documentation; attribute as "Archetype Atlas, Energy-Atlas" with the release number.

Exports of this release take Program JSON 6.2.0 (ADR 0063: the `not_conditioned` null status
and `controls.setpoint_coverage`); constructions 5.0.0, 4.0.0 and 2.0.0 and building services
1.0.1 are unchanged, naming `atlas-release-2.5.0`. The generator (`atlas-schedules` 4.1.2,
whose wheel bundles this release) reads it. Resolve the chain with `python -m scripts.atlas_delta`
(`scripts.atlas_delta.files('2.5.0')`); verify with `--verify`, rebuild and compare with
`--check`. Upstream notices are in 2.0.0's `notices/`.
