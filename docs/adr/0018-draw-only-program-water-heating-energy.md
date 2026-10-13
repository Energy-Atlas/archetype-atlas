# ADR 0018: Draw-only program water-heating energy

Date: 2026-10-12. Status: accepted modeling boundary; opt-in Program JSON 4
implemented, including the user-approved SmallHotel delivery cap below.

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

## Source-bounded delivery decision (2026-10-12)

The user approved: "Cap delivery at 60°C and report unmet target." Apply an
explicit `cap_at_source_outlet` policy only to the 90.1-2007/2013/2019 SmallHotel
main-loop laundry demands and mixtures containing those demands. Preserve the
requested 82.222°C target schedule, source main-loop assignment, source fuel and
conversion efficiency. The main heater's source outlet is 60°C; no additional
booster or independent laundry demand is introduced.

Report requested temperature, modeled delivered temperature, unmet temperature
in K and unmet thermal demand in W. Charge fuel only for delivered draw heat.
This is an ideal source-outlet bound, not a dynamic tank or capacity simulation.
The pinned EnergyPlus WaterUse implementation and checksum support the policy;
each affected recipe embeds that evidence and the user's decision date. Other
unapproved target/supply conflicts still fail validation.

The additive policy completes the unreleased opt-in 4.0.0 draft; it does not
revise a published/frozen schema or change existing v3 definitions. Future
released contract changes require their own version decision.

## Implementation and remaining work

- [Program JSON 4.0.0](../program-json-v4-contract.md) supplies the opt-in ready
  recipe. Program v3 and frozen/public artifacts remain unchanged. The simulation
  supplies fluid properties explicitly, alongside weather/calendar and scaling;
  this does not introduce an Atlas density or specific-heat assumption.
- All 154 commercial channels execute the pinned source factory/efficiency rule;
  the 41 residential heater conversions come from the preceding pinned recovery.
  EF/UEF are not exported as burner efficiency. Missing performance still fails
  export; no fallback efficiency or fuel is introduced.
- Main/booster temperature lifts, separate fuels, shared ownership and alternative
  detailed-equipment accounting are implemented and checked with focused tests.
- Three SmallHotel main-loop laundry target/supply conflicts use the approved
  delivery policy above. All three leaf programs and 12 dependent mixtures pass
  complete export validation, with original draw magnitudes and schedules intact.
- Specify heat-pump conversion if such heaters enter the supported inventory;
  do not replace a heat-pump model with burner efficiency. Heater auxiliaries
  and the one solar fixture now have explicit scope decisions above.
- Focused tests check weather sensitivity, scaling, fuel identity, shared-service
  deduplication, staging and heat conservation. The coverage census enumerates
  the skipped solar case separately from the approved capped temperature cases and
  services requiring consumer attachment. The full v4 catalogue is not generated
  or published by this implementation.

The opt-in schema/exporter and six pilots implement this decision. Site builds,
simulations and regeneration of the unchanged full program library are excluded
from this focused pass.
