# Program JSON v3 publication and branch-policy receipt

Publication verified: 2026-10-12.

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
The pre-fix full local suite passed 272 tests. The first protected PR run
(`38208867948`) then exposed a cross-runtime reproducibility error: Python 3.11's
builtin floating sum changed the active-member area normalization and resulting
control schedule hashes relative to newer Python. A real Python 3.11 regression
failed on ten `0.1` member weights, then passed after using `math.fsum`, consistent
with the other mixture calculations. The 21 focused control/completeness/aggregation
tests also passed. The regenerated Python 3.14 receipt still reports 1,900/1,900
ready, zero failures and the identical export-set SHA-256
`a81b45dc7e53ce98bf45fab2852634e591b6bc0789b656d121b29b9d168218c8`.
Only the exporter input checksum changed. Python 3.11 reproduced that exact receipt
with `program_completeness --check`. The full local suite after the fix passed all
273 tests in 683.867 seconds. Independent review found no Important or Critical
issues in the fix. The hosted gates are checked after this fix; the failed run
did not publish. Source values and accepted assumptions are unchanged.
All three required checks passed on `593728ebdb50b3805b0bf4bf97203321fbf8262b`
in [PR validation run 38212099832](https://github.com/Energy-Atlas/archetype-atlas/actions/runs/38212099832).
[PR #4](https://github.com/Energy-Atlas/archetype-atlas/pull/4) was merged normally,
without bypassing protection, at 2026-10-12 06:49:50 UTC. Its merge commit is
`d3c1b3bca09aae9e185b17dc4c61f8e50bb19bf4`. The working branch was then retired
locally and remotely.

## Observed production publication

[Main run 38214474243](https://github.com/Energy-Atlas/archetype-atlas/actions/runs/38214474243)
passed both research gates, the catalogue build and the Pages deployment on that
merge commit. The catalogue checks include all links and browser behavior; both
research runtimes reproduced the complete receipt and frozen releases. Production
publication was followed by independent HTTP checks at 2026-10-12 07:21:33 UTC.

The [live verification receipt](program-v3-live.json) records four published
raw/ready resources and their SHA-256 checksums. The public schema exactly matches
the committed v3 schema. Compressed and decoded lengths and resource hashes match
the page disclosures; all four payloads validate against the v3 schema. Ready
Medium Office and residential payloads exactly match the reviewed examples,
including their source/default distinctions, exclusions and required simulation
bindings. The published example files also match, and the live connector guide
reports version 3.0.0. There are no additional assumptions from publication.

Live examples: [Medium Office](https://energy-atlas.github.io/archetype-atlas/definitions/program-8c35a40eb0181596e0bfcac4/)
and [residential](https://energy-atlas.github.io/archetype-atlas/definitions/program-0079ce7b163bdb1bd0154dbe/).
The [connector guide](https://energy-atlas.github.io/archetype-atlas/guides/program-json/)
includes the source/default contract and consumer bindings. The roadmap now records
publication as complete; constructions and systems are the next contract task.

## Cleanup preservation

All eight completed remote branches were deleted, and their local counterparts
retired, after confirming they are ancestors of pre-publication `main`; their heads are recorded in
[the branch policy](../branch-policy.md). Both research heads were preserved and
verified remotely under `archive/research-first-release` and
`archive/research-full-typology-coverage` before deletion. The clean UI worktree
was retired after preserving all of its ignored build/cache directories locally.
Existing release tags and all frozen bundles remain unchanged.
