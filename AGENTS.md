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

Schedule generator (`atlas_schedules`, ADR 0035): a faithful but readable port
of the upstream ComStock/ResStock schedule code. Validate against native answer
keys at engineering tolerance (fractions 1e-6, annual totals 0.01 %, discrete
outcomes identical with flips reported), never bit for bit. Keep an upstream
quirk only if dropping it breaks that bar. Validate requests once at the
boundary; keep verification in tests, not runtime locks or proofs. Write small
single-purpose modules with family behaviour in data, plain names and one
statement per line.

Before EVERY commit inspect the staged diff and run the staged security audit.
Never commit credentials, PII, local authentication, or restricted source data.
Use `<type>(<scope>): <imperative description>` Conventional Commits. Use a
neutral automated identity and an `Agent-Model` trailer; do not impersonate a
human. Exact runtime model details unavailable to an agent must be recorded as
unavailable rather than invented. Commit logical reversible units freely.
Routine choices are autonomous under the brief; escalate only material science,
licensing, public feasibility, or architecture ambiguities.

Branch and publication policy: `main` is the sole production publisher and must
be changed through a pull request with all required checks passing and review
conversations resolved. Do not bypass its protection. Work on short-lived branches
(new agent branches use `codex/`); delete them after merging. Automatic CI runs on
PRs targeting `main` and pushes to `main`; manually dispatch Catalogue site to
validate an unmerged branch. Production deployment, including manual deployment,
requires `main`, successful research validation and the verified site artifact.
The `github-pages` environment permits `main` only. See `docs/branch-policy.md`.

Website UI and visual styling changes follow `design/ui-design-spec.md`; its
section 0 wins over the rest. `design/` is not published. Vendored fonts in
`website/assets/fonts/` keep their OFL notices; templates live in
`website/overrides/`. Style generated pages through CSS and generators only.
