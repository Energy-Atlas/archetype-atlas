# Schedule generator plan review response

Review date: 2026-10-14. All five requested revisions are incorporated in the
[implementation plan](../superpowers/plans/2026-10-13-schedule-generator.md)
and [design](../superpowers/specs/2026-10-13-schedule-generator-design.md).
Annual-total conservation for both source families remains unchanged.

## Known target and realization amplitude

The aggregate/reference annual target represents a known or calibrated quantity.
The effective magnitude is the normalization amplitude conditioned on a sampled
temporal schedule. The revised contract separates `reference_target` from
`effective_magnitude`, and retains the source definition, units, integral and
scaling receipt. It does not call the amplitude installed/nameplate capacity or
automatically cap it at a source rating. A separately requested physical capacity
constraint remains a distinct model condition.

The formula is unchanged: effective magnitude equals the known annual target
divided by the emitted schedule integral. Tasks 2, 6 and 8 test this for both
residential and commercial loads, including short/long operating-hour samples.

## Source RNG behavior takes priority

The pinned ResStock source was inspected and its cached bytes verified against
`sources/schedule-evidence-lock.json` before revising the plan.

The [generator](https://github.com/NatLabRockies/ResStock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/BuildResidentialScheduleFile/resources/schedules.rb)
defines a main occupancy/offset stream and six ordered end-use seed slots:
hygiene, dishwasher, clothes washer, clothes dryer, EV and cooking. These are
actual upstream streams, not proposed atlas subdivisions. Lighting and plugs
depend on the common occupancy trace. Sink/shower/bath share hygiene draws;
appliance water/power and washer/dryer routines retain their source dependencies.
Excluding EV output must not remove its seed slot and shift the cooking seed.

The [multifamily measure](https://github.com/NatLabRockies/ResStock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/BuildResidentialScheduleFile/measure.rb)
cumulatively multiplies the current seed by each unit's one-based position.
For master seed 42, the first three unit seeds are 42, 84 and 252; a zero seed
remains zero. Unit order is therefore significant. The plan preserves this
default instead of replacing it with key-hashed seeds or rejecting native seed
repetition. Master input validation and derived integer size are distinguished.

Tasks 3, 5 and 8 now compare actual source order/coupling. Independence assertions
are limited to branches demonstrated independent upstream. Any necessary wrapper
adaptation is named in the receipt and tested separately. ComStock's inspected
[sampler](https://github.com/NatLabRockies/ComStock/blob/3c103063c0debb177a200dd1df8406b8d0f8d515/sampling/tsv_sampling.py)
uses NumPy pseudorandom matrix draws; its initialization/layout must be
inspected separately rather than assumed to match Ruby's RNG.

## Source-required special profiles only

The rule/calendar adapter now handles only representations required by the
selected commercial or companion source object. Public special profiles are
optional. ResStock's weekday/weekend activity mechanism receives no invented
holiday/design-day abstraction. Existing relevant source selectors, precedence
and design-day values are retained. Tasks 3 and 6 explicitly test this boundary.

## Numerical equivalence and integrity are distinct

Forced nine-decimal rounding, generated-array content hashes and cross-machine
API/CLI bundle or ZIP hash equality are removed as acceptance criteria. Generated
IDs are scoped references. Comparisons resolve actual constituent/demand/slot
relationships and ignore irrelevant JSON formatting, key order and administrative
paths/timestamps.

The plan specifies tolerances by quantity: raw fractions use relative 1e-6 and
absolute 1e-8; temperatures use absolute 1e-4 degrees C; activity uses relative
and absolute 1e-6 W/person; annual targets use relative 1e-8 with declared absolute
unit tolerances. Export-only references additionally allow their stated source
quantization interval. Discrete decisions and supported RNG draw vectors remain
exact where the source permits them; continuous tolerance cannot excuse a changed
event or selected option.

SHA-256 still locks immutable sources, packaged resources, manifests and actual
frozen artifact bytes. Checking a stored artifact's integrity is distinct from
comparing a freshly regenerated numerical realization. Existing frozen atlas
release checks remain untouched. Tasks 2 and 9 enforce these distinctions.

## Deliver complete families progressively

Task 9 now ships M1 before Task 10 broadens coverage. M1 includes a representative
ResStock multifamily dwelling family and a source-bound Medium Office case, all
advertised active channels, repeated units, mixtures, source parity, conservation,
bindings and independent offline operation. Its manifest states supported
program/configuration/weather/template domains and the remaining coverage.

All 1,900 definitions/378 compositions and all 16 DOE reference locations are
eventual coverage objectives, not prerequisites for M1. Later family additions
repeat the same evidence and shipping gates and receive new immutable versions.
Unsupported channels inside an advertised milestone block that shipment;
unsupported families outside it remain explicit and do not block an already
usable milestone. Full catalogue completion is not claimed prematurely.

## Current status

Only planning/design documents were revised. No generator code was implemented,
no source behavior was modified, and no release was shipped by this review.
Implementation-plan review and execution-method selection remain pending.
