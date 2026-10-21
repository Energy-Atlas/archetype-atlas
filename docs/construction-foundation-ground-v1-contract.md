# Embedded foundation/ground contract v1

This fragment extends complete detailed construction JSON 3.0.0 and unified
construction JSON 2.0.0. It is not independently selected or exported. Those
consumer versions are available in the combined 1.0.0 release; frozen detailed 2.1.0, unified
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

## Reference identity and instantiated scope

`assembly_id` and `ground_method_id` resolve independently inside the selected
document. A method ID identifies reusable execution instructions, not a
construction identity or physical foundation. The Medium Office and Midrise
Apartment examples share an FFactor method while their assembly IDs and F-values
differ. Resolve both references before instantiating an IDF construction.

Every executable assembly, material, method, model-parameter and dimension-expression
reference must resolve in that same standalone document. Provenance/source-map
identifiers remain source locators, rather than requests for additional executable
resources. Importing another
document must not repair a missing reference. If a consumer interns resources
across documents, equal IDs require equal resolved definitions; conflicting
payloads must fail rather than overwrite each other.

IDF object reuse requires equivalent effective definitions and compatible object
scope. For F-factor constructions, compare the resolved F-value, actual area and
exposed perimeter; for C-factor constructions compare the C-value and actual
height. Check method/environment compatibility as well. A method ID, assembly
ID or coincidentally equal nominal conductance is insufficient on its own.
Reuse of equivalent stateless construction/material definitions is optional.

Kiva coupling is physical and geometry-dependent. One valid foundation group can
associate its slab and wall interfaces through the selected method. Repeated use
of that method does not authorize merging different foundations, thermal hosts,
topologies or solver domains, even when their numeric parameters match. BEMGen
must retain foundation-group identity and resolve each group's geometry and
initial conditions independently. Equal model-wide Kiva settings may be shared
only within their model-wide scope; conflicting requests fail. These are
consumer instantiation rules, not another public registry or suite selector.

## Explicit dimension operands and initialization weights

An expression such as `wall_height_above_grade.material_thickness_id` requests
one specific Kiva method operand from the referenced material. In the retained
5A detached-dwelling example, the referenced thickness is 0.1016 m. Resolve the
expression, including any declared scale/offset, without treating the layer stack
as a source for actual slab dimensions, perimeter, grade datum, basement depth
or foundation topology. Explicit method operands still have geometric meaning:
if the BEM/site configuration contradicts one, report the conflict instead of
silently rewriting the recipe or geometry. An override requires an explicitly
accepted policy and a recorded diagnostic; none is implied by ID reuse.

`parameters.initialization.outdoor`, `ground` and `indoor` are dimensionless
affine weights; `offset_K` is a temperature increment. First follow
`resstock_source_start_month_1.0.0` to obtain the temperature operands. The source
outdoor operand is the mean outdoor dry-bulb temperature of the simulation-start
month. With applicable thermostat controls, obtain heating/cooling setpoints for
the simulation start and derive approximate indoor temperature using the declared
balance thresholds and linear interpolation between them. Without thermostat
controls, the source policy uses that outdoor operand as indoor temperature.
Missing controls on an explicitly controlled host are an error, not permission
to switch to the no-controls branch.

Then apply:

```text
T_initial_C = outdoor * T_outdoor_C + ground * T_ground_C
            + indoor * T_indoor_C + offset_K
```

For the retained dwelling's weights (0, 0, 1) and zero offset, the result is the
derived indoor temperature, not 1 degree Celsius. Shared method IDs do not imply
shared weather/start dates, program controls or resolved initialization values.

The focused BEMGen acceptance cases are specified in
[the instantiation test requirements](bemgen-foundation-instantiation-tests.md).
Atlas reference checks do not establish that those consumer tests have passed.

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

C-factor wall vertices must follow the declared GlobalGeometryRules starting
corner/order. The target engine derives vertical height using that convention;
an inconsistent ordering can instead expose a horizontal edge as wall height.

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

The local release review records complete coverage, the 20 two-assignment native
exceptions, and numerical verification limits. No source-recovery blocker is
being hidden as a consumer default. Required actual BEM/site/weather/control
inputs are part of execution and remain BEMGen responsibilities.
