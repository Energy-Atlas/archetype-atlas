# Responses to the program JSON field annotations

Inspection date: 2026-10-09. Discussion draft against definition release v0.1.1 and program JSON schema 2.0.0.

Your annotations are retained in the [field review](program-json-field-review.md). Every one of its 54 entries links to a response group here, including the later unannotated entries. “Same”, “similar”, and “see previous” are interpreted by the relevant load object and question, rather than treated as blanket approval. The question under electric-equipment latent fraction's **Agreed decision** is still a question. No scientific or schema proposals below have been implemented.

The most useful change is to distinguish four cases: a reported value; a source recipe that deliberately creates no demand; an engine-supported optional input; and information that our extraction has not resolved. These cases currently appear together as nulls. A clean program JSON should preserve that distinction, retain source overrides, and expose unresolved inputs when they affect the requested experiment.

Two source boundaries explain much of the apparent inconsistency. Commercial source leaves are extracted **standards space-type recipes**, including code/prototype and DOE reference variants; they are not full ComStock building outputs. Residential source leaves reuse a **schedule-only** execution, not the full HPXML defaults and load translation. Later reviewed variants and mixtures propagate or resolve these source gaps. A building-type count such as “Office” or “Hotel” does not mean the occupied office or guest room has that gap.

Evidence aggregates and inspected source hashes are in [program-json-investigation-evidence.json](program-json-investigation-evidence.json). The existing field review supplies full-library denominators. Counts below use **768 commercial source leaves** or **41 dwelling fixtures**, unless otherwise specified; mixtures are not counted again as independent source observations.

## People activity

**Fields:** `controls.activity_schedule_id`. Related later fields: occupancy magnitude and occupancy schedule under [load coverage](#load-coverage).

ResStock's stochastic generator produces the **occupancy fraction**, not the metabolic activity schedule used by `People`. In the pinned HPXML translator, `InternalGains.apply_building_occupants` creates a separate constant activity schedule. `Defaults.get_occupancy_values` supplies 3,716 sensible plus 2,884 latent Btu/person/day over 16.5 hours: 400 Btu/person/hour, converted upstream to **117.228428 W/person**. This applies to the inspected nonzero-occupancy translator branch; zero occupants cause that routine to return before creating a People object. It is a source modeling rule, not a measured metabolic rate or a universal residential assumption. See [internal_gains.rb, lines 14–70](https://github.com/NatLabRockies/resstock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/HPXMLtoOpenStudio/resources/internal_gains.rb#L14-L70), [defaults.rb, lines 7441–7451](https://github.com/NatLabRockies/resstock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/HPXMLtoOpenStudio/resources/defaults.rb#L7441-L7451), and [unit_conversions.rb](https://github.com/NatLabRockies/resstock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/HPXMLtoOpenStudio/resources/unit_conversions.rb#L36-L39).

Our residential adapter imports no activity rule, so all 41 dwelling definitions lack it. The commercial table has 57 missing references, concentrated in plenums, attics, data centers, elevator cores, mechanical rooms and corridors. The standards helper assigns a People activity schedule only when a reference is supplied. EnergyPlus requires an activity schedule for an instantiated People object; it has no general 120 W/person fallback.

**Proposal:** recover the pinned residential constant with provenance, keep reported commercial activity schedules, and require an explicit experimental activity choice for genuinely unresolved, occupied commercial programs. Do not create a People object for source-proved zero occupancy merely to satisfy a uniform field list. The existing atlas 120 W/person fallback remains an experimental assumption until we revise its policy.

**Your response / decision:**


## Conditioning

**Fields:** `controls.heating_enabled`, `cooling_enabled`, and both setpoint schedule references. This addresses both possible readings of “same question as above”: system presence and missing desired-temperature schedules.

Separating program temperature preferences from subsequently assigned construction and HVAC fits the repository's modular model. However, the two current flags also carry reviewed **inactive-conditioning** information; deleting them without relocating that evidence would lose a distinction needed for cavities and indirectly conditioned support spaces.

All 41 residential fixtures already have both nominal thermostat profiles. Their missing load schedules are a different issue. The commercial source table lacks both thermostat references in the same **43** leaves: 14 attics, 10 plenums, eight elevator cores, five electrical/mechanical rooms, and six corridors. Frozen resolution rules cover these 43 through 24 reviewed-unconditioned and 19 inspected-inactive-controls cases. The full-library count of 116 missing references also includes definitions derived from source views; it does not establish 116 missing HVAC systems.

The standards helper creates a dual-setpoint thermostat and assigns either schedule only when its table reference exists. That operation alone neither hooks it to a zone nor proves equipment presence. The repository's earlier control inspection supplies stronger, explicitly scoped evidence for its reviewed cases. See [Standards.SpaceType.rb, lines 501–523](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/lib/openstudio-standards/standards/Standards.SpaceType.rb#L501-L523), [resolve.py](../../scripts/resolve.py), and [frozen resolutions](../../data/resolution-releases/v0.4.0/resolutions.json).

**Proposal:** remove equipment-presence interpretation from the program contract; retain nominal temperature preferences for programs that need them, and relocate applicability/conditioning constraints into the program-to-zone/HVAC assignment contract. Distinguish “no direct thermostat required by this source recipe” from “unknown desired temperature”. Preserve the source and reviewed variants separately. A consumer assigning HVAC to an originally unconditioned cavity must make that changed experimental condition explicit. This is a schema/assignment decision requiring an ADR and migration, not a deletion of evidence or an automatic 20/26 °C substitution.

**Your response / decision:**


## People heat

**Fields:** `controls.people_radiant_fraction`, `controls.people_sensible_fraction`.

EnergyPlus 25.1.0 supports blank People fields defaulting to **0.3 radiant fraction of sensible heat** and **autocalculate sensible fraction**. The latter calculates a sensible/latent split rather than setting it to zero. An OpenStudio importer may have its own required-field handling; the historical SDK IDD inspected in this repository marks radiant fraction required. “Omit from our JSON” therefore needs an importer policy, not a promise that every consumer can leave every field blank.

The current exporter hardcodes both raw operands to null; “never supplied” does not establish that the sources lack values. The pinned commercial helper explicitly sets radiant fraction to 0.3. ResStock explicitly supplies **sensible fraction 3716/6600 ≈ 0.5630303** and sets its People radiant field to **0.558 × that fraction ≈ 0.3141709**. Preserve that assignment exactly if reproducing the source; the People radiant field is defined relative to sensible heat, so it must not be casually reinterpreted as a fraction of total metabolic heat. See [Standards.People.rb, lines 62–72](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/lib/openstudio-standards/standards/Standards.People.rb#L62-L72) and [InternalGains.apply_building_occupants](https://github.com/NatLabRockies/resstock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/HPXMLtoOpenStudio/resources/internal_gains.rb#L23-L67).

**Proposal:** make these supported thermal parameters optional, retain source overrides, and allow documented engine defaults where the selected source recipe delegates them. Move redundant default-only fields out of ordinary program records if desired, but keep the engine/version and resolved value visible in import diagnostics. For residential records, extract the available source rules before dropping fields. The current 0.3/autocalculate atlas fallback is not a faithful replacement for the pinned residential translator.

**Your response / decision:**


## Equipment heat

**Fields:** electric and gas equipment `heat_fractions.latent`, `radiant`, `lost`, `visible`, `return_air`. All five “same as above” questions require object-specific treatment.

For EnergyPlus 25.1.0 `ElectricEquipment` and `GasEquipment`, latent, radiant and lost are supported inputs with defaults of zero. **Visible and return-air fractions are not fields of these objects.** Their appearance as universally missing attributes comes from our uniform five-fraction DTO, not five unresolved source inputs. `OtherEquipment`, used by the residential translator for fuel appliances, also needs its own fuel-aware mapping.

The commercial helper conditionally sets latent/radiant/lost when supplied and otherwise leaves those definition fields at SDK defaults. That can justify an explicit recipe/engine default for a newly constructed definition; it does not prove how an arbitrary pre-existing model object was configured. See [Standards.SpaceType.rb, lines 220–306](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/lib/openstudio-standards/standards/Standards.SpaceType.rb#L220-L306).

ResStock does **not** generally omit these fractions and let EnergyPlus choose zero. Its plug-load translator sets radiant to 0.6 × sensible outside the ASHRAE-140 branch, latent to the specified/defaulted latent share, and lost to 1 − sensible − latent. Appliance routines similarly calculate heat splits, then explicitly assign them through `Model.add_electric_equipment` / `add_other_equipment`. Those methods are outside our schedule-only execution. For example, the residual-MEL rule supplies sensible 0.855, latent 0.045 and lost 0.10; translation yields radiant 0.513. These are a rule illustration, not newly extracted magnitudes for the 41 fixtures. See [misc_loads.rb, lines 87–106](https://github.com/NatLabRockies/resstock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/HPXMLtoOpenStudio/resources/misc_loads.rb#L87-L106), [defaults.rb, get_residual_mels_values](https://github.com/NatLabRockies/resstock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/HPXMLtoOpenStudio/resources/defaults.rb#L7460-L7485), and [hotwater_appliances.rb](https://github.com/NatLabRockies/resstock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/HPXMLtoOpenStudio/resources/hotwater_appliances.rb#L50-L135).

**Proposal:** remove visible/return-air from these object-specific input shapes. Keep supported latent/radiant/lost as optional overrides, preserving every known value. Recover residential splits from the selected pinned defaults/translation branches. Permit engine defaults only through an explicit importer policy when the recipe actually delegates the field. Missing is not evidence that heat partition is unimportant: lost changes zone gains, latent changes moisture loads, and radiant changes the timing/location of sensible gains. No sensitivity simulation was run here, so negligible impact has not been established.

Mixtures need another distinction: their canonical aggregate carries component trajectories and an evaluation method, not scalar heat-fraction fields. The raw exporter reads only scalar fractions, so some apparent missing aggregate fractions are available in the constituents. Export/evaluate those source components rather than declaring them unknown or independently averaging fractions. The defaulted exporter already expands mixture leaves; its representation differs from the raw aggregate path. See [program_composition.py](../../scripts/program_composition.py) and [program_json.py](../../scripts/program_json.py).

**Your response / decision:**


## Lighting heat

**Fields:** lighting `heat_fractions.latent`, `lost`, `radiant`, `visible`, `return_air`.

These cannot all inherit the equipment answer. EnergyPlus `Lights` supports radiant, visible and return-air shares, each defaulting to zero in the inspected engine. It has no corresponding latent/lost input fields. The commercial tables supply meaningful lighting shares, often nonzero, and the helper applies them. Residential `Model.add_lights` explicitly sets **radiant 0.6, visible 0.2 and return-air 0.0** for interior/garage lighting. Exterior lighting uses a separate object without indoor heat fractions. See [model.rb, lines 236–248](https://github.com/NatLabRockies/resstock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/HPXMLtoOpenStudio/resources/model.rb#L236-L248) and [commercial lighting assignments](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/lib/openstudio-standards/standards/Standards.SpaceType.rb#L131-L202).

**Proposal:** remove latent/lost from the native Lights input shape; preserve radiant/visible/return-air when reported or deterministically supplied by the source translator. Allow a documented engine fallback only where justified. The return-air share needs a compatible return path when instantiated; its interaction with system assignment remains a consumer constraint. For an abstract heat-balance representation, unsupported native inputs would need a separately named, explicitly defined model rather than being presented as missing EnergyPlus parameters.

**Your response / decision:**


## Load coverage

**Fields:** electric equipment, lighting and occupancy `value` and `schedule_id`. This includes unannotated lighting magnitude and both occupancy fields.

The commercial gaps are specific program/template combinations, not a residential stochastic-generator limitation:

| Source field | Missing / 768 | Verified pattern |
| --- | ---: | --- |
| Electric-equipment schedule | 24 | 14 attics and 10 plenums; all have unknown equipment magnitude |
| Electric-equipment magnitude | 33 | The same 24 cavities, eight SmallHotel elevator cores, and one DOE Ref 1980-2004 Hospital ER_Triage |
| Ordinary lighting schedule | 28 | 10 plenums, 14 attics, two electrical/mechanical rooms and two elevator cores; 18 have reported zero lighting, ten have unknown lighting |
| Ordinary lighting magnitude | 10 | Plenums |
| Additional-lighting magnitude | 741 | Broadly absent in tables; distinct from ordinary lighting |
| Occupancy schedule | 45 | 30 unknown magnitudes and 15 reported zero magnitudes, concentrated in support spaces |
| Occupancy magnitude | 30 | 14 attics, ten plenums and six LargeOffice data-center leaves |

No missing commercial occupancy, ordinary-lighting or electric-equipment schedule in this scan has a **known positive** corresponding magnitude. Thus a generic “positive office equipment without a schedule” explanation would be wrong for these source leaves. Office cavity programs coexist with occupied offices that have complete data. Some apparent repeats also come from source/reviewed views and mixtures; those views must remain identifiable.

The large lighting-schedule count needs a further explanation: **400** of the 431 missing occurrences are additional lighting, comprising 28 source leaves and **372 mixtures**. When any constituent magnitude is unknown, composition leaves the aggregate magnitude and magnitude-weighted schedule unknown, even if individual schedule shapes exist. Those 372 are 186 source-view and 186 reviewed-view mixtures. They are not 372 failed schedule extractions. Electric equipment similarly has 72 missing commercial references: 24 source cavities, their 24 reviewed counterparts, and 24 mixtures with unknown aggregate magnitude. The original constituent trajectories remain available for a component-based export. This follows [program_composition.py](../../scripts/program_composition.py), not the stochastic generator.

Commercial density extraction currently creates all nominal load channels even when the helper would create no instance. The helper converts an absent additional-lighting density through `.to_f` and adds extra lights only if nonzero and within its lighting branch; this supports absence in that **clean recipe**, not a universal assertion that such a program never has extra lighting. Likewise, a hotel elevator can acquire direct/custom equipment elsewhere; a missing standards density does not recover its actual motor demand.

The dwelling profile gaps are now explainable from exact execution inputs:

| Profile channel | Missing original profiles / 41 | Frozen supplement already resolves them |
| --- | ---: | --- |
| Other plugs, TV, interior lighting, fixture water | 3 each | Three zero-occupant operational cases |
| Clothes washer, dryer, washer water | 8 each | Six selected-absent cases plus two vacancy cases |
| Cooking range | 4 | One selected-absent case plus three vacancy cases |

The vacancy and selected-absent sets overlap: one of the three vacant fixtures already lacks laundry appliances. These are deliberate generator omissions/operational skips, not failed stochastic generation. The original profile files correctly preserve what ran. **Our residential definition adapter fails to apply the additional frozen resolutions**, even though release v0.4.0 contains them. It also omits the separately resolved background channels; see [residential channels](#residential-channels). See [run_residential_profiles.rb](../../scripts/run_residential_profiles.rb), [residential_definitions.py](../../scripts/residential_definitions.py), and [frozen supplement](../../data/resolution-releases/v0.4.0/resolutions.json).

Magnitudes are a separate problem. All 205 exported residential appliance/plug magnitudes, 41 interior-lighting magnitudes and 82 water magnitudes are left unknown by design in the schedule-only adapter. A normalized annual profile supplies timing, not W/dwelling or m³/s/dwelling. Full translation uses appliance characteristics, usage factors, occupants/bedrooms, floor area where applicable, location, and selected calculation branches. Electrical design power is obtained from annual energy divided by equivalent full-load hours; annual kWh cannot be relabelled as peak W. See [SchedulesFile.calc_design_level_from_annual_kwh](https://github.com/NatLabRockies/resstock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/HPXMLtoOpenStudio/resources/schedules.rb#L1298-L1312).

**Proposal:** apply frozen residential resolutions through a separately identified reviewed definition view, leaving original execution evidence immutable; represent source-proved absent end uses explicitly and omit their active demand objects. Recover magnitudes from exact source rules where the required bindings are available, otherwise name the required input. For commercial recipes, similarly distinguish absent instances from unresolved direct/custom loads. Keep Hospital ER_Triage and elevator magnitude recovery open rather than merging them into the cavity explanation. Replace broad default-to-zero completeness claims with resolved/absent/unknown applicability reporting. Rebuild mixtures from the selected leaf views so known components survive.

**Your response / decision:**


## Gas presence

**Fields:** gas equipment `schedule_id`, `value`; connected fuel-classification gaps under [residential channels](#residential-channels).

The raw placeholder does not establish gas consumption. `build_programs` makes a gas-equipment channel for every commercial leaf; 713/768 have neither density nor schedule. The clean standards helper only creates gas equipment for a nonzero density. Existing reviewed resolutions already supply explicit zero density/schedule for those 713 recipe cases. The remaining 55 source leaves have gas magnitude and schedule data. This is not an all-electric-building classification: gas heating, water heating and separately added/custom equipment remain distinct.

The full-library missing gas-reference count of 902 is those 713 source leaves plus 189 source-view mixtures whose magnitude/schedule cannot be aggregated through unknown constituents. It does not demonstrate additional gas uses in 902 independent programs. Reviewed absence and constituent preservation should resolve the recipe semantics before considering any fallback.

**Proposal:** instantiate gas demands only when the chosen recipe supports them; retain absence status/evidence rather than a missing gas object with an invented schedule. Preserve uncertainty for models whose complete recipe has not been inspected. Apply the existing reviewed absence variant when that is the intended experiment. Separately fix residential fuel mapping: some cooking/drying demands consume fuel, and the current name-based classification hides that issue. Do not use “gas schedule absent” alone as either evidence of gas demand or evidence of zero building gas use.

**Your response / decision:**


## Water inlet

**Field:** `hot_water.inlet_temperature_schedule_id`, including shared-service demand entries.

This is not 700 independent missing source observations: the exporter always calls its inlet schedule function with `None`, so every exported water entry lacks the operand. Water mains/inlet temperature belongs primarily to weather/site/system context. The pinned residential translator derives daily inlet temperatures from weather and distribution/heat-recovery context, then assigns the resulting mains schedule. It is not universally 10 °C. See [hotwater_appliances.rb, lines 330–358](https://github.com/NatLabRockies/resstock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/HPXMLtoOpenStudio/resources/hotwater_appliances.rb#L330-L358).

**Proposal following your suggestion:** bind a shared weather-derived mains schedule at model/service level, with an explicit user-supplied alternative when needed. A climate-zone label alone is too coarse to reproduce a daily temperature trajectory. EnergyPlus `Site:WaterMainsTemperature` supports a schedule or weather-file correlation; `WaterUse:Equipment` can inherit that context when its cold-water supply schedule is omitted. Validate the resulting binding and temperature ordering, rather than silently dropping inlet context and hoping the engine chooses the intended climate. Retain any source-specific inlet or heat-recovery override at the relevant service boundary. Keep the existing 10 °C experimental fallback separately selectable until policy migration.

**Your response / decision:**


## Water demands

**Fields:** hot-water `schedule_id`, `value`, `target_temperature_schedule_id`. They share residential pipeline gaps but have different causes.

The eleven missing local schedules are **eight washer-water plus three fixture-water profiles** in dwelling definitions; their exact absence/vacancy resolutions are described under load coverage. Their missing magnitudes are all 82 residential water demands, independently of whether a shape exists. Existing commercial local/shared demand magnitudes and flow schedules are available in the emitted entries; omitted commercial allocations are a separate problem.

All 82 residential target temperatures are unresolved because the adapter does not translate water demand temperatures. The other **26** missing occurrences in the combined 108 total are **composed local commercial demands**, not unknown shared-service targets: ten Outpatient, ten LargeHotel and six SmallHotel aggregate entries. Every constituent retains a known **60 °C** target. The aggregation/raw-export path drops that scalar even though the evidence is present; the defaulted path instead expands the leaves. This is recoverable representation loss, not a new temperature assumption. See [program_composition.py](../../scripts/program_composition.py), [program_json.py](../../scripts/program_json.py) and the investigation evidence's `commercial_water_target_aggregation`.

In the residential translator, mixed fixture water uses **105 °F = 40.555556 °C**, while appliance water can leave target unset to inherit the served hot-water context. That is different from a water-heater storage setpoint. See [fixture mixing and target assignments](https://github.com/NatLabRockies/resstock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/HPXMLtoOpenStudio/resources/hotwater_appliances.rb#L330-L418) and [Model.add_water_use_equipment](https://github.com/NatLabRockies/resstock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/HPXMLtoOpenStudio/resources/model.rb#L150-L164).

**Proposal:** consume the existing shape resolutions, derive peak flow with the correct volume/time normalization, and distinguish fixture delivery target from heater/system supply temperature. Recover composed commercial demands from their source components; preserve the known common target here, and keep separate trajectories if component targets differ in future variants. Treat residential appliance inheritance as an explicit service binding where the source does so. EnergyPlus's blank water target inherits hot supply; blank hot supply itself inherits cold supply, so omission without a valid served hot-water context can eliminate the intended heating demand. A universal 60 °C target is not source recovery.

**Your response / decision:**


## Residential channels

**Fields:** omitted `ceiling_fan`, `dishwasher`, `hot_water_dishwasher`, `lighting_garage`; cooking-range and clothes-dryer fuel classifications. These are related to the same extraction boundary, but fuel and host allocation require additional care.

The canonical definition adapter selects a fixed channel list. It drops annual profiles that do exist for dishwasher and washer-independent dishwasher water (26 fixtures each), ceiling fans (26) and garage lighting (14). Frozen resolutions also supply refrigeration, freezer and exterior-lighting variants or absence states; these are missed by the adapter too. Recovering an omitted schedule does not establish its magnitude or the physical host of garage/exterior/shared loads.

The DTO currently labels all residential cooking/drying as electric equipment. Seventeen fixtures select gas/propane cooking and seven select gas/propane drying. The pinned residential translator can create **both electrical and fuel demands for the same appliance**, using explicit fuel type on `OtherEquipment`. A simple switch from electric to gas would still lose the electrical component and propane distinction. See [dryer translation](https://github.com/NatLabRockies/resstock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/HPXMLtoOpenStudio/resources/hotwater_appliances.rb#L114-L136) and [cooking translation](https://github.com/NatLabRockies/resstock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/HPXMLtoOpenStudio/resources/hotwater_appliances.rb#L278-L326).

**Proposal:** enumerate selected, included end uses from the resolved source inventory, not a short hardcoded list; preserve absent/excluded/unknown status. Represent fuel and potentially separate energy components explicitly, with stable demand identities and shared appliance schedule provenance. Preserve declared schedule-release exclusions. Discuss garage/exterior/common-area hosting and fuel-aware DTO shape before implementation; do not merge these into a generic missing-electric-equipment default.

**Your response / decision:**


## Schedule coverage

**Later unannotated field:** incomplete `schedules[].rules` coverage.

The audit found five distinct incomplete referenced rulesets affecting 18 program definitions: 12 LargeOffice and six MediumOffice. A missing schedule reference, a deliberately absent load and a present-but-partial ruleset are different cases. Our current default policy prepends a low-priority fallback while preserving source rule order; that produces an explicit experimental completion, not proof that the source supplied a complete ruleset.

**Proposal:** retain source/reviewed rule variants, rule dates, selectors, design days and source order. Inspect uncovered selectors/dates before choosing a fallback, and count only schedules attached to applicable demands/controls. Keep this item open for the next discussion: a load-absence resolution cannot repair a partially covered active schedule. The evidence date/calendar of an annual realization remains fixed; importing into a different simulation year needs an explicit calendar policy.

**Your response / decision:**


## Air requirements

**Distinct later fields:** omitted commercial ventilation per area/per person/ACH, infiltration rate/basis, and residential natural infiltration/outdoor air.

The DTO omits known outdoor-air terms: 700/768 per-area, 520/768 per-person and 39/768 ACH values exist upstream. Their different presence rates do not define interchangeable substitutes. Commercial infiltration rate/basis remain unresolved in this selection. Residential ACH50 is pressure-test evidence, not natural infiltration or mechanical outdoor-air demand.

**Proposed discussion:** put program outdoor-air requirements in the program/assignment interface while retaining calculation method and simultaneous terms; put envelope leakage and the weather/geometry-dependent conversion in the enclosure/model interface. Inspect helper combination rules before treating a null term as zero or taking a maximum/sum. This is a separate physical/schema decision, not covered by the heat-fraction omission suggestion.

**Your response / decision:**


## Water allocation

**Distinct later field:** omitted program/service allocation.

There are 279 unresolved distinct commercial source-program allocations, concentrated in supermarkets, hotels, hospitals and schools. They are separate from 206 source-proved no-modeled-program-draw cases. A whole-building/shared service can be known while the beneficiary distribution or fixture zone is not. Mains temperature and flow-schedule completion do not solve this allocation.

**Proposed discussion:** retain each physical service once; bind an explicit consumer host and independently document any reporting allocation. Do not clone the full building demand into every referenced program or use an unsupported floor-area allocation as a physical fixture location. Decide which allocation/host inputs the zoning experiment must supply.

**Your response / decision:**


## Context

**Distinct later fields:** dedicated `source.climate` and `source.vintage` context.

These residential descriptors exist upstream but lack dedicated DTO fields. They are not unknown physical operands and should not receive numerical defaults. Vintage describes the selected stock fixture; it must remain distinguishable from a commercial code/prototype template. Climate context is also different from the actual EPW/station proxy used for the schedule realization.

**Proposed discussion:** expose these as optional source-context descriptors, retaining weather realization provenance separately. Decide whether self-contained exports must include them or may resolve them through a pinned definition manifest. Avoid duplicating climate-independent program rows to manufacture coverage.

**Your response / decision:**


## Composition

**Distinct later field:** recipe members and weights for 378 mixtures.

The DTO exports weighted demand trajectories but does not carry a dedicated mixture recipe. Selecting corrected source/reviewed leaves affects mixtures; one cannot default an unknown aggregate to zero without potentially erasing known contributions. The recipe exists in the pinned canonical definitions.

**Proposed discussion:** retain a pinned recipe reference or explicit member IDs/weights, including the selected evidence view and scaling basis. Decide whether an exported DTO is an executable snapshot only or must also support reconstruction/editing of its program mix. This is independent of optional EnergyPlus object fields.

**Your response / decision:**


## Provenance

**Later fields:** `source.evidence[].original_value`, `source_file_id`, and omitted operand-to-evidence/source descriptors.

The full-library audit reports 3,285 null original-value evidence entries and 2,155 null source-file IDs. A retained source null and generated resolution evidence are not missing physical values to default. Generated evidence can legitimately have no raw-file ID while needing a traceable frozen resolution/helper reference. These counts repeat evidence across exports and are not counts of lost source files.

**Proposal:** preserve original nulls and distinguish raw-source evidence, deterministic derivations, reviewed resolutions and experimental assumptions. Provide operand links plus pinned source or generated-artifact descriptors if exports must be self-contained; otherwise require a pinned manifest binding. Never fill source metadata with invented originals or file IDs. This is a distinct export/provenance design discussion even though several physical gaps above arise from extraction omissions.

**Your response / decision:**


## Proposed order of work

1. Discuss the annotated groups: typed optional heat parameters; source-derived residential people rules; explicit demand applicability; weather/service inlet binding; program temperature preferences versus HVAC assignment.
2. Agree how recovered residential resolutions and source rules appear as reviewed variants, preserving immutable source execution. Recover available fields before choosing generic defaults for genuinely unresolved ones.
3. Discuss the remaining distinct items: fuel components and garage/exterior hosts; the non-cavity commercial equipment magnitudes; partial rulesets/calendar binding; air requirements; shared-water allocation; context; mixture reconstruction; and operand provenance. The 26 composed commercial water targets are an identified recovery task, not an unresolved default choice.
4. Record agreed schema decisions in ADRs, migrate exporters/importers and default-policy versioning, then validate the Medium Office pilot and residential examples before regenerating a release. This investigation makes no release-completeness or full-simulation claim.

## Engine and reproduction evidence

The engine field/default observations were read directly from **EnergyPlus 25.1.0** `Energy+.idd` bundled with the repository's SHA-256-locked OpenStudio 3.10.0 runtime. Relevant object locators are `People` (line 21431), `Lights` (22339), `ElectricEquipment` (22442), `GasEquipment` (22509), `Site:WaterMainsTemperature` (2366) and `WaterUse:Equipment` (93731). [Official versioned IDD source](https://github.com/NatLabRockies/EnergyPlus/blob/v25.1.0/idd/Energy%2B.idd.in). The inspected bundled bytes and archive checksum are recorded in the investigation evidence; defaults are version-specific, not an assertion about all engines or SDKs. Historical OpenStudio required-field behavior is pinned separately in [source-default-lock.json](source-default-lock.json).

All inspected ResStock methods use revision `dd25369f41a83a0767aefeeac0b6f8a0b0edd649`; commercial helpers use standards revision `c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907`. The reproduction script compares each inspected upstream file directly to its checksum-locked source/runtime archive. Counts read frozen canonical releases; source locators, original units/values, transformations and interpretation remain in frozen evidence and in the method references above. Formulas and numbers in these responses are source-rule examples, not newly inserted program values.

```powershell
.venv/Scripts/python.exe -m scripts.program_field_investigation
.venv/Scripts/python.exe -m scripts.program_field_investigation --check
.venv/Scripts/python.exe -m scripts.program_json_field_review --check
```

Locked local archives are prerequisites for reproducing source inspection; no upstream code or EnergyPlus simulation is executed by the investigation script. Your original per-field annotation blocks remain the decision record; the group response areas here can hold follow-up discussion.
