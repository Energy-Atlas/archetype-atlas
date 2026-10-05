# ADR 0009: Complete deterministic water reporting

Status: accepted by user on 2026-10-05.

## Intent and scope

Supply operational hot-water schedule coverage for every active commercial
program, without replacing frozen source nulls or claiming measured program
beneficiaries. The user approved the source-preserving/reporting-layer proposal.
Original work remains unlicensed. EV, cavity spaces, HVAC unavailability, and
complete load magnitudes remain outside the schedule milestone.

## Decision

Create `data/water-reporting-releases/v0.1.0` alongside the unchanged base atlas,
commercial-completion v0.1.0 and resolution v0.4.0. Retain every fixture path,
source schedule and evidence identifier through checksum-bound dependencies.
Represent local draw, reporting beneficiaries, and physical zone gains separately.
No new physical program is invented for a shared service.

Use source-defined beneficiary assignments first. Allocate dedicated booster
draw to kitchen programs as an explicit domain-derived process assignment;
this does not place fixtures or gains in the kitchen. Assign laundry to an
existing unique Laundry program as a derived process attribution; retain
hospital laundry and inseparable institutional demand as shared services. Treat hospital
lumped main demand as institutional shared service because it combines uses
whose rates cannot be inferred from headcount alone.

For other lumped main draws, select occupied non-support programs and distribute
the unchanged source draw using fixed design-occupant shares. Derive reference
counts from source floor polygons times zone multipliers times source people
density. Deduplicate OSM space handles across HVAC mappings. These are benchmark
reporting weights, not new geometry-atlas area fractions or physical capacities.
If no valid beneficiaries can be established, retain the full shared service.
Do not infer density zero from null or use occupancy timing as water timing.

Support exclusions are explicit source-space-type choices: stairs, corridors,
mechanical/electrical rooms, elevator cores, storage, vestibules, entries and
restrooms. Restroom exclusion applies only to occupant-beneficiary reporting;
source-assigned restroom fixtures remain assigned and are counted once.
Report a local zero only where source branch evidence says no local fixture
draw was created; a shared relationship is retained separately. Source schedules
with existing assignments remain available regardless of these reporting rules.

Build program mixed-draw reporting shapes by summing component reference flows
then peak-normalizing the result. Component temperatures and service types
remain separate for any heating calculation. Retain original rule dates,
selectors and source order in dependency packets; derived combined rules are
explicit month/day inspection equivalents, not original source rules. Do not
copy booster draw into the main path: upstream heat-exchanger coupling is an
energy connection, not a second fixture.

## Coverage and validation

Assess the same 734 active commercial programs and seven fields (5,138).
Publish both source-only missing counts (279 water assignments) and reporting
variant availability. Shared-service references qualify as operational water
coverage, not evidence of a positive program-local draw or sourced allocation.
Existing 41 dwelling records and 14 profiles remain assessed separately.
Do not relabel 100% schedule availability as full simulation readiness.

Require schema, dependency hashes, complete active-program inventory, positive
finite geometry/weights, exactly-once service accounting, conservation on every
month/day/day selector/hour including holidays and design days, field evidence,
and reproducible frozen payloads. Allocation weights sum to one or the full
service remains shared. Preserve zero versus unknown in local-draw status.

## Catalogue naming follow-up

Align building and program display labels across titles, facets, mappings and
referenced schedule contexts. Retain canonical IDs/raw strings and old URL aliases.
Keep source variants (floors, numbered corridors, apartment types) distinguishable.
Naming alignment is a presentation change, not a scientific merge.
