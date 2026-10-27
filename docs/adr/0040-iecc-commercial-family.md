# ADR 0040: The IECC commercial prototype family

Status: accepted (2026-10-26, user approval of every decision in section 2). The
family itself was decided earlier: IECC is a separate family from ASHRAE 90.1, with
no pairing between editions (plan round 9).

## 1. Context

The pinned PNNL set (`sources/reference-models-lock.json`, family `commercial-iecc`)
holds the IECC commercial prototypes. There are 16 building types, 6 editions (IECC
2006, 2009, 2012, 2015, 2018 and 2021) and 19 locations, one per ASHRAE 169 climate
zone from 0A to 8. Each location has an EnergyPlus 22.1 IDF and an output table, so
there are 1,824 models. The set has no IECC 2024.

Inspection on 2026-10-26 found the following:
- **Same model as the 90.1 prototype of a comparable edition.** Medium office,
  primary school and stand-alone retail, IECC 2021 or 2015 against 90.1-2019 or
  2013 in Buffalo, share:
  - geometry and zone names;
  - every non-lighting zone load;
  - all but a few schedules (lighting controls, door-opening infiltration and one
    outdoor-air damper schedule).
- **Differences from 90.1:**
  - lighting densities;
  - envelope insulation and glazing, as materials changed under unchanged
    construction names;
  - window-to-wall ratio, 0.30 in IECC against 0.33–0.35 in some types;
  - infiltration rates in some types.
- **No space types.** The IDFs have no Space objects, so space types come from
  elsewhere. The zone names match the openstudio-standards 90.1 geometry, whose
  spaces carry standards space-type tags.
- **Climate variation.** Within an edition, loads and schedules are mostly the same
  in all 19 locations.
  - Schedules that vary by climate are system schedules: outdoor-air dampers and
    heat-pump water heaters.
  - Loads vary in a few cases. For example, Medium Office 2021 lighting is
    6.59 W/m² in zones 0B and 1B against 5.93 W/m² elsewhere.
- **No atlas route yet.** openstudio-standards, the source of the 90.1 and DOE Ref
  templates, has no IECC templates. The atlas construction pipeline cannot produce
  IECC sets either.

## 2. Decisions

1. **Scope.**
   - All 16 types in all 6 editions: 96 folders under `commercial/iecc-<year>/`.
   - The apartment types stay commercial, as for 90.1 (ADR 0038 section 8).
   - Source family `iecc_commercial_prototype`.
2. **Source authority.**
   - The PNNL IDFs themselves are the source; openstudio-standards is not.
   - Values are extracted offline into committed definition inputs, one per
     edition, so CI does not need the 4.6 GB of archives.
   - Answer-key tests compare a pinned sample with the IDFs at the ADR 0035
     tolerance.
3. **Programs.**
   - A zone takes the standards space type of the same-named space in the
     openstudio-standards 90.1 geometry of its type. Aliases apply where names
     differ, as for the DOE reference models.
   - One program per space type, area-weighted over its zones.
   - A zone spanning several space types stays unmapped, with a reason.
4. **Fillings.**
   - The IDFs are complete models, so absence of an object is a source zero, as in
     ADR 0037. No research-assumption fillings are needed.
5. **Climate.**
   - Programs are climate-independent where all 19 locations agree.
   - Where a load differs by location, as Medium Office 2021 lighting does in 0B
     and 1B, those zones get climate-specific program variants, using the existing
     `climate` field.
   - System-only schedule variation stays out of scope with the systems (item 10).
6. **Constructions.**
   - Construction sets come from the IDF constructions and materials, with one
     context per climate zone (19 contexts, keyed as the 90.1 sets are).
   - Detailed representation (4.1.0) only. The unified equivalent (3.1.0) needs the
     pinned-producer equivalence pipeline and is deferred.
7. **Infiltration.** The IDF design-flow rules are the source method, per zone, with
   their schedules inline. There is no fixed natural-ACH method, because that comes
   from the openstudio-standards pipeline.
8. **Window ratios.**
   - Per program, by direction, at program level (user decision of 2026-10-26).
   - The 15 whole-building values go on the construction set.
   - The true-outdoor-wall basis applies, as in ADR 0037.
9. **Mixes, services and water.**
   - Department and general mixes use the composition recipes of the same building
     type, weighted by IDF zone floor area times multiplier.
   - Building services and refrigeration are extracted as in ADR 0037: elevators,
     exhaust fans, exterior lights, refrigeration cases and racks.
   - Water-use draws carry their zones and gain fractions.
10. **Deferred.**
    - HVAC, plant and water heaters, as for the DOE reconciliation.
    - The unified construction representation.
    - IECC 2024, until PNNL publishes it.
11. **Evidence only.** A report of the IECC and 90.1 differences per type and
    edition records the comparison above. It creates no pairing and no shared
    records.
12. **Release.** Release 1.3.0, a delta on 1.0.0 that also holds the changes of
    1.1.0 and 1.2.0, written by `scripts.atlas_minor_release`.

## 3. Consequences

- About 96 folders, each with programs, mixes, schedules, services, water and one
  construction set of 19 contexts. Release 1.3.0 grows by roughly the size of the
  90.1 templates.
- The IECC templates are the first in the atlas whose values come directly from
  EnergyPlus models rather than openstudio-standards. Their provenance points to
  pinned IDF files.
- BEMGen can build IECC variants from the same geometry knowledge as 90.1, because
  the prototypes share their plans.

## 4. Agent decisions (S11, 2026-10-26)

Taken under plan G1 while building release 1.3.0. Each entry gives the decision, the
alternatives, the reason and the evidence. The PR repeats this list. Section 2 item 5
is implemented as the user clarified it in plan C6: loads that differ by location carry
`value_by_climate` (Program JSON 5.2.0) instead of climate-specific program variants.

1. **Zone-tag conflicts take the 90.1-2019 tag.**
   - *Alternatives:* the tag of the 90.1 edition nearest each IECC edition; leaving the
     zones unmapped.
   - *Reason:* 24 zone names are tagged differently by the three geometries (Hospital
     offices, the Large Office zones, one Outpatient zone, the Stand-alone Retail front
     and core). 2019 has the finest split, the IDF loads follow it (the floor-1 and
     floor-5 hospital offices differ), and one tag set keeps the six editions comparable.
   - *Evidence:* `sources/iecc-commercial-zone-aliases.json`, one entry and reason per
     name. Every IECC zone of every edition matches after normalization, so no guesses
     were needed.
2. **Zones 7 and 8 are keyed `7-a` and `8-a`.**
   - *Alternatives:* keys `7` and `8` with an extended climate enum.
   - *Reason:* the plan names the key style `0-a` … `8-a`. ASHRAE 169-2013 and the IDF
     headers give zones 7 and 8 no moisture regime, and openstudio-standards assigns
     the same International Falls and Fairbanks weather to 7A/7B and 8A/8B.
   - *Evidence:* `lib/openstudio-standards/weather/information.rb` at the pinned
     revision. The context keeps the source label in `source.source_climate_label`
     (`7`, `8`); `value_by_climate` uses the same atlas labels (`7A`, `8A`).
3. **`value` is the most common value over the 19 locations, ties going to 5A.**
   - *Alternatives:* always the 5A value.
   - *Reason:* plan C6 ("value keeps the value for most zones"). The 2021 lighting
     reductions apply in up to nine locations, so a fixed 5A base could put the
     majority in the exceptions.
   - *Evidence:* the climate section of the
     [IECC and 90.1 report](../reviews/iecc-commercial-vs-90-1.md). Only IECC 2021
     varies by climate, in lighting (most types) and in hot water (Midrise
     Apartment, the hotel and hospital laundry heaters).
4. **A second Lights object is additional lighting.** Apartments have hard-wired and
   plug-in lights; strip-mall stores have base and display-allowance lights, each with
   its own schedule. The plug-in, allowance or display object becomes the program's
   `additional_lighting` with its own schedule. *Alternative:* one summed load on a
   mixed schedule. *Reason:* the atlas already has the two quantities, and nothing is
   averaged.
5. **Zone-located service equipment becomes building services.** ElectricEquipment
   with subcategory ElevatorLift or ElevatorLightsFan is an elevator service, as in ADR
   0037; ReachInRefrigerator and ReachInFreezer are `refrigeration_equipment`
   services. Each is instantiated once, at design level times zone multiplier, and
   names its zone's program as beneficiary. *Alternative:* fold them into the
   program's plug load. *Reason:* they run on their own schedules (always on, elevator
   schedules) and would otherwise force one mixed plug-load schedule.
6. **Exhaust fans are Fan:ZoneExhaust objects.** They become `exhaust_fan` services
   with electric power = maximum flow × pressure rise / total efficiency, keeping flow,
   pressure and efficiency. *Alternative:* omit them as HVAC. *Reason:* ADR 0040 item 9
   lists exhaust fans; their air flow stays deferred with the systems.
7. **Hot water.**
   - Zone WaterUse:Equipment draws form one program draw, stored as the 90.1 records
     store theirs: a program-service load and its service, per floor area, with the
     EnergyPlus zone gains of ADR 0037. Zoneless draws are building-level services.
   - A stand-alone water heater's use flow (no plant connection) is a program draw
     when its zone has no fixture draw, and a `booster` service of that program
     otherwise (the hospital kitchen's 82 °C heater). It carries no zone multiplier,
     because a heater is not zone equipment, and no zone gain.
   - Midrise Apartment 2021: three locations (5A, 6A, 7) keep per-unit heaters for
     the 23 modelled units, the other sixteen one central draw for 31 units. Both are
     stored with `value_by_climate` (the apartment draw is 0 in most locations; the
     central service is 0 in the three).
   - *Alternative:* one representation for every location. *Reason:* the totals
     differ, so either choice would misstate some locations.
8. **Slot conflicts take the area-dominant schedule** (`R-SLOT-CONFLICT`, as ADR 0037).
   Examples are the apartments' working-family and stay-home occupancy and the north
   and south guest-room setpoints. 38 to 44 per edition are listed in each input's
   `schedule_conflicts`.
9. **Conditioning is a source parameter.** A program is heated or cooled where its
   zones have the setpoint objects (dual or single). Plenums and attics without a
   thermostat are unconditioned as a source zero. *Reason:* absence in the complete
   model is a source zero (item 4). The exporters then need no filling.
10. **EMS-actuated setpoints are stored as their input schedules.** In 2021 the
    apartment and guest-room setpoint schedules are reset at run time by EMS programs.
    The input schedule is stored, and its evidence names the actuator. *Alternative:*
    leave them unknown. *Reason:* they are the source inputs; an EMS program is not a
    schedule.
11. **Mixes by climate.** A mix's `value_by_climate` is recomputed from its members'.
    `schedule_id_by_climate` is defined for a trajectory that would change, but no mix
    needs it: the 2021 reductions scale whole types uniformly.
12. **Construction assignments.**
    - Assemblies are content-addressed per type (layers or F/C factor and role); IDF
      names that share physics share one assembly, which lists every IDF name.
    - A component with several assemblies gets rules by story position (basement,
      ground, middle and top floor from the zone elevations) and space type, with the
      contract's precedence space type, story, building default.
    - Surfaces no rule explains get surface-level assignments with
      `source_element_ids`, marked `surface_override` in the selection decisions.
      Examples are the hospital air walls, the small-hotel rooms and some apartment
      walls.
    - *Alternative:* building default only. *Reason:* 2021 walls differ by floor
      (PNNL's thermal-bridging insulation), which a single default would lose.
13. **Component mapping.**
    - Doors whose construction is an overhead door are `OverheadDoor`.
    - Windows on roofs are `Skylight`.
    - Adiabatic and interzone surfaces are interior components; ground-contact surfaces
      are `GroundFloor` or `FoundationWall`, with the 90.1 sets' F- and C-factor ground
      methods.
    - Zone shading has no construction, so shading components are `source_absent`.
14. **The unified member is a stub.** The construction writer stores a detailed and a
    unified document per context. The IECC contexts carry a `deferred` unified stub,
    and the consumer export refuses it with the reason (item 10). *Alternative:* edit
    the writer, which is pinned.
15. **Construction JSON 4.2.0** adds the `source_design_flow` infiltration method,
    which needs no natural ACH. **Program JSON 5.2.0** adds `value_by_climate` and
    `schedule_id_by_climate` on loads, window ratios by climate, `source_zones`,
    `pnnl_building_type` and `standards_building_type`. Release 1.3.0 exports every
    program and detailed set in these minors. The 5.1.0 and building-services schemas'
    release enums gain 1.3.0. All changes are additive.
16. **Mass accounting from the IDFs.**
    - Internal-mass entries come from InternalMass with zone multipliers.
    - The interior budgets halve paired wall faces and count each floor once.
    - The IDF faces carry no pairing, so unequal-multiplier pair counts are 0, with an
      interpretation saying so.
17. **The release builder pins itself.** Release 1.2.0 pins
    `scripts/atlas_minor_release.py` by SHA-256. Release 1.3.0 is therefore added as a
    tagged block (`# >>> release 1.3.0` … `# <<< release 1.3.0`) before the main
    guard. `verify` strips the blocks of later releases before checking a manifest that
    pins the file, which restores the exact bytes that built 1.2.0.
    - *Alternatives:* rewrite the 1.2.0 manifest (released data; not allowed); a
      second builder script (the plan asks for a `RELEASES` entry).
    - *Evidence:* 1.2.0 still verifies.
18. **Small supporting choices.**
    - `scripts.idf_schedules` reads abbreviated month holidays (`Jan 1`, one IECC file).
    - The IECC sets' `source.definition_release` names the definition input
      (`iecc-commercial-<year>`).
    - The extractor checks every IDF against the archive member checksums recorded
      when the pinned archives were extracted (`--manifest`), and every location's zone
      geometry against 5A.
    - Program window ratios that differ by location (skylights in Stand-alone Retail
      and Warehouse from 2015) keep the most common ratios and list the others in
      `fenestration.value_by_climate`. Building services that differ (for example
      the 2021 Large Office data-centre HVAC equipment) carry `value_by_climate`.
19. **Fraction schedules above 1 are peak-normalized.** PNNL's IECC 2006 and 2009
    small-hotel meeting and lounge lighting schedules reach 1.1, which the Program JSON
    fraction contract does not allow.
    - The stored schedule is divided by its peak (`peak_divisor`) and the density
      multiplied by it (`schedule_peak_scaling` on the load), so the hourly load
      trajectory is unchanged.
    - *Alternative:* keep 1.1 and fail the export.
    - *Evidence:* the schedule's evidence row and the answer-key test, which applies the
      scaling.
20. **IECC programs export as source only.** They hold source values with no fillings,
    so the `filled` version would add nothing but the water-heating fold. That fold
    needs the source water heaters, which are deferred with the systems (item 10). The
    export refuses `filled` for IECC programs with that reason. *Alternative:* a filled
    export without water heating, which the 5.x filled contract does not define.
