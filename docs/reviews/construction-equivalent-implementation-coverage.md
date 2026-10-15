# Additive construction equivalent implementation coverage

Date: 2026-10-15. Local branch: `feature/json-completion`.

This is the exporter implementation record. The subsequent local site integration
is recorded [separately](unified-construction-site-local.md); the
[milestone closure](construction-milestone-closure.md) records the final review
and fresh checks. References below to unchanged website exports or site work
outside this implementation describe the earlier exporter-only phase.

The additive exporter is implemented alongside detailed construction v2.2.0.
It supplies one assembly per applicable semantic, precomputed source-archetype
weights, fixed reference ACH, mass budgets and derivation receipts. Existing
detailed construction, program, schedule and website exports are unchanged.
Version 1.1.0 is a local research artefact. Every context is ready under the
accepted approximation and consumer-geometry policies; it is not a production
publication or a claim of exact source-response reproduction.

## Coverage

| Item | Count |
| --- | ---: |
| Source construction sets retained | 177 |
| Detailed contexts represented | 3,320 |
| Ready contexts | 3,320 |
| Blocked contexts | 0 |
| Commercial source reference profiles | 129 |
| Residential source fixture profiles | 41 |
| Native commercial program keys recovered | 1,158 |

Program-library support profiles contain counted floor shares, native building
group and conditional program shares, component exposure, volume, story scopes,
and physical mass inventories. Native program keys link to published definitions
where exact source joins exist. Recovering a share key does not create a missing
program load contract. Non-counted scopes retain direct exposure; known absence
is zero, while an unresolved operand remains unknown.

## Accepted policies and resolved gaps

The user explicitly accepted both policies on 2026-10-15. Version 1.1.0 closes
all 331 previously blocked contexts without increasing fitting complexity.

| Previous gap | Affected contexts | Implemented policy |
| --- | ---: | --- |
| Different residential source overhang dimensions | 41 | Keep material recipes and common non-geometric solar modifiers active. Preserve every source overhang dimension and evidence ID in the component derivation; BEMGen supplies actual overhang geometry. |
| Unequal source zone multipliers on paired interzone faces | 290 for InternalMass; 227 of these also affected FloorDistributedMass | Average the two multiplied face areas, retaining both operands in the profile. Flag unequal multipliers as a reference-model approximation and report affected pair counts in derived mass accounting. |

The mass counts overlap. Both groups are resolved; no further policy decision is
required for this representation. Actual geometry remains a consumer input and
the paired-face mean is not a claim about physical copies. Different non-geometric
solar modifiers would still block readiness; none occur among these residential
window contributors. Previous 1.0.0 data and schema remain immutable and hydratable.

## Fixed approximation and evidence

The default remains two massive layers and a massless resistance, conserving
reference-film conductance and areal heat capacity. Source-proven massless
assemblies remain massless. The fixed representation cannot reproduce every
source assembly's transient behaviour. Every fit retains frequency-specific
response, transmission-amplitude and phase errors where meaningful. A review
flag reports approximation quality; it is not an annual energy-error estimate
or a hidden readiness blocker.

Current counts are per context recipe, including repeated shared recipes:

| Quality label | Count |
| --- | ---: |
| within_initial_screen | 20,002 |
| approximation_review | 13,539 |
| unchanged_source_physics | 10,199 |
| area_weighted_optical_proxy | 21 |

Normalization policy 1.0.1 uses a nominal 6 mm minimum total massive thickness
instead of the historical probe's arbitrary 40 mm gauge, so low-capacity metal
doors can satisfy the same material constraints. It changes no conserved target,
response equation, fitted parameter or layer count. Historical probe results
remain unchanged. See [ADR 0025](../adr/0025-additive-building-level-equivalents.md).

Paired floor/ceiling surfaces use InteriorFloor as the canonical construction
and its reverse on the adjacent ceiling. InteriorCeiling is for unpaired ceilings.
The physical inventory counts each pair once. Additional furnishings and residual
slab mass remain separate; BEMGen reconciles these budgets with actual represented
surfaces. Consumer geometry is not required to calculate blending weights.

## Verification

- 128 focused construction tests passed, including the existing detailed
  construction suite. No broad program, schedule or site generation was run.
- An independent homogeneous-slab solution at 1, 6, 24, 72 and 168 hours checks
  both boundary excitations, inward-flux signs, and swapped unequal film ordering.
  A separate analytical test checks the exposed last face of one-sided mass.
- Every exported context passed schema, physical material, source-reference,
  conserved R/C/U, assembly closure, finite-value and readiness checks during
  generation. Profile and release checks reproduce exact frozen bytes.
- Medium Office, Warehouse and residential opaque material cells completed one
  synthetic design day in EnergyPlus 25.1.0 with zero warnings and severe errors.
  [Smoke receipt](construction-equivalent-material-smoke-v1.json). These verify
  input viability, not annual building-level accuracy or residential shading.
  These smoke runs describe the unchanged thermal fitting method tested for 1.0.0;
  the 1.1.0 source-policy update is checked through focused tests and all-context validation.

A fresh code review found five correctness issues, now covered by regression
tests: paired-face iteration dependence, exterior/interior window-area mixing,
unknown exposures becoming zero, invalid native material operands, and missing
floor/ceiling reversal semantics. Final resource closure also removes unused
recipes after a mass semantic becomes blocked. No systematic construction-versus-
zoning experiment or more complex fit was introduced.

## Files and use

- Profiles: `data/program-support/construction-weighting-v1.1.0/`.
- Schema: `schemas/construction-equivalent-v1.1.schema.json`.
- Derived release: `data/construction-equivalent-releases/v1.1.0/`.
- Standalone examples: `examples/medium-office-2019-3B.json` and
  `examples/residential.json` within that release. Both examples are ready; residential overhangs are
  explicitly marked as consumer-resolved geometry.

```powershell
.venv/Scripts/python.exe -m scripts.construction_weighting --check
.venv/Scripts/python.exe -m scripts.construction_equivalent_release --check
.venv/Scripts/python.exe -m scripts.construction_equivalent_release --context-id ID --output selected.json
```

Manifests pin source revisions, retrieval/runtime hashes, input files and output
checksums. Ground, systems, translator implementation, site integration, push,
CI/CD and production deployment remain outside this implementation.
