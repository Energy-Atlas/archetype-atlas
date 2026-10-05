# Selective schedule resolution and executed residential profiles

The user's 2026-10-03 instruction authorizes selected, documented domain
assumptions and makes executing residential schedule generation the highest
priority. Work is on feat/schedule-resolution, based on the published catalogue.
Original work remains unlicensed. The autonomous instruction supersedes skill
approval handoffs; decisions and evidence are reviewable in this repository.

## Outcome and representation

Keep frozen source-input releases and their nulls unchanged. Produce a versioned,
machine-readable resolution supplement referencing v0.2.0 by manifest hash and
record IDs. Distinguish source facts, generator-derived profiles and explicit
research assumptions. The supplement has its own schema and provenance, and can
be applied deliberately by a downstream consumer. Original values remain visible.
Do not advertise complete simulation readiness merely because schedules exist.

## Rules authorized by the user

1. Inactive space conditioning requires evidence of no heating/cooling service
   or an explicit experiment classification. Represent disabled heating/cooling
   directly; do not use 0 degrees C or arbitrary extreme temperatures as facts.
   An adapter may create numerical sentinels only with a separately declared
   policy. Stair/corridor names alone do not prove unconditioned status.
2. Gas equipment is zero for a demonstrated all-electric configuration. Inspect
   all selected fuel-using end uses, including cooking, dryer, water heating,
   secondary heating and miscellaneous gas loads. Electric HVAC alone is
   insufficient. Unknown/contradictory fuel evidence prevents resolution.
3. Occupancy/lighting/equipment may be always zero when explicitly zero source
   magnitude or record-specific absent-load evidence justifies it. A support-space
   name is a candidate for review, not an automatic zero-load rule. Positive
   source loads and valid schedules are preserved.
4. Hot-water demand may be always zero when installed-use evidence or a specific
   source rule establishes no demand. Absence of a schedule alone is insufficient.
5. Generate residential profiles by executing pinned upstream code, not by
   inventing curves or borrowing commercial apartment schedules. Record toolchain,
   seed, year, timestep, weather/location inputs, argument translation, defaults
   and output hashes. Reconcile source options only with exact documented meaning.

## Residential generation boundary

The pinned ResStock revision dd25369f41a83a0767aefeeac0b6f8a0b0edd649 bundles
OpenStudio-HPXML 1.11.0 and requires OpenStudio 3.10.0. Prefer a local portable
runtime under ignored build/. Run the upstream schedule measure for source
configurations, retaining its stochastic method but fixing seeds deterministically
per fixture ID. Generated realization is not observed household behavior.
Schedule-only execution need not run annual EnergyPlus or determine geometry.

Inspect the generator's actual dependencies before choosing its inputs. Distinct
reference-context variants are permitted if a source configuration lacks an input
required for schedule generation, but must be labelled and must not claim exact
ResStock-model equivalence. Any unresolved inputs remain separately enumerated.
Known absent appliances must not become installed loads merely because a generic
generator emits potential-use columns. Thermostat controls must incorporate the
source base, offsets and unavailable periods or remain explicitly unresolved.

## Validation and delivery

Test fail-closed predicates, preservation of positive/source values, referential
integrity, units, dimensions, finite values, fractions, annual length, seeds,
calendar, provenance and deterministic reruns. Start with one residential pilot,
then all 41 recipes. Each failed run is recorded; no fabricated success.
Keep downloaded code immutable and checksum-locked. Execute only the explicitly
selected official generator in a local controlled workflow, with no credentials.
Large upstream/runtime files remain ignored and reproducibly retrievable.
Expose resolved status and generator/assumption evidence in the catalogue without
changing older release URLs. Publish only after the supplement and site pass checks.

## Alternatives considered

Blanket null-to-zero filling is rejected because it erases unknowns. Mutating
v0.2.0 is rejected because its manifest and scientific interpretation are frozen.
An additive supplement is selected: it permits deliberate use of assumptions,
independent validation and later promotion into a normalized data release.
