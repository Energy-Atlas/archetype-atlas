# Program hot-water draw equivalents

Attach draw demand to an **existing program** when the pinned source establishes
its serving relationship. A water schedule alone does not require a new restroom
program. Keep actual source-defined restrooms or service programs if present;
leave unsupported building-to-program allocations unknown.

## How EnergyPlus represents shared demand

A shared water draw need not be assigned to a thermal zone. EnergyPlus uses a
`WaterUse:Equipment` object with peak flow, a flow-fraction schedule and water
temperatures. `WaterUse:Connections` can connect that demand to the service-water
`PlantLoop`. The equipment's zone reference is optional. With no zone reference,
the draw still loads the water system, but contributes no fixture sensible or
latent gains to a room. EnergyPlus does not automatically distribute it among
the building's zones.

The pinned Standards [water-use constructor](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/lib/openstudio-standards/service_water_heating/create_water_use.rb#L21-L102)
defaults to `space: nil`, always creates a water connection, and calls `setSpace`
only when a space is supplied. It can connect either kind of fixture to the
service-water loop. Main, booster and laundry source calls without a space are
therefore meaningful shared system demands, rather than automatically missing
EnergyPlus inputs. A fixture's name or a heater's location alone does not assign
its heat and moisture gains to a zone.

This behavior is confirmed in [EnergyPlus 24.2 water-use source](https://github.com/NatLabRockies/EnergyPlus/blob/v24.2.0/src/EnergyPlus/WaterUse.cc):
zone lookup is conditional on a nonblank zone field, and zone internal-gain
registration is conditional on a positive zone index. Stand-alone water-use
objects also exist; their energy accounting differs from plant-connected demand.
See the [Input Output Reference](https://bigladdersoftware.com/epx/docs/24-2/input-output-reference/group-water-systems.html).

Other loads have different attachment rules. People, interior lights and ordinary
electric/gas internal gains require zone/space targets (or lists); building-wide
report totals aggregate these assignments. Exterior energy-use objects and
central plant components can operate without room assignments. There is no
universal rule that all unspecified loads attach to the `Building` object.

For the atlas, two questions remain separate:

- **Source-faithful simulation:** retain the shared water service once, with its
  source curve and original zone-gain behavior. A complete building demand can
  coexist with unknown program beneficiaries.
- **Program reporting equivalent:** optionally allocate that same demand to
  existing programs using documented weights, conserving every interval. Those
  reporting weights do not establish physical fixture locations or authorize
  adding zone sensible/latent gains. That additional thermal assignment requires
  its own evidence or explicitly labeled assumption.

The 279 program allocations remain open. This clarification neither closes them
nor changes the frozen coverage denominator. The mapping, envelope, HVAC,
reference-location and model-equivalence questions also remain open.

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

## Complete commercial source paths

Commercial-completion **v0.1.0** inventories 217 fixture-demand paths across all
83 represented building/template pairs. [Browse the fixture catalogue](../commercial-completion/index.md)
for source and conserved peak-normalized plots, SI rated flows, allocation weights,
source rule order, design days and field-level evidence. Positive demand attaches
to **existing programs**, with no new restroom program. Named source restrooms
remain their original programs.

The extension closes **206 missing program schedules** with source-complete no-draw
zeros. **279 assignments remain unknown** because 59 building-service paths lack
supported beneficiaries. Known positive source assignments are retained; an
unallocated main/booster/laundry service is not copied into each program. Large
Office's three core fixture instances and source multipliers remain distinct.

The exact canonical bundle, schema, source lock, executed control receipt and
notices are in the [complete snapshot](../commercial-completion/v0.1.0/snapshot.zip).
Its [manifest](../commercial-completion/v0.1.0/manifest.json) identifies every file.
The browser [catalogue JSON](../commercial-completion/v0.1.0/catalogue.json) is a
compact presentation of the canonical packet, not the manifest-hashed file.

## Remaining program allocations

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
