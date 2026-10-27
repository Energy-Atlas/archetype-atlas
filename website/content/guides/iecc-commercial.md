# IECC commercial prototypes

Release 1.3.0 adds the IECC commercial prototype family: the 16 PNNL building types in
the IECC 2006, 2009, 2012, 2015, 2018 and 2021 editions, 96 folders under
`commercial/iecc-<year>/<building-type>/`. The decision record is ADR 0040; the release
notes are `docs/release-notes-atlas-v1.3.0.md`.

The family is separate from ASHRAE 90.1. No IECC edition is paired with a 90.1
edition, and no record is shared. An evidence-only comparison is in
`docs/reviews/iecc-commercial-vs-90-1.md`.

## Where the values come from

- **Source:** the pinned PNNL IECC IDFs (EnergyPlus 22.1), one per climate zone from
  0A to 8. They are extracted offline into `data/program-inputs/iecc-commercial-<year>.json`
  by `scripts.iecc_commercial_values`, so the release builds without the 4.6 GB of
  archives.
- **Space types:** the IDFs have no spaces. A zone takes the standards space type of
  the same-named space in the openstudio-standards 90.1 geometry, through one lookup
  table. Where the 90.1 geometries tag a name differently, the 90.1-2019 tag applies;
  each such name is listed with its reason in `sources/iecc-commercial-zone-aliases.json`.
- **Programs:** one per space type, area-weighted over its zones with their
  multipliers. The IDFs are complete models, so an absent object is a source zero.
- **Type names:** atlas names (MediumOffice, not OfficeMedium); the PNNL name is kept
  as `pnnl_building_type`.
- **Mixes:** the composition-policy recipes of the same building type, weighted by
  IDF zone floor area times multiplier.

## Values that differ by climate

Loads are mostly the same in all 19 locations of an edition. Where one differs, mostly
IECC 2021 lighting, `value` holds the most common value and `value_by_climate` the
others, for example `{"0B": 6.59, "1B": 6.59}` for the 2021 medium office (Program
JSON 5.2.0). Zones 7 and 8 have no moisture regime in the source; the atlas labels them
`7A` and `8A` and keys their construction contexts `7-a` and `8-a`.

IECC programs export in the `source` version only. They hold source values with no
fillings, and the `filled` version's water-heating fold needs source water heaters,
which are deferred with the systems.

## Constructions

- **Sets:** one per folder, with 19 contexts, from the IDF constructions and materials
  (detailed construction JSON 4.2.0).
- **Assignments:** where a component varies, by story position (ground, middle, top) and
  space type. Surfaces no rule explains keep surface-level assignments.
- **Infiltration:** the IDF design-flow rules per zone, with their schedules inline, as
  the `source_design_flow` method. There is no natural-ACH value.
- **Window ratios:** the 15 whole-building values are on the set; programs carry their
  own by direction.
- **Unified representation:** from release 1.6.0 (ADR 0045). Each context holds a
  building-level equivalent weighted by the net surface areas of its IDF;
  `--representation unified` exports it as construction-equivalent 3.1.0. Release 1.3.0
  to 1.5.0 refuse it.

## Services and water

- **Building services:** elevators, reach-in refrigeration, exhaust fans, exterior
  lights and equipment, and refrigeration cases and racks.
- **Hot-water draws:** they keep their zones and EnergyPlus gain fractions.
- **Out of scope:** HVAC, plant and water heaters, as for the DOE reconciliation.
