# Approved finite schedule completion

The user's six annotation decisions approve commercial water-path extraction,
HVAC/controller inspection, refrigeration defaults/absence review, vacancy
handling and exterior lighting. EV is excluded from active outputs. Execution
is autonomous on `feat/schedule-resolution`; no routine approval gate is added.
The repository research brief governs provenance, security and release validation.

## Deliverables and scientific boundaries

Publish an additive resolution supplement after reviewing all 485 missing
commercial water assignments, 19 programs with missing heating/cooling controls,
76 refrigeration fields, 25 other zero-occupant fields and 41 exterior-lighting
applications. A reviewed unknown remains unknown; completion means executing and
documenting each applicable source path, not inventing a positive profile.

Refrigerator/freezer absence must follow selected installation and source object
creation guards. Missing stochastic export columns alone establish neither
absence nor inclusion in another load. For selected appliances, extend the
accepted fixed source-default variant with no temperature feedback. Preserve
upstream fractional weekday/weekend shapes and monthly multipliers. For explicitly
absent appliances, publish zero after checking the exact option binding.

The three vacant zero-occupant configurations retain their selected options and
zero occupancy. Evaluate upstream lighting, miscellaneous loads and hot-water/
appliance calculations with the exact occupant inputs and applicable ERI/default
context. Source-calculated zero demand can justify a zero fractional application;
do not invent occupants to defeat the stochastic skip. Use positive fallback
shapes only when a source-supported application remains. Exterior lighting uses
source presence/usage handling and its own default shape; distinguish dwelling
lighting from common-area building lighting.

For SmallHotel elevator/electrical-core and HighriseApartment corridor programs,
inspect source zones and actual pinned controller/HVAC creation phases, including
late customizations. An empty controller is different from an absent controller.
Classify explicitly inactive modeled heating/cooling only when no operative
controller/equipment path exists. Do not infer thermal isolation: adjacent-space
heat transfer remains possible. Retain any real recovered thermostat rules and
SI temperatures. No 0 C setpoint or invented occupied-office thermostat is used.

For commercial water, inspect main, per-space, lumped, booster, laundry and custom
paths for every affected building/template. Publish component schedules, SI flow
bases, exact source inputs and supported recipients. Preserve every source rule,
selector/date/design day/order. Existing-program assignments must conserve each
source draw and apply it once. Source-no-SWH and complete recipe no-local-demand
paths can support bounded zeros only after checking for other positive demand.
Lumped demand without a beneficiary mapping remains a separate building service
record; heater location is not fixture location. No implicit occupant-based
allocation, invented restroom program or duplicated central demand is introduced.

EV has no new schedule, execution binding, resolution, plot or completeness
denominator. Exclude its raw parameters from active catalogue presentation and
filter its archived runtime-gap notes out of active scope. Immutable historical
source/download snapshots remain unchanged as provenance, rather than rewritten.
HVAC equipment unavailability and complete magnitudes/full-model controls remain
outside this milestone. Parametric generator shipping remains deferred.

## Architecture and release handling

Keep atlas v0.2.0 and every existing supplement/water snapshot immutable. Extend
finite fixed-table parsing and resolution rules with version-gated policy flags so
historical bundles still reproduce byte for byte. Add locked source-completion
evidence and a strict machine-readable commercial path/control inventory. Source
files are independently SHA-256/Git-blob verified; runtime receipts identify which
source phases were executed and never claim sizing/EnergyPlus simulation.

Integrate reviewed program resolutions into supplement v0.4.0 and retain building
services separately in an independently verified additive bundle. The canonical
resolution schema enumerates new rule/reference forms. Derive the updated gap
inventory from the actual selected release. The MkDocs catalogue shows original
values beside applied decisions, usable curves and exact evidence. Historical
profile payloads can be shared rather than copied into public presentation.

## Acceptance

- Every approved group has a reproducible inspection result and per-record status.
- Selected positive refrigeration is preserved; explicit absence and source-zero
  vacancy rules cannot override contradictory positive exported profiles.
- Inactive heating/cooling requires inspected source controls and HVAC evidence.
- Water components conserve demand, deduplicate source identities and retain
  unallocated positive demand without falsely marking beneficiaries complete.
- EV is excluded from active assessment/presentation and all new profile outputs.
- Schema, physical, referential, schedule, provenance, independent reproduction,
  historical release integrity, staged security and rendered-site checks pass.
- Publish logical reversible commits with neutral identity and truthful model
  trailers; publish only verified artifacts on the existing publisher branch.
