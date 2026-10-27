# Atlas release 1.5.0 (commercial and residential, delta): release and migration notes

Release 1.5.0 is a delta on release 1.0.0 (ADR 0036), like 1.1.0 to 1.4.0. It holds
everything 1.4.0 changed and adds, under [ADR 0044](adr/0044-lighting-controls.md):

- the lighting controls of the source models, on every commercial program (stage L);
- programs for the 90 plenums release 1.2.0 left unmapped (stage G1).

## What the release holds

- `data/atlas-releases/v1.5.0/`, written and verified by
  `scripts.atlas_minor_release --release 1.5.0`.
- Every commercial program ID changes, because IDs hash program content and every
  leaf program gains `lighting_controls`. The residential tree is unchanged.

## Lighting controls

Each commercial source program and reviewed twin has a `lighting_controls` block;
mixes have none.

| Templates | Source | What the block holds |
| --- | --- | --- |
| IECC 2006, 2009 | IECC prototypes | `daylighting: null` (no controls in the models) |
| IECC 2012 | IECC prototypes | controls in 7 programs (skylit gyms, retail, warehouses); null elsewhere |
| IECC 2015, 2018, 2021 | IECC prototypes | controls in 37–38 programs per edition |
| 90.1-2007 | PNNL 90.1 prototypes | `daylighting: null`, plus the openstudio-standards space-type inputs |
| 90.1-2013, 2019 | PNNL 90.1 prototypes | controls in 38 programs each, plus the openstudio-standards inputs |
| DOE Ref Pre-1980, 1980-2004 | DOE reference models | `daylighting: null` (no DOE model has controls) |
| Types without a prototype | — | `status: unknown` with the reason |

- **Fields:** controlled floor fraction, controlled lighting-power fraction,
  illuminance setpoint (lux), control type (`continuous`, `stepped`,
  `continuous_off`), method, availability, minimum input-power and light-output
  fractions, stepped-control steps, and the zone counts.
- **By climate:** 17 records differ in zones 6A, 6B, 7A and 8A, where the prototypes
  have smaller skylights; they are in `daylighting_by_climate`.
- **Geometry:** the fractions hold for the prototype geometry
  (`geometry_dependent: true`). With other geometry, recompute them.
- **Occupancy sensors:** their credits are already inside the lighting schedules and
  are not repeated.
- **Dwellings:** no residential or manufactured-housing model has daylighting
  controls; dwelling programs carry no block.

## Plenum programs

The 90 spaces of the tall and super-tall buildings, the detailed offices and the
laboratory that had no standards row take the template's Any/Plenum row
(`sources/plenum-aliases.json`, one reason per entry). That adds a plenum program and
its reviewed twin to 19 folders. The spaces do not count toward floor area, so no mix
changes. The filled twins have no occupancy, lighting or hot water and are
unconditioned, as the 1.0.0 office plenums are. Release 1.2.0's known gap "unmapped
spaces" is closed.

## Exports

- **Program JSON 5.4.0** (`schemas/program-json-v5.4.schema.json`), an additive minor
  of 5.3.0 with `lighting_controls`, for every program of the release, dwellings
  included.
- The 5.1.0, 5.2.0, building services and source model constructions schemas add
  `atlas-release-1.5.0` to their release enums.

```
python -m scripts.atlas_exports --release 1.5.0 --program <id> --version source
```

## Verify

```
python -m scripts.atlas_minor_release --release 1.5.0 --verify
python -m scripts.atlas_minor_release --release 1.5.0 --check
python -m scripts.plenum_aliases --check
python -m scripts.lighting_controls --check      # needs the extracted prototypes and DOE IDFs
python -m unittest tests.test_lighting_controls
```

## Open decisions

ADR 0044 section 5: whether the 90.1 daylit fractions become plain values, and
whether to fetch the openstudio-standards template rules to check them.
