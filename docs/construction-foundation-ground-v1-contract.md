# Embedded foundation/ground contract v1

This fragment extends complete detailed construction JSON 3.0.0 and unified
construction JSON 2.0.0. It is not independently selected or exported. Those
consumer versions are under implementation; frozen detailed 2.1.0, unified
1.2.0 and shared mass 1.0.0 remain unchanged.

Select the ordinary Construction Suite, climate and reference context. Its four
additional component roles are GroundFloor, FoundationWall, FloorOverFoundation
and RimJoist. They reuse component targets, assignments, assembly references and
the existing provenance structures. The assignment's optional `ground_method_id`
references its execution instructions under `foundation_ground.methods`.
Ordinary construction components do not acquire ground-method references.
Assignment `when.boundary_condition: Ground` denotes physical soil contact in
the input BEM. It does not require an already translated `GroundFCfactorMethod`
or `Foundation` IDF boundary; the selected method determines that output.

## Parameter ownership

| Parameter | Authoritative executable location |
| --- | --- |
| F-factor or C-factor | Corresponding native assembly's `f_W_m_K` or `c_W_m2_K` |
| Layer and insulation material properties | Existing `materials` resources, referenced by IDs |
| Kiva insulation placement, custom blocks and local initialization weights | Selected ground method's `parameters` |
| Kiva soil material reference, model-wide solver settings and initialization control thresholds | One `foundation_ground.model_parameters` entry referenced by methods |
| Actual area, exposed perimeter, grade, foundation grouping and host volume | Consumer BEM/site; typed requirements and geometry-input references in the document |
| Source reference geometry, raw inventories and recovery/validation traces | Internal frozen inputs and support profiles |

Coupled Kiva slab and wall assignments can reference the same method. Its
parameters are stored once, without copying them into either assembly. Soil
conductivity/density/heat capacity use a material reference rather than shadow
material values in method settings. Unified native material resources use the
same material/evidence conventions as detailed; ordinary unified layers and
their existing simplified representation are preserved.

`foundation_ground` contains configuration, methods, model-wide parameters and
required geometry only. It contains no component/material/provenance registry,
source inventory or compatibility object. Component conditions remain the
existing assignment path; unsupported BEM interfaces or missing required inputs
must fail explicitly. A source blocker cannot be relabelled as a consumer input.

## Native methods and environment

- F/C-factor assemblies instantiate the native EnergyPlus construction objects
  and `GroundFCfactorMethod` boundary. F/C factors remain source-native; no fake
  material layers are exported. Actual F-factor perimeter may be zero, following
  the target engine's native underground/core branch. Never invent a positive
  perimeter. A perimeter denotes exposed foundation edges, not zone perimeters.
- Layered ground assemblies use their original layers and the `Ground` boundary,
  with declared BuildingSurface monthly ground temperatures supplied by the
  consumer. A large finite-R material named Adiabatic is not a zero-flux boundary.
- Kiva retains native soil/edge coupling, insulation geometry, material recipes,
  source model-wide settings and a source-derived initialization rule. The
  consumer supplies actual foundation topology/geometry, weather, simulation
  start and applicable program setpoints. Source initialization weights were
  checked against 588 direct evaluations of the pinned source function.
- FC and BuildingSurface monthly boundary temperatures are distinct inputs.
  FC source STAT processing rotates monthly outdoor temperatures by three months
  (`rotate(-3)`); a declared per-method monthly boundary is also supported. Do
  not use a fixed ACH reference-weather calendar or a universal indoor-minus-2°C
  rule for these native imports. Missing required weather/boundary inputs fail.
- Model-wide Kiva or ground-temperature requests must agree within one IDF.
  Conflicting requests fail; do not silently pick one source's settings.

Unconditioned crawlspace/basement hosts retain their source thermal interface and
base air-exchange rules. Source duct imbalance and mechanical operation are not
new construction loads. Whole-enclosure catalogue ACH is preserved. BEMGen owns
actual host volumes, adjacency and conditioned-host program controls.

## Unified representation and readiness

Ordinary unified components retain their existing single simplified recipe.
Ground native recipes can remain native. Multiple assignments are exceptional:
only GroundFloor/FoundationWall may retain them when physical equivalence or
homogenization is unjustified. Deduplicate equal recipes/configurations and
report every affected suite/role and its physical reason in the release summary.
Absence of an equivalent-layer fit alone does not block a native recipe.

Coverage retains 177 suites / 3,320 contexts. Internal reports distinguish complete
contact physics, source-supported no contact, and missing executable physics.
No-contact uses the existing component absence dispositions and an explicit
configuration reason. It is not missing data and does not authorize a generic
ground slab on incompatible consumer geometry. A missing recipe remains blocked.

Ground/soil capacity is excluded from ordinary interior-mass restoration. Keep
the existing shared mass contract unchanged and count each explicit interface
once. No second public foundation mass ledger is introduced.

The native source helper assumes one ground-floor face per space; a few tall
reference spaces violate this and have order-dependent reported area. Retain the
captured result as internal evidence. Consumers use actual BEM geometry; source
helper artefacts are not catalogue geometry defaults.

See ADR 0027 and the approved implementation plan for source pins, coverage and
release gates. BEMGen code remains a separate worker's responsibility.
