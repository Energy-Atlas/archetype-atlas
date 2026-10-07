# ADR 0013: Element definitions and a three-kind catalogue

Date: 2026-10-07. Status: accepted implementation of the approved design.

Publish independently versioned canonical definition bundles and delivery v2.
The primary kinds are program, construction and hvac_system. Schedules, materials,
components, services and provenance are supporting resources. Retain v1 and frozen
source archives without changing their meaning.

Use per-field SI values with explicit status, evidence and required operands.
Source/reviewed is an evidence view; composed/assumed describes derivation.
These axes are independent. Unknown values cannot establish element identity.
Programs distinguish alternate representations from additive physical demands;
services have stable ownership and must be instantiated once.

Construction packages select corresponding elements and scoped air requirements.
Assemblies retain ordered materials; U targets alone do not establish identity.
HVAC records are model-independent fixed performance definitions; conditional
rating tables retain their predicates instead of selecting arbitrary capacities.
No model sizing or consumer geometry belongs in the library.

Whole-dwelling programs are valid without room-area mixtures. Generic assumptions
are allowed only for unresolved internal and ground-contact constructions.
Other unresolved data remain explicit. The Medium Office pilot gates expansion.
