# ADR 0020: Above-ground construction first, with foundation/ground deferred

Date: 2026-10-13. Status: accepted scope and source reference geometry;
constant-ACH climate/conversion conditions open.

## Decisions

The user selected the second construction boundary: above-ground construction is
separate from a combined foundation/ground/basement axis, which includes its
below-grade assemblies. The first deliverable is a published above-ground
construction contract with 100% coverage. Ground/foundation and all system work
are deferred. This supersedes ADR 0019's requirement to finish those other kinds
before publishing the completed above-ground construction milestone; the broader
roadmap remains unfinished until its later phases are delivered.

The user accepted that foundation-dependent interface assemblies, including
floor-over-foundation insulation and rim-joist details, belong to the deferred
foundation axis. Ordinary above-ground floors and partitions remain construction.
Retain source evidence and original identities; the separation does not delete
ground records or imply zero ground heat transfer.

The user accepted infiltration-only air requirements for this construction
release. Mechanical outdoor-air and minimum total-supply requirements are
deferred with systems. Preserve their raw source evidence; do not count them as
zero or treat their unresolved values as active construction export blockers.

The user selected fixed catalogue natural ACH per construction and climate zone,
rather than ACH(t) or a scalar resolved from the consumer's actual geometry.
Store this enclosure-level value on a package/enclosure, not on an individual
wall/window material. The same selected catalogue value is reused across building
geometry and zoning variants. The user selects source archetype reference
geometry for deriving that fixed value. Recover its operands and source defaults
with provenance; do not substitute the proposed common enclosure. Climate
factors, conversion details and averaging policy remain open. Pressure-test
ACH50 and its reference pressure remain source evidence.

Earlier decisions remain: ASHRAE climate-zone/group resolution with no EPW-location
records in construction applicability; simple/detailed glazing alternatives for
one construction where needed; source-first recovery, SI and full provenance.
H and X entries remain unreviewed, and blank comments there do not mean agreement.

## Inventory and readiness

The old 3,798-construction inventory combines independent element and package
forms. Inspection of frozen v0.1.1 gives:

| Population | Count | Current disposition |
| --- | ---: | --- |
| Elements with above-ground/interior roles | 2,982 | All source-resolved in the existing recovery classifier; final consumer readiness unverified |
| Explicit ground-contact elements | 592 | Deferred, including the 59 misclassified/targetless cases |
| Commercial mixed construction packages | 183 | Need above-ground/infiltration-only projections and complete source selector closure |
| Residential whole-enclosure variants | 41 | Need above-ground projections, assembly translation and resolved constant-ACH policy |

The 2,982 elements comprise 767 exterior walls, 590 roofs, 590 exterior floors,
504 windows, 174 interior walls, 184 interior floors and 173 interior ceilings.
Their resolved status is not a 100% ready-export certificate.

The preliminary projection population is 3,206 existing identities: 2,982 elements,
183 packages and 41 residential enclosures. This is not the final release
denominator. The current package exporter
omits above-ground selectors that exist in source sets: exterior/overhead doors
(161 package occurrences each), glass doors (143), skylights (109), operable
windows (161), and interior doors/fixed/operable windows (161 each). Expand the
dependency closure and corresponding element inventory from those source
selectors before freezing eligibility. Preserve separate source variants and
record any additional IDs explicitly; do not claim completeness by restricting
the denominator to the old extracted subset.

There are 906 commercial package infiltration entries, all unknown in the frozen
table (768 unique source-program IDs repeated across packages). The other 3,624
package air-entry occurrences are mechanical outdoor/total-air requirements and
are deferred. Null leakage values still need source recovery or source-proven
applicability/absence; no general zero is authorized.

## Constant-ACH reference discussion

The pinned residential `airflow.rb` already supplies an annual-average natural
ACH helper, `get_infiltration_ACH_from_SLA`, and a pressure-test-to-specific-leakage
conversion. Its inputs include leakage, infiltration height and a weather and
shielding factor. The weather helper supplies that factor through its source
lookup or calculation, which itself uses specified reference conditions. This
is a candidate source-backed scalar method, not an executed recovery in this pass
or proof of parity with dynamic AIM-2 infiltration. It must not be applied to
commercial leakage without a separately supported commercial conversion.

The fixed catalogue and source archetype geometry choices are settled. Before
choosing final scalar values, recover the source reference enclosure and specify
the climate-zone factor/reference forcing and reproducible derivation. Retain the source method's reference
conditions explicitly; do not invent an ACH50 divisor or assign a unique weather
factor from climate-zone membership alone. Normalized outputs should not carry
EPW-location applicability axes.

### Accepted source archetype reference geometry

Use the pinned source archetype's reference geometry to derive the catalogue
constant, then reuse that value without recalculating it for consumer geometry.
Record the reference geometry identity and operands in derivation evidence.
Reference geometry is part of the value's derivation, not a required consumer
geometry input or a program-JSON dependency. Assemblies remain reusable.

The earlier alternative of one common 185 m² square, 2.5 m-high, 462.5 m³
enclosure is superseded by the user's source-archetype choice. The residential
weather helper's own fixed reference conditions still belong to that helper's
provenance; they do not replace each archetype's leakage geometry.

Read-only audit of `data/program-inputs/residential-v1.json#/records` finds
source CFA defaults for all 41 fixtures (322–5,587 ft²), plus ceiling height
(8.0 ft in all 41), above-grade floor count (1, 2, 3, 4 or 15) and aspect ratio
in all 41 expanded argument sets. These are starting operands, not a recovered
infiltration geometry certificate. Source height/volume methods, unit position
and exposure still need evaluation; total building floor count must not simply
be used as an apartment's leakage height.

Source geometry/exposure recovery now executes all 41 residential fixtures and
129 commercial reference cases in `data/construction-inputs/geometry-v1.json`.
All required residential pressure-boundary height/volume/exterior-fraction
operands are recovered. The audit above describes the earlier starting data.
The 16 attached fixtures have exterior fractions 0.1818–0.89567; the 15-storey
apartment fixture has one conditioned dwelling storey and an 8 ft leakage height.

All ten `Any` and five `Office` packages now have source reference matches.
`Any` scopes are attic/plenum sets; each Office package retains six compatibility
forms, distinct from actual building defaults. The receipt resolves 182/183
package reference matches. SmallHotel 2019's generic GuestRoom source set is not
instantiated in its model and is explicitly recorded with an unassigned whole-
building candidate. No form is averaged, merged or arbitrarily chosen.

Recover each source's leakage basis before using the reference geometry:
commercial floor-area and exterior-area rates require different conversions;
residential unit-total tests must retain their distinction from exterior-only
leakage. Attached-unit exterior fractions must not silently become one. These
conversion details and one reproducible factor per ASHRAE climate zone remain
open. Source geometry selection does not authorize a universal conversion or
discard foundation-associated leakage from a whole-enclosure pressure test.
Ground/foundation delivery remains deferred. Candidate residential sensitivities
and 42 climate-reference calculations are separate proposal evidence, not
approved/released scalar natural ACH values. See the
[reference and climate proposals](../reviews/construction-ach-reference-proposals.md)
for source findings, measured factor differences and explicit answer areas.

**Your comments on reference geometry:**

<!-- comments:constant-ach-reference:begin -->
Source archetype reference geometry
<!-- comments:constant-ach-reference:end -->

Source evidence: ResStock revision `dd25369f41a83a0767aefeeac0b6f8a0b0edd649`,
`resources/hpxml-measures/HPXMLtoOpenStudio/resources/airflow.rb`,
methods `get_values_from_air_infiltration_measurements`,
`get_infiltration_ACH_from_SLA`, `get_infiltration_SLA_from_ACH50`;
SHA-256 `0af553977ea48a169f1ed4f19baecb92508c08367a466d6f2f95a840d0b3996b`.
Supporting `weather.rb#calc_ashrae_622_wsf` SHA-256
`cf3c739456963363024554104e6197c0d3009cb8f404b60ef7c18ef0c585ca74`.
The existing construction recovery records both files and their pinned hashes.

## Completion gate

Recover residential above-ground assemblies and all missing above-ground source
selector dependencies; apply commercial source layers/defaults and material-model
requirements. Resolve infiltration and constant-ACH reference policy. Implement
the independent versioned above-ground construction schema/exporter, pilot it on
Medium Office, then residential, then all eligible variants. Produce a complete
eligible-ID/readiness receipt with zero active source-physics failures and
deterministic output hashes. Publish and verify this milestone independently of
the deferred ground/system kinds, through protected-main release checks. Keep
development checks focused and defer lengthy site/CI work until publication.
