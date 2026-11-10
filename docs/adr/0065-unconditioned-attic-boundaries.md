# ADR 0065: Unconditioned attics in the unified constructions (unified 4.1.0)

Status: proposed (2026-11-09; branch `codex/commercial-attic-roof-semantics`, merged in PR #54); published by release
2.6.0 at the repository owner's request ([ADR 0066](0066-release-2-6-0.md)), which carries section 3's correction in the
stored records and exports 4.1.0 for every unified context. Sections 1 to 3 describe the export over release 2.5.0. Raised by
BEMGen's gap G2: its DOE SmallOffice models omit the source attic and map `ExteriorRoof` to the zones' outdoor-facing
ceilings, so the top of the occupied zones gets the attic roof deck (U 2.61 W/m2K) instead of the insulated attic floor
(U 0.10 to 0.55 W/m2K). This ADR does not change release 2.5.0: its records and its 4.0.0 exports keep their bytes.

## 1. Context: what the source does

**90.1 and DOE Ref sets (openstudio-standards rules, pinned `c8c1b9eb`).** `Standards.Model.rb`,
`model_add_construction_set`, gives the `Attic` standards space type its own construction set: "insulation is actually
on the floor and the roof itself is uninsulated". The attic roof is `Typical Uninsulated Wood Joist Attic Roof`, the
soffit `Typical Attic Soffit`, and the attic's interior floor the set's `ExteriorRoof` construction (for SmallOffice the
`Attic and Other` roof, `Typical Wood Joist Attic Floor`, insulated to the roof requirement with the AtticFloor films
0.61 + 0.46 h ft2 F/Btu). `Prototype.Model.rb`, `model_add_constructions`, puts that set on the space type
(OpenStudio search distance 2) and the building set on the building (distance 4); it hard-assigns ceilings only below
plenums. The attic is served by no HVAC system (`data/program-inputs/conditioning-sides-v1.json`, ADR 0063).

**The zone ceilings of the attic-floor pairs.** OpenStudio 3.10.0 (`sources/construction-interzone-lock.json`) resolves a
matched surface pair whose two spaces inherit different default constructions to the one with the lower search
distance and gives the other surface its reverse (`ForwardTranslator::resolveMatchedSurfaceConstructionConflicts`;
`Surface_Impl::construction`; the distances in `Space_Impl::getDefaultConstructionWithSearchDistance`). The occupied
zones' ceilings under the attic therefore take the attic floor reversed, not the building default
`Typical Interior Ceiling` (carpet pad and 100 mm concrete). The published models agree: the PNNL
`ASHRAE901_OfficeSmall_STD2019/STD2007` IDFs give `Core_ZN_ceiling` `nonres_roof` (insulation, gypsum) and the attic
floor its reverse `nonres_roof_floor`; the DOE reference SmallOffice IDFs give both faces `Attic Non-res Floor`
(`sources/reference-models-lock.json`).

**What the atlas made of it.** The weighting profiles (construction-weighting 1.1.0) classify a surface by its type and
boundary condition and assign it by its own space's precedence: the attic floor is `InteriorFloor` (correct: a Floor
with a Surface boundary; it is also the floor inventory behind `FloorDistributedMass`, as the mass contract counts
attic quantities), the attic roof `ExteriorRoof`, the soffit `ExteriorFloor`, and the zone ceilings `InteriorCeiling`
with the building-default interior ceiling (wrong: the source gives them the attic floor reversed). The unified
paired-surface policy (`adjacent_ceiling: reverse the same canonical floor assembly`) is right for a consumer that keeps
the pair, but nothing in a unified 4.0.0 document says that `ExteriorRoof` sits over an unconditioned attic or that the
`InteriorFloor` contributor is the occupied zones' thermal boundary.

## 2. Decision: unified constructions 4.1.0 (additive minor)

`schemas/construction-equivalent-v4.1.schema.json` (`scripts.atlas_contracts.construction_schema_attics`, derived from
4.0.0) adds three optional fields; every 4.0.0 field keeps its meaning and a 4.0.0 document with its version raised
validates. `scripts.attic_boundary` forms them from a release's stored detailed and unified records; nothing is
recovered again and no geometry is guessed.

1. **`attics`**, one per source attic: `kind: unconditioned_attic`, the source family and space, the `exterior_parts`
   (role, contributors, reference areas, each contributor's own common-film U, share of the role's reference area),
   the `conditioned_boundary` (the role and contributor between the attic and the occupied zones, with the zone-side
   orientation: `reverse_layers` for an attic floor, `as_listed` for a ResStock ceiling), `other_interior_parts`
   (a garage ceiling), `area_ratio_roof_to_boundary`, for openstudio-standards sets `source_default_exterior_roof`
   (the building-default ExteriorRoof rule: what the source gives a roof directly over an occupied space; zero reference
   area where every roof is over the attic), the evidence, and `attic_omitted_roof`.
2. **`components.<role>.attics`**: which part of a role's reference area belongs to which attic.
3. **`export_corrections`**: a stored value the export corrects (section 3).

Recognition, per family: openstudio-standards sets by the assignments scoped to the `Attic` space type; IECC (PNNL IDF)
sets by the attic roof deck name and the attic surfaces of the floor and soffit assignments; ResStock dwellings by the
`attic - vented` / `attic - unvented` spaces of the assignments. An assembly an attic rule and a non-attic rule of the
same role both select is an error.

### 2.1 The attic-omitted roof (`attic_series_stack_1.0.0`)

*Agent decision, tested against the source rather than taken from the request.* Per m2 of conditioned boundary,
outside to inside: the roof deck's source layers with R/n and C·n (n = A_roof/A_boundary from the source reference
areas), one massless layer R = (R_ai + R_se)/n + R_ai − R_se for the two attic air films and the exterior-film area
correction, and the boundary's source layers in zone-side orientation. With the package's own films (R_se 0.04,
R_ai = R_si 0.13 m2 K/W) its common-film U is the ASHRAE ceiling–roof combination 1/U = 1/U_c + 1/(n U_r) of a sealed
attic whose only exterior part is the deck; its capacity is C_deck·n + C_boundary. It is fitted to the package's
three-slot form by the existing policy (`two_mass_one_resistance_1.0.1`) and carries its own fit metrics; the unscaled
stack is stated beside it. The deck's solar-absorbing face is outermost.

Bounds stated with it (`u_bounds_W_m2_K`): the sealed attic with all its exterior parts in parallel (roof, soffit, gable
walls), and the boundary alone (the attic air at outdoor temperature, the full-ventilation limit). Ventilation and the
other exterior parts move U from the equivalent towards those. Not represented: attic air capacity, attic ventilation
and infiltration (90.1 SmallOfficeDetailed adds 0.2001 m3/s; that is an airflow input, not a construction), radiant
exchange beyond the combined films, pitch and the deck's solar aperture, and a garage's exchange with the attic.
The equivalent instantiates the boundary's capacity, so a consumer deducts that contributor from
`FloorDistributedMass` once (mass contract: count a represented slab once).

90.1-2019 SmallOfficeDetailed 4A: U_c 0.11823, U_r 2.61438, n 1.17139: equivalent U 0.11384, C 31,414 J/m2K; all
exterior parts 0.11429; boundary only 0.11823; the source's default roof rule (the attic floor as a roof, exterior films) 0.11951.

Rejected: choosing between the deck, the attic floor or the default roof rule to reach a target heating result; folding
the attic into the existing `ExteriorRoof` component (it would change a 4.0.0 field's meaning).

## 3. Correction of the code-prototype InteriorCeiling derivation

For openstudio-standards sets the 4.1.0 export removes the attic-paired ceiling area (the attic `InteriorFloor`
contributor's pair area) from the `InteriorCeiling` derivation, where one non-space-type rule is the only contributor;
the recipe and its assembly are unchanged, and the stored and the corrected derivation are both in
`export_corrections` with the OpenStudio evidence. Several contributors, or a space-type ceiling rule, are reported as
`unresolved`. In release 2.5.0 all 568 attic contexts of the family are `corrected`; in SmallOffice the InteriorCeiling
reference area becomes 0 (`unique_source_recipe_without_reference_exposure`). The IECC and ResStock sets already give
the zone ceilings the insulated construction and are not corrected.

Plenum ceilings (offices, laboratories, tall buildings) are not changed here: the plenum roof is the building's
insulated roof, so the roof is the thermal boundary; whether the stored InteriorCeiling of those sets should follow the
plenum-floor hard assignment of `model_add_constructions` is left to the owner (open question).

## 4. Consequences and release path

- Release 2.5.0 is untouched; `python -m scripts.atlas_exports --construction SET --context KEY --representation
  unified --attics` and `python -m scripts.attic_boundary --export DIR` write 4.1.0 from its records, naming
  `atlas-release-2.5.0` (the data), with the correction stated. Publishing the correction in the stored records and
  4.1.0 as a release contract needs a delta release (2.6.0) under ADR 0036 / 0046: an edits module over 2.5.0, the
  writer block, release notes, the BEMGen handoff and the release tests. That is the owner's decision. *Taken:* release
  2.6.0, [ADR 0066](0066-release-2-6-0.md).
- BEMGen: dispatch on `MINOR` 1; where `attics` is present and the attic is not instantiated, use
  `attic_omitted_roof.assembly_id` for the occupied zones' top surfaces in place of `ExteriorRoof`, deduct the boundary
  from `FloorDistributedMass`, and keep `ExteriorRoof` for roofs over occupied space only where the document has no
  attic; where the attic is instantiated, keep the 4.0.0 roles and reverse the `InteriorFloor` attic floor on the
  zone ceilings.
- Inventory: `python -m scripts.attic_boundary --inventory DIR` lists every unified context with an attic (926 in
  release 2.5.0: 568 openstudio-standards, 342 IECC, 16 ResStock).
