# Program JSON v3 publication and branch-policy receipt

Publication preparation: 2026-10-12.

Program implementation: `15be6bb`; source recovery: `6038df7`. The committed
[completeness receipt](program-json-completeness.json) records 1,900 ready exports,
zero failures and zero open decisions within the accepted scope. Examples are
in [the v3 example directory](../examples/program-json-v3/medium-office.defaulted.json)
and [the residential example](../examples/program-json-v3/residential.defaulted.json).
The [v3 contract](../program-json-v3-contract.md) records bindings and exclusions.

The previous successful production publication was `c54b428` on 2026-10-07.
The new publication is integrated through a protected pull request rather than
giving the program-consistency branch production access. Its build checks the
v3 schema, source recovery, aggregation and completeness tests as well as the
catalogue and browser tests. Research validation reproduces the completeness
receipt and frozen releases on Linux and Windows. Production requires all three
checks on the same commit; the deployment log identifies the resulting merge
commit and artifact.

## Repository settings applied before integration

- Production environment allowlist reduced from six branches to `main` only.
- Pages remains Actions-based; its stored source changed from
  `research/first-release` to `main`.
- `main` requires a pull request, current required checks and resolved review
  conversations; administrator enforcement is enabled. Human approval count is
  zero. Force pushes and deletion are disabled.
- Automatic deletion of merged branches is enabled.

## Verification record

Local checks before integration: actionlint v1.7.12 passed for both workflows;
38 focused v3 schema/completion/completeness/recovery/triage/aggregation tests
passed. The actionlint archive was verified against the official SHA-256
`6e7241b51e6817ea6a047693d8e6fed13b31819c9a0dd6c5a726e1592d22f6e9`.
Independent deployment review found that a manual validation-only run could
displace a pending main publisher. Its concurrency group is now separate from
publication runs; workflow lint was repeated after this fix.
Pull-request results, the successful deployed commit and live
Medium Office/residential checks remain subject to their observed results. A build or pushed branch alone
does not establish publication. GitHub's immutable workflow/deployment records
are the authoritative links for the final deployed commit.

## Cleanup preservation

All eight completed branches were deleted locally and remotely after confirming
they are ancestors of pre-publication `main`; their heads are recorded in
[the branch policy](../branch-policy.md). Both research heads were preserved and
verified remotely under `archive/research-first-release` and
`archive/research-full-typology-coverage` before deletion. The clean UI worktree
was retired after preserving all of its ignored build/cache directories locally.
Existing release tags and all frozen bundles remain unchanged.
