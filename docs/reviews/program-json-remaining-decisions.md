# Program JSON: follow-up decisions

Date: 2026-10-11. The approved ADR 0016 completion rules are implemented in the
version 3 exporter. This document records the additional choices exposed by
source recovery. The user accepted the reference calendar and left both water
effects outside program scope on 2026-10-11. The machine-readable
`program-json-completeness.json` receipt lists affected program IDs.

## Equipment heat fractions: reference calendar

**Field:** `loads[].heat_fractions`, for aggregated ruleset equipment whose
component heat fractions differ.

**Pattern:** commercial mixtures combine equipment with different operating
hours and heat fractions. Annual energy weights depend on weekday alignment
and holiday dates. Residential schedules already specify their 2007 calendar.

**Proposal:** use 2007 with no designated holidays as the documented reference
for exported constant fractions. Preserve holiday and design-day rules for
simulation, and retain every component schedule so consumers can reaggregate
on another calendar. The current implementation records this accepted
choice in aggregation metadata and marks affected exports with
`accepted_decisions: ["ruleset_heat_weighting_calendar_2007_no_holidays"]`.

**Alternative:** require the simulation calendar before aggregation. That makes
the constant fractions model-specific instead of a single catalogue value.

**Status:** accepted by the user: “OK”. The calendar is now an approved policy,
not an unresolved assumption.

**Your comments / decision:**

<!-- Write here. -->

## Residential non-metered water-use heat gains

**Proposed field:** separate signed thermal gains, distinct from electricity
and fuel consumption.

**Pattern:** 38 occupied fixtures have both negative sensible and positive
latent gains from general water use. The three vacant fixtures have zero.
The pinned source's `Defaults.get_water_use_internal_gains` and
`InternalGains.apply_general_water_use` supply the magnitudes and heat fields.
Source default schedule rows 5–7 supply a complete profile (5,000 EFLH in 2007);
the frozen stochastic release has no channel for these gains.

**Proposal:** add two non-metered gain objects per occupied fixture: signed
sensible power with radiant fraction 0.6, and latent power with latent fraction
1. Source-derived design powers range from −116.29 to −25.29 W sensible and
+25.66 to +118.00 W latent. Preserve the source schedule and occupant-derived
equivalent-bedroom calculation. Do not put these powers on an electricity meter
or force the sensible value to zero to satisfy the positive-demand schema.

**Status:** user decision: “Leave both outside program scope”. Current exports
list `general_water_use_heat_gains` in `metadata.excluded_scope`. It is not
assumed zero; full residential zone-gain equivalence is not claimed.

**Your comments / decision:**

<!-- Write here. -->

## Residential distribution-waste water demand

**Proposed field:** a separately identified distribution-water demand.

**Pattern:** all 41 fixtures select uninsulated standard distribution, source
default pipe length, no recirculation and no drain-water heat recovery.
Distribution waste is positive in the same 38 occupied fixtures, zero in the
three vacant fixtures. The source formula simplifies to
`7.16 * occupants^0.7 * water_fixtures_usage_multiplier` US gal/day, or
4.296–34.0116 US gal/day across the occupied fixtures. It uses the existing
fixture schedule and 105 °F target; no new numerical default is needed.

**Proposal:** export this as a distinct distribution demand, with a binding
that prevents adding it twice when a downstream system models distribution.
Keep fixture delivered-water demand separate. Alternatively, require the water
system to create this draw from source distribution parameters.

**Status:** user decision: “Leave both outside program scope”. Current exports
list `dhw_distribution_and_system_effects` in `metadata.excluded_scope`; these
effects are not assumed zero.

All 41 source recirculation pumps are absent and their distribution energy
adjustment is 1. Water-heater losses (39 storage, two tankless systems) and the
one detailed 40 ft² indirect flat-plate solar system belong in system data.
That solar fixture is `residential_archetype-71cf018572bd7e3b4938`; an unset
scalar solar fraction does not imply zero collector contribution.

**Your comments / decision:**

<!-- Write here. -->

The three vacant source fixtures excluded from the positive water-effect
predicates are `residential_archetype-08a27444abac71d3b335`,
`residential_archetype-28457c00121833f065f2`, and
`residential_archetype-aa1f864c610bf3d98e2e`.
