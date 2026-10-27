# IECC residential prototypes

Release 1.4.0 adds the PNNL IECC residential prototypes, editions 2006, 2009, 2012,
2015, 2018, 2021 and 2024. The decision record is ADR 0041.

## Source

4,144 EnergyPlus 23.1 models: single-family and multifamily, 19 climate codes (18 for
multifamily), 4 heating systems, 4 foundations and 7 editions. They are read offline
into `data/program-inputs/iecc-residential-<edition>.json`; the release is built from
those files.

The source codes with suffixes get their own climate label in the release. WH is a
warm-humid location, T a tropical location, S the semi-conditioned tropical design
(half the living space unconditioned, solar water heating). Use the label as `climate`;
the other codes keep their names.

| Source code | Climate label | Zone | Location | Warm-humid | Tropical | Design |
| --- | --- | --- | --- | --- | --- | --- |
| 1AWH | `1A-warm-humid` | 1A | Miami | yes | no | standard |
| 1AWHT | `1A-tropical` | 1A | Honolulu | yes | yes | standard |
| 1AWHTS | `1A-tropical-semi-conditioned` | 1A | Honolulu | yes | yes | tropical semi-conditioned |
| 2AWH | `2A-warm-humid` | 2A | Tampa | yes | no | standard |
| 3AWH | `3A-warm-humid` | 3A | Montgomery | yes | no | standard |

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
- **`1A-tropical-semi-conditioned`.** The unconditioned living zone's lighting and
  adjustment loads are building services that apply with that climate.

## Construction sets

One per edition and type, with one context per climate and foundation
(`4-a.slab`, `1-a-tropical-semi-conditioned.heatedbsmt`, …): assemblies by surface class with layer-only
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
