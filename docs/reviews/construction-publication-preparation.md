# Construction site and release publication preparation

Date: 2026-10-15. Branch: `feature/json-completion`. Base: `9433be2`.
Status: prepared locally; no push, PR, CI/CD, merge or production deployment.

The user authorized task 2 after
[implementation closure](construction-milestone-closure.md). The candidate
preserves all frozen construction data, schemas and exporter identities. It adds
publication gates and documentation, not another research data version.

## Candidate and changes

- [Release notes](../release-notes-construction-v2.2.0.md) identify detailed
  distribution v2.2.0 / consumer schema 2.0.0, its immutable base and applicability
  delta, additive unified release/schema 1.1.0 and supporting profile release
  1.1.0. Coverage remains 177 complete sets and 3,320 supported contexts.
- README/changelog and generated construction guidance describe the two exports,
  embedded rules, retired partial selections, accepted fitting limitations,
  consumer geometry/mass responsibilities and license preservation.
- `site_check --require-construction` rejects a publication without its
  construction delivery marker. The default still permits small research fixtures.
  Existing packet/resource equality checks apply when the catalogue is present.
- The existing research matrix now checks reproduction of the detailed base,
  hotel applicability, complete distribution and additive unified output, plus
  frozen supporting-profile and declared input hashes.
- The build job now runs construction presentation tests and separate browser
  checks of both detailed/unified copy representations before artifact upload.
  Required job identities, event policy and main-only deployment remain unchanged.

Generation remains in the current pipeline. No artifact-delivery architecture,
schedule-generator, ground/system or BEMGen work is included.

## Local verification

- Two new regressions first failed before implementation: missing required
  construction delivery and the publication CLI's required-construction flag.
  Positive fixture delivery is also checked with the required flag enabled.
- 44 focused Python tests passed: construction presentation/refresh, versioned
  assets, HTML delivery, site delivery and active-site integration. Existing
  full construction validation remains in the closure receipt; no unchanged
  program catalogue or annual schedules were regenerated here.
- All 24 Node tests passed.
- Both workflow YAML files parsed. Main-only automatic events, deployment
  prerequisites and new construction module availability were checked locally.
  This does not claim a GitHub-hosted job result.
- The focused local refresh covered 177 construction pages / 3,320 contexts,
  zero program pages, zero new JSON resources. All construction delivery
  packets/resources matched their frozen releases.
- The construction browser harness passed Medium Office, Warehouse and
  residential cases: previews and clipboard JSON exactly matched the detailed
  and unified frozen exports, both buttons acted without dialogs, each packet
  loaded once, missing resource guards rejected invalid data, unsupported
  contexts disabled copying, and light/dark desktop/mobile checks passed.
- Hotel applicability `--check` reproduced all 143 affected contexts, with
  21 attached-recipe and 122 inherited contexts. Frozen profile verification
  passed with an empty recovery-cache directory.

Browser receipt: ignored local `build/unified-construction-browser.json`.
Screenshots: `build/screenshots/construction/`. No full local MkDocs/program/
schedule build or lengthy unchanged-program CI was run. Base-release and unified
reproduction are configured as required remote gates, not claimed as rerun during
this preparation; fresh all-context/reproducibility evidence from closure remains
linked above.

## Review correction

Independent review found that `construction_weighting --check` reads ignored
`build/equivalent-work/commercial-weights.json`. An empty-cache probe reproduced
the missing-file failure. A fresh CI checkout cannot execute that command
without native source recovery.

The final workflow uses `construction_weighting.load_profiles()` to verify the
frozen profile and input checksums, then reproduces equivalent output from the
verified profiles. An empty-cache probe passed that exact verification path.
No native source runtime is added to CI, no checksum check is weakened and no
frozen artifact is rewritten. Profile source re-execution remains a separate
maintenance operation. The reviewer reported no other actionable findings.

## Prepared PR description

Title: `Publish complete detailed and unified above-ground construction exports`

The catalogue now supplies complete above-ground construction sets with embedded
space rules and a separate one-assembly-per-semantic representation. Both cover
177 sets and 3,320 supported climate/reference contexts, retain provenance and
fixed reference ACH, and expose direct copy actions. Detailed source assemblies
remain intact; unified output retains fit errors and explicit mass/geometry
responsibilities.

Publication gates verify frozen construction outputs and supporting profiles,
reject missing construction delivery, and browser-check both representations.
Local construction closure and focused presentation/browser checks passed.
Ground/foundation and systems remain deferred. Schedule-generator work does not
block this publication or the following BEMGen test.

## Remaining publication gate

No PR has been opened. The later publication action must push the reviewed
candidate, open a PR targeting protected `main`, and pass the required `build`
and Linux/Python 3.11 plus Windows/Python 3.14 research jobs. All review
conversations must be resolved before merge. Production must use the verified
artifact for that main commit and then verify live detailed/unified exports and
their selected context. The local focused refresh is not a substitute for that
clean site build and remote gate.

BEMGen handoff/testing is the next planned integration task using existing
schedules. Lighter artifact delivery waits until the test is accepted.
