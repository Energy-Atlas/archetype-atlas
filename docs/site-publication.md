# Initial catalogue publication

Verified on 2026-10-03 at
<https://energy-atlas.github.io/archetype-atlas/>.

Publisher branch: `feat/catalogue-site`. Published implementation commit:
`5fd0d2b3fc6ca7c2977c91612a7fad0ee6507ae2`.
No research branch was merged. Frozen v0.1.0 and v0.2.0, their schemas and
canonical source data are unchanged.

## Automated verification

- [Catalogue build and deployment](https://github.com/Energy-Atlas/archetype-atlas/actions/runs/37120455617): success.
  It verifies both frozen manifests, Python/Node presentation contracts,
  schedule parity, strict MkDocs generation, every internal link/fragment and
  Chromium interactions before uploading and deploying the same artifact.
- [Atlas validation](https://github.com/Energy-Atlas/archetype-atlas/actions/runs/37120455598): success
  on Windows/Python 3.14 and Linux/Python 3.11, including locked source retrieval,
  all tests, schema/physical/provenance validation, reproduction, comparison,
  coverage, both release manifests and security audit.
- Local final suite: 50 Python and seven Node tests pass. All 39,830 inspected
  day/date selections across 569 schedules agree with the canonical Python
  schedule inspector. Two complete generations produced 30,180 identical files.
- Live HTTPS checks: catalogue filters and URL restoration, Medium Office
  plots/design-day selection/CSV, residential unavailable-profile state, no
  browser errors or failed site responses. Seven served files match local bytes:
  site manifest, both catalogue indexes, browser scripts, locked Plotly and the
  representative Medium Office JSON packet.

Live site-manifest SHA-256:
`8a3f2c6b7c24a62a1ea80f5063ee3bcf4d2c6e2c4204c013bed3b9f7593205d5`.
v0.2.0 catalogue index SHA-256:
`ac189b165b9e031e6cbe2e8e965c16641bf3c15d108da4fc8a188e0249ee8c9f`.

## Hosting and scope

Pages uses workflow-based deployment with HTTPS enforced. Its existing default
branch allowlist is retained and the designated publisher branch is added.
The workflow receives administrative permissions neither during build nor
deployment. See [the build guide](site-build.md) for reproduction and policy.

v0.2.0 exposes 8,959 catalogue entries, 83 commercial building/template
overviews, 41 residential configurations, 768 program records and 569 schedules.
v0.1.0 keeps its own URLs and downloads. Catalogue coverage does not establish
complete simulation readiness or generated-model equivalence. Existing/code
families, conditional applicability, missing inputs and original field evidence
remain visible. Original work remains unlicensed; upstream notices are retained.

The [review record](site-review.md) covers three corrected defects and the
[ADR](adr/0003-release-backed-catalogue-site.md) records implementation decisions.
