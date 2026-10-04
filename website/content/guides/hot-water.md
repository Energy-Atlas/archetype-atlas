# Program hot-water draw equivalents

Attach draw demand to an **existing program** when the pinned source establishes
its serving relationship. A water schedule alone does not require a new restroom
program. Keep actual source-defined restrooms or service programs if present;
leave unsupported building-to-program allocations unknown.

## Medium Office pilot

The pilot covers **MediumOffice / 90.1-2013 / office**. Its source already assigns
`OfficeMedium BLDG_SWH_SCH` to the office space type. The prototype has no lumped
main peak flow, so its water routine uses the per-space-type demand path.
Fifteen distinct office spaces map to one existing office program. The water
heater's location in `Core_bottom` does not establish restroom locations.

[Open the office program](../releases/v0.2.0/programs/program-29f8fa7a1d5e5afcf1f0.md)
to inspect the original and equivalent curves in the same interactive plot.
Select weekdays, Saturday, Sunday/holiday, or a design day. Rule dates, selectors,
source order and default fallback remain intact.

The source maximum fraction is **0.57**. The equivalent fraction is `f(t)/0.57`;
its compatible peak flow is `Q*0.57`. This preserves `Q*f(t)` at every interval.
**Do not use the normalized curve with the original rated flow**, which would
increase demand. The canonical JSON retains both scaling values in SI units,
the original units and values, the allocation weight, and source locators.

Demand belongs to represented office floor area. Apply each zone's area and
multiplier once, and avoid counting overlapping HVAC service mappings twice.
Do not add a separate building-wide sanitary demand on top of these allocations.
The profile represents **mixed fixture draw at the source target temperature**,
not heater energy, heater firing, hot/cold mixing fraction, storage loss or pump
operation. Dishwasher/washer demand must remain separate when those sources exist.

[Download canonical equivalent and evidence](../water-equivalents/v0.1.0/water-equivalent.json)
· [Frozen manifest](../water-equivalents/v0.1.0/manifest.json)
· [Complete snapshot with schema, source lock and notices](../water-equivalents/v0.1.0/snapshot.zip).

This pilot validates a known source schedule. It creates **no additional program**
and closes **zero missing schedules**. It is an explicitly optional equivalent;
the original atlas and schedule supplement remain unchanged.

## Extend to missing programs

Inspect each prototype's fixture/main/booster/laundry branch and its source
schedules before assigning demand. Map serving relationships explicitly. If a
source demand serves several programs, use supported nonnegative allocation
weights summing to one. Sum weighted fixture flows in each program, normalize
after summation, and require summed allocated draw to equal source draw at every
interval. A fixture's physical location is not automatically its beneficiary.

Retain reviewed local zeros where no fixture is assigned, and retain unknowns
where allocation evidence is insufficient. Never substitute occupancy timing
for every missing water schedule. The [coverage inventory](coverage.md) describes
the remaining work.
