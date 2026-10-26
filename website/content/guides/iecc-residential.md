# IECC residential prototypes

Release 1.4.0 adds the PNNL IECC residential prototypes, editions 2006, 2009, 2012,
2015, 2018, 2021 and 2024. The decision record is ADR 0041.

## Source

4,144 EnergyPlus 23.1 models: single-family and multifamily, 19 climate codes (18 for
multifamily), 4 heating systems, 4 foundations and 7 editions. They are read offline
into `data/program-inputs/iecc-residential-<edition>.json`; the release is built from
those files.

| Climate code | Meaning (agent reading of the models) |
| --- | --- |
| 1AWH, 2AWH, 3AWH | warm-humid location (Miami, Tampa, Montgomery) |
| 1AWHT | tropical location (Honolulu), same building as 1AWH |
| 1AWHTS | tropical semi-conditioned design: half the living space unconditioned, solar water heating |

## Programs

`residential/iecc-<edition>/{single-family,multifamily}/` holds one program per
appliance fuel:

- **gas appliances:** gas furnace homes (gas range, dryer and miscellaneous loads);
- **electric appliances:** electric resistance, heat pump and oil furnace homes.

An entry that holds only for some climate codes, foundations or heating systems
carries `applies_with`, for example `{"foundation": ["heatedbsmt"]}` for the
heated basement's lighting. Keep the entries whose conditions hold for your case:

```python
from scripts.atlas_exports import Release
from scripts.prototype_dwellings import document
release = Release(release='1.4.0')
program_id = next(p for p in release.dwellings.program_ids() if p.startswith('iecc-2021.single-family.gas-appliances.'))
dwelling = document(release.dwellings, program_id, 'source',
                    {'climate': '4A', 'foundation': 'slab', 'heating': 'gasfurnace'})
```

- **IECC adjustment.** `IECC_Adj` loads are their own quantities with
  `role: reference_design_adjustment`.
- **Host zones.** Every load names its source zone (`living`, `garage`, `attic`,
  `heatedbsmt`, `breezeway`, `uncond_living`, `exterior`).
- **Multifamily** is one program per dwelling unit; the 18 units have identical
  loads. Loads in the heated basement are building services, instantiated once.
- **1AWHTS.** The unconditioned living zone's lighting and adjustment loads are
  building services that apply with that climate code.

## Construction sets

One per edition and type, with one context per climate code and foundation
(`4-a.slab`, `1-awhts.heatedbsmt`, …): assemblies by surface class with layer-only
U-factors, windows (U-factor, SHGC), doors, internal mass, window shading control and
the source infiltration method (AirflowNetwork leakage for single-family, effective
leakage area per unit for multifamily). Export one context as source model
constructions 1.0.0:

```
python -m scripts.atlas_exports --release 1.4.0 --construction <set id> --context 4-a.slab
```

## Not included

HVAC, water heaters and solar water heating (systems are not stored for residential
families), and the unified construction representation.
