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

## Selective resolutions and executed residential profiles

Publisher branch: `feat/schedule-resolution`. Implementation commit:
`4c651d3f0c6fc2f99f36412ff0610579e2c75336`. No research branches are merged;
the frozen atlas v0.1.0/v0.2.0 remains unchanged. Resolution supplement v0.1.0
has an independent schema and references the v0.2.0 manifest hash.

- [Windows/Linux atlas validation](https://github.com/Energy-Atlas/archetype-atlas/actions/runs/37158611335)
  passed, including 67 Python tests, source retrieval, schema/physical/provenance
  checks, reproduction, source comparison, coverage, all frozen manifests and audit.
- [Catalogue build/deployment](https://github.com/Energy-Atlas/archetype-atlas/actions/runs/37158611426)
  passed. It verifies both catalogues and the supplement, eight Node contracts and all
  39,830 schedule selections; it builds strictly, checks internal links/fragments
  and exercises annual/day residential plots before deploying the same artifact.
- Two independent local site generations produced 30,277 byte-identical files.
  The built site contains 918,507,503 bytes. Three actual upstream residential
  executions reproduce every frozen CSV/JSON and the profile index byte for byte.
- Live HTTPS verification passed: 11 served artifact files match local bytes,
  including both catalogue indexes, browser scripts, locked Plotly, commercial
  and residential packets, an annual profile, and supplement manifest/index.
  Public Chromium checks pass for filters/permalinks, commercial plots/CSV and
  residential annual/day plots; July 1 occupancy values equal canonical hours.
  No browser errors or failed site requests were observed.

The supplement adds 677 resolutions across 80 records and all 41 executed
residential configurations: 38 stochastic realizations, three upstream
zero-occupant skips and 41 nominal thermostat profiles. Original values remain
visible beside separately labelled resolutions, complete evidence and remaining
unknowns. Calendar plots show actual local-standard-time 2007 hourly values;
canonical JSON, exact upstream CSV and the complete licensed supplement download
are linked from record pages. The Pages environment adds only this exact publisher
branch and retains its previous two policies.

v0.2.0 catalogue index SHA-256:
`6446232cfdf4437ffd9a7d87a659387020dec9cb2554fbaf19b957d422fd730b`.
Resolution manifest SHA-256:
`b35e6035c7cf7006d0b50712a21941fcd126be62cde023de1a6567e4a11abca5`.

The [availability report](schedule-availability.md) lists unresolved fields and
their reasons; [generation boundaries](residential-generation.md) document the
station-weather proxy, upstream zero-occupant skips and nominal thermostat scope.
[ADR 0004](adr/0004-selective-resolution.md) records evidence gates, and the
[review record](schedule-review.md) records the corrected failure-lifecycle defect.
Catalogue/profile coverage continues to be distinct from full simulation readiness.
The independently versioned supplement is tagged `resolution-v0.1.0`.

## Reviewed schedule resolutions — 2026-10-04

Published implementation: `362aaad`; publisher branch `feat/schedule-resolution`.
Data/decision commit: `ae539bb`. Research branches remain unmerged.

- [Windows/Linux validation](https://github.com/Energy-Atlas/archetype-atlas/actions/runs/37184883453)
  passed: 70 Python tests, schema/physical/provenance checks, byte reproduction,
  33,173 locked-source comparisons, coverage, both atlas releases and both
  resolution supplements, stable primary evidence retrieval and security audit.
- [Catalogue build/deployment](https://github.com/Energy-Atlas/archetype-atlas/actions/runs/37184883408)
  passed: frozen contracts, eight Node tests and 39,830 schedule selections,
  strict MkDocs build, internal links/fragments, Chromium checks and deployment.
- Live HTTPS verification passed for 15 exact artifact files, including both
  supplement manifests/indexes and representative plenum/data-centre packets.
  Those packets retain original nulls beside approved constant-zero resolutions.
  Filters, commercial plots/CSV and actual residential annual/day plots pass;
  July 1 occupancy values match canonical hours. No browser/HTTP errors occurred.
- The public schedule-methods guide includes the zero-occupant default sources,
  ten raw unavailable-day options versus nine fixtures with selected affected
  equipment, and the DOE representative-city/weather-location distinctions.

Supplement v0.2.0 adds ten plenum lighting zeros and six routine data-centre
occupancy zeros: 693 resolutions across 86 records, with 1,270 commercial fields
unresolved. Excluding attic/plenum/basement source programs leaves 1,202 active
gap fields. The 41 profile artifacts and index are byte-identical to supplement
v0.1.0; no generator rerun or silent weather replacement was introduced.

The active source evidence lock uses the stable official DOE technical report,
SHA-256 `39520427c39c4a424d8b0d072c47d5bfdc248631632e880501866aae6b0d131a`.
Hosted CI identified delivery-dependent bytes in the earlier HTML page; that
receipt remains historical. All frozen release/supplement hashes are unchanged.
The future parametric-generator direction remains a documented decision, with
the interface and runtime parity contract deferred to the next discussion.
