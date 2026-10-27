# Construction JSON contract

A construction set page lists every context of the set with its exports:

- **Detailed** (4.x): the source assemblies, materials, component assignments, foundation
  ground methods, fixed reference infiltration, mass accounting and provenance.
- **Unified** (3.x): precomputed archetype shares and simplified ordinary components,
  where the set has one. IECC commercial sets have no unified representation yet.
- **Source model constructions** (1.0.0): the IDF-derived envelopes of the IECC
  residential and manufactured-housing prototypes, one document per climate and
  foundation or location.

Each document is complete and standalone: library and evidence references are resolved
by the exporter. The page shows the detailed fields shared by every context once, then
each context's own fields and components; assemblies and materials link to the
template library page.

Contracts: [consumer contracts of release 1.0.0](https://github.com/Energy-Atlas/archetype-atlas/blob/main/docs/consumer-contracts-release-1.0.0.md),
[release 1.1.0](https://github.com/Energy-Atlas/archetype-atlas/blob/main/docs/consumer-contracts-release-1.1.0.md) and
[release notes 1.4.0](https://github.com/Energy-Atlas/archetype-atlas/blob/main/docs/release-notes-atlas-v1.4.0.md).

```console
python -m scripts.atlas_exports --release 1.4.0 --construction SET --context KEY --representation detailed
```
