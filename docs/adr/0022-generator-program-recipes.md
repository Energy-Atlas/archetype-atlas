# ADR 0022: Source-gated generator recipes and nominal companions

> Amended by ADR 0035 (2026-10-17): the semantic decisions stand; bit-level exactness, authority locks and certification ceremony are superseded.

Status: accepted for the exact M1 experiment, 2026-10-14.

Frozen definitions and Program JSON v3 remain immutable reference artifacts.
The generator compiler consumes `definition_release.read_bundle` and ready v3
exports, retaining source and reviewed identities separately. Only the ten
explicit cases in `schedule-generator-m1-scope.json` have physical resources.
All 1,900 definition IDs and 378 compositions have a compact support index;
uncompiled bindings fail with `unsupported_binding`. An indexed apartment unit
without source-backed appliance decomposition does not inherit fixture shares.
Apartment common spaces and hotel guestrooms are not reinterpreted as households.

Residential recovery contains individual physical demand records before v3
equipment aggregation. Recipes bind these individual records to ResStock time
allocation, preserving host, fuel, dwelling basis and demand identity. Original
`evidence.original_value.annual_kwh` or `daily_gallons` establishes the annual
target. Fitted recovered W or m3/s is retained as reference metadata and cannot
replace that independent target. kWh becomes Wh; US gal/day becomes annual m3
with 365 days and 0.003785411784 m3/US gal. Volumetric water bindings use `water`
as their carrier string; no water-heating fuel or energy demand is inferred.
The recovered artifact is checksum locked, with per-field original receipts and
upstream source hashes packaged alongside each exact configuration.

Callers supply the actual declared residents, bedrooms, presence flags, state,
coordinates, UTC offset, weather identity and thermostat arguments. Missing,
unknown or configuration-conflicting inputs fail. M1 residential annual weather
and reference cases remain on 2007; commercial rules support explicit non-leap
years with an empty holiday list. No source operand is supplied from an unrelated
fixture, no geometry is inferred and no population interpretation is made.

For commercial recipes, original frozen rules and original magnitudes establish
reference integrals before operating-hour sampling, occupancy/BPR adjustment,
native storage or rounding. The approved hybrid explicitly combines frozen
Atlas definitions with the v33 standalone sampler and Standards 0.8.6 transform.
The normalized nominal_people=1 Office carrier is an inference carrier only.
Plenum associates with it through the named MediumOffice configuration, never
through inferred geometry or its absent occupancy. Steps per hour, transform
modes, source clock, selected 0.231 peak adjustment and original rule objects
are explicit producer operands and receipts. V3 default and absence receipts
are retained, including accepted holiday completion, without replacing the raw
reference arrays supplied to the transform/budget boundary.

Companions implement selected source rules: fixed refrigerator/freezer/exterior
lighting defaults, source activity and water-target constants, and nominal
thermostat translation. Thermostats use base F plus bound offset directions,
F-to-C conversion and the upstream equal-season midpoint overlap correction.
The inspected source methods are checksum verified and packaged as evidence.
The source reference variant selects no ceiling-fan thermostat offset, on/off
deadband or equipment-unavailability overlay. Fixed backgrounds retain their
explicit no-temperature-feedback variant; a conditional rule without its
actual bound temperature input is rejected. Companions emit complete 8,760-hour
channels and receipts, with no energy normalization of temperature, activity
or occupancy/count semantics. Shared-service descriptors retain physical IDs;
there are no active shared services in these ten M1 cases.

Both Plenum ready v3 exports are explicitly inactive through accepted absence
and unconditioned-control receipts. `program-v1.slots` therefore permits an empty
array. The resolver permits empty slots only for an indexed `accepted_inactive`
recipe with its acceptance receipt; unresolved active records cannot use that
exception. No absent schedule is fabricated. Bundle constituent cardinality
already supports retaining such a constituent with empty slot/binding maps.
This preserves the M1 case denominator and allows a variable channel count of
zero for a known inactive program.

`resolve_program` returns the full Task 2 descriptor contract. Prepared internal
operands are under `inputs.reference_channels`, `reference_budgets`,
`source_context` and `companion_rules`; callers cannot inject these fields.
Task 8 owns coordinated operating groups, final budget binding and publication
of generated bundles. Compilation alone does not claim a shipped public runner.

Rebuild with `python -m scripts.schedule_generator_build --scope pilot
--destination <empty-directory> --tables-destination <directory>`. The four
inspection tables are generated canonical JSON; package manifest identity is
computed dynamically from every resource byte and inventory entry.
