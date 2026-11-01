# ADR 0061: Program JSON 6.1.0, the unoccupied lighting cap (release 2.4.0)

Status: accepted (2026-11-01; stage AT4, owner decision G4 of the 2026-10-31 review, round 2: "decide the field shape in
an ADR"). The exporter, schema, tests and guides change together on `main`; exports of release 2.3.0 keep Program JSON
6.0.0, exports of release 2.4.0 on take 6.1.0 (`scripts.atlas_contracts.PROGRAM_BY_RELEASE`). The data is
[ADR 0060](0060-release-2-4-0-pnnl-prototype-corrections.md) section 1.

## 1. The version

| Export | Release 2.3.0 | Release 2.4.0 on | Class |
| --- | --- | --- | --- |
| Program JSON | 6.0.0 | **6.1.0** (`schemas/program-json-v6.1.schema.json`, `urn:archetype-atlas:program-json:6.1.0`) | minor: one new optional field |
| Detailed / unified / source model constructions | 5.0.0 / 4.0.0 / 2.0.0 | unchanged | – |
| Building services | 1.0.1 | 1.0.1 (the release by pattern; the 90.1 folders now export it) | – |

6.1.0 is derived from 6.0.0 (`python -m scripts.atlas_exports --schemas`, `atlas_contracts.program_schema_6_1`) and adds
only `lighting_controls.unoccupied_lighting_cap`; every 6.0.0 field keeps its meaning and every 6.0.0 document other than
its `schema_version` const validates (docs/schema-versioning.md: minor). The schema is revision 1 in
`schemas/revisions.json`. 6.0.0 does not change, and a 2.3.0 export that met the field would be refused.

## 2. The field

```json
"lighting_controls": {
  "status": "known", "source": "pnnl_prototype", "daylighting": {…}, "daylighting_origin": {…},
  "unoccupied_lighting_cap": {
    "rule": {
      "cap_W_m2": 0.21527820833419445, "lighting_threshold_W_m2": 0.21505376344086022,
      "source_values": {"cap": 0.02, "threshold": 0.02, "unit": "W/ft2",
                        "cap_conversion_m2_per_ft2": 0.09290304, "threshold_conversion_m2_per_ft2": 0.093},
      "condition": "zone_occupant_count_zero", "comparison": "zone_lighting_power_density_at_least_threshold",
      "action": "set_lights_to_cap", "calling_point": "BeginTimestepBeforePredictor",
      "zones": 15, "controlled_zones": 15,
      "zone_conditions": [{"zone": "Perimeter_mid_ZN_2", "condition": "((DaylightSavings==0) && …"}]},
    "evidence_id": "evidence-…"}}
```

- **Where**: under `lighting_controls`, beside `daylighting`, on every known block; the exporter gives it on every known
  block of release 2.4.0 on. Unknown blocks and mixes have none (as for daylighting).
- **`rule`**: the rule (`CAP_RULE`: required `cap_W_m2`, `lighting_threshold_W_m2`, `source_values`, `condition`,
  `comparison`, `action`, `calling_point`, `zones`, `controlled_zones`; optional `condition_zone`, required with
  `other_zone_occupant_count_zero`, `zone_conditions`, `additional_lighting_when_capped_W_m2`), or **null** where the
  complete source model has no such rule in the program's zones.
- **The null's reason** is in `nulls`: `/lighting_controls/unoccupied_lighting_cap/rule` has status `none` and the reason
  of the cited evidence row (for example "No PNNL IECC 2018 prototype (16 types x 19 locations) has an unoccupied
  lighting cap program (the medium office header gives LPD_Ctrl = 0): none (a source zero)."). The meanings table
  (`atlas_contracts.NULLS`, printed by the Program JSON guide) gains that row with the record as its source.
- **`evidence_id`** resolves in `source.evidence` (ADR 0054 section 2): the EMS programs as written, or the scan.
- **SI with the source values beside**: the cap and threshold are W/m² of zone floor area; `source_values` keeps the
  W/ft² and the two conversions the EMS program uses (0.09290304 for the cap, 0.093 for the threshold), so a consumer can
  reproduce PNNL's arithmetic exactly.

## 3. Alternatives

- **A flat field, `unoccupied_lighting_cap: null` with a sibling evidence ID.** Rejected: the evidence of a null would sit
  outside the field and outside `cited` (which reads `evidence_id` and `*evidence_ids`); the object keeps rule and
  evidence together, and `rule: null` is still the explicit null with its reason in `nulls`.
- **A per-zone list.** Rejected: the atlas holds programs, not zones (ADR 0044); `zones` and `controlled_zones` say how
  many of the program's source zones carry the rule, and `zone_conditions` names the zones whose program differs.
- **A boolean or the cap value alone.** Rejected: the condition (whose occupant count), the threshold (which differs from
  the cap in the fourth digit) and the calling point are part of the rule, and the owner asked for the condition and the
  comparison on the record.

## 4. What a consumer changes

- Read `schema_version` 6.1.0 (embed the new schema); everything else of 6.0.0 reads as before.
- Where `lighting_controls.unoccupied_lighting_cap.rule` is an object, apply it per zone and timestep: while the occupant
  count of the zone (or of `condition_zone`) is 0 and the zone lighting power per floor area is at least
  `lighting_threshold_W_m2`, set the zone's general lighting to `cap_W_m2` x floor area (and the display lighting to
  `additional_lighting_when_capped_W_m2` where given); honour `zone_conditions` for the named zones. BEMGen applies it
  only to zones whose people are not zero at all times (G4).
- Where it is null, apply nothing; `nulls` says why.
