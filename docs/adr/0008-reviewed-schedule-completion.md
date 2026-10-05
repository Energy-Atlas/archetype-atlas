# ADR 0008: Source-bound finite schedule completion

Accepted 2026-10-04 under the user's approved scope. Original source nulls and
historical releases remain immutable. New resolutions are additive variants.

Refrigeration is installed as separate equipment by the pinned ResStock appliance
routine. A missing stochastic column proves neither absence nor inclusion in
miscellaneous plug loads. Extend the explicitly selected fixed default variant to
all 41 fixtures: 54 remaining positive shapes and 22 selected absences. Primary
refrigerators ordinarily use temperature coefficients; the user-approved fixed
variant deliberately uses source fractions without temperature feedback.

Execute upstream operational zero-occupant rules for the three exact vacant
fixtures (165449, 494980, 447245). These support 25 remaining foreground/draw zeros
and three dwelling exterior-lighting zeros. Export source exterior fractions for
38 occupied fixtures. Multifamily dwelling exterior loads do not establish shared
or common-area lighting. No occupied missing stochastic column may receive an
invented fixed fallback. Pinned execution uses latest ERI, not ASHRAE140.

Inspect thermostat creation, zone recreation, HVAC assignments, late custom tweaks
and transfer air for 19 exact SmallHotel/HighriseApartment programs. Executed
OpenStudio phases at climate 4A show dedicated zones with empty dual-setpoint
controllers, no HVAC/air loops/ideal loads or mixing. Mark direct controls inactive;
do not manufacture temperature sentinels. Passive heat transfer remains possible.
This is a pre-sizing phase inspection, not a complete simulation or successful
forward translation (the partial models omit constructions).

Extract all main, booster and laundry fixture paths across 83 prototype pairs.
Attach exact source tags to existing programs; do not invent restroom programs.
Keep 59 unallocated building-service rules separate. Heater location is not fixture
location. Preserve 28 schedules' rules, dates, selectors, design days and order.
Normalize draw fractions and compatible rated flow together to conserve every
interval. No-local fixture evidence closes 206 gaps only where no unallocated
service prevents a complete program-level interpretation. Retain 279 allocation
unknowns; do not copy occupancy or assign shared demand twice.

EV is excluded from active/new schedule outputs, catalogue presentation and
coverage denominators. Immutable source and historical snapshots retain their
original contents for provenance. HVAC unavailability remains excluded. Shipping
parametric generators follows the finite coverage milestone.

Evidence retrieval is checksum-locked by `sources/completion-evidence-lock.json`.
Execution receipts retain exact fixture/source/runtime bindings and reproducible
inspection scripts. The scope policy is versioned independently from frozen data.
