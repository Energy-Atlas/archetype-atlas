# ADR 0024: Ship complete construction sets; retain partial scopes as evidence

Date: 2026-10-14. Status: accepted by the user in chat.

## Decision

The current construction distribution exposes 177 complete sets (136 commercial
building sets and 41 residential whole-dwelling sets), with 3,320 supported
climate/reference contexts. It stops offering 47 standalone `space_type` sets.
Space/story conditions remain inside the complete sets; scope remains source
metadata. All four SmallHotel 2019 specific guest-room variants and the approved
generic GuestRoom applicability remain unchanged. BEMGen owns future matching
and translation.

Distribution v2.2.0 is a deterministic selection layer over immutable v2.1.0 and
v2.0.0. Consumer JSON schema remains 2.0.0: no component rules, resources,
selection receipts, infiltration, source provenance or geometry instructions
change. The current loader/CLI is `scripts.construction_distribution`; previous
loaders remain historical source APIs. Historical releases are not rewritten.

## Coverage proof and exceptions

For every standalone source context with a supported building parent at the
same reference and climate, verify containment of complete assignment objects
and complete selection receipts (including candidate alternatives). Only the
additional Atlas applicability extension is removed for proof comparison.
This verifies 1,470 source contexts before producing the current distribution.
Missing or changed embedded rules fail the build.

Eight contexts have no supported complete building parent: legacy MediumOffice
and LargeOffice, DOE Ref Pre-1980 and DOE Ref 1980-2004, climates 0A and 0B.
Their original Plenum definitions, contexts, selections, fixed ACH, materials,
assemblies and provenance are preserved in `source-evidence.json`, explicitly
`consumer_selectable: false`. Their existence does not extend building climate
coverage. All 47 original partial definitions remain in frozen source releases.

## Site and delivery

Remove partial sets from both construction finders, current construction
packets, record routes, object registry, search entries and current selective
query results. Retained assembly pages link to complete parent sets, retaining
the original source-space identity as evidence text. The current query snapshot
is updated for construction only; program/system indexes and supporting artifacts
are reused. Generated superseded snapshots and construction packets are removed
to preserve the site's existing current-only publication rule. Immutable research
releases in the repository remain historical evidence.
The eight unsupported contexts have a labelled source-evidence download.

Remove Set scope and Evidence view controls from construction finders only.
Every construction entry has source evidence; that view selector did not change
results. Retain source evidence metadata and program/HVAC controls. Keep Search,
Building type, Vintage/standard/source and Climate. Climate selection controls
supported applicability, assembly selection and fixed reference ACH; identical
assemblies can share resources without erasing full climate labels.

## Validation and publication boundary

Use focused tests for embedded-rule containment, archive integrity, construction
only query updates, filter rendering, retirement and site copying. Refresh only
construction pages/finders and their counts/guides in the marked local build.
Verify current packets, resources and copied pilot/hotel JSON against the frozen
source. Do not regenerate programs, recover native models, perform a full site
build, push, dispatch CI/CD or publish. Ground and systems remain outside scope.
