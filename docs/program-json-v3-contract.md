# Program JSON for simulation import

Contract **3.0.0**, JSON Schema Draft 2020-12. The catalogue exports this form.

- [Program schema](../schemas/program-json-v3.schema.json), including embedded schedule definitions.
- [Standalone schedule schema](../schemas/schedule-json-v2.schema.json), unchanged from version 2.
- [Ready Medium Office](examples/program-json-v3/medium-office.defaulted.json) and [raw Medium Office](examples/program-json-v3/medium-office.raw.json).
- [Default policy](../sources/program-json-defaults-v2.json), `atlas-program-defaults-2.0.0`.

`export_mode: "raw"` retains source unknowns in the connector representation.
`export_mode: "defaulted"` is the ready form: source recovery and approved
resolutions are already applied, active loads have complete operands, and all
referenced schedules are embedded. This certifies the included operand inventory;
`metadata.excluded_scope` and `metadata.accepted_decisions` identify
the agreed scope and calendar choices described in the
[decision record](reviews/program-json-remaining-decisions.md).
The consumer supplies geometry, weather,
calendar and HVAC assignment; it does not select missing program defaults.
If an active operand remains unresolved, ready export fails. Raw data and
historical version 2 artifacts remain separate and unchanged.

## Physical inputs and metadata

| Field | Meaning |
| --- | --- |
| `loads` | Active local demands with SI magnitude, scaling basis, schedule and physical host. |
| `controls` | Explicit `conditioning_state` and service flags; only active heating/cooling has a setpoint schedule. People activity and heat settings appear when occupancy is active. |
| `schedules` | Complete objects keyed by schedule ID. No external manifest lookup is required. |
| `shared_services` | Physical shared demands instantiated once per identity, with model host binding. |
| `required_bindings` | Applicable area, dwelling/person count, weather, host and calendar inputs supplied by the model. |
| `source` | Simulation-ignored provenance, including source family and climate/vintage applicability descriptors. |
| `metadata` | Simulation-ignored source operands, recoveries, approved resolutions, absent demands, component records and mixture/aggregation evidence. |
| `default_policy_id` | Versioned resolution policy used for the ready form. |

The former top-level `assumptions` array is replaced by `metadata.resolutions`.
Provenance can contain original
nulls; it is not an executable input. Applicability descriptors distinguish
`exact`, documented `shared`, and `unknown` context. Stock vintage and
code/prototype template remain distinct from each other and from the actual
simulation weather file.

Conditioning states are `unconditioned`, `heating_only`, `cooling_only`, and
`heating_and_cooling`; raw output may be `unknown`. Disabled services have no
artificial extreme-temperature setpoint. A known heating service remains active
when cooling is disabled. Zero/absent demands are omitted from executable
`loads` and retained in `metadata.absent_demands`.

## Load and heat interpretation

`actual(t) = value × scale(basis) × schedules[schedule_id](t)`.

| Basis | Scale | Example units |
| --- | --- | --- |
| `floor_area` | Assigned area in m² | W/m², person/m², m³/s/m² |
| `dwelling_unit` | Assigned dwelling count | W/dwelling, person/dwelling, m³/s/dwelling |
| `person` | Design person count | W/person, m³/s/person |
| `absolute` | 1 | W, person, m³/s |

Do not apply area scaling again to absolute/dwelling demands or apply the
occupancy schedule again to person-based scaling. `demand_id` identifies the
physical demand. Deduplicate repeated shared services across assigned programs;
reporting allocations do not create additional physical loads.

Native heat inputs depend on the object:

- Lighting: `radiant`, `visible`, `return_air`.
- Electrical and fuel equipment: `radiant`, `latent`, `lost`.
- People: activity in W/person, radiant fraction of sensible heat, and a
  numerical sensible fraction or explicit `"autocalculate"` engine mode.

Mixed programs retain each occupancy load's `activity_schedule_id` from its
resolved member. This overrides the common control activity schedule, if one
exists. Unoccupied members cannot cause an occupied member's known activity to
be replaced by the fallback. Different member activities remain separate.

`exterior_lighting` represents outside lights without indoor heat fractions.
Loads in an identified nonconditioned space retain that physical host; do not
move them into the assigned indoor zone merely to combine equipment.

For power objects, the convective share is the residual. Preserve fuel identity
and host. A `gas_equipment` grouping does not authorize converting propane to
natural gas; consumers must use the reported `fuel` with a suitable native
object, including `OtherEquipment` where necessary.

Equipment groups combine only compatible hosts, fuels, units and scaling bases.
Their magnitude and normalized schedule preserve the summed power trajectory.
Constant heat fractions use annual component energy on the calendar recorded in
`metadata.aggregation`. This preserves the annual heat partition on that
calendar; constant fractions can approximate the hourly partition. Component
records and `component_schedules` remain in metadata for inspection and
reaggregation when needed, including the leaf groups used by mixtures.
The user-approved reference calendar for ruleset-only annual heat weighting is
2007 with no designated holidays. Annual source realizations retain their
recorded year. Residential general-water-use signed gains and distribution-water
effects are outside program scope by explicit user decision; omission does not
assert zero energy or moisture effects.

Hot water supplies flow and a target-temperature schedule. The inlet instruction
is `{"method":"CorrelationFromWeatherFile","engine":"EnergyPlus","engine_version":"25.1.0"}`,
using the simulation weather file and EnergyPlus's Christensen/Burch mains
correlation. It replaces the old fixed 10 °C fallback. Source targets take
precedence over the approved 60 °C unresolved-target fallback. Water-heater and
HVAC sizing remain model responsibilities. Physical hosts remain relevant when
the fixture implementation applies zone gains.

## Schedules and completion

Schedules retain the version 2 representation: hourly interval values, SI units,
ordered inclusive `MM-DD` rules, wrapped seasons and explicit holiday/design-day
selectors. The last matching specific rule wins, otherwise the last applicable
Default rule. Missing coverage is not implicitly zero. Annual schedules retain
their recorded calendar and local standard time; do not transplant them to
another year or apply DST/holiday overrides.

The approved completions copy each affected Medium Office schedule's Sunday
profile to its missing holiday selector and extend the data-center February
profiles through February 29, including existing design-day profiles. Covered
source values and rule order are retained. Unrelated active schedule gaps fail
ready export rather than receiving a general constant fallback.

Recover source operands before applying the scoped absence/engine policies.
Additional-lighting absence and reviewed support-space absence do not establish
a universal zero for unknown occupied-space loads. The Hospital post-1980
ER_Triage magnitude is recovered separately from the original DOE scorecard.
Resolve source leaves before recomputing mixtures.

## Migration and validation

Version 2 consumers must update object-specific heat fields, disabled-control
omission, zero-load omission, fuel/host preservation, weather-derived inlet
instructions and metadata handling. Do not use the old general unknown-load
zero, 20/26 °C thermostat, or fixed-mains-temperature defaults with version 3.
Ventilation and infiltration are excluded from this migration; their omission
does not mean zero building air requirements.

In addition to schema validation, verify reference closure, schedule units and
calendar/design-day coverage, positive active magnitudes, fraction bounds,
active heating/cooling consistency, fuel identity, unique physical demands and
the required model bindings. Aggregation checks must compare component and
combined hourly energy and annual heat partitions. A valid program export does
not constitute a complete building simulation.
