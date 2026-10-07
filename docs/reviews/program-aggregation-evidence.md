# Source-area evidence for program aggregation

Inspection date: 2026-10-06. Companion to the editable [decision matrix](program-aggregation-matrix.md).
Status: **source inspection; numerical area evidence, not released mixed energy presets**.

## What this inventory contains

- All 768 commercial program records in atlas `v0.2.0`, organized into 171 building/source-space-label combinations across 17 building types.
- 83 selected building/template contexts using 34 distinct geometry files, each verified against its locked SHA-256.
- Calculable counted-floor-area shares for all 83 contexts. The earlier 16 unresolved contexts are now resolved using the matching OpenStudio 2.2.1 source default, with the original blank fields preserved as evidence.
- Five commercial templates kept separate. No averaging of templates, stock variants or source families.
- ResStock has 41 separate dwelling fixtures in this release. They are not commercial room programs and have no extracted internal room-area composition. Keep these dwelling bundles separate from the selected commercial apartment family; no internal room aggregation is inferred.

The commercial tables are OpenStudio Standards source inputs and geometry implementations. Their relationship to ComStock is upstream lineage, not proof that each table reproduces a particular ComStock generated model or its current ratio rules. Equivalence to independently downloaded DOE/PNNL IDFs has not been established.

## Reading the tables

| Column / marker | Meaning |
| --- | --- |
| E-pre | DOE Ref Pre-1980, existing-stock benchmark family |
| E-post | DOE Ref 1980-2004, existing-stock benchmark family |
| C07 / C13 / C19 | ASHRAE 90.1-2007 / 2013 / 2019, code/prototype rules family |
| Numeric cell | Percent of the counted floor area of that exact source building/template; three-decimal inspection rounding |
| NC | Source spaces are explicitly outside counted floor area; not zero energy or absent space |
| U | Reserved for an unresolved denominator; none remain after the documented source-default check |
| — | This source program or building context is absent in the frozen selection; not a zero share |

A whole-building fraction is not a target-program recipe weight. For the approved member subset with areas A_i, its internal weights are A_i / sum(A_i). Use the decision matrix for actual membership. The source tables retain basement/attic shares for provenance, but every approved mixture excludes those programs and renormalizes over its eligible members. Basement/attic presets remain optional and separate. A building-wide PACU or corridor area need not all belong to a selected department.
Variant names such as top-floor, occupied/vacant, or tenant type do not by themselves establish subordinate uses that should be blended. Keep alternatives explicit.

## Method and provenance

Original values: source `OS:Surface` Floor vertex X/Y/Z tuples in metres, `OS:Space` Part of Total Floor Area Yes/No or blank flags, exact standards building/space tags on `OS:SpaceType`, and `OS:ThermalZone` dimensionless multipliers. Blank flags are interpreted only through the matching versioned source rule below; raw files are unchanged.
Source locator for each table cell: the listed geometry file and all `OS:Space` objects whose linked `OS:SpaceType` exactly matches the row's Standards Building Type and Standards Space Type; join their `OS:Surface` floors through Space Name/handle and their thermal zones through Thermal Zone Name/handle. A plenum without a building tag uses the extractor's explicit `Any` convention. The exact source file revision and SHA-256 are in the lock table below.
Transformation: sum planar floor polygon areas using the full XYZ coordinates, multiply each unique space's zone multiplier once, include effective Yes spaces (explicit or source-defaulted), group by exact source tags, and divide by the sum over all effective Yes spaces in the selected model. HVAC mappings are not summed; the same space can have multiple HVAC services. Use unrounded areas to compute any eventual recipe.
Interpretation: source-model benchmark composition only, not a required architectural ratio, population weight, BEMGen plan geometry, or claim of weather-independent controls. Different templates may reuse a geometry file while having different energy semantics.
Validation on 2026-10-06: 34 file checksums passed; all 768 program records matched their source tags; no explicitly counted space was left without a canonical program. Positive counted-space areas and multipliers were checked. Unrounded grouped areas equaled each of the 83 complete building denominators within relative tolerance 1e-10. Rounding may leave displayed totals slightly different from 100%.

Reproduce from the repository root with `python -m docs.reviews.tools.extract_program_area_evidence` then `python -m docs.reviews.tools.render_program_area_evidence`. Retrieve the geometry locks with `python -m scripts.fetch` first if the cache is absent. The extractor verifies/fetches the [matching SDK defaults](source-default-lock.json) through checksum-locked retrieval. The calculation uses the existing [floor-polygon reader](../../scripts/water_reporting.py) and [tagged space reader](../../scripts/semantics.py). Raw downloads remain immutable. No canonical table or delivery packet was changed.

Canonical energy inputs and IDs for a cell can be found in [programs.json](../../data/releases/v0.2.0/programs.json) by exact `building_type`, `template`, `source_building_type`, and `source_space_type`. Source field locators, original energy values/units and transformations are in [provenance.json](../../data/releases/v0.2.0/provenance.json). This is the source view; a reviewed supplemental view must be chosen explicitly for a final recipe.

Input file checksums for this inspection:

| Input | SHA-256 |
| --- | --- |
| [data/releases/v0.2.0/programs.json](../../data/releases/v0.2.0/programs.json) | `71076176fda99b940873fafce8a4bc89a4a72dad903b780b887e3d7d57173d92` |
| [data/releases/v0.2.0/source_files.json](../../data/releases/v0.2.0/source_files.json) | `6cbd647d922a2722d28c714a29cc42cae22a04946c7889f0c20000dc358311df` |
| [sources/selection.json](../../sources/selection.json) | `34e6bef5973411bfb450b8885e3ca1d3360eeac7727f4ab58ba6b5041dd67e8e` |

## Building/program inventory

### FullServiceRestaurant

| Exact source space type | Standards Building Type | E-pre % | E-post % | C07 % | C13 % | C19 % |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `Attic` | `FullServiceRestaurant` | — | NC | NC | NC | NC |
| `Dining` | `FullServiceRestaurant` | 72.727 | 72.727 | 72.727 | 72.727 | 72.727 |
| `Kitchen` | `FullServiceRestaurant` | 27.273 | 27.273 | 27.273 | 27.273 | 27.273 |

| Context | Geometry lock | Counted building floor area, m² |
| --- | --- | ---: |
| E-pre | G27 | 511.153316 |
| E-post | G09 | 511.153316 |
| C07 | G09 | 511.153316 |
| C13 | G09 | 511.153316 |
| C19 | G09 | 511.153316 |

### HighriseApartment

| Exact source space type | Standards Building Type | E-pre % | E-post % | C07 % | C13 % | C19 % |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `Apartment` | `HighriseApartment` | — | — | 79.955 | 79.955 | 79.955 |
| `Apartment_topfloor_NS` | `HighriseApartment` | — | — | 4.505 | 4.505 | 4.505 |
| `Apartment_topfloor_WE` | `HighriseApartment` | — | — | 4.505 | 4.505 | 4.505 |
| `Corridor` | `HighriseApartment` | — | — | 8.919 | 8.919 | 8.919 |
| `Corridor_topfloor` | `HighriseApartment` | — | — | 0.991 | 0.991 | 0.991 |
| `Office` | `HighriseApartment` | — | — | 1.126 | 1.126 | 1.126 |

| Context | Geometry lock | Counted building floor area, m² |
| --- | --- | ---: |
| C07 | G10 | 7836.479192 |
| C13 | G10 | 7836.479192 |
| C19 | G10 | 7836.479192 |

### Hospital

| Exact source space type | Standards Building Type | E-pre % | E-post % | C07 % | C13 % | C19 % |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `Basement` | `Hospital` | 16.667 | 16.667 | 16.667 | 16.667 | 16.667 |
| `Corridor` | `Hospital` | 17.412 | 17.412 | 17.412 | 17.412 | 17.412 |
| `Dining` | `Hospital` | 3.106 | 3.106 | 3.106 | 3.106 | 3.106 |
| `ER_Exam` | `Hospital` | 0.994 | 0.994 | 0.994 | 0.994 | 0.994 |
| `ER_NurseStn` | `Hospital` | 5.507 | 5.507 | 5.507 | 5.507 | 5.507 |
| `ER_Trauma` | `Hospital` | 0.248 | 0.248 | 0.248 | 0.248 | 0.248 |
| `ER_Triage` | `Hospital` | 0.497 | 0.497 | 0.497 | 0.497 | 0.497 |
| `HospitalOfficeFlr1` | `Hospital` | — | — | — | 0.311 | 0.311 |
| `HospitalOfficeFlr5` | `Hospital` | — | — | — | 2.546 | 2.546 |
| `ICU_NurseStn` | `Hospital` | 2.981 | 2.981 | 2.981 | 2.981 | 2.981 |
| `ICU_Open` | `Hospital` | 2.754 | 2.754 | 2.754 | 2.754 | 2.754 |
| `ICU_PatRm` | `Hospital` | 1.149 | 1.149 | 1.149 | 1.149 | 1.149 |
| `Kitchen` | `Hospital` | 4.141 | 4.141 | 4.141 | 4.141 | 4.141 |
| `Lab` | `Hospital` | 2.360 | 2.360 | 2.360 | 2.360 | 2.360 |
| `Lobby` | `Hospital` | 6.573 | 6.573 | 6.573 | 6.573 | 6.573 |
| `NurseStn` | `Hospital` | 17.226 | 17.226 | 17.226 | 17.226 | 17.226 |
| `OR` | `Hospital` | 2.733 | 2.733 | 2.733 | 2.733 | 2.733 |
| `Office` | `Hospital` | 2.857 | 2.857 | 2.857 | — | — |
| `PatRoom` | `Hospital` | 8.448 | 8.448 | 8.448 | 8.448 | 8.448 |
| `PhysTherapy` | `Hospital` | 2.174 | 2.174 | 2.174 | 2.174 | 2.174 |
| `Radiology` | `Hospital` | 2.174 | 2.174 | 2.174 | 2.174 | 2.174 |

| Context | Geometry lock | Counted building floor area, m² |
| --- | --- | ---: |
| E-pre | G11 | 22436.084160 |
| E-post | G11 | 22436.084160 |
| C07 | G11 | 22436.084160 |
| C13 | G04 | 22436.084160 |
| C19 | G04 | 22436.084160 |

### LargeHotel

| Exact source space type | Standards Building Type | E-pre % | E-post % | C07 % | C13 % | C19 % |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `Banquet` | `LargeHotel` | 5.847 | 5.847 | 5.847 | 5.847 | 5.847 |
| `Basement` | `LargeHotel` | 17.442 | 17.442 | 17.442 | 17.442 | 17.442 |
| `Cafe` | `LargeHotel` | 1.665 | 1.665 | 1.665 | 1.665 | 1.665 |
| `Corridor` | `LargeHotel` | 3.633 | 3.633 | 3.633 | 3.633 | 3.633 |
| `Corridor2` | `LargeHotel` | 13.729 | 13.729 | 13.729 | 13.729 | 13.729 |
| `GuestRoom` | `LargeHotel` | 5.503 | 5.503 | 5.503 | 5.503 | 5.503 |
| `GuestRoom2` | `LargeHotel` | 32.861 | 32.861 | 16.433 | 16.433 | 16.433 |
| `GuestRoom3` | `LargeHotel` | 0.688 | 0.688 | 0.688 | 0.688 | 0.688 |
| `GuestRoom4` | `LargeHotel` | 1.946 | 1.946 | 1.946 | 1.946 | 1.946 |
| `GuestRoom8` | `LargeHotel` | — | — | 16.428 | 16.428 | 16.428 |
| `Kitchen` | `LargeHotel` | 0.911 | 0.911 | 0.911 | 0.911 | 0.911 |
| `Laundry` | `LargeHotel` | 0.688 | 0.688 | 0.688 | 0.688 | 0.688 |
| `Lobby` | `LargeHotel` | 11.531 | 11.531 | 11.531 | 11.531 | 11.531 |
| `Mechanical` | `LargeHotel` | 1.448 | 1.448 | 1.448 | 1.448 | 1.448 |
| `Retail` | `LargeHotel` | 0.591 | 0.591 | 0.591 | 0.591 | 0.591 |
| `Retail2` | `LargeHotel` | 0.685 | 0.685 | 0.685 | 0.685 | 0.685 |
| `Storage` | `LargeHotel` | 0.835 | 0.835 | 0.835 | 0.835 | 0.835 |

| Context | Geometry lock | Counted building floor area, m² |
| --- | --- | ---: |
| E-pre | G24 | 11345.286931 |
| E-post | G24 | 11345.286931 |
| C07 | G12 | 11345.286931 |
| C13 | G12 | 11345.286931 |
| C19 | G12 | 11345.286931 |

### LargeOffice

| Exact source space type | Standards Building Type | E-pre % | E-post % | C07 % | C13 % | C19 % |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `OfficeLarge Data Center` | `Office` | — | — | 0.938 | 0.938 | 0.938 |
| `OfficeLarge Main Data Center` | `Office` | — | — | 1.692 | 1.692 | 1.692 |
| `Plenum` | `Any` | NC | NC | NC | NC | NC |
| `WholeBuilding - Lg Office` | `Office` | 100.000 | 100.000 | 97.370 | — | — |
| `WholeBuilding - Lg Office-basement` | `Office` | — | — | — | 6.000 | 6.000 |
| `WholeBuilding - Lg Office-others` | `Office` | — | — | — | 91.370 | 91.370 |

| Context | Geometry lock | Counted building floor area, m² |
| --- | --- | ---: |
| E-pre | G25 | 46320.378316 |
| E-post | G25 | 46320.378316 |
| C07 | G13 | 46320.378316 |
| C13 | G05 | 46320.378316 |
| C19 | G05 | 46320.378316 |

### MediumOffice

| Exact source space type | Standards Building Type | E-pre % | E-post % | C07 % | C13 % | C19 % |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `Plenum` | `Any` | NC | NC | NC | NC | NC |
| `WholeBuilding - Md Office` | `Office` | 100.000 | 100.000 | 100.000 | 100.000 | 100.000 |

| Context | Geometry lock | Counted building floor area, m² |
| --- | --- | ---: |
| E-pre | G14 | 4982.185895 |
| E-post | G14 | 4982.185895 |
| C07 | G14 | 4982.185895 |
| C13 | G14 | 4982.185895 |
| C19 | G14 | 4982.185895 |

### MidriseApartment

| Exact source space type | Standards Building Type | E-pre % | E-post % | C07 % | C13 % | C19 % |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `Apartment` | `MidriseApartment` | 87.275 | 87.275 | 64.752 | 64.752 | 64.752 |
| `Apartment_topfloor_NS` | `MidriseApartment` | — | — | 11.261 | 11.261 | 11.261 |
| `Apartment_topfloor_WE` | `MidriseApartment` | — | — | 11.261 | 11.261 | 11.261 |
| `Corridor` | `MidriseApartment` | 9.910 | 9.910 | 7.432 | 7.432 | 7.432 |
| `Corridor_topfloor` | `MidriseApartment` | — | — | 2.477 | 2.477 | 2.477 |
| `Office` | `MidriseApartment` | 2.815 | 2.815 | 2.815 | 2.815 | 2.815 |

| Context | Geometry lock | Counted building floor area, m² |
| --- | --- | ---: |
| E-pre | G26 | 3134.591677 |
| E-post | G26 | 3134.591677 |
| C07 | G15 | 3134.591677 |
| C13 | G15 | 3134.591677 |
| C19 | G15 | 3134.591677 |

### Outpatient

| Exact source space type | Standards Building Type | E-pre % | E-post % | C07 % | C13 % | C19 % |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `Anesthesia` | `Outpatient` | 0.264 | 0.264 | 0.264 | 0.264 | 0.264 |
| `BioHazard` | `Outpatient` | 0.137 | 0.137 | 0.137 | 0.137 | 0.137 |
| `Cafe` | `Outpatient` | 1.026 | 1.026 | 1.026 | 1.026 | 1.026 |
| `CleanWork` | `Outpatient` | 0.711 | 0.711 | 0.711 | 0.711 | 0.711 |
| `Conference` | `Outpatient` | 0.821 | 0.821 | 0.821 | 0.821 | 0.821 |
| `DressingRoom` | `Outpatient` | 0.212 | 0.212 | 0.212 | 0.212 | 0.212 |
| `Elec/MechRoom` | `Outpatient` | 1.094 | 1.094 | 1.094 | 1.094 | 1.094 |
| `ElevatorPumpRoom` | `Outpatient` | 0.222 | 0.222 | 0.222 | 0.222 | 0.222 |
| `Exam` | `Outpatient` | 10.289 | 10.289 | 10.289 | 10.289 | 10.289 |
| `Hall` | `Outpatient` | 15.022 | 15.022 | 15.022 | 15.022 | 15.022 |
| `Hall_infil` | `Outpatient` | 4.220 | 4.220 | 4.220 | 4.220 | 4.220 |
| `IT_Room` | `Outpatient` | 0.274 | 0.274 | 0.274 | 0.274 | 0.274 |
| `Janitor` | `Outpatient` | 6.721 | 6.721 | 6.721 | 6.721 | 6.721 |
| `Lobby` | `Outpatient` | 1.519 | 1.519 | 1.519 | 1.519 | 1.519 |
| `LockerRoom` | `Outpatient` | 1.905 | 1.905 | 1.905 | 1.905 | 1.905 |
| `Lounge` | `Outpatient` | 2.928 | 2.928 | 2.928 | 2.928 | 2.928 |
| `MRI` | `Outpatient` | 1.075 | 1.075 | 1.075 | 1.075 | 1.075 |
| `MRI_Control` | `Outpatient` | 0.410 | 0.410 | 0.410 | 0.410 | 0.410 |
| `MedGas` | `Outpatient` | 0.137 | 0.137 | 0.137 | 0.137 | 0.137 |
| `NurseStation` | `Outpatient` | 1.888 | 1.888 | 1.888 | 1.888 | 1.888 |
| `OR` | `Outpatient` | 3.458 | 3.458 | 3.458 | 3.458 | 3.458 |
| `Office` | `Outpatient` | 18.283 | 18.283 | 18.283 | 14.155 | 14.155 |
| `OutpatientFloor2Work` | `Outpatient` | — | — | — | 4.127 | 4.127 |
| `PACU` | `Outpatient` | 2.315 | 2.315 | 2.315 | 2.315 | 2.315 |
| `PhysicalTherapy` | `Outpatient` | 4.621 | 4.621 | 4.621 | 4.621 | 4.621 |
| `PreOp` | `Outpatient` | 1.287 | 1.287 | 1.287 | 1.287 | 1.287 |
| `ProcedureRoom` | `Outpatient` | 0.696 | 0.696 | 0.696 | 0.696 | 0.696 |
| `Reception` | `Outpatient` | 3.646 | 3.646 | 3.646 | 3.646 | 3.646 |
| `Soil Work` | `Outpatient` | 0.884 | 0.884 | 0.884 | 0.884 | 0.884 |
| `Stair` | `Outpatient` | 1.456 | 1.456 | 1.456 | 1.456 | 1.456 |
| `Toilet` | `Outpatient` | 1.929 | 1.929 | 1.929 | 1.929 | 1.929 |
| `Undeveloped` | `Outpatient` | 8.352 | 8.352 | 8.352 | 8.352 | 8.352 |
| `Xray` | `Outpatient` | 2.198 | 2.198 | 2.198 | 2.198 | 2.198 |

| Context | Geometry lock | Counted building floor area, m² |
| --- | --- | ---: |
| E-pre | G16 | 3804.007876 |
| E-post | G16 | 3804.007876 |
| C07 | G16 | 3804.007876 |
| C13 | G06 | 3804.007876 |
| C19 | G06 | 3804.007876 |

### PrimarySchool

| Exact source space type | Standards Building Type | E-pre % | E-post % | C07 % | C13 % | C19 % |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `Cafeteria` | `PrimarySchool` | 4.584 | 4.584 | 4.584 | 4.584 | 4.584 |
| `Classroom` | `PrimarySchool` | 56.105 | 56.105 | 47.941 | 47.941 | 47.941 |
| `ComputerRoom` | `PrimarySchool` | — | — | 2.358 | 2.358 | 2.358 |
| `Corridor` | `PrimarySchool` | 16.330 | 16.330 | 16.330 | 16.330 | 16.330 |
| `Gym` | `PrimarySchool` | 5.196 | 5.196 | 5.196 | 5.196 | 5.196 |
| `Kitchen` | `PrimarySchool` | 2.445 | 2.445 | 2.445 | 2.445 | 2.445 |
| `Library` | `PrimarySchool` | — | — | 5.807 | 5.807 | 5.807 |
| `Lobby` | `PrimarySchool` | 2.489 | 2.489 | 2.489 | 2.489 | 2.489 |
| `Mechanical` | `PrimarySchool` | 3.668 | 3.668 | 3.668 | 3.668 | 3.668 |
| `Office` | `PrimarySchool` | 6.418 | 6.418 | 6.418 | 6.418 | 6.418 |
| `Restroom` | `PrimarySchool` | 2.765 | 2.765 | 2.765 | 2.765 | 2.765 |

| Context | Geometry lock | Counted building floor area, m² |
| --- | --- | ---: |
| E-pre | G30 | 6871.000000 |
| E-post | G30 | 6871.000000 |
| C07 | G17 | 6871.000000 |
| C13 | G17 | 6871.000000 |
| C19 | G17 | 6871.000000 |

### QuickServiceRestaurant

| Exact source space type | Standards Building Type | E-pre % | E-post % | C07 % | C13 % | C19 % |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `Attic` | `QuickServiceRestaurant` | — | NC | NC | NC | NC |
| `Dining` | `QuickServiceRestaurant` | 50.000 | 50.000 | 50.000 | 50.000 | 50.000 |
| `Kitchen` | `QuickServiceRestaurant` | 50.000 | 50.000 | 50.000 | 50.000 | 50.000 |

| Context | Geometry lock | Counted building floor area, m² |
| --- | --- | ---: |
| E-pre | G28 | 232.342952 |
| E-post | G18 | 232.342952 |
| C07 | G18 | 232.342952 |
| C13 | G18 | 232.342952 |
| C19 | G18 | 232.342952 |

### RetailStandalone

| Exact source space type | Standards Building Type | E-pre % | E-post % | C07 % | C13 % | C19 % |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `Back_Space` | `Retail` | 16.560 | 16.560 | 16.560 | 16.560 | 16.560 |
| `Core_Retail` | `Retail` | — | — | — | 69.768 | 69.768 |
| `Entry` | `Retail` | 0.523 | 0.523 | 0.523 | 0.523 | 0.523 |
| `Front_Retail` | `Retail` | — | — | — | 6.574 | 6.574 |
| `Point_of_Sale` | `Retail` | 6.574 | 6.574 | 6.574 | 6.574 | 6.574 |
| `Retail` | `Retail` | 76.343 | 76.343 | 76.343 | — | — |

| Context | Geometry lock | Counted building floor area, m² |
| --- | --- | ---: |
| E-pre | G31 | 2293.992900 |
| E-post | G31 | 2293.992900 |
| C07 | G01 | 2293.992900 |
| C13 | G07 | 2293.992900 |
| C19 | G07 | 2293.992900 |

### RetailStripmall

| Exact source space type | Standards Building Type | E-pre % | E-post % | C07 % | C13 % | C19 % |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `Strip mall - type 1` | `StripMall` | 25.000 | 25.000 | 25.000 | 25.000 | 25.000 |
| `Strip mall - type 2` | `StripMall` | 25.000 | 25.000 | 25.000 | 25.000 | 25.000 |
| `Strip mall - type 3` | `StripMall` | 50.000 | 50.000 | 50.000 | 50.000 | 50.000 |

| Context | Geometry lock | Counted building floor area, m² |
| --- | --- | ---: |
| E-pre | G19 | 2090.318400 |
| E-post | G19 | 2090.318400 |
| C07 | G19 | 2090.318400 |
| C13 | G19 | 2090.318400 |
| C19 | G19 | 2090.318400 |

### SecondarySchool

| Exact source space type | Standards Building Type | E-pre % | E-post % | C07 % | C13 % | C19 % |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `Auditorium` | `SecondarySchool` | 5.043 | 5.043 | 5.043 | 5.043 | 5.043 |
| `Cafeteria` | `SecondarySchool` | 3.185 | 3.185 | 3.185 | 3.185 | 3.185 |
| `Classroom` | `SecondarySchool` | 35.280 | 35.280 | 30.410 | 30.410 | 30.410 |
| `ComputerRoom` | `SecondarySchool` | — | — | 4.869 | 4.869 | 4.869 |
| `Corridor` | `SecondarySchool` | 21.437 | 21.437 | 21.437 | 21.437 | 21.437 |
| `Gym` | `SecondarySchool` | 10.086 | 10.086 | 16.456 | 16.456 | 16.456 |
| `Gym - audience` | `SecondarySchool` | 6.370 | 6.370 | — | — | — |
| `Kitchen` | `SecondarySchool` | 1.102 | 1.102 | 1.102 | 1.102 | 1.102 |
| `Library` | `SecondarySchool` | 4.287 | 4.287 | 4.287 | 4.287 | 4.287 |
| `Lobby` | `SecondarySchool` | 2.144 | 2.144 | 2.144 | 2.144 | 2.144 |
| `Mechanical` | `SecondarySchool` | 3.491 | 3.491 | 3.491 | 3.491 | 3.491 |
| `Office` | `SecondarySchool` | 5.431 | 5.431 | 5.431 | 5.431 | 5.431 |
| `Restroom` | `SecondarySchool` | 2.144 | 2.144 | 2.144 | 2.144 | 2.144 |

| Context | Geometry lock | Counted building floor area, m² |
| --- | --- | ---: |
| E-pre | G32 | 19592.000000 |
| E-post | G32 | 19592.000000 |
| C07 | G20 | 19592.000000 |
| C13 | G20 | 19592.000000 |
| C19 | G20 | 19592.000000 |

### SmallHotel

| Exact source space type | Standards Building Type | E-pre % | E-post % | C07 % | C13 % | C19 % |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `Attic` | `SmallHotel` | NC | NC | — | — | — |
| `Corridor` | `SmallHotel` | 13.125 | 13.125 | 10.000 | 10.000 | 10.000 |
| `Corridor4` | `SmallHotel` | — | — | 3.125 | 3.125 | 3.125 |
| `Elec/MechRoom` | `SmallHotel` | 0.375 | 0.375 | 0.375 | 0.375 | 0.375 |
| `ElevatorCore` | `SmallHotel` | 1.125 | 1.125 | 0.750 | 0.750 | 0.750 |
| `ElevatorCore4` | `SmallHotel` | — | — | 0.375 | 0.375 | 0.375 |
| `Exercise` | `SmallHotel` | 0.812 | 0.812 | 0.812 | 0.812 | 0.812 |
| `GuestLounge` | `SmallHotel` | 4.063 | 4.063 | 4.063 | 4.063 | 4.063 |
| `GuestRoom` | `SmallHotel` | 63.125 | 63.125 | — | — | — |
| `GuestRoom123Occ` | `SmallHotel` | — | — | 28.625 | 28.625 | 28.625 |
| `GuestRoom123Vac` | `SmallHotel` | — | — | 14.813 | 14.813 | 14.813 |
| `GuestRoom4Occ` | `SmallHotel` | — | — | 12.187 | 12.187 | 12.187 |
| `GuestRoom4Vac` | `SmallHotel` | — | — | 7.500 | 7.500 | 7.500 |
| `Laundry` | `SmallHotel` | 2.437 | 2.437 | 2.437 | 2.437 | 2.437 |
| `Mechanical` | `SmallHotel` | 0.813 | 0.813 | 0.813 | 0.813 | 0.813 |
| `Meeting` | `SmallHotel` | 2.000 | 2.000 | 2.000 | 2.000 | 2.000 |
| `Office` | `SmallHotel` | 3.250 | 3.250 | 3.250 | 3.250 | 3.250 |
| `PublicRestroom` | `SmallHotel` | 0.813 | 0.813 | 0.813 | 0.813 | 0.813 |
| `StaffLounge` | `SmallHotel` | 0.812 | 0.812 | 0.812 | 0.812 | 0.812 |
| `Stair` | `SmallHotel` | 4.000 | 4.000 | 3.000 | 3.000 | 3.000 |
| `Stair4` | `SmallHotel` | — | — | 1.000 | 1.000 | 1.000 |
| `Storage` | `SmallHotel` | 3.250 | 3.250 | 2.438 | 2.438 | 2.438 |
| `Storage4Front` | `SmallHotel` | — | — | 0.312 | 0.312 | 0.312 |
| `Storage4Rear` | `SmallHotel` | — | — | 0.500 | 0.500 | 0.500 |

| Context | Geometry lock | Counted building floor area, m² |
| --- | --- | ---: |
| E-pre | G33 | 4013.586894 |
| E-post | G33 | 4013.586894 |
| C07 | G21 | 4013.582212 |
| C13 | G21 | 4013.582212 |
| C19 | G21 | 4013.582212 |

### SmallOffice

| Exact source space type | Standards Building Type | E-pre % | E-post % | C07 % | C13 % | C19 % |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `Attic` | `Office` | — | NC | NC | NC | NC |
| `WholeBuilding - Sm Office` | `Office` | 100.000 | 100.000 | 100.000 | 100.000 | 100.000 |

| Context | Geometry lock | Counted building floor area, m² |
| --- | --- | ---: |
| E-pre | G29 | 511.157400 |
| E-post | G22 | 511.157400 |
| C07 | G22 | 511.157400 |
| C13 | G22 | 511.157400 |
| C19 | G22 | 511.157400 |

### SuperMarket

| Exact source space type | Standards Building Type | E-pre % | E-post % | C07 % | C13 % | C19 % |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `Bakery` | `SuperMarket` | 5.000 | 5.000 | 5.000 | 5.000 | 5.000 |
| `Corridor` | `SuperMarket` | 1.182 | 1.182 | 1.182 | 1.182 | 1.182 |
| `Deli` | `SuperMarket` | 5.375 | 5.375 | 5.375 | 5.375 | 5.375 |
| `Dining` | `SuperMarket` | 1.111 | 1.111 | 1.111 | 1.111 | 1.111 |
| `DryStorage` | `SuperMarket` | 10.098 | 10.098 | 10.098 | 10.098 | 10.098 |
| `Elec/MechRoom` | `SuperMarket` | 1.333 | 1.333 | 1.333 | 1.333 | 1.333 |
| `Meeting` | `SuperMarket` | 1.111 | 1.111 | 1.111 | 1.111 | 1.111 |
| `Office` | `SuperMarket` | 0.666 | 0.666 | 0.666 | 0.666 | 0.666 |
| `Produce` | `SuperMarket` | 17.015 | 17.015 | 17.015 | 17.015 | 17.015 |
| `Restroom` | `SuperMarket` | 1.500 | 1.500 | 1.500 | 1.500 | 1.500 |
| `Sales` | `SuperMarket` | 54.943 | 54.943 | 54.943 | 54.943 | 54.943 |
| `Vestibule` | `SuperMarket` | 0.667 | 0.667 | 0.667 | 0.667 | 0.667 |

| Context | Geometry lock | Counted building floor area, m² |
| --- | --- | ---: |
| E-pre | G23 | 4180.838688 |
| E-post | G23 | 4180.838688 |
| C07 | G23 | 4180.838688 |
| C13 | G08 | 4180.838688 |
| C19 | G08 | 4180.838688 |

### Warehouse

| Exact source space type | Standards Building Type | E-pre % | E-post % | C07 % | C13 % | C19 % |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `Bulk` | `Warehouse` | 66.282 | 66.282 | 66.282 | 66.282 | 66.282 |
| `Fine` | `Warehouse` | 28.818 | 28.818 | 28.818 | 28.818 | 28.818 |
| `Office` | `Warehouse` | 4.899 | 4.899 | 4.899 | 4.899 | 4.899 |

| Context | Geometry lock | Counted building floor area, m² |
| --- | --- | ---: |
| E-pre | G34 | 4835.128518 |
| E-post | G34 | 4835.128518 |
| C07 | G02 | 4835.131610 |
| C13 | G03 | 4835.131610 |
| C19 | G03 | 4835.131610 |

## Resolved floor-area defaults

The previous U markers were an extraction limitation, not proof that geometry or usable area shares were missing. All seven affected OSM files declare version 2.2.1. At OpenStudio revision `0a5e9cec3f9e57872c44b1e074e9a625cfd9531b` (v2.2.1), the model IDD defaults Part of Total Floor Area to Yes. Space.cpp applies that default to a blank field unless the thermal zone is a supply/return plenum. ThermalZone.cpp defines that exception by actual plenum connections, not by an architectural room name. No supply/return plenum objects exist in the seven affected geometry files; explicit No fields are still excluded. Thus all previously blank fields in these files resolve to Yes. This is a source-defined default, not an empirical area assumption.

| Matching source rule | SHA-256 |
| --- | --- |
| [openstudiocore/src/model/Space.cpp](https://github.com/NatLabRockies/OpenStudio/blob/0a5e9cec3f9e57872c44b1e074e9a625cfd9531b/openstudiocore/src/model/Space.cpp) | `37da9563a1eb8d6006dd0f4d631d098aaaa8b14df6c6c19f403f609b0d250854` |
| [openstudiocore/src/model/ThermalZone.cpp](https://github.com/NatLabRockies/OpenStudio/blob/0a5e9cec3f9e57872c44b1e074e9a625cfd9531b/openstudiocore/src/model/ThermalZone.cpp) | `ee55c0d8c8fd2b81fca33dfd4e481b621272d6a01b693237d13fad5f7c64d637` |
| [openstudiocore/resources/model/OpenStudio.idd](https://github.com/NatLabRockies/OpenStudio/blob/0a5e9cec3f9e57872c44b1e074e9a625cfd9531b/openstudiocore/resources/model/OpenStudio.idd) | `05fd80c0a33a8b3526485284d0262a2bb824930583f6b7c5ce19544d734c8f91` |

## Geometry source locks

All files below come from OpenStudio Standards revision `c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907`. Source license notices are retained in [the source notice](../../sources/licenses/openstudio-standards.txt). The links locate original source values; local raw caches are retrieval artifacts, not new delivery files.

| Lock | Pinned source geometry | SHA-256 |
| --- | --- | --- |
| G01 | [data/geometry/ASHRAE90120042007RetailStandalone.osm](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/data/geometry/ASHRAE90120042007RetailStandalone.osm) | `0522ce179e88b70a0e39ac17b9d29f4f12a6b04fa7b8496ea9a1f3ad0d1212af` |
| G02 | [data/geometry/ASHRAE90120042007Warehouse.osm](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/data/geometry/ASHRAE90120042007Warehouse.osm) | `35145a4a2ed767787a4ed7ff2237496a8539d9f0610f651c8cafbcee8c3cb356` |
| G03 | [data/geometry/ASHRAE90120102013Warehouse.osm](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/data/geometry/ASHRAE90120102013Warehouse.osm) | `5ea56a3bd8917b524bff407892ff62468d32957d78bae7d092522b617e770f9e` |
| G04 | [data/geometry/ASHRAE9012013Hospital.osm](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/data/geometry/ASHRAE9012013Hospital.osm) | `89667d8fdac0fe186c43ce93db3508deef8902cbb5f3b18376eb8226fffef7b0` |
| G05 | [data/geometry/ASHRAE9012013LargeOffice.osm](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/data/geometry/ASHRAE9012013LargeOffice.osm) | `8bb930526e0eeb6acdd90ec66d1da1a12b16d2ec1d3225516731b3fd87e6efc5` |
| G06 | [data/geometry/ASHRAE9012013Outpatient.osm](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/data/geometry/ASHRAE9012013Outpatient.osm) | `ca4e56c0374712f363a6231ece2428e7c87fd6884d728f27bb1bd6ce52b50db6` |
| G07 | [data/geometry/ASHRAE9012013RetailStandalone.osm](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/data/geometry/ASHRAE9012013RetailStandalone.osm) | `a08a6503588b40d9c19f169cad7599468298eddf67cfdb613a8983b8431b8b04` |
| G08 | [data/geometry/ASHRAE9012013SuperMarket.osm](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/data/geometry/ASHRAE9012013SuperMarket.osm) | `5f7cefefd1ca68b02b8b2020bd8c2bb7f5f0355649076f961ead03b5503ec01c` |
| G09 | [data/geometry/ASHRAEFullServiceRestaurant.osm](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/data/geometry/ASHRAEFullServiceRestaurant.osm) | `35a57a86dd71fab46b094ff694a287eeffd8fbdf4f4ae5a91da8c4ad4338dbfc` |
| G10 | [data/geometry/ASHRAEHighriseApartment.osm](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/data/geometry/ASHRAEHighriseApartment.osm) | `9ab8dfa44829b3e083af898832527f2c4bee0a20e20f365e8f402a9bc1245a5d` |
| G11 | [data/geometry/ASHRAEHospital.osm](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/data/geometry/ASHRAEHospital.osm) | `464c07c6e760aabeb5aad365c33bdb074c07af5fd661adceb4bb83b5409834d1` |
| G12 | [data/geometry/ASHRAELargeHotel.osm](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/data/geometry/ASHRAELargeHotel.osm) | `55a972daba1ae81aff56aed578ef31541773eb98fbf55c19122ee1d346221f7b` |
| G13 | [data/geometry/ASHRAELargeOffice.osm](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/data/geometry/ASHRAELargeOffice.osm) | `ccd617112331bea5a8a083e057fe7d1825ee822145bbbf52fef3e4cf6ccf01f8` |
| G14 | [data/geometry/ASHRAEMediumOffice.osm](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/data/geometry/ASHRAEMediumOffice.osm) | `abec0be3271d24904a0d8d6135b63872df4df0c04d0629a75e8a4e11c3785a90` |
| G15 | [data/geometry/ASHRAEMidriseApartment.osm](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/data/geometry/ASHRAEMidriseApartment.osm) | `0fb375dfbd5a84e94965c00ac5143d2102ce395dea87e1f6168c41f1826150d9` |
| G16 | [data/geometry/ASHRAEOutpatient.osm](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/data/geometry/ASHRAEOutpatient.osm) | `01d3fa77f1c50f17f4de07105f8ddd50640e2366bf0be1a4391778b7c4eae7b1` |
| G17 | [data/geometry/ASHRAEPrimarySchool.osm](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/data/geometry/ASHRAEPrimarySchool.osm) | `b8150a866114eba7050e4da2a7d7d7d7c8875ea8db9101166e8fb79243a726b0` |
| G18 | [data/geometry/ASHRAEQuickServiceRestaurant.osm](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/data/geometry/ASHRAEQuickServiceRestaurant.osm) | `2b391a75d0f46ab47eff693993b7c5e7af46b3f1a0364be990db63ac22380961` |
| G19 | [data/geometry/ASHRAERetailStripmall.osm](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/data/geometry/ASHRAERetailStripmall.osm) | `614eabad49a412aa2967fbe121e4c5bbaa3b4af0788407d8cc3f6317bd155d31` |
| G20 | [data/geometry/ASHRAESecondarySchool.osm](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/data/geometry/ASHRAESecondarySchool.osm) | `7da882eb71a12472bb85b7638d87e3d0af750bddae7478d55f10392a7bb2e3ce` |
| G21 | [data/geometry/ASHRAESmallHotel.osm](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/data/geometry/ASHRAESmallHotel.osm) | `f385c599147793c431337c245dc0c6aa256121b89e1448c762b32ff5312a2cf6` |
| G22 | [data/geometry/ASHRAESmallOffice.osm](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/data/geometry/ASHRAESmallOffice.osm) | `0dd8bfd4e266230863f9299b40e981a939d5e7621d602ab6e444662cda0193e7` |
| G23 | [data/geometry/ASHRAESuperMarket.osm](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/data/geometry/ASHRAESuperMarket.osm) | `de97588620d4b71d5fe9719de6817d0ecc8b9a660cc837e5c6d73c144ce32c80` |
| G24 | [data/geometry/DOERefLargeHotel.osm](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/data/geometry/DOERefLargeHotel.osm) | `f9222bfe252991c8d1603aeb4484d113940f4bfea73ebbe20e436b14bb612e03` |
| G25 | [data/geometry/DOERefLargeOffice.osm](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/data/geometry/DOERefLargeOffice.osm) | `7e3795d68ca363ffdbed2efe6985e138ccafc311e1d8e9b9c0785d005ab71078` |
| G26 | [data/geometry/DOERefMidriseApartment.osm](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/data/geometry/DOERefMidriseApartment.osm) | `1f6eac197db5d6cb63d0ff8479468369ee6e5a0a032924f57f7f8dee38094fca` |
| G27 | [data/geometry/DOERefPre1980FullServiceRestaurant.osm](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/data/geometry/DOERefPre1980FullServiceRestaurant.osm) | `baf0acfabcfa0c5ede3d5b19913e74b59d774b05ea3ebeaa6e7a6c4a4c80294a` |
| G28 | [data/geometry/DOERefPre1980QuickServiceRestaurant.osm](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/data/geometry/DOERefPre1980QuickServiceRestaurant.osm) | `f2aca851c82b5178b77003a733f92cc54c2c616e55a6bee36a7bfd756c1e8803` |
| G29 | [data/geometry/DOERefPre1980SmallOffice.osm](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/data/geometry/DOERefPre1980SmallOffice.osm) | `af761cfb6683630d0a32286026ce75f06b71618cbaf9e843c46ad1ffa7052b8b` |
| G30 | [data/geometry/DOERefPrimarySchool.osm](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/data/geometry/DOERefPrimarySchool.osm) | `06eba9d62c9181ba4a27bf53e5ab697dba9d7af2ec451146223f90cfa198f74d` |
| G31 | [data/geometry/DOERefRetailStandalone.osm](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/data/geometry/DOERefRetailStandalone.osm) | `6406ace5785fbee762153b1e22facdd67d01638a90bcdd49965f5db7d52686b5` |
| G32 | [data/geometry/DOERefSecondarySchool.osm](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/data/geometry/DOERefSecondarySchool.osm) | `cdbff7e55f95ba45bfc0a82e3daeb202d60c825895d8f19fc12ea48ef6c7f545` |
| G33 | [data/geometry/DOERefSmallHotel.osm](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/data/geometry/DOERefSmallHotel.osm) | `f10d0f45d75fb78f58742a7db8329c1c6af11c768a38af9a63eee84263bafd5c` |
| G34 | [data/geometry/DOERefWarehouse.osm](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/data/geometry/DOERefWarehouse.osm) | `bf710b716e3531269c8363751f6508754e3f4198eb6129a063ed5b2264059e81` |

## Annotation boundary

Edit membership, target weights and decisions in [the main matrix](program-aggregation-matrix.md). This companion records source evidence and should not be edited to make a desired recipe appear source-reported. If a ratio is chosen as an experimental assumption, record it as an assumption with its rationale in the main matrix.
