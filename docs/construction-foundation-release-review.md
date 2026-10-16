# Combined Construction Suite — local release review

Detailed JSON **3.0.0** and unified JSON **2.0.0** add source-native ground
physics to the existing suite selection. Above-ground components, catalogue ACH,
shared mass contract 1.0.0 and historical frozen releases remain unchanged.

## Coverage

All **177 suites / 3,320 contexts** are supported for their source configuration:
**3,308** executable contact contexts and **12** source-supported no-contact
contexts. Missing executable physics: **0**. This does not cover arbitrary new
basements, buried roofs or converting an upper apartment into a whole building.
The eight unsupported historical office/plenum contexts remain source evidence.

Native recovery executed 2,625 commercial reference/climate queries grouped into
822 exact source cases, plus 41 residential fixtures. All 210 deferred residential
source objects were retained. Method ownership is checked: F/C factors are on
assemblies, material properties in materials, coupled Kiva parameters once on
their referenced method, and model-wide settings once in model_parameters.

## Unified exceptions

**20 residential suite/role exceptions retain two native assignments each:**
15 GroundFloor entries distinguish garage from dwelling/basement/crawlspace
coupling and initialization; five FoundationWall entries distinguish soil-contact
Kiva from non-soil adiabatic/interzone walls. These are physical differences,
not alternative equivalent-layer fits. The exact suite IDs/reasons are recorded
in the release's completeness.json. Commercial suites have no native multiples.
Ordinary above-ground components and floor/rim interfaces remain simplified.

## Verification and limits

- All 3,320 paired exports passed both full schemas and focused physical,
  ownership, reference and provenance checks.
- Residential Kiva initialization passed 588 direct source-function probes.
- Six one-day synthetic cells run in pinned EnergyPlus 26.2: F-factor perimeter
  and zero-perimeter core, layered ground, C-factor, Kiva slab and coupled
  wall/slab. All have finite output and no warnings/severe/fatal errors.
- The smoke driver and receipt are scripts/construction_foundation_smoke.py and
  data/construction-inputs/foundation-smoke-v1.json. Running native recovery or
  simulations is explicitly opt-in; normal exports/site generation read freezes.

The one-day smoke is not a steady-state F×perimeter flux comparison or annual
archetype validation. Transient storage can produce core-slab heat flow despite
large native resistance. Shared-edge/perimeter invariance is checked separately;
the engine's native zero-perimeter branch is preserved. No new steady-state or
building-level approximation is inferred from the smoke output.

One source helper assumes one ground floor face per space. Tall reference spaces
with several faces can have order-dependent reference area. This remains internal
evidence; actual consumer BEM area and external exposed edges are required.
C-factor wall vertex order must agree with GlobalGeometryRules so EnergyPlus
derives the intended vertical wall height. The native smoke verifies this.

BEMGen must still implement/import these contracts and supply actual geometry,
foundation groups/hosts, site/weather and applicable controls. Atlas completeness
does not certify that integration. No generic ground or weather fallback was
introduced. Publication remains a later review gate; systems remain deferred.
