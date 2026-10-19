# Foundation publication preparation

Date: 2026-10-19. Branch: `codex/foundation-ground`.
Preparation baseline: `e9a982d2e8cae9d2b0fad369b1c32d11a273baa6`.
Status: prepared and validated locally; no push, PR, hosted CI/CD or deployment.

This records publication-preparation tasks 1–3. It does not replace the later
clean-checkout rehearsal, protected-main checks or live publication verification.
See the [release notes](../release-notes-construction-foundation-v1.0.0.md) for
versions, coverage, consumer migration and remaining publication gates.

## Changes

- Update the browser harness to use frozen detailed 3.0.0 / unified 2.0.0 pairs
  and account for the selected foundation summary's initial detailed-packet load.
  Preview and direct clipboard actions reuse each verified representation packet.
- Add exact combined-release/example reproduction under the existing pinned
  Windows x64 / CPython 3.14.7 producer. Both research platforms validate all
  combined pairs and verify frozen source, airflow and native-smoke receipts.
  These gates do not execute native extraction or EnergyPlus or download runtimes.
- Verify combined manifest/resource/input closure and foundation presentation
  tests in the existing build job. Preserve required job names, triggers,
  deployment dependencies and the main-only publication guard.
- Update README, changelog, roadmap, build guidance and release/migration notes.
  Foundation publication and BEMGen consumer acceptance remain explicitly pending.

Frozen data, schemas, source records, historical releases and local handover
packets are unchanged. BEMGen remains read-only. The ignored v7 packet is not a
CI or site-build dependency; no packet revision is needed for these changes.

## Local verification

- Reproduced the old browser failure before changing the harness: it incorrectly
  expected no construction packet on page entry. All four new publication
  regressions also failed before implementation and passed afterward.
- Passed 29 focused tests covering publication workflow policy, foundation
  hydration, construction presentation/refresh and versioned site assets.
- Passed `python -m scripts.construction_foundation_release --check --examples`
  with the pinned Windows x64 / CPython 3.14.7 runtime.
- Passed `python -m scripts.validate_construction_foundation --all`: all 3,320
  combined detailed/unified pairs, across 177 suites. Coverage remains 3,308
  executable-contact and 12 supported no-contact contexts, with zero missing
  executable physics in the supported source population.
- Passed frozen recovery, airflow and native-smoke receipt verification. The
  recovery records cover 2,625 queries, 822 commercial cases and 41 residential
  fixtures; airflow verification covers 41 fixtures and smoke receipt verification
  covers six cells. Native simulations were not rerun.
- Passed browser checks for Medium Office, Warehouse, a conditioned basement,
  an upper apartment without direct ground contact, SmallDataCenter layered ground
  and Hospital C-factor. Previews and clipboard contents match frozen exports.
  Summary hydration, one packet load per representation, missing-resource guards,
  unsupported-context behavior and mobile/light/dark checks pass.
- Both workflow files parse, changed-document relative links resolve and
  `git diff --check` passes. Fresh independent review found no actionable issues.

Ignored local evidence is in `build/local-plans/foundation-publication-*.log`,
`build/unified-construction-browser.json` and
`build/foundation-publication-smoke/`. Browser checks used the existing local
construction site; no full MkDocs, program or schedule generation was performed.
Windows local results do not claim Linux execution or GitHub-hosted checks.

## Remaining gates

1. Rehearse the release/publication path from a clean checkout and verify that
   committed inputs suffice, without local handover/recovery caches.
2. Open the protected-main PR and pass required hosted checks and review; merge
   through the repository's normal protection, deploy from main, then verify live
   exports and record the publication marker.
3. Continue BEMGen v7 testing independently and resolve any Atlas defects found.
   Do not claim consumer acceptance until its required tests pass.

Systems and schedule-generator packaging remain outside this milestone. Lighter
artifact delivery stays deferred until BEMGen testing is accepted.
