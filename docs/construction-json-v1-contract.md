# Above-ground construction JSON 1

This contract supplies independent above-ground construction semantics: ordered
engine materials and assemblies, source package selectors, residential enclosure
assignments and the accepted fixed catalogue natural ACH. Program loads and all
system equipment are separate. Foundation/ground/basement and their interface
assemblies remain deferred under ADR 0020.

The catalogue preserves the eligible frozen construction IDs and adds missing
source selector dependencies and residential assembly children. A completeness
receipt reconciles the entire eligible source census against ready exports. It
does not restrict eligibility to the old extracted subset. Source-default,
source-calculated and previously accepted experimental assumptions remain
distinguishable from each other.

## Objects and selection

`assemblies` contains opaque layered, simple-glazing and detailed-glazing
alternatives. Ordered layers reference `materials`; each executable material
property references an entry in `evidence`. Target U/SHGC and actual engine
properties are separate. Detailed glazing does not require optional whole-window
rating summaries. Engine-autocalculated visible transmittance is an explicit
instruction where the pinned source omits it; it is not an invented scalar.
Massless and air-gap models require resistance and do not acquire fabricated mass.

`packages` contains every source commercial construction set. Its selectors
retain source climate/category/type and any real geometric predicates. Absent
source slots have an explicit disposition. Selection fails for unsupported or
physically ambiguous contexts; it never chooses the nearest climate or averages
different reference variants. Physically equivalent source candidates can be
returned together while keeping all their identities.

`enclosures` contains every residential source fixture, including the fixture
whose solar DHW case was skipped elsewhere. It references every supported
above-ground assembly and source geometry/adjacency rules. Reference areas are
evidence; consumer geometry supplies actual surface areas and internal-mass
scaling. Source framing, pitch and parallel-path operands remain explicit where
they affect construction physics. Foundation-dependent floors/rim joists/slabs
are accounted for as deferred entries, not zero heat transfer.

Package and enclosure infiltration references the fixed-ACH derivation approved
in ADR 0020. Full 2013 climate forcing labels remain separate from shared thermal
assemblies. Source geometry determines the constant; the consumer reuses that
constant across its geometry/zoning variants. Legacy program-scoped infiltration
bases replaced by the source NIST envelope helper are recorded as superseded,
not copied as additional loads. Mechanical air requirements remain deferred.

## Readiness and consumer inputs

An export is ready only when all active source physics and dependencies are
complete. Genuine assignment inputs include climate, surface role/adjacency,
geometry/scaling and a source reference variant when several are available.
Unknown source materials, unresolved layer recipes and missing selectors cannot
be relabelled as consumer bindings. The supported source applicability remains
explicit; readiness does not promise every possible geometry or role.

## Validation and delivery

The exporter validates the Medium Office pilot first, a residential pilot next,
then the complete source census. Focused checks cover schema, model-specific
physics, selectors and dependencies, source provenance, fixed ACH, preserved
source identities and deterministic bytes. A receipt lists eligible/exported/
deferred identities and requires zero missing exports or active blockers.

Canonical release artifacts and independent examples are committed on the
feature branch. Website publication and protected-main release checks are
separate work; this task does not run program generation, site building or CI.

## Frozen coverage and source behavior

The `data/construction-releases/v1.0.0/` catalogue contains 5,092 ready identities:
4,868 assemblies, 183 commercial packages and 41 residential enclosures. It
preserves all 3,206 eligible baseline identities, adds 1,456 commercial selector
dependencies and 430 residential assembly children, and retains all stock/code
variants. There are 858 material resources and 7,972 evidence resources. The
receipt verifies 4,751 package/climate/reference combinations. The 592 frozen
ground identities, three ground slots per commercial package and 210 residential
foundation/ground elements are explicitly deferred. All 41 residential fixtures
are included; the solar-DHW exclusion does not remove construction coverage.

The pinned native construction methods determine actual engine materials and
layer order, including insulation removal and rejected setter behavior. Source
nulls and SDK defaults remain distinguishable in per-property evidence; they
are not new Atlas defaults. Target performance and attained properties remain
separate. The source detailed-glazing U helper refuses scalar target adjustment,
and its SHGC setter conditional can leave a target unapplied. The export retains
those outcomes and never claims that every target was attained.

Commercial selection follows the pinned prototype caller's first source match,
with exact climate group and documented parent-group fallback. The source
percentage helper returns null bounds for the caller across all five templates;
retained WWR/orientation operands are evidence, not an invented consumer WWR
algorithm. Consumers may select a retained alternative by element ID using
`resolve_source_selector`. Fifty-six older DOE packages lack thermal property
rows for 0A/0B: these contexts are explicitly unsupported. ACH benchmarks for
climate 0 do not make those thermal contexts applicable. No nearest-climate
substitution is made.

Residential effective recipes preserve parallel-path operands and source films.
Roof recipes require the recorded compatible pitch; a different pitch requires
re-evaluating the source calculation. Internal-mass areas scale from the
consumer's CFA with the source both-sides and interstory conventions. Source
window curtains have equal summer/winter factors in this fixture population;
apply the exported constant incident-solar multiplier in addition to bare SHGC.
It does not alter glazing U or replace SHGC. Overhang dimensions and source
adjacency/area evidence guide compatible assignment; geometry remains external.
Five adiabatic attached-door assignments were rejected by the SDK's generated
source geometry, but their source recipes were recovered independently. This
limitation is recorded and does not deliver invalid source geometry.

## Reproduction and migration

Run these construction-only commands from the repository root with its Python
environment and pinned source/runtime retrievals available:

```text
python -m scripts.recover_construction_selectors --check
python -m scripts.recover_residential_assemblies --check
python -m scripts.construction_export --check
python -m unittest tests.test_construction_export tests.test_residential_assemblies tests.test_construction_selectors tests.test_construction_ach tests.test_construction_geometry_recovery
```

The native recovery checks execute only construction methods. The exporter
consumes committed recovery/ACH inputs and validates pilots before the full
catalogue. Without `--check`, it writes deterministic UTF-8/LF artifacts and a
manifest with schema, source revisions, input hashes, output hashes and byte
counts. Standalone Medium Office (90.1-2019/4A) and residential examples contain
their material/evidence dependency closure and explicit selection metadata.

This is a new independent consumer contract, not an in-place change to frozen
definition v0.1.1 or Program JSON. Read consumers from the new schema and resource
tables rather than assuming a scalar U/SHGC exists for every assembly. Preserve
the selected reference variant and fixed ACH. Compatible geometry/assignments,
simulation weather and independent program/system inputs remain consumer work.
Ground heat transfer is not supplied by this release.
