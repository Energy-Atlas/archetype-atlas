# Proposal for one construction assembly per semantic

Date: 2026-10-15. Status: generally approved; revised to incorporate user review.
Source audit baseline: `689e5b6`. Initial proposal commit: `9ea86d6`.

An additional unified building-level export should provide exactly one assembly for each
applicable semantic: one exposed-wall construction, one roof construction, one
exposed-floor construction, and equivalent single recipes for the other supported
roles. Program and building-type distinctions are resolved before export using
explicit shares. BEMGen then assigns by component semantic, without recovering
the original program-to-face relationships. This representation is intended for
applications where program-specific envelope allocation is unavailable or
unnecessary. It is additive: preserve existing detailed assemblies, assignment
rules, source mappings and exports as usable products, alongside the equivalent
representation. Detailed data are not demoted to audit-only evidence.

The same resolution must cover internal mass, floor-distributed mass and
infiltration. Each quantity uses its own conservation basis. Floor-area shares
can drive the process, but exposed surfaces, stored heat and airflow cannot all
be averaged with the same unqualified weights.

All required share profiles should be obtainable through the program library.
That requires extending its supporting composition data: the current library
does not yet contain complete whole-building program/exposure/mass profiles for
every construction archetype. The feasibility map below identifies the work.

Precomputed archetype-based shares are the default. Recover exposure from source
archetypes once and publish their profiles; consumer geometry-specific weighting
is not required. Actual component areas remain BEMGen inputs for instantiation,
not inputs needed to choose or refit the default equivalent assembly.

This revision includes the small linear-conduction design probe in section 5.
It does not implement a catalogue exporter, change frozen JSON, build the site,
push, dispatch CI/CD, or implement BEMGen. Ground and systems remain deferred.
Mechanical outdoor-air requirements are inventoried here only to distinguish
them from envelope infiltration.

## 1 Target contract and semantic census

Add a separately versioned `building_level_equivalent` representation, initially
schema 1.0.0, alongside the existing detailed construction contract. It does not
replace or migrate the existing schema, exports or assignment rules. A consumer
explicitly selects detailed or unified representation. A unified export has:

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
  measured approximation errors. Source recipes remain available in the detailed
  representation; only the unified representation omits alternative assignments.

The unified semantic census is based on the existing component roles: exterior wall,
roof, exposed floor, exterior window, opaque door, glass door, overhead door,
skylight, interior wall/floor/ceiling/door/window, internal mass, tubular daylight
dome/diffuser, and shading where supported. Map the source `InteriorPartition`
InternalMass role to the clearer unified semantic `InternalMass`, leaving the
original role untouched in existing exports. Add a distinct
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

The default profile describes each source archetype separately and is precomputed.
Source stock fixtures, vintages and climate variants are not population samples
to be blended together. A user-selected mixed-building composition needs
explicit group shares; none are inferred from stock prevalence. Custom mixtures
can use the same calculation later, but are not required to obtain a ready
archetype-based equivalent and do not introduce geometry-specific weighting.

For component `c`, use net exposed areas of the source archetype when available,
not areas from the consumer BEM. The profile stores the resulting default weights.
Exposure ratios also provide a controlled derivation for an explicit custom mix:

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

For compatible assemblies, use precomputed exposed-area fractions `f_i`. Evaluate
every source assembly under common reference films of 0.04 m2 K/W outside and
0.13 m2 K/W inside. These are declared Atlas fitting conditions, not universal
EnergyPlus convection coefficients. Compute from attained layer properties:

```text
R_i = sum_j(thickness_ij / conductivity_ij) + sum_j(massless_R_ij)
U_i = 1 / (0.04 + R_i + 0.13)
U_target = sum(f_i * U_i)
R_target = 1 / U_target - 0.04 - 0.13
C_A_target = sum(f_i * sum_j(rho_ij * cp_ij * thickness_ij))
```

Do not substitute nominal code U targets for attained properties. If only a
reported U is available, resolve its film convention before including it. Explicit
massless layers contribute zero capacity; missing mass properties remain unknown.

#### Fixed parameters and two optimized parameters

Use three slots: exterior `Material`, middle `Material:NoMass`, interior
`Material`. This is an effective thermal model, not a claim of actual composition.
For positive total capacity C = C_A_target, fix specific heat to 1000 J/(kg K)
and density to min(1000, C / (1000 * 0.04)) kg/m3. This numerical normalization
gives at least 0.04 m total massive-layer thickness; its values are derived model
parameters, not recovered source material properties. Fix R_target and C exactly.

Optimize only x, the exterior fraction of capacity, and beta, the fraction of
total material resistance assigned to the two massive layers:

```text
C_ext = x*C;                 C_int = (1-x)*C
R_ext = x*beta*R_target;     R_int = (1-x)*beta*R_target
R_middle = (1-beta)*R_target
thickness_side = C_side / (density*specific_heat)
conductivity_side = thickness_side / R_side
```

The two massive layers consequently share conductivity. No free fitting of
individual density, specific heat, thickness, absorptance or extra layers occurs.
If source-proven C is zero, use a massless representation without invented mass.

#### Weighted transient response and fitting objective

Use linear one-dimensional diffusion with constant layer properties and the
common films above. Calculate each original multilayer assembly independently,
then area-weight its boundary heat flux response, not its layer properties.
For a sinusoidal angular frequency omega, a layer with resistance R and capacity C
has the thermal quadrupole:

```text
z = sqrt(i*omega*R*C)
M_layer = [[cosh(z), R*sinh(z)/z],
           [i*omega*C*sinh(z)/z, cosh(z)]]
M_massless = [[1, R], [0, 1]]
M_total = M_outside_film * M_layer1 * ... * M_inside_film
Y = [[D/B, -1/B], [-1/B, A/B]] for M_total = [[A,B],[C,D]]
Y_target(omega) = sum_i(f_i * Y_i(omega))
```

Y maps the two air-boundary temperatures to inward heat fluxes. Excite one
boundary at a time with a 1 K sinusoid about 22 degC, holding the other at 22 degC.
The real part of Y*exp(i*omega*t) is the periodic transient response. Including
all four Y entries fits both transmission and storage response on both sides.
Fit periods of 6, 24 and 168 hours with equal weight; retain 12 and 72 hours as
simple checks outside the fitted periods. No annual weather or zoning model is
needed for this design probe.

Minimize the mean of |Y_fit-Y_target|^2 / max(|Y_target|, U_target)^2 across the
three fitted periods and four matrix entries. The U_target floor prevents a
nearly zero transmitted response from dominating the objective. The reported
normalized response RMS is the square root of this objective.

Use a deterministic grid: x = 0.08, 0.10, ..., 0.92; beta = 0.005, 0.01, 0.02,
0.04, 0.08, 0.16, 0.32, 0.64, 0.8. Refine once around the best admissible point
with x offsets -0.010 through +0.010 at 0.002 spacing and beta multipliers 0.80
through 1.20 at 0.04 spacing. Break exact objective ties by ascending x, then beta.
Record all operands, search version, selected parameters and measured errors.
Do not introduce more layers or a sophisticated optimizer unless simple tests
show a meaningful practical need and the change is reviewed.

#### Material constraints and fixed surface properties

Reject nonfinite/nonpositive R, density, conductivity or massive-layer thickness;
require 0 < x,beta < 1 and specific heat >= 100 J/(kg K). For this initial method,
also require each massive layer thickness >= 0.003 m, conductivity <= 5 W/(m K),
and diffusivity <= 1e-5 m2/s. These conservative search bounds follow the
[EnergyPlus material guidance](https://bigladdersoftware.com/epx/docs/24-2/input-output-reference/group-surface-construction-elements.html#material);
they do not by themselves guarantee a successful engine run. Preserve resistance
and capacity to numerical precision; never clip a negative middle resistance or
invent capacity to make a candidate valid. An empty admissible grid is a visible
fit failure requiring inspection, not an automatic increase in layer count.

Fix each exposed face's thermal, solar and visible absorptances to its separately
area-weighted source-face value, constrained to [0,1]. Select each face's roughness
from the largest-weight source contributor, breaking ties by source assembly ID;
categorical roughness is not averaged. These are declared approximation policies,
outside the two-parameter conduction fit. Missing face properties remain unknown.
Solar geometry, nonlinear films, moisture and phase-change materials are outside
this probe's applicability. A focused EnergyPlus input/run smoke check remains
necessary when actual derived exports are implemented.

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

For two-sided interior surfaces, reuse the two-parameter conduction procedure
with 0.13 m2 K/W reference films on both sides. For a one-sided InternalMass
object, use the source-consistent exposed-area/capacity convention and an
adiabatic back: reduce the two-port admittance to
Y_one_face = Y00 - Y01*Y10/Y11 before weighting and fitting. Match that scalar
complex response at the same periods, normalized by max(|Y_target|, C/86400).
Keep the declared equivalent R as a fixed source-derived reference parameter;
an adiabatic mass object has no steady through-conductance to identify by fitting.
Floor-distributed mass follows the one-sided convention only where BEMGen uses
it as an InternalMass object. The three exterior examples below do not test this
path; add one small mass example when its quantity inventory is available.

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

## 5 Focused checks and practical acceptance

Validate the share table before fitting assemblies. For each building, template,
reference and applicable climate, enumerate every semantic and every source
override, apply precedence, and assign each physical contribution exactly once.
Check whole-building and subgroup denominators, excluded/non-counted scopes,
positive areas/volumes, matched program IDs, multipliers, story coverage and
complete input provenance. Equal source names are not a sufficient join key.
Report feasibility per semantic as direct, derivable, assumption required,
not applicable or blocked; do not convert a partial mapping into a whole-set pass.

Conservation checks compare total UA, thermal capacity, exposed mass area and
airflow under their declared reference conditions. Regrouping the same reference
profile must leave these budgets unchanged. Explicit and transferred mass share
one ledger. Preserve consumer geometry requirements for physical instantiation,
but do not require consumer surface allocations to compute the default blend.

### 5.1 Three small design tests, completed locally

The reproducible [probe script](../../../scripts/experiments/construction_equivalence_probe.py)
compares original source multilayer responses against the three-slot equivalent.
Full source IDs, layer R/C values, weights, fitted parameters, periods, Python
version and input SHA-256 receipts are in the
[probe results](../../reviews/construction-equivalence-probe-v1.json).

Run from repository root:

```powershell
.venv/Scripts/python.exe -m scripts.experiments.construction_equivalence_probe --output docs/reviews/construction-equivalence-probe-v1.json
```

All examples use 90.1-2019 assemblies at 3B. Medium Office is the first pilot.
Warehouse uses its precomputed source gross-wall shares, explicitly provisional
because opening subtraction has not yet been recovered. It is a diagnostic blend,
not a canonical net-area weighting release. Both Office and Fine select the same
wall assembly, with Bulk selecting the less-insulated variant; precedence is
applied before weighting, so the building default is not counted again.

| Test | Fitted response RMS | Daily transmission amplitude error | Daily phase error | Maximum response RMS at held-out 12/72 h |
|---|---|---|---|---|
| Medium Office wall, four original layers | 4.84% | -0.52% | 0.056 h | 4.62% |
| Warehouse wall, weighted source variants | 0.56% | +0.02% | 0.001 h | 0.39% |
| Medium Office roof, including thin metal deck | 0.16% | <0.01% | 0.003 h | 0.13% |

R and capacity are preserved within relative 1e-12 in all three examples. Basic
solver checks cover a pure resistor, subdivision of a homogeneous slab,
reciprocity and layer reversal. These check the analytical probe, not EnergyPlus.
The office wall's six-hour response RMS is 8.05%, compared with 2.30% at 24 h;
one transmission-amplitude statistic alone would conceal that larger self-response
error. The two held-out periods check interpolation without optimizing to them.

The tests support retaining the simple two-parameter, three-layer default. They
do not establish a universal error bound, annual energy accuracy or solver
compatibility across all assemblies. No extra layers or advanced optimizer are
justified by these examples.

### 5.2 Acceptance policy calibrated to the design probe

Keep exact input coverage, physical validity, source identity and algebraic
conservation as hard requirements. Treat dynamic-fit thresholds as engineering
screening guidance, with measured errors visible in the derived metadata:

| Check | Initial policy |
|---|---|
| Share, reference, source-identity coverage | 100% of applicable contributions; no unknown contributor dropped |
| Algebraic U, capacity and airflow conservation | Relative error <= 1e-6, with declared absolute tolerances near zero |
| Dynamic response RMS | About 10% or less across the fitted periods and simple held-out checks is an initial practical screen |
| Daily transmission, when amplitude >= 0.1*U_target | About 10% amplitude error and 1 h phase error are initial review flags |
| Near-zero transmission | Inspect absolute complex error / U_target; do not apply unstable percentage or phase gates |
| Internal/floor mass | Conserve quantity and capacity; inspect a small representative response example when implementing this path |
| Engine compatibility | A focused input/run smoke check on representative derived materials; no comprehensive simulation campaign |

The response screen is deliberately approximate, informed by the small examples
above rather than asserted as a scientific standard. A screening exceedance
triggers inspection and a documented UBEM-use judgement; it does not automatically
block an otherwise valid approximation or demand extra layers. Record a quality
flag and the errors rather than silently presenting an exact match. Unknown
inputs and invalid materials remain blocking conditions. Keep fitting-policy and
acceptance-policy versions separate so recalibrating a screen need not refit data.

### 5.3 Deferred scientific validation

Defer systematic isolation of construction-homogenization error from zoning
simplification error. There is no requirement now for paired annual test cells,
an all-archetype dynamic acceptance campaign, or factorial construction-versus-
zoning comparisons. The original annual 2% energy / 5% peak targets are withdrawn
as release requirements. Revisit this research during the journal experiment or
if reviewers identify a need. Ordinary data/schema/provenance checks still apply
to every exported record; the deferral concerns systematic simulation validation.

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
3. **Add the unified schema and reduce pilots.** Keep detailed exports intact.
   Extend the small conduction probe to a residential fixture and internal/floor
   mass example as those quantities become available. Export the additional one-
   assembly-per-semantic representation plus conserved mass quantities and retained
   fixed ACH, with precomputed archetype weights and measured fit quality metadata.
4. **Check data and expand.** Validate schema, physical, share and provenance
   coverage for all 177 source sets and supported contexts. Test hotel story/
   generic and school/retail/hospital composition accounting without a systematic
   all-archetype simulation campaign. Run only focused engine smoke checks.
5. **Integrate after review.** Offer detailed and unified products explicitly on
   the site, retaining original source mappings and assignment rules in detailed
   downloads. Prepare the additional contract for BEMGen; translator implementation
   remains its responsibility. Local checks only unless publication is separately
   authorized. Journal-level error-isolation studies remain deferred.

Program library supplies the precomputed archetype share profiles; Atlas produces
the additional equivalents with focused quality checks; BEMGen instantiates semantic components and
reconciles represented mass quantities with actual geometry. Construction,
program and system products remain independently selectable.

## 7 Decisions for annotation

The user generally approved the proposal with the revisions incorporated above:
reproducible simple fitting, practical acceptance, deferred systematic error
validation, additive exports and archetype-based weighting. The table records
the resulting design and leaves room for further annotation. New unreviewed
choices are not approved merely because their comment cells are blank.

| Decision | Proposed resolution | User comments |
|---|---|---|
| D1 Semantic census | One recipe per physical role; collapse fixed/operable window recipes; InternalMass plus a separately reconciled FloorDistributedMass semantic | |
| D2 Program-library contents | Publish complete source composition and exposure/volume/story/mass profiles as supporting data, independently of program load JSON | |
| D3 Weight basis | Precompute archetype shares from source net exposure, with labelled eligible floor-share fallback; do not require geometry-specific weighting | |
| D4 Infiltration | Carry the accepted fixed reference ACH unchanged initially; add program-sensitive flow-conserving reduction only as an explicitly selected later policy | |
| D5 Unconditioned nodes | Retain boundary/topology distinctions; collapsing attic/garage/plenum thermal nodes requires a separate approved network reduction | |
| D6 Numerical acceptance | Use the simple two-parameter fit; section 5 records completed small tests and flexible screens; defer systematic construction-versus-zoning error studies | |
| D7 Missing source quantities | Recover source values or publish a blocked status; bring any proposed furnishings, room-height or mass-distribution defaults back for explicit decision | |
| D8 Additive representation | Keep detailed assemblies, source mappings, assignment rules and existing exports; add a separately versioned unified building-level product | |

## 8 Evidence and audit scope

The feasibility counts are read-only joins of the files below at baseline
`689e5b6a3a0582fe2cb56c2bc42f885518c2fd8a`, inspected 2026-10-15. The counted-space
join uses native standards building/space keys and preserves the established
`Any` Plenum convention. Residential joins use the exact source fixture ID.
Commercial space overrides are counted once per reference and space type;
story overrides once per reference and story. The later small analytical probe
uses the same source baseline and records its own input receipts. No native
model generation, EnergyPlus run or annual-energy validation has been performed.

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
