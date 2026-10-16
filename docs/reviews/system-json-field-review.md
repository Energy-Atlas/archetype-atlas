# HVAC and hot-water system JSON field review

Updated: 2026-10-12. Reviewed objects: 1242.

One entry per field/property across applicable records. Counts are field occurrences;
the JSON census retains every affected ID. Model-inapplicable properties are excluded.
Unprefixed definition fields describe the frozen baseline; `recovered.*` fields describe
the new source sidecars. They are separate populations, not additive gap counts.
Source recovery inputs remain separate from published program JSON and frozen definitions.
A recovered recipe is not proof that an engine model is ready. No new Atlas physical defaults are applied.

**Scope:** source-defined defaults and prior approved assumptions only. Unresolved physics
blocks readiness; geometry, sizing and assignment are explicit consumer inputs.

**Evidence:** [coverage census](energy-json-field-coverage.json),
[work record](json-completion-work-record.md), and
[source-recovery decisions](../adr/0017-independent-energy-source-recovery.md).

| Field | Applicable | Known | Unresolved | Consumer input | Recoverable / reviewed policy |
| --- | ---: | ---: | ---: | ---: | ---: |
| `components.ancillary_equipment.efficiency_or_cop` | 140 | 0 | 140 | 0 | 0 |
| `components.ancillary_equipment.heating_fuel` | 140 | 0 | 140 | 0 | 0 |
| `components.ancillary_equipment.ventilation_strategy` | 140 | 0 | 140 | 0 | 0 |
| `components.ancillary_equipment.zone_terminal_type` | 140 | 0 | 140 | 0 | 0 |
| `components.cooling.capacity` | 30 | 0 | 0 | 30 | 0 |
| `components.cooling.cop` | 30 | 0 | 30 | 0 | 0 |
| `components.cooling.efficiency_or_cop` | 794 | 0 | 794 | 0 | 0 |
| `components.cooling.rated_capacity` | 794 | 0 | 0 | 794 | 0 |
| `components.curve_assignment` | 726 | 0 | 726 | 0 | 0 |
| `components.fan.efficiency` | 869 | 0 | 869 | 0 | 0 |
| `components.fan.pressure_rise` | 869 | 0 | 869 | 0 | 0 |
| `components.heat_pump.capacity` | 4 | 0 | 0 | 4 | 0 |
| `components.heat_pump.cop` | 4 | 0 | 4 | 0 | 0 |
| `components.heating.capacity` | 36 | 0 | 0 | 36 | 0 |
| `components.heating.cop` | 36 | 0 | 36 | 0 | 0 |
| `components.heating.efficiency_or_cop` | 911 | 0 | 911 | 0 | 0 |
| `components.heating.rated_capacity` | 911 | 0 | 0 | 911 | 0 |
| `components.required_inputs.applicable_rating_conditions` | 707 | 0 | 707 | 0 | 0 |
| `components.required_inputs.controls` | 70 | 0 | 70 | 0 | 0 |
| `components.required_inputs.curves` | 70 | 0 | 70 | 0 | 0 |
| `components.required_inputs.fan_performance` | 70 | 0 | 70 | 0 | 0 |
| `components.required_inputs.rating_capacity_W` | 707 | 0 | 0 | 707 | 0 |
| `components.required_inputs.serving_assignment` | 140 | 0 | 140 | 0 | 0 |
| `components.required_inputs.source_equipment_subtype` | 707 | 0 | 707 | 0 | 0 |
| `parameters.efficiency_or_cop` | 1005 | 0 | 0 | 0 | 1005 |
| `parameters.heating_fuel` | 1046 | 41 | 1005 | 0 | 0 |
| `parameters.ventilation_strategy` | 1005 | 0 | 1005 | 0 | 0 |
| `parameters.zone_terminal_type` | 1005 | 0 | 1005 | 0 | 0 |
| `recovered.cooling.cooling_capacity` | 30 | 0 | 0 | 30 | 0 |
| `recovered.cooling.location` | 30 | 0 | 0 | 30 | 0 |
| `recovered.heat_pump.cooling_capacity` | 4 | 0 | 0 | 4 | 0 |
| `recovered.heat_pump.heating_capacity` | 4 | 0 | 0 | 4 | 0 |
| `recovered.heat_pump.location` | 4 | 0 | 0 | 4 | 0 |
| `recovered.heating.heating_capacity` | 42 | 0 | 0 | 42 | 0 |
| `recovered.heating.location` | 42 | 0 | 0 | 42 | 0 |
| `recovered.water_heater.heating_capacity` | 41 | 39 | 0 | 2 | 0 |
| `required_bindings.consumer_sizing` | 1200 | 0 | 0 | 1200 | 0 |
| `required_bindings.loss_host` | 196 | 0 | 0 | 196 | 0 |
| `required_bindings.serving_assignment` | 1046 | 0 | 0 | 1046 | 0 |
| `required_bindings.sizing.heating_capacity` | 2 | 0 | 0 | 2 | 0 |
| `required_bindings.water_demand_assignment` | 196 | 0 | 0 | 196 | 0 |
| `required_bindings.water_mains_temperature` | 196 | 0 | 0 | 196 | 0 |
| `unresolved.controls_and_curves` | 993 | 0 | 993 | 0 | 0 |
| `unresolved.distribution_and_control_translation` | 41 | 0 | 41 | 0 | 0 |
| `unresolved.engine_controls_and_performance_translation` | 42 | 0 | 42 | 0 | 0 |
| `unresolved.factory_performance_and_template_adjustments` | 12 | 0 | 12 | 0 | 0 |
| `unresolved.heater_efficiency_and_loss_model` | 154 | 0 | 154 | 0 | 0 |
| `unresolved.performance_assignment` | 993 | 0 | 993 | 0 | 0 |
| `unresolved.performance_curve_assignment` | 12 | 0 | 12 | 0 | 0 |
| `unresolved.performance_curves_and_fan_defaults` | 41 | 0 | 41 | 0 | 0 |
| `unresolved.source_component_recipe` | 993 | 0 | 993 | 0 | 0 |
| `unresolved.source_factory_template_adjustments` | 154 | 0 | 154 | 0 | 0 |

## `components.ancillary_equipment.efficiency_or_cop`

**Pattern:** ancillary_equipment (140).

**Proposal / resolution:** Sizing is a consumer operand. Recover efficiency, fan performance, curves and controls from exact source helpers/rating conditions; no common fallback performance is approved.

**Representative IDs:** `hvac_system-014e214988a4d0e3e2c767f1`, `hvac_system-03873cbb01117253138f95c0`, `hvac_system-04d31b0cf0bafcfada097235`.

**User comments / decision:**

<!-- annotation:components.ancillary_equipment.efficiency_or_cop:begin -->
<!-- Write here. -->
<!-- annotation:components.ancillary_equipment.efficiency_or_cop:end -->

## `components.ancillary_equipment.heating_fuel`

**Pattern:** ancillary_equipment (140).

**Proposal / resolution:** Sizing is a consumer operand. Recover efficiency, fan performance, curves and controls from exact source helpers/rating conditions; no common fallback performance is approved.

**Representative IDs:** `hvac_system-014e214988a4d0e3e2c767f1`, `hvac_system-03873cbb01117253138f95c0`, `hvac_system-04d31b0cf0bafcfada097235`.

**User comments / decision:**

<!-- annotation:components.ancillary_equipment.heating_fuel:begin -->
<!-- Write here. -->
<!-- annotation:components.ancillary_equipment.heating_fuel:end -->

## `components.ancillary_equipment.ventilation_strategy`

**Pattern:** ancillary_equipment (140).

**Proposal / resolution:** Sizing is a consumer operand. Recover efficiency, fan performance, curves and controls from exact source helpers/rating conditions; no common fallback performance is approved.

**Representative IDs:** `hvac_system-014e214988a4d0e3e2c767f1`, `hvac_system-03873cbb01117253138f95c0`, `hvac_system-04d31b0cf0bafcfada097235`.

**User comments / decision:**

<!-- annotation:components.ancillary_equipment.ventilation_strategy:begin -->
<!-- Write here. -->
<!-- annotation:components.ancillary_equipment.ventilation_strategy:end -->

## `components.ancillary_equipment.zone_terminal_type`

**Pattern:** ancillary_equipment (140).

**Proposal / resolution:** Sizing is a consumer operand. Recover efficiency, fan performance, curves and controls from exact source helpers/rating conditions; no common fallback performance is approved.

**Representative IDs:** `hvac_system-014e214988a4d0e3e2c767f1`, `hvac_system-03873cbb01117253138f95c0`, `hvac_system-04d31b0cf0bafcfada097235`.

**User comments / decision:**

<!-- annotation:components.ancillary_equipment.zone_terminal_type:begin -->
<!-- Write here. -->
<!-- annotation:components.ancillary_equipment.zone_terminal_type:end -->

## `components.cooling.capacity`

**Pattern:** cooling (30).

**Proposal / resolution:** Sizing is a consumer operand. Recover efficiency, fan performance, curves and controls from exact source helpers/rating conditions; no common fallback performance is approved.

**Representative IDs:** `residential-component-1a883967f36d27bd51c01c15`, `residential-component-2ed29a11975e12d40815b911`, `residential-component-2fa338816300f7d9632a891b`.

**User comments / decision:**

<!-- annotation:components.cooling.capacity:begin -->
<!-- Write here. -->
<!-- annotation:components.cooling.capacity:end -->

## `components.cooling.cop`

**Pattern:** cooling (30).

**Proposal / resolution:** Sizing is a consumer operand. Recover efficiency, fan performance, curves and controls from exact source helpers/rating conditions; no common fallback performance is approved.

**Representative IDs:** `residential-component-1a883967f36d27bd51c01c15`, `residential-component-2ed29a11975e12d40815b911`, `residential-component-2fa338816300f7d9632a891b`.

**User comments / decision:**

<!-- annotation:components.cooling.cop:begin -->
<!-- Write here. -->
<!-- annotation:components.cooling.cop:end -->

## `components.cooling.efficiency_or_cop`

**Pattern:** cooling (794).

**Proposal / resolution:** Sizing is a consumer operand. Recover efficiency, fan performance, curves and controls from exact source helpers/rating conditions; no common fallback performance is approved.

**Representative IDs:** `component-0008a7465a30113dfb2a0876`, `component-004d83aedf57eb429e681e7f`, `component-0169313117de899ea5fa3d00`.

**User comments / decision:**

<!-- annotation:components.cooling.efficiency_or_cop:begin -->
<!-- Write here. -->
<!-- annotation:components.cooling.efficiency_or_cop:end -->

## `components.cooling.rated_capacity`

**Pattern:** cooling (794).

**Proposal / resolution:** Sizing is a consumer operand. Recover efficiency, fan performance, curves and controls from exact source helpers/rating conditions; no common fallback performance is approved.

**Representative IDs:** `component-0008a7465a30113dfb2a0876`, `component-004d83aedf57eb429e681e7f`, `component-0169313117de899ea5fa3d00`.

**User comments / decision:**

<!-- annotation:components.cooling.rated_capacity:begin -->
<!-- Write here. -->
<!-- annotation:components.cooling.rated_capacity:end -->

## `components.curve_assignment`

**Pattern:** performance_curve (726).

**Proposal / resolution:** 726 source curves are available but unassigned. Recover exact component association and independent-variable domains; similarity of names is insufficient.

**Representative IDs:** `curve-003c7404c05d2789307c436a`, `curve-004f2bcc835dc65b83d9ac21`, `curve-00bef6e36efc484712a29762`.

**User comments / decision:**

<!-- annotation:components.curve_assignment:begin -->
<!-- Write here. -->
<!-- annotation:components.curve_assignment:end -->

## `components.fan.efficiency`

**Pattern:** fan (869).

**Proposal / resolution:** Sizing is a consumer operand. Recover efficiency, fan performance, curves and controls from exact source helpers/rating conditions; no common fallback performance is approved.

**Representative IDs:** `component-002e9b8bc4cced2ae34c565a`, `component-0057b6f24f2783da8018a253`, `component-00a738081b675eb8dfc5adc9`.

**User comments / decision:**

<!-- annotation:components.fan.efficiency:begin -->
<!-- Write here. -->
<!-- annotation:components.fan.efficiency:end -->

## `components.fan.pressure_rise`

**Pattern:** fan (869).

**Proposal / resolution:** Sizing is a consumer operand. Recover efficiency, fan performance, curves and controls from exact source helpers/rating conditions; no common fallback performance is approved.

**Representative IDs:** `component-002e9b8bc4cced2ae34c565a`, `component-0057b6f24f2783da8018a253`, `component-00a738081b675eb8dfc5adc9`.

**User comments / decision:**

<!-- annotation:components.fan.pressure_rise:begin -->
<!-- Write here. -->
<!-- annotation:components.fan.pressure_rise:end -->

## `components.heat_pump.capacity`

**Pattern:** heat_pump (4).

**Proposal / resolution:** Sizing is a consumer operand. Recover efficiency, fan performance, curves and controls from exact source helpers/rating conditions; no common fallback performance is approved.

**Representative IDs:** `residential-component-38482fa9f37ddebd462e04de`, `residential-component-615c0d2e1b98482318e752a4`, `residential-component-9ba5ab455efa9b591774a6a2`.

**User comments / decision:**

<!-- annotation:components.heat_pump.capacity:begin -->
<!-- Write here. -->
<!-- annotation:components.heat_pump.capacity:end -->

## `components.heat_pump.cop`

**Pattern:** heat_pump (4).

**Proposal / resolution:** Sizing is a consumer operand. Recover efficiency, fan performance, curves and controls from exact source helpers/rating conditions; no common fallback performance is approved.

**Representative IDs:** `residential-component-38482fa9f37ddebd462e04de`, `residential-component-615c0d2e1b98482318e752a4`, `residential-component-9ba5ab455efa9b591774a6a2`.

**User comments / decision:**

<!-- annotation:components.heat_pump.cop:begin -->
<!-- Write here. -->
<!-- annotation:components.heat_pump.cop:end -->

## `components.heating.capacity`

**Pattern:** heating (36).

**Proposal / resolution:** Sizing is a consumer operand. Recover efficiency, fan performance, curves and controls from exact source helpers/rating conditions; no common fallback performance is approved.

**Representative IDs:** `residential-component-1b64b1a68d33ef7d6f7eb368`, `residential-component-1dac0cedd605aaf0f4bd2804`, `residential-component-229058d3bff4e7aa1d313128`.

**User comments / decision:**

<!-- annotation:components.heating.capacity:begin -->
<!-- Write here. -->
<!-- annotation:components.heating.capacity:end -->

## `components.heating.cop`

**Pattern:** heating (36).

**Proposal / resolution:** Sizing is a consumer operand. Recover efficiency, fan performance, curves and controls from exact source helpers/rating conditions; no common fallback performance is approved.

**Representative IDs:** `residential-component-1b64b1a68d33ef7d6f7eb368`, `residential-component-1dac0cedd605aaf0f4bd2804`, `residential-component-229058d3bff4e7aa1d313128`.

**User comments / decision:**

<!-- annotation:components.heating.cop:begin -->
<!-- Write here. -->
<!-- annotation:components.heating.cop:end -->

## `components.heating.efficiency_or_cop`

**Pattern:** heating (911).

**Proposal / resolution:** Sizing is a consumer operand. Recover efficiency, fan performance, curves and controls from exact source helpers/rating conditions; no common fallback performance is approved.

**Representative IDs:** `component-00b5e69b20e36f3c3a5f2407`, `component-01490993eb89b539f36f0a0d`, `component-014deb4fca0583dc0eeb60a4`.

**User comments / decision:**

<!-- annotation:components.heating.efficiency_or_cop:begin -->
<!-- Write here. -->
<!-- annotation:components.heating.efficiency_or_cop:end -->

## `components.heating.rated_capacity`

**Pattern:** heating (911).

**Proposal / resolution:** Sizing is a consumer operand. Recover efficiency, fan performance, curves and controls from exact source helpers/rating conditions; no common fallback performance is approved.

**Representative IDs:** `component-00b5e69b20e36f3c3a5f2407`, `component-01490993eb89b539f36f0a0d`, `component-014deb4fca0583dc0eeb60a4`.

**User comments / decision:**

<!-- annotation:components.heating.rated_capacity:begin -->
<!-- Write here. -->
<!-- annotation:components.heating.rated_capacity:end -->

## `components.required_inputs.applicable_rating_conditions`

**Pattern:** conditional_performance_rule (707).

**Proposal / resolution:** Preserve capacity-band/date predicates and original metrics. Capacity can come from sizing; source subtype, rating conditions and curve/control assignment require exact source evidence.

**Representative IDs:** `performance-rule-0003ecc48fc721ae1d71fd23`, `performance-rule-0087e57556fa781df176bb0f`, `performance-rule-015b93f6927941e788f182ee`.

**User comments / decision:**

<!-- annotation:components.required_inputs.applicable_rating_conditions:begin -->
<!-- Write here. -->
<!-- annotation:components.required_inputs.applicable_rating_conditions:end -->

## `components.required_inputs.controls`

**Pattern:** heating (36); cooling (30); heat_pump (4).

**Proposal / resolution:** Preserve capacity-band/date predicates and original metrics. Capacity can come from sizing; source subtype, rating conditions and curve/control assignment require exact source evidence.

**Representative IDs:** `residential-component-1a883967f36d27bd51c01c15`, `residential-component-1b64b1a68d33ef7d6f7eb368`, `residential-component-1dac0cedd605aaf0f4bd2804`.

**User comments / decision:**

<!-- annotation:components.required_inputs.controls:begin -->
<!-- Write here. -->
<!-- annotation:components.required_inputs.controls:end -->

## `components.required_inputs.curves`

**Pattern:** heating (36); cooling (30); heat_pump (4).

**Proposal / resolution:** Preserve capacity-band/date predicates and original metrics. Capacity can come from sizing; source subtype, rating conditions and curve/control assignment require exact source evidence.

**Representative IDs:** `residential-component-1a883967f36d27bd51c01c15`, `residential-component-1b64b1a68d33ef7d6f7eb368`, `residential-component-1dac0cedd605aaf0f4bd2804`.

**User comments / decision:**

<!-- annotation:components.required_inputs.curves:begin -->
<!-- Write here. -->
<!-- annotation:components.required_inputs.curves:end -->

## `components.required_inputs.fan_performance`

**Pattern:** heating (36); cooling (30); heat_pump (4).

**Proposal / resolution:** Preserve capacity-band/date predicates and original metrics. Capacity can come from sizing; source subtype, rating conditions and curve/control assignment require exact source evidence.

**Representative IDs:** `residential-component-1a883967f36d27bd51c01c15`, `residential-component-1b64b1a68d33ef7d6f7eb368`, `residential-component-1dac0cedd605aaf0f4bd2804`.

**User comments / decision:**

<!-- annotation:components.required_inputs.fan_performance:begin -->
<!-- Write here. -->
<!-- annotation:components.required_inputs.fan_performance:end -->

## `components.required_inputs.rating_capacity_W`

**Pattern:** conditional_performance_rule (707).

**Proposal / resolution:** Preserve capacity-band/date predicates and original metrics. Capacity can come from sizing; source subtype, rating conditions and curve/control assignment require exact source evidence.

**Representative IDs:** `performance-rule-0003ecc48fc721ae1d71fd23`, `performance-rule-0087e57556fa781df176bb0f`, `performance-rule-015b93f6927941e788f182ee`.

**User comments / decision:**

<!-- annotation:components.required_inputs.rating_capacity_W:begin -->
<!-- Write here. -->
<!-- annotation:components.required_inputs.rating_capacity_W:end -->

## `components.required_inputs.serving_assignment`

**Pattern:** ancillary_equipment (140).

**Proposal / resolution:** Preserve capacity-band/date predicates and original metrics. Capacity can come from sizing; source subtype, rating conditions and curve/control assignment require exact source evidence.

**Representative IDs:** `hvac_system-014e214988a4d0e3e2c767f1`, `hvac_system-03873cbb01117253138f95c0`, `hvac_system-04d31b0cf0bafcfada097235`.

**User comments / decision:**

<!-- annotation:components.required_inputs.serving_assignment:begin -->
<!-- Write here. -->
<!-- annotation:components.required_inputs.serving_assignment:end -->

## `components.required_inputs.source_equipment_subtype`

**Pattern:** conditional_performance_rule (707).

**Proposal / resolution:** Preserve capacity-band/date predicates and original metrics. Capacity can come from sizing; source subtype, rating conditions and curve/control assignment require exact source evidence.

**Representative IDs:** `performance-rule-0003ecc48fc721ae1d71fd23`, `performance-rule-0087e57556fa781df176bb0f`, `performance-rule-015b93f6927941e788f182ee`.

**User comments / decision:**

<!-- annotation:components.required_inputs.source_equipment_subtype:begin -->
<!-- Write here. -->
<!-- annotation:components.required_inputs.source_equipment_subtype:end -->

## `parameters.efficiency_or_cop`

**Pattern:** PSZ-AC (535); PTAC (199); UnitHeater (75); VAV (67); SAC (60); PVAV (42); DC (12); CAV (10); DOAS Cold Supply (5).

**Proposal / resolution:** Replace the ambiguous aggregate with component-level rating metrics and conditional predicates. Missing operating performance still blocks equipment; do not convert SEER/EER/AFUE into one system COP.

**Representative IDs:** `hvac_system-00059d9d621381fcae2235f3`, `hvac_system-006c38d902344f33d1963b78`, `hvac_system-0080a2434302d0c17ddaffc5`.

**User comments / decision:**

<!-- annotation:parameters.efficiency_or_cop:begin -->
<!-- Write here. -->
<!-- annotation:parameters.efficiency_or_cop:end -->

## `parameters.heating_fuel`

**Pattern:** PSZ-AC (535); PTAC (199); UnitHeater (75); VAV (67); SAC (60); PVAV (42); DC (12); CAV (10); DOAS Cold Supply (5).

**Proposal / resolution:** Recover exact source component/recipe semantics; descriptor categories alone do not specify fuel conversion, terminals or ventilation controls. Keep unresolved when no exact source binding is available.

**Representative IDs:** `hvac_system-00059d9d621381fcae2235f3`, `hvac_system-006c38d902344f33d1963b78`, `hvac_system-0080a2434302d0c17ddaffc5`.

**User comments / decision:**

<!-- annotation:parameters.heating_fuel:begin -->
<!-- Write here. -->
<!-- annotation:parameters.heating_fuel:end -->

## `parameters.ventilation_strategy`

**Pattern:** PSZ-AC (535); PTAC (199); UnitHeater (75); VAV (67); SAC (60); PVAV (42); DC (12); CAV (10); DOAS Cold Supply (5).

**Proposal / resolution:** Recover exact source component/recipe semantics; descriptor categories alone do not specify fuel conversion, terminals or ventilation controls. Keep unresolved when no exact source binding is available.

**Representative IDs:** `hvac_system-00059d9d621381fcae2235f3`, `hvac_system-006c38d902344f33d1963b78`, `hvac_system-0080a2434302d0c17ddaffc5`.

**User comments / decision:**

<!-- annotation:parameters.ventilation_strategy:begin -->
<!-- Write here. -->
<!-- annotation:parameters.ventilation_strategy:end -->

## `parameters.zone_terminal_type`

**Pattern:** PSZ-AC (535); PTAC (199); UnitHeater (75); VAV (67); SAC (60); PVAV (42); DC (12); CAV (10); DOAS Cold Supply (5).

**Proposal / resolution:** Recover exact source component/recipe semantics; descriptor categories alone do not specify fuel conversion, terminals or ventilation controls. Keep unresolved when no exact source binding is available.

**Representative IDs:** `hvac_system-00059d9d621381fcae2235f3`, `hvac_system-006c38d902344f33d1963b78`, `hvac_system-0080a2434302d0c17ddaffc5`.

**User comments / decision:**

<!-- annotation:parameters.zone_terminal_type:begin -->
<!-- Write here. -->
<!-- annotation:parameters.zone_terminal_type:end -->

## `recovered.cooling.cooling_capacity`

**Pattern:** cooling (30).

**Proposal / resolution:** Use the recovered SI source field with its exact metric and default provenance. Unknown capacities are sizing operands; active missing physical fields remain blocked. Alternative HPXML fields are not universally required.

**Representative IDs:** `recovered-equipment-c6560c8c676cd507bbe08ca2`, `recovered-equipment-6fbb3d038ad03c737dd0a2b7`, `recovered-equipment-1887a49eba547f8830c37087`.

**User comments / decision:**

<!-- annotation:recovered.cooling.cooling_capacity:begin -->
<!-- Write here. -->
<!-- annotation:recovered.cooling.cooling_capacity:end -->

## `recovered.cooling.location`

**Pattern:** cooling (30).

**Proposal / resolution:** Use the recovered SI source field with its exact metric and default provenance. Unknown capacities are sizing operands; active missing physical fields remain blocked. Alternative HPXML fields are not universally required.

**Representative IDs:** `recovered-equipment-c6560c8c676cd507bbe08ca2`, `recovered-equipment-6fbb3d038ad03c737dd0a2b7`, `recovered-equipment-1887a49eba547f8830c37087`.

**User comments / decision:**

<!-- annotation:recovered.cooling.location:begin -->
<!-- Write here. -->
<!-- annotation:recovered.cooling.location:end -->

## `recovered.heat_pump.cooling_capacity`

**Pattern:** heat_pump (4).

**Proposal / resolution:** Use the recovered SI source field with its exact metric and default provenance. Unknown capacities are sizing operands; active missing physical fields remain blocked. Alternative HPXML fields are not universally required.

**Representative IDs:** `recovered-equipment-3818c5b88755c94147453466`, `recovered-equipment-122b5a2390dd13d8bfaa2832`, `recovered-equipment-2f5b32513a80a8c3b842410b`.

**User comments / decision:**

<!-- annotation:recovered.heat_pump.cooling_capacity:begin -->
<!-- Write here. -->
<!-- annotation:recovered.heat_pump.cooling_capacity:end -->

## `recovered.heat_pump.heating_capacity`

**Pattern:** heat_pump (4).

**Proposal / resolution:** Use the recovered SI source field with its exact metric and default provenance. Unknown capacities are sizing operands; active missing physical fields remain blocked. Alternative HPXML fields are not universally required.

**Representative IDs:** `recovered-equipment-3818c5b88755c94147453466`, `recovered-equipment-122b5a2390dd13d8bfaa2832`, `recovered-equipment-2f5b32513a80a8c3b842410b`.

**User comments / decision:**

<!-- annotation:recovered.heat_pump.heating_capacity:begin -->
<!-- Write here. -->
<!-- annotation:recovered.heat_pump.heating_capacity:end -->

## `recovered.heat_pump.location`

**Pattern:** heat_pump (4).

**Proposal / resolution:** Use the recovered SI source field with its exact metric and default provenance. Unknown capacities are sizing operands; active missing physical fields remain blocked. Alternative HPXML fields are not universally required.

**Representative IDs:** `recovered-equipment-3818c5b88755c94147453466`, `recovered-equipment-122b5a2390dd13d8bfaa2832`, `recovered-equipment-2f5b32513a80a8c3b842410b`.

**User comments / decision:**

<!-- annotation:recovered.heat_pump.location:begin -->
<!-- Write here. -->
<!-- annotation:recovered.heat_pump.location:end -->

## `recovered.heating.heating_capacity`

**Pattern:** heating (42).

**Proposal / resolution:** Use the recovered SI source field with its exact metric and default provenance. Unknown capacities are sizing operands; active missing physical fields remain blocked. Alternative HPXML fields are not universally required.

**Representative IDs:** `recovered-equipment-f5b30a23472aa481da7422fb`, `recovered-equipment-a2bc122aa66656f4b99babf5`, `recovered-equipment-e1a874aa8a8d587a7300330d`.

**User comments / decision:**

<!-- annotation:recovered.heating.heating_capacity:begin -->
<!-- Write here. -->
<!-- annotation:recovered.heating.heating_capacity:end -->

## `recovered.heating.location`

**Pattern:** heating (42).

**Proposal / resolution:** Use the recovered SI source field with its exact metric and default provenance. Unknown capacities are sizing operands; active missing physical fields remain blocked. Alternative HPXML fields are not universally required.

**Representative IDs:** `recovered-equipment-f5b30a23472aa481da7422fb`, `recovered-equipment-a2bc122aa66656f4b99babf5`, `recovered-equipment-e1a874aa8a8d587a7300330d`.

**User comments / decision:**

<!-- annotation:recovered.heating.location:begin -->
<!-- Write here. -->
<!-- annotation:recovered.heating.location:end -->

## `recovered.water_heater.heating_capacity`

**Pattern:** water_heater (2).

**Proposal / resolution:** Use the recovered SI source field with its exact metric and default provenance. Unknown capacities are sizing operands; active missing physical fields remain blocked. Alternative HPXML fields are not universally required.

**Representative IDs:** `recovered-equipment-5e4c212ce5e8eb05495b8691`, `recovered-equipment-128847e9cffa5205102bec89`.

**User comments / decision:**

<!-- annotation:recovered.water_heater.heating_capacity:begin -->
<!-- Write here. -->
<!-- annotation:recovered.water_heater.heating_capacity:end -->

## `required_bindings.consumer_sizing`

**Pattern:** PSZ-AC (535); PTAC (199); UnitHeater (75); VAV (67); SAC (60); PVAV (42); Residential fixture equipment (41); Hospital (15); DC (12); LargeHotel (11); CAV (10); SuperTallBuilding (9); TallBuilding (9); FullServiceRestaurant (8); PrimarySchool (8); SecondarySchool (8); SmallHotel (8); College (5); Courthouse (5); DOAS Cold Supply (5); LargeOffice (5); LargeOfficeDetailed (5); MediumOffice (5); MediumOfficeDetailed (5); MidriseApartment (5); Outpatient (5); QuickServiceRestaurant (5); SmallOffice (5); SmallOfficeDetailed (5); SuperMarket (5); HighriseApartment (3); Laboratory (3); LargeOfficeDetail (3); RetailStandalone (3); RetailStripmall (3); Warehouse (3).

**Proposal / resolution:** Retain an explicit consumer operand; no Atlas value is substituted. Bind it when assigning this independent object to a simulation.

**Representative IDs:** `hvac_system-00059d9d621381fcae2235f3`, `hvac_system-006c38d902344f33d1963b78`, `hvac_system-0079ce7b163bdb1bd0154dbe`.

**User comments / decision:**

<!-- annotation:required_bindings.consumer_sizing:begin -->
<!-- Write here. -->
<!-- annotation:required_bindings.consumer_sizing:end -->

## `required_bindings.loss_host`

**Pattern:** Residential fixture equipment (42); Hospital (15); LargeHotel (11); SuperTallBuilding (9); TallBuilding (9); FullServiceRestaurant (8); PrimarySchool (8); SecondarySchool (8); SmallHotel (8); College (5); Courthouse (5); LargeOffice (5); LargeOfficeDetailed (5); MediumOffice (5); MediumOfficeDetailed (5); MidriseApartment (5); Outpatient (5); QuickServiceRestaurant (5); SmallOffice (5); SmallOfficeDetailed (5); SuperMarket (5); HighriseApartment (3); Laboratory (3); LargeOfficeDetail (3); RetailStandalone (3); RetailStripmall (3); Warehouse (3).

**Proposal / resolution:** Retain an explicit consumer operand; no Atlas value is substituted. Bind it when assigning this independent object to a simulation.

**Representative IDs:** `recovered-equipment-cc898ff4644341d63eb02de3`, `recovered-equipment-5e4c212ce5e8eb05495b8691`, `recovered-equipment-cad8c3b303354e662bc1d525`.

**User comments / decision:**

<!-- annotation:required_bindings.loss_host:begin -->
<!-- Write here. -->
<!-- annotation:required_bindings.loss_host:end -->

## `required_bindings.serving_assignment`

**Pattern:** PSZ-AC (535); PTAC (199); UnitHeater (75); VAV (67); SAC (60); PVAV (42); Residential fixture equipment (41); DC (12); CAV (10); DOAS Cold Supply (5).

**Proposal / resolution:** Retain an explicit consumer operand; no Atlas value is substituted. Bind it when assigning this independent object to a simulation.

**Representative IDs:** `hvac_system-00059d9d621381fcae2235f3`, `hvac_system-006c38d902344f33d1963b78`, `hvac_system-0079ce7b163bdb1bd0154dbe`.

**User comments / decision:**

<!-- annotation:required_bindings.serving_assignment:begin -->
<!-- Write here. -->
<!-- annotation:required_bindings.serving_assignment:end -->

## `required_bindings.sizing.heating_capacity`

**Pattern:** Residential fixture equipment (2).

**Proposal / resolution:** Retain an explicit consumer operand; no Atlas value is substituted. Bind it when assigning this independent object to a simulation.

**Representative IDs:** `recovered-equipment-5e4c212ce5e8eb05495b8691`, `recovered-equipment-128847e9cffa5205102bec89`.

**User comments / decision:**

<!-- annotation:required_bindings.sizing.heating_capacity:begin -->
<!-- Write here. -->
<!-- annotation:required_bindings.sizing.heating_capacity:end -->

## `required_bindings.water_demand_assignment`

**Pattern:** Residential fixture equipment (42); Hospital (15); LargeHotel (11); SuperTallBuilding (9); TallBuilding (9); FullServiceRestaurant (8); PrimarySchool (8); SecondarySchool (8); SmallHotel (8); College (5); Courthouse (5); LargeOffice (5); LargeOfficeDetailed (5); MediumOffice (5); MediumOfficeDetailed (5); MidriseApartment (5); Outpatient (5); QuickServiceRestaurant (5); SmallOffice (5); SmallOfficeDetailed (5); SuperMarket (5); HighriseApartment (3); Laboratory (3); LargeOfficeDetail (3); RetailStandalone (3); RetailStripmall (3); Warehouse (3).

**Proposal / resolution:** Retain an explicit consumer operand; no Atlas value is substituted. Bind it when assigning this independent object to a simulation.

**Representative IDs:** `recovered-equipment-cc898ff4644341d63eb02de3`, `recovered-equipment-5e4c212ce5e8eb05495b8691`, `recovered-equipment-cad8c3b303354e662bc1d525`.

**User comments / decision:**

<!-- annotation:required_bindings.water_demand_assignment:begin -->
<!-- Write here. -->
<!-- annotation:required_bindings.water_demand_assignment:end -->

## `required_bindings.water_mains_temperature`

**Pattern:** Residential fixture equipment (42); Hospital (15); LargeHotel (11); SuperTallBuilding (9); TallBuilding (9); FullServiceRestaurant (8); PrimarySchool (8); SecondarySchool (8); SmallHotel (8); College (5); Courthouse (5); LargeOffice (5); LargeOfficeDetailed (5); MediumOffice (5); MediumOfficeDetailed (5); MidriseApartment (5); Outpatient (5); QuickServiceRestaurant (5); SmallOffice (5); SmallOfficeDetailed (5); SuperMarket (5); HighriseApartment (3); Laboratory (3); LargeOfficeDetail (3); RetailStandalone (3); RetailStripmall (3); Warehouse (3).

**Proposal / resolution:** Retain an explicit consumer operand; no Atlas value is substituted. Bind it when assigning this independent object to a simulation.

**Representative IDs:** `recovered-equipment-cc898ff4644341d63eb02de3`, `recovered-equipment-5e4c212ce5e8eb05495b8691`, `recovered-equipment-cad8c3b303354e662bc1d525`.

**User comments / decision:**

<!-- annotation:required_bindings.water_mains_temperature:begin -->
<!-- Write here. -->
<!-- annotation:required_bindings.water_mains_temperature:end -->

## `unresolved.controls_and_curves`

**Pattern:** PSZ-AC (535); PTAC (199); UnitHeater (75); VAV (67); SAC (60); PVAV (30); DC (12); CAV (10); DOAS Cold Supply (5).

**Proposal / resolution:** Keep blocked until the pinned source calculation/recipe and its operands are recovered. No new physical fallback is approved.

**Representative IDs:** `hvac_system-00059d9d621381fcae2235f3`, `hvac_system-006c38d902344f33d1963b78`, `hvac_system-0080a2434302d0c17ddaffc5`.

**User comments / decision:**

<!-- annotation:unresolved.controls_and_curves:begin -->
<!-- Write here. -->
<!-- annotation:unresolved.controls_and_curves:end -->

## `unresolved.distribution_and_control_translation`

**Pattern:** Residential fixture equipment (41).

**Proposal / resolution:** Keep blocked until the pinned source calculation/recipe and its operands are recovered. No new physical fallback is approved.

**Representative IDs:** `hvac_system-0079ce7b163bdb1bd0154dbe`, `hvac_system-0258b60b93c78f9469d64925`, `hvac_system-03fe19ed8968e605f4be3b8d`.

**User comments / decision:**

<!-- annotation:unresolved.distribution_and_control_translation:begin -->
<!-- Write here. -->
<!-- annotation:unresolved.distribution_and_control_translation:end -->

## `unresolved.engine_controls_and_performance_translation`

**Pattern:** Residential fixture equipment (42).

**Proposal / resolution:** Keep blocked until the pinned source calculation/recipe and its operands are recovered. No new physical fallback is approved.

**Representative IDs:** `recovered-equipment-cc898ff4644341d63eb02de3`, `recovered-equipment-5e4c212ce5e8eb05495b8691`, `recovered-equipment-cad8c3b303354e662bc1d525`.

**User comments / decision:**

<!-- annotation:unresolved.engine_controls_and_performance_translation:begin -->
<!-- Write here. -->
<!-- annotation:unresolved.engine_controls_and_performance_translation:end -->

## `unresolved.factory_performance_and_template_adjustments`

**Pattern:** PVAV (12).

**Proposal / resolution:** Keep blocked until the pinned source calculation/recipe and its operands are recovered. No new physical fallback is approved.

**Representative IDs:** `hvac_system-391c926cf557a50df9f3d0f8`, `hvac_system-48bcd42ec2335b67017c82b6`, `hvac_system-6a6fb1756906319c2d4bbce6`.

**User comments / decision:**

<!-- annotation:unresolved.factory_performance_and_template_adjustments:begin -->
<!-- Write here. -->
<!-- annotation:unresolved.factory_performance_and_template_adjustments:end -->

## `unresolved.heater_efficiency_and_loss_model`

**Pattern:** Hospital (15); LargeHotel (11); SuperTallBuilding (9); TallBuilding (9); FullServiceRestaurant (8); PrimarySchool (8); SecondarySchool (8); SmallHotel (8); College (5); Courthouse (5); LargeOffice (5); LargeOfficeDetailed (5); MediumOffice (5); MediumOfficeDetailed (5); MidriseApartment (5); Outpatient (5); QuickServiceRestaurant (5); SmallOffice (5); SmallOfficeDetailed (5); SuperMarket (5); HighriseApartment (3); Laboratory (3); LargeOfficeDetail (3); RetailStandalone (3); RetailStripmall (3); Warehouse (3).

**Proposal / resolution:** Keep blocked until the pinned source calculation/recipe and its operands are recovered. No new physical fallback is approved.

**Representative IDs:** `source-water-heater-4099caa580bf7884f2a36f74`, `source-water-heater-60a46368282b5b9b93f87c0c`, `source-water-heater-fa8346401fa7a4c34f1995e6`.

**User comments / decision:**

<!-- annotation:unresolved.heater_efficiency_and_loss_model:begin -->
<!-- Write here. -->
<!-- annotation:unresolved.heater_efficiency_and_loss_model:end -->

## `unresolved.performance_assignment`

**Pattern:** PSZ-AC (535); PTAC (199); UnitHeater (75); VAV (67); SAC (60); PVAV (30); DC (12); CAV (10); DOAS Cold Supply (5).

**Proposal / resolution:** Keep blocked until the pinned source calculation/recipe and its operands are recovered. No new physical fallback is approved.

**Representative IDs:** `hvac_system-00059d9d621381fcae2235f3`, `hvac_system-006c38d902344f33d1963b78`, `hvac_system-0080a2434302d0c17ddaffc5`.

**User comments / decision:**

<!-- annotation:unresolved.performance_assignment:begin -->
<!-- Write here. -->
<!-- annotation:unresolved.performance_assignment:end -->

## `unresolved.performance_curve_assignment`

**Pattern:** PVAV (12).

**Proposal / resolution:** Keep blocked until the pinned source calculation/recipe and its operands are recovered. No new physical fallback is approved.

**Representative IDs:** `hvac_system-391c926cf557a50df9f3d0f8`, `hvac_system-48bcd42ec2335b67017c82b6`, `hvac_system-6a6fb1756906319c2d4bbce6`.

**User comments / decision:**

<!-- annotation:unresolved.performance_curve_assignment:begin -->
<!-- Write here. -->
<!-- annotation:unresolved.performance_curve_assignment:end -->

## `unresolved.performance_curves_and_fan_defaults`

**Pattern:** Residential fixture equipment (41).

**Proposal / resolution:** Keep blocked until the pinned source calculation/recipe and its operands are recovered. No new physical fallback is approved.

**Representative IDs:** `hvac_system-0079ce7b163bdb1bd0154dbe`, `hvac_system-0258b60b93c78f9469d64925`, `hvac_system-03fe19ed8968e605f4be3b8d`.

**User comments / decision:**

<!-- annotation:unresolved.performance_curves_and_fan_defaults:begin -->
<!-- Write here. -->
<!-- annotation:unresolved.performance_curves_and_fan_defaults:end -->

## `unresolved.source_component_recipe`

**Pattern:** PSZ-AC (535); PTAC (199); UnitHeater (75); VAV (67); SAC (60); PVAV (30); DC (12); CAV (10); DOAS Cold Supply (5).

**Proposal / resolution:** Keep blocked until the pinned source calculation/recipe and its operands are recovered. No new physical fallback is approved.

**Representative IDs:** `hvac_system-00059d9d621381fcae2235f3`, `hvac_system-006c38d902344f33d1963b78`, `hvac_system-0080a2434302d0c17ddaffc5`.

**User comments / decision:**

<!-- annotation:unresolved.source_component_recipe:begin -->
<!-- Write here. -->
<!-- annotation:unresolved.source_component_recipe:end -->

## `unresolved.source_factory_template_adjustments`

**Pattern:** Hospital (15); LargeHotel (11); SuperTallBuilding (9); TallBuilding (9); FullServiceRestaurant (8); PrimarySchool (8); SecondarySchool (8); SmallHotel (8); College (5); Courthouse (5); LargeOffice (5); LargeOfficeDetailed (5); MediumOffice (5); MediumOfficeDetailed (5); MidriseApartment (5); Outpatient (5); QuickServiceRestaurant (5); SmallOffice (5); SmallOfficeDetailed (5); SuperMarket (5); HighriseApartment (3); Laboratory (3); LargeOfficeDetail (3); RetailStandalone (3); RetailStripmall (3); Warehouse (3).

**Proposal / resolution:** Keep blocked until the pinned source calculation/recipe and its operands are recovered. No new physical fallback is approved.

**Representative IDs:** `source-water-heater-4099caa580bf7884f2a36f74`, `source-water-heater-60a46368282b5b9b93f87c0c`, `source-water-heater-fa8346401fa7a4c34f1995e6`.

**User comments / decision:**

<!-- annotation:unresolved.source_factory_template_adjustments:begin -->
<!-- Write here. -->
<!-- annotation:unresolved.source_factory_template_adjustments:end -->

## Prior annotation: `required_bindings.sizing.backup_heating_capacity`

This field is no longer an active gap; its annotation is retained.

<!-- annotation:required_bindings.sizing.backup_heating_capacity:begin -->
<!-- Write here. -->
<!-- annotation:required_bindings.sizing.backup_heating_capacity:end -->
