# Retail/Office P0 preflight: parent reference union, programme area, authority transition

Status: P0 design report for `retail-office-followup-subplan.md` (handover
copy). Design only; no production code changed. Cut: HEAD `5bcd098`
(v0.8.0 shipped), apartment authority lock
`sources/schedule-generator-apartment-authority-lock.json` SHA-256
`083390097f463e22c9c184f1f111594b49b3b3c3c285a27dd21a179928495b26`, all 67
current dependencies and its producer byte-identical to the tree (checked
2026-10-16). Inputs are the frozen definitions
`data/definition-releases/v0.1.1/{programs,compositions,services}.json`.

## Verified source facts

- RetailStripmall: 40 programmes, 10 parents (one per template and view), each
  composed of Type1, Type2, Type3 members at 522.5796, 522.5796 and 1045.1592
  m2 (weights 0.25, 0.25, 0.5).
- Six code-template parents (2007, 2013, 2019 by source/reviewed) each list
  seven `service_ids`. In every one, the parent's SID set equals the union of
  its three members' SID sets (2 + 2 + 3), and the member sets are disjoint.
  Every SID is an absolute `hot_water_volume` service whose only beneficiary
  is the member's `source_id`. No parent or member has a water load. The
  parent's frozen SID order differs from member order, so both orders must be
  kept.
- Four DOE parents and their members have no service references.
- LargeOffice: 36 programmes; 10 (one per template and view) reference one
  absolute service each, 5 SIDs in all, `instantiate_once`,
  `consumer_host_when_applicable`; no water loads. Each SID has three physical
  roles (Core_bottom, Core_mid, Core_top) per the subplan.

## Decision A: parent service-reference union

Add a separately discriminated requirement kind,
`original_source_reference_union`, rather than widening
`original_source_components` (which requires an original mixed water demand).

Compiler (`scripts/schedule_generator_physical_sets.py`). For a programme
with a `composition_id`, non-empty `service_ids` and no water load:
1. Resolve the exact composition and its members in member order.
2. For each SID in the parent's frozen order, require exactly one member whose
   own `service_ids` contain it, and one compiled `original_service_reference`
   leaf for that member and SID; otherwise `requires_binding`.
3. Require the union of member SIDs to equal the parent's SID set, with no
   SID in two members and no member SID outside the parent.
4. Emit one requirement with: `parent_programme`, `original_service_relation`
   (nested source of `/service_ids`, frozen order), `composition`, and
   `members` = per member {`member_program_id`, `member_source_id`,
   `member_evidence_view`, `represented_area_m2`, `original_weight`,
   `child_requirement_ids` in that member's SID order}, plus a derived
   `closure_order` (member order, then each member's SID order). No demand,
   load, beneficiary or water component is created.

Exact validation (`atlas_schedules/physical_sets.py` `validate_requirements`):
re-derive steps 1–3 from the retained originals; require child requirements
to be `original_service_reference` leaves with matching programme, view,
template and roles; reject role overlap between members; reject any parent
water load.

Runtime: the parent is generated as today's source parent for energy (members
at represented areas, summed, divided once). Water: the parent emits a
non-owning reference-union projection listing the actual role owners for its
seven roles in `closure_order` — references and recomputed sums only, with no
own slot, demand, schedule, binding index or effective magnitude. Explicit
role owners are required exactly as for leaf references. `service_graph`
reconstructs and checks the same projection. DOE parents keep an explicitly
empty service path.

Wire: the projection kind is a new value under explicit params schema 1.2
only; 1.0 and 1.1 semantics and older releases are untouched (needs an ADR
0029 addendum).

Tests (red first): `test_parent_service_relation_union_has_no_original_water_load`;
union equals child union; missing member SID, extra parent SID, SID in two
members, swapped member view, parent with an invented water load, reordered
parent relation kept as provenance but not used for closure; DOE parent empty.

## Decision B: programme area is not fixture extent

Today `physical_sets.py` (around lines 806–809) sets the comparison extent to
1 for `original_service_reference` and rejects a caller programme
`floor_area` other than 1 m2. For direct beneficiaries this conflates the
programme's energy area with the absolute fixture's whole extent.

Proposal: for `original_service_reference` and the new union kind, fixture
`consumed_extent` stays 1 (unit 1, multiplicity 1) and is never compared with
or scaled by the programme area. The programme's energy `floor_area` follows
the same rules as any normalized programme in C2–C6: an explicit caller extent
with its evidence, or the source represented area for composition members.
Arbitrary caller HOO stays `requires_binding`. `original_programme_demand`
(area-basis water) keeps its existing extent equality check unchanged.

Decision required from review: whether explicit caller energy areas are
accepted for water-referencing programmes (proposed: yes, matching other
normalized programmes, because absolute fixtures are whole per building), or
only source areas. The alternative is stricter and limits Office use.

Consumers: exact preparation (`physical_sets.py`), graph reconstruction
(`service_graph.py`), source-parent staging (`source_compositions.py`),
binder and composer denominators, examples. Tests: unequal source member areas
with whole fixtures; fixture rate unchanged when programme area changes;
caller area 1 m2 not inferred; foreign area rejected; overlapping owners
rejected.

## Decision C: authority transition

The lock pins 67 runtime and build files, including the planned edit targets
`physical_sets.py`, `source_compositions.py`, `service_graph.py`,
`commercial/*`, `generator.py` and `schedule_generator_build.py`. Any edit
breaks `verify_current_code` and therefore the apartment authority build.

Per change set, as R70 did (`scripts/schedule_generator_runtime_cut.py`):
1. Snapshot the current lock and code-cut into
   `data/schedule-generator/apartment/evidence/<label>-current-then/`.
2. Write the new lock with the explicit changed-file set, unchanged pins and
   an interpretation of the delta; no blind refresh.
3. Add a narrow transition checker and test asserting the snapshot, that only
   the declared files changed, and that everything else is unchanged.
4. Covering proof on the new code: `verify_current_authority`, apartment
   certification and case-matrix suites on both runtimes, and affected
   commercial suites. The shipped v0.8.0 release verifies its own packaged
   code and is unaffected; it is not rebuilt.

Group the Stripmall runtime edits into one transition where possible, and
LargeOffice into another.

## Native work still missing (from the subplan)

The pinned OpenStudio `3.10.0+86d7e215a1` runtime in the existing pilots runs
on this machine. Existing pilots
(`native-stripmall-pilot-20261014-01`, `native-large-office-pilot-20261014-01`)
are reused unchanged. Missing: full selected-slot contexts for all ten
template/views per family (Strip 2013 source has People and water only),
first-registration order in the complete object set, DOE source-path absence,
and two-seed public observations. These are captured in S3 and L2 only.

## Addendum after independent review (APPROVE WITH NOTES)

Review confirmed every source fact above. These points complete A–C before
S2 or L1 code; P1 may start now.

**A, every branch keyed on the existing composition kind.** The union kind
must be handled explicitly at `atlas_schedules/physical_sets.py:181` (parent
programme accessor), `:247` and `:269` (validation branches), `:643` (force
`source_reference_area_normalized`; reject `caller_parent_floor_area` for a
union parent, with a negative test), `:687` (role expansion: the union's
roles are its children's `expected_role_ids` in `closure_order`), `:797`
(route to exact parent preparation), `:806` (never read `expected_role_ids`
from the union), `:818–828` (Phase 5 area-to-extent check skipped for the
union, because its children are absolute), `source_compositions.py:335–390`
(`_prepare_exact_parent`) and `service_graph.py:172–192, 378–392`.

- `service_graph._original_obligations` today expects one
  `original_service_reference` per parent SID (seven leaves) and rejects any
  other kind. It gains a recomputable predicate: composition parent, no water
  load, non-empty `service_ids`, all SIDs absolute and owned by members gives
  exactly one `('original_source_reference_union', sids)` obligation. Test:
  seven parent-alias leaves are rejected.
- Each union member record also carries `component_index` and
  `original_method_reference`, so `_prepare_exact_parent` and the graph bind
  each child to its original method and view, keeping the
  `permitted_child_variants` and `resolve_child_variant` guards.
- Wire: bundle schema 1.2 gains `projection_kind`
  `source_reference_union` with `target_kind` `physical_role_set` and the
  same `{1, '1'}` denominator as the leaf reference projection. It is an
  additive enum value inside 1.2.0, so a pre-v0.9 reader rejects the bundle
  rather than misreading it; old releases keep their own packaged schemas.
  Edit both `atlas_schedules/schemas/` (pinned) and the root `schemas/` mirror.
- Gate the compile predicate by inventory family (`RetailStripmall` only in
  this milestone) and require absolute child SIDs. LargeHotel, SmallHotel and
  Outpatient parents that match the predicate stay `requires_binding` until
  their own plans; negative test with an area-basis child SID.
- Validation re-derives and compares `closure_order`.

**B, scope and policy.** The conflict is `physical_sets.py:806–809` and only
affects directly requested leaf programmes (all LargeOffice programmes and
standalone Stripmall members); union children already use source areas
(`source_compositions.py:323`), so `source_compositions.py` is not a B
consumer. Policy (option 1, reviewer-recommended, approved by the user on
2026-10-17, ruling 149):

| Requirement kind | Programme energy area | Fixture extent |
| --- | --- | --- |
| `original_programme_demand` (area water) | must equal summed role extents (unchanged) | role consumed extents |
| `original_service_reference` (absolute) | explicit caller area, positive, finite, with evidence; missing or inferred area rejected | 1, never scaled |
| `original_source_reference_union` | source member areas only | 1 per child role |

The water-to-area ratio is not recorded as a density. Required assertions for
`test_absolute_fixture_extent_does_not_own_programme_area`: a caller area of
800 m2 is accepted, the fixture's effective rate equals its original rate,
and the area does not appear in any water binding. Current rejection path for
the six parents is `source_integrity` at `/source_requirements`
(`physical_sets.py:252–254`), not `requires_binding`; P1 tests expect that.

**C, transition consequences.** `verify_r70_transition`
(`scripts/schedule_generator_runtime_cut.py:140–171`) compares the live lock
with the R64 preimage, so the next transition turns
`tests/test_schedule_generator_runtime_cut.py` red. Each transition therefore:
snapshots the current lock and cut under
`data/schedule-generator/apartment/evidence/<label>-current-then/`; retains
`qualification-code/<label>-current-then/<changed file>` copies; carries the
retention table and historical edge relocations forward as R70 did; and
rebases the R70 checker on its stored R70 lock rather than the live one (the
checker is pinned, so it is part of the delta). The compiler
`scripts/schedule_generator_physical_sets.py` is not pinned, so covering proof
asserts that apartment and C6 compiled requirements are byte-identical before
and after. Pinned files keep LF endings. The case-matrix `_CODE_PROVENANCE`
constants and fixture manifest are historical identities of the frozen
mapping and are not refreshed; the case-matrix suites re-run because they
import `source_compositions` and `seeds`. Expect each transition to take 2–3
hours of the S2 and L1 budgets.

## Proposed order and ETA

P1 sources (3–4 h) → S1 HOO (3–4 h) → S2 recipes and union (4–6 h) → S3
native (3–5 h) → S4 qualification (2–3 h) → S5 ship → L1–L4 (8–12 h).
