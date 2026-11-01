# Energy Archetype Atlas release 2.4.0 (PNNL prototype corrections, delta on 2.3.0)

A delta release (ADR 0036 section 2, ADR 0062): this folder holds only its own files, and a
reader resolves every other path in `../v2.3.0/`, `../v2.2.0/`, `../v2.1.0/` and then
`../v2.0.0/`, whose manifest hashes the chain of `manifest.json` files records. `removed`
lists the 2.3.0 paths this release drops: the old names of the programs whose IDs move.

- Unoccupied lighting cap (ADR 0060 section 1): every known `lighting_controls` block gains
  `unoccupied_lighting_cap` with `rule` and `evidence_id`. The rule is PNNL's per-zone EMS
  program of the 90.1-2019 prototypes (zone occupant count 0 and lighting at least 0.02 W/ft2:
  lights set to 0.02 W/ft2) on 19 programs of the offices, restaurants, retail types and the
  warehouse; `rule` is null, a source zero with its reason, on the 1,875 others, whose source
  models were read and carry no such program (90.1-2007, 90.1-2013, the other 90.1-2019
  types, IECC 2006 to 2021, the DOE reference models).
- Office lighting power follows PNNL (section 2): the 11 whole-building office programs of
  the 90.1-2007, 2013 and 2019 folders take the prototype `Lights` density, with evidence
  citing the IDF and the replaced value (90.1-2013 rises 16 to 24 percent, 90.1-2007 and 2019
  move between -4 and +8 percent).
- Elevators and kitchen reach-ins (section 3): 84 PNNL 90.1 objects become building services
  of 36 folders, as the IECC and DOE Ref families store them.
- `id-map-2.4.0.json`: every 2.3.0 ID that moves (2,301 programs), mapped to its 2.4.0 ID
  (`ids`). The 2.3.0 and 2.0.0 maps keep the earlier moves.
- Citing files follow the new IDs: `generation.json`, `services.json`,
  `definition-map.json` and `exporter-inputs.json`.
- `LICENSE` is the MIT License for code and `LICENSE-DATA` the CC BY 4.0 legal code for data
  and documentation; attribute as "Archetype Atlas, Energy-Atlas" with the release number.

Exports of this release take Program JSON 6.1.0 (ADR 0061: the cap field); constructions
5.0.0, 4.0.0 and 2.0.0 and building services 1.0.1 are unchanged, naming
`atlas-release-2.4.0`. The generator (`atlas-schedules` 4.1.1, whose wheel bundles this
release) reads it. Resolve the chain with `python -m scripts.atlas_delta`
(`scripts.atlas_delta.files('2.4.0')`); verify with `--verify`, rebuild and compare with
`--check`. Upstream notices are in 2.0.0's `notices/`.
