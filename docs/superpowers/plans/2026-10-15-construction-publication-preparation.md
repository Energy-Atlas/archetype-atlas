# Construction publication preparation

> **For agentic workers:** Use superpowers:executing-plans inline. The user authorized this task after construction implementation closure.

**Goal:** Prepare the reviewed construction exports and site for the protected-main publication path, without pushing or starting CI/CD.

**Architecture:** Retain frozen detailed v2.2.0 and additive unified 1.1.0 data. Extend existing publication gates rather than change artifact generation architecture. Publish the existing two independent consumer contracts and their documented limitations.

**Tech stack:** Python, unittest, existing MkDocs/Playwright tooling, GitHub workflow YAML.

**Spec:** [Construction closure](../../reviews/construction-milestone-closure.md), [current roadmap](../../roadmap.md#current-execution-order), [branch policy](../../branch-policy.md).

## Constraints and review focus

- Work on the existing feature branch; no push, PR creation, workflow dispatch, merge or deployment in this preparation task.
- No frozen data/schema mutation, broad local program/schedule generation or full local site build.
- Retain required job identities, protected-main-only deployment and existing generation policy. Lighter delivery remains deferred.
- A publication build missing the construction catalogue must fail rather than silently skip its validation; small research fixtures may remain construction-free.
- Both detailed and unified release reproduction and direct-copy browser behavior must gate publication.
- Ground/systems, schedule-generator packaging and BEMGen translation remain deferred.

## Tasks

1. Add a failing regression for a required-but-missing construction delivery.
   Implement an opt-in required flag in the existing delivery verifier and site
   checker. Run focused delivery tests; research fixtures retain the default.
2. Add frozen construction release checks to the existing research matrix,
   construction presentation tests to the build job and the separate construction
   browser harness before artifact upload. Keep deployment prerequisites intact.
3. Finalize release notes, README/changelog and generated construction/selection
   guidance. Record exact release/schema identities, migration, limitations,
   retained licenses and the prepared-but-unpublished state.
4. Run focused Python/Node checks, refresh only local construction presentation,
   run the construction browser harness and review the final changes independently.
   Record actual evidence and unrun remote gates; audit and commit locally.

## Execution record

Base: `9433be2`. Existing clean `feature/json-completion` checkout reused.
Preflight: fresh generation already calls construction integration; site_check
already compares frozen packets, but accepts a missing construction marker for
fixtures. Existing CI has no explicit construction release reproduction or
construction browser gate. These interfaces are extended in place.

Ruling: preparation is local and keeps the current publication architecture.
Remote checks and deployment remain a later gate, not a claimed result.

Review correction: `construction_weighting --check` requires ignored native
recovery data. CI instead calls `load_profiles()` for frozen file/input checksum
verification and reproduces unified output from those profiles. No native
runtime/recovery is added to CI. Source-profile re-execution remains maintenance
work; claiming that reproduction in a fresh checkout would be incorrect.

Completed locally: both missing-delivery regressions were observed failing and
then passing; the final 44 focused Python tests and 24 Node tests passed. A
177-page construction-only refresh generated zero program pages and zero new JSON
resources. The three-case browser harness verified exact preview/clipboard
equality for both representations, direct copying, lazy loading, unsupported
contexts and mobile/light/dark presentation. The hotel overlay check passed.
Independent review's fresh-cache finding was fixed and its empty-cache
verification path checked. Release notes and publication instructions are saved;
no data/schema changes, full build or remote actions were performed.
