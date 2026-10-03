# Independent review and disposition

2026-10-02: a separate read-only code-review agent reviewed the governing brief,
implementation from initialization through `df06c8d`, current canonical tables,
tests and source contracts. It reported no Critical issues and three Important
issues. Each Important issue was reproduced by a regression test before fixing:

- Adjacent empty API-key examples were falsely detected by a regex consuming
  newlines. Assignment whitespace now permits horizontal whitespace only;
  actual token/credential detection remains tested.
- Structurally plausible LPD drift or incomplete semantic tables could be frozen.
  Release creation now requires independent source comparison AND offline
  canonical byte-rebuild equality before creating the immutable target.
- Extracted mapping floor-area flags lacked their actual original field/value.
  Provenance now preserves the original Yes/No flag list and aggregation.

Three nonblocking validator follow-ups are deferred to a later release:

1. Exact uniqueness/coverage of source `(source_id, path)` keys, beyond current
   primary-key uniqueness, membership and count checks. Current canonical files
   have exact lock coverage; the enforced byte-rebuild release gate also catches
   drift. A standalone validation call on maliciously reconstructed metadata
   could accept a duplicate unreferenced source entry under a forged ID.
2. Version-dispatched unit contracts for historical releases. Frozen validation
   currently uses the Python SI unit constant alongside the frozen schema. The
   constant is correct for 0.1.0; future code changing that constant must preserve
   the old contract or introduce explicit schema-version dispatch first.
3. Validation of the manifest's release-version label. File hashes, inventory,
   counts, schema version and source-lock hash are verified; the release label
   itself is not independently bound to a frozen release-version contract.

The reviewer declined final DOE/PNNL generated-model/scorecard equivalence,
sufficiency of unresolved inputs for the larger zoning experiment, and future
cross-platform runs. These are retained as explicit scope limitations, not
inferred passing results. The release is a source-input research artifact;
simulation assembly and benchmark validation remain separate work.
