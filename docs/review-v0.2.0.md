# v0.2.0 independent review and disposition

A separate read-only reviewer assessed v0.1.0..f86df34 and the extension's current
generated data/documentation against the governing brief and design. It found no
Critical issues and four Important issues. The following fixes retain the
source-input scope and are covered by targeted regressions:

1. Missing display-case and specialized generator evidence: added all five
   ref_cases tables and supermarket/hospital/outpatient/refrigeration routines
   to the immutable lock and specialized_rules export. Source code is inert
   evidence; no conditional process load is silently applied. Regression:
   test_display_case_and_generator_evidence_retained.
2. Unidentified numeric refrigeration units: every numeric field now has an
   explicit unit_interpretations entry. It cites the locked generator's first
   conversion declaration and lines, or records an unresolved status. Upstream
   numeric intent remains unverified, including SI-looking values interpreted
   as F by the generator. No conversion is guessed. Regression:
   test_refrigeration_numeric_units_have_explicit_interpretation_status.
3. Incomplete residential bindings could pass validation/comparison: validation
   now requires all matching references and a complete disjoint option partition;
   independent comparison reconstructs exact argument-bearing TSV lines and
   unmatched/no-argument classifications. Regression:
   test_incomplete_residential_binding_partition_rejected.
4. Provenance retained excluded demographic columns: source-row evidence is now
   projected onto energy and physical context fields before provenance creation.
   Regression: test_source_configuration_provenance_excludes_demographic_columns.

An additional coverage mutation demonstrated that excluded spaces could coexist
with a completeness flag. The audit now reports incomplete when any source space
is excluded. Regression: test_source_space_exclusions_prevent_complete_coverage_claim.

The reviewer also identified a snapshot documentation omission. The new release
copies its current review, verification and source-comparison evidence alongside
the historical review document. No review finding is deferred for v0.2.0.

Independent inspection confirmed all 83 commercial selections exactly match
pinned prototype_inputs and every parsed source space appears in mappings.
The original v0.1.0 snapshot remains unchanged and passes its frozen verification.
Final regression suite and retrieval/rebuild evidence are recorded in
validation/verification-v0.2.0.json. The fixes were validated by regressions and
the full suite; no second reviewer pass is claimed.

Not established: OpenStudio/EnergyPlus execution, direct DOE/PNNL IDF equivalence,
complete residential HPXML runtime semantics, or remote cross-platform CI.
The 524 unmatched source option instances and six base thermostat overlaps remain
explicit scientific limitations, not silently resolved defaults.
