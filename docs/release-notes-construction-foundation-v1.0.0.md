# Combined Construction Suite 1.0.0 — publication candidate

Prepared locally on 2026-10-19. This records the foundation/ground release
candidate, not a claim of hosted checks, main-branch merge or deployment.

## Versions and immutable inputs

| Artifact | Version |
| --- | --- |
| Combined construction delivery | 1.0.0 |
| Detailed consumer JSON | 3.0.0 |
| Unified consumer JSON | 2.0.0 |
| Embedded foundation contract | 1 |
| Shared mass-accounting contract | 1.0.0, unchanged |

The combined delivery is frozen at
[`data/construction-foundation-releases/v1.0.0`](../data/construction-foundation-releases/v1.0.0/manifest.json).
It extends detailed distribution v2.2.0, unified thermal-assembly release 1.1.0
and shared mass release 1.0.0. Those earlier artifacts and consumer schemas remain
unchanged. Release versions identify bundles; consumer schema versions identify
standalone JSON contracts and must not be inferred from the bundle version.

The new detailed/unified pair preserves existing above-ground construction,
fixed reference ACH, ordinary equivalent recipes/fit errors and shared mass
quantities. Program JSON, schedules and systems are unchanged.

## Coverage and representation

All **177 suites / 3,320 supported contexts** remain in the denominator:
**3,308** have executable ground-contact physics and **12** have source-supported
absence of direct ground contact. Missing executable physics: **zero** within
that supported source population. The eight unsupported historical source
contexts remain evidence rather than selectable consumer contexts.

GroundFloor, FoundationWall, FloorOverFoundation and RimJoist use the existing
component/assignment, assembly/material and provenance structures. The selected
suite/climate/reference also selects its ground content. There is no independent
ground catalogue, selector, compatibility registry or third JSON download.

Native F/C-factor, layered-ground and Kiva methods retain their physical meaning.
F/C factors live on assemblies, material properties in material resources, and
coupled Kiva placement/initialization parameters once on referenced methods.
Model-wide parameters retain their own scope and must agree within one IDF.

Unified ordinary components stay simplified. **20 residential suite/role
exceptions** retain exactly two native assignments each: 15 GroundFloor host/
coupling distinctions and five FoundationWall soil/non-soil distinctions.
They must not be homogenized into one layered construction. Exact affected
suite IDs and reasons are in the release's `completeness.json`.

## Consumer migration

Consumers must explicitly support detailed **3.0.0** / unified **2.0.0**. Older
importers must reject unsupported versions instead of silently dropping ground.

- Resolve an assignment's `assembly_id` and `ground_method_id` independently
  inside its selected document. IDs identify recipes/instructions, not a
  physical foundation or a geometry-dependent instantiated IDF object.
- Dispatch native F/C objects without requiring fabricated layers. Use the
  specified FC versus BuildingSurface temperature input for the native method.
- Supply actual BEM areas, external exposed edges, foundation groups, hosts and
  topology. Cancel shared zone edges; native zero-perimeter handling remains
  valid. Unsupported new configurations fail rather than acquiring a generic
  soil-contact recipe.
- Resolve explicit method dimension expressions as scoped operands. They do
  not replace actual BEM/site geometry. Report conflicts without silent overrides.
- Derive temperature operands under the declared source initialization policy,
  using start-month mean weather and applicable program controls, then apply
  dimensionless affine weights and the temperature increment. Missing controlled
  inputs fail; shared recipes do not merge separate Kiva solver domains.
- Preserve shared mass ownership. Ground/soil capacity is outside ordinary
  interior-mass restoration; do not count interfaces or source budgets twice.

See the [complete embedded contract](construction-foundation-ground-v1-contract.md)
and [BEMGen acceptance tests](bemgen-foundation-instantiation-tests.md).
Complete paired review examples are in
[`docs/examples/construction-foundation-v1`](examples/construction-foundation-v1/manifest.json).
The local BEMGen v7 packet has 19 pairs, including an existing-source Hospital
C-factor case. That ignored local packet is not a CI or site-build dependency.
Consumer integration acceptance remains pending; Atlas completeness does not
certify BEMGen implementation or simulation results.

## Publication gates and limits

The catalogue research matrix retains its Linux/Python 3.11 and Windows/Python
3.14 jobs. Combined byte/example reproduction uses the existing pinned Windows
x64 / CPython 3.14.7 producer. Both platforms verify frozen recovery/airflow/smoke
receipts and validate all 3,320 combined pairs. Receipt verification does not run
native source recovery, download an engine or execute EnergyPlus.

The build job verifies the combined manifest/input closure, foundation browser
hydration and publication-policy regressions. The local browser harness compares
both preview and clipboard JSON with the frozen combined exporter for office,
warehouse, basement, upper apartment, data centre and Hospital examples. It checks
the selected foundation summary, one verified initial detailed packet, one load
per representation, missing resources, unsupported contexts and desktop/mobile
light/dark views.

Earlier native source verification includes 588 initialization probes and six
EnergyPlus 26.2 short-run smoke cells. Those establish source-policy/input and
short-run numerical checks, not steady-state F-times-perimeter or annual accuracy.
No systematic construction/zoning error experiment is claimed.

Next gates remain clean-checkout/publication verification, protected-main PR
checks, merge, main-only deployment and live export checks. BEMGen v7 testing can
proceed independently; any discovered Atlas defect must be resolved. Systems and
schedule-generator packaging are outside this milestone. Lighter artifact delivery
remains deferred until BEMGen testing is accepted. Preserve original Atlas and
upstream license terms; no MIT relicensing permission is added.
