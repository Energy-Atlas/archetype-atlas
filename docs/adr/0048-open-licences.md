# ADR 0048: Open licences for original work

Status: accepted (2026-10-29, user decision: "use your preferred licenses").

## 1. Context

- Until now original code and documentation carried no licence at the owner's
  request (AGENTS.md, ADR 0003, ADR 0011). A public repository without a licence
  grants nobody the right to reuse, adapt or redistribute it.
- The goal is now public use: the construction and program library with its
  deterministic schedules, the schedule generator as an optional add-on, and BEMGen
  reading both. BEMGen is MIT-licensed.
- Most atlas content is derived from upstream sources that keep their own terms
  (`sources/licenses/`, each release's `notices/`).

## 2. Decision

1. **Code is MIT.** Python packages (`atlas_schedules`), scripts, tests, JSON
   schemas, and site and build tooling. MIT matches BEMGen and the permissive
   upstream code licences (openstudio-standards, ResStock and OpenStudio-HPXML are
   BSD-3-Clause).
2. **Original data and documentation are CC BY 4.0.** Release folders, program,
   system and reconciliation inputs, `docs/`, `website/content/` and the generated
   site. Attribution: "Archetype Atlas, Energy-Atlas" with the release number. CC BY
   asks for attribution, which a source-traceable library already does for its own
   sources, and adds no share-alike duty that could block mixing with other data.
3. **Upstream material is excluded** and keeps its terms. Notices travel with every
   release, as before.
4. **Earlier releases are covered.** The root `LICENSE` extends both grants to
   releases published before it, including 2.0.0. Release folders are not edited
   for this: 2.0.0 already took its one in-place erratum (ADR 0046 section 11), so its
   packaged `LICENSE` keeps the old text, and the next release packages the new one.

## 3. Consequences

- `LICENSE`, `README.md`, `AGENTS.md`, `CLAUDE.md`, `mkdocs.yml`, the site's sources
  page and the data-delivery guide state the new terms.
- Historical plans, ADRs and release notes that say "unlicensed" stay as written;
  this ADR supersedes those statements.
- The copyright holder is written as "The Archetype Atlas authors". If an
  institution owns the work, the owner changes that line.
