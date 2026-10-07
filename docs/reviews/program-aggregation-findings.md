# Follow-up source findings for program aggregation

Inspected 2026-10-06; research decisions updated 2026-10-07. Read with the [decision matrix](program-aggregation-matrix.md)
and [complete source-area tables](program-aggregation-evidence.md). These are
research findings and generator requirements; no mixed energy presets have been
released. All source values below concern the frozen selected Standards models,
not a population-weighted ComStock sample.

## SuperMarket: the area shares are recoverable

The earlier `U` cells were an extraction limitation, not missing source geometry.
Some source spaces have a blank Part of Total Floor Area field. Their OSM version
is 2.2.1: the matching OpenStudio IDD defaults this field to Yes, and the Space
implementation applies that default unless the space is a plenum connected to
an air-loop supply/return plenum. All seven affected geometry files have no such
plenum objects. Explicit No fields remain excluded. A space name alone does not
establish this SDK condition.

Applying the versioned source rule resolves all 16 previously unresolved contexts.
**All 83 selected building/template contexts now have calculable area shares**,
covering 768 canonical commercial program rows and 34 locked geometry files.
Original raw files and blank field values are preserved. Canonical `area_fraction`
fields and delivery packets have not been changed by this inspection.

For SuperMarket the represented counted area is approximately 4,180.839 m².
The following shares agree to three decimals across all five selected templates:

| Program | Building area % |
| --- | ---: |
| Sales | 54.943 |
| Produce | 17.015 |
| DryStorage | 10.098 |
| Deli | 5.375 |
| Bakery | 5.000 |
| Restroom | 1.500 |
| Elec/MechRoom | 1.333 |
| Corridor | 1.182 |
| Dining | 1.111 |
| Meeting | 1.111 |
| Vestibule | 0.667 |
| Office | 0.666 |

An empirical fallback is therefore unnecessary for this selection. A group's
weights are its member areas divided by their own sum, not these whole-building
percentages. Use unrounded polygon areas, not inspection-table rounding. BEMGen
can use source ratios as defaults; a changed plan ratio is an explicit scenario.

## RetailStripmall: all three types are retail tenant aggregates

The selected geometry contains two large stores and eight small stores. Its
source-space allocation is:

| Source type | Source spaces | Building area % |
| --- | --- | ---: |
| Strip mall - type 1 | LGstore1, SMstore1 | 25 |
| Strip mall - type 2 | SMstore2, SMstore3, SMstore4 | 25 |
| Strip mall - type 3 | LGstore2, SMstore5, SMstore6, SMstore7, SMstore8 | 50 |

All five selected templates use the same locked geometry. These types have retail
ventilation classifications; their differences include lighting and operating
schedules. They are not three categories of retail/circulation/atrium. There is
**no separately modeled public corridor or atrium** in this source geometry and
no reported internal circulation fraction to subtract from each tenant.

The researcher approved the 25/25/50 retail mixture on 2026-10-07, alongside the
three original types. No internal atrium/corridor work is required for this family.
Tenant-internal ancillary activities may be implicit in a retail aggregate, but
no quantitative decomposition was established here.

Do not generalize this result to every ComStock strip-mall realization. The pinned
[ComStock methodology](https://github.com/NatLabRockies/ComStock/blob/3c103063c0debb177a200dd1df8406b8d0f8d515/documentation/reference_doc/4_2_meta.tex#L99)
describes separate workflow rules allowing restaurant shares. Those are a
different layer from the three selected Standards tenant types.

## Apartment variants: geometry and generator additions matter

Within each selected 90.1-2007, 2013 and 2019 template, the normalized base
loads, schedules, ventilation and thermostat fields of `Apartment_topfloor_NS`
and `Apartment_topfloor_WE` match `Apartment`. `Corridor_topfloor` likewise
matches the ordinary base corridor fields. This holds for HighriseApartment and
MidriseApartment. Some raw lighting classification labels differ without changing
these extracted numerical values or schedules. The legacy selected Midrise
templates do not offer the same top-floor program rows.

In the inspected 2013 geometries, the top-floor apartments have outdoor roofs,
whereas ordinary apartments do not. NS labels occur on N/S units; the WE-labeled
set includes corner units named NE/NW/SE/SW, so it should not be interpreted as
exclusively east/west-facing facades. The top corridor also has an outdoor roof.
Preserve the optional distinct presets and assign exposure through geometry.

However, equality of base table fields is **not equality of complete generated
models**. The locked prototype Ruby code adds equipment to particular spaces:

| Family | Assigned space | Elevator rated power | Lights/fans rated power in selected code templates |
| --- | --- | ---: | --- |
| HighriseApartment | `T Corridor` | 20,370 W | 161.9 W for 2007; 63 W for 2013/2019 |
| MidriseApartment | `G Corridor` | 16,055 W | 161.9 W for 2007; 63 W for 2013/2019 |

Both components set latent/radiant fractions to zero and lost fraction to 0.95;
their rated electricity is not all zone heat. Elevator and lights/fans have
separate schedules. Legacy Midrise also adds the elevator using a pre-2004
schedule. These are space-assigned building-service components, not a per-area
load to duplicate into every corridor or an entire top-floor program class.

The generator also applies ground-corridor door infiltration. Midrise's
`adjust_clg_setpoint` changes the office cooling schedule in specified dry climate
zones for templates including selected 2007. Thus base program tables do not
establish weather/climate independence of final setpoints or infiltration.
These post-table rules were inspected in source; their full generated-model
execution has not been reproduced in this review. Preserve this limitation and
do not silently fill the atlas's missing infiltration values with these rules.

## Other corrections and defaults

- FullServiceRestaurant has 72.727% Dining / 27.273% Kitchen in all selected
  geometries. QuickServiceRestaurant is **50% / 50%**. Apply the same two-program
  generator concept with different source defaults. A depth fraction equals its
  area fraction when both departments span the same plan length.
- RetailStandalone retains the legacy `Retail` source row through **90.1-2007**.
  `Front_Retail` and `Core_Retail` occur in the selected 2013/2019 templates.
  Select recipes by actual available rows, not a guessed pre-2007 threshold.
- The researcher selected area-weighted, pointwise heating/cooling setpoint
  blending on 2026-10-07. It is an intentional simplification to benchmark later,
  not a source-prescribed thermostat policy. No representative-controller choice
  or extra thermal partition is required. Other compatible numerical program
  values follow the area-weighted simplification; unit/basis conversions and
  unknown source fields retain their existing meaning.
- Basement and attic programs are excluded from every mix, including counted
  floor areas. They remain available separately but are not expected in default
  generated plans. This supersedes the earlier inclusion of LargeHotel Basement
  in General. Default standard is 90.1-2019.
- ResStock's 41 dwelling fixtures remain a separate family of dwelling-level
  semantics. No internal room-area fractions have been extracted from them;
  do not substitute them for a commercial apartment family by label alone.

## Source locators and checksums

Standards geometry and table revision:
`c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907`.
The complete 34 geometry SHA-256 values and original metre-valued polygon,
dimensionless multiplier and floor-inclusion locators are in the companion
[evidence tables](program-aggregation-evidence.md). Canonical program provenance
is in `data/releases/v0.2.0/provenance.json`. The runtime sources below are locked
in [completion-evidence-lock.json](../../sources/completion-evidence-lock.json).

| Runtime source and locator | SHA-256 |
| --- | --- |
| [Prototype.HighRiseApartment.rb](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/lib/openstudio-standards/prototypes/common/buildings/Prototype.HighRiseApartment.rb#L49), `add_extra_equip_corridor`, `add_door_infiltration` | `93b60fd8d3aeb7a32fd5acf0ea62f5e4ddc78ac32b8eacd8c9f120c98e64bc52` |
| [Prototype.MidriseApartment.rb](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/lib/openstudio-standards/prototypes/common/buildings/Prototype.MidriseApartment.rb#L30), `adjust_clg_setpoint`, `add_extra_equip_corridor`, `add_door_infiltration` | `1690e0972a8b307e3d1cb87ebb6a8e3a3efa9d2ff2d5d492f8a3c3be54b341ac` |
| [Prototype.RetailStripmall.rb](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/lib/openstudio-standards/prototypes/common/buildings/Prototype.RetailStripmall.rb) | `093b7e9e65ca029065c7acde0caea2ae2728994f1a338e0678c542d89db45a81` |

OpenStudio v2.2.1 resolves to revision
`0a5e9cec3f9e57872c44b1e074e9a625cfd9531b`:

| Default/implementation source and original locator | SHA-256 |
| --- | --- |
| [OpenStudio.idd](https://github.com/NatLabRockies/OpenStudio/blob/0a5e9cec3f9e57872c44b1e074e9a625cfd9531b/openstudiocore/resources/model/OpenStudio.idd), OS:Space Part of Total Floor Area, lines 4924–4928, default Yes | `05fd80c0a33a8b3526485284d0262a2bb824930583f6b7c5ce19544d734c8f91` |
| [Space.cpp](https://github.com/NatLabRockies/OpenStudio/blob/0a5e9cec3f9e57872c44b1e074e9a625cfd9531b/openstudiocore/src/model/Space.cpp), `partofTotalFloorArea`, lines 419–428; `isPlenum` | `37da9563a1eb8d6006dd0f4d631d098aaaa8b14df6c6c19f403f609b0d250854` |
| [ThermalZone.cpp](https://github.com/NatLabRockies/OpenStudio/blob/0a5e9cec3f9e57872c44b1e074e9a625cfd9531b/openstudiocore/src/model/ThermalZone.cpp), `isPlenum`, lines 2117–2125 | `ee55c0d8c8fd2b81fca33dfd4e481b621272d6a01b693237d13fad5f7c64d637` |

Extraction date for this review: 2026-10-06. Restaurant/strip/supermarket fractions
are derived from source metre-valued floor polygons and dimensionless zone
multipliers; electrical design levels above are original watt values with no unit
conversion. Interpretation: source-specific benchmark defaults and rule inspection,
not a claim that these rules have already been materialized into published presets.
