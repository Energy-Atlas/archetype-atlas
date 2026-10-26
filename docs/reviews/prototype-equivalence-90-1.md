# Equivalence of the atlas 90.1 templates and the PNNL prototype models

Stage S3 of the [DOE reference reconciliation plan](../superpowers/plans/2026-10-24-doe-reference-reconciliation.md).
Date: 2026-10-25.

**Question:** are the atlas's new-construction templates (90.1-2007, 2013 and 2019, built
from openstudio-standards) the same as the PNNL prototype models in the aspects that
matter? The aspects compared are geometry, construction, infiltration, internal mass and
fenestration. Loads and schedules are excluded; by decision they are recorded as
evidence only.

**Answer:** not entirely.
- **Equal:** geometry for 13 of 16 types, fenestration for 15 of 16, ground-floor
  F-factors everywhere, and most roofs.
- **Different, systematically:** exterior walls, doors and part of the glazing.

Under the plan's rules this is a real construction difference, so the stage stops here
for discussion before anything is applied.

## Method

`python -m scripts.prototype_equivalence --prototype-root <commercial-ashrae901> --standards-raw <openstudio-standards cache>`

- **Inputs:** the pinned prototype bundles (`sources/reference-models-lock.json`), the
  atlas release v1.0.0 construction sets (exported through `scripts.atlas_exports`) and
  `data/construction-inputs/geometry-v1.json`. The latter holds the openstudio-standards
  geometry the atlas recovered.
- **Coverage:** 3 editions × 16 types. Geometry uses the Denver file. Constructions use
  all 19 climates, each matched to the atlas context named by the IDF's
  `AnalysisClimateZone` (zone 7 to `7-a`, zone 8 to `8-a`).
- **Tolerance:** 1% relative.
- **Geometry is judged on building totals, weighted by zone multipliers.** Three modelling
  conventions differ between the models without changing the building:
  - the prototypes leave plenum floors to one-sided "Zone" boundaries;
  - they lift the representative middle floor of multiplied floors to a different height;
  - they repeat apartment floors with `ZoneGroup` multipliers.
- **Constructions:** for each component, every prototype construction variant is compared
  with the atlas building-default assembly. Opaque assemblies compare layer resistance
  without air films; glazing compares U-factor and SHGC; ground floors compare F-factor.
  The full output is in `build/reconciliation/prototype-equivalence.json`, and the summary
  is in [prototype-equivalence-90-1.json](../validation/prototype-equivalence-90-1.json).

## Geometry and fenestration

| Result | Types (same in all three editions) |
| --- | --- |
| **Equal:** conditioned floor area, exterior wall and roof area, WWR | Mid-rise and high-rise apartment, large and small hotel, large, medium and small office, outpatient, both restaurants, stand-alone retail, strip mall, both schools |
| **Hospital differs** | The prototype has 5,197 m² of exterior wall and 3,739 m² of roof; the openstudio-standards geometry has 7,373 and 4,353. WWR is 0.163 vs 0.115. The prototype's figures equal the DOE reference hospital. |
| **Warehouse differs** | Conditioned floor area is 4,598 vs 4,835 m². The openstudio-standards geometry counts a fine-storage floor of 237 m² above the office, which the prototype does not have. |

The skylight-to-roof ratio varies by climate in some prototypes (stand-alone retail,
warehouse), as noted in the plan's Q16-B.

## Constructions

Results are counted over 19 climates × the types that have the component. The ratio is
the prototype value over the atlas value, as a median over the differing cases.

| Component | 90.1-2007 | 90.1-2013 | 90.1-2019 |
| --- | --- | --- | --- |
| Ground floor (F-factor) | 247 equal | 247 equal | 247 equal |
| Exterior roof | 212 equal, 92 differ | 212 / 92 | 212 / 92 |
| Exterior wall | 0 equal, 304 differ (R ×0.64) | 0 / 304 (R ×0.60) | 0 / 304 (R ×0.60) |
| Exterior window | 64 / 240 (U ×0.93) | 266 / 38 (U ×0.99) | 141 / 163 (U ×1.02) |
| Skylight | 0 / 76 (U ×0.87) | 45 / 31 | 51 / 25 |
| Exterior door | 0 / 266 (R ×2.5) | 0 / 266 (R ×1.7) | 0 / 266 (R ×1.5) |
| Glass door | 8 / 30 | 0 / 38 | 0 / 38 |
| Exterior floor (small office soffit) | 0 / 19 | 0 / 19 | 0 / 19 |

**What the differences are:**

- **Walls (real).** The prototypes give each floor its own wall insulation layer (`_grd`,
  `_mid`, `_top`), far lower than the code-level assembly openstudio-standards selects.
  - Medium Office, 90.1-2019, Denver: the prototype insulation is R 0.73–1.03 m²K/W, and
    PNNL's own results table reports wall U-factors with films of 0.70–0.89 W/m²K.
  - The atlas assembly (typical insulation R-16) has layer resistance 3.05 m²K/W, about
    U 0.31 with films.
  - This is in the prototype files and their results, not an artefact of the comparison.
    The plan does not yet record why PNNL models it this way.
- **Doors (real).** The prototype door panels are more resistive than the atlas assemblies
  in every edition.
- **Glazing (real, small).** The prototypes use per-orientation and per-space-type
  (residential vs non-residential) window constructions, about 2–7% from the atlas
  building default in 2007 and 2019. 2013 mostly agrees.
- **Roofs (mostly a comparison limit).**
  - In the apartments and hotels, the prototype uses residential and non-residential roof
    variants, while the comparison checks only the atlas building default. The atlas may
    hold the residential variant as a space-type assignment, which a refined comparison
    should check.
  - In the attic types (small office, both restaurants, warehouse), the prototype
    insulates differently, so roof and soffit roles do not line up one to one.

## Infiltration and internal mass

- **Infiltration:** the methods differ, as expected.
  - The prototypes use design flow per exterior wall area: 0.000570 m³/s·m² in 2019 and
    0.001025 in 2007 for the medium office, with schedules.
  - The atlas uses a fixed natural air-change rate (ADR 0020).
  - Plan decision Q8 adds the design-flow method as a second, selectable method; for the
    90.1 templates its values would come from the prototypes.
- **Internal mass:** equal in occupied spaces (2.0 m² per m² of floor) for 11 of 16 types.
  - openstudio-standards also puts mass in plenums and attics (about 2.0 m²/m²), which the
    prototypes do not.
  - The apartments and warehouse differ in occupied-space mass. For the warehouse the
    prototype has 1.31 vs the atlas's 0.67.

## What this means for the plan

The proof of "same in what matters" does not hold for constructions. Decisions for the user:
1. **Construction authority for the 90.1 templates.** Keep openstudio-standards, adopt the
   prototype constructions, or carry both with one as an alternate.
2. **Geometry inputs** (hospital, warehouse, plenum mass). These matter to the atlas only
   through WWR (Q16) and internal mass; geometry itself is BEMGen's concern.
3. **Whether to refine the comparison** for scoped roof assignments and attic roles
   before deciding.
