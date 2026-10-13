# ADR 0019: All-variant readiness and HVAC delivery scope

Date: 2026-10-12. Status: accepted user decisions; implementation remains open.

## Decisions

The user answered the release-readiness question: "Every variant must be
simulation-ready." Ready Medium Office and residential pilots are intermediate
gates, not sufficient to close roadmap step 2. Every construction and HVAC
variant in the agreed catalogue must have a ready consumer export before this
step's completed release can be published and live verified.

The baseline inventory is 3,798 constructions and 1,046 HVAC systems from frozen
definition release v0.1.1. Preserve their identities and variants; do not shrink
the eligible inventory, merge stock/code contexts, drop difficult variants or
relabel missing source physics as consumer inputs to reach complete coverage.
Record any future inventory revision explicitly. No general fallback layers,
efficiencies, topology or controls are authorized by the readiness requirement.

The user also answered: "no need of detailed dhw." Step 2's ready system
delivery is HVAC. Detailed water-heater, tank-loss, auxiliary and solar models
are not required consumer exports. Retain the recovered 195 heater records and
one solar record as separate source evidence, with their current provenance and
limitations; their detailed translation blockers do not hold up this release.
This refines the earlier HVAC-plus-DHW equipment scope rather than deleting data.

Simplified water-heating fuel energy remains in the separate Program JSON 4
contract under ADR 0018: draw heating only, standby/auxiliaries/pilot excluded,
solar fixture skipped, approved SmallHotel source outlet cap and unmet reporting.
The solar skip is specific to simplified DHW; it does not exempt that fixture's
construction or HVAC variant from all-variant readiness. Program v3 publication
already completes roadmap step 1; full v4 publication is a separate follow-up.

## Meaning of readiness

All required source physics, dependency references and applicable schedule
semantics must be resolved and validated. Geometry, weather/calendar, sizing and
serving assignment remain explicit simulation inputs. A capacity-dependent
source rule may retain its sizing operand when the rule and its applicable
performance/curves are complete; a missing source efficiency or curve cannot be
delegated as an ordinary sizing binding. Ready JSON alone does not certify an
energy simulation or implement cross-contract mixing and matching.

Blocked/raw evidence remains useful during development, but cannot substitute
for a ready export in the completion receipt. Receipts must enumerate the full
eligible inventory, successful exports, failures, source/schema/policy/code
identities and reproducible output hashes. Step 2 stays open if any eligible
construction or HVAC export remains blocked.

## Implementation consequences

1. Resolve the 41 residential enclosure assembly translations and 59 remaining
   ground-construction models; retain geometry-dependent operands explicitly.
2. Recover exact commercial and residential HVAC recipes, performance rules,
   curves, fans, controls and distribution semantics. Validate Medium Office
   first, then residential, then every remaining variant.
3. Build independent construction and HVAC consumer schemas/exporters and
   all-variant completeness receipts. Preserve raw evidence and frozen releases.
4. Publish separate JSONs/pages only after the completed catalogue meets the
   all-ready gate and required release checks. Continue focused development
   validation; defer full site builds and lengthy CI to the publication phase.

No additional numerical assumption is accepted here. Escalate genuinely missing
source physics with concrete source-specific proposals after recovery attempts.
