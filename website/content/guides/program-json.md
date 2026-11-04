# Program JSON contract

Every program page offers the two consumer exports of release {{ release }}, read straight from the release by
`scripts.atlas_exports`, as Program JSON {{ schema:program }}:

- **source**: actual values only, as the source states them, including values the source implies as zero. Unknowns
  stay null with their reason.
- **filled**: actual values plus fillings and approved defaults, each filling recorded in `metadata.resolutions`
  with its rule and decision, and draw-only water heating. This is the version BEMGen consumes. Mixes are split into
  their members' loads; holiday rules are added to schedules that lack them (`resolved-schedule-…`).

The program page shows the source export under the download's own keys, then a **Filled export** section with
every block the filled export changes, then the release record's fillings and the record values no export carries.
`?version=source` and `?version=filled` hide the other export's blocks.

The major is 5; each data release added optional fields as a minor: 5.1.0 (DOE reference reconciliation:
fenestration, source calendar, alternates, building services), 5.2.0 (IECC commercial: loads and schedules by
climate, source zones), 5.3.0 (dwelling programs) and 5.4.0 (lighting controls, ADR 0044). A later minor's optional
blocks render on the program page without a site change. IECC commercial, IECC residential and manufactured-housing
programs export the source version only until their water heaters are stored; the
[coverage page](../coverage/index.md) counts them with the reason.

Contracts and schemas: [consumer contracts of release 1.0.0](https://github.com/Energy-Atlas/archetype-atlas/blob/main/docs/consumer-contracts-release-1.0.0.md),
[release 1.1.0](https://github.com/Energy-Atlas/archetype-atlas/blob/main/docs/consumer-contracts-release-1.1.0.md),
the release notes of each data release in [`docs/`](https://github.com/Energy-Atlas/archetype-atlas/tree/main/docs), and the
schemas in [`schemas/`](https://github.com/Energy-Atlas/archetype-atlas/blob/main/schemas). The exporter reads
releases {{ releases }}:

```console
python -m scripts.atlas_exports --release {{ release }} --program ID --version filled
```

## Checksums

Each download names its release and the SHA-256 of the JSON file it saves. The file is the store's canonical JSON:
keys sorted, no insignificant whitespace, UTF-8 without `\u` escapes, numbers as Python writes them, no trailing
newline (`json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))`). The same JSON in any
layout, such as the exporter's indented output, has the same canonical SHA-256:

```console
python -m scripts.site_store program.json
```

Without JavaScript, **Download** saves the gzip file itself, named by the SHA-256 of its gzip bytes; decompressed,
it is the canonical file. The [site index guide](site-index.md) describes the store.

## Nulls and zeros

From release 2.3.0 (Program JSON 6.0.0, [ADR 0054](https://github.com/Energy-Atlas/archetype-atlas/blob/main/docs/adr/0054-release-2-3-0-export-contracts.md))
a null never stands alone. Every load has a `status`: `known` (the source value, a source zero included),
`unknown` (null, with its `reason`) or `filled` (a stored filling, with its rules and basis; filled version only).
`nulls` gives every other null its meaning by JSON pointer: `unknown` (the source does not give it), `none`
(known: there is none), `not_applicable` (the field does not apply) or, from 6.2.0, `not_conditioned` (a setpoint side
no source equipment serves). A known 0 is a value: a source zero, or the
accepted absence of an unknown load in the filled version (rule `accepted_absence`, ADR 0016, stored on the record).
The filled version lists its zero loads in `metadata.absent_demands`.

From release 2.4.0, Program JSON 6.1.0 ([ADR 0061](https://github.com/Energy-Atlas/archetype-atlas/blob/main/docs/adr/0061-program-json-6-1-0-unoccupied-lighting-cap.md))
adds one optional field and nothing else: `lighting_controls.unoccupied_lighting_cap`, the source model's unoccupied
lighting cap or, where the source has none, `rule: null` with its reason in `nulls`
([lighting controls guide](lighting-controls.md#the-unoccupied-lighting-cap)).

From release 2.5.0, Program JSON 6.2.0 ([ADR 0063](https://github.com/Energy-Atlas/archetype-atlas/blob/main/docs/adr/0063-conditioning-sides-and-per-side-mixes.md))
decides each setpoint side from the source equipment:

- **A side no source equipment serves is absent.** The warehouse bulk storage, the stand-alone retail entry and the
  small-hotel stairs and mechanical room have unit heaters and nothing that cools: `controls.cooling_enabled` is
  `false`, `cooling_setpoint_schedule_id` is null and `nulls` gives it the status `not_conditioned` with the systems
  and the source schedule it replaces (for example 50 °C, which no equipment acts on). Spaces no system serves (the
  90.1 small-hotel storage and laundry) have neither side. The source version states `conditioning_state`
  (`heating_only`, `unconditioned`, …) wherever both flags are known.
- **A mix averages each side over the members that have it**, with the weights renormalised, and
  `controls.setpoint_coverage` gives each side's coverage: the represented-area share of the members that have it.
  The 90.1-2019 warehouse storage mix cools at the fine storage's 26.7 °C with `{"heating": 1.0, "cooling": 0.303}`;
  a side no member has is null (`not_conditioned`, coverage 0).

Hot water differs by family: DOE Ref and IECC programs carry it as a load, 0 where the source zone has no draw;
a 90.1 program carries it only where openstudio-standards assigns a draw to its space type, and otherwise its
folder's `water.json` says whether the space has no local draw, an unknown assignment or a share of a building
draw. Conditioning differs too: IECC programs state it from their thermostats; 90.1 and DOE Ref programs state it
where their source equipment leaves a side unserved (6.2.0) or a filling sets it, and otherwise their setpoint
schedules imply it.

The meanings, which the exporter applies (the first matching row wins):

<!-- nulls-table:start -->
| JSON pointer (`*` one segment) | Meaning of null | Reason |
| --- | --- | --- |
| `/loads/*/value` | `unknown` (or the record's) | The source does not give the magnitude. |
| `/shared_services/*/loads/*/value` | `unknown` (or the record's) | The source does not give the magnitude. |
| `/loads/*/schedule_id` | `unknown` | No schedule: the load's magnitude is unknown, or the source gives no schedule for it. |
| `/shared_services/*/loads/*/schedule_id` | `unknown` | No schedule: the load's magnitude is unknown, or the source gives no schedule for it. |
| `/loads/*/heat_fractions/*` | `unknown` | The source gives no heat fraction; the filled version applies the EnergyPlus default. |
| `/shared_services/*/loads/*/heat_fractions/*` | `unknown` | The source gives no heat fraction; the filled version applies the EnergyPlus default. |
| `/loads/*/*` | `none` | The source object leaves this field blank (no such input). |
| `/shared_services/*/loads/*/*` | `none` | The source object leaves this field blank (no such input). |
| `/controls/people_radiant_fraction` | `unknown` | The source gives no people radiant fraction; the filled version applies the EnergyPlus default (0.3). |
| `/controls/people_sensible_fraction` | `unknown` | The source gives no people sensible fraction; the filled version autocalculates it (EnergyPlus). |
| `/controls/heating_enabled` | `unknown` | The source states no conditioning; setpoint schedules, where given, imply it (the filled version resolves it). |
| `/controls/cooling_enabled` | `unknown` | The source states no conditioning; setpoint schedules, where given, imply it (the filled version resolves it). |
| `/controls/*` | `unknown` (or the record's) | The source gives no value for this control. |
| `/default_policy_id` | `none` | No default policy: the source version applies none. |
| `/fenestration/wwr/*` | `not_applicable` | No exterior wall faces this direction in the program's source zones. |
| `/fenestration/roof` | `not_applicable` | No exterior roof over the program's source zones. |
| `/fenestration/value_by_climate/*/wwr/*` | `not_applicable` | No exterior wall faces this direction in the program's source zones. |
| `/fenestration/value_by_climate/*/roof` | `not_applicable` | No exterior roof over the program's source zones. |
| `/fenestration/variants/*/wwr/*` | `not_applicable` | No exterior wall faces this direction in the dwelling's source zones. |
| `/fenestration/variants/*/roof` | `not_applicable` | No exterior roof over the dwelling's source zones. |
| `/lighting_controls/daylighting` | `none` | A source zero: the complete source model has no daylighting controls in these zones. |
| `/lighting_controls/daylighting_by_climate/*` | `none` | A source zero: the complete source model has no daylighting controls in these zones in that climate. |
| `/lighting_controls/standards_rule/target_illuminance_setpoint_lux` | `none` | openstudio-standards gives no target; its default of 375 lux applies (space_add_daylighting_controls). |
| `/lighting_controls/unoccupied_lighting_cap/rule` | `none` (or the record's) | A source zero: the complete source model has no unoccupied lighting cap in these zones. |
| `/water_use_gains/*/sensible_fraction` | `unknown` | The source gives no sensible fraction for the water use. |
| `/water_use_gains/*/latent_fraction` | `unknown` | The source gives no latent fraction for the water use. |
| `/water_heating/*/service_id` | `none` | A draw of the program itself, served by no shared building service. |
| `/water_heating/*/draw/value` | `unknown` (or the record's) | The source does not give the magnitude. |
| `/water_heating/*/draw/heat_fractions/*` | `unknown` | The source gives no heat fraction; the filled version applies the EnergyPlus default. |
| `/water_heating/*/draw/*` | `none` | The source object leaves this field blank (no such input). |
| `/water_heating/*/*` | `none` | The water heating has no such part. |
| `/water_heating/*/stages/*/*` | `none` | The water-heating stage has no such part. |
| `/dwelling/climate` | `not_applicable` | A code-prototype dwelling spans climates; entries that depend on climate carry applies_with. |
| `/dwelling/vintage` | `not_applicable` | A code-prototype dwelling has a code template, not a stock vintage. |
| `/dwelling/*` | `unknown` | The source dwelling records no value for this field. |
| `/dwelling/*/*` | `unknown` | The source dwelling records no value for this field. |
| `/source_calendar/daylight_saving` | `none` | The source model has no daylight saving period. |
<!-- nulls-table:end -->
