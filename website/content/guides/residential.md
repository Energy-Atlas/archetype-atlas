# Residential and multifamily inputs

Two source families support apartment experiments:

- Commercial/code apartment programs describe source-defined space types,
  loads, schedules and systems in the Standards-derived benchmark workflows.
- ResStock configurations preserve jointly selected source-fixture options,
  exact option bindings, occupants, thermostat bases and runtime gaps.

Keep these families separate. A commercial apartment program is not a resolved
ResStock dwelling recipe and should not silently supply missing residential
schedules.

## Find a configuration

Select residential_archetypes in the catalogue, then a building class. Available
classes include detached and attached single-family, 2–4-unit multifamily,
5+-unit low-rise multifamily, midrise and highrise apartments, and
manufactured/mobile homes.

Each configuration shows its reported climate, stock vintage, geometry context,
selected options and the lookup records that match exactly. Unmatched selections
are listed with their source labels and reconciliation reasons. These modeled
fixtures are examples of source inputs, not population representatives.

## Thermostats and missing schedules

Heating and cooling bases are Celsius values before offsets, seasons and
unavailable-day controls. Base overlaps are flagged where present.
The site does not plot constant bases as if they were effective daily schedules.
Full profiles require the pinned generator and an explicit calendar.

Floor area remains a reported bin; exact SI area and derived densities remain
unknown. HPXML defaults, argument translation and simulation generation have not
been executed. Inspect every runtime gap before assigning inputs to dwelling
units, corridors or common areas in a separate geometry generator.
