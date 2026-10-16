# Foundation/ground within construction suites — implementation plan

> **For agentic workers:** The owner approved this revised plan for implementation on 2026-10-16. Use `superpowers:executing-plans` task by task. Keep each method parameter authoritative in one location, retain ordinary unified simplifications, and report the small set of physically necessary native multi-assignment exceptions. Do not infer additional assumptions from blank comments.

**Status:** Implemented locally, 2026-10-16; final branch review and owner release review gate apply. Approved for implementation, 2026-10-16. D1–D4 and the five architectural clarifications are accepted, with the two execution constraints below. Execute locally task by task; BEMGen remains view-only and publication remains a later gate.

**Goal:** Extend each detailed and unified construction suite with its source-supported foundation/ground specification, including foundation-dependent interfaces and the instructions needed to resolve it against a generated BEM and site.

**Architecture:** One Construction Suite remains the public selection and delivery unit. GroundFloor, FoundationWall, FloorOverFoundation and RimJoist reuse its existing component/assignment, assembly/material and provenance structures. The `foundation_ground` section contains only foundation configuration, ground-transfer methods, required geometry and method-specific parameters. Existing suite/climate selection also selects its foundation content; consumers map interfaces using the existing assignment rules and reject unsupported configurations. Internal storage retains full recovery inventories and audit evidence without adding a second public suite, component registry or matching system.

**Tech stack:** Python/jsonschema and the existing checksum-locked Standards/ResStock/OpenStudio Ruby recovery tools. BEMGen owns geometry resolution, Grasshopper integration and IDF writing.

**Spec / planning brief:** The owner's 2026-10-16 request, acceptance of D1–D4, and subsequent five revisions: reuse existing structures; compact public JSON; ordinary suite/climate selection and interface assignment; preserve native ground recipes in unified; retain the coverage denominator while distinguishing supported absence from missing physics. ADRs 0020–0026 supply the existing construction, approximation and mass-accounting constraints. This changes ADR 0020's delivery boundary prospectively; its historical above-ground release remains valid and immutable. Section 4 records the accepted decisions rather than requesting them again.

## Global constraints

- Each method parameter has one authoritative executable location. Assemblies own F/C factors; materials own layer/insulation/soil properties; `foundation_ground` owns coupled Kiva placement, initialization and solver/environment configuration without copying material physics. Internal original-value evidence is not another executable parameter source.
- Ordinary unified construction components retain their existing simplified representation. Multiple native foundation assignments are exceptions only where physical equivalence/homogenization is unjustified; deduplicate equivalent recipes and warn with the affected suites/roles and reasons in the summary.

- Baseline: `construction-delivery-2026-10-16`, commit `0a7b86fd5cda8dd990d0fed1cfdbb4e31d580801`; branch `codex/foundation-ground`.
- Preserve all 177 suites and 3,320 current supported construction contexts: 136 commercial suites / 3,273 contexts and 41 residential fixtures / 47 contexts.
- Detailed 2.1.0, unified 1.2.0, shared mass 1.0.0 and their frozen artifacts remain unchanged. New contracts are versioned separately.
- Keep detailed and unified as two complete, separate JSON exports. Keep their current above-ground data, source rules, accepted equivalents, error reports and fixed ACH.
- Program and system JSON remain independent. No schedule-generator, systems, broad CI optimization or annual construction-error experiment belongs to this work.
- All extracted physics require source revision, locator, SHA-256, original value/unit, SI transformation, extraction date and interpretation. Null is unknown, never zero.
- Retain full extraction provenance and source inventories internally. Public exports reuse existing provenance references and include only execution inputs and the evidence needed for reproducibility; do not embed recovery logs, raw source inventories or detailed validation reports by default.
- Retain stock versus code/prototype distinctions. Do not promote a stock prevalence choice into a physical compatibility rule.
- Climate applicability remains the current ASHRAE label/group metadata. Weather/site data are simulation inputs; add no EPW-location catalogue axis.
- Apply the suite's selected climate/template/reference context to foundation recipes and parameters through the existing selector/export path. No independent foundation filter, selector, matching service or public compatibility object is introduced.
- Put all four foundation roles in the existing top-level `components` structure and reuse the existing assembly/material/evidence structures. `foundation_ground` must not contain another `components`, material, assignment or provenance registry.
- Geometry requirements are schema-controlled metadata inside the selected suite. Do not reintroduce `required_bindings`, `deferred_scope`, standalone space-type suites or one suite per surface role.
- Actual footprint, exposed edges, grade, depths, foundation-zone topology and adjacency belong to BEMGen. Source reference geometry supports derivations; it does not prescribe consumer geometry.
- Unified material weighting stays precomputed from source archetypes. Actual geometry instantiates the selected ground method; it does not trigger geometry-specific material refitting/reblending.
- `D:\BEMGen` and its worktrees are view-only. A handover can describe changes; this plan does not authorize edits there.
- Keep focused local validation during development. Site publication is a later, explicit gate through protected `main`; do not rebuild programs unnecessarily.

## Review focus

1. A top-floor apartment or ambient/pier fixture must not acquire an invented soil-contact slab when used on incompatible geometry. Task 1/4 tests distinguish supported absence from missing physics without adding compatibility objects.
2. A source-labelled “Adiabatic” material must not become a zero-flux boundary merely because of its name. Task 2 tests actual construction type, finite resistance and final boundary.
3. Rezoning must not turn internal zone edges into exposed foundation perimeter. Task 4/5 tests preserve external edge totals and handle core regions explicitly.
4. Global ground-temperature/Kiva settings must not silently conflict or be replaced with a different method's settings. Task 3/5 tests fail on incompatible model-wide requests.
5. Ground slabs, rim joists and floor-over-foundation interfaces must not be counted again in ordinary interior-mass restoration. Task 4/5 tests enforce exclusive ownership and unchanged historical budgets.

## 1. Source coverage verified for this plan

This is a **static evidence and source-code audit**, not a new ready-release receipt. Candidate selection is not proof of the construction finally assigned by the native workflow. No native model recovery or simulation was run for this plan.

### Commercial catalogue

| Evidence population | Verified coverage | Interpretation |
| --- | ---: | --- |
| Historical ground elements | 592: 414 floor, 178 wall | Broader source library, not 592 building suites |
| Corrected target categories across that library | 354 F-factor; 113 C-factor; 64 recovered layered-U; 59 targetless; 2 generic experimental recipes | These categories sum to 592. The historical C-factor label is wrong for some U-based and targetless rows |
| Published commercial suites with ground-floor candidates | 136/136 | All 3,273 commercial contexts have exactly one climate-matching building-default candidate |
| Active floor candidates | 204 distinct IDs | 177 F-target records and 27 targetless records; not 204 different physical foundations |
| Commercial contexts with F-target candidates | 3,147/3,273 | Target available; final caller/boundary/geometry still need closure |
| Targetless active floor contexts | 126 across six suites | SmallDataCenterLowITE and SmallDataCenterHighITE, each 90.1-2007/2013/2019 |
| Published suites with underground-wall candidates | 124/136 | 3,021/3,273 contexts; 127 distinct IDs: 95 C-target and 32 recovered layered-U records |
| No underground-wall candidate | 12 suites / 252 contexts | All four small/large, high/low-ITE data-centre types in those three standards. This is an unsupported basement possibility, not proof the current source buildings are missing necessary walls |
| Ground-contact ceiling selector | 0 active building suites | Buried roofs/earth-covered ceilings are outside the demonstrated source coverage |

The selected building-default floor recipes have three names: carpeted 6-inch slab, carpeted 8-inch slab, and `Adiabatic GroundContactFloor`. The known selected F targets span **0.7338315–1.2634363 W/(m K)**, with eight distinct values. Selected C targets span **0.3577306–6.4732202 W/(m² K)**, with five distinct values. These are source targets, not achieved whole-ground U-values.

Those counts describe building defaults. Among the 47 embedded former space-type sets, 16 have different floor selectors and 20 have different wall selectors from their matching building parent; ten `Any` scopes have no same-named building parent. Selector differences are not necessarily differences in the final assigned physics. The source prototype's explicit ground assignments can supersede these defaults.

The existing cached geometry/mass recovery covers 129 commercial references. At its **pre-construction** stage, 118 contain `Ground` floors and ten contain `Ground` walls. Sixteen references also contain `OtherSideCoefficients` surfaces: **14 floor faces and 90 wall faces**. Eleven references have no literal `Ground` floor but do have that other-side path. Therefore a Ground-only scan misses real source foundation paths. These are raw face counts, before multiplier or physical-area interpretation; they are not final IDF boundary counts.

### Residential fixtures

The selected stock-option labels include 18 slab, eight vented crawlspace, seven heated basement, four ambient, three unheated basement and one unvented crawlspace. Use the **effective source-workflow configuration** instead:

| Effective configuration | Fixtures | Foundation work |
| --- | ---: | --- |
| Slab-on-grade | 14 | Slab, edge/under-slab insulation and soil coupling |
| Conditioned basement | 7 | Foundation walls/slab/rim joists and conditioned-host semantics |
| Vented crawlspace | 5 | Walls/slab/rim joists, floor interface and crawlspace air exchange |
| Unconditioned basement | 3 | Walls/slab/rim joists, floor interface and unconditioned host |
| Unvented crawlspace | 1 | Walls/slab/rim joists, floor interface and source air-exchange assumptions |
| Above another apartment | 7 | No direct ground contact; retain ordinary inter-dwelling interfaces |
| Ambient/open underside | 4 | No soil-contact assembly; retain applicable exposed-floor/underbelly semantics |
| **Total** | **41** | **30 with direct foundation elements; 11 without them** |

The current above-ground recovery deliberately deferred **45 slab objects, 78 foundation-wall objects, 78 rim-joist objects and nine floor-over-foundation objects** across those 30 fixtures. Multiple slab objects may belong to one fixture or different hosts, including a garage. These are source-object counts, not 45 independent slab variants. Actual layer/insulation/Kiva recipes have not yet been exported for them.

Seven selected stock foundation labels are superseded by `Above Apartment` after unit-position processing. A top/middle apartment fixture is not a whole apartment-building foundation specification. Do not copy its original Slab/Crawlspace option onto a generated whole building.

### What these counts establish

There is enough pinned evidence to **target a combined specification for every current suite in its supported source conditions**. There are currently **zero published suites containing the proposed executable foundation extension**. A 100% ready-coverage forecast is not yet defensible: exact caller behavior, environment policies and interface physics remain to be recovered. The acceptance denominator stays all 177/3,320. The internal readiness report must distinguish:

- **Executable, contact present:** the applicable source ground physics is complete.
- **Source-supported no ground contact:** the source unit/configuration legitimately has none. Retain it in coverage with an explicit reason and the existing component absence disposition; this is a complete supported case, not missing physics.
- **Blocked, executable physics missing:** the source configuration requires a recipe or parameter that has not been recovered. It remains in the denominator and prevents a 100% completion claim.

The three context counts sum to 3,320; report suite-level totals against 177 as well. A consumer requesting a basement or soil-contact slab on an otherwise complete no-contact suite is an unsupported conversion request, not a missing source recipe to fabricate and not a reason to remove that suite from coverage. These are internal reporting distinctions, not a new public compatibility/readiness object.

This is not evidence for arbitrary cross-combinations of slab, crawlspace, basement and buried roofs with every suite. ResStock contains wider source options/sample cases, but their full compatibility matrix has not been audited or approved for this catalogue.

## 2. Revised combined contract and ordinary suite assignment

### 2.1 Public structure

Extend the existing Construction Suite structures in both complete documents. The new roles do not get a separate foundation component registry:

| Existing location | Foundation extension |
| --- | --- |
| `components` | Add GroundFloor, FoundationWall, FloorOverFoundation and RimJoist with the existing target, assignment and disposition conventions |
| `assemblies` / material resources | Store the selected physical recipes alongside the existing assemblies. Extend the assembly model discriminator for native F/C/Kiva semantics; do not fabricate ordinary layers for those methods |
| Assignment fields | Reuse `assembly_id`, `when`, `geometry` and evidence references to map foundation interfaces and hosts. No foundation-specific rule language |
| Existing evidence/provenance structures | Use the representation's current evidence/provenance conventions and the same selected suite/context identity; no nested evidence registry |

Reserve `foundation_ground` for:

| Content | Purpose |
| --- | --- |
| Foundation configuration | Effective foundation/contact type and required thermal hosts; express source-supported absence without inventing contact |
| Ground-transfer methods | F-factor, C-factor, layered ground-temperature, Kiva or source-proven adiabatic instructions associated with existing assembly references |
| Required geometry | Typed SI area, exposed perimeter, grade/depth and grouping operands required to instantiate the selected method |
| Method-specific parameters | References to assembly F/C values and insulation/soil materials; Kiva placement/settings, boundary-temperature resolution and initialization inputs; identify model-wide versus per-foundation parameters |

An ordinary component assignment references its assembly and, where needed, a ground method. It creates no second recipe identity, component target or assignment precedence. Layered floor/rim-joist materials remain in the ordinary assembly/material locations. Ordinary assignment geometry remains there; the foundation section adds only the operands required by ground transfer, without duplicating values.

### 2.2 Compact public payload

**Public:** selected executable component recipes, necessary assignment conditions, native transfer parameters, required geometry/environment inputs, source-supported absence reasons and existing provenance references sufficient to trace/reproduce the selection. Either JSON contains its complete executable material/recipe dependency closure.

**Internal:** full source object/geometry inventories, unused alternatives, raw HPXML/native captures, per-field recovery evidence, caller traces, exposure/weighting derivations and detailed validation reports. Preserve their hashes/locators in the pinned release and use the existing provenance mechanism where a reference is needed. Include inventory operands in public JSON only when a consumer actually needs them for execution or mass accounting; exclude audit-only operands by default.

The existing shared mass-accounting contract remains an execution requirement and is preserved. This change does not remove its necessary public quantities or introduce a second public foundation-mass ledger. Ground-related audit inventories stay internal; any additional public accounting operand must have a demonstrated consumer use and fit the existing accounting structure.

### 2.3 Simple selection and assignment

1. **Select the existing Construction Suite.** Its climate/template/reference selection filters foundation content through the same source selector/export path. For example, a 3B suite export contains its 3B-resolved foundation recipes/parameters, not an independent all-climate foundation catalogue to filter again.
2. **Map generated foundation interfaces to the existing applicable component assignments.** Recovered source explicit assignments and inheritance supply those rules. BEMGen provides the actual contact/host/grade geometry and required method operands; it does not choose another suite or run a separate foundation matching stage.
3. **Reject unsupported requests.** An interface with no applicable recipe, an incompatible required host, or missing method inputs produces a clear conversion diagnostic through the existing assignment/validation path. A supported absence uses the existing component disposition. No compatibility objects or separate matching service are added.

Effective residential unit position and commercial caller precedence are recovered **internally while preparing the suite**, not exposed as another consumer matching algorithm. Unused source alternatives remain internal evidence. BEMGen records realized operands and explicit overrides in its ordinary conversion diagnostics/provenance.

For F-factor and Kiva methods, exposed perimeter means **external exposed foundation edges**, not the sum of the boundaries of generated thermal zones. Preserve shared-edge cancellation, openings/walkout distinctions, foundation grouping and multipliers. Core slabs with no exposed edge need the native solver's supported handling; do not invent a positive perimeter to pass validation. The residential source's own minimum-perimeter convention must be retained as an explicit source approximation, not silently copied as a universal BEMGen repair.

### 2.4 Detailed versus unified

Detailed extends its existing component assignments and assembly/material registry with the applicable foundation recipes. Unified extends its existing component/assembly references with native ground recipes where homogenization is not physically justified. Both use the same selected suite/climate context, effective foundation configuration and method-specific execution parameters. Full source inventories and validation details remain internal.

Where one native ground recipe suffices, unified uses its existing single `assembly_id` component form. If physically distinct native cases require assignment rules, reuse the detailed assignment form for those foundation components rather than inventing a ground-specific selector/registry. Do not force a misleading single equivalent assembly just to retain the ordinary above-ground component shorthand. Retain only the native cases needed to execute the selected suite.

The existing three-layer approximation remains the above-ground default. **Do not force F/C-factor or Kiva ground heat transfer into that representation.** EnergyPlus F/C constructions are method-specific whole-construction objects; Kiva includes multidimensional soil/edge behavior. They are not ordinary layered U-value recipes. Native ground recipes remain executable in unified JSON through the existing component/assignment structures, including distinct native cases where required. Lack of a homogenized equivalent alone is not a readiness blocker.

The audited prototype `model_set_floor_constructions` selects its F target at building level; `model_set_below_grade_wall_constructions` uses its own building-category lookup. Their explicit assignments can remove an apparent need for GuestRoom/PatientRoom ground blending. Execute and verify these paths before choosing weights.

If heterogeneous active ground recipes remain: inventory true ground floor/wall areas and exposed edge lengths by source scope first. F-factor aggregation uses source exposed-perimeter contributions, not program floor-area fractions; layered assemblies use the appropriate source surface areas. C-factor or Kiva combinations also depend on depth, insulation topology and solver settings, so area-averaging their labels is insufficient. Preserve distinct native cases through existing assignments instead of forcing a blend. Report a blocker only if required executable physics or its faithful representation is missing, with measured examples for discussion. No new multidimensional fit, universal solver, extra-layer fitting, or floor-share fallback is approved here.

### 2.5 Physical mass and airflow ownership

Keep the current shared above-ground mass contract byte-identical. Maintain an internal foundation audit inventory to verify exclusive component ownership; do not embed it automatically in public JSON. Soil capacity and solver-generated fictitious F/C layers are not interior furnishing/restoration mass. An explicit ground slab never consumes the existing InteriorFloor restoration budget. A floor-over-foundation interface is counted once across its two faces, with any new restoration policy reviewed separately; do not quietly extend the current interior budget denominator.

Preserve current whole-enclosure fixed ACH. Foundation ventilation/interzone exchange, when needed for an unconditioned basement or crawlspace, is a separate source path and must not be added again as dwelling infiltration. Mechanical HVAC remains outside scope. Actual foundation air volumes and host temperatures remain consumer inputs to the declared method.

## 3. Gaps, reasons and closure proposals

| Gap | Why it matters | Proposed closure |
| --- | --- | --- |
| Final commercial caller and assignment closure | Table targets/default packages do not capture explicit F/C surface assignments, source basement fallback layers or boundary changes | Execute only the pinned construction/weather phases; capture before/after boundary, object type, source setter returns and material/target operands. Include `OtherSideCoefficients` paths and caller precedence |
| 59 historical targetless floors; 27 used IDs / 126 active contexts | “Adiabatic GroundContactFloor” was mislabelled as a C-factor wall. A large finite material resistance is not an adiabatic boundary | Preserve historical records; classify the newly executed construction correctly. Test both relevant constructor forms and the final prototype caller. No invented F/C factor or zero-U interpretation |
| 64 recovered layered-U ground records | Achieved layers exist, but a U target does not specify the soil-side boundary or complete assembly behavior | Preserve target/achieved values, source films and exact layers; recover the actual boundary and monthly temperature policy. Do not label U as C or add soil twice |
| Residential layer/Kiva closure | Current source choices and element IDs omit native foundation materials, edge insulation, depth relationships, Kiva settings and initialization | Extend the reviewed HPXML harness with only foundation construction/default phases. Capture complete physical materials, insulation geometry, ground settings, initial-temperature rule and source approximation flags |
| Unconditioned foundation thermal hosts and airflow | A vented crawlspace, sealed crawlspace and unconditioned basement have different thermal/air boundaries; none is simply outdoor air or fixed-temperature soil | Export required host topology and the pinned venting/leakage/exchange rules. Require BEMGen support for that host/coupled model; no invented constant host temperature |
| Reference exposure/depth data | Current frozen support profiles include above-ground exposures but no internal ground exposure/perimeter profile. Raw cache has areas/boundaries but no edge vertices/perimeters | Add an internal ground-support profile with footprint edges, grade/depth, host, source scope and multipliers. Keep previous profiles immutable. Do not estimate perimeter shares from program floor shares |
| Unsupported geometry/context combinations | Twelve data-centre suites lack underground-wall selectors; seven apartment fixtures and four ambient fixtures have no direct soil-contact element; no active buried-roof selector | Use existing component dispositions and applicable assignments. Reject an unsupported interface/configuration through the normal conversion path; do not introduce a compatibility object or silently attach generic walls/slabs |
| Soil and ground-temperature policy | Source native defaults, weather-derived boundaries and BEMGen's existing indoor-minus-2°C policy are distinct. Climate alone does not determine soil | Apply accepted D3: ship reproducible method-specific policies and source defaults, with consumer weather/site inputs and explicit override provenance |
| Unified native ground representation | Different active methods, depths and insulation positions cannot be made equivalent by averaging U, F or C indiscriminately | Preserve complete native recipes and reuse existing assignments for distinct cases. No homogenization is required for readiness; escalate only missing physics or a case that cannot be represented faithfully through those structures |
| Public payload scope | Full recovery inventories, all-climate candidates and validation traces would duplicate internal evidence and make ordinary exports bulky | Project the selected suite/climate's executable resource closure using existing component/provenance structures. Keep raw inventories and validation details internal; test that none leak into public JSON unless explicitly required for execution/reproduction |
| Consumer capability and versioning | Current BEMGen main writer targets EnergyPlus 26.2 but has a layered GroundFloor and BuildingSurface temperatures, not a demonstrated native F/C/Kiva path | Prepare a separate BEMGen handover for method dispatch, typed geometry, new IDF classes, boundary/environment handling and unsupported-input diagnostics. Test source recovery under pinned OpenStudio 3.10 and consumer syntax separately against 26.2 |

Broader conditions not demonstrated by this audit include arbitrary foundation-type substitutions, conditioned crawlspaces, mixed slab/basement/stepped foundations, party foundations between differently conditioned hosts, earth-covered roofs and highly irregular below-grade geometry. The upstream code has some relevant branches (including walkout handling), but that is not a completeness certificate for the 177-suite release.

## 4. Accepted decisions and review status

D1–D4 and the revised plan are **accepted by the owner for implementation**, with the two execution constraints in Global constraints. Comment areas below are retained for corrections, not renewed approval requests. Blank comments authorize no additional assumptions or scope.

### D1 — Preserve native ground methods in both exports

**Accepted, with revision:** Carry source-backed F/C-factor, layered ground and residential Kiva methods through the combined contract using the existing component/assignment, assembly and provenance structures. Keep native F/C/Kiva recipes in unified whenever homogenization is not physically justified; do not impose the above-ground three-layer fit. Reserve `foundation_ground` for configuration, methods, required geometry and method-specific parameters. A universal ordinary-layer floor would be a new scientific approximation and would not reproduce Kiva edge/soil behavior.

**Review comments:**

<!-- decision:D1:begin -->
Accepted by owner with architectural revisions, 2026-10-16; revised plan subsequently approved for implementation.
<!-- decision:D1:end -->

### D2 — Limit initial readiness to source-supported foundation conditions

**Accepted, with revision:** Complete all current suites for their demonstrated source conditions. Keep the denominator at 177 suites / 3,320 contexts and distinguish supported absence from missing executable physics. Select the ordinary suite/climate context, apply its existing component assignments and reject unsupported BEMGen foundation interfaces/configurations. Do not synthesize a whole-building foundation from an above-apartment fixture or add a separate matching system/compatibility object. Extending every suite to every foundation type is outside this first completion.

**Review comments:**

<!-- decision:D2:begin -->
Accepted by owner with architectural revisions, 2026-10-16; revised plan subsequently approved for implementation.
<!-- decision:D2:end -->

### D3 — Use method-specific source/environment policies

**Accepted, with revision:** Preserve recovered source soil defaults and initialization rules, with an explicit site override path. Ground-temperature rules use the consumer's actual weather or declared monthly boundary input where required, rather than applying the fixed-ACH reference calendar/climate or indoor-minus-2°C universally. Include only method parameters and reproducibility references needed in public JSON; retain raw fallback/caller evidence internally. Missing required environment data blocks instantiation. Foundation material/parameter selection follows the suite's existing climate context; consumer weather does not create a second catalogue filter.

The Standards weather helper uses STAT-derived lagged monthly air temperatures for FC when available and has reference-climate and generic BuildingSurface fallbacks. Capture these branches internally; setting BuildingSurface temperatures does not supply FCfactorMethod temperatures. Specify a valid per-method boundary resolution order; any newly required numerical fallback must be discussed using recovered cases. Existing BEMGen legacy/test-ground behavior stays on its existing path; native Atlas import gets method dispatch through the selected construction assignments.

**Review comments:**

<!-- decision:D3:begin -->
Accepted by owner with architectural revisions, 2026-10-16; revised plan subsequently approved for implementation.
<!-- decision:D3:end -->

### D4 — Preserve unconditioned foundation hosts

**Accepted, with revision:** Deliver basement/crawlspace recipes through the existing components and assignments, with the thermal-host and source air-exchange operands needed for execution. BEMGen supplies the corresponding unconditioned host or an explicitly supported coupled model and reports unsupported input when it cannot. Do not substitute outdoor air, a constant temperature or a hidden effective-floor approximation. Source-host inventories and recovery diagnostics remain internal; no independent host-matching object is added.

Conditioned foundation hosts obtain their controls/program from the consumer's normal program assignment. Construction describes host/contact requirements without embedding a second program or HVAC definition.

**Review comments:**

<!-- decision:D4:begin -->
Accepted by owner with architectural revisions, 2026-10-16; revised plan subsequently approved for implementation.
<!-- decision:D4:end -->

No decision is needed yet on an imputed perimeter weighting, a universal soil value or extra equivalent layers: none is proposed. If source execution exposes a case requiring one, report its affected contexts and options before implementing it.

## 5. Implementation sequence after revised-plan review and execution authorization

The file/interface names below are proposed extension points. No historical self-hashed generator or release is edited in place.

### Task 1 — Freeze the internal ground-source and dependency census

**Files:** Create `scripts/construction_foundation_recovery.py`, `tests/test_construction_foundation_recovery.py`, and `data/construction-inputs/foundation-source-v1.json`. Add the accepted boundary ADR, proposed `docs/adr/0027-combined-construction-foundation.md`.

**Interfaces:** `inventory_foundation_sources(definitions, contexts, geometry) -> dict` produces internal suite/context/source-role links and census dispositions for Task 2. Its output separates selected stock option from effective configuration and table candidate from executed assignment; it is not a public compatibility object.

- [x] Test the fixed 177/3,320 denominator, the 136 floor/124 wall selector counts, all seven effective residential categories, absence versus unknown, and the eight already unsupported source contexts remaining evidence-only.
- [x] Test that executable-contact, source-supported-no-contact and missing-physics context counts sum to 3,320 without counting missing physics as absence or dropping no-contact suites.
- [x] Run the focused test and observe failure before adding the inventory implementation.
- [x] Pin every new source file/caller and runtime dependency; preserve original identities and historical source notices. Normalize the census with per-field evidence and input hashes.
- [x] Verify every context has a disposition; enumerate missing dependencies instead of narrowing eligibility. Reconcile the planning counts above and document any source-execution correction.
- [x] Inspect staged diff, run `python -m scripts.audit --staged`, and commit a reversible census/ADR unit with neutral agent identity and model trailer.

### Task 2 — Recover native physics and final assignment paths

**Files:** Extend the new Python adapter; create `scripts/recover_commercial_foundations.rb`, `scripts/recover_residential_foundations.rb` and corresponding tests. Do not edit frozen recovery scripts to change their old outputs.

**Interfaces:** `normalize_foundation_execution(native: dict, source_receipts: dict) -> dict` yields final method, materials, boundary instructions, typed geometry/environment operands and host rules. Source execution is opt-in; ordinary export later consumes frozen output.

- [x] Test Medium Office first: source F target, assigned object type, area/perimeter operands and boundary; then a residential slab and vented crawlspace.
- [x] Observe the focused failures, implement construction-only native captures, and compare normalized operands/materials with source objects and setter outcomes.
- [x] Cover SmallDataCenter targetless finite-R behavior; legacy U-based walls; Hospital/LargeHotel/LargeOffice other-side paths; Tall/SuperTall walls; conditioned/unconditioned basement and no-contact residential cases.
- [x] Recover source venting/exchange and Kiva initial-temperature dependencies without sizing HVAC, expanding annual schedules or running the whole source workflow. Capture source minimum/perimeter approximations explicitly.
- [x] Run `python -m unittest tests.test_construction_foundation_recovery -v`; require complete active physics, boundary and dependency evidence per declared model, or emit a concrete blocker report.
- [x] Audit and commit the source recovery unit.

### Task 3 — Extend the existing construction structures and ground-method metadata

**Files:** Create `scripts/construction_foundation.py`, `schemas/construction-foundation-ground-v1.schema.json`, `tests/test_construction_foundation.py`, and `docs/construction-foundation-ground-v1-contract.md`.

**Interfaces:** `prepare_foundation_extension(source_context: dict, recovered: dict, profiles: dict, representation: str) -> dict` produces extensions to the representation's existing component/assignment, assembly/material and evidence/provenance fields, plus the restricted `foundation_ground` method metadata. `validate_foundation_extension(document: dict) -> None` validates those additions against the complete construction document and existing registries. The ground-method schema is an embedded schema fragment, not a standalone suite or component contract.

- [x] Test the four roles in the existing top-level `components`, normal assignment/assembly/evidence references, each native model's operands, source-proven absence/adiabatic and model-wide setting conflicts. Reject nested component/material/assignment/evidence registries or public compatibility objects inside `foundation_ground`.
- [x] Observe failures, implement SI/provenance/reference/physical validation and deterministic identities, then pass the tests.
- [x] Encode accepted D1–D4 and the owner's five revisions. Reuse existing assignment precedence and suite/climate selection; no new matching service. Keep source physics self-contained while raw inventories/recovery reports remain internal.
- [x] Test climate selection end to end: selecting the suite's climate filters both above-ground and foundation recipes/parameters, with no second foundation selector or all-climate foundation candidate collection in the consumer document.
- [x] Test public resource closure and compactness: include required execution parameters and reproducibility references; exclude audit-only source inventories, recovery traces and detailed validation metadata. Preserve full evidence internally and the existing public mass-accounting operands required for execution.
- [x] Reject a source blocker mislabeled as a consumer geometry requirement. Keep weather/grade inputs separate from missing material properties.
- [x] Audit and commit contract/schema/validator together.

### Task 4 — Add ground support profiles and both combined exports

**Files:** Create `scripts/construction_foundation_profiles.py`, `scripts/construction_foundation_export.py`, `tests/test_construction_foundation_profiles.py`, `tests/test_construction_foundation_export.py`; add new consumer schemas, proposed detailed **3.0.0** and unified **2.0.0**.

**Interfaces:** `build_foundation_profile(source_reference: dict) -> dict` builds internal derivation support. `compose_foundation_export(base_document: dict, extension: dict, representation: str) -> dict` merges Task 3's additions into the existing construction fields and adds only the restricted method metadata under `foundation_ground`. Both wrappers use the same selected suite/climate context and internal source inventory; the inventory is not embedded automatically.

- [x] Test footprint/shared-edge and zero-perimeter core cases, source multipliers, grade splits, supported absence versus requested unsupported interfaces, exclusive mass/interface ownership and rejection through the existing assignment path.
- [x] Observe failures, recover normalized internal support profiles and compose over the current exports. Detailed extends existing assignments; unified keeps native F/C/Kiva recipes where equivalent-layer homogenization is unjustified. Reuse the existing assignment form for native cases that cannot use its ordinary single-assembly shorthand.
- [x] Audit actual heterogeneous assignments before any blend. Reuse identical native recipes and preserve distinct native cases through existing assignments. Test that absence of an equivalent-layer fit does not block a complete native export. Escalate only missing executable physics or an unrepresentable required native case; do not average incompatible models.
- [x] Ensure no change to old base materials, equivalent fit errors, fixed ACH, program outputs, source mass budgets or old consumer schemas. New required ground semantics justify major consumer versions and explicit BEMGen version dispatch.
- [x] Run the focused new profile/export tests and current mass/export regression tests, then audit and commit.

### Task 5 — Freeze the combined delivery and focused validation

**Files:** Create `scripts/construction_foundation_release.py`, `scripts/validate_construction_foundation.py`, `tests/test_construction_foundation_release.py`, `data/construction-foundation-releases/v1.0.0/`, and paired examples under `docs/examples/construction-foundation-v1/`.

**Interfaces:** `export_pair(context_id: str, ...) -> tuple[dict, dict]`; CLI `python -m scripts.construction_foundation_release --check --examples`; validator `python -m scripts.validate_construction_foundation`.

- [x] Test manifest tampering, orphan contexts/resources, partial recovery, deterministic bytes, complete new exports and identical shared configuration/provenance across each pair.
- [x] Test that each standalone export contains executable selected resources only, uses the suite's climate selection, has no parallel foundation registry/compatibility object, and does not leak internal inventories or validation traces.
- [x] Observe failures, implement normalized internal storage and complete standalone exports. This internal release is an overlay/build artifact, not a separate public foundation-suite product.
- [x] Validate all 177 suites / 3,320 contexts with zero unresolved active source physics. Count source-supported no-ground-contact cases as supported completions with explicit absence reasons; count missing executable physics as blocked. Report unsupported external geometry requests separately. Keep the full denominator and verify the context-category sum.
- [x] Supply paired pilots for Medium Office, Warehouse, SmallDataCenter, a legacy basement, Tall/SuperTall, residential slab, conditioned basement, unconditioned basement, vented/unvented crawlspace, ambient and above-apartment cases. Reuse recipes to keep fixtures compact.
- [x] Check native object serialization and small local heat-transfer/initialization smoke cases for each active method, including core/perimeter and split-zone geometry. Compare F-factor steady-state `F × exposed perimeter` behavior where applicable; do not demand full annual parity or a systematic zoning-error study.
- [x] Pin the original source recovery runtime and separately validate target EnergyPlus 26.2 object fields/compatibility. Do not replace older source defaults with newer engine defaults silently.
- [x] Audit and commit the verified release unit only when the readiness gate is actually met.

### Task 6 — Prepare the BEMGen handover

**Files:** Prepare a new ignored packet and prompt under `build/local-handover/` and `build/local-plans/`; update tracked Atlas contract/examples/release notes. Never mutate previously pinned packets.

- [x] Include new schemas and paired examples, manifests/checksums, notices and a human-readable supported/unsupported-case table; do not add public JSON compatibility objects.
- [x] Specify extension of BEMGen's existing construction assignment path: consume the already climate-selected suite, map its four foundation roles, instantiate F/C/Kiva with actual geometry/environment inputs and reject unsupported cases. Include global-setting checks, hosts/airflow, grade ownership and mass accounting. Invalid imports must not fall back to an example envelope.
- [x] Require a separate BEMGen worker to implement/test importer, GH ports and IDF writing. Preserve its old legacy ground policy on the legacy path; imported native methods need their own valid environment objects.
- [x] State that successful Atlas schema/source validation is not successful BEMGen integration or simulation. Test acceptance and unsupported combinations must be reported by that worker.
- [x] Retain original-work and upstream licensing terms; copying a fixture packet does not grant an MIT relicensing permission.

### Task 7 — Site integration and later publication

**Files:** Update `scripts/construction_site.py`, `scripts/construction_equivalent_site.py`, `scripts/construction_site_refresh.py`, `website/assets/construction_core.js`, related smoke/Node tests and the construction guide.

- [x] Test both direct-copy buttons producing complete new-version documents; verify preview/copy parity and no source chooser or separate foundation download.
- [x] Add compact method/required-input and source-supported absence information to existing construction pages. Current climate/reference selection filters the foundation content in both exports; no independent foundation filter, matching UI or catalogue.
- [x] Use construction-only local refresh and focused desktop/mobile/browser checks. Check packet resource closure and size; no program/schedule regeneration unless a demonstrated dependency requires it.
- [x] Stop for release review. A later authorized PR/main deployment uses the repository's required checks, successful main-only Pages artifact and live verification. Do not run publication as part of this plan request.

## Local execution receipt — 2026-10-16

Tasks 1–7 are implemented locally. The fixed gate is 177 suites / 3,320 contexts:
3,308 contact, 12 supported absence, zero missing executable physics. All paired
schemas and focused physical/reference/ownership checks passed; 588 source
initialization probes and six pinned EnergyPlus 26.2 one-day cells passed.

Task 5 qualification: native numerical smoke verifies serialization and finite
short-run behavior, not steady-state F×perimeter flux or annual accuracy. Source
shared-edge cancellation/core handling are checked independently. The narrower
verification claim is recorded in construction-foundation-release-review.md.

Native unified exceptions are 20 residential suite/role entries, two assignments
each (15 GroundFloor hosts and five FoundationWall soil/non-soil boundaries).
Ordinary components remain simplified. Parameter ownership follows the latest
owner constraint and ADR 0027's refined coupled-method placement rule.

New local BEMGen packet: build/local-handover/bemgen-construction-foundation-v5,
18 paired examples, full schemas, SHA-256 manifest and notices. Prior packets
are unchanged. BEMGen code remains untouched; consumer integration remains open.
Construction-only refresh updated 177 pages and 3,320 contexts, with zero program
pages regenerated. Both direct-copy buttons retain the same selected context.
Local method and no-contact displays were checked at desktop/mobile widths.
Publication, push and CI/CD remain outside this execution; stop for owner review.

## 6. Source and audit locators

Pinned Standards revision: `c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907`. Relevant methods:

- `lib/openstudio-standards/prototypes/common/objects/Prototype.Model.rb`: `model_add_constructions`, `model_set_floor_constructions`, `model_set_below_grade_wall_constructions`; SHA-256 `9540fef6a67207a06ed3acf5eb4c5ff82c1dd583525be414807156d17a7a63bd`.
- `lib/openstudio-standards/standards/Standards.Model.rb`: `model_add_construction`, `model_add_construction_set`; SHA-256 `c88dada83a0e1a25db534917912766dcb2c451da8a0402befff1a16b3497f145`.
- `lib/openstudio-standards/constructions/modify.rb`: surface F/C setters; locally inspected SHA-256 `4ec16e16de4047d1d08cfb9345e161d4b342542f995d800a787881ae8c22d99b` (add its locked retrieval receipt during Task 1).
- `lib/openstudio-standards/weather/modify.rb#model_set_ground_temperatures`: STAT/FC and generic-temperature branches; locally inspected SHA-256 `4ee3064f883d0ea63f677d464daa731b8f874786bbbcd69e2ae2ae2c7e7ac196`. Supporting `weather/stat_file.rb` SHA-256 `9fd04dfae4bbd70be9de695efcb98a890f65dbe348e947bc2a8c3e6eb81e7ed8`. Add locked retrieval receipts for these and all newly called files during Task 1.

Pinned ResStock revision: `dd25369f41a83a0767aefeeac0b6f8a0b0edd649`, `resources/hpxml-measures/HPXMLtoOpenStudio/resources/`:

- `geometry.rb#apply_foundation_walls_slabs`, `apply_foundation_wall`, `apply_foundation_slab`; SHA-256 `652b6d5480e3a8ce09183753ec315830e54961b8d4d6d0fcc1495ffb45d609fd`.
- `constructions.rb`: foundation layers, Kiva creation/settings/initialization; SHA-256 `4d21db2a0b3242d3b6d8676c83f9fc88139ee90a2f2bdb847f5f13305672a2a7`.
- `defaults.rb`: foundation/site defaults; SHA-256 `863bc3d3699d0e321882fc4de8b01310592317c59e94f39c3855549b2866fbf6`.
- `materials.rb`: soil/material properties; SHA-256 `e89b718a14c48bd74f88efb21123845a719bdb4a03c40d037b9371eabba24992`.
- `airflow.rb`: foundation ventilation/leakage paths to close; SHA-256 `0af553977ea48a169f1ed4f19baecb92508c08367a466d6f2f95a840d0b3996b`.

The five residential file hashes were checked against the existing pinned receipts during this audit. Runtime/archive pins remain in `sources/runtime-lock.json` and the recovery manifests.

Catalogue/census inputs:

| File | SHA-256 |
| --- | --- |
| `data/definition-releases/v0.1.1/constructions.json` | `5b15d8a47b971a56024e2ad3d3c59829b964faabc647bf9581289896d0a3dab5` |
| `data/construction-inputs/source-v1.json` | `1aca792d65e66304e9d8ce7b918cdd17cee038ae24c18b25f61bffa164a4526a` |
| `data/construction-inputs/geometry-v1.json` | `66274536119e312f296abc05c98223e69f296c8560fff4670589216b4a581bf0` |
| `data/construction-inputs/residential-assemblies-v1.json` | `1163f41618296a464c31457a7255122655199402c7204c77686504034370619b` |
| `data/construction-releases/v2.0.0/catalogue.json` | `dceeb82b8461342ae9c5f4b35fbdc6a5f21f1618c2e0699f30d9ad16841f2998` |
| `data/construction-releases/v2.2.0/selection.json` | `fa035be9684888168aaa0d84ec7781b875a260646afa3adb6f9fbf094bdee7aa` |

The local planning census is retained at `build/foundation-ground-planning-audit.json`, with input hashes, context/candidate IDs and deferred residential object IDs. Its cached reference-boundary census is provisional recovery evidence, not a frozen release claim. Task 1 must provide the reproducible canonical replacement.

BEMGen compatibility inspection was read-only against its primary checkout on 2026-10-16: `src/Lod.Export/Idf/IdfDefaults.cs`, `IdfWriter.cs`, `IdfObjects.cs`, `GroundTemperatureRule.cs`, and `src/Lod.Core/Envelope/EnvelopePreset.cs`. The 26.2 target and legacy layered GroundFloor/BuildingSurface temperature path were observed there; other in-progress BEMGen worktrees were not audited for this plan.

Primary engine references, checked 2026-10-16:

- [EnergyPlus 26.2 surface-construction objects](https://energyplus.readthedocs.io/en/v26.2.0/guides/input-output-reference/1.9-group-surface-construction-elements.html): F/C objects and required boundary condition.
- [EnergyPlus 26.2 C/F-factor engineering method](https://energyplus.readthedocs.io/en/v26.2.0/guides/engineering-reference/3.12-ground-heat-transfer-calculations-using-c-and-f-factor-constructions.html): geometry dependence and method-specific ground temperatures.
- [EnergyPlus 26.2 Kiva engineering method](https://energyplus.readthedocs.io/en/v26.2.0/guides/engineering-reference/3.11-ground-heat-transfer-calculations-using-foundationkiva.html): edge/soil coupling, core slabs and initialization.
- [EnergyPlus 26.2 advanced surface concepts](https://energyplus.readthedocs.io/en/v26.2.0/guides/input-output-reference/1.11-group-advanced-surface-concepts.html): Foundation:Kiva and settings.
