# ADR 0045: Unified constructions of the IECC commercial family (release 1.6.0)

Status: accepted for release 1.6.0 (2026-10-27). Stage U of plan
`docs/superpowers/plans/2026-10-27-stages-after-release-1-4-0.md`, with U-1 to U-3 taken
as recommended (user, 2026-10-27). Lifts the deferral of ADR 0040 item 6 and item 10
("the unified representation") and replaces the `deferred` stub of ADR 0040 agent
decision 14. The choices the plan left open are agent decisions, listed in section 4.

## 1. Context

- **The unified form** (construction-equivalent 3.x) gives one building-level assembly
  per component, an area-weighted two-mass, one-resistance fit of the source
  assemblies that keeps U and heat capacity (`scripts.construction_equivalence`), plus
  glazing proxies and mass components.
- **The 90.1 and DOE Ref sets** take their area weights from profiles recovered with
  OpenStudio over the openstudio-standards geometry
  (`data/program-support/construction-weighting-v1.1.0`). Their recipe IDs hash
  full-precision fit errors, so those releases reproduce byte for byte only under the
  pinned CPython 3.14.7 on Windows.
- **The IECC sets** (release 1.3.0) come from the PNNL IDFs, which have no
  openstudio-standards profile. Their contexts carried a `deferred` stub, and the
  export refused it.

## 2. Decisions

1. **Weights from the IDFs (U-1).** `scripts.iecc_unified` reads the 1,824 IECC IDFs
   and stores, for every edition, type and location, the net area of each component
   entry of the envelope payload: base surfaces less their windows and doors,
   subsurfaces as drawn, both times their multipliers
   (`data/program-inputs/iecc-unified-areas-v1.json`, 0.5 MB). Each assignment of the
   detailed document takes the area of its entry.
2. **The existing physics.** Each component's recipe comes from
   `construction_equivalent_export._recipe`: the same opaque fit, glazing proxy and
   surface-property weighting as the 90.1 sets. Nothing in the equivalence modules
   changes.
3. **Ground constructions.** F- and C-factor ground components keep their native
   assembly and ground method, as the 90.1 unified documents do.
4. **Mass.** `InternalMass` is the fit of the source internal-mass recipes, weighted by
   their reference areas; `FloorDistributedMass` the fit of the interior floor
   inventory of the detailed mass accounting. The mass accounting, foundation methods
   and design-flow infiltration are copied unchanged from the detailed document.
5. **Determinism (U-2).** The weights are areas rounded to 1e-9 m², and the composition
   reads only committed inputs, so the release reproduces from them. No new
   interpreter pin is added; the 90.1 pins stay as they are.
6. **Residential (U-3).** The IECC residential and manufactured-housing sets keep their
   source model constructions and get no unified form.
7. **Release 1.6.0**, a delta on 1.0.0 holding everything of 1.5.0, with the stubs
   replaced. Programs keep Program JSON 5.4.0; IECC unified contexts export as
   construction-equivalent 3.1.0, unchanged (it has no release enum).

## 3. Consequences

- All 1,824 IECC contexts export `--representation unified` with status `ready`.
- `python -m scripts.iecc_unified --check` rebuilds the areas where the IDFs are
  present; `tests/test_iecc_unified.py` checks the composition and the export.

## 4. Agent decisions

Each entry: decision; alternatives; reason; evidence.

1. **Adiabatic F-factor floors are left out of the fits.** 570 contexts (single-story
   and some multi-story types) have core-zone floors whose boundary is adiabatic but
   whose construction is an F-factor ground floor. The detailed sets classify them as
   interior floors, faithfully. They have no layers, so the unified form leaves them
   out of the `InteriorFloor` fit and the floor mass inventory, and lists them in
   `provenance.excluded_ground_constructions` with their areas. Where an interior floor
   has only such constructions, the component is `not_applicable`
   (`source_ground_construction_on_interior_surface`). *Alternatives:* block those
   contexts; treat the floors as ground floors (changes the source boundary).
   *Evidence:* e.g. `IECC_OfficeSmall_STD2015_SanDiego.idf`, `Core_ZN_floor`
   (adiabatic, `Core_ZN_floor_Ffactor`).
2. **Weight basis named `source_model_net_component_area`**, beside the 90.1 sets'
   `source_archetype_net_component_area`, because the areas come from the source
   model, not an archetype profile. `weighting_policy` stays
   `precomputed_source_archetype`, which the 3.1.0 schema fixes.
3. **Composition at build time, not a second writer.** The 1.6.0 overlay replaces
   `iecc_commercial_documents.Documents.pair`'s stub for the length of a build; the
   pinned writers stay as they are.

## 5. Open questions

- Whether the 90.1 recipe IDs should move to the same interpreter-independent hashing
  in release 2.0.0 (stage X1), ending the pinned-producer dependency.
