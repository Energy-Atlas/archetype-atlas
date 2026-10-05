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

## Executed profiles and remaining gaps

Heating and cooling bases are Celsius values before offsets, seasons and
unavailable-day controls. Base overlaps are flagged where present.
The v0.4.0 resolution supplement provides profiles produced by pinned
ResStock/OpenStudio-HPXML code: 38 stochastic configurations, three zero-occupant
skips with explicitly zero occupancy, and 41 nominal thermostat profiles.
Use the calendar date and annual view controls to inspect actual generated hours.
Fractions are normalized shapes; selected load amplitudes remain separate.

Every profile uses calendar 2007, an hourly timestep and a fixed seed equal to
the source fixture ID. Weather is an explicitly labelled ZIP-mapped TMY3 station
proxy because the original county archive is unavailable. Nominal thermostat
profiles execute source offsets and overlap correction; equipment unavailable-day
overlays are excluded from the selected release. All 574 assessed profile fields
are supplied, with fixed refrigeration and dwelling exterior-lighting variants
added separately. Reviewed zero-occupant operational loads are zero; selected
refrigerators/freezers retain background profiles. Missing stochastic columns
alone never establish absence. See [schedule mechanisms](schedule-methods.md) for
these sources, the ten HVAC-unavailability cases and future generator decisions.

Floor area remains a reported bin; exact SI area and derived densities remain
unknown in the frozen source snapshot. Full building HPXML defaults and EnergyPlus
simulation have not been executed. Inspect every runtime gap before assigning inputs to dwelling
units, corridors or common areas in a separate geometry generator.

Download canonical annual JSON with inputs, exact argument bindings, generator
provenance and hashes, or the execution CSV. The complete supplement includes
locked retrieval metadata and upstream notices. Source snapshot values and
`simulation_ready=false` remain unchanged; the supplement is an explicit overlay.
