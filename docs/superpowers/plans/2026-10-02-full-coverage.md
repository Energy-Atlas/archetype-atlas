# Full typology coverage implementation

Spec: docs/superpowers/specs/2026-10-02-full-coverage-design.md
Governing specification: docs/AGENT_RESEARCH_BRIEF.md
Execution: inline, autonomously authorized by the user's brief and extension request.

1. [x] Lock missing commercial source inputs and residential fixture; verify
   checksums. Preserve source revisions and frozen v0.1.0.
2. [x] Write failing coverage/residential-binding/version compatibility tests.
   Extend schema and extraction, including exact selected-option references and
   explicit runtime gaps. Validate Medium Office and residential pilot first.
3. [x] Build all types, inspect missing mappings and specialized end uses;
   strengthen source comparisons and generate machine-readable coverage.
4. [x] Run the complete suite, offline byte reproduction and staged security
   audit; obtain independent review and fix material findings.
5. [x] Update documentation/migration/release notes; freeze, verify and tag
   v0.2.0 locally. Do not push as part of this extension.

Review focus: source fixture compatibility, unreported defaults, loss of
specialized loads, coverage counts without mapped programs, older release
verification, and accurate distinction between type coverage and model readiness.

Completed locally: 38 tests, 33,173 independent comparisons, 160 locked source
blobs, fresh-download byte reproduction, both frozen release verifications and
fresh Git checkout reproduction. Independent review's four Important findings
were fixed by regression tests; no findings deferred. v0.2.0 is frozen locally;
source simulation readiness remains explicitly unresolved. Branch retained under
the user's autonomous workflow; publication/integration were not part of this task.
