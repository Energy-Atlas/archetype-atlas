# ADR 0042: The manufactured-housing prototype family

Status: accepted for release 1.4.0 (2026-10-26). The templates, programs and
sub-contexts are user decisions (plan
`docs/superpowers/plans/2026-10-26-residential-and-manufactured-families.md`, R6 and
M1–M3). Storage follows ADR 0038 and the code-prototype pattern of ADR 0041. The
choices the plan left open are agent decisions, listed in section 4.

## 1. Context

The pinned PNNL manufactured-housing set (`sources/reference-models-lock.json`,
family `manufactured-housing`, EnergyPlus 8.0) has, per location, a `HUD`, a
`FinalRule` and a `CompleteSet` archive:
`<zone>_<City>_{HUD,FinalRule}/<SS|MS>_<City>_<zone>_<HUD|tier1|tier2>_<heating>.idf`.

- **Types:** single-section (SS) and multi-section (MS) homes.
- **Locations:** 19, one per climate zone (1A, 2A, 2B, 3B, 3C, 4A to 4C, 5A, 5B, 6A,
  6B, 7, 8) except 3A, which has five cities (Atlanta, Birmingham, Charleston,
  Jackson, Memphis).
- **Standards:** the HUD Code baseline, and the 2022 DOE Final Rule, tier 1 for
  single-section and tier 2 for multi-section homes.
- **Heating:** electric furnace, gas furnace, heat pump, oil furnace.
- **Zones:** a living zone, an attic and a crawlspace.

Inspection of the 304 HUD and FinalRule models (`scripts.manufactured_housing`) found:
- loads, thermostats and ventilation agree across heating systems and locations;
- the HUD and Final Rule models differ in their hot-water draw schedules only, apart
  from the envelope;
- construction contexts agree across heating systems.

## 2. Decisions

1. **Family** `manufactured_housing_prototype`; templates `hud-code` (HUD Code) and
   `doe-final-rule` (DOE Final Rule 2022), with the tier (`tier1`, `tier2`) as a
   record field (R6).
2. **Source folders (M1).** Only HUD and FinalRule are read. Every CompleteSet model is
   checked by SHA-256 against its copy (304 identical), recorded in the input.
3. **Offline extraction** into the committed
   `data/program-inputs/manufactured-housing.json` (0.7 MB).
4. **Programs (M2).** One per template and section type:
   `residential/{hud-code,doe-final-rule}/{single-section,multi-section}/`.
5. **Sub-contexts (M3).** Construction contexts are the climate zones (`4-a`, `7`, …);
   the five 3A cities are sub-contexts `3-a.atlanta`, `3-a.birmingham`,
   `3-a.charleston`, `3-a.jackson` and `3-a.memphis`.
6. **Infiltration** is the source `ZoneInfiltration:EffectiveLeakageArea` of the
   living zone and the attic and crawlspace vents, in the construction context.
7. **Gap (user decision):** the set has no existing-building category. Existing
   manufactured homes come only from the ResStock fixture (three dwellings under
   `residential/resstock-sdr/manufactured-home/`); no code prototype stands for them.
8. **Out of scope:** systems, as for every residential family (ADR 0038 section 7).

## 3. Consequences

- 4 programs, 4 construction sets and 76 construction contexts.
- Answer-key tests compare every location under the HUD Code (152 models) with the
  release files when the IDFs are present (`tests/test_prototype_answer_keys.py`).

## 4. Agent decisions

Each entry: decision; alternatives; reason; evidence.

1. **EnergyPlus 8.0 field layout.** The idf reader's layouts hold for 8.0 except
   `Window`, which still has its Shading Control Name field (removed in 9.0), and
   window shading, which is `WindowProperty:ShadingControl` before 9.0. Both are read
   by version. *Evidence:* `scripts/prototype_extract.py`; the answer-key tests
   compare window U-factors, SHGC, leakage areas and every load with the IDFs. People,
   Lights, ElectricEquipment, Exterior:Lights, WaterUse:Equipment, Zone,
   ZoneInfiltration:EffectiveLeakageArea, ZoneVentilation:DesignFlowRate, Material
   and Construction share the 23.1 positions read here; BuildingSurface:Detailed and
   InternalMass have no Space fields before 9.6.
2. **Load basis.** Lights and miscellaneous equipment are `Watts/Area` in the source,
   so they stay W/m² on the floor-area basis; people, exterior lighting and draws stay
   per dwelling. *Alternative:* convert to W/dwelling with the model floor area.
   *Reason:* ADR 0038 keeps the source basis. Each program records the dwelling floor
   area (85.9 m² single-section, 145.7 m² multi-section) for consumers who need a per-
   dwelling reading.
3. **Calendar.** The 8.0 run period takes its start day from the weather file
   (`UseWeatherFile`). The stored rulesets are day-type rules and need no calendar;
   their full-year check uses a calendar that starts on a Sunday.
4. **Template programs.** Each template folder holds its own program, though the two
   programs differ only in the draw schedules. *Alternative:* one shared program.
   *Reason:* folders are per template (ADR 0038), and the draw schedules differ.
5. **Garage lights.** The models carry an `Exterior:Lights` object named
   `Garage-Lights` (14.0 W) although they have no garage; it is kept as exterior
   lighting, as in ADR 0041.
6. **Source version only**, as ADR 0041 agent decision 6.
