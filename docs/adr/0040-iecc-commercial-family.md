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
