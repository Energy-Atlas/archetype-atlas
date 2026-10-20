# Above-ground construction milestone closure

Date: 2026-10-15. Branch: `feature/json-completion`.
Implementation reviewed: `ab1d17b`.

## Decision and boundary

The above-ground construction implementation is complete under the user-approved
scope and approximation policies. Both detailed and additive unified exports
cover every current supported context. There are no remaining implementation
blockers or scientific decisions for this milestone. This closes implementation
and local integration, not production publication or BEMGen integration testing.

The user requested this closure separately from subsequent publication preparation.
No push, pull request, workflow dispatch, CI/CD, Pages deployment, broad
program/schedule generation or full site build accompanies this review.

Ground/foundation/basement and foundation-dependent assemblies, HVAC/mechanical
air requirements and detailed DHW remain deferred. BEMGen owns translation and
actual geometry. Schedule-generator packaging is not a prerequisite for
publication or the first BEMGen test. Lighter artifact delivery waits until that
test is accepted. See the [updated roadmap](../roadmap.md#current-execution-order).

## Deliverables and coverage

| Deliverable | Reviewed result |
| --- | --- |
| Detailed distribution | v2.2.0; consumer schema 2.0.0; 177 complete sets and 3,320 supported climate/reference contexts |
| Set families | 136 building sets and 41 residential whole-dwelling sets, using the same detailed consumer structure |
| Detailed resources | 4,868 assemblies and 858 materials retained, including independent source-table recipes without invented prototype applicability |
| Embedded space rules | 1,470 source contexts retained inside building sets; 47 standalone partial space sets retired from current selection |
| Unsupported source contexts | Eight legacy office plenum 0A/0B contexts retained as nonselectable evidence |
| Unified release | 1.1.0; one assembly per applicable semantic; all 3,320 contexts ready, zero blocked |
| Supporting profiles | 129 commercial references and 41 residential fixtures; 1,158 native commercial program keys |
| Local site | 177 construction definition pages with separate direct-copy Detailed and Unified actions; no legacy source-record chooser on those pages |

The denominator is the approved above-ground source catalogue and its supported
climate/reference contexts. It does not mean every conceivable climate,
typology or ground/system variant. Native support keys are not new program load
contracts. Known absence remains distinct from unknown source information.

## Review and fresh verification

The [machine-readable receipt](construction-milestone-closure.json) pins the
reviewed manifests, coverage and verification results.

- All 138 focused Python tests passed. The suite covers construction source
  definitions/selectors, geometry/ACH, detailed export/hydration/distribution,
  weighting, numerical reduction, unified export/release, local site delivery,
  asset versioning and HTML delivery.
- All 24 JavaScript tests passed, including construction selection and existing
  program/schedule behavior.
- `construction_weighting --check` reproduced the supporting profiles and their
  manifest; `construction_distribution --check` reproduced current selection,
  embedding evidence and the eight-context evidence archive.
- `construction_equivalent_release --check` regenerated and validated all 3,320
  unified contexts from frozen inputs and reproduced every release byte.
- Every current detailed context was freshly hydrated and passed schema,
  physical, assignment, referential and provenance validation. All retained
  detailed resources also passed schema/graph checks, including table-only
  resources that do not occur in a supported prototype selection.
- All declared outputs and inputs of the five reviewed manifests were checked
  against their hashes and declared output byte counts. No frozen research data,
  schema or exporter changed in this closure pass.
- Every local detailed/unified site packet and linked resource matched the
  frozen release. All 177 construction definition pages had both named copy
  controls, no legacy `data-raw` binding and valid local links. This is a static
  delivery check; the existing direct-copy browser verification remains in the
  [site record](unified-construction-site-local.md).
- An independent read-only review found no justified correctness or coverage
  findings in the final implementation. It examined numerical/boundary
  conventions, weighting, mass accounting, distribution, schemas and site
  controls. Different assembly IDs on paired wall faces were probed and had
  equal capacities; they were not treated as a defect without evidence.

The focused numerical tests include the independent homogeneous-wall solution at
1, 6, 24, 72 and 168 hours, both boundary excitations, unequal film ordering,
inward-flux signs and one-sided InternalMass conventions. The earlier three
EnergyPlus 25.1.0 material smoke cases are retained as
[historical engine evidence](construction-equivalent-material-smoke-v1.json).
They were not rerun here and do not validate an annual building model.

## Accepted limitations and consumer responsibilities

Detailed assemblies, layers, source identities, assignment precedence and
selector alternatives remain intact. The unified representation is additive.
Opaque equivalents use the fixed two-mass-layer plus massless-resistance method,
conserving common-reference-film conductance and areal heat capacity. It cannot
reproduce every source transient response; errors and quality flags remain
visible, without increasing model complexity or claiming annual energy accuracy.
There are 13,539 `approximation_review` entries counted per context recipe,
including repeated shared recipes, rather than 13,539 distinct failed contexts.

Reference weights use recovered source exposure and physical inventories. Generic
hotel GuestRoom applicability creates no invented reference exposure. Paired
faces with unequal zone multipliers use the accepted symmetric mean, preserving
both operands and approximation flags. Residential source overhang dimensions
remain evidence; actual overhang geometry is supplied by BEMGen.

BEMGen must supply actual component areas, geometry and counted floor area;
resolve detailed rules or use the unified semantic recipes; reverse the canonical
InteriorFloor recipe on a paired ceiling; and reconcile represented physical
wall/slab capacity with InternalMass and residual FloorDistributedMass budgets.
It must not add slabs or furnishings twice. The fixed reference natural ACH is
unchanged between representations and is not a mechanical ventilation model.

Systematic separation of construction approximation errors from zoning errors
remains deferred to journal experiments or a later reviewer request. Ready means
complete under these accepted policies, not exact transient or building-energy
reproduction.

## Closure and next gate

Implementation review and local integration are closed. The next planned
milestone is site/release publication preparation, followed by the
BEMGen test handoff using existing schedules. Neither has started in this pass.
Production publication still requires the protected-main PR/check process;
BEMGen translation and test acceptance remain separate downstream gates.
