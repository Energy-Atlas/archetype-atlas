# ADR 0004: Evidence-gated resolutions alongside frozen source inputs

Accepted 2026-10-03. User authority: selected domain assumptions and executed
residential generation are authorized; missing values must not be filled
automatically. Original source-input v0.2.0 remains immutable.

## Decision

Publish resolution supplement v0.1.0 with its own schema and a hash reference to
the v0.2.0 manifest. A consumer explicitly chooses the supplement. Each resolution
contains the original value, separate resolved value, basis, rule, SI unit and
source evidence with original units/value, revision/hash, locator, extraction date,
transformation and interpretation. Research assumptions remain labelled as such.
The resolver and policy reproduce the resolution rows exactly; profiles retain
their original input selections and executed CSV/JSON checksums.

| Rule | Evidence required | Resolution |
| --- | --- | --- |
| Explicit zero magnitude | Source magnitude exactly 0; corresponding schedule absent | Constant fraction 0 |
| Reviewed unconditioned | Exact allowlisted attic/plenum ID, both thermostats absent, every mapping has no HVAC and excludes total floor area | Heating/cooling disabled; no numeric sentinel |
| Reviewed no occupancy | Exact allowlisted cavity ID, source occupancy magnitude and schedule absent | Constant modeled occupancy fraction 0; transient maintenance excluded |
| Reviewed no hot water | Exact allowlisted attic/plenum/elevator core ID, source schedule absent, no positive reported flow | Constant local demand fraction 0 as an explicit research assumption |
| Demonstrated all electric | Every selected primary/secondary heating, cooking, dryer, water heater, miscellaneous gas, pool and spa option proves electricity/absence | Dwelling gas equipment 0 W |
| Selected absent end use | Exact source appliance `None` or explicit ceiling-fan no-use selection | Constant potential-use fraction 0 |
| Executed residential profile | Actual pinned upstream execution, source occupants/state/seed, calendar and explicitly labelled weather variant | Annual hourly series; nominal thermostat boundary retained |

The 24 reviewed cavity programs and 29 no-hot-water programs are enumerated in
the policy. This decision does not generalize to new IDs or similarly named
spaces. Electrical rooms may have substantial positive equipment loads; those
remain intact. Corridors/stairs are not automatically unoccupied, unlit or
unconditioned. No hot-water rule disables a central water-heating loop, standby
losses or a circulation pump. All-electric is tested for the whole selected
dwelling configuration, not inferred from electric HVAC alone. Unknown/other fuel
prevents that rule. Load 0 W is used instead of inventing a floor-area density
when residential area is unresolved.

## Profile boundary and remaining uncertainty

See `docs/residential-generation.md` for the actual execution and locked retrieval.
38 occupied configurations have stochastic profiles; three explicitly zero-occupant
configurations honor upstream skip behavior and resolve only occupancy to zero.
All 41 have upstream nominal thermostat profiles. Station weather substitutes
only in an explicit proxy variant because the original county archive returns
HTTP 403. HVAC unavailable-day placement, EV and non-exported end uses remain
unknown; original v0.2.0 `simulation_ready=false` remains valid.

## Consequences

This additive schema is deliberately separate from source-input tables. Applying
an assumption requires an explicit consumer choice; source nulls stay recoverable.
Unjustified program fields are enumerated with reasons. Promotion to a future
atlas schema would require a migration and renewed model-level validation.
Numeric thermostat sentinels are an adapter decision, never source measurements.
Profiles are deterministic seeded realizations, not observed people or population
weights. Generation is opt-in local upstream-code execution; catalogue publication
uses the validated frozen artifacts without executing the runtime.
