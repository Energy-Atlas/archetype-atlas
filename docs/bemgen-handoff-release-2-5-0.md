# BEMGen handoff: atlas release 2.5.0 (conditioning sides and per-side mixes)

What BEMGen receives when it moves to atlas release 2.5.0 ([ADR 0064](adr/0064-release-2-5-0.md)), and the exact fields
it reads. The data and contract are [ADR 0063](adr/0063-conditioning-sides-and-per-side-mixes.md) (owner decisions D1b,
D2b, D3, D5 of 2026-11-04). BEMGen's own part is D1c (the plausibility warning) and D4d (merging with a judged per-side
change in conditioned area), with its ADR-041.

## 1. Versions and IDs

| Item | Release 2.4.0 | Release 2.5.0 |
| --- | --- | --- |
| Release label (`source.release`) | `atlas-release-2.4.0` | `atlas-release-2.5.0` |
| Program JSON | 6.1.0 | **6.2.0**, `urn:archetype-atlas:program-json:6.2.0`, `schemas/program-json-v6.2.schema.json` |
| Constructions, building services | 5.0.0 / 4.0.0 / 2.0.0, 1.0.1 | unchanged |
| Generator | `atlas-schedules` 4.1.1 | **4.1.2** (4.1.0's code; the wheel bundles the 2.5.0 view) |
| ID map | `id-map-2.4.0.json` | **`id-map-2.5.0.json`**: 518 IDs (72 source programs, all 446 mixes) |

- [ ] Re-key every stored 2.4.0 program ID through `id-map-2.5.0.json` (`ids`: old to new). No construction set or
  service ID moves.
- [ ] Embed the 6.2.0 schema. Every 6.1.0 field keeps its meaning; 6.2.0 adds one null status and one optional field.

## 2. A side no source equipment serves (source programs)

**What changed.** 72 90.1 and DOE Ref source programs have a setpoint side that no system of the prototype serves (the
openstudio-standards HVAC map, each system type read as its builder makes it). The IECC programs already had their sides
from the IDF thermostats and do not change; their absent sides now carry the same status.

**Fields BEMGen reads** (Program JSON 6.2.0, both versions unless noted):

- `controls.heating_enabled`, `controls.cooling_enabled`: booleans. In the **source** version they were null for 90.1
  and DOE Ref programs; they are now `true`/`false` on every program whose record states its sides (the 72, the IECC
  programs, every mix whose sides are known). Elsewhere they stay null and the filled version resolves them, as before.
- `controls.conditioning_state`: `heating_and_cooling`, `heating_only`, `cooling_only` or `unconditioned`. The source
  version now states it wherever both flags are known (6.1.0 always wrote `unknown` there).
- `controls.heating_setpoint_schedule_id` / `cooling_setpoint_schedule_id`: **null** for an absent side in the source
  version; **absent** (the key is not there) in the filled version, as for any disabled side.
- `nulls["/controls/cooling_setpoint_schedule_id"]` (or heating): `{"status": "not_conditioned", "reason": "…"}`; the
  reason names the systems and the replaced source schedule. `not_conditioned` is the new status value.

90.1-2019 warehouse bulk storage, source version (`90-1-2019.warehouse.source.bulk.b043c0`):

```json
"controls": {"heating_enabled": true, "cooling_enabled": false, "conditioning_state": "heating_only",
             "heating_setpoint_schedule_id": "90-1-2019.warehouse.warehouse-bulk-storage-heating-setpoint-schedule.2e9879",
             "cooling_setpoint_schedule_id": null, ...},
"nulls": {"/controls/cooling_setpoint_schedule_id": {"status": "not_conditioned",
  "reason": "Bulk (1 source space): served by UnitHeater, 2 x Zone Ventilation in ASHRAEWarehouse.json; no cooling equipment. A side no equipment serves is not conditioned, whatever setpoint the space type gives it (ADR 0063). The setpoint of each side with no equipment is an explicit null; the source thermostat schedule stays in the evidence and in the folder schedules: cooling (source schedule 'Warehouse ClgSetp BulkStorage', 50.0 degC)."}}
```

Filled version: `{"heating_enabled": true, "cooling_enabled": false, "conditioning_state": "heating_only",
"heating_setpoint_schedule_id": "…2e9879"}`. The 90.1-2019 small-hotel storage (`90-1-2019.small-hotel.source.storage.6e5e98`)
is `unconditioned`: both setpoints null (source) or absent (filled), both `not_conditioned`.

- [ ] Read a `not_conditioned` side as absent: no thermostat side, so ADR-018 writes `SingleHeating` for a heated-only
  zone, and no thermostat at all for an unconditioned one. Do not substitute a default setpoint.
- [ ] Keep the source schedule out of the model: it is evidence only (`source.evidence[*].original_value
  .replaced_schedules`).

## 3. Mixes: per-side setpoints and coverage

**What changed.** Every mix averages each setpoint side over the members that have it, with the weights renormalised,
and records the represented-area share of those members. 373 mixes have coverage 1 on both sides (their setpoints are
unchanged), 69 have a lower coverage, and 4 (the 90.1-2007 and 2013 tall and super-tall general mixes) have an unknown
side.

**Fields BEMGen reads:**

- `controls.setpoint_coverage`: `{"heating": number or null, "cooling": number or null}`, each in [0, 1]; mixes only.
  0 means no member has the side: its setpoint is null (source) or absent (filled), status `not_conditioned`. null
  means a member's side is unknown (`nulls["/controls/setpoint_coverage/heating"]`, status `unknown`).
- `controls.heating_enabled` / `cooling_enabled` of a mix: `true` where the coverage is above 0.
- The setpoint schedules: the per-side mix; where the coverage is 1 they are the 2.4.0 schedules, unchanged.

90.1-2019 warehouse storage mix, source version (`90-1-2019.warehouse.department.storage-mixed.bfa555`; 2.4.0 ID
`…storage-mixed.05aa51`):

```json
"controls": {"heating_enabled": true, "cooling_enabled": true, "conditioning_state": "heating_and_cooling",
             "heating_setpoint_schedule_id": "90-1-2019.warehouse.storage-mixed-heating-setpoint.98c1b8",
             "cooling_setpoint_schedule_id": "90-1-2019.warehouse.storage-mixed-cooling-setpoint.b72a75",
             "setpoint_coverage": {"cooling": 0.30303030303030376, "heating": 1.0}, ...}
```

The heating schedule is unchanged (11.685 °C); the cooling schedule is the fine storage's 26.7 °C (2.4.0: 42.94 °C).
The 90.1-2019 small-hotel support mix (`…support-mixed.1ec515`) is `heating_only` with
`{"heating": 0.11817853953501062, "cooling": 0.0}`.

- [ ] Show or log each mix's coverage; under D4d, compare the per-side conditioned area of a zoning with the reference's.
- [ ] A Mix Programs picker that mixes member exports itself applies the same rule: per side, over the members whose
  side is not `not_conditioned`, weights `A_i / Σ A_j` of those members.

## 4. The LOD prototypes (90.1-2007 and 90.1-2019)

Every program of the warehouse, stand-alone retail and small hotel whose sides or coverage changed (all other programs of
those folders keep their sides; mixes with full coverage only move their ID):

| Template | Program | 2.5.0 ID | 2.4.0 ID | heating | cooling |
| --- | --- | --- | --- | --- | --- |
| 90.1-2007 | `General_Mixed_RetailStandalone` | `90-1-2007.retail-standalone.general.general-mixed.b9fee5` | `90-1-2007.retail-standalone.general.general-mixed.d75c9a` | coverage 1.0000 | coverage 0.9937 |
| 90.1-2007 | `Entry_RetailStandalone` | `90-1-2007.retail-standalone.source.entry.ed8db2` | `90-1-2007.retail-standalone.source.entry.12144e` | yes | **not_conditioned** |
| 90.1-2007 | `Support_Mixed_SmallHotel` | `90-1-2007.small-hotel.department.support-mixed.8b31f3` | `90-1-2007.small-hotel.department.support-mixed.3ebd36` | coverage 0.1182 | coverage 0.0000 |
| 90.1-2007 | `VerticalCirculation_Mixed_SmallHotel` | `90-1-2007.small-hotel.department.vertical-circulation-mixed.6dc34f` | `90-1-2007.small-hotel.department.vertical-circulation-mixed.56cf00` | coverage 0.7805 | coverage 0.0000 |
| 90.1-2007 | `General_Mixed_SmallHotel` | `90-1-2007.small-hotel.general.general-mixed.5086ec` | `90-1-2007.small-hotel.general.general-mixed.5b6fd3` | coverage 0.9173 | coverage 0.8619 |
| 90.1-2007 | `Laundry_SmallHotel` | `90-1-2007.small-hotel.source.laundry.40acd2` | `90-1-2007.small-hotel.source.laundry.7346e6` | **not_conditioned** | **not_conditioned** |
| 90.1-2007 | `Mechanical_SmallHotel` | `90-1-2007.small-hotel.source.mechanical.52cff4` | `90-1-2007.small-hotel.source.mechanical.92c78c` | yes | **not_conditioned** |
| 90.1-2007 | `Stair_SmallHotel` | `90-1-2007.small-hotel.source.stair.18b004` | `90-1-2007.small-hotel.source.stair.3c009f` | yes | **not_conditioned** |
| 90.1-2007 | `Stair4_SmallHotel` | `90-1-2007.small-hotel.source.stair4.8f8fab` | `90-1-2007.small-hotel.source.stair4.3592ef` | yes | **not_conditioned** |
| 90.1-2007 | `Storage_SmallHotel` | `90-1-2007.small-hotel.source.storage.a22714` | `90-1-2007.small-hotel.source.storage.95520c` | **not_conditioned** | **not_conditioned** |
| 90.1-2007 | `Storage4Front_SmallHotel` | `90-1-2007.small-hotel.source.storage4-front.0cd692` | `90-1-2007.small-hotel.source.storage4-front.ac854c` | **not_conditioned** | **not_conditioned** |
| 90.1-2007 | `Storage4Rear_SmallHotel` | `90-1-2007.small-hotel.source.storage4-rear.4bd05c` | `90-1-2007.small-hotel.source.storage4-rear.e4e4e5` | **not_conditioned** | **not_conditioned** |
| 90.1-2007 | `Storage_Mixed_Warehouse` | `90-1-2007.warehouse.department.storage-mixed.72dad5` | `90-1-2007.warehouse.department.storage-mixed.d163ac` | coverage 1.0000 | coverage 0.3030 |
| 90.1-2007 | `Bulk_Warehouse` | `90-1-2007.warehouse.source.bulk.ee09d3` | `90-1-2007.warehouse.source.bulk.3c5618` | yes | **not_conditioned** |
| 90.1-2019 | `General_Mixed_RetailStandalone` | `90-1-2019.retail-standalone.general.general-mixed.9c28b1` | `90-1-2019.retail-standalone.general.general-mixed.d95322` | coverage 1.0000 | coverage 0.9937 |
| 90.1-2019 | `Entry_RetailStandalone` | `90-1-2019.retail-standalone.source.entry.11866b` | `90-1-2019.retail-standalone.source.entry.3a7f41` | yes | **not_conditioned** |
| 90.1-2019 | `Support_Mixed_SmallHotel` | `90-1-2019.small-hotel.department.support-mixed.1ec515` | `90-1-2019.small-hotel.department.support-mixed.a9148f` | coverage 0.1182 | coverage 0.0000 |
| 90.1-2019 | `VerticalCirculation_Mixed_SmallHotel` | `90-1-2019.small-hotel.department.vertical-circulation-mixed.58433d` | `90-1-2019.small-hotel.department.vertical-circulation-mixed.a59d4b` | coverage 0.7805 | coverage 0.0000 |
| 90.1-2019 | `General_Mixed_SmallHotel` | `90-1-2019.small-hotel.general.general-mixed.85e817` | `90-1-2019.small-hotel.general.general-mixed.c17f51` | coverage 0.9173 | coverage 0.8619 |
| 90.1-2019 | `Laundry_SmallHotel` | `90-1-2019.small-hotel.source.laundry.c97ffb` | `90-1-2019.small-hotel.source.laundry.a3af6a` | **not_conditioned** | **not_conditioned** |
| 90.1-2019 | `Mechanical_SmallHotel` | `90-1-2019.small-hotel.source.mechanical.48774b` | `90-1-2019.small-hotel.source.mechanical.dc8de9` | yes | **not_conditioned** |
| 90.1-2019 | `Stair_SmallHotel` | `90-1-2019.small-hotel.source.stair.6783d8` | `90-1-2019.small-hotel.source.stair.91e6ad` | yes | **not_conditioned** |
| 90.1-2019 | `Stair4_SmallHotel` | `90-1-2019.small-hotel.source.stair4.b880f7` | `90-1-2019.small-hotel.source.stair4.1bf4ca` | yes | **not_conditioned** |
| 90.1-2019 | `Storage_SmallHotel` | `90-1-2019.small-hotel.source.storage.6e5e98` | `90-1-2019.small-hotel.source.storage.00720b` | **not_conditioned** | **not_conditioned** |
| 90.1-2019 | `Storage4Front_SmallHotel` | `90-1-2019.small-hotel.source.storage4-front.750209` | `90-1-2019.small-hotel.source.storage4-front.728423` | **not_conditioned** | **not_conditioned** |
| 90.1-2019 | `Storage4Rear_SmallHotel` | `90-1-2019.small-hotel.source.storage4-rear.b126d6` | `90-1-2019.small-hotel.source.storage4-rear.eebf1b` | **not_conditioned** | **not_conditioned** |
| 90.1-2019 | `Storage_Mixed_Warehouse` | `90-1-2019.warehouse.department.storage-mixed.bfa555` | `90-1-2019.warehouse.department.storage-mixed.05aa51` | coverage 1.0000 | coverage 0.3030 |
| 90.1-2019 | `Bulk_Warehouse` | `90-1-2019.warehouse.source.bulk.b043c0` | `90-1-2019.warehouse.source.bulk.39f8eb` | yes | **not_conditioned** |

## 5. The generator

`atlas-schedules` 4.1.2 is 4.1.0's code. It already reads a known null setpoint as no slot and averages setpoints over the
members that have them (`atlas_schedules.mixtures._setpoints`), so a heated-only programme or mix side generates no
`cooling_setpoint` schedule and a mix's cooling setpoint is the fine storage's.

- [ ] Pin `atlas-schedules` 4.1.2 and re-key requests through `id-map-2.5.0.json`.

## 6. What is not in this release

- The DOE Ref outpatient `Utility` program (only 0.361 of its area served) is unchanged, for the owner.
- The tall and super-tall buildings have no HVAC map at the pinned revision; unchanged.
- No coverage threshold withholds a mix; the over-conditioning a low coverage implies is BEMGen's D4d metric.
- `data/lod-recommendations/` is the next stage's (LOD drop 6).
