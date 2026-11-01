# ADR 0053: Data corrections for release 2.3.0 (internal mass, the small-hotel elevator, stored absences, names)

Status: accepted (2026-11-01; owner decisions of the 2026-10-31 review, issues A2, F3a, C2, C9, implemented in
stage AT1). The edits are source changes on `main` (`scripts/atlas_edits.py` and its two inputs); the delta folder
of release 2.3.0 is written by stage REL-A. It amends [ADR 0036](0036-suite-based-release-storage.md) section 4
(where the accepted absence lives), [ADR 0037](0037-doe-reference-reconciliation.md) section 1 (an exception to
its prototype rule) and [ADR 0016](0016-program-completion-policy.md) (the accepted absence is stored, not applied
by name).

## 1. Unified internal mass from the whole inventory (issue A2, review S1-01)

**Context.** Release 1.1.0 added DOE-only furnishings to the `mass_accounting.additional_mass.entries` of eight DOE
Ref building-scope sets (retail standalone, small hotel, supermarket and warehouse, both vintages; entries with an
`evidence_id`), but the unified `InternalMass` component kept the quantity of the older entries only. 152 unified
documents disagree with their own inventory: warehouse 0.674 against 2.0 m²/m², small hotel 2.369 against 2.522,
the retail sets under 1 %. The mass contract asks for agreement, and BEMGen refuses all 152.

**Decision.**
- `construction_equivalent_export.internal_mass_from_inventory` forms the unified `InternalMass` of a
  building-scope set from the whole inventory: quantity = the sum of every entry's `area_per_counted_floor_area`;
  contributors = the entries' reference areas by recipe; layers = the fit of the recipes weighted by those areas
  (the fit `_mass_from_profile` always used). In the eight sets every entry uses one recipe, so the fitted assembly
  and its capacity are unchanged; only the quantity and the contributors' reference area change. The edit refuses
  to run if a fit would change, rather than invent a library assembly.
- The edit rewrites the component in the 8 set files (152 contexts); their content-hashed IDs move.
- A check: `atlas_exports.Release.construction` refuses a unified document of release 2.3.0 on whose ready
  `InternalMass` quantity differs from its inventory (`construction_equivalent_export.mass_agrees`), and
  `tests/test_atlas_edits.py` requires every unified document of the edited release to agree (5,138 contexts).

## 2. The 90.1 small-hotel elevator from the PNNL prototypes (issue F3a)

**Context.** openstudio-standards gives the 90.1 small-hotel `Elec/MechRoom` space type 198.2 W/ft²
(2133.407 W/m², evidence locator `/space_types/2xx/electric_equipment_per_area`): DOE Ref's 32 110 W elevator motor
spread over the 15.05 m² ground-floor elevator core `ElevatorCoreFlr1`. PNNL's 90.1 prototypes put 16 024.3 W in
that zone (`ElevatorCoreFlr1_Elevators_Equip`, end use `ElevatorLift`, schedule `BLDG_ELEVATORS`, radiant 0.5,
latent and lost 0) for STD2004 to STD2019, and 8 721.8 W for STD2022. In a reference simulation the 32 kW keeps the
unconditioned core at 53–98 °C all year (38–65 °C with 16 kW). The reconciliation (ADR 0037; plan
`docs/superpowers/plans/2026-10-24-doe-reference-reconciliation.md`, round 6, decision 1) holds that prototype
against openstudio-standards load and schedule differences do not matter.

**Decision (owner, 2026-11-01).**
- **A recorded exception to that rule.** The 90.1 small-hotel elevator takes the PNNL prototype value:
  16 024.3 W / 15.0503 m² = **1064.717 W/m²** in 90.1-2007, 2013 and 2019. The value is read from the PNNL IDFs by
  `scripts/pnnl_point_loads.py` into `data/program-inputs/pnnl-point-load-exceptions-v1.json`: the object's design
  level and the zone's floor area (the sum of its floor surfaces) of the Buffalo file the 90.1 lighting controls cite
  (ADR 0044), with every one of the 19 cities of each standard required to agree. The program's load cites a new
  evidence row: locator `ElevatorCoreFlr1_Elevators_Equip/Design Level {W}`, the IDF as its source file
  (`sourcefile-1bd674a2f0b61e4df440`, `sourcefile-1d796930eb6708ef05fe` and `sourcefile-2f8971af6dc0566d8192` for 2007,
  2013 and 2019; path, SHA-256 and archive in the glossary), the replaced value and evidence ID in its original value. The schedule and heat
  fractions stay (they agree with PNNL).
- **Mixes follow.** The department mix `Support_Mixed_SmallHotel` that holds the room is recomposed as
  `program_composition.compose` forms it (value and mixed schedule from the members; the recomputation reproduces
  every stored small-hotel mix exactly before the edit): 126.163 → 67.88 W/m². The general mix keeps its unknown
  electric equipment (another member is unknown) and takes the stored filling of section 3.
- **The second motor.** openstudio-standards `Prototype.SmallHotel.rb` (`add_extra_equip_elevator_coreflr1`, revision
  `c8c1b9eb`) adds a second 32 110 W motor and a 125 W lights/fan object on `ElevatorCoreFlr1` for 90.1-2004 to 2019.
  The atlas takes neither, and keeps it that way: the PNNL prototype has one 16 024.3 W motor; no atlas record
  carries a second motor (the small-hotel source programs sum to one motor before the edit).
- **The other 90.1 point loads were checked** against the PNNL IDFs (STD2007, 2013, 2019; Denver and Buffalo, every
  value equal between them; programs matched to zones through their openstudio-standards space names). No other
  per-area load carries a DOE Ref point-load magnitude that PNNL changed, so no other value changes. The differences
  found are listed for the owner, not changed:

  | Program (90.1) | Quantity | Atlas | PNNL | Note |
  | --- | --- | --- | --- | --- |
  | Outpatient `Elevator Pump Room` | electric equipment | 57.05 W/m² (2007), 22.60 W/m² (2013, 2019): the lights/fan load | + 13 672.8 W lift motor (`Floor 1 Elevator Pump Room_Elevators_Equip`, 8.45 m²) | motor not carried |
  | Medium office `whole building` | electric equipment | plug load only | + 16 363.2 W lift motor in `Core_bottom` | motor not carried |
  | Secondary school `Mechanical` | electric equipment | plug load only | + 22 659.4 W lift motor (`Mech_ZN_1_FLR_1`) | motor not carried |
  | Highrise / Midrise apartment corridors | electric equipment | 0 W/m² on the elevator schedule | + 17 212.1 W / 8 012.2 W lift motor | motor not carried |
  | Hospital, large hotel, large office | – | – | lift motor as `Exterior:FuelEquipment` (57.6 kW, 75.4 kW, 226.2 kW) | no zone; not carried |
  | Kitchens (both restaurants, hospital, large hotel, both schools) | electric equipment | the main kitchen object to within 0.03 % | + reach-in freezer and refrigerator objects (1–6 % of the zone) | reach-ins not carried |
  | Large office `whole building` (2007), outpatient `Office` (2007), stand-alone retail `Entry` (2007) | electric equipment | 8.07 / 11.84 / 3.23 W/m² | 7.40 / 11.38 / 0 W/m² equivalent | ordinary prototype differences |

  Elevators of types without a PNNL prototype (college, courthouse, laboratory, data centers, office, supermarket,
  tall buildings) were not checked.

## 3. The accepted absence on the record, and every unknown's reason (issue C2, review S1-07, S2-05)

**Context.** 1,596 commercial loads were unknown with neither a filling nor a reason (1,457 additional lighting,
105 electric equipment, 21 occupancy, 13 lighting), and 228 stored fillings (`reviewed_no_occupancy`,
`reviewed_no_lighting`) set only a schedule. The program exporter set their value to 0 by a name rule (ADR 0016:
additional lighting, support spaces by name, data-center occupancy), so a reader of the release saw unknown where
the filled export said absent, and the reason the guide promised was in no file.

**Decision.**
- Every such load of a source program stores its reason (`unresolved`, a glossary `unresolved` ID: additional
  lighting not given by the space-type row; a support-space value not given; or the existing `u-b10d86`) and the
  filling of the accepted absence: `{basis: research_assumption, rules: [accepted_absence], set: {status: known,
  value: 0}}`, with a rule note in the glossary and one evidence row per folder citing this section. A filling that set
  only the schedule gains the value and the rule. An unknown load that a stored filling already resolved (the
  approved gas-equipment absence, `reviewed_no_gas_equipment`) gains its reason only.
- Every unknown load of a mix stores the mix reason (a member is unknown, ADR 0012) and, where its members are then
  all known in the filled view, a filling with the area-weighted value and mixed schedule classified by the members'
  rules (ADR 0036 section 4; the recomputation reproduces all 166 stored mix fillings). Five Courthouse mixes, whose
  member schedules have no design days on the rule calendar (ADR 0039 F3), keep only the reason; the exporter mixes
  the members it completes.
- The exporter's name rule is off for release 2.3.0 on (`program_json_v3.ProgramExporter.absence_by_name`): an
  unknown that reaches the filled view without a filling stops the export. Filled values do not change.
- **IDs move.** A filling and a reason are program content, so 1,550 program IDs move (with the mixes that cite
  them), as ADR 0036 section 8 has it. The rejected alternative, a per-folder fillings file outside the ID like
  `generation.json` (ADR 0051), would have kept the IDs but split one filling model in two; the owner asked for the
  fillings on the record.

## 4. Names that tell same-named records apart (issue C9, review S3-04, S2-07)

**Context.** 42 programs share a folder, mode and name with another (the tall buildings take space types from
other building types' rows: three `Corridor_SuperTallBuilding`), and four 90.1-2007 and 2013 small-hotel
construction sets share their name in pairs.

**Decision.** `scripts/distinguishing_names.py` derives each such record's name from its source distinction into
`data/program-inputs/distinguishing-names-v1.json`: a program takes the openstudio-standards building type of its
space-type row (`Corridor (LargeHotel)_SuperTallBuilding`); a set takes its construction-set row's `is_residential`
(`SmallHotel construction package (residential)` / `(nonresidential)`, rows 27 and 26 of the 2007 table). A name is
outside the program ID; a set's name is also in its stored documents, so the four set IDs move.

## 5. IDs, references and the delta

`atlas_edits.edit(files('2.2.0'))` applies the four edits, re-derives every program and set ID by its rule
(`scripts.release_editor.program_ids`, `set_ids`), renames the files of the IDs that move and substitutes every
citation, including the 2.2.0 `generation.json` blocks, `definition-map.json` and `exporter-inputs.json`. Over
release 2.2.0 it changes or adds 1,883 files, removes 1,562 and moves 1,562 IDs (1,550 programs, 12 sets);
`id_map_bytes` writes the map from 2.2.0 to 2.3.0 IDs for the delta. Re-deriving the IDs of the result moves none, no
file cites a moved ID, and every program and construction exports. Stage REL-A writes the delta from these files.

## 6. Consequences

- Release 2.3.0 changes values only in the 90.1 small-hotel elevator and its support mixes, and the unified
  `InternalMass` quantity of 8 DOE Ref sets; every other filled value is unchanged.
- The generator reads the stored fillings as it reads the others (`atlas_schedules.programmes.view_record`); known
  zeros make no slot, as unknowns did, so bundles change only where values change.
- Consumers that keep 2.2.0 IDs translate them with the 2.3.0 ID map.
