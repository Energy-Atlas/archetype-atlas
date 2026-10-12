# Branch and publication policy

Accepted by the repository owner on 2026-10-12 after review of all remote branches,
commit ancestry, repository protection, workflows and the Pages environment.

## Working branches and integration

`main` is the default integration branch and the sole production publisher.
Use short-lived branches for changes; new agent-created branches use `codex/`.
Existing branch names need not be renamed during work. Integrate through a pull
request, with the branch current against `main`, passing required checks and all
review conversations resolved. Protection applies to administrators too. No
human approval count is required. Force pushes and deletion of `main` are blocked.
Automatically delete the working branch after merging. Preserve historical
milestones with tags and immutable research bundles rather than active branches.

The required checks are the catalogue `build` and both Linux/Python 3.11 and
Windows/Python 3.14 jobs in the reusable research validation matrix. GitHub
branch-protection settings use the observed check names and bind them to GitHub
Actions. Do not bypass protection to publish.

## CI and production

`catalogue-site.yml` is the sole event-driven pipeline: pushes to `main`, pull
requests targeting `main`, and manual dispatch. Every qualifying run executes
the research matrix from reusable `validate.yml` and the catalogue build. The
deployment job needs both to succeed for the same commit. Required workflows
have no path filters, so documentation-only PRs still report their checks and
new schema versions cannot silently miss CI. There is no duplicate feature-push
run when a pull request is already open.

Working branches can be validated manually:

```console
gh workflow run catalogue-site.yml --ref BRANCH
```

Production publishes automatically after a validated push to `main`. A manual
dispatch can republish `main` with `deploy=true`; working branches cannot deploy
to production. The workflow condition and the `github-pages` environment both
enforce this. Only `main` belongs to that environment's deployment allowlist.
Pages uses the Actions artifact, not a `gh-pages` checkout. The stored Pages
source setting points to `main` rather than the retired first-release branch.
All successful production runs publish to the same public site; feature branches
have no production publication permission. No separate preview site is configured.
Manual validation-only runs use a separate concurrency group so they cannot
replace a pending automatic publication. Publishing runs share the production
queue; an active publication is not cancelled by a newer push.

Research verification and byte reproduction remain mandatory. Moving generated
JSON into Git or to an explicitly invoked generation workflow remains a separate
design discussion in [roadmap item 5](roadmap.md#5-discuss-a-lighter-site-and-decoupled-generation).

## Cleanup inventory

The pre-change production commit was `c54b428`. All branches below were verified
as ancestors of that commit and had no unique work to merge:

| Completed branch | Head | Disposition |
| --- | --- | --- |
| `feat/catalogue-site` | `aff4d3f` | Remove production access; delete branch |
| `feat/schedule-resolution` | `403ea28` | Remove production access; retain existing `v0.3.0` tag; delete branch |
| `feature/dto-json-v2` | `bac6145` | Delete branch |
| `feature/query-dto` | `c1538e3` | Remove production access; delete branch |
| `feature/ui-design` | `c54b428` | Remove production access; retire clean checkout; delete branch |
| `research/first-release` | `b421f41` | Remove production access; preserve archive tag; delete branch |
| `research/full-typology-coverage` | `2f3f7a9` | Preserve archive tag; delete branch |
| `gh-pages` | `b421f41` | Remove obsolete source setting; delete branch |

`fix/program-consistency` was nine commits ahead of `main` at `be942ec`, with no
divergence. It carries Program JSON v3 and its evidence. Add the policy/workflow
changes here, verify through a pull request, merge, then retire this branch too.
Deletion does not remove immutable research release directories or retained
commit history. Preserve needed local ignored files before retiring a checkout.

The publication review and deployed commit are recorded in
[the publication receipt](reviews/program-v3-publication.md).
