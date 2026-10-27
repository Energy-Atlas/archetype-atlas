# Atlas release 1.6.0 (commercial and residential, delta): release and migration notes

Release 1.6.0 is a delta on release 1.0.0 (ADR 0036), like 1.1.0 to 1.5.0. It holds
everything 1.5.0 changed and adds the unified constructions of the IECC commercial
family ([ADR 0045](adr/0045-iecc-unified-constructions.md), stage U).

## What changes

- The 96 IECC construction sets (6 editions × 16 types, 19 contexts each) and their
  template libraries. Every other file equals release 1.5.0's, except `README.md` and
  `manifest.json`.
- Each of the 1,824 IECC contexts holds a building-level equivalent instead of the
  `deferred` stub. All are `ready`.
- The manifest no longer lists the IECC unified representation as deferred.

## How the equivalents are made

- **Weights:** the net surface area of each component entry in the source IDF
  (`data/program-inputs/iecc-unified-areas-v1.json`, from `python -m
  scripts.iecc_unified`). Base surfaces lose their windows and doors; every area is
  multiplied by its subsurface and zone multipliers.
- **Physics:** the 90.1 sets' own equivalence code. Opaque components are fitted to
  a two-mass, one-resistance form that keeps U and heat capacity; glazing becomes an
  area-weighted proxy, or keeps its layers where they are identical.
- **Ground:** F- and C-factor ground floors and walls keep their native assemblies
  and ground methods.
- **Mass:** `InternalMass` comes from the source internal-mass objects,
  `FloorDistributedMass` from the interior floor inventory. The mass accounting,
  foundation methods and design-flow infiltration equal the detailed document's.
- **Adiabatic F-factor floors:** 570 contexts have core-zone floors that PNNL models as
  adiabatic with an F-factor construction. They have no layers, so they are left out of
  the fits and listed in `provenance.excluded_ground_constructions`.

## Exports

```
python -m scripts.atlas_exports --release 1.6.0 --construction <IECC set id> --context 5-a --representation unified
```

IECC unified contexts export as construction-equivalent 3.1.0, and programs as
Program JSON 5.4.0, as in release 1.5.0. The Program JSON 5.1.0, 5.2.0 and 5.4.0,
building services and source model constructions schemas add `atlas-release-1.6.0`
to their release enums.

## Verify

```
python -m scripts.atlas_minor_release --release 1.6.0 --verify
python -m scripts.atlas_minor_release --release 1.6.0 --check
python -m scripts.iecc_unified --check        # needs the extracted IECC IDFs
python -m unittest tests.test_iecc_unified
```

## Open decisions

ADR 0045 section 5: whether release 2.0.0 moves the 90.1 recipe IDs to the same
interpreter-independent hashing.
