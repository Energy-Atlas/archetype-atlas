# Construction-set v2 review

Steps 1–3 are implemented for review on `feature/json-completion`. The schema,
exporter and complete examples are ready for comments; site integration and
publication have not started. BEMGen owns the translator.

## Shared structure and source metadata

Both examples have `kind: construction_set` and the same nineteen component type
keys. Header and `source` fields follow Program JSON naming and climate/vintage
semantics. Climate/reference choices are already resolved. Source identity and
stock/code distinctions remain explicit. There is no generic `required_bindings`
list or `deferred_scope` field.

- [Medium Office JSON](../examples/construction-json-v2/medium-office.json)
- [Residential JSON](../examples/construction-json-v2/residential.json)
- [Schema](../../schemas/construction-json-v2.schema.json)
- [Contract and reproduction](../construction-json-v2-contract.md)

**Your comments:**

<!-- comments:construction-set-v2-structure:begin -->

<!-- comments:construction-set-v2-structure:end -->

## Component assignment semantics

Medium Office includes exterior/interior walls, roof/floors, glazing/doors,
partitions and tubular daylight constructions in one set. Its source Plenum
floor override is embedded alongside the building default. Targets declare BEM
surface types/boundary conditions; rules declare source scopes and fixed/operable
window choices. Absent overrides inherit the building default. Compatibility-only
Office lookups do not override the selected wall. Ambiguous or unmatched cases
must produce an error in BEMGen rather than an arbitrary assignment.

The original 224 source definitions remain indexed, including explicitly partial
space sets. A whole-building set already contains its applicable source space
overrides; consumers do not download separate sets for exterior/interior walls.

**Your comments:**

<!-- comments:construction-set-v2-assignment:begin -->

<!-- comments:construction-set-v2-assignment:end -->

## Geometry and unchanged physics

Residential rules preserve multiple wall/window variants and parent-wall
adjacency, source-compatible roof pitch, overhang dimensions, partition CFA
scaling and ordinary interstory scaling. `source_reference_reversed` is source
assignment evidence, not an instruction to reverse the selected recipe again.
Source member IDs aid correspondence; BEMGen supplies actual geometry and uses
an explicit assignment identity or a unique compatible rule.

Medium Office contains 19 assemblies, 22 materials and 197 evidence resources;
residential contains 12 assemblies, 16 materials and 32 evidence resources.
Selected fixed ACH remains 0.1396961316 and 0.671608067 ACH respectively. Frozen
source physics, source conditions and target/attained distinctions are retained.
The review manifest locks schema/input identities and example bytes.

**Your comments:**

<!-- comments:construction-set-v2-geometry:begin -->

<!-- comments:construction-set-v2-geometry:end -->
