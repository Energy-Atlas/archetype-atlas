# Schedule generator plan review response

Review date: 2026-10-14. All five original revisions and both final adjustments
are incorporated in the
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

Task 9 ships M1 before Task 10 broadens coverage. Its authoritative
[`scope manifest`](../../sources/schedule-generator-m1-scope.json) enumerates
six exact frozen ResStock low-rise multifamily configurations/weather bindings
and four Medium Office 90.1-2013 Office/Plenum source/reviewed views. M1 is
restricted to these configurations and year 2007, with variable seeds,
explicit physical scaling, repeated instances and compatible mixtures.

Complete M1 coverage means every listed case and included channel passes
source parity, conservation, binding/mixture and independent offline checks.
Tasks 1 and 9 validate the exact set; one missing/failed case or included
channel blocks shipment. The shipped manifest preserves the case set and its
version/hash, with resolved configuration/resource references and per-case
evidence. A scope change requires an explicit versioned revision; successful
cases cannot silently become the denominator.

All 1,900 definitions/378 compositions and all 16 DOE reference locations are
eventual coverage objectives, not prerequisites for M1. Later family additions
repeat the same evidence and shipping gates and receive new immutable versions.
Unsupported channels inside an advertised milestone block that shipment;
unsupported families outside it remain explicit and do not block an already
usable milestone. Full catalogue completion is not claimed prematurely.

## Final adjustment: commercial sampling preflight

The [pinned-source assessment](comstock-sampling-semantics-2026-10-14.md)
confirms that an upstream population row is not determined by one local seed.
The pseudorandom path assigns NumPy global draws through grouped/bucketed
matrices; Sobol adds Python random shifts and a pandas shuffle. Sample index,
count, bucket layout, group/vector order, prior draws and precomputed allocation
matter. Conditional option selection itself can be tested with an identical
resolved row and uniform draw.

Task 1 now requires the actual selected TSV/configuration per-parameter audit
before Task 6's kernel. The selected archive and full parameter closure are
still pending; the preliminary assessment is not a passed gate. The pure
Python seeded wrapper is explicitly labeled `atlas_conditional_seeded_v1`,
with recorded conditioning/RNG/draw policy and
`population_realization_equivalent: false`. Wrapper reproduction, conditional
selection parity and transformation parity are separate checks. Missing
selectors or unavailable source tables keep the commercial gate closed.

## Current status

Only planning/design documents, a source assessment and the planned scope
manifest were revised. No generator code was implemented,
no source behavior was modified, and no release was shipped by this review.
The user has accepted the revised direction for implementation. The two final
adjustments are incorporated; native execution can proceed in the isolated
worktree, starting with the unresolved source/configuration gates.
