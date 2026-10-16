# Construction JSON field review

Updated: 2026-10-12. Reviewed objects: 3798.

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
| `existing_assumptions` | 4 | 0 | 0 | 0 | 4 |
| `layers` | 3615 | 3574 | 41 | 0 | 0 |
| `materials.roughness` | 5478 | 5313 | 0 | 0 | 165 |
| `materials.solar_absorptance` | 5478 | 5312 | 0 | 0 | 166 |
| `materials.thermal_absorptance` | 5478 | 5312 | 0 | 0 | 166 |
| `materials.visible_absorptance` | 5478 | 5312 | 0 | 0 | 166 |
| `parameters.c_W_m2_K` | 172 | 113 | 59 | 0 | 0 |
| `parameters.shgc` | 504 | 398 | 0 | 0 | 106 |
| `parameters.u_W_m2_K` | 2984 | 2166 | 0 | 0 | 818 |
| `parameters.visible_transmittance` | 504 | 248 | 0 | 0 | 256 |
| `required_bindings.construction_selection_by_climate_and_role` | 183 | 0 | 0 | 183 | 0 |
| `required_bindings.exposed_perimeter` | 415 | 0 | 0 | 415 | 0 |
| `required_bindings.geometry` | 105 | 0 | 0 | 105 | 0 |
| `required_bindings.ground_boundary` | 41 | 0 | 0 | 41 | 0 |
| `required_bindings.ground_boundary_condition` | 66 | 0 | 0 | 66 | 0 |
| `required_bindings.pressure_to_natural_infiltration_model` | 41 | 0 | 0 | 41 | 0 |
| `required_bindings.surface_area` | 415 | 0 | 0 | 415 | 0 |
| `required_bindings.wall_height` | 113 | 0 | 0 | 113 | 0 |
| `required_bindings.weather` | 41 | 0 | 0 | 41 | 0 |
| `unresolved.assembly_layers_and_thermal_mass` | 41 | 0 | 41 | 0 | 0 |
| `unresolved.geometry_dependent_enclosure_translation` | 41 | 0 | 41 | 0 | 0 |
| `unresolved.ground_factor_target` | 59 | 0 | 59 | 0 | 0 |

## `existing_assumptions`

**Pattern:** GroundContactFloor (1); GroundContactWall (1); InteriorFloor (1); InteriorWall (1).

**Proposal / resolution:** Retain the four existing internal/ground-contact generic assumptions and their policy scope; no new default is introduced. Review applicability before using them.

**Representative IDs:** `construction-01ca09773f42690a68caf31c`, `construction-63dc564e76ebf4b7dacbbd6e`, `construction-67150f1251dcaabb839b7669`.

**User comments / decision:**

<!-- annotation:existing_assumptions:begin -->
<!-- Write here. -->
<!-- annotation:existing_assumptions:end -->

## `layers`

**Pattern:** dwelling_enclosure (41).

**Proposal / resolution:** Recover ordered source layers and thermal mass. Twelve selector-only glazing collisions are resolved in the recovery sidecar; 41 residential enclosure translations remain blocked.

**Representative IDs:** `construction-0079ce7b163bdb1bd0154dbe`, `construction-0258b60b93c78f9469d64925`, `construction-03fe19ed8968e605f4be3b8d`.

**User comments / decision:**

<!-- annotation:layers:begin -->
<!-- Write here. -->
<!-- annotation:layers:end -->

## `materials.roughness`

**Pattern:** MasslessOpaqueMaterial (165).

**Proposal / resolution:** Require this property only for applicable material models. 166 material instances have source/runtime defaults recovered with raw null retained: solar/visible nil.to_f setters produce zero; rejected thermal zero retains SDK 0.9; massless roughness retains SDK Smooth. No fabricated mass is added.

**Representative IDs:** `material-031210ef042c3f727d0de2b7`, `material-04b345016a3e15015bc02a87`, `material-0593ae384c754404071be0e0`.

**User comments / decision:**

<!-- annotation:materials.roughness:begin -->
<!-- Write here. -->
<!-- annotation:materials.roughness:end -->

## `materials.solar_absorptance`

**Pattern:** MasslessOpaqueMaterial (165); StandardOpaqueMaterial (1).

**Proposal / resolution:** Require this property only for applicable material models. 166 material instances have source/runtime defaults recovered with raw null retained: solar/visible nil.to_f setters produce zero; rejected thermal zero retains SDK 0.9; massless roughness retains SDK Smooth. No fabricated mass is added.

**Representative IDs:** `material-0130b92838f24c32c1fd60bf`, `material-031210ef042c3f727d0de2b7`, `material-04b345016a3e15015bc02a87`.

**User comments / decision:**

<!-- annotation:materials.solar_absorptance:begin -->
<!-- Write here. -->
<!-- annotation:materials.solar_absorptance:end -->

## `materials.thermal_absorptance`

**Pattern:** MasslessOpaqueMaterial (165); StandardOpaqueMaterial (1).

**Proposal / resolution:** Require this property only for applicable material models. 166 material instances have source/runtime defaults recovered with raw null retained: solar/visible nil.to_f setters produce zero; rejected thermal zero retains SDK 0.9; massless roughness retains SDK Smooth. No fabricated mass is added.

**Representative IDs:** `material-0130b92838f24c32c1fd60bf`, `material-031210ef042c3f727d0de2b7`, `material-04b345016a3e15015bc02a87`.

**User comments / decision:**

<!-- annotation:materials.thermal_absorptance:begin -->
<!-- Write here. -->
<!-- annotation:materials.thermal_absorptance:end -->

## `materials.visible_absorptance`

**Pattern:** MasslessOpaqueMaterial (165); StandardOpaqueMaterial (1).

**Proposal / resolution:** Require this property only for applicable material models. 166 material instances have source/runtime defaults recovered with raw null retained: solar/visible nil.to_f setters produce zero; rejected thermal zero retains SDK 0.9; massless roughness retains SDK Smooth. No fabricated mass is added.

**Representative IDs:** `material-0130b92838f24c32c1fd60bf`, `material-031210ef042c3f727d0de2b7`, `material-04b345016a3e15015bc02a87`.

**User comments / decision:**

<!-- annotation:materials.visible_absorptance:begin -->
<!-- Write here. -->
<!-- annotation:materials.visible_absorptance:end -->

## `parameters.c_W_m2_K`

**Pattern:** GroundContactFloor (59).

**Proposal / resolution:** Use the applicable source material/assembly model. Glazing source-code VT defaults stay labeled; opaque U can be calculated from layers with an explicit film convention. F/C models retain geometry operands; do not fill inapplicable optical fields.

**Representative IDs:** `construction-04342b2df6149dd313e7524a`, `construction-06fab6c2dc26737437db87f5`, `construction-07aad1f5b1e80da795af944f`.

**User comments / decision:**

<!-- annotation:parameters.c_W_m2_K:begin -->
<!-- Write here. -->
<!-- annotation:parameters.c_W_m2_K:end -->

## `parameters.shgc`

**Pattern:** ExteriorWindow (106).

**Proposal / resolution:** Use the applicable source material/assembly model. Glazing source-code VT defaults stay labeled; opaque U can be calculated from layers with an explicit film convention. F/C models retain geometry operands; do not fill inapplicable optical fields.

**Representative IDs:** `construction-007045ab01839a6e2ddf6c26`, `construction-0362ae44b7800d8d561865e7`, `construction-049909dbebac32a5f2ffdb9a`.

**User comments / decision:**

<!-- annotation:parameters.shgc:begin -->
<!-- Write here. -->
<!-- annotation:parameters.shgc:end -->

## `parameters.u_W_m2_K`

**Pattern:** InteriorFloor (184); InteriorWall (174); InteriorCeiling (173); ExteriorFloor (123); ExteriorRoof (103); ExteriorWall (59); GroundContactFloor (1); GroundContactWall (1).

**Proposal / resolution:** Use the applicable source material/assembly model. Glazing source-code VT defaults stay labeled; opaque U can be calculated from layers with an explicit film convention. F/C models retain geometry operands; do not fill inapplicable optical fields.

**Representative IDs:** `construction-0013de16ce6061d7959e17f7`, `construction-00d33179df394b7b19f0f777`, `construction-013da9bd9b3224701f9e7119`.

**User comments / decision:**

<!-- annotation:parameters.u_W_m2_K:begin -->
<!-- Write here. -->
<!-- annotation:parameters.u_W_m2_K:end -->

## `parameters.visible_transmittance`

**Pattern:** ExteriorWindow (256).

**Proposal / resolution:** Use the applicable source material/assembly model. Glazing source-code VT defaults stay labeled; opaque U can be calculated from layers with an explicit film convention. F/C models retain geometry operands; do not fill inapplicable optical fields.

**Representative IDs:** `construction-000e46cac36d6a13fbb89790`, `construction-005688c873aa18a9116ef2bb`, `construction-007045ab01839a6e2ddf6c26`.

**User comments / decision:**

<!-- annotation:parameters.visible_transmittance:begin -->
<!-- Write here. -->
<!-- annotation:parameters.visible_transmittance:end -->

## `required_bindings.construction_selection_by_climate_and_role`

**Pattern:** package (183).

**Proposal / resolution:** Retain an explicit consumer operand; no Atlas value is substituted. Bind it when assigning this independent object to a simulation.

**Representative IDs:** `construction-00c8834aecb7e1a79a3cbfef`, `construction-063d3de715308138dedc942e`, `construction-065e2be2332c15d04a224fe3`.

**User comments / decision:**

<!-- annotation:required_bindings.construction_selection_by_climate_and_role:begin -->
<!-- Write here. -->
<!-- annotation:required_bindings.construction_selection_by_climate_and_role:end -->

## `required_bindings.exposed_perimeter`

**Pattern:** GroundContactFloor (414); GroundContactWall (1).

**Proposal / resolution:** Retain an explicit consumer operand; no Atlas value is substituted. Bind it when assigning this independent object to a simulation.

**Representative IDs:** `construction-006e2c9de2739c72d4992d72`, `construction-00f278d5f2d9f41d4f964177`, `construction-01ca09773f42690a68caf31c`.

**User comments / decision:**

<!-- annotation:required_bindings.exposed_perimeter:begin -->
<!-- Write here. -->
<!-- annotation:required_bindings.exposed_perimeter:end -->

## `required_bindings.geometry`

**Pattern:** GroundContactWall (64); dwelling_enclosure (41).

**Proposal / resolution:** Retain an explicit consumer operand; no Atlas value is substituted. Bind it when assigning this independent object to a simulation.

**Representative IDs:** `construction-0079ce7b163bdb1bd0154dbe`, `construction-0258b60b93c78f9469d64925`, `construction-034ff44ff59637b0bdfb17c1`.

**User comments / decision:**

<!-- annotation:required_bindings.geometry:begin -->
<!-- Write here. -->
<!-- annotation:required_bindings.geometry:end -->

## `required_bindings.ground_boundary`

**Pattern:** dwelling_enclosure (41).

**Proposal / resolution:** Retain an explicit consumer operand; no Atlas value is substituted. Bind it when assigning this independent object to a simulation.

**Representative IDs:** `construction-0079ce7b163bdb1bd0154dbe`, `construction-0258b60b93c78f9469d64925`, `construction-03fe19ed8968e605f4be3b8d`.

**User comments / decision:**

<!-- annotation:required_bindings.ground_boundary:begin -->
<!-- Write here. -->
<!-- annotation:required_bindings.ground_boundary:end -->

## `required_bindings.ground_boundary_condition`

**Pattern:** GroundContactWall (65); GroundContactFloor (1).

**Proposal / resolution:** Retain an explicit consumer operand; no Atlas value is substituted. Bind it when assigning this independent object to a simulation.

**Representative IDs:** `construction-01ca09773f42690a68caf31c`, `construction-034ff44ff59637b0bdfb17c1`, `construction-056ec910baf3b65dae5545f8`.

**User comments / decision:**

<!-- annotation:required_bindings.ground_boundary_condition:begin -->
<!-- Write here. -->
<!-- annotation:required_bindings.ground_boundary_condition:end -->

## `required_bindings.pressure_to_natural_infiltration_model`

**Pattern:** dwelling_enclosure (41).

**Proposal / resolution:** Retain an explicit consumer operand; no Atlas value is substituted. Bind it when assigning this independent object to a simulation.

**Representative IDs:** `construction-0079ce7b163bdb1bd0154dbe`, `construction-0258b60b93c78f9469d64925`, `construction-03fe19ed8968e605f4be3b8d`.

**User comments / decision:**

<!-- annotation:required_bindings.pressure_to_natural_infiltration_model:begin -->
<!-- Write here. -->
<!-- annotation:required_bindings.pressure_to_natural_infiltration_model:end -->

## `required_bindings.surface_area`

**Pattern:** GroundContactFloor (414); GroundContactWall (1).

**Proposal / resolution:** Retain an explicit consumer operand; no Atlas value is substituted. Bind it when assigning this independent object to a simulation.

**Representative IDs:** `construction-006e2c9de2739c72d4992d72`, `construction-00f278d5f2d9f41d4f964177`, `construction-01ca09773f42690a68caf31c`.

**User comments / decision:**

<!-- annotation:required_bindings.surface_area:begin -->
<!-- Write here. -->
<!-- annotation:required_bindings.surface_area:end -->

## `required_bindings.wall_height`

**Pattern:** GroundContactWall (113).

**Proposal / resolution:** Retain an explicit consumer operand; no Atlas value is substituted. Bind it when assigning this independent object to a simulation.

**Representative IDs:** `construction-066c6dc86200d265432da748`, `construction-0f57fe62ed6e7b327fc8e8b3`, `construction-108ab495bc6abef879bab72e`.

**User comments / decision:**

<!-- annotation:required_bindings.wall_height:begin -->
<!-- Write here. -->
<!-- annotation:required_bindings.wall_height:end -->

## `required_bindings.weather`

**Pattern:** dwelling_enclosure (41).

**Proposal / resolution:** Retain an explicit consumer operand; no Atlas value is substituted. Bind it when assigning this independent object to a simulation.

**Representative IDs:** `construction-0079ce7b163bdb1bd0154dbe`, `construction-0258b60b93c78f9469d64925`, `construction-03fe19ed8968e605f4be3b8d`.

**User comments / decision:**

<!-- annotation:required_bindings.weather:begin -->
<!-- Write here. -->
<!-- annotation:required_bindings.weather:end -->

## `unresolved.assembly_layers_and_thermal_mass`

**Pattern:** dwelling_enclosure (41).

**Proposal / resolution:** Keep blocked until the pinned source calculation/recipe and its operands are recovered. No new physical fallback is approved.

**Representative IDs:** `construction-0079ce7b163bdb1bd0154dbe`, `construction-0258b60b93c78f9469d64925`, `construction-03fe19ed8968e605f4be3b8d`.

**User comments / decision:**

<!-- annotation:unresolved.assembly_layers_and_thermal_mass:begin -->
<!-- Write here. -->
<!-- annotation:unresolved.assembly_layers_and_thermal_mass:end -->

## `unresolved.geometry_dependent_enclosure_translation`

**Pattern:** dwelling_enclosure (41).

**Proposal / resolution:** Keep blocked until the pinned source calculation/recipe and its operands are recovered. No new physical fallback is approved.

**Representative IDs:** `construction-0079ce7b163bdb1bd0154dbe`, `construction-0258b60b93c78f9469d64925`, `construction-03fe19ed8968e605f4be3b8d`.

**User comments / decision:**

<!-- annotation:unresolved.geometry_dependent_enclosure_translation:begin -->
<!-- Write here. -->
<!-- annotation:unresolved.geometry_dependent_enclosure_translation:end -->

## `unresolved.ground_factor_target`

**Pattern:** GroundContactFloor (59).

**Proposal / resolution:** Keep blocked until the pinned source calculation/recipe and its operands are recovered. No new physical fallback is approved.

**Representative IDs:** `construction-04342b2df6149dd313e7524a`, `construction-06fab6c2dc26737437db87f5`, `construction-07aad1f5b1e80da795af944f`.

**User comments / decision:**

<!-- annotation:unresolved.ground_factor_target:begin -->
<!-- Write here. -->
<!-- annotation:unresolved.ground_factor_target:end -->
