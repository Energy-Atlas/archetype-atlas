# Program aggregation decisions and generator requirements

Recorded from the researcher's comments on 2026-10-06 and decisions on 2026-10-07. This replaces the initial
role-based worksheet: the decisions are organized by source building family,
without requiring an annotation-status vocabulary.

The [source-area tables](program-aggregation-evidence.md) provide the complete
per-template evidence. The [follow-up findings](program-aggregation-findings.md)
explain apartment variants, strip-mall scope and the recovered supermarket areas.

This is the fixed decision baseline for stage 1 (mixtures). Before implementing
stages 1–3, discuss stage 2 (catalogue redesign) with the researcher. Stage 3 is
the BEMGen handoff for plan generators, preset schema and the catalogue value
fetcher. The existing local handover is preparatory material, not a dispatch.

## Shared rules

- Keep every original source program available, with its source ID and provenance.
  Add a building-family suffix to consumer-facing names, such as `Corridor_Hospital`
  or `Office_HighriseApartment`; do not rename or overwrite frozen canonical IDs.
- Mixed programs are additional named definitions. Each recipe selects leaf
  programs from one exact building/template/family, with fixed weights derived
  from represented source floor areas. Do not average different standards or
  existing-stock and code/prototype families.
- Use three aggregation modes where the family calls for them: **SourcePrograms**
  (each original program), **DepartmentMixes** (specified subordinate groups),
  and **GeneralMix** (specified broad aggregate). These are program-composition
  modes, separate from BEMGen's existing geometric/zoning simplification levels.
  Families with fewer modes expose only the meaningful choices.
- Every family, available vintage and aggregation mode requires a corresponding
  BEMGen plan definition. One generator per family may select its definitions via
  optional Standard/Vintage and AggregationMode enums; avoid one component per
  version. The omitted-mode default should be the finest supported program mode.
  The default standard is **ASHRAE 90.1-2019**. Unsupported combinations must be reported, not replaced
  with another vintage or family.
- When an old template lacks a listed subordinate program, use the programs that
  actually exist and renormalize their source areas within that template's group.
  Record the actual membership; do not fabricate a missing row or zero value.
  If a group is empty, it is unavailable for that template.
- Source area ratios are generator defaults and recipe evidence. Fixed recipes
  and downstream geometry must agree on the intended program scope. Changing an
  adjustable plan ratio is an explicit scenario change, not an unnoticed change
  to a fixed preset. **Basement and attic programs are excluded from every mix,
  even when the source counts their floor area.** This includes named variants
  such as `WholeBuilding - Lg Office-basement`. Supply them separately as optional
  presets; do not place them automatically in generated plans. Users may prefer
  their own basement/attic treatment. Exclude other NC floor areas from mixing
  and retain their source background/volume definitions.
- At each mode, active programs must partition the eligible leaf programs:
  no dropped eligible leaves and no original leaf counted both individually and inside a
  mix. Compute a coarse mix from leaves, or multiply nested weights correctly;
  never sum an intermediate mix alongside its own constituents.
- Use the same source-area weights to blend **heating and cooling setpoint
  schedules pointwise**, and other compatible numerical program quantities.
  This is an intentional simplification whose error will be benchmarked in later
  steps. Do not require a representative thermostat choice, component controllers
  or extra thermal partitions before using a mixture. Preserve the unmixed
  source mode for comparison. A required unknown member value makes that mixed
  field unknown; do not average only the known values or interpret null as zero.
- For scheduled loads, blend the actual hourly density `sum(w_i*d_i*s_i(t))`;
  this is the area-weighted load, not the product of independently averaged
  densities and fractional schedules. Keep compatible SI bases and schedule
  calendars. Absolute/shared water and geometry-dependent infiltration still
  need their existing basis transformations; this does not introduce additional
  control-policy options or authorize filling missing source values.

## Family matrix

Names for mixes not explicitly named by the researcher below are descriptive
working names. Membership below incorporates the researcher's 2026-10-07 approvals.
Every mixture uses the global basement/attic exclusions above.
Programs not mentioned in a DepartmentMixes group remain individual.

| Family | SourcePrograms | DepartmentMixes | GeneralMix / broadest mode | BEMGen plan requirement |
| --- | --- | --- | --- | --- |
| FullServiceRestaurant | `Dining`, `Kitchen`; no mixture | Same two separate departments | No combined restaurant program requested | Fixed depth, parametric length, adjustable dining-depth fraction; dining default 72.727%, kitchen remainder; accept separate dining and kitchen presets |
| HighriseApartment | `Apartment`; optional distinct `Apartment_topfloor_NS`, `Apartment_topfloor_WE`; `Corridor`; opt-in `Corridor_topfloor`; `Office_HighriseApartment` | No mixture | No mixture | Apartment-based housing generator with explicit family/vintage selection and optional top-floor variants |
| Hospital | Every source program, suffixed `_Hospital`; basement optional | ER, ICU, food service, diagnostics/therapy and office groups below; OR and NurseStn individual | `General_Mixed_Hospital` plus separate corridor and lobby; basement optional and unmixed | Multi-floor generators for the first two modes; parameterized floor count and declared default room/program locations; a single-floor general-program plate for the broad mode |
| LargeHotel | Every source program, suffixed `_LargeHotel`; basement optional | Guest rooms; retail; kitchen+cafe+banquet; mechanical+laundry+storage; corridor variants each become the groups below | Eligible leaves except corridors and lobby become General; corridors mixed; lobby separate; basement optional | Hotel family with matching fine, department and general floor-plan definitions |
| LargeOffice | Existing whole-building office programs; retain explicit basement/data-centre/plenum variants | No new office mixture | No new office mixture | Reuse source office aggregates; preserve separately available source programs; do not infer a service-core breakdown from thermal core zones |
| MediumOffice | Existing `WholeBuilding - Md Office`; retain source plenum background | No new mixture | No new mixture | Office plan using the existing aggregate, without inventing a work-area/core energy decomposition |
| MidriseApartment | Same policy as HighriseApartment, names suffixed `_MidriseApartment` | No mixture | No mixture | Apartment and corridor presets replacing illustrative dwelling/corridor semantics in sourced configurations; optional top-floor variants |
| Outpatient | Every source program, suffixed `_Outpatient` | Approved surgery, diagnostics, clinical-support and office groups below | General aggregate excluding Hall, Hall_infil, Stair and Lobby; Reception included; basement/attic optional and unmixed | Multi-floor fine/department plans and a broad-program plate, analogous to Hospital |
| PrimarySchool | Every source program | Food: cafeteria+kitchen; Activity: computer room+gym+library | Everything except corridor becomes General; corridor separate | One school generator with vintage and mode enums; match each template's actual membership and ratios |
| QuickServiceRestaurant | `Dining`, `Kitchen`; no mixture | Same two separate departments | No combined restaurant program requested | Same two-department generator concept as full service, but default dining-depth fraction is 50% for this source |
| RetailStandalone | Every source program | Sales: front+core retail+point of sale, or available legacy retail+point of sale | Everything except `Back_Space` becomes General; back space separate | Retail family with source, sales-department and front/back plan modes; choose membership by actual template |
| RetailStripmall | Three distinct retail tenant aggregates | `Retail_Mixed_RetailStripmall`: type 1+type 2+type 3 at 25/25/50 source area shares | Same retail mixture; no additional broad mode needed | Strip-retail plan with three original tenant presets or their mixture; no internal atrium/corridor requirement |
| SecondarySchool | Every source program | Primary-school food/activity pattern, with additional activity uses addressed below | Everything except corridor becomes General; corridor separate | School generator with per-vintage definitions and mode enum |
| SmallHotel | Every source program, suffixed `_SmallHotel`; attic optional | Guest rooms, support, corridors, amenities, staff/office, vertical circulation; PublicRestroom individual | Eligible leaves except corridor variants and lobby, if present, become General; mixed corridor separate | Small-hotel-specific plan definitions; no automatic attic generation |
| SmallOffice | Existing `WholeBuilding - Sm Office`; retain attic background | No new mixture | No new mixture | Source aggregate office plan, as for other office families |
| SuperMarket | Every source program | Office+meeting; vestibule+bakery+deli+dining+produce; dry storage+electrical/mechanical+restroom; sales and corridor remain individual | Everything becomes `General_Mixed_SuperMarket` | Source, department and whole-program plans; source area defaults are recoverable, so no empirical fallback is needed |
| Warehouse | `Bulk`, `Fine`, `Office`, separately | `Storage_Mixed_Warehouse` = bulk+fine; office separate | No further mixture requested | Storage/office plan with source and mixed-storage modes |

## Exact memberships

### Hospital

| Mixed program | Leaf source programs |
| --- | --- |
| `ER_Mixed_Hospital` | `ER_Exam`, `ER_NurseStn`, `ER_Trauma`, `ER_Triage` |
| `ICU_Mixed_Hospital` | `ICU_NurseStn`, `ICU_Open`, `ICU_PatRm` |
| `FoodService_Mixed_Hospital` | `Kitchen`, `Dining` |
| `Diagnostics_Mixed_Hospital` | `Lab`, `PhysTherapy`, `Radiology` |
| `Office_Mixed_Hospital` | `Office`, `HospitalOfficeFlr1`, `HospitalOfficeFlr5` when present |
| `General_Mixed_Hospital` | Every eligible counted-floor source program except `Corridor`, `Lobby` |

The 2026-10-07 request to align Hospital with Outpatient supersedes the earlier
cross-functional `Facility_Mixed_Hospital`. Food service and diagnostics/therapy
are now distinct; office variants are grouped as in Outpatient. Keep `OR` as the
individual surgery program and `NurseStn` as the individual general clinical-support
program: each category has only one remaining source leaf, so no one-member mix
is needed. ER/ICU nurse stations remain inside ER/ICU and are not counted again.
`PatRoom` remains individual. At GeneralMix, corridor and lobby remain separate;
basement is available only as an optional unmixed preset. Do not place department
mixes alongside General when it already contains their leaves.

### LargeHotel

| Mixed program | Leaf source programs |
| --- | --- |
| `GuestRooms_Mixed_LargeHotel` | `GuestRoom`, `GuestRoom2`, `GuestRoom3`, `GuestRoom4`, `GuestRoom8` when present |
| `Retail_Mixed_LargeHotel` | `Retail`, `Retail2` when present |
| `FoodService_Mixed_LargeHotel` | `Kitchen`, `Cafe`, `Banquet` when present |
| `Support_Mixed_LargeHotel` | `Mechanical`, `Laundry`, `Storage` when present |
| `Corridor_Mixed_LargeHotel` | `Corridor`, `Corridor2` when present |
| `General_Mixed_LargeHotel` | Every eligible counted-floor leaf except corridor variants and `Lobby` |

Basement is excluded from all hotel mixtures even when counted by the source.
It remains an optional separate preset, with no default basement plan requirement.

### SmallHotel

Apply the same group intentions using its actual labels:

| Mixed program | Leaf source programs / remaining interpretation |
| --- | --- |
| `GuestRooms_Mixed_SmallHotel` | `GuestRoom`, `GuestRoom123Occ`, `GuestRoom123Vac`, `GuestRoom4Occ`, `GuestRoom4Vac` when present; these are an explicitly requested within-template composition, not an unannounced merge of stock variants |
| `Support_Mixed_SmallHotel` | `Mechanical`, `Elec/MechRoom`, `Laundry`, `Storage`, `Storage4Front`, `Storage4Rear` |
| `Corridor_Mixed_SmallHotel` | `Corridor`, `Corridor4` |
| `Amenities_Mixed_SmallHotel` | `Exercise`, `Meeting`, `GuestLounge` |
| `StaffOffice_Mixed_SmallHotel` | `StaffLounge`, `Office` |
| `VerticalCirculation_Mixed_SmallHotel` | `Stair`, `Stair4`, `ElevatorCore`, `ElevatorCore4` |
| `General_Mixed_SmallHotel` | All eligible counted-floor leaves except corridor variants and `Lobby` if present |

There is no extracted SmallHotel retail/kitchen/cafe/banquet group to fabricate.
The researcher approved these memberships on 2026-10-07. The additional groups
separate guest amenities, staff/office uses and vertical circulation.
Keep `PublicRestroom` individual at DepartmentMixes;
it is the remaining public support use rather than part of the storage/mechanical
group.
Stairs/lift cores remain separate from Corridor at DepartmentMixes. Under the
requested broad hotel rule they join General; only corridor variants and a
source `Lobby`, if present, are excluded in addition to all basement/attic programs.
`GuestLounge` is not automatically a lobby.
Only programs present in the selected template participate in each group.

### Outpatient

The following groups were approved on 2026-10-07. Outpatient has no `ER_*` or
`ICU_*` source groups; use its own source leaves for the corresponding departments.

| Mixed program | Leaf source programs |
| --- | --- |
| `Surgery_Mixed_Outpatient` | `OR`, `Anesthesia`, `PACU`, `PreOp`, `ProcedureRoom` |
| `Diagnostics_Mixed_Outpatient` | `Exam`, `MRI`, `MRI_Control`, `Xray`, `PhysicalTherapy` |
| `ClinicalSupport_Mixed_Outpatient` | `CleanWork`, `Soil Work`, `NurseStation`, `MedGas`, `BioHazard` |
| `Office_Mixed_Outpatient` | `Office`, `Conference`, `OutpatientFloor2Work` |
| `General_Mixed_Outpatient` | All eligible counted-floor leaves except `Hall`, `Hall_infil`, `Stair`, `Lobby` |

All remaining leaves stay individual at DepartmentMixes. `PreOp` and
`ProcedureRoom` join surgery; exam and imaging join Diagnostics. `Reception`
joins General at the broad mode. Basement/attic are optional unmixed presets in
all modes. No groups are named ER/ICU where those source programs do not exist.

### PrimarySchool and SecondarySchool

| Mixed program | Leaf source programs |
| --- | --- |
| `FoodService_Mixed_PrimarySchool` | `Cafeteria`, `Kitchen` |
| `Activity_Mixed_PrimarySchool` | `ComputerRoom`, `Gym`, `Library` when present |
| `General_Mixed_PrimarySchool` | All eligible counted-floor leaves except `Corridor` |
| `FoodService_Mixed_SecondarySchool` | `Cafeteria`, `Kitchen` |
| `Activity_Mixed_SecondarySchool` | `ComputerRoom`, `Gym`, `Library`, `Auditorium`, `Gym - audience` when present; extension approved 2026-10-07 |
| `General_Mixed_SecondarySchool` | All eligible counted-floor leaves except `Corridor` |

The broad school mix includes `Lobby`, unlike the broad Hospital mix. Old
versions may have fewer leaf programs; the source tables define availability.
Preserve a per-template recipe and plan definition even when two geometries or
ratios happen to agree, since energy properties/schedules can still differ.

### RetailStandalone

| Mixed program | Leaf source programs |
| --- | --- |
| `Sales_Mixed_RetailStandalone` | Available `Front_Retail`, `Core_Retail`, `Point_of_Sale`; legacy `Retail` instead of front/core where present |
| `General_Mixed_RetailStandalone` | All eligible counted-floor leaves except `Back_Space` |

In this frozen selection, the legacy `Retail` row persists through **90.1-2007**;
front/core retail appear in **90.1-2013 and 2019**. Use actual row availability,
not a hard-coded "pre-2007" cutoff. `Entry` remains individual at DepartmentMixes
and joins General at the broad mode.

### SuperMarket and Warehouse

| Mixed program | Leaf source programs |
| --- | --- |
| `Office_Mixed_SuperMarket` | `Office`, `Meeting` |
| `CustomerServices_Mixed_SuperMarket` | `Vestibule`, `Bakery`, `Deli`, `Dining`, `Produce` |
| `Support_Mixed_SuperMarket` | `DryStorage`, `Elec/MechRoom`, `Restroom` |
| `General_Mixed_SuperMarket` | Every eligible counted-floor leaf, including `Sales` and `Corridor` |
| `Storage_Mixed_Warehouse` | `Bulk`, `Fine` |

`Sales` and `Corridor` remain individual in SuperMarket DepartmentMixes because
they were not included in the specified subordinate groups. Warehouse `Office`
remains individual at both levels.

## BEMGen interface and organization notes

The ignored [local handover](../../build/handovers/program-aggregation-bemgen.md)
contains the family requirements and findings for a BEMGen agent. It is guidance
for future BEMGen work; BEMGen is read-only from this task.

- Add separate residential and commercial plan-generator tabs. Apartment
  families belong with residential plans; source classification must remain
  explicit even though their energy rows come from the commercial Standards
  collection. Keep generic preset/data-fetch components reusable.
- Standard/Vintage and AggregationMode are optional typed inputs on family
  generators, with one selected combination recorded in plan provenance.
- Hospitals and outpatient plans need a stack of potentially different floor
  definitions from one generation call, with floor count parameterized, analogous
  to the existing terraced-housing mechanism. Declared reference layouts/program
  locations are defaults, not assertions about all real buildings.
- Do not globally rename every existing enum or discard unrelated empirical
  presets merely to replace illustrative dwelling/corridor inputs. Expose sourced
  Apartment/Corridor selections with explicit high-/mid-rise family metadata and
  retain optional top-floor presets. Names alone are not matching semantics.
- Strip-mall plans use retail tenants or their approved mixture. There is no
  internal atrium/corridor component to develop for this family.

## Decisions confirmed on 2026-10-07

The researcher approved area-weighted setpoints as an intentional simplification,
the Outpatient/SmallHotel/SecondarySchool groups above, the strip-retail mixture,
90.1-2019 as the default, and universal optional/unmixed basement and attic presets.
Hospital has been aligned with the functional Outpatient groups where its leaves
permit. No additional human decision is pending on these points. Numerical weights
use unrounded source areas; source-reported and simplified meanings remain distinct.
Mixed energy presets still require implementation and publication; this document
records the approved specification, not an already changed delivery contract.
