# ADR 0006: Deliver deterministic coverage before generator interfaces

Date: 2026-10-04. Status: accepted under the user's explicit annotation decisions.

## Release order

Prioritize a full or near-full coverage release of preprogrammed schedules. Ship
neither a ResStock nor a ComStock parametric generator before that milestone.
ADR 0005 preserves the future direction; its interface discussion comes later.
The existing extraction and reproducibility scripts remain research tooling.
Incremental supplements may close reviewed gaps without claiming full coverage.

## Gas equipment

Adopt constant-zero gas equipment fractions and 0 W/m2 gas equipment density for
the exact 713 reviewed program records where both source schedule and density are
absent and the pinned clean space-type recipe creates no gas equipment. Preserve
the original nulls in atlas v0.2.0. Publish the zero as a separate opt-in research
variant, backed by table-field and source-code evidence. Reject positive densities,
existing schedules, additional gas schedules and unreviewed IDs. This concerns
program gas equipment, not gas heating, water heating, whole-building fuel status,
or a model with pre-existing direct/custom loads.

## Three zero-occupant dwelling programs

| Source fixture | Program | Refrigerator | Freezer |
| --- | --- | --- | --- |
| 165449 | SingleFamilyDetached dwelling | EF 17.6 | EF 12, National Average |
| 494980 | MultiFamily5PlusLowRise dwelling unit | EF 17.6 | None: zero |
| 447245 | SingleFamilyDetached dwelling | EF 19.9 | EF 12, National Average |

Extract the pinned default table's 24 weekday fractions, 24 weekend fractions and
12 monthly multipliers for refrigeration. Store these shared finite tables once,
with row locators, original values, units, transformations and hashes. The fixed
normalized fraction is `hour_fraction * month_multiplier / maximum_product`.
Monday-Friday use weekdays; Saturday-Sunday use weekends; intervals start at the
hour in local standard time. No holiday/design-day override is reported for these
fixed variants. A finite annual export is reproducible for any explicit calendar.

This is a user-selected fixed default variant, not a measured household history
or upstream full-model execution. It needs no weather or appliance temperature;
the alternative temperature-coefficient model is outside this release. Retain
source monthly seasonality as a preprogrammed table, without live temperature
feedback. Appliance efficiency and usage multipliers affect magnitude, which is
outside the requested normalized-shape scope. Positive fixed profiles cover only
selected refrigeration background loads; zero occupants alone cannot determine
lighting, TV, other plugs, EV charging or fixture draws.

## Program-level hot-water equivalent: proposed next coverage step

Represent water as local fixture draw demand. Keep heater firing, storage losses
and circulation-pump operation separate. Retain source water schedules when
available. An explicitly unassigned/no-fixture program has a zero **local draw**
baseline; a missing source input without supporting allocation evidence remains
unknown. The 495 remaining source nulls are not proof that the actual programs
lack plumbing: the inspected generic recipe assigns no local WaterUseEquipment,
but another prototype path may assign demand at a building or service-zone level.

For an allocation-equivalent variant, first inventory the pinned prototype's
fixture/draw objects and schedules, then associate them with demand-serving
programs using explicit source mappings. For program p, combine fixture flows
as `q_p(t) = sum_i Q_i * f_i(t)`; export `q_p(t) / max_t q_p(t)` and retain the
source Q_i and allocation weights as provenance even if magnitudes are not a
delivered target. Require nonnegative allocations and equality of summed program
draw to source building draw at every interval. Keep fixture and appliance draws
distinct so dishwasher/washer water is not counted twice. A program served by a
shared restroom may receive an allocation equivalent only as a clearly labelled
variant; do not assert that fixtures physically lie in that program.

Examples: restaurant kitchen retains dishwashing/preparation demand; dining can
retain zero local fixtures and a separately mapped shared-restroom allocation.
Hotel guest-room and laundry draws stay separate; a corridor's local draw is zero
unless a source fixture is assigned there. Office sanitary demand follows its
source restroom/service-zone mapping. Never synthesize every hot-water profile
by copying occupancy: event timing and fixture demand differ.

Build and validate a Medium Office equivalent first, then expand by building,
program and template. Publish per-record status `source`, `reviewed local zero`,
`allocation equivalent` or `unknown`, with a coverage denominator and remaining
gaps. This annotation round documents that method; it does not invent positive
flows or claim the 495 gaps have been resolved.

Concrete pilot candidate: atlas v0.2.0 already contains
`OfficeMedium BLDG_SWH_SCH` (`schedule-1a7eda5cfd8f681cc7d7`), alongside the
Small/Large Office building-water curves. Inspect its complete source rules and
provenance in the canonical schedule table. Verify which prototype/template
references it before assigning an office sanitary-demand equivalent. A known
building-water curve supplies timing; it does not by itself establish the
allocation to a specific program or the physical location of fixtures.

## HVAC unavailability is separate from vacancy

The source defines unavailable days as equipment unavailability and cites 2020
RECS. Heating sampling depends on cooling unavailability, federal poverty level
and building type; cooling sampling depends on poverty level, building type and
tenure. Vacancy is a separate source option/control. All ten affected atlas
fixtures are explicitly `Vacancy Status=Occupied`, with 1-5 occupants, including
the year-round unavailable case. No vacancy assumption follows from those options.
Nominal setpoints remain separate from future equipment-availability overlays.

Primary references and SHA-256 receipts are in the active evidence lock. See
[source review](../schedule-source-review.md) and [future generator decision](0005-parametric-schedule-generators.md).

## Subsequent implementation decision

[ADR 0007](0007-program-water-equivalents.md) supersedes the pending pilot and
availability-overlay scope above: execute the Medium Office fixture draw
equivalent on its existing office program, and exclude HVAC equipment-unavailability
overlays from the deterministic schedule release. Preserve raw source options and
historical notes. The published water pilot closes zero source nulls because that
office already has its source schedule. Coverage-first delivery remains in force.
