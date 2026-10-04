# Resolution supplement v0.3.0

An incremental deterministic-coverage supplement to atlas v0.2.0. Schema version
0.3.0; generation date 2026-10-04. Earlier atlas/supplement snapshots are immutable.

## Added data

- 713 user-reviewed program gas-equipment absence cases now have opt-in constant
  zero schedules and 0 W/m2 densities: 1,426 resolution rows. Positive loads,
  existing/additional schedules and unreviewed IDs block the rule. Building gas
  heating/water heating and direct/custom-load variants remain separate.
- Three zero-occupant dwelling fixtures receive five fixed default refrigeration
  profiles: three refrigerators and two freezers. The low-rise apartment's
  explicitly absent freezer is zero. Hourly fractions and monthly multipliers
  come from the pinned source default table; no live temperature feedback.
- Source evidence lock version 3 adds primary definitions for HVAC unavailability
  and its sampling dependencies. All ten unavailable-day fixtures are occupied;
  vacancy is a different control.

There are 2,125 resolutions for 754 records. Remaining commercial fields: 495
water, 24 cavity electric equipment, 19 heating and 19 cooling schedules.
The non-cavity assessment has 523 gaps: 485 water and 38 thermostats. Residential
non-exported end uses and availability overlays retain their own documented gaps.
This is not full schedule coverage. Full or near-full deterministic coverage
must precede shipping either parametric generator.

## Consumer migration

Use the supplement's own resolution schema. New rule enums are
`reviewed_no_gas_equipment` and `fixed_background_default`; `W/m2` is a new
resolution unit. Base atlas tables and their null meanings do not change.
Consumers must explicitly opt into these separate resolved values.

A fixed default reference has `fixed_schedule_id` and
`schedule_file="fixed-background-schedules.json"`. Look up the shared table,
select Monday-Friday weekday or Saturday-Sunday weekend hourly fractions,
multiply by the January-December month multiplier, and divide by `peak_divisor`.
Use explicit calendar/local standard time; hour 0 is [00:00,01:00). No holiday
or design-day override is claimed. Values are dimensionless use fractions;
equipment magnitude/efficiency/usage factors are not encoded in the shape.

All 83 pre-existing profile/index artifacts are byte-identical to supplement
v0.2.0. Their execution metadata remain historical; the new fixed defaults are
a separate variant. Retrieve the locked primary evidence before verification:

```powershell
python -m scripts.fetch --lock sources/schedule-evidence-lock.json
python -m scripts.resolve --verify
```

For the catalogue, complete ZIPs preserve every frozen file. Identical current
profile downloads reuse historical URLs through a download map. Derived search
indexes retain record titles and full guide text without duplicating
record evidence. Entry tables, provenance, plot data and canonical downloads are
retained. The publication check enforces a conservative 1,000,000,000-byte ceiling.

The proposed source-conserving program-level hot-water allocation equivalent,
its Medium Office pilot and release sequence are in
[ADR 0006](adr/0006-deterministic-coverage-release.md). The 495 water gaps remain
unresolved until fixture/service-program allocations have supporting evidence.
