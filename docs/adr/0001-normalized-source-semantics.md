# ADR 0001: Preserve rules and source granularity

Accepted 2026-10-02 under the autonomous research brief.

The canonical artifacts are named JSON tables plus `metadata.json`; a combined
`atlas.json` and CSV exports are generated locally and ignored by Git to avoid
triplicating ~40 MB of provenance. JSON supports explicit nulls, conditional envelope records, and full
schedule rules; CSV exports make scalar tables easier to inspect. JSON Schema
2020-12 specifies structure, with Python checks for cross-table/physical rules.

Programs are climate-independent and retain source space-type distinctions.
IDs derive from source, template, building type, and source program identity.
Canonical program names use a small explicit vocabulary plus reversible slugs
of source labels; they do not merge programs with different parameters.

Envelope components replace a wide envelope row: source U-values are often
maximum assembly values, not final simulated assemblies; floor F-factors are
not U-values. Categories, climate-zone sets, WWR/projection limits, films, and
operation types remain explicit. No climate Cartesian duplication is generated.

Systems retain source HVAC descriptors, referenced schedules, and unresolved
fields as null. Capacity/fuel/subtype-dependent efficiency rules are separate;
they are not unconditional COPs assigned to systems. Building/program mappings
use observed OSM space-type assignments and zone multipliers; area fractions
remain null because this pipeline does not evaluate source geometry. Counts
are benchmark context, not mandates for parametric geometry.

Schedules retain all named source rules, units, dates, selectors, design days,
and order. Constant/hourly values remain exact; no artificial 8760 calendar or
stochastic schedule is generated. The profile helper serves validation, with
last matching specific source rule taking precedence, consistent with creating
OpenStudio rules in source order. The [official SDK constructor documentation](https://openstudio-sdk-documentation.s3.amazonaws.com/cpp/OpenStudio-3.10.0-doc/model/html/classopenstudio_1_1model_1_1_schedule_rule.html)
confirms each new rule receives highest priority. Annual/calendar interoperability requires an
explicit adapter. Holiday rules are retained even where the Ruby generator does
not apply them. This atlas exposes source inputs, not a claim of equivalence to
generated models after controls, overrides, sizing, or defaults.

Every output field has an entry in record-level provenance (source filename,
JSON index/OSM handle/TSV line, revision, original field/unit/value, transformation,
date, and interpretation). Source nulls stay null. Semantic joins are exact and
reject multiple matches. ResStock option arguments form deterministic evidence
rows; they are not joined into fabricated complete dwelling models. ComStock
option rows similarly retain measure arguments and continuation-line context.
These are evidence tables; primary program archetypes remain deterministic.

Source downloads are ignored by Git to avoid duplicating ~25 MB of upstream
blobs; an immutable checksum lock and fetch verification reproduce them. Upstream
license notices remain tracked. v0.1.0 is a source-input atlas with explicit
coverage gaps, not a ready-to-run simulation generator.
