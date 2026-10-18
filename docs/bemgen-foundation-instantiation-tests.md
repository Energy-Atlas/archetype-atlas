# BEMGen foundation instantiation — required acceptance tests

These tests clarify the existing detailed 3.0.0 / unified 2.0.0 contract. They
introduce no schema, source-physics, recipe or public registry change. Apply
each relevant case to both representations. BEMGen owns their implementation
and importer-generated IDF/simulation verification; this document specifies
required results, not a claim that the consumer implementation exists.

## Fixture anchors

Use the new handover packet's unchanged complete JSON examples:

- `medium-office-2019-3B`: FFactor GroundFloor, F = 1.26343630645112 W/(m K).
- `retained-midrise-apartment-2019-3B`: the same method ID, distinct assembly,
  F = 0.934596719840551 W/(m K).
- `retained-residential-5A`: Kiva slab-on-grade, conditioned host, initialization
  weights (outdoor, ground, indoor) = (0, 0, 1), offset = 0 K. Its explicit
  wall-height operand references a 0.1016 m material thickness.
- `residential-vented-crawlspace`: coupled native slab/wall interfaces and
  non-unit initialization weights (0.9, 0, 0.1) for the crawlspace host.
- `residential-conditioned-basement`: native soil/non-soil assignments whose
  boundary conditions must remain distinct.
- `hospital-2019-3B-native-c-factor`: an additional pair exported from the existing
  frozen release, supplying an actual C-factor foundation-wall recipe for R4.
  Existing packet examples and all physical source data remain unchanged.

The packet includes `acceptance/initialization-cases.json` with numeric reference
cases verified against the existing Atlas source-policy port. Input weather and
setpoints there are declared synthetic test conditions, not catalogue defaults.

## Identity, closure and scoped object reuse

| ID | Setup | Required result |
| --- | --- | --- |
| R1 | Import office and apartment with their shared FFactor method; supply area 100 m2 and exposed perimeter 40 m for each | Independently resolve each assignment's assembly and method; retain both F-values and distinct effective F-factor constructions. Method-only caching must fail this test |
| R2 | Instantiate the office assembly twice: (area, exposed perimeter) = (100 m2, 40 m) and (200 m2, 60 m) | Resolve two geometry-dependent definitions. Do not reuse the first object's area/perimeter for the second |
| R3 | Repeat an otherwise identical F-factor request with matching F, area, perimeter, native object definition and compatible environment/scope | Reuse is allowed but not mandatory. Either path preserves effective inputs and surface behavior; no physical coupling is invented |
| R4 | Use one source C-factor recipe for two walls with actual heights 2 m and 3 m | Keep the height-dependent definitions distinct; method/assembly identity alone cannot authorize reuse. Retain the existing wall-vertex ordering test |
| R5 | Remove an assigned assembly, method, referenced model-parameters entry, layer/insulation/soil material, or dimension-expression reference from one selected document; leave a matching ID in another document | Reject each orphan in the selected document. Another document or a global cache must not repair it |
| R6 | Attempt cross-document interning with equal IDs but conflicting resolved payloads | Report an identity conflict; do not overwrite or select the first definition. Equal IDs with equal payloads still do not authorize shared foundation geometry |

## Kiva grouping and geometric operands

| ID | Setup | Required result |
| --- | --- | --- |
| K1 | Map valid crawlspace/basement slab and soil-contact wall interfaces into one physical foundation group | Resolve their assignments and method references, then retain the intended native coupling. Do not split legitimate coupling merely because assembly IDs differ |
| K2 | Instantiate the same Kiva recipes/method for two physically separate foundations with numerically identical dimensions, parameters and controls | Preserve separate physical group/solver-instance ownership. ID equality or numeric equality must not merge them; any shared native definition must demonstrably preserve independent domains |
| K3 | Use the same method on groups with different geometry, thermal hosts, topology or initialization conditions | Resolve each group independently. No geometry, host or initialization operand may leak through an ID-keyed cache |
| K4 | Resolve the retained 5A dwelling's `wall_height_above_grade.material_thickness_id` while supplying a declared 10 m by 12 m slab with 44 m external perimeter | The method operand is 0.1016 m; slab area remains 120 m2 and perimeter remains 44 m. Material layers do not set the actual BEM footprint or grade datum |
| K5 | Supply a BEM/site configuration that contradicts an explicit method operand, or omit a required topology/geometry operand | Emit a clear unsupported/missing-input diagnostic. No silent geometry rewrite, source-recipe rewrite or guessed positive perimeter. No override is authorized by these fixtures |
| K6 | Combine equal versus conflicting model-wide Kiva settings or ground-temperature requests | Share agreeing model-wide settings where valid; reject conflicts. Do not confuse model-wide sharing with sharing a coupled foundation instance |

Retain the earlier shared-edge cancellation and zero-exposed-perimeter tests.
Compare group membership and actual operands, not generated names or object
counts alone. A fake implementation that just emits more objects must not pass.

## Initialization policy and affine weights

| ID | Setup | Required result |
| --- | --- | --- |
| I1 | Retained dwelling, controls present, heating 20 C / cooling 26 C; start-month outdoor means 8, 12.5 and 18 C | Derived indoor and final initial temperatures are respectively 20, 23 and 26 C; never 1 C |
| I2 | Repeat at exactly the declared 10 C and 15 C balance thresholds | Continuous endpoint results: 20 C and 26 C |
| I3 | Explicit no-thermostat host, start-month outdoor mean 12.5 C | Source indoor operand and final dwelling-weighted temperature are 12.5 C. This is not a fallback for missing controlled-host setpoints |
| I4 | Keep the January mean at 8 C but set instantaneous first-hour outdoor temperature to 30 C | Initialization still uses January's monthly mean, yielding 20 C with the stated controls. Select a different start month and use that month's mean instead |
| I5 | Vented-crawlspace weights (0.9, 0, 0.1), outdoor mean 8 C and derived indoor 20 C | Initial temperature is 9.2 C, proving weights are applied after deriving operands |
| I6 | Explicitly controlled host lacks heating/cooling input or has heating above cooling | Reject; no invented setpoint, no reuse of another foundation's controls, no implicit no-controls branch |

Test settings are synthetic. Obtain real start-day controls from the selected
program's schedules with the source policy's date/selector semantics. Preserve
dimensionless weights and temperature-increment units; do not treat a weight as
a temperature or apply a Celsius/Fahrenheit absolute-temperature conversion to
`offset_K`. Changing another foundation's geometry or controls must not mutate
this foundation's resolved initial temperature.

## Consumer execution gate

Validate emitted native objects and references against EnergyPlus 26.2; run
small importer-generated F/C/Kiva smoke cases and check diagnostics/output for
the intended groups. Report which cases pass, fail or remain unsupported.
Successful Atlas packet/schema/reference/numeric checks are not successful
BEMGen importer tests, and no annual or systematic building-level experiment
is requested here. Preserve legacy importer behavior on its existing path.
