# Schema 0.1.0

`schemas/atlas.schema.json` is JSON Schema 2020-12. `metadata.json` plus named
JSON arrays are canonical. `load_atlas(directory)` assembles them in memory;
the build also emits combined JSON and CSV inspection views. CSV nulls are the
literal `null`; nested cells are JSON. CSV is not the typed interchange contract.

## Tables and relationships

| Table | Primary key | Relationships |
| --- | --- | --- |
| programs | id | Typed schedule IDs; provenance_id |
| schedules | id | provenance_id; ordered source rules |
| envelope_components | id | template, climate_zone_set, source category/predicates; provenance_id |
| systems | id | Typed availability/OA schedules; provenance_id |
| mappings | id | program_id, nullable system_id; provenance_id |
| efficiency_rules | id | Conditional equipment table and template; provenance_id |
| residential_options | id | ResStock parameter/option/measure args; provenance_id |
| commercial_options | id | ComStock parameter/option/measure args; provenance_id |
| provenance | id | table + record_id, source_file_id, field map |
| source_files | id | Repository/path/revision/URL/hash/date/license lock |

IDs use namespace-prefixed truncated SHA-256 over semantic identity. They are
stable for identical identity inputs, not a promise that a new source revision
will leave every record unchanged. Schedule IDs include source name and physical
role; a shared named source schedule can serve several templates. Other source
indices remain part of identity where upstream does not supply a durable ID.
Primary-key collisions and exact program lookup ambiguity fail validation.

## Units and nulls

Canonical density fields are SI: people/m², W/m², m³/s/m², m³/s/person and 1/h.
Temperature schedules are °C; activity schedules are W/person; fractional
schedules and SHGC/VT are dimensionless. The exact root `units` map is validated.
Lighting/additional lighting are separate inputs; do not silently add controls
or replace absent additional loads with an assumed component.

`source_attributes`, equipment `metrics` and stock-option `arguments` are original
source evidence with upstream units, not additional canonical SI parameters.
LPD/electric loads use W/ft²; gas loads use Btu/h·ft²; occupancy uses people per
1,000 ft²; outdoor-air fields use cfm/ft² or cfm/person. Envelope U-values use
Btu/h·ft²·°F (including explicitly documented legacy conventions). Fuel efficiencies
are ratios; EER/IEER/SEER/HSPF ratings retain their own definitions and test
conditions. No seasonal rating is converted into a steady-state COP.

Null indicates missing, unreported, unresolved or invalid source input as explained
in provenance. It never means zero or a default. Every canonical field has an
original field/unit/value, transformation and status in its provenance entry.
The full original row preserves source constraints and secondary parameters.

## Source granularity and dependency handling

- `program` uses explicit `office` and `apartment_unit` names where justified;
  otherwise it is a slug of the original program label. `source_space_type` and
  `variant` preserve every source distinction, including support/plenum and
  apartment top-floor variants. This is not an ontology claiming semantic
  equivalence among every source label.
- Envelope components preserve all surface/category/climate/window-area/
  projection/operation predicates and film flags. `u_W_m2_K`, SHGC and VT are
  source limits/targets, not final simulated assembly properties. An envelope
  assembler must select compatible components and account for thermal mass.
- Systems preserve source descriptors. HVAC Ruby rules, equipment capacity,
  sizing and climate can change the final generated system. `efficiency_rules`
  stay conditional and unassigned; unresolved COP/fuel/terminal fields stay null.
- Mapping multiplicity sums source zone multipliers for spaces in each program/
  system group. A space may have several services, so counts across systems are
  not necessarily additive. Geometry generators choose their own unit counts.
- Schedule rules retain source dates, source order, selector, value type, units
  and category. Hourly entries have 24 values; constants have one. No calendar,
  holidays, daylight-saving time, leap-year choice or weather is silently added.
  The profile helper inspects month/day rules for validation, with specific
  selectors overriding defaults and later rules overriding earlier matches.
  It does not replace an OpenStudio/EnergyPlus calendar adapter.

## Validation and versions

Structural required fields and bounds, finite values, unique keys, source lock
metadata, foreign keys, building/template/climate labels, typed schedules,
hourly/constant lengths, fraction/activity/temperature bounds, efficiency bounds,
mapping consistency, and provenance field coverage are checked. Thermostat
deadbands are checked on every month/day, weekdays, holidays and design days.
An independent source comparison checks numeric conversions, exact schedule
rules, source attributes and HVAC-map name membership. Offline rebuilding must
match all canonical table bytes.

Breaking changes require a new major schema version and migration notes. Added
compatible fields/source coverage require release notes; corrections identify
affected source fields and records. Frozen releases carry their own contract
and source selection; `release --verify` uses that frozen contract.
