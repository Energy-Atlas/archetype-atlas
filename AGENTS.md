# Repository operating rules

Read `docs/AGENT_RESEARCH_BRIEF.md` in full; it governs this repository.
The atlas supplies deterministic energy semantics for zoning-LOD experiments,
not population weights or geometry. Prefer official primary sources; preserve
existing-stock versus code/prototype distinctions. Pin source revisions and
SHA-256 checksums; never silently guess missing inputs or merge stock variants.

Canonical JSON tables use SI units and schema versioning; CSV is a generated
inspection export. Every extracted field must have a source locator, original
unit/value, transformation, extraction date, and interpretation note. Null means
unknown or not reported, never implicitly zero. Preserve schedule rule dates,
day selectors, design days, and source order. Document schema decisions in ADRs.

Use Python scripts to fetch, build, validate, compare, and freeze releases.
Validate a Medium Office pilot before expanding. Run schema, physical,
referential, schedule, provenance, and reproducibility checks before releasing.
Keep raw downloads immutable; untracked large sources require locked retrieval.
Retain upstream license notices; original work is unlicensed by user choice.

Before EVERY commit inspect the staged diff and run the staged security audit.
Never commit credentials, PII, local authentication, or restricted source data.
Use `<type>(<scope>): <imperative description>` Conventional Commits. Use a
neutral automated identity and an `Agent-Model` trailer; do not impersonate a
human. Exact runtime model details unavailable to an agent must be recorded as
unavailable rather than invented. Commit logical reversible units freely.
Routine choices are autonomous under the brief; escalate only material science,
licensing, public feasibility, or architecture ambiguities.

Website UI and visual styling changes follow `design/ui-design-spec.md`; its
section 0 wins over the rest. `design/` is not published. Vendored fonts in
`website/assets/fonts/` keep their OFL notices; templates live in
`website/overrides/`. Style generated pages through CSS and generators only.
