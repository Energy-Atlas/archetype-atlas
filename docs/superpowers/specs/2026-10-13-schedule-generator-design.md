# Pure Python program schedule generator design

Date: 2026-10-13. Status: direction approved on 2026-10-13; revised on 2026-10-14 following the user's plan review on source fidelity, numerical equivalence and staged delivery. Implementation has not started.
Working branch: `codex/stochastic-schedule-extraction`, based on `c2dd1fd`.

## Intended result

Provide a separately shipped pure Python generator that maps explicit program
parameters and one seed to all included program schedules. Every output schedule
has 8,760 hourly values; the number of schedules depends on the active program
loads, controls, shared services and constituent instances. Programs reference
schedule slots instead of embedding a particular realization.

ResStock supplies stochastic residential time allocation, including apartment
units. Actual program definitions supply load magnitudes and their physical
bases. Both residential and commercial generated loads preserve the definition's
annual energy or volume. A definition with a reference magnitude and schedule
supplies its annual target through their integral. Commercial operating hours
are sampled from the seed using applicable ComStock source distributions, and
its own transformations coordinate the related schedules. These samples change
temporal allocation; effective magnitudes are rescaled so they do not change
the annual total.

The generator supplies energy semantics, not geometry or population weights.
Retain existing-stock and code/prototype identity, source-fixed channels,
explicit absences and unknowns. Frozen releases and existing Program JSON v3
remain immutable reference cases. Production integration follows the protected
`main` pull-request policy; this work remains in its separate worktree.

## Accepted user requirements

- Generation runs entirely in Python. Ruby, OpenStudio, EnergyPlus, external
  services and network access are not required to generate a packaged realization.
- The generator returns a variable number of schedules, each with exactly 8,760
  hourly samples. Variable length does not mean a variable simulation horizon.
- ResStock-derived schedules become the apartment-unit generator method, with
  combined provenance labeled explicitly. Apartment common spaces retain their
  applicable commercial or fixed methods.
- Commercial operating hours are sampled from the supplied seed, rather than
  required as caller-selected hours.
- Residential constituents receive upstream-assigned unit seeds under one master
  seed, preserving source order and any source-defined degeneracy. Commercial
  constituents in the same coordinated operating group share sampled parameters.
- Generate constituent schedules before computing mixture schedules. A mixture
  can contain any supported number of members, including repeated units.
- Scale annual-energy and annual-volume magnitudes against the generated
  schedule integral rather than reusing a magnitude fitted to another realization.
- Apply annual-total conservation to both residential and commercial loads,
  including commercial definitions originally expressed as design power or
  power density with a reference schedule. Sampled operating hours change the
  temporal distribution only.
- Treat the aggregate/reference annual target as known or calibrated, and the
  schedule-conditioned effective magnitude as realization-specific normalization.
- Preserve upstream RNG draw order and coupling ahead of insertion/removal
  invariance; identify deliberate departures explicitly as adaptations.
- Expose source-required rule/special-profile semantics only. Do not invent a
  generalized schedule language or extra ResStock holiday/design-day behavior.
- Accept generated results by discrete/source and numerical equivalence, not
  cross-machine JSON hashes. Keep immutable source/resource integrity locks.
- Ship a usable residential/commercial family milestone before broad catalogue
  expansion, with explicit supported scope and remaining coverage statuses.

## Existing repository and primary mechanisms

The frozen definition catalogue contains 1,900 programs and 378 mixtures.
Mixtures contain between 2 and 29 source members. The base atlas contains 768
commercial source programs across 17 building classes and five templates, plus
41 residential fixtures. These counts describe catalogue records, not stock
frequencies; source and reviewed views are distinct.

`scripts/run_residential_profiles.rb` runs a pinned ResStock generator for
reference fixtures. `scripts/residential_profiles.py` supplies the selected
inputs and verifies outputs. `data/program-inputs/residential-v1.json` recovers
residential annual energy and daily water use, then derives effective power and
flow using each reference schedule integral. `scripts/program_json_v3.py` exports
the completed definitions. `scripts/program_json_aggregation.py` conserves
compatible equipment trajectories and annual heat partitions. These are useful
reference mechanisms, but do not yet implement a shipped parametric generator.

ResStock revision `dd25369f41a83a0767aefeeac0b6f8a0b0edd649` defines occupant
activity chains, independent end-use random streams, appliance/event data,
state/month offsets and an additional unit-level time offset. Its official
measure supports all multifamily dwelling units. The current atlas runner is
limited to a particular hourly calendar and supplies additional thermostat and
fixed-default schedules outside the activity generator.

ComStock revision `3c103063c0debb177a200dd1df8406b8d0f8d515` transforms
prototype schedules using weekday/weekend operating hours and separate occupancy
and lighting/equipment adjustments. Its `resources/Gemfile` requires
`openstudio-standards = 0.8.6`. The atlas's independently selected Standards
revision `c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907` must not be asserted to
be that runtime dependency. The commercial port must trace the selected upstream
transformation to its actual dependency and retain the atlas's base-rule identity.

ComStock's public `sampling/tsv_sampling.py` specifies dependency-aware sampling
and ordered cumulative probabilities; public `sampling/tsvs/tsvs-vNN.zip`
archives contain the probability tables. An options lookup alone does not supply
the probabilities. Bind one explicit table version to a source configuration,
record its selection rationale, and lock the archive and selected members before
porting its sampling behavior. Do not choose a table version merely because its
filename has the largest number.

Existing locks pin the ResStock mechanism and selected Standards/ComStock files.
`sources/schedule-generator-inspection-lock.json` additionally pins the inspected
ComStock dependency declaration and sampler documentation/code. Retain upstream
license notices with extracted data and translated code.

## Generator and program contracts

The Python entry point is `generate(params, seed) -> bundle`. Provide a CLI that
reads the same request as strict JSON and writes JSON. Program and
bundle schema versions are explicit; introduce a separate generated-program
contract instead of silently changing Program JSON v3.

Program definitions expose stable schedule slots, for example
`occupancy`, `lighting_interior`, `equipment`, `heating_setpoint` and
`cooling_setpoint`. Each load/control refers to its slot. A generator recipe
identifies the method, fixed source inputs and required instance bindings.
The output bundle resolves these slots to realization-specific schedule IDs.

The bundle contains:

- `schedules`: an ID-indexed collection of dimensionless, temperature or activity
  schedules, each with 8,760 finite hourly values and an explicit unit;
- `bindings`: program/constituent slot references, resolved schedule IDs, known
  aggregate/reference targets and schedule-conditioned effective magnitudes with
  their physical basis and unit;
- `constituents`: stable instance keys, generator method and derived seed receipts;
- `generation`: algorithm version, complete effective arguments, master seed,
  calendar, operating-hour samples, weather/source resource identities and hashes;
- `metadata`: original definitions, scaling receipts, source provenance, rule
  calendars/design days, scope exclusions and interpretation notes.

This keeps the useful mapping `args + seed -> schedules`, while shipping the
magnitude bindings required to use newly generated schedules correctly. Replacing
only a schedule reference while retaining a reference-fitted wattage is invalid.

Use an explicit non-leap Gregorian year; the initial default remains 2007 to match
the atlas references. Reject leap years rather than dropping February 29.
Hourly values describe `[hour, hour+1)` in local standard time. Apply no implicit
DST, timezone conversion or holiday calendar. Retain holiday, design-day,
date-selector and precedence semantics where the selected source mechanism
actually contains them. ResStock's activity chains use weekday/weekend selection;
do not add a holiday or design-day layer to those chains. Public special profiles
are optional and limited to source-required representations. All constituent
arrays share the same calendar; no generalized rule language is introduced.

Inputs include the program/recipe IDs, explicit household arguments, stable
constituent keys, mixture weights and scaling bases, operating-group IDs,
calendar, source variant and required location/weather bindings. Required
physical inputs cannot be guessed from names, population prevalence or missing
values. Commercial operating hours are outputs of seeded sampling. Record every
sampled parameter and its distribution row.

## Annual allocation and load scaling

Port the pinned activity-chain and end-use event mechanism together with its
calibration resources. Preserve occupancy/end-use relationships, internal random
streams, weekday/weekend behavior, state/month offsets, appliance presence,
lighting location inputs and ceiling-fan weather dependence. Appliance power
samples can influence a generated shape; they do not replace the program's
annual load definition.

In calibration/inverse modeling the aggregate/reference annual energy or volume
is known, while behavior and its temporal allocation are latent. Keep this known
target separate from the schedule-conditioned effective magnitude. The latter
is a normalization amplitude for this realization, not necessarily an installed
capacity or physical nameplate power density. Changing a seed changes the shape
and this amplitude together while retaining the known target.

For each residential or commercial time-allocated energy demand, let `g[h]` be
the emitted normalized generated shape and `H_g = sum(g[h]) * 1 hour` its
equivalent full-load hours.
With a direct annual definition `E_Wh`, use:

```text
P_generated = E_Wh / H_g
q[h] = P_generated * g[h]
sum(q[h] * 1 hour) = E_Wh
```

If only a reference magnitude `P_reference` and compatible reference schedule
`r[h]` are defined, derive the reference annual energy first:

```text
H_reference = sum(r[h]) * 1 hour
E_Wh = P_reference * H_reference
P_generated = P_reference * H_reference / H_g
```

Apply the same equations to power density in W/m2 without inventing floor area.
A basis of one dwelling is not convertible to floor area without an explicit
compatible area binding. Prefer recovered original annual kWh to an annual total
reconstructed from a rounded reference magnitude. Preserve fuel auxiliaries and
distinct physical hosts separately.

For volume, use `V_generated = V_annual_m3 / (sum(g[h]) * 3600 seconds)`.
Recover a reported daily volume using the explicitly bound 365-day calendar.
Preserve target temperature, fuel and heat fractions; water volume conservation
does not assert conservation of weather-dependent water-heating energy.

Example: a definition is 10 W/m2 with 2,000 reference full-load hours, so its
annual target is 20,000 Wh/m2. A generated shape with 1,600 full-load hours uses
12.5 W/m2 as its effective magnitude. The original 10 W/m2 stays in provenance.

Compute scaling from the actual emitted numeric values, after any declared
rounding. Keep fractional schedules in their valid range by changing effective
magnitudes rather than multiplying fractions above one. Store the source target,
original unit/value, reference integral when used, generated integral,
conversion, scaling factor and extraction date per demand.

A zero target yields an explicit zero demand. A positive target with a zero
generated integral is an error with the affected channel and arguments; do not
divide by zero, erase the demand or silently draw another seed. Missing targets
remain unresolved and block a ready realization. There is no arbitrary cap that
silently changes annual totals. Preserve reported nameplate values separately;
do not automatically use them to cap or reject a normalization amplitude. An
explicitly selected physical capacity constraint is a separate model condition
and must be reported if incompatible with the calibrated target/shape.

The integral adjustment applies to both source families' annual energy/volume
allocations, including reference-derived commercial and apartment budgets.
Conservation refers to the load-weighted annual integral: the product of effective
magnitude and schedule sum. A fractional shape's sum can change while that product
remains constant. It does not scale temperatures, activity W/person, installed
capacity or the number of residents.
Occupancy fractions describe actual modeled residents and remain bounded by one;
their stochastic person-hours can vary. Preserve fixed/background refrigeration
and source-defined zero-occupant behavior through their applicable companion
recipes. An absent stochastic column does not prove equipment absence.

For a DOE/Standards apartment unit, retain actual definition magnitudes and
controls and label the ResStock time-allocation substitution. Aggregate electric
loads cannot be assigned guessed appliance energy shares. Apply separate
generated end-use shapes only where definitions supply those shares; otherwise
use an explicitly defined compatible aggregate channel or report the binding
as unresolved. No residential behavior is transplanted into hotel guestrooms
merely because the space is named a room.

## Commercial generation

Sample the required operating-hour fields using the selected public source
tables, their dependency selectors, option order and conditional relationships.
Use seeded pseudorandom sampling; full-stock Sobol sampling and prevalence-based
building selection are outside the generator's purpose. Sampling the schedule
parameters does not resample program intensity, geometry, stock vintage or
construction properties.

Apply the source's operating-hour transformations and its conditional exclusions
to the original program schedules. Related occupancy, lighting, equipment,
thermostat and applicable water channels use the same operating context. Preserve
source-fixed schedules when the method does not transform them. Handle constant
profiles, zero/full-day operation, overnight wrapping, weekday/weekend distinctions,
ramps, rule order and design-day treatment explicitly.

For commercial definitions expressed as design power or power density, calculate
the annual target from the unchanged source/reference magnitude and its reference
schedule, before applying sampled operating hours or any sampled shape adjustment.
After the source transformation, recompute the effective magnitude using the
generated schedule integral. Longer sampled hours distribute the same annual
target across more time; shorter sampled hours concentrate it. An explicitly
annual-energy-defined commercial demand uses that annual target directly.

This final normalization is the user's atlas experimental policy. It is separate
from the upstream ComStock shape transformation and must not be presented as
unmodified ComStock annual-consumption behavior. Preserve the original source
magnitude and both schedule integrals in provenance. Record the magnitude method
on every binding: `annual_budget`, `reference_budget_substitution`, or a
non-energy control method. There is no active commercial design-magnitude
exception to annual-total conservation.

One coordinated commercial operating group receives one sample; room/member
seeds do not independently shift that group. Distinct tenants can supply distinct
stable group IDs under the same master seed. The generator carries no implicit
national prototype versus California/DEER substitution. Regions and templates
retain their actual applicability and source family.

## Seed derivation and reproducibility

Require an explicit unsigned 64-bit master seed; reject booleans and invalid
numeric values. Preserve the inspected source's seed initialization, random draw
order and coupling. The pinned ResStock generator has a main occupancy/offset
stream and ordered hygiene, dishwasher, clothes-washer, clothes-dryer, EV and
cooking streams. Sink/shower/bath share hygiene draws; appliance power/water and
washer/dryer routines retain their source dependencies. Keep the EV seed slot
even when EV output is excluded. Do not introduce additional end-use substreams.

The official multifamily measure cumulatively multiplies the current seed by
each unit's one-based position. Preserve that default unit-order behavior and
record the resulting seeds, including source-defined zero-seed degeneracy.
Native derived integers need not fit the master seed's 64-bit input range.
Unique constituent keys resolve references, not a promise of reordering or
insertion invariance. Test independence only where the source actually provides
it. Any different allocation/grouping policy is a declared, versioned adaptation.

Generation is offline and deterministic for the complete versioned request,
including source-significant order and locked inputs, within supported/common
environments insofar as the source mechanism permits. Require exact discrete
decisions and supported RNG draw vectors; compare continuous schedule values
with stated source/precision-aware tolerances. Same-input reference comparisons
retain source arithmetic and call order. Serialization differences do not alter
scientific acceptance. Do not round values merely to force cross-machine hashes.

SHA-256 verifies immutable source archives, packaged resources and frozen
manifests. A frozen generated example may have an integrity hash, but a fresh
equivalent realization need not reproduce that hash. Match generated outputs by
slots, units, parameters, source decisions and numerical values. IDs are scoped
references, not scientific equivalence tests; administrative metadata is separate.

## Mixtures and physical conservation

Resolve each constituent's active definitions, generate its related channels and
derive its effective magnitudes before composing any mixed load. Repeated
residential instances retain separate instance keys even when their program IDs
are identical. Expose constituent outputs for inspection and reuse.

For compatible area-based components with weights `w_i`, effective magnitudes
`D_i` and generated fractional schedules `s_i[h]`, compute:

```text
q_mix[h] = sum(w_i * D_i * s_i[h])
D_mix = sum(w_i * D_i)
s_mix[h] = q_mix[h] / D_mix
```

Require finite nonnegative weights and an explicit recipe denominator. Convert
bases only with supplied physical scaling inputs. Keep different fuels and
physical hosts separate. Do not count a shared-service demand once per member.
Zero groups require an explicit zero result and no division. Preserve annual
energy and volume after constituent scaling and composition. Weight constant
equipment heat fractions by annual component energy, retaining the existing
documented limitation that constant fractions approximate hourly partitions.

Keep occupancy activity coupled to its corresponding constituent. Existing
mixed thermostat logic remains the explicit area-weighted representative
approximation over members with that service active; inactive members supply no
artificial extreme temperatures. Temperature averages are not conserved heat
trajectories. Retain the applicable member fraction and original control objects.

## Coverage and source packaging

Inventory every current source/reviewed program and composition. For each channel,
record its method, source variant, binding status and climate/vintage dependencies.
Normalize identical recipes rather than duplicating a Cartesian product. Shared
applicability requires evidence; unknown applicability is not shared applicability.

Residential occupant chains have no direct vintage selector. Equipment,
thermostats and applicable default recipes can depend on vintage-selected inputs.
State/month offsets, solar/location inputs and weather-dependent channels require
more than a climate-zone label. Use the existing approved DOE 16-location set
for reference weather cases and preserve both 3B locations. Acquire/bind these
incrementally with supported families; the entire set is not a prerequisite for
the first shipment. Lock exact EPWs and their geographical bindings before
asserting that reference-location coverage.
Keep earlier station-proxy fixtures labeled as their original variants.

Retain the existing exclusions of residential EV and HVAC equipment-unavailability
overlays. Thermostats describe nominal desired temperatures. New generator
coverage does not imply new coverage of ventilation, infiltration or system
sizing. Source-fixed/background schedules are valid generator outputs with
their method recorded; unsupported active mappings cannot be counted as complete.

Fetch and extraction use Python, immutable raw artifacts and SHA-256 locks.
Package only the required calibration tables and recipes with upstream notices,
member hashes and source locators. Distributed generation loads these resources
locally; extraction/build performs retrieval separately. Original atlas work
remains unlicensed under the repository's policy.

## Validation and completion

Validate and ship a first milestone for a representative ResStock multifamily
dwelling family and Medium Office before expanding. Each milestone declares
supported programs, parameter/weather/template domains, active channels and
remaining catalogue coverage. Completeness is required within the declared
milestone, not across all 1,900 definitions/378 compositions before any shipment.
Repeat the end-to-end evidence and release checks for each added family. The
test and evidence set must demonstrate:

- seeded operating-hour selection against exact source probability rows;
- ResStock activity/event and commercial transformation comparisons against
  pinned upstream reference fixtures, with disclosed numerical tolerances;
- exactly 8,760 finite values, correct units, fraction bounds, reference closure,
  thermostat ordering and preserved date/design-day semantics;
- same-request source/numerical reproduction, changed-seed behavior, source RNG
  order/coupling, unique constituent references and coordinated commercial groups;
- annual energy and water-volume conservation for both residential and commercial
  loads across different seeds and sampled hours, correct new
  magnitudes when schedule sums change and emitted-value rounding consistency;
- reference commercial design magnitudes retained in provenance, with final
  effective magnitudes rescaled to their unchanged reference annual budgets;
- arbitrary mixture member counts, per-hour trajectory conservation, fuel/host
  separation, shared-service deduplication and annual heat partitions;
- explicit behavior for zero/absent/unknown inputs, zero generated integrals,
  unsupported mappings and physical scaling conflicts;
- complete provenance, locked resources, upstream notices and unchanged frozen
  releases.

Keep the existing Ruby/OpenStudio runners as development reference tools only;
the shipped generator and its ordinary tests run in Python with local resources.
Reference execution is opt-in and its results carry runtime/source hashes.
A statistical check alone is insufficient to claim a faithful port; retain
traceable same-input component comparisons and disclose intentional adaptations.
Compare commercial source transformations before atlas normalization, then test
the final normalization separately for annual-total conservation. A normalized
atlas output is not an unmodified upstream commercial realization.

Run the repository's full schema, physical, referential, schedule, provenance,
release-integrity and numerical/source reproduction checks before declaring a
milestone delivered. Exact hashes verify the frozen artifact and locked inputs;
new generated numerical output is accepted by equivalence rather than byte hashes.
Count coverage by supported channel/binding and applicable parameter family;
catalogue class names alone do not establish generator completeness.

## Review and implementation sequence

Review this written contract, then write a concrete implementation plan around
the source inventory, Python ports, magnitude bindings, mixture adapter and
coverage/reproduction gates. Record the approved schema/source-method decisions
in an ADR. The initial implementations must be usable, shipped family milestones
rather than an all-or-nothing whole-library migration. Integrate only after
required checks and review conversations are resolved; deployment remains a
separate main-only step.
