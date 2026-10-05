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

## Coverage-first schedule supplement — 2026-10-04

Published implementation and `resolution-v0.3.0` tag: `6a7be09`, on
`feat/schedule-resolution`. Research branches remain unmerged.

- [Windows/Linux validation](https://github.com/Energy-Atlas/archetype-atlas/actions/runs/37190981569)
  passed: 75 Python tests, schema/physical/referential/schedule/provenance checks,
  byte reproduction, 33,173 primary-source comparisons, all historical atlas and
  resolution snapshots, 30 locked primary evidence files and security audit.
- [Catalogue build and deployment](https://github.com/Energy-Atlas/archetype-atlas/actions/runs/37190981539)
  passed: eight JavaScript tests, 39,830 source schedule selections, strict build,
  links/fragments/assets, publication size and Chromium checks. Global search
  retains all 14,870 record titles and guide text; full entry evidence remains
  on each page and in canonical downloads. Built size: 978,986,697 bytes locally.
- Two independent site-source generations produced 30,393 byte-identical files.
  All 83 pre-existing residential profile/index artifacts match supplement v0.2.0.
- Live verification matched 19 served artifact hashes, including all three
  supplement manifests/indexes, v0.3.0 resolutions, fixed recipe tables, annual
  fixed plot values and the shared profile download map. Public search and daily/
  annual refrigeration plots passed with no browser errors. The low-rise
  apartment exposes only its selected refrigerator in the fixed-profile view.

Supplement v0.3.0 has 2,125 resolution rows for 754 records: approved zero gas
equipment schedules/densities for 713 programs; five fixed refrigeration defaults
for three zero-occupant dwelling fixtures; and one explicitly absent freezer zero.
The active non-cavity assessment retains 523 commercial schedule gaps: 485 water
and 38 thermostats. Other residential end uses/availability overlays remain
documented. Full or near-full deterministic coverage precedes generator shipping.

The [release notes](release-notes-resolution-v0.3.0.md) document new schema enums,
SI density units, fixed-reference evaluation and preserved snapshot inventories.
[ADR 0006](adr/0006-deterministic-coverage-release.md) records the proposed
source-conserving hot-water equivalent and its existing Medium Office curve
candidate. Program allocation remains a separate verification step.


## Program water equivalent and release scope — 2026-10-04

Data/decision implementation and `water-v0.1.0` tag: `63885ec`. Portable archive
delivery: `38e4769`. Both are on `feat/schedule-resolution`; research branches
remain unmerged, and no published tag or frozen snapshot was rewritten.

- [Windows/Linux validation](https://github.com/Energy-Atlas/archetype-atlas/actions/runs/37237145237)
  passed: 84 Python tests, schema/physical/referential/schedule/provenance checks,
  byte reproduction, 33,173 locked-source comparisons, all historical atlas and
  resolution snapshots, the water pilot and security audit.
- [Catalogue build and deployment](https://github.com/Energy-Atlas/archetype-atlas/actions/runs/37237145220)
  passed: eight JavaScript tests and 39,830 source schedule selections, frozen
  contracts, strict MkDocs build, links/fragments/project-subpath assets,
  publication size, Chromium and deployment. Local built size with the corrected
  archive: 988,564,492 bytes.
- The seven-file primary water evidence lock was independently fetched and
  verified. An independent water freeze reproduced every frozen file byte for
  byte. The new schema preserves source rules, dates, selectors, design days,
  indices and field-level evidence; historical releases retain their hashes.
- Live HTTPS verification matched eight exact artifacts, including the canonical
  equivalent, schema, manifest, source lock, complete ZIP, office and derived
  schedule packets and per-record coverage inventory. Original/equivalent plots,
  the dedicated provenance page, gas notes and scope/coverage guides passed with
  no browser errors. Plotted hourly curves include a repeated hour-24 endpoint;
  source draw equals equivalent fraction times 0.57 at every plotted interval.

The pilot attaches to the existing Medium Office 90.1-2013 office program and
conserves its mixed fixture demand. It creates no extra restroom program and
closes zero missing schedules because that office already had a source curve.
The original curve and source nulls remain available beside derived/resolved
values. The documented 713 zero gas-equipment schedules/densities apply to the
reviewed program recipe, independently of building heating/water-heating fuel.

The release-scope policy excludes sampled HVAC equipment unavailability and
complete magnitudes/full-model controls. Near-full deterministic coverage still
precedes parametric-generator delivery. Active commercial coverage is 4,615 of
5,138 schedule fields (89.8%), with 485 water and 38 thermostat gaps. Residential
coverage is 473 of 574 assessed profile fields (82.4%), with 101 missing pairs;
EV/exterior lighting and specialized end uses retain separate applicability
reviews. No near-full milestone is claimed.

See [release notes](release-notes-water-v0.1.0.md),
[ADR 0007](adr/0007-program-water-equivalents.md),
[public water guide](https://energy-atlas.github.io/archetype-atlas/guides/hot-water/)
and [public coverage guide](https://energy-atlas.github.io/archetype-atlas/guides/coverage/).
Water manifest SHA-256:
`85f870364bdee8fb718a851e5ce392c8049d96173025cdcbc4c6f6ccc3ca97d1`.
Portable snapshot ZIP SHA-256:
`27d189b5f099b153e656ab3df9a1f1c5eb877b2c37cfbf9878c1c7031d5a8a30`.

## Reviewed schedule completion — 2026-10-04

Published and tested commit: `a82e5c7` on `feat/schedule-resolution`. Annotated
tags `resolution-v0.4.0` and `completion-v0.1.0` identify the verified tree.
Research branches remain unmerged; prior tags and frozen snapshots are unchanged.

- [Windows/Linux scientific validation](https://github.com/Energy-Atlas/archetype-atlas/actions/runs/37248120174)
  passed **97 tests on each OS**, canonical byte reproduction, 33,173 source
  comparisons, all historical snapshots and repository security. Every local
  implementation commit also passed the staged security audit.
- [Catalogue build and deployment](https://github.com/Energy-Atlas/archetype-atlas/actions/runs/37248120414)
  passed: frozen contracts, eight JavaScript tests, schedule parity, strict
  MkDocs build, every link/fragment, publication size and Chromium behavior.
  The local verified artifact is **955,861,081 bytes**. The HTML hook preserves
  literal regions and links while reducing repeated template indentation.
- A clean four-lock cache reproduced the commercial packet, including all 34
  geometry witnesses. The hosted workflow explicitly fetches the base source
  lock as well as schedule, water and completion evidence locks.
- Independent repeated freezes matched all 13 commercial-completion and 114
  supplement files byte-for-byte. Eight locked source-phase control cases and
  upstream vacancy/exterior default application were executed and verified.
  Independent code and site reviews found no material findings.
- Live HTTPS verification matched both manifests and **every archived file**
  against the frozen trees. The stored commercial ZIP also matched local bytes;
  the compressed supplement ZIP was verified through its complete canonical
  inventory. The historic water ZIP retained its published hash. Live plots
  matched exterior/refrigeration source expansions and both conserved fixture
  curves, including their repeated hour-24 endpoints.

The [fixture catalogue](https://energy-atlas.github.io/archetype-atlas/commercial-completion/)
preserves 217 draw paths, 28 recipes and 59 unallocated services. Source-supported
demand attaches to existing programs; 206 reviewed absences have zero profiles.
**279 commercial program-water allocations remain unknown**. Active commercial
coverage is 4,859/5,138 fields (94.6%). All 574 assessed residential fields and all
41 dwelling exterior-lighting profiles are supplied. Missing stochastic columns
alone do not establish appliance absence. Sampled HVAC unavailability, complete
magnitudes and full-model controls remain excluded; inactive zone evidence is
limited to inspected pre-sizing phases at climate 4A.

Excluded end uses have no active schedules, catalogue entries, plots or coverage
denominator. Historical public option addresses point to source archives without
being indexed. Original snapshots and source nulls retain their original meaning.
No full-stock or complete-model equivalence claim is made; parametric generators
remain deferred. See [release notes](release-notes-v0.4.0.md) and the
[current public coverage](https://energy-atlas.github.io/archetype-atlas/guides/coverage/).

Live supplement ZIP SHA-256:
`33eebbc773096275ebedff80d2f6f0d1261666df4e97d1266806bf8262310202`.
Live commercial ZIP SHA-256:
`318155e78a5334c89983cb6ad4f95c17952e6c71bd26115f9b4b6f588bdddaf7`.
Manifest hashes are recorded in the release notes and validation receipt.
