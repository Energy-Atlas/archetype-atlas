# ADR 0018: Draw-only program water-heating energy

Date: 2026-10-12. Status: accepted modeling boundary; consumer schema and
implementation pending.

## Decision

The user wants to simplify simulation to a program-level water-heating energy
load. The user explicitly selected: "Include draw heating only; explicitly
exclude standby losses."

Develop a simplified program energy representation from the existing water
draw, schedule, fixture target temperature and weather-derived mains policy.
Retain source fuel and appropriate conversion performance, including their
template/fixture variants. Do not require a detailed heater or plant loop for
this representation. Standby losses are an explicit scope exclusion, not a
source observation of zero. No tank ambient-temperature assumption is needed
for the excluded standby calculation.

The user also explicitly selected exclusion of heater auxiliaries. Heater
pump/control electricity and pilot consumption are outside the simplified
energy representation; retain them in detailed source data. These exclusions
do not remove unrelated program appliance or pump loads.

The user instructed: "skip the solar case." Exclude the solar-equipped fixture
`source_building_402849` from this simplified DHW energy rollout:
source `residential_archetype-71cf018572bd7e3b4938`, program
`program-1a9bafb870d938bc1ff6a0ee`. Retain its existing program, volumetric water
demand and detailed solar/heater records. Report this case as out of scope for
the new representation, rather than exporting zero energy or substituting an
uncredited conventional heater.

The original volumetric demand and detailed equipment evidence remain available.
The simplified energy representation and explicit equipment heating must be
alternatives for the same demand; they must not both consume heating energy.
Shared demand remains owned and counted once. Water-heating fuel consumption
does not automatically become an indoor equipment heat gain.

This changes the proposed consumer delivery boundary, not the immutable source
data or the completed recovery work in [ADR 0017](0017-independent-energy-source-recovery.md).
Detailed DHW/solar definitions and recovered loss coefficients remain separate
source evidence and can support future detailed consumers.

## Remaining contract work

- Specify a versioned program representation and the selection of its alternative
  to explicit equipment heating. Program JSON 3.0.0 currently exports water draw;
  it does not yet implement this energy representation.
- Recover and identify conversion performance. EF/UEF ratings are not automatically
  interchangeable with burner conversion efficiency. Missing performance stays
  unknown; this decision introduces no fallback efficiency or fuel.
- Preserve main/booster thermal staging so already heated water is not heated
  from mains twice. Demand ownership and inlet-temperature semantics must remain
  explicit where source services are coupled.
- Specify heat-pump conversion if such heaters enter the supported inventory;
  do not replace a heat-pump model with burner efficiency. Heater auxiliaries
  and the one solar fixture now have explicit scope decisions above.
- Validate weather sensitivity, unit/basis scaling, fuel identity, shared-service
  deduplication and energy conservation for the included draw-heating scope.
  Enumerate the skipped solar fixture separately from unresolved performance.

This decision records the selected scope only. No schema, program artifact,
site or simulation implementation is changed by this ADR.
