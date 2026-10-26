# ADR 0041: The IECC residential prototype family

Status: accepted for release 1.4.0 (2026-10-26). The scope and the variant rules are
user decisions (plan `docs/superpowers/plans/2026-10-26-residential-and-manufactured-families.md`,
R1–R8 and S1–S3, R1–R6 of section 5). Storage follows ADR 0038. The choices the plan
left open are agent decisions, listed in section 4 with their evidence.

## 1. Context

The pinned PNNL residential set (`sources/reference-models-lock.json`,
`residential/resstd_AllCodes.zip`, EnergyPlus 23.1) holds 4,144 models:
`US+<SF|MF>+CZ<climate>+<heating>+<foundation>+IECC_<edition>.idf`.

- **Editions:** IECC 2006, 2009, 2012, 2015, 2018, 2021 and 2024 (592 models each).
- **Types:** single-family (SF): one living zone, a garage and an attic; multifamily
  (MF): 18 dwelling units (3 floors, front and back rows, 3 units per row and floor),
  a breezeway and an attic.
- **Climate codes:** 19 for SF (1AWH, 1AWHT, 1AWHTS, 2AWH, 2B, 3A, 3AWH, 3B, 3C, 4A
  to 4C, 5A to 5C, 6A, 6B, 7, 8); MF has no 1AWHTS (18).
- **Heating systems:** electric resistance (`elecres`), gas furnace, heat pump (`hp`),
  oil furnace. **Foundations:** crawlspace, heated basement (`heatedbsmt`), slab,
  unheated basement.
- **Schedules:** `Schedule:Compact`, `Schedule:Constant` and `Schedule:Year` with
  `Schedule:Week:Compact` and `Schedule:Day:Hourly`; no `Schedule:File`, and no
  special days.

Inspection of all 4,144 models (`scripts.iecc_residential`) found:
- Loads depend on the appliance fuel: gas furnace homes have a gas range, gas dryer
  and gas miscellaneous loads; the other three heating systems have electric ones.
- The heated basement adds basement lighting and an `IECC_Adj_heatedbsmt` load, and
  changes the `IECC_Adj` and miscellaneous-load values.
- 1AWHTS halves the living-zone lighting and `IECC_Adj` and puts the other half in an
  unconditioned living zone with walls but no floor (`uncond_living`).
- IECC 2024 changes appliance levels and hot-water draw schedules by climate code
  and heating system.
- The multifamily units have identical loads; the heated basement is a building zone.
- Construction contexts (envelope and infiltration) agree across heating systems
  for every climate code and foundation.

## 2. Decisions

1. **Family** `iecc_residential_prototype`; templates `IECC <edition>`; folders
   `residential/iecc-<edition>/{single-family,multifamily}/` (R8: all 7 editions).
2. **Offline extraction** (`scripts.iecc_residential`) into committed
   `data/program-inputs/iecc-residential-<edition>.json` (2.5–2.8 MB each). The
   release build (`scripts.prototype_dwellings`) reads only these files.
3. **Programs (R1).** One per edition, type and appliance fuel: `gas-appliances`
   (gas furnace) and `electric-appliances` (electric resistance, heat pump, oil
   furnace). Loads keep the source basis: `EquipmentLevel` and `LightingLevel` as
   W/dwelling, people as person/dwelling, draws as m³/s/dwelling.
4. **IECC adjustment (R2).** `IECC_Adj`, `IECC_Adj_heatedbsmt` and `Addl_IECC_Adj`
   are their own quantities with `role: reference_design_adjustment`.
5. **Auxiliary zones (R3).** Every load carries `host_zone`, the normalized source
   zone (`living`, `garage`, `attic`, `heatedbsmt`, `breezeway`, `uncond_living`;
   `exterior` for `Exterior:Lights`).
6. **Multifamily (R4).** One per-unit program; the 18 units are checked to agree.
   `building_context` records 18 units, 3 floors, front and back rows, 3 units per row
   and floor, and the non-dwelling zones. Loads in zones outside the units (the heated
   basement's lighting and adjustment) are building-level services.
7. **1AWHTS (R5).** The unconditioned living zone's absolute loads (lighting
   168.995 W, `Addl_IECC_Adj` 252.7 W with gas appliances) are building-level services
   (`shared_services`, instantiated once) that apply with climate code 1AWHTS.
8. **Infiltration (R6).** The source method as it is: SF uses AirflowNetwork surface
   leakage (effective leakage area per component, the surfaces it is linked to);
   MF uses `ZoneInfiltration:EffectiveLeakageArea` per zone and unit position. It is
   stored in the construction context, because it varies with climate code and
   foundation.
9. **Schedules** convert to atlas rulesets checked over the full year and both design
   days against the source objects (`scripts.idf_schedules.Schedules`).
10. **Construction sets:** one per edition and type, with one context per climate
    code and foundation (`4-a.slab`, `1-awhts.heatedbsmt`, …): 76 for SF, 72 for MF.
11. **Window ratios** are program level (`fenestration`), from the dwelling zones'
    outdoor walls; **thermostat** setpoints and **mechanical ventilation** are program
    entries.
12. **Out of scope (R7):** systems (HVAC, water heaters, solar water heating) and
    the unified construction representation.

## 3. Consequences

- 28 programs, 14 construction sets and 1,036 construction contexts. Every value is
  one a source model holds; nothing is averaged across models.
- A consumer selects a program by edition, type and appliance fuel, then keeps the
  entries whose `applies_with` holds for its climate code, foundation and heating
  system (`scripts.prototype_dwellings.select`).
- Answer-key tests compare every edition in 4A and 1AWH (448 models) with the
  release files when the IDFs are present (`tests/test_prototype_answer_keys.py`).

## 4. Agent decisions

Each entry: decision; alternatives; reason; evidence.

1. **The 1A suffixes.** WH is a warm-humid location, T a tropical location and S the
   semi-conditioned tropical design. *Alternatives:* moisture regimes or code
   variants only. *Reason:* the archive has no PNNL residential documentation, so the
   models decide. *Evidence:* `Site:Location` is Miami for 1AWH, Honolulu for 1AWHT
   and 1AWHTS, Atlanta for 3A, Montgomery for 3AWH, Tampa for 2AWH. All 224 1AWH and
   1AWHT model pairs are identical apart from location, as are 3A and 3AWH. 1AWHTS
   adds the unconditioned living zone (half the living space without conditioning),
   flat-plate solar water heating and a thinner ceiling insulation layer
   (`ceil_consol_layer`, 0.285 m to 0.146 m in IECC 2021), matching the IECC
   tropical-zone provisions (R401.2.1). The codes stay context names (R5).
2. **Variation as `applies_with`, not as separate programs.** *Alternatives:* a
   program per fuel and foundation, or climate-specific program variants as in
   ADR 0040 item 5. *Reason:* R1 asks one program per edition, type and fuel; the
   variation is sparse and different per load. Each entry names exactly the
   climate codes, foundations and heating systems whose models hold it, as a union
   of axis-value products. *Evidence:* the SF electric program has 27 load entries,
   13 of them conditional, in every edition from 2006 to 2021, and 51 entries, 45
   conditional, in 2024.
3. **The heated-basement part (R1)** is the set of entries that apply with the
   `heatedbsmt` foundation: basement lighting, `IECC_Adj_heatedbsmt`, and the changed
   `IECC_Adj` and miscellaneous-load values. *Alternative:* a separate basement
   program. *Reason:* the values replace, not add to, the slab-on-grade ones.
4. **IECC 2024's climate and heating-system differences** (appliance levels, draw
   schedules) are `applies_with` entries on `heating` and `climate` (R4: a load that
   differs by heating system gets a variant). *Evidence:* SF 2024 models have 12
   distinct electric-equipment sets and 2 water-use sets, against 8 and 1 in 2021.
5. **Constructions as source model constructions 1.0.0**, not detailed 4.1.0.
   *Alternatives:* detailed 4.1.0 as ADR 0040 plans for IECC commercial.
   *Reason:* 4.1.0 requires the mass-accounting and foundation-ground sections that
   the openstudio pipeline produces; the IDFs give assemblies, surfaces and leakage.
   Each context stores assemblies by surface class (with summed source areas),
   windows, doors, internal mass, window shading control and infiltration;
   assemblies carry the layer-only U-factor (no air films), glazing its simple-glazing
   U-factor and SHGC. *Evidence:* `schemas/construction-source-model-v1.schema.json`.
6. **Source version only.** The code prototypes export Program JSON 5.3.0 `source`.
   *Alternative:* a filled version. *Reason:* the source models are complete (no
   nulls); the filled version adds draw-only water heating, which needs the water
   heaters, and systems are not stored (ADR 0038 section 7).
7. **Hot water** is the `WaterUse:Equipment` draw per dwelling with its target
   temperature schedule. The source gives no zone, so the draws add no zone gains;
   the mains temperature (`Site:WaterMainsTemperature` correlation per location) is
   weather and stays unresolved in the export.
8. **Mechanical ventilation** (`ZoneVentilation:DesignFlowRate`, `Fan:ZoneExhaust`,
   `ZoneHVAC:EnergyRecoveryVentilator` with its heat exchanger effectiveness) is kept
   as program ventilation entries, though ventilators are HVAC objects. *Reason:*
   ventilation rate is program semantics in the brief (section 4.1). An energy
   recovery ventilator replaces the exhaust fan in climate codes 7 and 8 in IECC
   2021, and in more climate codes and heating systems in 2024.
9. **`Garage-Lights`** are `Exterior:Lights` objects (no zone, no gains); they stay
   exterior lighting with `host_zone: exterior`.
10. **Schedule:Year conversion.** Each period's Default rule takes the day schedule of
    most day kinds (ties to the earliest kind, Monday first); `CustomDay1` vacation
    days never occur (no special days) and are not converted.
11. **Floor area.** Each program records the dwelling's floor area (living-zone floor
    surfaces over the number of units) as a conditional entry, so per-area readings
    are possible without geometry.
12. **Evidence** cites one representative model per entry (the first in sorted order)
    with the number of models it holds in; every model read is listed with its
    SHA-256 in the definition input.

### Residential storage (S12a, ADR 0038) agent decisions

13. **ResStock fillings.** The filled reading of a ResStock dwelling replaces its
    loads by the recovered magnitudes of `data/program-inputs/residential-v1.json`
    (the frozen exporters' whole-dwelling path). Each dwelling stores them unchanged
    in one `filling` block (loads, controls, climate, vintage, unresolved, metadata),
    citing the dwelling's resolution rows of `data/resolution-releases/v0.4.0`
    (stored in `evidence/residential/resstock-sdr/resolutions.json`); each recovered
    load cites the rows of its profile column. The block's basis is the strictest of
    the rows (`research_assumption` for the fixed background schedules).
    *Alternative:* per-load inline fillings as for commercial programs. *Reason:* the
    source has no reviewed twins, and the recovered list is not one-to-one with the
    source loads (refrigerator, freezer, second range, lighting). *Evidence:*
    `tests/test_residential_storage.py` compares every value with its frozen source
    and the exports of one dwelling per type with the frozen exporters.
14. **Labels 7AK and 8AK.** The construction release expanded six dwellings' labels
    into A and B contexts with identical documents but for the label. The set keeps
    one context, the A document, keyed by the dwelling's own label (`7-ak`);
    the test checks the B documents.
15. **Annual series** keep their metadata (seed, weather, calendar) per dwelling;
    value arrays are deduplicated within the folder (stored in the first dwelling
    file that uses them).
16. **Dwelling IDs**: `<climate>-<vintage>-<area bin>ft2-b<building>` (`<1940` becomes
    `pre1940`, `4000+` `4000plus`); folders use the ResStock building types
    (`multifamily-5-plus-low-rise`, …).
17. **Building context** stores the source's `Geometry …` options verbatim (units in
    the building, stories, level, horizontal position, foundation, attic, garage).
18. **Apartments** cite the commercial apartment folders of all five templates in
    `commercial_counterparts` (ADR 0038 section 8).
19. **Program JSON 5.3.0.** The dwelling minor is numbered 5.3.0 and derived from
    5.2.0, the IECC commercial minor (ADR 0040, C6), so it stays additive over both.
    (Rebased onto release 1.3.0 on 2026-10-26.)
20. **Builder digest.** `scripts/atlas_minor_release.py` holds every minor release's
    entry. Superseded on rebase: release 1.4.0 is a tagged block after the 1.3.0 block
    (ADR 0040's rule), and `--verify` strips later blocks before comparing the
    builder's digest, so the digest check stays in force for every release.
21. **No new research-assumption fillings** were added (S1): the code prototypes have
    no source nulls, and the ResStock fillings moved unchanged.
