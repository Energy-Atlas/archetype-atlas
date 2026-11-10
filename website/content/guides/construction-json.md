# Construction JSON contract

A construction set page lists every context of the set with its exports in release {{ release }}:

- **Detailed** ({{ schema:construction_set }}): the source assemblies, materials, component assignments, foundation
  ground methods, fixed reference infiltration, mass accounting, provenance and, from release 2.0.0, the PNNL
  prototype alternates.
- **Unified** ({{ schema:building_level_equivalent }}): precomputed archetype shares and simplified ordinary
  components. Every commercial set has one, the IECC commercial sets from release 1.6.0 (ADR 0045), and so do the
  ResStock dwellings' sets. From release 2.6.0 the unified documents are 4.1.0 (ADR 0065, ADR 0066): a context with an
  unconditioned attic states it in `attics`, with the conditioned boundary under the attic and an `attic_omitted_roof`
  for a model without the attic, and the openstudio-standards attic contexts state their corrected `InteriorCeiling` in
  `export_corrections`.
- **Source model constructions** ({{ schema:source_model_construction }}): the IDF-derived envelopes of the IECC
  residential and manufactured-housing prototypes, one document per climate and foundation or location. One
  document serves both representations; the site index names it as both `detailed` and `unified`.

Each document is complete and standalone: library and evidence references are resolved by the exporter. The page
shows the detailed fields shared by every context once, then each context's own fields and components; assemblies
and materials link to the template library page. On the largest sets the context fields load when asked for, from
the same store document the page would otherwise inline; each context's download is the complete document either way.

Contracts: [consumer contracts of release 1.0.0](https://github.com/Energy-Atlas/archetype-atlas/blob/main/docs/consumer-contracts-release-1.0.0.md),
[release 1.1.0](https://github.com/Energy-Atlas/archetype-atlas/blob/main/docs/consumer-contracts-release-1.1.0.md) and
the release notes in [`docs/`](https://github.com/Energy-Atlas/archetype-atlas/tree/main/docs). The exporter reads
releases {{ releases }}:

```console
python -m scripts.atlas_exports --release {{ release }} --construction SET --context KEY --representation detailed
```

Downloads carry the same canonical SHA-256 as program exports ([Program JSON contract](program-json.md#checksums)).
