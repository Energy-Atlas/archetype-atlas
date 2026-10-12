# ADR 0016: source recovery and automatic program completion

Date: 2026-10-11.
Status: policy accepted through the user's field-review comments; implementation pending. Both schedule-completion assumptions were also accepted by the user on 2026-10-11.

## Context

The field audit combines source omissions, adapter omissions, absent demands,
unsupported object fields and missing source metadata. The user reviewed the
[grouped responses](../reviews/program-json-annotation-responses.md) and asked
for a complete simulation-ready program DTO with automatic defaults, compact
equipment schedules and provenance that the simulation consumer may ignore.
Their comments are preserved there. This decision refines ADRs 0012 and 0015;
it does not rewrite frozen source records or claim that the current exporter
already implements the policy.

## Decision

Recover pinned source values, translator rules and existing frozen resolutions
before applying experimental assumptions. Preserve reported values. Resolve
leaves before recomputing mixtures, retain distinct source/reviewed variants,
and record each assumption without presenting it as a source observation.

- Recover residential activity at 117.228428 W/person and the source People
  heat fractions. If active occupancy still lacks activity, apply the existing
  atlas 120 W/person assumption. Missing People heat fractions use the documented
  engine policy: radiant 0.3 and sensible autocalculation.
- Use object-specific heat parameters. Preserve source overrides and use
  documented engine fallbacks for supported unresolved parameters. Unsupported
  inputs need no artificial value. In particular, equipment visible/return-air
  and Lights latent/lost are not native inputs to the corresponding objects.
- Resolve missing additional lighting to zero. Resolve missing support-space
  lighting/equipment and occupancy to absence in the reviewed cases identified
  in the response document. Never erase positive source loads. The Hospital
  ER_Triage equipment magnitude is outside this support-space assumption.
- Recover fuel appliance components before resolving remaining gas-equipment
  absence to no gas equipment. Preserve electrical auxiliaries and fuel identity.
- Represent active heating/cooling explicitly, including neither service,
  without artificial extreme setpoints. Known heating does not disappear merely
  because cooling is inactive. Resolve the identified missing-control support
  recipes using their reviewed evidence and the user's unconditioned assumption.
- Use EnergyPlus's Christensen/Burch `CorrelationFromWeatherFile` mains policy
  with the simulation weather file instead of a fixed 10 degrees C fallback.
  Preserve relevant downstream source treatment. Recover demand target
  temperatures and service inheritance first; then use 60 degrees C if a target
  remains unresolved. Retain the recovered 105 degrees F mixed fixture target.
- Aggregate equipment by summing power trajectories after basis/host scaling;
  export a matching design power and normalized schedule. Weight constant heat
  fractions by annual component energy on a common calendar, not merely by peak
  power or area. This preserves annual heat partition, while a constant fraction
  can approximate its hourly distribution. Retain the component record.
- Form compact electrical and fuel equipment groups while retaining distinct
  fuel components and physical hosts where one simulation object cannot preserve
  them. Do not silently turn propane into natural gas or combine exterior loads
  into an indoor host.
- Exclude air requirements from this migration. Omit water reporting allocation
  when it does not affect energy; retain each physical shared-service demand
  once and retain physical host information when zone gains depend on it.
- Include available climate/vintage applicability as metadata, distinguishing
  documented shared applicability from unknown context. Preserve the stock versus
  code/prototype distinction and separate applicability from realization weather.
- Make provenance simulation-ignored metadata. Retain research traceability and
  original nulls there. Strict JSON uses metadata fields rather than comments.

The ready DTO must contain all active program operands and embedded schedules,
or explicit executable engine instructions such as sensible autocalculation
and weather-derived mains temperature. The consumer must not choose missing
program defaults or fetch another atlas manifest to resolve physical operands.
Geometry, weather/calendar and HVAC assignment remain normal model context.
Version the migrated schema and default policy; represent modes explicitly
rather than disguising them as unresolved nulls.

## Open items and validation

Five source rulesets have specific gaps. Four Medium Office schedules lack
holiday selectors; the accepted completion copies each schedule's Sunday
profile. One data-center schedule lacks February 29; the accepted completion
extends the February values to that day, including the existing design-day
values. The user accepted both assumptions on 2026-10-11. Exact IDs, profiles
and affected definitions are in the response document. Preserve covered values
and source rule order. The investigation verifies the repairs in memory;
application to releases and export defaults remains pending.

Residential magnitude/fuel recovery and the Hospital ER_Triage exception still
need work; acceptance of defaults is not evidence of complete extraction.
Do not freeze a new complete release with unresolved active operands. Bring
any remaining material assumption outside this policy back with specific
affected programs and a concrete proposed value or method.

Validate the Medium Office pilot, residential cases and mixtures. Verify
hourly and annual energy conservation, heat-fraction bounds and annual
partition, fuel identity, schedule/reference closure, calendar and design-day
coverage, service deduplication and unchanged known source values. Run the
repository's schema, physical, referential, schedule, provenance and
reproducibility checks before release. No full simulation has been run for
this documentation decision.
