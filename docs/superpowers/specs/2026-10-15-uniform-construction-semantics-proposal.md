# Proposal for one construction assembly per semantic

Date: 2026-10-15. Status: proposal for user review. Baseline: `689e5b6`.

The resolved construction export should provide exactly one assembly for each
applicable semantic: one exposed-wall construction, one roof construction, one
exposed-floor construction, and equivalent single recipes for the other supported
roles. Program and building-type distinctions are resolved before export using
explicit shares. BEMGen then assigns by component semantic, without recovering
the original program-to-face relationships.

The same resolution must cover internal mass, floor-distributed mass and
infiltration. Each quantity uses its own conservation basis. Floor-area shares
can drive the process, but exposed surfaces, stored heat and airflow cannot all
be averaged with the same unqualified weights.

All required share profiles should be obtainable through the program library.
That requires extending its supporting composition data: the current library
does not yet contain complete whole-building program/exposure/mass profiles for
every construction archetype. The feasibility map below identifies the work.

This proposal does not implement a reducer, change frozen JSON, run simulations,
build the site, push, dispatch CI/CD, or implement BEMGen. Ground and systems
remain deferred. Mechanical outdoor-air requirements are inventoried here only
to distinguish them from envelope infiltration.

## 1 Target contract and semantic census

Use a new version of the derived construction contract, provisionally JSON v3.
The existing source-rule contract and immutable construction releases remain
available for evidence and reference comparisons. A resolved export has:

- Exactly one `assembly_id` per applicable assembly semantic, with complete SI
  material layers and provenance. No program-specific `when` clauses, alternative
  assignment arrays, or consumer requests to choose an assembly within a semantic.
- Explicit `not_applicable` and `unknown` states. Unknown applicable inputs block
  readiness; absence does not create a dummy construction or an implicit zero.
- One normalized quantity rule where a recipe needs an amount, such as exposed
  internal-mass area per conditioned floor area. BEMGen supplies actual geometric
  areas and volumes under these rules.
- One infiltration rule, independent of the material assemblies. The accepted
  fixed natural ACH remains the initial reference policy.
- A derivation receipt containing source assembly IDs, the chosen program/share
  profile, all denominators, reference conditions, approximation policies and
  validation errors. Historical candidate recipes remain audit evidence rather
  than active consumer choices.

The semantic census is based on the existing component roles: exterior wall,
roof, exposed floor, exterior window, opaque door, glass door, overhead door,
skylight, interior wall/floor/ceiling/door/window, internal mass, tubular daylight
dome/diffuser, and shading where supported. Rename the source `InteriorPartition`
InternalMass role to the clearer derived semantic `InternalMass`. Add a distinct
`FloorDistributedMass` recipe/quantity for floor mass that must survive removal
of represented interstory surfaces. These two mass quantities share a ledger
with explicit surfaces to prevent duplication.

Fixed and operable windows are source contributors to one `ExteriorWindow`
recipe, rather than new semantics introduced to retain the old multiplicity.
Orientation changes how surfaces are exposed; it does not create a construction
recipe per orientation. Directional exposure weights can remain audit inputs.
Floor and ceiling recipes must satisfy the declared reversal/pairing policy.

Semantic classification still distinguishes different physical boundary roles.
Combining material recipes does not eliminate an attic/garage/plenum temperature
node or establish an interzone adjacency. Those are separate geometry/network
choices that BEMGen must make explicitly.

## 2 Program library as the authoritative source of shares

Publish versioned supporting **building composition and weighting profiles** in
the program library. Program load JSON and construction JSON remain separate;
the shared profile supplies derivation weights, not a mandatory association
between one program and one construction product. A consumer can obtain all
weighting operands through that library without opening raw geometry files.

Each profile should contain:

| Input | Meaning and required basis |
|---|---|
| Building group share | Floor area of a building-type group divided by total counted floor area, when a mixed-building composition is selected |
| Program share within group | Program counted floor area divided by that group's counted floor area |
| Exposed component ratios | Net opaque wall, roof and exposed-floor area per program floor area; separate window, door and skylight area ratios |
| Volume ratio | Reference volume per program floor area, with explicit inclusion of buffer/non-counted spaces |
| Story allocation | Reference program/exposure allocation by source story where source rules depend on story |
| Non-program envelope scopes | Direct envelope allocations for attics, plenums and similar scopes excluded from counted program floor area |
| Internal mass inventory | Source construction, quantity, exposed-side convention and capacity per reference floor area for partitions, furnishings and additional mass |
| Floor inventory | Unique slab/floor contributions and their represented-surface versus distributed-mass treatment |
| Status and provenance | Known, derived, imputed, not applicable or unknown; source IDs, revision, original operands/units, transformations and checksums |

For group share `alpha_b` and conditional program share `p_t_given_b`, the global
floor share is `alpha_b * p_t_given_b`. Do not multiply a whole-building share by
a group share a second time. Preserve mixture denominators: Warehouse's current
storage mixture contains only Bulk and Fine, so its weights exclude Office.

The initial default profile should describe each source archetype separately.
Source stock fixtures, vintages and climate variants are not population samples
to be blended together. A user-selected mixed-building composition needs
explicit group shares; none are inferred from stock prevalence.

For component `c`, use actual net reference exposed areas when available. For a
different selected program mix, exposure ratios provide a controlled derivation:

```text
e[b,t,c] = source exposed area[b,t,c] / source program floor area[b,t]
w[b,t,c] = alpha[b] * p[t|b] * e[b,t,c]
f[b,t,c] = w[b,t,c] / sum(w[*,*,c])
```

These are component-specific weights. For non-counted scopes, the ratio above
is undefined: use a separate direct exposure allocation. A zero denominator
never authorizes division by zero, renormalization that drops unknowns, or an
invented program share. Source default rules apply only to the residual scopes
left after higher-precedence overrides, not to another full share of the building.

Floor-area imputation is a final fallback, equivalent to assuming equal exposure
per unit floor area among the eligible contributors to that component. Record
this assumption and its eligible set. Apply known zero exposure constraints
before normalization. Missing exposure is unknown, not evidence of zero.

## 3 Blending methods and conservation targets

### 3.1 Opaque envelope assemblies

For compatible assemblies under declared common reference boundary conditions,
use exposed-area fractions `f_i` and preserve:

```text
U_target = sum(f_i * U_i)
C_A_target = sum(f_i * sum_j(rho_ij * cp_ij * thickness_ij))
```

U values must share a film convention. If they include reference films, remove
those films from `1/U_target` before allocating resistance to material layers;
EnergyPlus handles boundary heat transfer separately. Preserve actual source
attained properties where available rather than substituting a nominal code
target. Explicitly massless source layers contribute no capacity; missing mass
properties remain unknown.

Fit an exterior mass layer, a middle resistance layer and an interior mass layer.
Constrain their total layer resistance and areal heat capacity to the targets.
Use source mass locations to initialize the interior/exterior split, then fit
the split and resistance allocation against weighted transient heat fluxes.
Normalize thickness/density/specific heat by a declared deterministic policy;
R and C alone do not uniquely determine four material properties. Enforce
positive, solver-compatible values. Allow an unnecessary zero-capacity slot to
collapse rather than inventing mass. Never clip an infeasible negative middle
resistance into a seemingly ready construction.

Match daily amplitude/phase and short/long step responses, because equality of
U and total capacity does not establish dynamic equivalence. Thermal absorptance,
solar absorptance and roughness also need declared treatment and solar-response
checks. Categorical roughness labels cannot be numerically averaged.

### 3.2 Glazing and other surface effects

Derive one glazing recipe per opening semantic using opening area shares. Check
conductance, transmitted solar energy and visible transmission separately.
Fixed/operable contributions are included in that one recipe. Do not substitute
opaque thermal mass layers for a glazing model. Detailed glazing whose attained
properties are not reported requires forward calculation or an explicit proxy
decision before it can contribute to a ready equivalent.

Shading, curtains, overhangs and tubular daylight effects need their own inventory.
A weighted material property cannot generally reproduce a geometric shadow or
an angular optical response. Determine whether one aggregate semantic rule can
meet the validation criteria; expose an unresolved status if it cannot. Do not
claim that the opaque three-layer method resolves these effects automatically.

### 3.3 Internal and floor-distributed mass

Blend the **quantity and construction** of internal mass. A shared material
recipe without an area/capacity quantity is insufficient.

For floor share `p_i`, let `s_i` be exposed mass area per counted floor area and
`gamma_i` be the source-consistent thermal capacity per counted floor area:

```text
s_equivalent = sum(p_i * s_i)                     [m2 exposed / m2 floor]
gamma_equivalent = sum(p_i * gamma_i)             [J / (m2 floor K)]
C_A_equivalent = gamma_equivalent / s_equivalent  [J / (m2 exposed K)]
```

The last equation requires positive known exposure. Source-proven zero mass
uses an explicit not-applicable state; unknown exposure or positive capacity
with zero exposed area blocks this representation instead of forcing a quotient.

Derive `gamma_i` using the source object's actual layer/area convention. Retain
both-side exposure explicitly. EnergyPlus InternalMass uses the area exposed
to the zone, so doubling exposed area while retaining an incompatible full
physical-wall capacity can duplicate stored heat. Fit one equivalent mass
construction to capacity **and heat-exchange response**, not capacity alone.
Unknown furnishings/contents mass is not silently supplied by a generic default.

Maintain a unique physical mass ledger across envelope, explicit interior
surfaces, added internal mass and distributed floor mass. A paired floor/ceiling
is one physical slab inventory item. When rezoning removes an interior surface,
its contribution is transferred once to the appropriate distributed-mass budget.
When the surface remains represented, that contribution is not added again.
Negative residual budgets expose an inconsistency; they are not silently clipped.

The derived contract supplies one recipe and a normalized quantity per mass
semantic. BEMGen reconciles the total with the surfaces it actually instantiates.
This requires semantic surface inventories, not the lost program-to-face mapping.

### 3.4 Infiltration and air exchange

The current construction catalogue already has one accepted fixed natural ACH
per construction/climate/reference context. Source space overrides do not add
another infiltration load. **Initially carry that scalar through unchanged.**
Changing program shares should not silently revoke the accepted source geometry,
2013 climate map and passive-envelope reference decisions.

Where a later explicitly selected profile contains genuinely different compatible
program/group infiltration rates, conserve airflow first:

```text
Q_total = sum(a_i * V_i)                         [m3/s; a_i in 1/s]
a_equivalent = Q_total / sum(V_i)                [1/s]
```

ACH is volume-weighted, not generally floor-area-weighted. Program floor shares
can supply volume weights through known source `volume/floor_area` ratios. A
common height is an additional assumption, not a source fact. Flow-per-floor-area
and flow-per-exterior-area inputs must first be converted using their respective
areas and the same reference operating/weather conditions. Pressure-test ACH50
must not be mixed directly with natural ACH. Preserve the declared volume
denominator, including its treatment of attics/plenums, rather than changing it
to conditioned volume without a decision.

One constant equivalent natural ACH can be distributed across consumer zones by
their compatible volume basis, conserving total flow across rezoning. Different
infiltration schedules/operating terms require flow-trajectory aggregation or an
explicit constant-reference reduction; independently averaging normalized
schedules does not conserve airflow.

Keep mechanical ventilation, exhaust and interzone mixing distinct. Program
per-person/per-area/ACH outdoor-air clauses retain their source combination
rules and schedules. They are not folded into the envelope ACH or counted twice.
HVAC equipment, heat recovery and control implementation remain deferred.

## 4 Feasibility across all current building types

The current distribution has 136 building-scope sets spanning 129 distinct
reference/template contexts, plus 41 residential whole-dwelling sets. Generic
Office sets reference the MediumOffice geometry; SmallHotel has additional source
set variants. These seven additional sets do not create seven new typologies.

The table checks every counted positive-area source space against the exact
`template + reference building type + native standards building/space type`
program key. This is share/mapping feasibility, not a claim that a fitted
equivalent construction has passed simulation validation.

`P` means all counted spaces have exact program mappings and their source floor
shares can be derived. `R` means the reference building has no exact program
context in the selected source program table: establish a proven crosswalk or
recover its source program rows. Aliases must be explicit; similar names do not
prove equal programs. All rows still need publication of a complete weighting
profile and the mass/optical/airflow checks above.

| Reference building type | Reference/template contexts | Exact counted-space program mapping | Additional weighting requirement |
|---|---:|---|---|
| College | 5 | R, 0/5 complete | Recover/map programs; inventory mass quantities |
| Courthouse | 5 | R, 0/5 complete | Recover/map programs; inventory mass quantities |
| FullServiceRestaurant | 5 | P, 5/5 | Non-counted attic scopes in four contexts |
| HighriseApartment | 3 | P, 3/3 | Apartment/corridor exposure; floor and mass quantities |
| Hospital | 5 | P, 5/5 | PatRoom override; whole-building rather than department-only shares |
| Laboratory | 3 | R, 0/3 complete | Missing exact Plenum program as well as program context |
| LargeDataCenterHighITE | 3 | R, 0/3 complete | Program/ITE scope mapping; quantities and air-reference policy |
| LargeDataCenterLowITE | 3 | R, 0/3 complete | Program/ITE scope mapping; quantities and air-reference policy |
| LargeHotel | 5 | P, 5/5 | Nine instantiated GuestRoom override combinations across templates |
| LargeOffice | 5 | P, 5/5 | Non-counted Plenum envelope in all five contexts |
| LargeOfficeDetailed | 5 | R, 0/5 complete | Prove program crosswalk or recover detailed source rows |
| MediumOffice | 5 | P, 5/5 | Non-counted Plenum envelope in all five contexts |
| MediumOfficeDetailed | 5 | R, 0/5 complete | Prove program crosswalk or recover detailed source rows |
| MidriseApartment | 5 | P, 5/5 | Apartment/corridor exposure; floor and mass quantities |
| Outpatient | 5 | P, 5/5 | Department weights do not cover every whole-building contribution |
| PrimarySchool | 5 | P, 5/5 | Recover component exposure and internal mass quantities |
| QuickServiceRestaurant | 5 | P, 5/5 | Non-counted attic scopes in four contexts |
| RetailStandalone | 5 | P, 5/5 | Whole-building shares plus exposed component quantities |
| RetailStripmall | 5 | P, 5/5 | Tenant/group multipliers; distinguish party walls and exposed walls |
| SecondarySchool | 5 | P, 5/5 | Recover component exposure and internal mass quantities |
| SmallDataCenterHighITE | 3 | R, 0/3 complete | Program/ITE scope mapping; quantities and air-reference policy |
| SmallDataCenterLowITE | 3 | R, 0/3 complete | Program/ITE scope mapping; quantities and air-reference policy |
| SmallHotel | 5 | P, 5/5 | 15 story rules; two attic scopes; generic GuestRoom has no native extra share |
| SmallOffice | 5 | P, 5/5 | Non-counted attic scopes in four contexts |
| SmallOfficeDetailed | 5 | R, 0/5 complete | Program mapping and non-counted attic exposure |
| SuperMarket | 5 | P, 5/5 | Complete whole-building composition; source mass quantities |
| SuperTallBuilding | 3 | R, 0/3 complete | Three GuestRoom5/6/7 overrides in the 2019 reference; multipliers/story allocation |
| TallBuilding | 3 | R, 0/3 complete | Three GuestRoom5/6/7 overrides in the 2019 reference; multipliers/story allocation |
| Warehouse | 5 | P, 5/5 | Office/Fine/Bulk exposure differs from floor shares |

Totals: **83/129 contexts across 17 types** have complete exact counted-program
maps. **46/129 contexts across 12 types** require program context mapping/recovery.
The five generic `Office` source sets reuse the MediumOffice reference profile;
keep their construction source identities separate.

Residential fixtures have a whole-dwelling program match, not a published mixture
of room programs. Their base counted program share is one whole dwelling; attic,
garage, party-wall and other adjacency exposure still need separate quantities.

| ResStock fixture building type | Construction fixtures | Matching whole-dwelling programs | Existing mass quantity rules |
|---|---:|---:|---|
| SingleFamilyDetached | 22 | 22 | Partition scaling in all; ordinary interstory scaling in 16 |
| SingleFamilyAttached | 5 | 5 | Partition scaling in all; ordinary interstory scaling in 2 |
| ManufacturedHome | 3 | 3 | Partition scaling in all |
| MultiFamily2To4 | 3 | 3 | Partition scaling in all |
| MultiFamily5PlusLowRise | 6 | 6 | Partition scaling in all |
| MidriseApartment | 1 | 1 | Partition scaling |
| HighriseApartment | 1 | 1 | Partition scaling |

All 41 fixtures have a matching program and partition area/CFA rule. Eighteen have
the explicit ordinary-interstory scaling rule. This does not establish that the
other fixtures have no floor mass. Their source floor/adjacency inventories must
still be reconciled. Preserve every existing-stock fixture separately.

For building-scope sets, 124/136 have an InteriorPartition recipe, but its current
area rule requires actual BEM area. All 136 have interior floor and ceiling
recipes with actual-area rules. None of those recipe counts establishes an
additional furnishings/internal-mass quantity. The source program attributes
checked here have no mass/partition/furnishings quantity field. Recover those
quantities from source models/defaults, or retain an explicit unknown status.

### 4.1 Space rule and share exceptions

The commercial exact-name override audit contains 72 distinct reference/space
combinations, collapsed over climates and components:

| Classification | Count | Treatment |
|---|---:|---|
| Program exists and counted floor area is positive | 33 | Publish source program floor and component exposure weights |
| Program exists but all its source floor area is non-counted | 24 | Publish direct non-program envelope allocation |
| No exact matching program in the reference archetype/template | 14 | Six occupied GuestRoom scopes need mapping; eight attic/plenum scopes need explicit envelope treatment |
| Generic GuestRoom absent from SmallHotel 2019 source geometry | 1 | Preserve applicability without inventing or double-counting a source area share |

The 14 gaps are GuestRoom5/6/7 in TallBuilding and SuperTallBuilding (six), Attic
in SmallOfficeDetailed across five templates, and Plenum in Laboratory across
three templates. Residential additionally has 12 distinct interior/exterior
adjacency pairs. These are physical boundary categories, not missing program
floor-area fractions.

### 4.2 Reference exposure is already partly available

Commercial geometry recovery contains gross outdoor wall, roof and floor areas
for all 5,725 recovered spaces in 129 references. Recover net opaque and opening
areas from the pinned source geometry under the same geometry tweaks and
multiplier rules. Extract exposed perimeter/orientation where useful, but use
actual area for the component weights. Multiply source representative spaces
once; do not repeat multipliers already included in a source quantity.

Warehouse 2019 illustrates the available distinction:

| Source space | Counted floor share | Gross exposed wall share | Gross exposed roof share |
|---|---:|---:|---:|
| Office | 4.90% | 5.99% | 0% |
| Fine | 28.82% | 30.47% | 30.30% |
| Bulk | 66.28% | 63.54% | 69.70% |

Gross wall/roof values still include openings. The Office's known zero outdoor
roof exposure must survive any floor-area fallback. Whole-building shares must
include Office even though the published storage mixture contains only Fine/Bulk.

## 5 Validation and acceptance

Validate the share table before fitting assemblies. For each building, template,
reference and applicable climate, enumerate every semantic and every source
override, apply precedence, and assign each physical contribution exactly once.
Check whole-building and subgroup denominators, excluded/non-counted scopes,
positive areas/volumes, matched program IDs, multipliers, story coverage and
complete input provenance. Equal source names are not a sufficient join key.
Report feasibility per semantic as direct, derivable, assumption required,
not applicable or blocked; do not convert a partial mapping into a whole-set pass.

Conservation checks compare total UA, thermal capacity, exposed mass area and
airflow under their declared reference conditions. Program regrouping and zone
merging must leave these budgets unchanged. Explicit and transferred mass share
one ledger. A remaining geometry requirement is visible, rather than supplied
by a hidden room-height or floor-count default.

Provisional acceptance targets for review:

| Check | Proposed initial criterion |
|---|---|
| Share, reference, source-identity coverage | 100% of applicable contributions; no unknown contributor dropped |
| Algebraic U, capacity and airflow conservation | Relative error <= 1e-6, with declared absolute tolerances for near-zero quantities |
| Daily dynamic conduction | Heat-flux amplitude error <= 5%, phase error <= 1 hour where signal amplitude is meaningful |
| Heating/cooling test-cell energy | Each non-negligible annual heating and cooling demand within 2%; peak loads within 5% |
| Internal mass transient tests | Capacity/exposure conservation plus response fitting against the original source objects |
| Rezoning | Identical normalized envelope, mass and airflow budgets for equivalent physical geometry |

The algebraic tolerance applies to equivalent targets under the chosen reference,
not equality between different weather-dependent surface films. Dynamic thresholds
are proposed engineering acceptance values, not source standards or validated
results. If a three-layer construction fails, improve its reduction policy or
retain a blocked state; do not relax the contract by exporting multiple choices.

Pin the validation EnergyPlus release and solver settings when implementation
starts. Compare source assemblies represented as parallel physical surfaces with
the one equivalent construction under common boundary forcing, then assess solar
and multi-zone effects separately. Keep model sizes small and tests focused.

## 6 Work sequence and deliverables

1. **Complete feasibility and source inventory.** Turn this first-pass map into a
   reproducible per-semantic report. Verify exact aliases before recovery; account
   for all non-counted and story/adjacency restrictions. Inventory source internal
   mass objects, floor mass and all air-exchange bases. Deliver a coverage table
   with the remaining scientific decisions, rather than starting fits on incomplete
   inputs.
2. **Complete program-library weighting profiles.** Publish complete source
   building compositions, exposure/volume/story ratios, non-program allocations
   and mass inventories as supporting tables. Recover/map the 46 missing exact
   commercial contexts. Keep load/schedule JSON unchanged unless missing source
   program definitions actually require additions. No broad schedule regeneration.
3. **Define the derived semantic schema and reduce pilots.** Medium Office first,
   then Warehouse and a residential fixture with attic/garage/interstory mass.
   Export one assembly per semantic plus conserved mass quantities and the
   retained fixed natural ACH. Keep derivation weights in metadata/evidence.
4. **Validate and expand.** Add hotel story/generic tests, school/retail/hospital
   composition tests, and extended typologies after program mapping. Cover every
   one of the 177 construction source sets and all their supported contexts.
5. **Integrate after review.** Show resolved semantic recipes and the share basis
   on the site, retaining source audit access. Prepare the schema/quantity contract
   for BEMGen; translator implementation remains its responsibility. Local checks
   only unless publication is separately authorized.

Program library supplies the share profiles; Atlas produces and validates the
resolved equivalent constructions; BEMGen instantiates semantic components and
reconciles represented mass quantities with actual geometry. Construction,
program and system products remain independently selectable.

## 7 Decisions for annotation

The three-layer direction and one-assembly-per-semantic goal are agreed design
inputs. The following details are proposals; blank annotations are not approval.

| Decision | Proposed resolution | User comments |
|---|---|---|
| D1 Semantic census | One recipe per physical role; collapse fixed/operable window recipes; InternalMass plus a separately reconciled FloorDistributedMass semantic | |
| D2 Program-library contents | Publish complete source composition and exposure/volume/story/mass profiles as supporting data, independently of program load JSON | |
| D3 Weight basis | Prefer known net source exposure; allow labelled floor-share imputation only among eligible contributors with explicit treatment of buffer scopes | |
| D4 Infiltration | Carry the accepted fixed reference ACH unchanged initially; add program-sensitive flow-conserving reduction only as an explicitly selected later policy | |
| D5 Unconditioned nodes | Retain boundary/topology distinctions; collapsing attic/garage/plenum thermal nodes requires a separate approved network reduction | |
| D6 Numerical acceptance | Use the provisional tolerances in section 5 for pilot evaluation, revisiting them only against documented results | |
| D7 Missing source quantities | Recover source values or publish a blocked status; bring any proposed furnishings, room-height or mass-distribution defaults back for explicit decision | |

## 8 Evidence and audit scope

The feasibility counts are read-only joins of the files below at baseline
`689e5b6a3a0582fe2cb56c2bc42f885518c2fd8a`, inspected 2026-10-15. The counted-space
join uses native standards building/space keys and preserves the established
`Any` Plenum convention. Residential joins use the exact source fixture ID.
Commercial space overrides are counted once per reference and space type;
story overrides once per reference and story. No native model generation or
EnergyPlus validation has been run for this proposal.

| Repository input | SHA-256 |
|---|---|
| `data/construction-releases/v2.2.0/manifest.json` | `4a26d369805da34b6eb96a86ec2b48a624fce7b2af00e2b79436c181ea77242b` |
| `data/construction-inputs/geometry-v1.json` | `66274536119e312f296abc05c98223e69f296c8560fff4670589216b4a581bf0` |
| `data/construction-inputs/commercial-ach-geometry-v1.json` | `10b50e099bed46d80f0c9dd7a083ea16a28475ab97e54b4d6846dbd7f8a65d1a` |
| `data/releases/v0.2.0/programs.json` | `71076176fda99b940873fafce8a4bc89a4a72dad903b780b887e3d7d57173d92` |
| `data/definition-releases/v0.1.1/programs.json` | `98d8fc21073fb7f47a286bcc708aca5468d0cc5abef43e80525f0c5a3ce71d60` |
| `data/definition-releases/v0.1.1/compositions.json` | `cfdbde1066da73909e2bab6d9cf8de0111613a58105de0269b05f5b1a6eae183` |

Method references, EnergyPlus 24.2 documentation, accessed 2026-10-15:

- [Layer properties and construction definitions](https://bigladdersoftware.com/epx/docs/24-2/input-output-reference/group-surface-construction-elements.html).
- [Transient conduction and transfer functions](https://bigladdersoftware.com/epx/docs/24-2/engineering-reference/conduction-through-the-walls.html).
- [InternalMass exposed-area convention](https://bigladdersoftware.com/epx/docs/24-2/input-output-reference/group-thermal-zone-description-geometry.html#internalmass).
- [Airflow calculation bases](https://bigladdersoftware.com/epx/docs/24-2/input-output-reference/group-airflow.html#zoneinfiltrationdesignflowrate).

The proposed fitting strategy, tolerances and new library profile fields are
Atlas design choices. The cited engine documentation does not validate this
equivalence scheme or establish these acceptance thresholds.
