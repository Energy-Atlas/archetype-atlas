# Atlas release 2.5.0 (delta on 2.4.0): release and migration notes

Release 2.5.0 decides each setpoint side from the source equipment and mixes setpoints per side
([ADR 0064](adr/0064-release-2-5-0.md); data and contract [ADR 0063](adr/0063-conditioning-sides-and-per-side-mixes.md);
owner decisions D1b, D2b, D3 and D5 of 2026-11-04). It is a delta on 2.4.0: `data/atlas-releases/v2.5.0` holds only its
own files, and its `manifest.json` names 2.4.0 as `base_release`, with that manifest's SHA-256, and lists the 2.4.0 paths
it removes. Status `released` (2026-11-04).

## What changes for readers

- **Resolve the chain.** Read `v2.0.0`, then lay `v2.1.0` to `v2.5.0` over it, removing each manifest's `removed` paths
  (`scripts.atlas_delta.files('2.5.0')`). `scripts.atlas_exports.Release()`, the generator and the site default to 2.5.0.
- **A setpoint side no source equipment serves is absent** (ADR 0063 sections 2.1 and 2.2). The 90.1 and DOE Ref
  programs take their spaces from the openstudio-standards prototypes, whose HVAC maps say which system serves each
  space; a system type serves the sides its builder makes coils for (a unit heater heats only; a PVAV cools, although
  its map record has no `cooling_type`). 72 source programs have a side no system serves. That side's setpoint is an
  explicit null and `parameters.conditioning` states both sides; Program JSON 6.2.0 gives the null the status
  `not_conditioned` with the systems and the source schedule it replaces (which stays in the evidence and the folder's
  `schedules.json`).

  | Program | Templates | Absent | Was (°C) |
  | --- | --- | --- | --- |
  | Warehouse `Bulk` | 90.1, DOE Ref | cooling | 50; DOE Ref 24 to 30 |
  | Stand-alone retail `Entry` | 90.1, DOE Ref | cooling | 100; DOE Ref 90 |
  | Small hotel `Stair`, `Stair4`, `Mechanical` | 90.1 | cooling | 40 |
  | Small hotel `Stair`, `Storage` | DOE Ref | cooling | 40 |
  | Small hotel `Storage`, `Storage4Front`, `Storage4Rear`, `Laundry` | 90.1 | both (no system) | 7.2 / 40; laundry 21.1 / 23.9 |
  | Midrise apartment `Corridor`, `Corridor_topfloor` | 90.1 | both (no system) | 21.7 / 24.4 |
  | Midrise apartment `Corridor` | DOE Ref | cooling | 40 |
  | Outpatient `Elec/MechRoom`, `ElevatorPumpRoom`, `Janitor`, `Stair`, `Toilet`, `Undeveloped` | DOE Ref | both (no system) | 18.3 to 21.1 / 22.2 to 25 |
  | Courthouse `Parking` | 90.1, DOE Ref | both (no system) | 15.6 to 21 / 24 to 26.7 |
  | Data centres, high and low ITE, large and small | 90.1 | heating (CRAH, CRAC) | 15 |

  The IECC programs already took their sides from the IDF thermostats, which agree with the IDFs' equipment; they do not
  change, and their absent sides now export as `not_conditioned` too (6.1.0: `none`). Unchanged: the 76 programs that
  already had the unconditioned treatment (elevator cores, attics, plenums, shafts), the DOE Ref hospital basement (the
  DOE file serves it, where the openstudio-standards map does not), the DOE Ref outpatient `Utility` (0.361 of its area
  served: left for the owner), and the tall and super-tall buildings (no HVAC map at the pinned revision).
- **Per-side mixes** (section 2.3, amending ADR 0012). Each setpoint side of a mix is averaged over the members that have
  it, with the weights renormalised, and `composition.setpoint_coverage` (Program JSON `controls.setpoint_coverage`)
  gives the represented-area share of those members. 69 mixes have a coverage below 1; 373 keep their setpoints exactly;
  4 (the 90.1-2007 and 2013 tall and super-tall general mixes) have an unknown side. In every template the warehouse
  storage, stand-alone retail general, small-hotel vertical-circulation, support and general mixes change. 90.1-2019:

  | Mix | Heating | Cooling |
  | --- | --- | --- |
  | `warehouse.department.storage-mixed` | 11.69 °C, coverage 1.0 (unchanged) | 26.7 °C, coverage 0.303 (was 42.9 °C) |
  | `retail-standalone.general.general-mixed` | coverage 1.0 | coverage 0.994 (the entry's 100 °C is out) |
  | `small-hotel.department.vertical-circulation-mixed` | coverage 0.781 | none (coverage 0) |
  | `small-hotel.department.support-mixed` | coverage 0.118 | none (coverage 0) |
  | `small-hotel.general.general-mixed` | coverage 0.917 | coverage 0.862 |

- **IDs.** All 446 mixes and the 72 source programs move: `id-map-2.5.0.json` maps the 518 old IDs to the new ones.
- **Contracts.** Program JSON **6.2.0** (`schemas/program-json-v6.2.schema.json`): the null status `not_conditioned`,
  the optional `controls.setpoint_coverage`, and `conditioning_state` stated in the source version where both flags are
  known. The release-record program schema is 1.1.0 (`composition.setpoint_coverage`). Constructions and building
  services are unchanged.
- **Generator.** `atlas-schedules` **4.1.2** (4.1.0's code) bundles the 2.5.0 view; a heated-only programme or mix
  side generates no cooling setpoint.

## Site

The catalogue builds release 2.5.0: 940,091,624 bytes in 30,822 files (under the 1 GB Pages limit). Program pages
show a *Conditioning* fact (for example "heating only (cooling `not_conditioned`: no source equipment serves it)") and
a mix's setpoint coverage.

## Migration

1. Re-key stored 2.4.0 program IDs through `id-map-2.5.0.json`.
2. Read Program JSON 6.2.0; treat a `not_conditioned` null as an absent side, and `controls.setpoint_coverage` as the
   share of a mix's floor area each side covers.
3. Pin `atlas-schedules` 4.1.2 for 2.5.0 IDs.

The BEMGen items are in [`docs/bemgen-handoff-release-2-5-0.md`](bemgen-handoff-release-2-5-0.md).

## Verify

```console
python -m scripts.atlas_delta --verify            # the delta against its manifest and base
python -m scripts.atlas_delta --check             # rebuild 2.5.0 from its inputs; 2,847 views assemble
python -m scripts.conditioning_sides --check      # the conditioning-side input from the pinned openstudio-standards files
python -m scripts.conditioning_sides --review     # the IDF cross-check (needs the prototype IDFs)
```
