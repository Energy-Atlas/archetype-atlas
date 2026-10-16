# Construction JSON v2.0.0

Accepted unified above-ground construction sets, frozen on the feature branch.
Site integration and protected-main publication remain pending. Ground,
foundation-dependent assemblies, systems and the BEMGen translator are deferred.

Coverage: 224 source definitions, 4,798 supported climate/reference contexts,
4,868 assemblies, 858 materials and 8,014 evidence records. The source-identity
denominator is 5,092 (224 definitions plus 4,868 assemblies), all ready.
Of the assemblies, 3,429 participate in supported prototype selections;
1,439 additional source-table recipes have complete physics and provenance but
no recovered prototype mapping. They are retained separately, without invented
applicability. Unsupported source climates remain unsupported.

## Files

catalogue.json contains source definitions, contexts and common metadata.
component_configurations.json and selector_receipts.json contain interned
assignment configurations and source selections. assemblies.json, materials.json
and evidence.json contain shared resources. Together these files satisfy the
reconstructed-catalogue schema in schemas/construction-catalogue-v2.schema.json.
The raw catalogue.json header alone is not a self-contained catalogue.

index.json supports source/climate/reference selection. completeness.json records
coverage and validation. manifest.json locks input and output SHA-256 hashes and
byte counts. examples/ contains complete selected Medium Office and residential
documents matching schemas/construction-json-v2.schema.json.

## Use and reproduction

From the repository root, load the frozen tables and verify every file checksum:

    from scripts.construction_set_release import load_release, hydrate_context
    release = load_release()
    document = hydrate_context(release, context_id)

The CLI exports a standalone document from frozen v2 tables only:

    python -m scripts.construction_set_release --context-id ID --output selected.json

Optional --variant source-definition-id/selector=assembly-id selects a retained
source alternative for its supported context. Invalid contexts or ambiguous
consumer matching must fail explicitly; BEMGen supplies actual geometry.

To rebuild or compare exact UTF-8/LF release bytes, using locked v1 inputs:

    python -m scripts.construction_set_release
    python -m scripts.construction_set_release --check

Both commands validate every context and selector alternative; they do not run
native source recovery, program generation, site builds or CI. Schema, physical,
reference, provenance, source-equality and hydration checks cover all resources.
V1 assemblies/materials and fixed ACH are unchanged. Preserve LICENSE and all
sources/licenses notices. Original Atlas work remains unlicensed by user choice.
