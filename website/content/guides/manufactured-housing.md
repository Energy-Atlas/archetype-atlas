# Manufactured-housing prototypes

Release 1.4.0 adds the PNNL manufactured-housing prototypes. The decision record is
ADR 0042.

## Source

304 EnergyPlus 8.0 models from the HUD and FinalRule folders: single-section and
multi-section homes, 19 locations and 4 heating systems. The CompleteSet folders hold
the same files and are only checked by checksum. The models are read offline into
`data/program-inputs/manufactured-housing.json`.

## Templates and programs

| Folder | Standard | Tier |
| --- | --- | --- |
| `residential/hud-code/single-section/` | HUD Code baseline | |
| `residential/hud-code/multi-section/` | HUD Code baseline | |
| `residential/doe-final-rule/single-section/` | DOE Final Rule 2022 | tier 1 |
| `residential/doe-final-rule/multi-section/` | DOE Final Rule 2022 | tier 2 |

Each folder has one program: the loads agree across heating systems and locations.
The two templates' programs differ only in their hot-water draw schedules.

- Lighting and plug loads keep the source basis, W/m² of floor area. The program
  records the dwelling floor area: 85.9 m² single-section, 145.7 m² multi-section.
- People, exterior lighting and hot-water draws are per dwelling.

## Construction sets

One per template and section type, with a context per location:

- one per climate zone (`1-a`, `4-a`, `7`, …);
- for 3A, one per city: `3-a.atlanta`, `3-a.birmingham`, `3-a.charleston`,
  `3-a.jackson`, `3-a.memphis`.

Each context holds the assemblies, windows, doors, internal mass, window shading
control and the source effective leakage areas of the living zone and the attic and
crawlspace vents.

## Gap

The set has no existing-building category. Existing manufactured homes appear only
as the three ResStock fixture dwellings under `residential/resstock-sdr/manufactured-home/`.
