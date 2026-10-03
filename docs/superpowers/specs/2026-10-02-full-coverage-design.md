# Typology coverage extension

The user authorizes extending v0.1.0 to all DOE Reference and PNNL commercial
typologies and detached, attached, multifamily and manufactured residential
classes, under the governing research brief's autonomous workflow.

Use the same pinned upstream revisions. Expand model selection using exact
prototype_inputs rows, never filename guesses. Cover the union of the DOE
16-type and PNNL 16-type lists across the five existing templates. This is
Standards-derived source-input coverage, not direct DOE/PNNL IDF equivalence,
every published code edition, or completed simulation inputs.

Add deterministic residential configurations from the public ResStock SDR
minimal buildstock fixture, preserving complete selected options and exact
option/measure bindings. Enumerate all supplied records instead of selecting
statistical representatives or independently combining dependent parameters.
Normalize directly reported area, occupants and base thermostat temperatures;
retain envelope, HVAC, appliances, infiltration and schedule arguments in
referenced option rows with original units. Do not invent hourly profiles,
convert ACH50 to natural infiltration, or apply unexecuted HPXML defaults.
Clearly label source fixture configuration status and unresolved runtime inputs.

Add a residential_archetypes table and source-binding validation in schema
0.2.0. Preserve existing field meanings and identifiers. Older frozen snapshots
must still verify using their own table inventory, schema and selection.
Add a machine-readable coverage report with explicit expected and observed
typology sets and per-template counts. Full means those named suites/classes;
it does not mean every stock combination or simulation-ready completeness.

Specialized supermarket refrigeration and healthcare process loads must remain
visible as source evidence, with unsupported normalization documented.

Acceptance: full named typology coverage; no unexplained lost source spaces;
exact residential option resolution; provenance, schema, physical, schedule,
source comparison and offline reproducibility pass; v0.1.0 unchanged; reviewed
and frozen v0.2.0 with Conventional Commits and agent trailers.
