# Responses to the program JSON field annotations

Inspection dates: 2026-10-09 and 2026-10-11. Decision record and investigation against definition release v0.1.1 and program JSON schema 2.0.0.

Your annotations are retained in the [field review](program-json-field-review.md) and verbatim below. Every one of its 54 entries links to a response group here, including the later unannotated entries. **The dated follow-ups below supersede the earlier proposals where your comments settle a choice.** Accepted policy is recorded in [ADR 0016](../adr/0016-program-completion-policy.md). This update changes the investigation and decision record; the JSON/schema/export migration has not been implemented. Schedule gap completions remain proposals for discussion.

The most useful change is to distinguish four cases: a reported value; a source recipe that deliberately creates no demand; an engine-supported optional input; and information that our extraction has not resolved. These cases currently appear together as nulls. A clean program JSON should preserve that distinction, retain source overrides, and expose unresolved inputs when they affect the requested experiment.

Two source boundaries explain much of the apparent inconsistency. Commercial source leaves are extracted **standards space-type recipes**, including code/prototype and DOE reference variants; they are not full ComStock building outputs. Residential source leaves reuse a **schedule-only** execution, not the full HPXML defaults and load translation. Later reviewed variants and mixtures propagate or resolve these source gaps. A building-type count such as “Office” or “Hotel” does not mean the occupied office or guest room has that gap.

Evidence aggregates and inspected source hashes are in [program-json-investigation-evidence.json](program-json-investigation-evidence.json). The existing field review supplies full-library denominators. Counts below use **768 commercial source leaves** or **41 dwelling fixtures**, unless otherwise specified; mixtures are not counted again as independent source observations.

## People activity

**Fields:** `controls.activity_schedule_id`. Related later fields: occupancy magnitude and occupancy schedule under [load coverage](#load-coverage).

ResStock's stochastic generator produces the **occupancy fraction**, not the metabolic activity schedule used by `People`. In the pinned HPXML translator, `InternalGains.apply_building_occupants` creates a separate constant activity schedule. `Defaults.get_occupancy_values` supplies 3,716 sensible plus 2,884 latent Btu/person/day over 16.5 hours: 400 Btu/person/hour, converted upstream to **117.228428 W/person**. This applies to the inspected nonzero-occupancy translator branch; zero occupants cause that routine to return before creating a People object. It is a source modeling rule, not a measured metabolic rate or a universal residential assumption. See [internal_gains.rb, lines 14–70](https://github.com/NatLabRockies/resstock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/HPXMLtoOpenStudio/resources/internal_gains.rb#L14-L70), [defaults.rb, lines 7441–7451](https://github.com/NatLabRockies/resstock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/HPXMLtoOpenStudio/resources/defaults.rb#L7441-L7451), and [unit_conversions.rb](https://github.com/NatLabRockies/resstock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/HPXMLtoOpenStudio/resources/unit_conversions.rb#L36-L39).

Our residential adapter imports no activity rule, so all 41 dwelling definitions lack it. The commercial table has 57 missing references, concentrated in plenums, attics, data centers, elevator cores, mechanical rooms and corridors. The standards helper assigns a People activity schedule only when a reference is supplied. EnergyPlus requires an activity schedule for an instantiated People object; it has no general 120 W/person fallback.

**Proposal:** recover the pinned residential constant with provenance, keep reported commercial activity schedules, and require an explicit experimental activity choice for genuinely unresolved, occupied commercial programs. Do not create a People object for source-proved zero occupancy merely to satisfy a uniform field list. The existing atlas 120 W/person fallback remains an experimental assumption until we revise its policy.

**Your response / decision:**
For the missing references in the commercial tables, e.g. attics, elevator cores, mech rooms ... they are almost certainly zero occupancy settings.
Try to recover the pinned residential.
If you have occupancy but lack the metabloic activity, it is safe to use a default value for that.

**Agent follow-up — 2026-10-11 (accepted):** recover the residential **117.228428 W/person** source rule first. Of the 57 commercial missing activity references, **27 already have zero occupancy and 30 have unknown occupancy; none has a known positive occupancy magnitude**. The 30 are 14 attics, ten plenums and six data-center leaves. Apply your unoccupied-support-space assumption to these missing occupancy cases, recording it as a reviewed assumption rather than changing the raw source. Omit inactive People objects. For an active People object whose activity remains unresolved after recovery, use the existing atlas **120 W/person** fallback automatically and identify it as an atlas assumption, not an engine default. Preserve all reported positive occupancy and activity values.

## Conditioning

**Fields:** `controls.heating_enabled`, `cooling_enabled`, and both setpoint schedule references. This addresses both possible readings of “same question as above”: system presence and missing desired-temperature schedules.

Separating program temperature preferences from subsequently assigned construction and HVAC fits the repository's modular model. However, the two current flags also carry reviewed **inactive-conditioning** information; deleting them without relocating that evidence would lose a distinction needed for cavities and indirectly conditioned support spaces.

All 41 residential fixtures already have both nominal thermostat profiles. Their missing load schedules are a different issue. The commercial source table lacks both thermostat references in the same **43** leaves: 14 attics, 10 plenums, eight elevator cores, five electrical/mechanical rooms, and six corridors. Frozen resolution rules cover these 43 through 24 reviewed-unconditioned and 19 inspected-inactive-controls cases. The full-library count of 116 missing references also includes definitions derived from source views; it does not establish 116 missing HVAC systems.

The standards helper creates a dual-setpoint thermostat and assigns either schedule only when its table reference exists. That operation alone neither hooks it to a zone nor proves equipment presence. The repository's earlier control inspection supplies stronger, explicitly scoped evidence for its reviewed cases. See [Standards.SpaceType.rb, lines 501–523](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/lib/openstudio-standards/standards/Standards.SpaceType.rb#L501-L523), [resolve.py](../../scripts/resolve.py), and [frozen resolutions](../../data/resolution-releases/v0.4.0/resolutions.json).

**Proposal:** remove equipment-presence interpretation from the program contract; retain nominal temperature preferences for programs that need them, and relocate applicability/conditioning constraints into the program-to-zone/HVAC assignment contract. Distinguish “no direct thermostat required by this source recipe” from “unknown desired temperature”. Preserve the source and reviewed variants separately. A consumer assigning HVAC to an originally unconditioned cavity must make that changed experimental condition explicit. This is a schema/assignment decision requiring an ADR and migration, not a deletion of evidence or an automatic 20/26 °C substitution.

**Your response / decision:**
Inactive conditioning almost certainly means no cooling applied. We can treat even this zone as unconditioned if heating is also not applied. I believe there should be some flag to say a zone is not conditioned / or represent it as the zone has a sufficiently low/high heating/cooling setpoint.
For the commercial programs, it is almost certain that the attics, elevator cores ... other spaces ... are not conditioned.

**Agent follow-up — 2026-10-11 (accepted direction):** use an explicit conditioning state, distinguishing neither service, heating only, cooling only and both. This avoids artificial extreme temperatures. A missing cooling control does not disable known heating. The 43 missing-both-control cases above can resolve to no active conditioning under your support-space assumption and the existing reviewed evidence; retain that interpretation in metadata. System selection remains independent of program temperature preferences. Do not infer conditioning absence for unrelated occupied programs merely from a missing reference.

## People heat

**Fields:** `controls.people_radiant_fraction`, `controls.people_sensible_fraction`.

EnergyPlus 25.1.0 supports blank People fields defaulting to **0.3 radiant fraction of sensible heat** and **autocalculate sensible fraction**. The latter calculates a sensible/latent split rather than setting it to zero. An OpenStudio importer may have its own required-field handling; the historical SDK IDD inspected in this repository marks radiant fraction required. “Omit from our JSON” therefore needs an importer policy, not a promise that every consumer can leave every field blank.

The current exporter hardcodes both raw operands to null; “never supplied” does not establish that the sources lack values. The pinned commercial helper explicitly sets radiant fraction to 0.3. ResStock explicitly supplies **sensible fraction 3716/6600 ≈ 0.5630303** and sets its People radiant field to **0.558 × that fraction ≈ 0.3141709**. Preserve that assignment exactly if reproducing the source; the People radiant field is defined relative to sensible heat, so it must not be casually reinterpreted as a fraction of total metabolic heat. See [Standards.People.rb, lines 62–72](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/lib/openstudio-standards/standards/Standards.People.rb#L62-L72) and [InternalGains.apply_building_occupants](https://github.com/NatLabRockies/resstock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/HPXMLtoOpenStudio/resources/internal_gains.rb#L23-L67).

**Proposal:** make these supported thermal parameters optional, retain source overrides, and allow documented engine defaults where the selected source recipe delegates them. Move redundant default-only fields out of ordinary program records if desired, but keep the engine/version and resolved value visible in import diagnostics. For residential records, extract the available source rules before dropping fields. The current 0.3/autocalculate atlas fallback is not a faithful replacement for the pinned residential translator.

**Your response / decision:**
ok. fall back to engine default is a good idea, as you have suggested

**Agent follow-up — 2026-10-11 (accepted):** source values take precedence, including the residential assignments above. Otherwise the ready DTO/import contract supplies **0.3 radiant** and the explicit **engine autocalculate** sensible mode. Autocalculate is a complete executable instruction, not an unresolved null; the user need not choose a fallback at import time. Pin the engine policy and encode supported modes in the migrated schema.

## Equipment heat

**Fields:** electric and gas equipment `heat_fractions.latent`, `radiant`, `lost`, `visible`, `return_air`. All five “same as above” questions require object-specific treatment.

For EnergyPlus 25.1.0 `ElectricEquipment` and `GasEquipment`, latent, radiant and lost are supported inputs with defaults of zero. **Visible and return-air fractions are not fields of these objects.** Their appearance as universally missing attributes comes from our uniform five-fraction DTO, not five unresolved source inputs. `OtherEquipment`, used by the residential translator for fuel appliances, also needs its own fuel-aware mapping.

The commercial helper conditionally sets latent/radiant/lost when supplied and otherwise leaves those definition fields at SDK defaults. That can justify an explicit recipe/engine default for a newly constructed definition; it does not prove how an arbitrary pre-existing model object was configured. See [Standards.SpaceType.rb, lines 220–306](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/lib/openstudio-standards/standards/Standards.SpaceType.rb#L220-L306).

ResStock does **not** generally omit these fractions and let EnergyPlus choose zero. Its plug-load translator sets radiant to 0.6 × sensible outside the ASHRAE-140 branch, latent to the specified/defaulted latent share, and lost to 1 − sensible − latent. Appliance routines similarly calculate heat splits, then explicitly assign them through `Model.add_electric_equipment` / `add_other_equipment`. Those methods are outside our schedule-only execution. For example, the residual-MEL rule supplies sensible 0.855, latent 0.045 and lost 0.10; translation yields radiant 0.513. These are a rule illustration, not newly extracted magnitudes for the 41 fixtures. See [misc_loads.rb, lines 87–106](https://github.com/NatLabRockies/resstock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/HPXMLtoOpenStudio/resources/misc_loads.rb#L87-L106), [defaults.rb, get_residual_mels_values](https://github.com/NatLabRockies/resstock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/HPXMLtoOpenStudio/resources/defaults.rb#L7460-L7485), and [hotwater_appliances.rb](https://github.com/NatLabRockies/resstock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/HPXMLtoOpenStudio/resources/hotwater_appliances.rb#L50-L135).

**Proposal:** remove visible/return-air from these object-specific input shapes. Keep supported latent/radiant/lost as optional overrides, preserving every known value. Recover residential splits from the selected pinned defaults/translation branches. Permit engine defaults only through an explicit importer policy when the recipe actually delegates the field. Missing is not evidence that heat partition is unimportant: lost changes zone gains, latent changes moisture loads, and radiant changes the timing/location of sensible gains. No sensitivity simulation was run here, so negligible impact has not been established.

Mixtures need another distinction: their canonical aggregate carries component trajectories and an evaluation method, not scalar heat-fraction fields. The raw exporter reads only scalar fractions, so some apparent missing aggregate fractions are available in the constituents. Export/evaluate those source components rather than declaring them unknown or independently averaging fractions. The defaulted exporter already expands mixture leaves; its representation differs from the raw aggregate path. See [program_composition.py](../../scripts/program_composition.py) and [program_json.py](../../scripts/program_json.py).

**Your response / decision:**
mixing should be weighted average based on actual annual power per zone

**Agent follow-up — 2026-10-11 (accepted, calculation clarified):** use annual **energy**, equivalently annual mean power over the same calendar, to weight heat fractions. First resolve the actual source power and schedule, mixture weights and area/unit basis. For component power `P_i(t)`, calculate `E_i = sum(P_i(t) * dt)` and `f_mix = sum(E_i * f_i) / sum(E_i)`. Integrate `P_i(t) * f_i(t)` if a fraction varies with time. Omit a zero-energy demand rather than divide by zero. These are source-model energy weights, not measured utility consumption.

Construct the combined equipment schedule by summing **hourly power**: `P_mix(t) = sum(P_i(t))`, then export a design power and normalized schedule that reconstruct that sum. Directly weighting peak-normalized schedules by annual energy can change the total energy. For example, two 1 kW loads running for one and three overlapping hours consume 4 kWh; their combined 2 kW schedule is `[1, 0.5, 0.5]`. Applying their 25%/75% annual-energy weights to their original schedules instead would yield `[1, 0.75, 0.75]` and 5 kWh at that design power. Heat fractions of 0.2 and 0.6 correctly combine to 0.5. A constant combined fraction preserves annual heat partition but can approximate the hourly partition; retain the components in audit metadata. Keep calendar and design-day profiles separate and preserve source rule precedence.

## Lighting heat

**Fields:** lighting `heat_fractions.latent`, `lost`, `radiant`, `visible`, `return_air`.

These cannot all inherit the equipment answer. EnergyPlus `Lights` supports radiant, visible and return-air shares, each defaulting to zero in the inspected engine. It has no corresponding latent/lost input fields. The commercial tables supply meaningful lighting shares, often nonzero, and the helper applies them. Residential `Model.add_lights` explicitly sets **radiant 0.6, visible 0.2 and return-air 0.0** for interior/garage lighting. Exterior lighting uses a separate object without indoor heat fractions. See [model.rb, lines 236–248](https://github.com/NatLabRockies/resstock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/HPXMLtoOpenStudio/resources/model.rb#L236-L248) and [commercial lighting assignments](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/lib/openstudio-standards/standards/Standards.SpaceType.rb#L131-L202).

**Proposal:** remove latent/lost from the native Lights input shape; preserve radiant/visible/return-air when reported or deterministically supplied by the source translator. Allow a documented engine fallback only where justified. The earlier claim about needing a compatible return path is corrected in the follow-up below. For an abstract heat-balance representation, unsupported native inputs would need a separately named, explicitly defined model rather than being presented as missing EnergyPlus parameters.

**Your response / decision:**
use documented engine fallback wherever needed.
why " The return-air share needs a compatible return path when instantiated; its interaction with system assignment remains a consumer constraint. " ? - i do not understand the challenge here.

**Agent follow-up — 2026-10-11 (accepted and corrected):** there is no additional missing input for you to resolve here. EnergyPlus sends this share into the **zone air** when there is no zone return system or no return airflow. For example, 100 W of lights with a 0.2 return-air fraction supplies 20 W to return air when available, otherwise that heat goes into the zone air. Keep known source fractions and use the documented zero defaults for missing supported Lights fractions. The engine handles the routing. My earlier wording overstated the constraint. See the [pinned EnergyPlus 25.1 Lights documentation](https://github.com/NatLabRockies/EnergyPlus/blob/68a4a7c7744c380886913a92e061aba3d4a3fc54/doc/input-output-reference/src/overview/group-internal-gains-people-lights-other.tex#L907).

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
If additional lighting is not there, we believe we can say that is zero
Attic, mech, elevator cores ... if lighting/equipment load is not there, probably there is no lighting or equipment.
Support/attic/... spaces without occupancy seem feasible to me.

**Agent follow-up — 2026-10-11 (accepted):** missing additional lighting resolves to zero. Missing lighting/equipment in the identified attic, plenum, mechanical/electrical and elevator-core recipes resolves to absence; missing support-space occupancy resolves to zero. Apply these assumptions to missing operands only, then rebuild every affected mixture from the resolved leaves. Preserve positive source loads and distinguish assumed absence from source-reported zero. A zero load needs no active demand or invented schedule. These choices address the repeated downstream mixture gaps as well as the annotated leaf fields.

One commercial exception remains outside that pattern: **DOE Ref 1980-2004 Hospital / ER_Triage electric-equipment magnitude**. It is an occupied clinical program, not a cavity or elevator core. Recover its source recipe before proposing a substitute; this comment does not authorize an ER-specific zero assumption. Residential magnitudes also still require translation of the source rules, not a blanket zero. These are implementation/recovery work still to do; the current JSON has not become complete merely because the policy is clearer.

## Gas presence

**Fields:** gas equipment `schedule_id`, `value`; connected fuel-classification gaps under [residential channels](#residential-channels).

The raw placeholder does not establish gas consumption. `build_programs` makes a gas-equipment channel for every commercial leaf; 713/768 have neither density nor schedule. The clean standards helper only creates gas equipment for a nonzero density. Existing reviewed resolutions already supply explicit zero density/schedule for those 713 recipe cases. The remaining 55 source leaves have gas magnitude and schedule data. This is not an all-electric-building classification: gas heating, water heating and separately added/custom equipment remain distinct.

The full-library missing gas-reference count of 902 is those 713 source leaves plus 189 source-view mixtures whose magnitude/schedule cannot be aggregated through unknown constituents. It does not demonstrate additional gas uses in 902 independent programs. Reviewed absence and constituent preservation should resolve the recipe semantics before considering any fallback.

**Proposal:** instantiate gas demands only when the chosen recipe supports them; retain absence status/evidence rather than a missing gas object with an invented schedule. Preserve uncertainty for models whose complete recipe has not been inspected. Apply the existing reviewed absence variant when that is the intended experiment. Separately fix residential fuel mapping: some cooking/drying demands consume fuel, and the current name-based classification hides that issue. Do not use “gas schedule absent” alone as either evidence of gas demand or evidence of zero building gas use.

**Your response / decision:**
If no gas equipment is resolved via the means in the proposal, fall back to no gas equipment

**Agent follow-up — 2026-10-11 (accepted):** recover reported and fuel-aware appliance components first; if no gas equipment is resolved, export explicit absence automatically. Apply the same policy through mixtures. This is the program's appliance/equipment channel and does not disable gas heating or water heating assigned elsewhere.

## Water inlet

**Field:** `hot_water.inlet_temperature_schedule_id`, including shared-service demand entries.

This is not 700 independent missing source observations: the exporter always calls its inlet schedule function with `None`, so every exported water entry lacks the operand. Water mains/inlet temperature belongs primarily to weather/site/system context. The pinned residential translator derives daily inlet temperatures from weather and distribution/heat-recovery context, then assigns the resulting mains schedule. It is not universally 10 °C. See [hotwater_appliances.rb, lines 330–358](https://github.com/NatLabRockies/resstock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/HPXMLtoOpenStudio/resources/hotwater_appliances.rb#L330-L358).

**Proposal following your suggestion:** bind a shared weather-derived mains schedule at model/service level, with an explicit user-supplied alternative when needed. A climate-zone label alone is too coarse to reproduce a daily temperature trajectory. EnergyPlus `Site:WaterMainsTemperature` supports a schedule or weather-file correlation; `WaterUse:Equipment` can inherit that context when its cold-water supply schedule is omitted. Validate the resulting binding and temperature ordering, rather than silently dropping inlet context and hoping the engine chooses the intended climate. Retain any source-specific inlet or heat-recovery override at the relevant service boundary. Keep the existing 10 °C experimental fallback separately selectable until policy migration.

**Your response / decision:**
water mains temperature should be figured out during simulation time, using the Craig Christensen and Jay Burch method supported in EnergyPlus, as as function of outdoor temperature, ... (all could be obtained from the weather file).

**Agent follow-up — 2026-10-11 (accepted and verified):** declare EnergyPlus `Site:WaterMainsTemperature` with **CorrelationFromWeatherFile** and the simulation EPW. The Christensen/Burch method uses annual average outdoor temperature, the range of monthly average outdoor temperatures and day of year to calculate the seasonal mains curve. The consumer can obtain these from the weather file without a manual program-specific temperature input. This replaces the fixed 10 °C fallback in the ready-export policy. Retain source-specific downstream heat-recovery/distribution treatment where applicable. See the [weather-file correlation input](https://github.com/NatLabRockies/EnergyPlus/blob/68a4a7c7744c380886913a92e061aba3d4a3fc54/doc/input-output-reference/src/overview/group-location-climate-weather-file-access.tex#L1740) and [Christensen/Burch engineering description](https://github.com/NatLabRockies/EnergyPlus/blob/68a4a7c7744c380886913a92e061aba3d4a3fc54/doc/engineering-reference/src/simulation-models-encyclopedic-reference-005/water-systems.tex#L12).

## Water demands

**Fields:** hot-water `schedule_id`, `value`, `target_temperature_schedule_id`. They share residential pipeline gaps but have different causes.

The eleven missing local schedules are **eight washer-water plus three fixture-water profiles** in dwelling definitions; their exact absence/vacancy resolutions are described under load coverage. Their missing magnitudes are all 82 residential water demands, independently of whether a shape exists. Existing commercial local/shared demand magnitudes and flow schedules are available in the emitted entries; omitted commercial allocations are a separate problem.

All 82 residential target temperatures are unresolved because the adapter does not translate water demand temperatures. The other **26** missing occurrences in the combined 108 total are **composed local commercial demands**, not unknown shared-service targets: ten Outpatient, ten LargeHotel and six SmallHotel aggregate entries. Every constituent retains a known **60 °C** target. The aggregation/raw-export path drops that scalar even though the evidence is present; the defaulted path instead expands the leaves. This is recoverable representation loss, not a new temperature assumption. See [program_composition.py](../../scripts/program_composition.py), [program_json.py](../../scripts/program_json.py) and the investigation evidence's `commercial_water_target_aggregation`.

In the residential translator, mixed fixture water uses **105 °F = 40.555556 °C**, while appliance water can leave target unset to inherit the served hot-water context. That is different from a water-heater storage setpoint. See [fixture mixing and target assignments](https://github.com/NatLabRockies/resstock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/HPXMLtoOpenStudio/resources/hotwater_appliances.rb#L330-L418) and [Model.add_water_use_equipment](https://github.com/NatLabRockies/resstock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/HPXMLtoOpenStudio/resources/model.rb#L150-L164).

**Proposal:** consume the existing shape resolutions, derive peak flow with the correct volume/time normalization, and distinguish fixture delivery target from heater/system supply temperature. Recover composed commercial demands from their source components; preserve the known common target here, and keep separate trajectories if component targets differ in future variants. Treat residential appliance inheritance as an explicit service binding where the source does so. EnergyPlus's blank water target inherits hot supply; blank hot supply itself inherits cold supply, so omission without a valid served hot-water context can eliminate the intended heating demand. A universal 60 °C target is not source recovery.

**Your response / decision:**
OK. if all such resolution fails, we may still fall back to the 60 degC default which is fine.

**Agent follow-up — 2026-10-11 (accepted):** preserve recovered targets, including 40.555556 °C mixed fixture water and the common 60 °C commercial component targets. Resolve appliance inheritance through its served hot-water context. If these methods still leave a target unresolved, apply **60 °C** automatically with an assumption record. This fallback is a target-temperature choice; peak flow still needs its source volume/time calculation.

## Residential channels

**Fields:** omitted `ceiling_fan`, `dishwasher`, `hot_water_dishwasher`, `lighting_garage`; cooking-range and clothes-dryer fuel classifications. These are related to the same extraction boundary, but fuel and host allocation require additional care.

The canonical definition adapter selects a fixed channel list. It drops annual profiles that do exist for dishwasher and washer-independent dishwasher water (26 fixtures each), ceiling fans (26) and garage lighting (14). Frozen resolutions also supply refrigeration, freezer and exterior-lighting variants or absence states; these are missed by the adapter too. Recovering an omitted schedule does not establish its magnitude or the physical host of garage/exterior/shared loads.

The DTO currently labels all residential cooking/drying as electric equipment. Seventeen fixtures select gas/propane cooking and seven select gas/propane drying. The pinned residential translator can create **both electrical and fuel demands for the same appliance**, using explicit fuel type on `OtherEquipment`. A simple switch from electric to gas would still lose the electrical component and propane distinction. See [dryer translation](https://github.com/NatLabRockies/resstock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/HPXMLtoOpenStudio/resources/hotwater_appliances.rb#L114-L136) and [cooking translation](https://github.com/NatLabRockies/resstock/blob/dd25369f41a83a0767aefeeac0b6f8a0b0edd649/resources/hpxml-measures/HPXMLtoOpenStudio/resources/hotwater_appliances.rb#L278-L326).

**Proposal:** enumerate selected, included end uses from the resolved source inventory, not a short hardcoded list; preserve absent/excluded/unknown status. Represent fuel and potentially separate energy components explicitly, with stable demand identities and shared appliance schedule provenance. Preserve declared schedule-release exclusions. Discuss garage/exterior/common-area hosting and fuel-aware DTO shape before implementation; do not merge these into a generic missing-electric-equipment default.

**Your response / decision:**
Good catch regarding the fuel.
But remember we would like to agg all elec equipment to elec equipment schedule, and all gas appliances to gas equipment schedule eventually (after your discussion / fuel aware mapping).

**Agent follow-up — 2026-10-11 (accepted direction):** first recover each appliance's electrical and fuel components, then aggregate electrical equipment into one power trajectory per program/host using the method under equipment heat. Aggregate fuel equipment similarly while retaining its actual fuel identity. Natural gas and propane cannot be silently relabelled as the same fuel; a gas-equipment group can carry separate fuel components where necessary. Appliance water stays in the water channel and garage/exterior loads retain their host until assigned. Components with different physical hosts or scaling bases must be bound to a common host/basis before forming one simulation object. The audit metadata can retain component detail while the executable view stays compact.

## Schedule coverage

**Later unannotated field:** incomplete `schedules[].rules` coverage.

The audit found five distinct incomplete referenced rulesets affecting 18 program definitions: 12 LargeOffice and six MediumOffice. A missing schedule reference, a deliberately absent load and a present-but-partial ruleset are different cases. Our current default policy prepends a low-priority fallback while preserving source rule order; that produces an explicit experimental completion, not proof that the source supplied a complete ruleset.

**Proposal:** retain source/reviewed rule variants, rule dates, selectors, design days and source order. Inspect uncovered selectors/dates before choosing a fallback, and count only schedules attached to applicable demands/controls. Keep this item open for the next discussion: a load-absence resolution cannot repair a partially covered active schedule. The evidence date/calendar of an annual realization remains fixed; importing into a different simulation year needs an explicit calendar policy.

**Your response / decision:**
Inspect and report and discuss. it is impossible to respond to what you have presented here due to lack of further info.

**Agent follow-up — 2026-10-11 (investigated; proposed completions):** ordinary weekdays and weekends are covered. The exact gaps are four missing **holiday selectors** and one missing **February 29**. Counts below include source and reviewed definitions; Medium Office equipment and lights occur in the same definitions, so the rows overlap. There are **18 unique affected definitions**.

| Schedule (ID suffix) | Affected definitions | Actual gap | Proposed completion |
| --- | --- | --- | --- |
| `DataCenter_EQUIP_SCH` (`202c9398290fc3e56f8f`) | 12 LargeOffice: two data-center types, 90.1-2007/2013/2019, source/reviewed | February 29 for all ten selectors; February ends on 02-28 | Extend February rules through 02-29: normal weekdays/weekends/holidays **0.5**, winter design **0.25**, summer design **1.0** |
| `OfficeMedium BLDG_EQUIP_SCH_2004` (`24cc945309d37fb31db6`) | 2 MediumOffice, 90.1-2007, source/reviewed | Holiday selector throughout year | Copy its Sunday profile: **0.30** all day |
| `OfficeMedium BLDG_EQUIP_SCH_2013` (`4082e09c5f9727640add`) | 4 MediumOffice, 90.1-2013/2019, source/reviewed | Holiday selector throughout year | Copy its Sunday profile: **0.2307553806** hours 00:00–06:00 and 18:00–24:00; **0.288107175** hours 06:00–18:00 |
| `OfficeMedium BLDG_LIGHT_SCH_2013` (`4f028eec18f19916e7d2`) | Same 4 MediumOffice; ordinary and additional lights | Holiday selector throughout year | Copy its Sunday profile: **0.05** hours 00:00–06:00 and 18:00–24:00; **0.04311628** hours 06:00–18:00 |
| `OfficeMedium BLDG_LIGHT_SCH_2004` (`994cd1f711d51f30a4f0`) | Same 2 MediumOffice; ordinary and additional lights | Holiday selector throughout year | Copy its Sunday profile: **0.05** all day |

These values are dimensionless load fractions. Each ID above has the full prefix `schedule-`. The data-center schedule already covers a non-leap year; the additional day matters when realizing it in a leap year. The proposed holiday profiles preserve each source's low-occupancy background load. Which dates are holidays still comes from the simulation calendar; this proposal supplies the profile when a date is designated a holiday.

The pinned [standards schedule helper](https://github.com/NatLabRockies/openstudio-standards/blob/c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/lib/openstudio-standards/standards/Standards.Model.rb#L2767-L2892) does not supply a holiday-to-Sunday rule. None of these tables supplies a Default row. The helper treats design days as global special-day profiles; the canonical rules retain their source dates. Therefore the Sunday and leap-day completions are explicit atlas assumptions, not recovered hidden source values. The current atlas zero fallback would instead remove background load in the missing intervals.

The investigation script constructs these changes **in memory only**, verifies complete coverage for all date/day selectors, and confirms unchanged values for every previously covered date/selector. It does not change the frozen schedules. I propose **holiday = the same schedule's Sunday profile**, and **February 29 = the same schedule's February profile**, retaining all other values and rule ordering.

**Your follow-up on these two completions:**

<!-- Accept or revise the holiday-to-Sunday and February-29-to-February proposals here. -->

## Air requirements

**Distinct later fields:** omitted commercial ventilation per area/per person/ACH, infiltration rate/basis, and residential natural infiltration/outdoor air.

The DTO omits known outdoor-air terms: 700/768 per-area, 520/768 per-person and 39/768 ACH values exist upstream. Their different presence rates do not define interchangeable substitutes. Commercial infiltration rate/basis remain unresolved in this selection. Residential ACH50 is pressure-test evidence, not natural infiltration or mechanical outdoor-air demand.

**Proposed discussion:** put program outdoor-air requirements in the program/assignment interface while retaining calculation method and simultaneous terms; put envelope leakage and the weather/geometry-dependent conversion in the enclosure/model interface. Inspect helper combination rules before treating a null term as zero or taking a maximum/sum. This is a separate physical/schema decision, not covered by the heat-fraction omission suggestion.

**Your response / decision:**
Agree to not include them for now.

**Agent follow-up — 2026-10-11 (accepted):** exclude these air requirements from this program-completion migration. Retain canonical evidence for later use. Describe the exported scope accordingly; program completeness does not assert that infiltration or ventilation is zero in the assembled building model.

## Water allocation

**Distinct later field:** omitted program/service allocation.

There are 279 unresolved distinct commercial source-program allocations, concentrated in supermarkets, hotels, hospitals and schools. They are separate from 206 source-proved no-modeled-program-draw cases. A whole-building/shared service can be known while the beneficiary distribution or fixture zone is not. Mains temperature and flow-schedule completion do not solve this allocation.

**Proposed discussion:** retain each physical service once; bind an explicit consumer host and independently document any reporting allocation. Do not clone the full building demand into every referenced program or use an unsupported floor-area allocation as a physical fixture location. Decide which allocation/host inputs the zoning experiment must supply.

**Your response / decision:**
Agree to not include them for now and for the future if it is not related to energy use.

**Agent follow-up — 2026-10-11 (accepted scope, energy distinction):** omit beneficiary/reporting allocation where it only labels who consumed the hot water. Retain each physical shared-service demand once because its volume, temperatures and schedule determine water-heating energy. Do not drop an unresolved shared demand or duplicate it across every beneficiary program. If fixture location determines modeled zone sensible/latent gains, that physical host can affect energy and must remain part of model assembly; it is different from a reporting percentage. The 279 unresolved allocations are not authorization to erase the associated physical demand.

## Context

**Distinct later fields:** dedicated `source.climate` and `source.vintage` context.

These residential descriptors exist upstream but lack dedicated DTO fields. They are not unknown physical operands and should not receive numerical defaults. Vintage describes the selected stock fixture; it must remain distinguishable from a commercial code/prototype template. Climate context is also different from the actual EPW/station proxy used for the schedule realization.

**Proposed discussion:** expose these as optional source-context descriptors, retaining weather realization provenance separately. Decide whether self-contained exports must include them or may resolve them through a pinned definition manifest. Avoid duplicating climate-independent program rows to manufacture coverage.

**Your response / decision:**
Do include vintage and climate if possible; if the program spec is shared across CZ and / or vintage, mark them this way.

**Agent follow-up — 2026-10-11 (accepted):** include vintage and climate applicability in descriptive metadata. Represent a known value, a documented shared range/set, and unknown applicability distinctly. Do not interpret missing climate as “all climates,” or identical numeric values as proof of shared applicability. Preserve residential stock vintage versus commercial code/prototype template, and distinguish applicability from the weather file used for a particular realization.

## Composition

**Distinct later field:** recipe members and weights for 378 mixtures.

The DTO exports weighted demand trajectories but does not carry a dedicated mixture recipe. Selecting corrected source/reviewed leaves affects mixtures; one cannot default an unknown aggregate to zero without potentially erasing known contributions. The recipe exists in the pinned canonical definitions.

**Proposed discussion:** retain a pinned recipe reference or explicit member IDs/weights, including the selected evidence view and scaling basis. Decide whether an exported DTO is an executable snapshot only or must also support reconstruction/editing of its program mix. This is independent of optional EnergyPlus object fields.

**Your response / decision:**
We should not have any unknowns for now after this round of remap/
Exported DTO should be complete and ready for simulation without the need to specifically specify defaults / to bridge gaps

**Agent follow-up — 2026-10-11 (accepted target):** the ready DTO must contain every active program operand and embedded schedule, or an executable engine instruction such as sensible autocalculation or weather-derived mains temperature. Apply the accepted defaults during resolution/export; do not require the user to choose them or query another atlas manifest during import. Rebuild mixtures after leaf resolution and retain their recipe in metadata. Inactive/unsupported fields need no fabricated value. Geometry, simulation weather/calendar and assigned HVAC remain ordinary model context, not missing program defaults. Raw evidence can retain nulls. This is the acceptance criterion for the migration, **not a claim that the current exporter already meets it**. Source recovery, the ER_Triage exception and the schedule choices above remain outstanding work.

## Provenance

**Later fields:** `source.evidence[].original_value`, `source_file_id`, and omitted operand-to-evidence/source descriptors.

The full-library audit reports 3,285 null original-value evidence entries and 2,155 null source-file IDs. A retained source null and generated resolution evidence are not missing physical values to default. Generated evidence can legitimately have no raw-file ID while needing a traceable frozen resolution/helper reference. These counts repeat evidence across exports and are not counts of lost source files.

**Proposal:** preserve original nulls and distinguish raw-source evidence, deterministic derivations, reviewed resolutions and experimental assumptions. Provide operand links plus pinned source or generated-artifact descriptors if exports must be self-contained; otherwise require a pinned manifest binding. Never fill source metadata with invented originals or file IDs. This is a distinct export/provenance design discussion even though several physical gaps above arise from extraction omissions.

**Your response / decision:**
ok - but i feel provenance should be decorative/comment style fields

**Agent follow-up — 2026-10-11 (accepted):** treat provenance as simulation-ignored metadata, separate from executable fields. JSON has no native comments, so use a descriptive metadata object that a simulation importer can ignore. All required physical operands must already be resolved without traversing provenance links. The atlas build still validates provenance and retains original values/units, source locators, transformations, dates and assumption records; decorative to the consumer does not mean discarded from the research record.

## Proposed order of work

1. Resolve the two specific schedule-completion choices above. The other accepted choices are recorded in ADR 0016 and do not need another round of approval.
2. Recover residential magnitudes, heat splits, fuel components and frozen schedule resolutions; investigate the single Hospital ER_Triage equipment magnitude outside the support-space pattern. Preserve immutable original source execution and distinguish reviewed assumptions.
3. Implement the typed ready-DTO contract, automatic default-policy revision, explicit conditioning state, weather-derived mains instruction and descriptive metadata. Apply resolved leaf values before aggregating hourly demand and annual-energy-weighted heat fractions. Preserve physical shared services and fuel/host distinctions.
4. Validate the Medium Office pilot, residential examples and mixture energy conservation before regenerating a release. Verify schema, physical, referential, schedule, provenance and reproducibility checks. This investigation makes no release-completeness or full-simulation claim.

## Engine and reproduction evidence

The engine field/default observations were read directly from **EnergyPlus 25.1.0** `Energy+.idd` bundled with the repository's SHA-256-locked OpenStudio 3.10.0 runtime. Relevant object locators are `People` (line 21431), `Lights` (22339), `ElectricEquipment` (22442), `GasEquipment` (22509), `Site:WaterMainsTemperature` (2366) and `WaterUse:Equipment` (93731). [Official versioned IDD source](https://github.com/NatLabRockies/EnergyPlus/blob/v25.1.0/idd/Energy%2B.idd.in). The inspected bundled bytes and archive checksum are recorded in the investigation evidence; defaults are version-specific, not an assertion about all engines or SDKs. Historical OpenStudio required-field behavior is pinned separately in [source-default-lock.json](source-default-lock.json).

All inspected ResStock methods use revision `dd25369f41a83a0767aefeeac0b6f8a0b0edd649`; commercial helpers use standards revision `c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907`. The reproduction script compares each inspected upstream file directly to its checksum-locked source/runtime archive. Counts read frozen canonical releases; source locators, original units/values, transformations and interpretation remain in frozen evidence and in the method references above. Formulas and numbers in these responses are source-rule examples, not newly inserted program values.

```powershell
.venv/Scripts/python.exe -m scripts.program_field_investigation
.venv/Scripts/python.exe -m scripts.program_field_investigation --check
.venv/Scripts/python.exe -m scripts.program_json_field_review --check
```

Locked local archives are prerequisites for reproducing source inspection; no upstream code or EnergyPlus simulation is executed by the investigation script. Your original per-field annotation blocks remain the decision record; the group response areas here can hold follow-up discussion.

The follow-up also retrieves official EnergyPlus 25.1 documentation at revision `68a4a7c7744c380886913a92e061aba3d4a3fc54`, with SHA-256, byte length and the upstream license pinned in [program-json-followup-source-lock.json](program-json-followup-source-lock.json). The script verifies these bytes, reports the five exact coverage gaps and evaluates the proposed repairs without modifying source schedules. This source inspection is not a full engine run.
