# Plain program JSON for connector import

Contract version: **2.0.0**, JSON Schema Draft 2020-12.
Implemented locally on `feature/dto-json-v2`; the catalogue emits this contract.

## Files to use now

- [Program schema](../schemas/program-json-v2.schema.json): self-contained,
  including the full schedule schema under `$defs.schedule`. No remote schema
  retrieval or archive query is required to validate a program.
- [Standalone schedule schema](../schemas/schedule-json-v2.schema.json): the same
  schedule definition for validating an individual schedule.
- [Default-filled Medium Office](examples/program-json-v2/medium-office.defaulted.json):
  an actual 90.1-2019 reviewed program with every referenced schedule embedded.
- [Raw Medium Office](examples/program-json-v2/medium-office.raw.json): the same
  connector representation with source unknowns retained.
- [Annual residential schedule](examples/program-json-v2/residential-annual.schedule.json):
  an actual 2007 realization with 8,760 hourly values and its original seed/weather
  context, validating against the standalone schedule schema.
- [Default policy](../sources/program-json-defaults.json): explicit experimental
  assumptions, not source-reported measurements or regulatory defaults.

`raw` and `defaulted` are the same DTO contract. Raw means source values and
unknowns preserved in this connector representation; it is not a byte-for-byte
copy of the older archive's record format. The canonical research archive stays
unchanged. `defaulted` is the form the BEMGen connector should accept for ordinary
program creation. A JSON Schema validator validates values; it does not fill
them. The atlas exporter applies the policy before producing this form.

## Program structure

| Field | Interpretation |
| --- | --- |
| `schema_version`, `kind` | Exact contract `2.0.0` and object kind `program`. |
| `export_mode` | `raw` or `defaulted`. Defaulted requires all physical load/control inputs to be non-null. |
| `id`, `name`, `scope` | Export identity, display name, and `program` or `whole_dwelling` scope. Defaulted identity differs from the original definition. |
| `source` | Original program ID, release and context, plus original evidence. Do not apply simulation defaults to evidence or metadata. |
| `loads` | Additive local demands, each with its own unit, basis and fractional schedule. |
| `controls` | Heating/cooling enabled states, temperature and activity schedule IDs, and people heat-partition settings. |
| `schedules` | Dictionary containing complete schedule objects, keyed by their IDs. All references must resolve here. |
| `shared_services` | Building-serving demands, instantiated once per service identity and assigned to a consumer-selected host zone. |
| `default_policy_id`, `assumptions` | Versioned default policy and exact JSON Pointer substitutions. Raw output has no applied assumptions. |
| `required_bindings` | Geometry, multiplicity, host or calendar bindings the consuming model provides. No geometry or HVAC sizing is fabricated. |

Optional/inapplicable properties are omitted. For example, occupancy does not
have power-equipment heat fractions; opaque materials are not involved in this
program contract. Source metadata and original evidence may legitimately contain
null even in a defaulted export. These are not missing simulation operands.

## Load interpretation

For each load at time `t`:

`actual(t) = value * scale(basis) * schedules[schedule_id](t)`

| Basis | Scale | Permitted units |
| --- | --- | --- |
| `floor_area` | Assigned floor area in m2 | `person/m2`, `W/m2`, `m3/s/m2` |
| `dwelling_unit` | Assigned dwelling count | `person/dwelling`, `W/dwelling`, `m3/s/dwelling` |
| `person` | Assigned design person count | `W/person`, `m3/s/person` |
| `absolute` | 1 | `person`, `W`, `m3/s` |

There is no extra scaling by area for an absolute or dwelling-based load.
Person-based scaling uses the declared design count, not an instantaneous count
that would apply occupancy variation twice. Convert upstream hourly volume
units to the stated SI volume-flow units before import; heater power and fixture
volume flow are different physical quantities.

`type` is the importer grouping: `occupancy`, `lighting`, `electric_equipment`,
`gas_equipment`, or `hot_water`. `end_use` preserves the finer channel, such as
`additional_lighting`, `clothes_dryer`, or `hot_water_fixtures`.

Distinct physical demands add. `demand_id` identifies a physical demand, so
alternative unit representations or repeated references must not create another
copy. A local water load already present in `loads` is not repeated in
`shared_services`. Consumers must deduplicate shared-service IDs across programs.
Do not add reporting allocations on top of the original physical service.

Power-load `heat_fractions` are radiant, latent, lost, visible and return-air
shares. The remaining fraction is convective; do not also add an independent
convective term. The sum must be at most one. People instead use activity in
W/person and `people_radiant_fraction` of sensible heat;
`people_sensible_fraction: "autocalculate"` delegates the sensible/latent split
to the simulation engine's temperature/activity calculation. This is an explicit
mode, not a numeric zero.

Water loads supply volume flow, target-temperature schedule and inlet-temperature
schedule. They are fixture demand, not a water-heater or HVAC sizing definition.
This initial program import does not add water draw as zone heat; plant/heater
representation and any explicit moisture/zone-gain model remain separate.

## Schedule interpretation

All schedules currently use 60-minute timesteps. Values describe interval
`[h, h+1)`; use stepwise values without interpolation. `unit` is exactly `1`
(fraction), `degC` (temperature), or `W/person` (activity).

### Rule-based schedules

`type: "ruleset"` contains an ordered `rules` array. Each rule contains inclusive
recurring `MM-DD` boundaries, `day_types`, and either one constant value or 24
hourly values. If the start date is later than the end date, the interval crosses
New Year. Never sort these rules during import.

Selectors are `Default`, `Wkdy`, `Wknd`, individual `Mon` through `Sun`, `Hol`,
`WntrDsn`, and `SmrDsn`. Wkdy matches Mon–Fri; Wknd matches Sat/Sun. For a given
date and effective day type, scan in array order, retaining the last matching
specific rule and the last applicable Default rule. Use the last specific match,
or the last Default if there was no specific match. An explicit weekday does
not receive additional priority over a later matching Wkdy rule. No applicable
rule is an error/gap, not an implicit zero.

The consumer supplies the calendar year and an explicit holiday list (which may
be empty). A holiday uses the Hol selector rather than also applying its ordinary
weekday selector. Winter and summer design days are separate inspection/sizing
contexts; they are not ordinary days in the annual operating calendar. The DTO
normalizes the legacy DummySmrDsn alias to SmrDsn while preserving rule order.

### Annual schedules

`type: "annual"` contains `year`, `clock: "local_standard_time"`, and chronological
hourly `values` from Jan 1 00:00. A non-leap year has 8,760 values and a leap year
8,784. The consumer's calendar must match the recorded year. Do not resample,
repeat a selected day, add DST/holiday overrides, or transplant a 2007 realization
to a different year.

## Experimental defaults

The user authorized the atlas to choose defaults; the popup has only raw and
default-filled choices. Policy `atlas-program-defaults-1.0.0` specifies:

- Unknown additive magnitudes: zero in the existing unit.
- Missing fractional schedule: constant zero for a zero magnitude; constant one
  for a known positive magnitude. Preserve every known schedule.
- Missing coverage within a known ruleset: prepend a lowest-priority Default
  rule, using zero for fractions, 120 W/person for activity, or the compatible
  control-temperature fallback. Every source rule keeps its original order and
  precedence over this fallback. Give the completed schedule a new identity and
  record the changed reference. This fills gaps without changing known profiles.
- Unknown nonconvective power-load heat fractions: zero; retain all known shares
  and use the convective residual.
- Missing heating/cooling schedules: constant 20/26 degC. When only one is
  missing, adjust that fallback conservatively to leave at least a 2 degC
  deadband against the known schedule's extrema. Never change known setpoints.
- Unknown conditioning flags: enabled. Retain explicit disabled states.
- Missing people activity: constant 120 W/person; missing radiant fraction: 0.3
  of sensible heat; missing sensible fraction: `autocalculate`.
- Missing hot-water target/inlet temperature: constant 60/10 degC, adjusted when
  necessary to avoid a target below a known inlet or an inlet above a known
  target. Preserve known temperatures.

For mixtures, apply the policy to unresolved source leaves before recomputing
the approved mixture. Never replace an unknown aggregate with zero if that
would erase known positive contributions. Known schedules, controls, source
membership and weights remain authoritative.

These fallbacks produce importable definitions under an explicit experimental
policy; they do not establish realistic missing residential magnitudes. Record
each substitution, including generated schedule references. A defaulted object's
ID includes its policy identity, so it is not mistaken for the original physical
definition. Canonical unknowns remain unchanged.

## Checks in addition to JSON Schema

JSON Schema checks structure, allowed unit/basis combinations, null restrictions,
fraction bounds, and vector lengths. The importer must also check:

1. Each schedule dictionary key equals its object's ID; every reference resolves.
2. Load schedules use unit `1`; temperature references use `degC`; activity uses
   `W/person`. Reject unexpected units rather than coercing them.
3. Validate real MM-DD dates using a leap-capable reference year. Preserve rule
   order and check calendar coverage for the selected model year and design days.
4. Annual vector length matches its stated year's leap status. All annual
   schedules in one imported program must have a compatible recorded year.
5. Heat fractions sum to at most one. Heating does not exceed cooling in the
   relevant active periods. Water target is not below inlet.
6. No demand/service is instantiated twice; geometry/count bindings are present
   when applying the definition to model objects.

The prepared raw and defaulted Medium Office examples pass their schema,
reference closure, schedule-unit and heat-fraction checks. The defaulted sample
contains six loads, ten embedded schedules and twenty-two recorded substitutions.
The atlas exporter and website implement this contract. The BEMGen connector is
maintained separately and is outside this branch's implementation scope.
