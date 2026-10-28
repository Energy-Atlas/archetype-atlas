# BEMGen handoff: atlas release 2.0.0

Things BEMGen updates when it moves to atlas release 2.0.0 ([ADR 0046](adr/0046-release-2-0-0.md)).
The list grows while milestone A runs (plan
`docs/superpowers/plans/2026-10-27-stages-after-release-1-4-0.md`, section 5a); each
item says what changed in the atlas and what BEMGen does about it.

## 1. Daylighting fractions are plain values (user decision L-1, 2026-10-27)

**Atlas change.** Releases 1.5.0 and 1.6.0 marked each program's
`lighting_controls` with `geometry_dependent: true`: the daylit fractions held for
the PNNL prototype geometry, and a consumer with other geometry was expected to
recompute them (ADR 0044 decision 2.1). Release 2.0.0 drops the flag. The fractions
are program values, applied as given, like a lighting power density.

**BEMGen updates.**

- [ ] Read `lighting_controls.daylighting` (and `daylighting_by_climate` for the
  model's climate zone) from the Program JSON and apply it without recomputing the
  daylit area from BEMGen's geometry:
  - `controlled_lighting_fraction`: the share of the program's lighting power under
    daylight control (EnergyPlus `Daylighting:Controls` reference-point fraction);
  - `illuminance_setpoint_lux`, `control_type`, `method`,
    `minimum_input_power_fraction`, `minimum_light_output_fraction`,
    `stepped_control_steps`: the control settings as recorded;
  - `availability`: `all_days_except_design_days`.
- [ ] Give every zone of the program one reference point that controls
  `controlled_lighting_fraction` of its lights, so the program's controlled share
  matches the record; treat `controlled_floor_fraction` and the zone counts as
  provenance, not as an instruction to split zones.
- [ ] Treat `daylighting: null` as no daylighting controls (a source zero), and
  `status: unknown` as not recorded: neither gets controls.
- [ ] Stop reading `geometry_dependent`; files from release 2.0.0 do not have it.
- [ ] Mixes carry no block: take each member program's controls.

## 2. IDs re-derived once (milestone B, stages B1 and B4, 2026-10-28)

**Atlas change.** Release 2.0.0 re-derives its commercial content-hashed IDs under rules that do
not depend on the interpreter (ADR 0046 section 8). 11,507 IDs changed: library materials and
assemblies, construction sets and programs. `id-map.json` at the release root maps each one to its
new value. 57 pairs of near-identical fitted assemblies became one record each.

**BEMGen updates.**

- [ ] Re-key any stored atlas program, construction-set or assembly ID through `id-map.json` (old to
  new); IDs not in the map are unchanged.
- [ ] Expect one assembly where two near-identical ones were (the map sends both old IDs to it).
- [ ] Recompute nothing: values are unchanged, apart from the merged twins (at most 1e-9 relative).

## 3. PNNL prototype constructions as alternates (milestone B, stage B3, 2026-10-28)

**Atlas change.** Detailed constructions of release 2.0.0 are 4.3.0 (ADR 0046 section 9). In the
90.1 templates, a context whose PNNL prototype builds a component differently by more than 1% carries
`alternates.<role>`. Each holds the atlas values compared and every prototype variant with its share of
the role's net area, an assembly in the document's `assemblies` and its evidence. The building default
stays the openstudio-standards assembly (user decision P1).

**BEMGen updates.**

- [ ] Accept detailed construction 4.3.0 (an additive minor; `alternates` is optional).
- [ ] Keep instantiating the assignments as before; `alternates` is information, not an assignment.
- [ ] To model a component the PNNL way, split its surfaces by the variants' `area_share` (by floor for
  walls: `_grd`, `_mid`, `_top`), each with the variant's assembly.
