# ADR 0007: Attach conserved fixture draw equivalents to existing programs

Date: 2026-10-04. Status: accepted under the user's instruction to proceed.

## Program assignment

Attach fixture draw to an existing energy program when source space-type tags or
service assignments establish that relationship. Do not create a restroom or
service program solely to host a curve. A source that explicitly defines such a
program may retain it; a truly unallocated building-level demand remains a
separate service record until a defensible allocation is available.

The first pilot is MediumOffice / 90.1-2013 / office,
`program-29f8fa7a1d5e5afcf1f0`. The locked prototype input has a main water loop
but a null building-wide peak flow. The pinned `model_add_swh` therefore uses
its space-type map. `model_add_swh_end_uses_by_space` defaults to flow per floor
area, multiplies by each space's area and multiplier, and uses the space-type
water schedule. Fifteen distinct tagged office spaces map to this existing
program. Deduplicate identities across HVAC mappings; HVAC service groups are
not additional water loads. Plenums have a separately reviewed zero local draw.
The water heater's `Core_bottom` location does not locate the demand fixtures.
The source helper creates the draw without assigning a physical fixture space;
this pilot records an empty physical-location list rather than guessing rooms.

## Equivalent profile and conservation

The office source already references `OfficeMedium BLDG_SWH_SCH`. Preserve its
three ordered rules, dated ranges, day selectors, holidays/default fallback and
summer/winter design-day definitions. Its maximum fraction is 0.57. The equivalent
fraction is `f(t)/0.57`; the equivalent peak flow is `Q*0.57`. Consequently
`Q*f(t) == equivalent_peak*equivalent_fraction(t)` at every interval. The locked
per-area Q is 0.0009509957485 US gal/h/ft2, converted to m3/s/m2. Keep this scaling
metadata even though normalized schedules, rather than load magnitudes, are the
current user-facing target. Do not apply a peak-normalized curve with the old
rated flow: that would inflate demand by 1/0.57.

The reference 51 US gal/h and 53,628 ft2 table fields remain upstream evidence;
this default branch uses per-area flow and actual source space areas. The geometry
atlas supplies represented office area. Split repeated zones by their represented
areas with each multiplier applied once. Never add both the equivalent program
demand and a duplicate building-wide sanitary demand. This is mixed fixture draw
at the reported 140 F / 60 C target, not heater firing, energy consumption, pure
hot-water mixing fraction, tank losses or circulation. Appliance water remains
distinct; the pilot has no booster or laundry branch.

## Packaging and extension

Freeze an additive `data/water-releases/v0.1.0` pilot with its own versioned schema,
source lock, checksums, field evidence and reproducible extraction script. The
atlas and schedule supplement snapshots remain immutable. Attach the pilot to
the existing office page and record packet as an explicit optional variant,
with source and equivalent plots. This validates the method but closes **zero**
missing schedules: this office already had its source curve. Do not count the
equivalent as an additional program or an additional covered gap.

Next inspect each missing program's prototype main/booster/laundry paths, source
fixture schedules and serving relationships. Allocate each source draw once
across its supported programs; use weights summing to one per source demand and
test interval conservation before publishing. A service-location assignment is
not automatically a beneficiary allocation. Retain unknowns when source evidence
cannot establish one. Never copy generic occupancy timing to all water gaps.

## Release scope

The user excludes HVAC equipment-unavailability overlays from this deterministic
schedule release. Use nominal desired-temperature profiles without sampled
repair/affordability interruptions. Keep raw source options and historical
execution notes available for traceability, but stop counting unavailable-day
placement as missing work. Source setpoint offsets and overlap correction remain.
Full load magnitudes and full-model control application are also outside this
release's requested schedule coverage. The machine-readable scope is
`sources/schedule-release-scope.json`. Near-full deterministic coverage remains
the gate before shipping either source's parametric generator; no generator
interface is added by this finite pilot.
