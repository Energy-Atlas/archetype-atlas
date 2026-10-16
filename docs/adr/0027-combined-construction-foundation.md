# ADR 0027 — Foundation/ground within the Construction Suite

Accepted 2026-10-16; implementation authorized after owner review of the revised plan.

## Decision

Extend the existing detailed and unified Construction Suites. GroundFloor,
FoundationWall, FloorOverFoundation and RimJoist use the existing component,
assignment, assembly/material and provenance structures. `foundation_ground`
contains effective configuration, method references, method-specific environment
settings and required consumer geometry. It is not a second component catalogue
or matching system. The existing suite/climate selection also filters foundation
content. BEMGen maps its interfaces to applicable assignments and rejects
unsupported configurations.

Each parameter has one authoritative location. Assembly physics (including F/C
factors and layer material properties) belongs to assemblies/material resources.
Kiva solver/environment configuration belongs to `foundation_ground`; an assembly
references that configuration rather than copying it. Assembly-specific Kiva
insulation recipes stay with their assembly. Shared settings use references;
neither section carries a shadow copy of the other's operands. Provenance may
preserve original values internally without creating a second executable input.

Public documents contain selected executable dependencies, required inputs and
reproducibility references. Source inventories, caller traces and validation
details remain internal. Frozen above-ground releases and current mass budgets
are immutable. New consumer contracts are versioned separately.

Ordinary unified components retain their existing simplified representation.
Native F/C-factor and Kiva ground methods remain native where equivalent layers
would misrepresent physics. Multiple native foundation assignments are permitted
only when physical equivalence/homogenization is unjustified. Deduplicate equal
recipes, keep this exception set small and report affected suites/roles and
reasons in the release summary. Lack of an equivalent-layer fit alone is not a
blocker for an otherwise executable native recipe.

## Accepted scientific boundaries

- Preserve source methods rather than invent a universal ground solver (D1).
- Complete source-supported conditions for all 177 suites / 3,320 contexts;
  source-supported no-contact is valid coverage, missing physics is blocked (D2).
- Preserve method-specific soil/weather/initialization policies and typed site
  inputs. Do not invent numerical fallbacks or apply indoor-minus-2°C to native
  methods universally (D3).
- Preserve required unconditioned hosts and source air-exchange semantics.
  Missing consumer host support is unsupported input, not permission to substitute
  outdoor air or a constant-temperature boundary (D4).

## Consequences

Actual contact geometry, exposed perimeter, grade and thermal hosts remain
BEMGen's responsibility. Climate-filtered suite selection is sufficient; there
is no independent foundation selection axis or public compatibility object.
Source candidates must be checked against executed source assignments before
claiming ready physics. Native recovery blockers and any required new scientific
approximation must be reported with affected contexts and concrete alternatives.

This prospectively extends ADR 0020's above-ground delivery boundary; it does not
rewrite that historical release. Systems and schedule generators remain outside
this work. BEMGen is view-only; its importer changes are a separate handover.
