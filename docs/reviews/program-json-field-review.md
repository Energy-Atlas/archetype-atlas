# Program JSON field review

Audit date: 2026-10-09. Program JSON schema: **2.0.0**. Definitions: **v0.1.1**.

This working document has **one review entry per JSON field and load type**, aggregated across all program definitions. It contains no individual program-record entries. Each field has its own annotation area.

Coverage uses 1,900 validated raw exports, before the experimental program-default policy. Source records, reviewed variants and mixtures are counted separately; these are not population weights. Missing counts are field occurrences; affected-program counts deduplicate program IDs within that field.

Hot-water counts include local and shared-service loads. Shared references are not additional physical services. Only applicable fields enter a denominator; absent inapplicable properties are not treated as missing. Null means unknown/unreported, not zero. Passing the current schema does not establish complete program semantics.

Write in each **Your annotations / proposed approach** area and keep its markers intact. Regeneration preserves annotations and refuses to discard orphaned blocks. The stated defaults describe existing behavior; they are not new decisions.

```powershell
.venv/Scripts/python.exe -m scripts.program_json_field_review --refresh
.venv/Scripts/python.exe -m scripts.program_json_field_review --check
```

## Load and control fields with missing data

### Controls — `activity_schedule_id`

**JSON field:** `controls.activity_schedule_id`.

**Missing:** 185/1,900 applicable field occurrences; **affected programs:** 185.

**Pattern / shared program types:** 41/185 affected program definitions are whole dwellings. Residential schedule-only execution does not determine load magnitude. 60/185 affected definitions have attic, plenum, basement or data-center names; these names do not establish zero load or disabled conditioning.

**Affected building types:** SmallHotel (60); LargeOffice (22); SingleFamilyDetached (22); MidriseApartment (17); HighriseApartment (13); MediumOffice (10); FullServiceRestaurant (8); QuickServiceRestaurant (8); SmallOffice (8); MultiFamily5PlusLowRise (6); SingleFamilyAttached (5); ManufacturedHome (3); MultiFamily2To4 (3).

**Current handling:** Constant 120 W/person.

<!-- annotation:controls:activity_schedule_id:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:controls:activity_schedule_id:end -->

### Controls — `cooling_enabled`

**JSON field:** `controls.cooling_enabled`.

**Missing:** 1,857/1,900 applicable field occurrences; **affected programs:** 1,857.

**Pattern / shared program types:** Missing broadly across commercial programs and all dwellings; explicit disabled states exist only in selected reviewed support programs. 41/1857 affected program definitions are whole dwellings. Residential schedule-only execution does not determine load magnitude. 60/1857 affected definitions have attic, plenum, basement or data-center names; these names do not establish zero load or disabled conditioning.

**Affected building types:** Outpatient (369); Hospital (243); SmallHotel (240); LargeHotel (226); SuperMarket (150); SecondarySchool (145); PrimarySchool (123); RetailStandalone (64); MidriseApartment (49); RetailStripmall (40); Warehouse (40); HighriseApartment (31); LargeOffice (31); SingleFamilyDetached (22); FullServiceRestaurant (19); QuickServiceRestaurant (19); MediumOffice (15); SmallOffice (14); MultiFamily5PlusLowRise (6); SingleFamilyAttached (5); ManufacturedHome (3); MultiFamily2To4 (3).

**Current handling:** true when unknown; preserve known false.

<!-- annotation:controls:cooling_enabled:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:controls:cooling_enabled:end -->

### Controls — `cooling_setpoint_schedule_id`

**JSON field:** `controls.cooling_setpoint_schedule_id`.

**Missing:** 116/1,900 applicable field occurrences; **affected programs:** 116.

**Pattern / shared program types:** 48/116 affected definitions have attic, plenum, basement or data-center names; these names do not establish zero load or disabled conditioning.

**Affected building types:** SmallHotel (60); HighriseApartment (12); LargeOffice (10); MediumOffice (10); FullServiceRestaurant (8); QuickServiceRestaurant (8); SmallOffice (8).

**Current handling:** 26 degC nominal; if heating is known, use max(26, maximum heating + 2).

<!-- annotation:controls:cooling_setpoint_schedule_id:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:controls:cooling_setpoint_schedule_id:end -->

### Controls — `heating_enabled`

**JSON field:** `controls.heating_enabled`.

**Missing:** 1,857/1,900 applicable field occurrences; **affected programs:** 1,857.

**Pattern / shared program types:** Missing broadly across commercial programs and all dwellings; explicit disabled states exist only in selected reviewed support programs. 41/1857 affected program definitions are whole dwellings. Residential schedule-only execution does not determine load magnitude. 60/1857 affected definitions have attic, plenum, basement or data-center names; these names do not establish zero load or disabled conditioning.

**Affected building types:** Outpatient (369); Hospital (243); SmallHotel (240); LargeHotel (226); SuperMarket (150); SecondarySchool (145); PrimarySchool (123); RetailStandalone (64); MidriseApartment (49); RetailStripmall (40); Warehouse (40); HighriseApartment (31); LargeOffice (31); SingleFamilyDetached (22); FullServiceRestaurant (19); QuickServiceRestaurant (19); MediumOffice (15); SmallOffice (14); MultiFamily5PlusLowRise (6); SingleFamilyAttached (5); ManufacturedHome (3); MultiFamily2To4 (3).

**Current handling:** true when unknown; preserve known false.

<!-- annotation:controls:heating_enabled:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:controls:heating_enabled:end -->

### Controls — `heating_setpoint_schedule_id`

**JSON field:** `controls.heating_setpoint_schedule_id`.

**Missing:** 116/1,900 applicable field occurrences; **affected programs:** 116.

**Pattern / shared program types:** 48/116 affected definitions have attic, plenum, basement or data-center names; these names do not establish zero load or disabled conditioning.

**Affected building types:** SmallHotel (60); HighriseApartment (12); LargeOffice (10); MediumOffice (10); FullServiceRestaurant (8); QuickServiceRestaurant (8); SmallOffice (8).

**Current handling:** 20 degC nominal; if cooling is known, use min(20, minimum cooling - 2).

<!-- annotation:controls:heating_setpoint_schedule_id:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:controls:heating_setpoint_schedule_id:end -->

### Controls — `people_radiant_fraction`

**JSON field:** `controls.people_radiant_fraction`.

**Missing:** 1,900/1,900 applicable field occurrences; **affected programs:** 1,900.

**Pattern / shared program types:** Missing across every program type: the adapter does not populate these people heat-partition operands. 41/1900 affected program definitions are whole dwellings. Residential schedule-only execution does not determine load magnitude. 84/1900 affected definitions have attic, plenum, basement or data-center names; these names do not establish zero load or disabled conditioning.

**Affected building types:** Outpatient (369); SmallHotel (255); Hospital (243); LargeHotel (226); SuperMarket (150); SecondarySchool (145); PrimarySchool (123); RetailStandalone (64); MidriseApartment (49); RetailStripmall (40); Warehouse (40); HighriseApartment (37); LargeOffice (36); FullServiceRestaurant (23); QuickServiceRestaurant (23); SingleFamilyDetached (22); MediumOffice (20); SmallOffice (18); MultiFamily5PlusLowRise (6); SingleFamilyAttached (5); ManufacturedHome (3); MultiFamily2To4 (3).

**Current handling:** 0.3 of people sensible heat.

<!-- annotation:controls:people_radiant_fraction:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:controls:people_radiant_fraction:end -->

### Controls — `people_sensible_fraction`

**JSON field:** `controls.people_sensible_fraction`.

**Missing:** 1,900/1,900 applicable field occurrences; **affected programs:** 1,900.

**Pattern / shared program types:** Missing across every program type: the adapter does not populate these people heat-partition operands. 41/1900 affected program definitions are whole dwellings. Residential schedule-only execution does not determine load magnitude. 84/1900 affected definitions have attic, plenum, basement or data-center names; these names do not establish zero load or disabled conditioning.

**Affected building types:** Outpatient (369); SmallHotel (255); Hospital (243); LargeHotel (226); SuperMarket (150); SecondarySchool (145); PrimarySchool (123); RetailStandalone (64); MidriseApartment (49); RetailStripmall (40); Warehouse (40); HighriseApartment (37); LargeOffice (36); FullServiceRestaurant (23); QuickServiceRestaurant (23); SingleFamilyDetached (22); MediumOffice (20); SmallOffice (18); MultiFamily5PlusLowRise (6); SingleFamilyAttached (5); ManufacturedHome (3); MultiFamily2To4 (3).

**Current handling:** autocalculate: simulation engine determines sensible/latent split.

<!-- annotation:controls:people_sensible_fraction:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:controls:people_sensible_fraction:end -->

### Electric equipment — `heat_fractions.latent`

**JSON field:** `loads[].heat_fractions.latent (type=electric_equipment)`.

**Missing:** 631/2,064 applicable field occurrences; **affected programs:** 467.

**Pattern / shared program types:** Coverage depends on load type and which heat fractions the source reports; null can be unreported or inapplicable. Mixed raw records can lack an aggregate fraction while leaves retain known shares. 48/467 affected definitions have attic, plenum, basement or data-center names; these names do not establish zero load or disabled conditioning.

**Affected building types:** SmallHotel (72); LargeHotel (70); Hospital (54); Outpatient (50); SuperMarket (40); SecondarySchool (30); PrimarySchool (26); SingleFamilyDetached (22); RetailStandalone (20); LargeOffice (10); MediumOffice (10); RetailStripmall (10); Warehouse (10); FullServiceRestaurant (8); QuickServiceRestaurant (8); SmallOffice (8); MultiFamily5PlusLowRise (6); SingleFamilyAttached (5); ManufacturedHome (3); MultiFamily2To4 (3); HighriseApartment (1); MidriseApartment (1).

**Current handling:** 0 for a missing source-leaf fraction; preserve known shares, convection is residual. Rebuild mixtures from leaves rather than zeroing unknown aggregates.

**Missing occurrences by end use:** electric_equipment (426); clothes_dryer (41); clothes_washer (41); cooking_range (41); plug_loads_other (41); plug_loads_tv (41).

<!-- annotation:electric_equipment:heat_fractions.latent:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:electric_equipment:heat_fractions.latent:end -->

### Electric equipment — `heat_fractions.lost`

**JSON field:** `loads[].heat_fractions.lost (type=electric_equipment)`.

**Missing:** 631/2,064 applicable field occurrences; **affected programs:** 467.

**Pattern / shared program types:** Coverage depends on load type and which heat fractions the source reports; null can be unreported or inapplicable. Mixed raw records can lack an aggregate fraction while leaves retain known shares. 48/467 affected definitions have attic, plenum, basement or data-center names; these names do not establish zero load or disabled conditioning.

**Affected building types:** SmallHotel (72); LargeHotel (70); Hospital (54); Outpatient (50); SuperMarket (40); SecondarySchool (30); PrimarySchool (26); SingleFamilyDetached (22); RetailStandalone (20); LargeOffice (10); MediumOffice (10); RetailStripmall (10); Warehouse (10); FullServiceRestaurant (8); QuickServiceRestaurant (8); SmallOffice (8); MultiFamily5PlusLowRise (6); SingleFamilyAttached (5); ManufacturedHome (3); MultiFamily2To4 (3); HighriseApartment (1); MidriseApartment (1).

**Current handling:** 0 for a missing source-leaf fraction; preserve known shares, convection is residual. Rebuild mixtures from leaves rather than zeroing unknown aggregates.

**Missing occurrences by end use:** electric_equipment (426); clothes_dryer (41); clothes_washer (41); cooking_range (41); plug_loads_other (41); plug_loads_tv (41).

<!-- annotation:electric_equipment:heat_fractions.lost:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:electric_equipment:heat_fractions.lost:end -->

### Electric equipment — `heat_fractions.radiant`

**JSON field:** `loads[].heat_fractions.radiant (type=electric_equipment)`.

**Missing:** 631/2,064 applicable field occurrences; **affected programs:** 467.

**Pattern / shared program types:** Coverage depends on load type and which heat fractions the source reports; null can be unreported or inapplicable. Mixed raw records can lack an aggregate fraction while leaves retain known shares. 48/467 affected definitions have attic, plenum, basement or data-center names; these names do not establish zero load or disabled conditioning.

**Affected building types:** SmallHotel (72); LargeHotel (70); Hospital (54); Outpatient (50); SuperMarket (40); SecondarySchool (30); PrimarySchool (26); SingleFamilyDetached (22); RetailStandalone (20); LargeOffice (10); MediumOffice (10); RetailStripmall (10); Warehouse (10); FullServiceRestaurant (8); QuickServiceRestaurant (8); SmallOffice (8); MultiFamily5PlusLowRise (6); SingleFamilyAttached (5); ManufacturedHome (3); MultiFamily2To4 (3); HighriseApartment (1); MidriseApartment (1).

**Current handling:** 0 for a missing source-leaf fraction; preserve known shares, convection is residual. Rebuild mixtures from leaves rather than zeroing unknown aggregates.

**Missing occurrences by end use:** electric_equipment (426); clothes_dryer (41); clothes_washer (41); cooking_range (41); plug_loads_other (41); plug_loads_tv (41).

<!-- annotation:electric_equipment:heat_fractions.radiant:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:electric_equipment:heat_fractions.radiant:end -->

### Electric equipment — `heat_fractions.return_air`

**JSON field:** `loads[].heat_fractions.return_air (type=electric_equipment)`.

**Missing:** 2,064/2,064 applicable field occurrences; **affected programs:** 1,900.

**Pattern / shared program types:** Coverage depends on load type and which heat fractions the source reports; null can be unreported or inapplicable. Mixed raw records can lack an aggregate fraction while leaves retain known shares. 84/1900 affected definitions have attic, plenum, basement or data-center names; these names do not establish zero load or disabled conditioning.

**Affected building types:** Outpatient (369); SmallHotel (255); Hospital (243); LargeHotel (226); SuperMarket (150); SecondarySchool (145); PrimarySchool (123); RetailStandalone (64); MidriseApartment (49); RetailStripmall (40); Warehouse (40); HighriseApartment (37); LargeOffice (36); FullServiceRestaurant (23); QuickServiceRestaurant (23); SingleFamilyDetached (22); MediumOffice (20); SmallOffice (18); MultiFamily5PlusLowRise (6); SingleFamilyAttached (5); ManufacturedHome (3); MultiFamily2To4 (3).

**Current handling:** 0 for a missing source-leaf fraction; preserve known shares, convection is residual. Rebuild mixtures from leaves rather than zeroing unknown aggregates.

**Missing occurrences by end use:** electric_equipment (1859); clothes_dryer (41); clothes_washer (41); cooking_range (41); plug_loads_other (41); plug_loads_tv (41).

<!-- annotation:electric_equipment:heat_fractions.return_air:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:electric_equipment:heat_fractions.return_air:end -->

### Electric equipment — `heat_fractions.visible`

**JSON field:** `loads[].heat_fractions.visible (type=electric_equipment)`.

**Missing:** 2,064/2,064 applicable field occurrences; **affected programs:** 1,900.

**Pattern / shared program types:** Coverage depends on load type and which heat fractions the source reports; null can be unreported or inapplicable. Mixed raw records can lack an aggregate fraction while leaves retain known shares. 84/1900 affected definitions have attic, plenum, basement or data-center names; these names do not establish zero load or disabled conditioning.

**Affected building types:** Outpatient (369); SmallHotel (255); Hospital (243); LargeHotel (226); SuperMarket (150); SecondarySchool (145); PrimarySchool (123); RetailStandalone (64); MidriseApartment (49); RetailStripmall (40); Warehouse (40); HighriseApartment (37); LargeOffice (36); FullServiceRestaurant (23); QuickServiceRestaurant (23); SingleFamilyDetached (22); MediumOffice (20); SmallOffice (18); MultiFamily5PlusLowRise (6); SingleFamilyAttached (5); ManufacturedHome (3); MultiFamily2To4 (3).

**Current handling:** 0 for a missing source-leaf fraction; preserve known shares, convection is residual. Rebuild mixtures from leaves rather than zeroing unknown aggregates.

**Missing occurrences by end use:** electric_equipment (1859); clothes_dryer (41); clothes_washer (41); cooking_range (41); plug_loads_other (41); plug_loads_tv (41).

<!-- annotation:electric_equipment:heat_fractions.visible:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:electric_equipment:heat_fractions.visible:end -->

### Electric equipment — `schedule_id`

**JSON field:** `loads[].schedule_id (type=electric_equipment)`.

**Missing:** 98/2,064 applicable field occurrences; **affected programs:** 81.

**Pattern / shared program types:** 9/81 affected program definitions are whole dwellings. Residential schedule-only execution does not determine load magnitude. 48/81 affected definitions have attic, plenum, basement or data-center names; these names do not establish zero load or disabled conditioning.

**Affected building types:** SmallHotel (24); LargeOffice (10); MediumOffice (10); FullServiceRestaurant (8); QuickServiceRestaurant (8); SmallOffice (8); Hospital (4); SingleFamilyDetached (4); HighriseApartment (1); ManufacturedHome (1); MidriseApartment (1); MultiFamily2To4 (1); MultiFamily5PlusLowRise (1).

**Current handling:** Missing schedule: constant 0 for zero magnitude, constant 1 for a known positive magnitude. Preserve existing profiles.

**Missing occurrences by end use:** electric_equipment (72); clothes_dryer (8); clothes_washer (8); cooking_range (4); plug_loads_other (3); plug_loads_tv (3).

<!-- annotation:electric_equipment:schedule_id:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:electric_equipment:schedule_id:end -->

### Electric equipment — `value`

**JSON field:** `loads[].value (type=electric_equipment)`.

**Missing:** 295/2,064 applicable field occurrences; **affected programs:** 131.

**Pattern / shared program types:** All 205 exported residential appliance/plug-load magnitudes are unresolved; 33/768 commercial source equipment magnitudes are also missing. 41/131 affected program definitions are whole dwellings. Residential schedule-only execution does not determine load magnitude. 48/131 affected definitions have attic, plenum, basement or data-center names; these names do not establish zero load or disabled conditioning.

**Affected building types:** SmallHotel (40); SingleFamilyDetached (22); LargeOffice (10); MediumOffice (10); FullServiceRestaurant (8); QuickServiceRestaurant (8); SmallOffice (8); Hospital (6); MultiFamily5PlusLowRise (6); SingleFamilyAttached (5); ManufacturedHome (3); MultiFamily2To4 (3); HighriseApartment (1); MidriseApartment (1).

**Current handling:** 0 in the declared unit for an unknown source-leaf magnitude; rebuild mixtures from leaves and preserve known contributions.

**Missing occurrences by end use:** electric_equipment (90); clothes_dryer (41); clothes_washer (41); cooking_range (41); plug_loads_other (41); plug_loads_tv (41).

<!-- annotation:electric_equipment:value:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:electric_equipment:value:end -->

### Gas equipment — `heat_fractions.latent`

**JSON field:** `loads[].heat_fractions.latent (type=gas_equipment)`.

**Missing:** 1,794/1,859 applicable field occurrences; **affected programs:** 1,794.

**Pattern / shared program types:** Coverage depends on load type and which heat fractions the source reports; null can be unreported or inapplicable. Mixed raw records can lack an aggregate fraction while leaves retain known shares. 84/1794 affected definitions have attic, plenum, basement or data-center names; these names do not establish zero load or disabled conditioning.

**Affected building types:** Outpatient (364); SmallHotel (240); Hospital (238); LargeHotel (216); SecondarySchool (140); SuperMarket (140); PrimarySchool (118); RetailStandalone (64); MidriseApartment (48); RetailStripmall (40); Warehouse (40); HighriseApartment (36); LargeOffice (36); MediumOffice (20); FullServiceRestaurant (18); QuickServiceRestaurant (18); SmallOffice (18).

**Current handling:** 0 for a missing source-leaf fraction; preserve known shares, convection is residual. Rebuild mixtures from leaves rather than zeroing unknown aggregates.

**Missing occurrences by end use:** gas_equipment (1794).

<!-- annotation:gas_equipment:heat_fractions.latent:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:gas_equipment:heat_fractions.latent:end -->

### Gas equipment — `heat_fractions.lost`

**JSON field:** `loads[].heat_fractions.lost (type=gas_equipment)`.

**Missing:** 1,794/1,859 applicable field occurrences; **affected programs:** 1,794.

**Pattern / shared program types:** Coverage depends on load type and which heat fractions the source reports; null can be unreported or inapplicable. Mixed raw records can lack an aggregate fraction while leaves retain known shares. 84/1794 affected definitions have attic, plenum, basement or data-center names; these names do not establish zero load or disabled conditioning.

**Affected building types:** Outpatient (364); SmallHotel (240); Hospital (238); LargeHotel (216); SecondarySchool (140); SuperMarket (140); PrimarySchool (118); RetailStandalone (64); MidriseApartment (48); RetailStripmall (40); Warehouse (40); HighriseApartment (36); LargeOffice (36); MediumOffice (20); FullServiceRestaurant (18); QuickServiceRestaurant (18); SmallOffice (18).

**Current handling:** 0 for a missing source-leaf fraction; preserve known shares, convection is residual. Rebuild mixtures from leaves rather than zeroing unknown aggregates.

**Missing occurrences by end use:** gas_equipment (1794).

<!-- annotation:gas_equipment:heat_fractions.lost:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:gas_equipment:heat_fractions.lost:end -->

### Gas equipment — `heat_fractions.radiant`

**JSON field:** `loads[].heat_fractions.radiant (type=gas_equipment)`.

**Missing:** 1,794/1,859 applicable field occurrences; **affected programs:** 1,794.

**Pattern / shared program types:** Coverage depends on load type and which heat fractions the source reports; null can be unreported or inapplicable. Mixed raw records can lack an aggregate fraction while leaves retain known shares. 84/1794 affected definitions have attic, plenum, basement or data-center names; these names do not establish zero load or disabled conditioning.

**Affected building types:** Outpatient (364); SmallHotel (240); Hospital (238); LargeHotel (216); SecondarySchool (140); SuperMarket (140); PrimarySchool (118); RetailStandalone (64); MidriseApartment (48); RetailStripmall (40); Warehouse (40); HighriseApartment (36); LargeOffice (36); MediumOffice (20); FullServiceRestaurant (18); QuickServiceRestaurant (18); SmallOffice (18).

**Current handling:** 0 for a missing source-leaf fraction; preserve known shares, convection is residual. Rebuild mixtures from leaves rather than zeroing unknown aggregates.

**Missing occurrences by end use:** gas_equipment (1794).

<!-- annotation:gas_equipment:heat_fractions.radiant:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:gas_equipment:heat_fractions.radiant:end -->

### Gas equipment — `heat_fractions.return_air`

**JSON field:** `loads[].heat_fractions.return_air (type=gas_equipment)`.

**Missing:** 1,859/1,859 applicable field occurrences; **affected programs:** 1,859.

**Pattern / shared program types:** Coverage depends on load type and which heat fractions the source reports; null can be unreported or inapplicable. Mixed raw records can lack an aggregate fraction while leaves retain known shares. 84/1859 affected definitions have attic, plenum, basement or data-center names; these names do not establish zero load or disabled conditioning.

**Affected building types:** Outpatient (369); SmallHotel (255); Hospital (243); LargeHotel (226); SuperMarket (150); SecondarySchool (145); PrimarySchool (123); RetailStandalone (64); MidriseApartment (48); RetailStripmall (40); Warehouse (40); HighriseApartment (36); LargeOffice (36); FullServiceRestaurant (23); QuickServiceRestaurant (23); MediumOffice (20); SmallOffice (18).

**Current handling:** 0 for a missing source-leaf fraction; preserve known shares, convection is residual. Rebuild mixtures from leaves rather than zeroing unknown aggregates.

**Missing occurrences by end use:** gas_equipment (1859).

<!-- annotation:gas_equipment:heat_fractions.return_air:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:gas_equipment:heat_fractions.return_air:end -->

### Gas equipment — `heat_fractions.visible`

**JSON field:** `loads[].heat_fractions.visible (type=gas_equipment)`.

**Missing:** 1,859/1,859 applicable field occurrences; **affected programs:** 1,859.

**Pattern / shared program types:** Coverage depends on load type and which heat fractions the source reports; null can be unreported or inapplicable. Mixed raw records can lack an aggregate fraction while leaves retain known shares. 84/1859 affected definitions have attic, plenum, basement or data-center names; these names do not establish zero load or disabled conditioning.

**Affected building types:** Outpatient (369); SmallHotel (255); Hospital (243); LargeHotel (226); SuperMarket (150); SecondarySchool (145); PrimarySchool (123); RetailStandalone (64); MidriseApartment (48); RetailStripmall (40); Warehouse (40); HighriseApartment (36); LargeOffice (36); FullServiceRestaurant (23); QuickServiceRestaurant (23); MediumOffice (20); SmallOffice (18).

**Current handling:** 0 for a missing source-leaf fraction; preserve known shares, convection is residual. Rebuild mixtures from leaves rather than zeroing unknown aggregates.

**Missing occurrences by end use:** gas_equipment (1859).

<!-- annotation:gas_equipment:heat_fractions.visible:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:gas_equipment:heat_fractions.visible:end -->

### Gas equipment — `schedule_id`

**JSON field:** `loads[].schedule_id (type=gas_equipment)`.

**Missing:** 902/1,859 applicable field occurrences; **affected programs:** 902.

**Pattern / shared program types:** 713/768 commercial source leaves lack a gas end-use magnitude/reference. Many reviewed overlays supply reviewed zeros; a raw null alone does not prove absence. 42/902 affected definitions have attic, plenum, basement or data-center names; these names do not establish zero load or disabled conditioning.

**Affected building types:** Outpatient (182); SmallHotel (125); Hospital (119); LargeHotel (108); SecondarySchool (70); SuperMarket (70); PrimarySchool (59); RetailStandalone (32); MidriseApartment (24); RetailStripmall (20); Warehouse (20); HighriseApartment (18); LargeOffice (18); MediumOffice (10); FullServiceRestaurant (9); QuickServiceRestaurant (9); SmallOffice (9).

**Current handling:** Missing schedule: constant 0 for zero magnitude, constant 1 for a known positive magnitude. Preserve existing profiles.

**Missing occurrences by end use:** gas_equipment (902).

<!-- annotation:gas_equipment:schedule_id:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:gas_equipment:schedule_id:end -->

### Gas equipment — `value`

**JSON field:** `loads[].value (type=gas_equipment)`.

**Missing:** 902/1,859 applicable field occurrences; **affected programs:** 902.

**Pattern / shared program types:** 713/768 commercial source leaves lack a gas end-use magnitude/reference. Many reviewed overlays supply reviewed zeros; a raw null alone does not prove absence. 42/902 affected definitions have attic, plenum, basement or data-center names; these names do not establish zero load or disabled conditioning.

**Affected building types:** Outpatient (182); SmallHotel (125); Hospital (119); LargeHotel (108); SecondarySchool (70); SuperMarket (70); PrimarySchool (59); RetailStandalone (32); MidriseApartment (24); RetailStripmall (20); Warehouse (20); HighriseApartment (18); LargeOffice (18); MediumOffice (10); FullServiceRestaurant (9); QuickServiceRestaurant (9); SmallOffice (9).

**Current handling:** 0 in the declared unit for an unknown source-leaf magnitude; rebuild mixtures from leaves and preserve known contributions.

**Missing occurrences by end use:** gas_equipment (902).

<!-- annotation:gas_equipment:value:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:gas_equipment:value:end -->

### Hot water — `inlet_temperature_schedule_id`

**JSON field:** `loads[].inlet_temperature_schedule_id (type=hot_water); also shared_services[].loads[]`.

**Missing:** 700/700 applicable field occurrences; **affected programs:** 405.

**Pattern / shared program types:** Every water-demand entry lacks inlet temperature; the exporter currently does not ingest it. 41/405 affected program definitions are whole dwellings. Residential schedule-only execution does not determine load magnitude.

**Affected building types:** Outpatient (115); LargeHotel (96); SmallHotel (59); RetailStripmall (24); MidriseApartment (23); SingleFamilyDetached (22); HighriseApartment (19); LargeOffice (10); MediumOffice (10); MultiFamily5PlusLowRise (6); FullServiceRestaurant (5); QuickServiceRestaurant (5); SingleFamilyAttached (5); ManufacturedHome (3); MultiFamily2To4 (3).

**Current handling:** 10 degC nominal; if target is known, use min(10, minimum target).

**Missing occurrences by end use:** hot_water_volume (618); hot_water_clothes_washer (41); hot_water_fixtures (41).

**Missing occurrences by scope:** shared_services[].loads[] (358); loads[] (342).

<!-- annotation:hot_water:inlet_temperature_schedule_id:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:hot_water:inlet_temperature_schedule_id:end -->

### Hot water — `schedule_id`

**JSON field:** `loads[].schedule_id (type=hot_water); also shared_services[].loads[]`.

**Missing:** 11/700 applicable field occurrences; **affected programs:** 8.

**Pattern / shared program types:** 8/8 affected program definitions are whole dwellings. Residential schedule-only execution does not determine load magnitude.

**Affected building types:** SingleFamilyDetached (4); HighriseApartment (1); MidriseApartment (1); MultiFamily2To4 (1); MultiFamily5PlusLowRise (1).

**Current handling:** Missing schedule: constant 0 for zero magnitude, constant 1 for a known positive magnitude. Preserve existing profiles.

**Missing occurrences by end use:** hot_water_clothes_washer (8); hot_water_fixtures (3).

**Missing occurrences by scope:** loads[] (11).

<!-- annotation:hot_water:schedule_id:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:hot_water:schedule_id:end -->

### Hot water — `target_temperature_schedule_id`

**JSON field:** `loads[].target_temperature_schedule_id (type=hot_water); also shared_services[].loads[]`.

**Missing:** 108/700 applicable field occurrences; **affected programs:** 67.

**Pattern / shared program types:** 41/67 affected program definitions are whole dwellings. Residential schedule-only execution does not determine load magnitude.

**Affected building types:** SingleFamilyDetached (22); LargeHotel (10); Outpatient (10); MultiFamily5PlusLowRise (6); SmallHotel (6); SingleFamilyAttached (5); ManufacturedHome (3); MultiFamily2To4 (3); HighriseApartment (1); MidriseApartment (1).

**Current handling:** 60 degC nominal; preserve known target temperatures and keep target at or above known inlet.

**Missing occurrences by end use:** hot_water_clothes_washer (41); hot_water_fixtures (41); hot_water_volume (26).

**Missing occurrences by scope:** loads[] (108).

<!-- annotation:hot_water:target_temperature_schedule_id:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:hot_water:target_temperature_schedule_id:end -->

### Hot water — `value`

**JSON field:** `loads[].value (type=hot_water); also shared_services[].loads[]`.

**Missing:** 82/700 applicable field occurrences; **affected programs:** 41.

**Pattern / shared program types:** All 82 residential water magnitudes are unresolved. Existing commercial local/shared demand magnitudes are present; unknown allocations are a separate gap below. 41/41 affected program definitions are whole dwellings. Residential schedule-only execution does not determine load magnitude.

**Affected building types:** SingleFamilyDetached (22); MultiFamily5PlusLowRise (6); SingleFamilyAttached (5); ManufacturedHome (3); MultiFamily2To4 (3); HighriseApartment (1); MidriseApartment (1).

**Current handling:** 0 in the declared unit for an unknown source-leaf magnitude; rebuild mixtures from leaves and preserve known contributions.

**Missing occurrences by end use:** hot_water_clothes_washer (41); hot_water_fixtures (41).

**Missing occurrences by scope:** loads[] (82).

<!-- annotation:hot_water:value:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:hot_water:value:end -->

### Lighting — `heat_fractions.latent`

**JSON field:** `loads[].heat_fractions.latent (type=lighting)`.

**Missing:** 3,759/3,759 applicable field occurrences; **affected programs:** 1,900.

**Pattern / shared program types:** Coverage depends on load type and which heat fractions the source reports; null can be unreported or inapplicable. Mixed raw records can lack an aggregate fraction while leaves retain known shares. 84/1900 affected definitions have attic, plenum, basement or data-center names; these names do not establish zero load or disabled conditioning.

**Affected building types:** Outpatient (369); SmallHotel (255); Hospital (243); LargeHotel (226); SuperMarket (150); SecondarySchool (145); PrimarySchool (123); RetailStandalone (64); MidriseApartment (49); RetailStripmall (40); Warehouse (40); HighriseApartment (37); LargeOffice (36); FullServiceRestaurant (23); QuickServiceRestaurant (23); SingleFamilyDetached (22); MediumOffice (20); SmallOffice (18); MultiFamily5PlusLowRise (6); SingleFamilyAttached (5); ManufacturedHome (3); MultiFamily2To4 (3).

**Current handling:** 0 for a missing source-leaf fraction; preserve known shares, convection is residual. Rebuild mixtures from leaves rather than zeroing unknown aggregates.

**Missing occurrences by end use:** additional_lighting (1859); lighting (1859); lighting_interior (41).

<!-- annotation:lighting:heat_fractions.latent:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:lighting:heat_fractions.latent:end -->

### Lighting — `heat_fractions.lost`

**JSON field:** `loads[].heat_fractions.lost (type=lighting)`.

**Missing:** 3,759/3,759 applicable field occurrences; **affected programs:** 1,900.

**Pattern / shared program types:** Coverage depends on load type and which heat fractions the source reports; null can be unreported or inapplicable. Mixed raw records can lack an aggregate fraction while leaves retain known shares. 84/1900 affected definitions have attic, plenum, basement or data-center names; these names do not establish zero load or disabled conditioning.

**Affected building types:** Outpatient (369); SmallHotel (255); Hospital (243); LargeHotel (226); SuperMarket (150); SecondarySchool (145); PrimarySchool (123); RetailStandalone (64); MidriseApartment (49); RetailStripmall (40); Warehouse (40); HighriseApartment (37); LargeOffice (36); FullServiceRestaurant (23); QuickServiceRestaurant (23); SingleFamilyDetached (22); MediumOffice (20); SmallOffice (18); MultiFamily5PlusLowRise (6); SingleFamilyAttached (5); ManufacturedHome (3); MultiFamily2To4 (3).

**Current handling:** 0 for a missing source-leaf fraction; preserve known shares, convection is residual. Rebuild mixtures from leaves rather than zeroing unknown aggregates.

**Missing occurrences by end use:** additional_lighting (1859); lighting (1859); lighting_interior (41).

<!-- annotation:lighting:heat_fractions.lost:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:lighting:heat_fractions.lost:end -->

### Lighting — `heat_fractions.radiant`

**JSON field:** `loads[].heat_fractions.radiant (type=lighting)`.

**Missing:** 909/3,759 applicable field occurrences; **affected programs:** 475.

**Pattern / shared program types:** Coverage depends on load type and which heat fractions the source reports; null can be unreported or inapplicable. Mixed raw records can lack an aggregate fraction while leaves retain known shares. 48/475 affected definitions have attic, plenum, basement or data-center names; these names do not establish zero load or disabled conditioning.

**Affected building types:** SmallHotel (80); LargeHotel (70); Hospital (54); Outpatient (50); SuperMarket (40); SecondarySchool (30); PrimarySchool (26); SingleFamilyDetached (22); RetailStandalone (20); LargeOffice (10); MediumOffice (10); RetailStripmall (10); Warehouse (10); FullServiceRestaurant (8); QuickServiceRestaurant (8); SmallOffice (8); MultiFamily5PlusLowRise (6); SingleFamilyAttached (5); ManufacturedHome (3); MultiFamily2To4 (3); HighriseApartment (1); MidriseApartment (1).

**Current handling:** 0 for a missing source-leaf fraction; preserve known shares, convection is residual. Rebuild mixtures from leaves rather than zeroing unknown aggregates.

**Missing occurrences by end use:** additional_lighting (434); lighting (434); lighting_interior (41).

<!-- annotation:lighting:heat_fractions.radiant:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:lighting:heat_fractions.radiant:end -->

### Lighting — `heat_fractions.return_air`

**JSON field:** `loads[].heat_fractions.return_air (type=lighting)`.

**Missing:** 909/3,759 applicable field occurrences; **affected programs:** 475.

**Pattern / shared program types:** Coverage depends on load type and which heat fractions the source reports; null can be unreported or inapplicable. Mixed raw records can lack an aggregate fraction while leaves retain known shares. 48/475 affected definitions have attic, plenum, basement or data-center names; these names do not establish zero load or disabled conditioning.

**Affected building types:** SmallHotel (80); LargeHotel (70); Hospital (54); Outpatient (50); SuperMarket (40); SecondarySchool (30); PrimarySchool (26); SingleFamilyDetached (22); RetailStandalone (20); LargeOffice (10); MediumOffice (10); RetailStripmall (10); Warehouse (10); FullServiceRestaurant (8); QuickServiceRestaurant (8); SmallOffice (8); MultiFamily5PlusLowRise (6); SingleFamilyAttached (5); ManufacturedHome (3); MultiFamily2To4 (3); HighriseApartment (1); MidriseApartment (1).

**Current handling:** 0 for a missing source-leaf fraction; preserve known shares, convection is residual. Rebuild mixtures from leaves rather than zeroing unknown aggregates.

**Missing occurrences by end use:** additional_lighting (434); lighting (434); lighting_interior (41).

<!-- annotation:lighting:heat_fractions.return_air:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:lighting:heat_fractions.return_air:end -->

### Lighting — `heat_fractions.visible`

**JSON field:** `loads[].heat_fractions.visible (type=lighting)`.

**Missing:** 909/3,759 applicable field occurrences; **affected programs:** 475.

**Pattern / shared program types:** Coverage depends on load type and which heat fractions the source reports; null can be unreported or inapplicable. Mixed raw records can lack an aggregate fraction while leaves retain known shares. 48/475 affected definitions have attic, plenum, basement or data-center names; these names do not establish zero load or disabled conditioning.

**Affected building types:** SmallHotel (80); LargeHotel (70); Hospital (54); Outpatient (50); SuperMarket (40); SecondarySchool (30); PrimarySchool (26); SingleFamilyDetached (22); RetailStandalone (20); LargeOffice (10); MediumOffice (10); RetailStripmall (10); Warehouse (10); FullServiceRestaurant (8); QuickServiceRestaurant (8); SmallOffice (8); MultiFamily5PlusLowRise (6); SingleFamilyAttached (5); ManufacturedHome (3); MultiFamily2To4 (3); HighriseApartment (1); MidriseApartment (1).

**Current handling:** 0 for a missing source-leaf fraction; preserve known shares, convection is residual. Rebuild mixtures from leaves rather than zeroing unknown aggregates.

**Missing occurrences by end use:** additional_lighting (434); lighting (434); lighting_interior (41).

<!-- annotation:lighting:heat_fractions.visible:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:lighting:heat_fractions.visible:end -->

### Lighting — `schedule_id`

**JSON field:** `loads[].schedule_id (type=lighting)`.

**Missing:** 431/3,759 applicable field occurrences; **affected programs:** 403.

**Pattern / shared program types:** 3/403 affected program definitions are whole dwellings. Residential schedule-only execution does not determine load magnitude. 24/403 affected definitions have attic, plenum, basement or data-center names; these names do not establish zero load or disabled conditioning.

**Affected building types:** SmallHotel (74); LargeHotel (70); Hospital (54); Outpatient (50); SuperMarket (40); SecondarySchool (30); PrimarySchool (26); RetailStandalone (20); Warehouse (10); LargeOffice (5); MediumOffice (5); FullServiceRestaurant (4); QuickServiceRestaurant (4); RetailStripmall (4); SmallOffice (4); SingleFamilyDetached (2); MultiFamily5PlusLowRise (1).

**Current handling:** Missing schedule: constant 0 for zero magnitude, constant 1 for a known positive magnitude. Preserve existing profiles.

**Missing occurrences by end use:** additional_lighting (400); lighting (28); lighting_interior (3).

<!-- annotation:lighting:schedule_id:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:lighting:schedule_id:end -->

### Lighting — `value`

**JSON field:** `loads[].value (type=lighting)`.

**Missing:** 1,860/3,759 applicable field occurrences; **affected programs:** 1,840.

**Pattern / shared program types:** Most gaps are additional lighting, not ordinary lighting: commercial source leaves lack 741/768 additional-lighting magnitudes versus 10/768 ordinary-lighting magnitudes. All 41 dwelling lighting magnitudes are unresolved. 41/1840 affected program definitions are whole dwellings. Residential schedule-only execution does not determine load magnitude. 84/1840 affected definitions have attic, plenum, basement or data-center names; these names do not establish zero load or disabled conditioning.

**Affected building types:** Outpatient (369); SmallHotel (255); Hospital (243); LargeHotel (226); SuperMarket (150); SecondarySchool (145); PrimarySchool (123); RetailStandalone (64); Warehouse (40); LargeOffice (36); MidriseApartment (31); FullServiceRestaurant (23); QuickServiceRestaurant (23); SingleFamilyDetached (22); MediumOffice (20); HighriseApartment (19); SmallOffice (18); RetailStripmall (16); MultiFamily5PlusLowRise (6); SingleFamilyAttached (5); ManufacturedHome (3); MultiFamily2To4 (3).

**Current handling:** 0 in the declared unit for an unknown source-leaf magnitude; rebuild mixtures from leaves and preserve known contributions.

**Missing occurrences by end use:** additional_lighting (1799); lighting_interior (41); lighting (20).

<!-- annotation:lighting:value:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:lighting:value:end -->

### Occupancy — `schedule_id`

**JSON field:** `loads[].schedule_id (type=occupancy)`.

**Missing:** 45/1,900 applicable field occurrences; **affected programs:** 45.

**Pattern / shared program types:** 30/45 affected definitions have attic, plenum, basement or data-center names; these names do not establish zero load or disabled conditioning.

**Affected building types:** SmallHotel (15); LargeOffice (11); MediumOffice (5); FullServiceRestaurant (4); QuickServiceRestaurant (4); SmallOffice (4); MidriseApartment (2).

**Current handling:** Missing schedule: constant 0 for zero magnitude, constant 1 for a known positive magnitude. Preserve existing profiles.

**Missing occurrences by end use:** occupancy (45).

<!-- annotation:occupancy:schedule_id:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:occupancy:schedule_id:end -->

### Occupancy — `value`

**JSON field:** `loads[].value (type=occupancy)`.

**Missing:** 60/1,900 applicable field occurrences; **affected programs:** 60.

**Pattern / shared program types:** 60/60 affected definitions have attic, plenum, basement or data-center names; these names do not establish zero load or disabled conditioning.

**Affected building types:** LargeOffice (22); MediumOffice (10); FullServiceRestaurant (8); QuickServiceRestaurant (8); SmallOffice (8); SmallHotel (4).

**Current handling:** 0 in the declared unit for an unknown source-leaf magnitude; rebuild mixtures from leaves and preserve known contributions.

**Missing occurrences by end use:** occupancy (60).

<!-- annotation:occupancy:value:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:occupancy:value:end -->

### Schedules — `rules coverage`

**JSON field:** `schedules[].rules`.

**Missing:** 5/3,761 applicable field occurrences; **affected programs:** 18.

**Pattern / shared program types:** Five distinct rulesets lack complete date/day-selector coverage, including special days. A known schedule reference does not guarantee complete coverage.

**Affected building types:** LargeOffice (12); MediumOffice (6).

**Current handling:** Prepend a lowest-priority Default rule: 0 for fractions, 120 W/person for activity, or a compatible temperature fallback; preserve all source rules.

<!-- annotation:schedules:rules coverage:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:schedules:rules coverage:end -->

### Source evidence — `original_value`

**JSON field:** `source.evidence[].original_value`.

**Missing:** 3,285/14,044 applicable field occurrences; **affected programs:** 1,481.

**Pattern / shared program types:** Evidence metadata can legitimately be null for unknown source values or derived records. Keep those unknowns; do not fill evidence with simulation defaults.

**Affected building types:** Outpatient (319); Hospital (189); SmallHotel (187); LargeHotel (156); SecondarySchool (115); SuperMarket (110); PrimarySchool (97); MidriseApartment (48); RetailStandalone (44); HighriseApartment (36); LargeOffice (36); RetailStripmall (30); Warehouse (30); FullServiceRestaurant (23); QuickServiceRestaurant (23); MediumOffice (20); SmallOffice (18).

**Current handling:** Preserve null; no experimental defaults apply to evidence.

<!-- annotation:source.evidence:original_value:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:source.evidence:original_value:end -->

### Source evidence — `source_file_id`

**JSON field:** `source.evidence[].source_file_id`.

**Missing:** 2,155/14,044 applicable field occurrences; **affected programs:** 1,091.

**Pattern / shared program types:** Evidence metadata can legitimately be null for unknown source values or derived records. Keep those unknowns; do not fill evidence with simulation defaults.

**Affected building types:** Outpatient (207); SmallHotel (159); Hospital (146); LargeHotel (143); SuperMarket (90); SecondarySchool (85); PrimarySchool (72); RetailStandalone (42); RetailStripmall (25); Warehouse (25); MidriseApartment (24); HighriseApartment (18); LargeOffice (18); MediumOffice (10); FullServiceRestaurant (9); QuickServiceRestaurant (9); SmallOffice (9).

**Current handling:** Preserve null; no experimental defaults apply to evidence.

<!-- annotation:source.evidence:source_file_id:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:source.evidence:source_file_id:end -->

## Missing or omitted information without a usable DTO field

These are contract/export gaps, kept separate from null operands in existing fields. Their annotation areas can record whether and how to add them.

### `ventilation_m3_s_m2` — air requirements

**Field to review:** `ventilation_m3_s_m2`; not represented in program JSON.

**Upstream commercial coverage:** 700/768 present; 68/768 unknown.

**Pattern:** Known outdoor-air terms are omitted by the DTO. Missing per-area/per-person/ACH terms may be alternative inputs; do not infer total ventilation from one term alone. Infiltration rate and basis remain unresolved across the commercial source selection.

**Building types with upstream nulls:** Hospital (30); LargeOffice (11); MediumOffice (5); SuperMarket (5); FullServiceRestaurant (4); QuickServiceRestaurant (4); SmallOffice (4); Outpatient (3); SmallHotel (2).

**Example source space types with nulls:** Plenum, Basement, ICU_Open, OR, Elec/MechRoom, ER_Exam.

**Current handling:** No program-JSON fallback. Preserve source bases and distinguish ventilation from infiltration.

<!-- annotation:omitted:ventilation_m3_s_m2:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:omitted:ventilation_m3_s_m2:end -->

### `ventilation_m3_s_person` — air requirements

**Field to review:** `ventilation_m3_s_person`; not represented in program JSON.

**Upstream commercial coverage:** 520/768 present; 248/768 unknown.

**Pattern:** Known outdoor-air terms are omitted by the DTO. Missing per-area/per-person/ACH terms may be alternative inputs; do not infer total ventilation from one term alone. Infiltration rate and basis remain unresolved across the commercial source selection.

**Building types with upstream nulls:** Outpatient (60); Hospital (47); SmallHotel (38); LargeOffice (16); PrimarySchool (15); SecondarySchool (15); SuperMarket (13); LargeHotel (12); MediumOffice (8); SmallOffice (7); Warehouse (6); FullServiceRestaurant (4); QuickServiceRestaurant (4); RetailStandalone (3).

**Example source space types with nulls:** Plenum, WholeBuilding - Sm Office, Mechanical, ElevatorCore4, ICU_Open, Stair.

**Current handling:** No program-JSON fallback. Preserve source bases and distinguish ventilation from infiltration.

<!-- annotation:omitted:ventilation_m3_s_person:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:omitted:ventilation_m3_s_person:end -->

### `ventilation_ach` — air requirements

**Field to review:** `ventilation_ach`; not represented in program JSON.

**Upstream commercial coverage:** 39/768 present; 729/768 unknown.

**Pattern:** Known outdoor-air terms are omitted by the DTO. Missing per-area/per-person/ACH terms may be alternative inputs; do not infer total ventilation from one term alone. Infiltration rate and basis remain unresolved across the commercial source selection.

**Building types with upstream nulls:** Outpatient (162); SmallHotel (96); LargeHotel (83); Hospital (76); SecondarySchool (60); SuperMarket (60); PrimarySchool (51); RetailStandalone (22); LargeOffice (18); MidriseApartment (15); RetailStripmall (15); Warehouse (15); FullServiceRestaurant (14); QuickServiceRestaurant (14); MediumOffice (10); HighriseApartment (9); SmallOffice (9).

**Example source space types with nulls:** Plenum, WholeBuilding - Sm Office, Basement, OR, PACU, Mechanical.

**Current handling:** No program-JSON fallback. Preserve source bases and distinguish ventilation from infiltration.

<!-- annotation:omitted:ventilation_ach:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:omitted:ventilation_ach:end -->

### `infiltration_m3_s_m2` — air requirements

**Field to review:** `infiltration_m3_s_m2`; not represented in program JSON.

**Upstream commercial coverage:** 0/768 present; 768/768 unknown.

**Pattern:** Known outdoor-air terms are omitted by the DTO. Missing per-area/per-person/ACH terms may be alternative inputs; do not infer total ventilation from one term alone. Infiltration rate and basis remain unresolved across the commercial source selection.

**Building types with upstream nulls:** Outpatient (162); Hospital (97); SmallHotel (96); LargeHotel (83); SecondarySchool (60); SuperMarket (60); PrimarySchool (51); MidriseApartment (24); RetailStandalone (22); HighriseApartment (18); LargeOffice (18); RetailStripmall (15); Warehouse (15); FullServiceRestaurant (14); QuickServiceRestaurant (14); MediumOffice (10); SmallOffice (9).

**Example source space types with nulls:** Plenum, WholeBuilding - Sm Office, Basement, OR, PACU, Mechanical.

**Current handling:** No program-JSON fallback. Preserve source bases and distinguish ventilation from infiltration.

<!-- annotation:omitted:infiltration_m3_s_m2:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:omitted:infiltration_m3_s_m2:end -->

### `infiltration_basis` — air requirements

**Field to review:** `infiltration_basis`; not represented in program JSON.

**Upstream commercial coverage:** 0/768 present; 768/768 unknown.

**Pattern:** Known outdoor-air terms are omitted by the DTO. Missing per-area/per-person/ACH terms may be alternative inputs; do not infer total ventilation from one term alone. Infiltration rate and basis remain unresolved across the commercial source selection.

**Building types with upstream nulls:** Outpatient (162); Hospital (97); SmallHotel (96); LargeHotel (83); SecondarySchool (60); SuperMarket (60); PrimarySchool (51); MidriseApartment (24); RetailStandalone (22); HighriseApartment (18); LargeOffice (18); RetailStripmall (15); Warehouse (15); FullServiceRestaurant (14); QuickServiceRestaurant (14); MediumOffice (10); SmallOffice (9).

**Example source space types with nulls:** Plenum, WholeBuilding - Sm Office, Basement, OR, PACU, Mechanical.

**Current handling:** No program-JSON fallback. Preserve source bases and distinguish ventilation from infiltration.

<!-- annotation:omitted:infiltration_basis:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:omitted:infiltration_basis:end -->

### `loads[].end_use=ceiling_fan` — absent demand channel

**Coverage gap:** 26/41 dwelling configurations retain this channel's annual profile upstream but have no corresponding exported load.

**Pattern:** Whole-dwelling records; the fixed exporter channel list omits this end use. A retained profile does not establish its missing magnitude.

**Current handling:** No load created and no magnitude fallback applied to this omitted channel.

<!-- annotation:omitted:ceiling_fan:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:omitted:ceiling_fan:end -->

### `loads[].end_use=dishwasher` — absent demand channel

**Coverage gap:** 26/41 dwelling configurations retain this channel's annual profile upstream but have no corresponding exported load.

**Pattern:** Whole-dwelling records; the fixed exporter channel list omits this end use. A retained profile does not establish its missing magnitude.

**Current handling:** No load created and no magnitude fallback applied to this omitted channel.

<!-- annotation:omitted:dishwasher:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:omitted:dishwasher:end -->

### `loads[].end_use=hot_water_dishwasher` — absent demand channel

**Coverage gap:** 26/41 dwelling configurations retain this channel's annual profile upstream but have no corresponding exported load.

**Pattern:** Whole-dwelling records; the fixed exporter channel list omits this end use. A retained profile does not establish its missing magnitude.

**Current handling:** No load created and no magnitude fallback applied to this omitted channel.

<!-- annotation:omitted:hot_water_dishwasher:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:omitted:hot_water_dishwasher:end -->

### `loads[].end_use=lighting_garage` — absent demand channel

**Coverage gap:** 14/41 dwelling configurations retain this channel's annual profile upstream but have no corresponding exported load.

**Pattern:** Whole-dwelling records; the fixed exporter channel list omits this end use. A retained profile does not establish its missing magnitude.

**Current handling:** No load created and no magnitude fallback applied to this omitted channel.

<!-- annotation:omitted:lighting_garage:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:omitted:lighting_garage:end -->

### `loads[].type` — cooking_range fuel

**Gap:** 17/41 source configurations select Gas or Propane, but this channel is labelled `electric_equipment`.

**Pattern:** Residential cooking range; source-option counts: Electric Resistance (22); Gas (14); Propane (3); Electric Induction (1); None (1).

**Current handling:** Category is inferred from the channel name rather than source fuel; magnitudes remain unknown. No correction applied by this review.

<!-- annotation:classification:cooking_range:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:classification:cooking_range:end -->

### `loads[].type` — clothes_dryer fuel

**Gap:** 7/41 source configurations select Gas or Propane, but this channel is labelled `electric_equipment`.

**Pattern:** Residential clothes dryer; source-option counts: Electric (28); Gas (6); None (6); Propane (1).

**Current handling:** Category is inferred from the channel name rather than source fuel; magnitudes remain unknown. No correction applied by this review.

<!-- annotation:classification:clothes_dryer:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:classification:clothes_dryer:end -->

### Hot water — program/service allocation

**Missing:** 279 distinct commercial source-program allocations remain unresolved.

**Pattern / building types:** SuperMarket (50); SmallHotel (48); Hospital (47); SecondarySchool (43); PrimarySchool (41); LargeHotel (27); RetailStandalone (11); Warehouse (9); FullServiceRestaurant (3). Concentrated in supermarkets, hotels, hospitals and schools.

**Current handling:** Shared services and reporting allocations do not prove local fixture placement. Keep source unknowns distinct from the 206 reviewed no-modeled-draw cases.

<!-- annotation:omitted:water_allocation:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:omitted:water_allocation:end -->

### Residential — natural infiltration and outdoor air

**Pattern / missing information:** All 41 dwelling DTOs omit these operands. Separate enclosure definitions retain unresolved natural infiltration/outdoor air; pressure-test leakage such as ACH50 requires a conversion model, geometry and weather.

**Current handling:** No new fields or defaults added by this review.

<!-- annotation:omitted:residential_air:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:omitted:residential_air:end -->

### `source.climate` — dedicated context field

**Pattern / missing information:** Residential climate context exists in canonical definitions/evidence but has no dedicated DTO field. Program data are not duplicated by climate merely to fill a Cartesian table.

**Current handling:** No new fields or defaults added by this review.

<!-- annotation:omitted:source_climate:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:omitted:source_climate:end -->

### `source.vintage` — dedicated context field

**Pattern / missing information:** Residential stock vintage exists upstream but has no dedicated DTO field. Keep existing-stock vintages distinct from code/prototype templates.

**Current handling:** No new fields or defaults added by this review.

<!-- annotation:omitted:source_vintage:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:omitted:source_vintage:end -->

### Composition — members and weights

**Pattern / missing information:** The 378 mixture definitions lack dedicated DTO recipe/member fields. Weighted demand trajectories are exported, while recipe membership/weights remain in the pinned definitions. Resolve missing source leaves before recomposition.

**Current handling:** No new fields or defaults added by this review.

<!-- annotation:omitted:composition:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:omitted:composition:end -->

### Provenance — operand links and source descriptors

**Pattern / missing information:** All programs retain program-level evidence, but lack a complete self-contained operand-to-evidence map and upstream revision/checksum descriptors. The repository retains pinned source evidence; this is an export representation gap.

**Current handling:** No new fields or defaults added by this review.

<!-- annotation:omitted:provenance:begin -->
**Your annotations / proposed approach:**


**Agreed decision:**


**Status:** Open
<!-- annotation:omitted:provenance:end -->

## Scope boundaries and pinned inputs

Geometry, area/count scaling, calendar/holiday bindings, service hosts, envelope and HVAC/sizing remain separate consumer inputs/contracts. Residential annual profiles retain their recorded 2007 calendar and schedule-only/proxy-weather limitations. Identity, type, unit and scaling-basis fields have no missing values in this audit. Raw `default_policy_id=null` and `assumptions=[]` are intentional mode semantics. Source evidence may legitimately remain null even in defaulted exports. No original physical data or default policy changes are made by this document.

Counts are derived from the following SHA-256-pinned inputs. Original values, units, source locators, transformations, extraction dates and interpretation notes remain in the frozen evidence.

| Input | SHA-256 |
| --- | --- |
| [data/completion-releases/v0.1.0/commercial-completion.json](../../data/completion-releases/v0.1.0/commercial-completion.json) | `16a9d28d4080815cddb1f37c41eddbc4004b25d7aebf619aef386f547b5fed30` |
| [data/definition-releases/v0.1.1/compositions.json](../../data/definition-releases/v0.1.1/compositions.json) | `cfdbde1066da73909e2bab6d9cf8de0111613a58105de0269b05f5b1a6eae183` |
| [data/definition-releases/v0.1.1/manifest.json](../../data/definition-releases/v0.1.1/manifest.json) | `5787c554fd7ee554b45742b6a3bb7df04ea25219f7903d14f43603793e6fcd4e` |
| [data/definition-releases/v0.1.1/metadata.json](../../data/definition-releases/v0.1.1/metadata.json) | `1fa26be4a27eed2733b6086e7dfff8cb2b90fa98dbbeef10082ee61df02ad5e8` |
| [data/definition-releases/v0.1.1/programs.json](../../data/definition-releases/v0.1.1/programs.json) | `98d8fc21073fb7f47a286bcc708aca5468d0cc5abef43e80525f0c5a3ce71d60` |
| [data/definition-releases/v0.1.1/provenance.json](../../data/definition-releases/v0.1.1/provenance.json) | `48be5d51fd0cfc08673c709f1a8c2e6961c6f939a920f07778277ed474fff378` |
| [data/definition-releases/v0.1.1/schedules.json](../../data/definition-releases/v0.1.1/schedules.json) | `2036622cc1918b9f4811e001290fba6e861013282fb408753e3bea4c51469b3f` |
| [data/definition-releases/v0.1.1/services.json](../../data/definition-releases/v0.1.1/services.json) | `da74ee593a86aa4388f8640661de16522be57a5997649b2f0f1847194f51660f` |
| [data/releases/v0.2.0/programs.json](../../data/releases/v0.2.0/programs.json) | `71076176fda99b940873fafce8a4bc89a4a72dad903b780b887e3d7d57173d92` |
| [data/releases/v0.2.0/residential_archetypes.json](../../data/releases/v0.2.0/residential_archetypes.json) | `8ad3be46b2e8631088c096c1e86f57cc6f4c2afa5201bfbc12c68ad4a5e6eecb` |
| [schemas/program-json-v2.schema.json](../../schemas/program-json-v2.schema.json) | `6319981a2a193e09adec4e0f507b09a3d16dd8369a9a228626006286e1fac863` |
| [scripts/program_json.py](../../scripts/program_json.py) | `570b4317b99939cd6eda11d37b20fc7345fd0ea7c5494ee902b24c4d49636de5` |
| [scripts/schedule_json.py](../../scripts/schedule_json.py) | `570b8c86c0d5a03d4c6046fd885a2ae9968a75b0cd5e287b6eaca968de9a0ffc` |
| [sources/program-json-defaults.json](../../sources/program-json-defaults.json) | `ddcd188e47badab1ca915c16b3c432a94d393742713c8a5bc6856f90495573b0` |
