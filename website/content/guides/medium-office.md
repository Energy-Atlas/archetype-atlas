# Medium Office worked example

In the **v0.2.0 catalogue**, set **Building type → MediumOffice** and
**Vintage / template → 90.1-2013**. Open the building overview, then its **office**
program. The plenum program remains a separate source-defined program.

The office program's lighting value originates at **0.82 W/ft²**; the normalized
value is approximately **8.8264 W/m²**. People density originates at
**5 people/1,000 ft²**, approximately **0.05382 person/m²**. These are inputs from
the pinned OpenStudio Standards source, not measured operating values.
The detail page provides the exact canonical precision and field evidence.

## Inspect controls

The office page overlays its occupancy, lighting, equipment and control schedules.
Select Monday, then Saturday. Change the month/day to inspect seasonal rules.
Temperature profiles appear on a separate Celsius axis; activity profiles
remain in their reported units. Hover for values or expand the profile tables.

The selected specific rule is the final matching rule in source order; default
rules provide fallback. Holiday and winter/summer design-day inspection uses
explicit selectors. The date is an inspection control, not a simulation calendar.

Use **Overlay a schedule** for comparisons. An overlay is an inspection view
and does not modify the program or attach a new schedule to the atlas.

## Inspect assembly gaps

The building page lists mappings and systems. Mapping multiplicity is source
benchmark context and may overlap across HVAC services. Unknown area fractions
or conditioned states require resolution in the geometry/model workflow.
Do not infer them from a displayed mapping count.

Envelope rules are selected independently by template, climate set and the full
source predicates. The overview links to template evidence; it does not choose a
construction or invent a climate-specific copy of the office program.

Download the program and related schedules, then retain their IDs and the frozen
release manifest in your experiment. Resolve infiltration, system parameters,
control overrides and other documented gaps before simulation.
