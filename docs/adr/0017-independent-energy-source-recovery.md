# ADR 0017: Independent construction and system source recovery

Date: 2026-10-12. Status: accepted execution boundaries; recovery implemented.
Consumer export interfaces and publication remain subsequent work.

The later [ADR 0019](0019-all-variant-readiness-and-hvac-delivery-scope.md) requires
ready consumer exports for every construction/HVAC variant and removes detailed
DHW models from step 2 delivery. This ADR's HVAC/DHW recovery scope and detailed
translation gaps remain historical evidence; detailed DHW readiness is no longer
a release blocker.

The later [draw-only program water-heating decision](0018-draw-only-program-water-heating-energy.md)
refines the proposed DHW consumer delivery. Detailed equipment and losses remain
source evidence; the simplified program representation excludes standby losses.

## Decision

The user authorized autonomous field reviews and source recovery, with focused
Medium Office/residential pilot validation. Program, construction and system JSON
remain independent. Cross-contract mixing, compatibility resolution and geometry
generation are outside this pass. Systems cover HVAC and domestic hot-water
equipment together, including heater losses and solar.

Use source-defined defaults and previously approved assumptions only. Retain
unknown physics explicitly and block readiness; do not select new Atlas defaults
to fill equipment performance, assemblies or source topology. Follow the program
JSON conventions for SI, exact source identity, raw evidence, derived values,
explicit consumer operands and deterministic receipts. Preserve the program
2007/no-holiday aggregation convention without changing simulation calendars.

Store separate versioned recovery inputs under `data/construction-inputs/` and
`data/system-inputs/`. Their schema is `energy-source-recovery-v1.schema.json`.
It describes recovery evidence and dispositions, not the final construction or
system consumer contract. `resolved` means no identified source blocker in this
recovery scope; it does not certify an engine simulation or published ready JSON.
Frozen releases and published program JSON are unchanged. Reuse the prior pinned
residential CFA calculation as source-default evidence for nominal heater values,
not as delivered geometry or an executable dependency on program JSON.

## Source interpretation corrections

- Twelve glazing assemblies have duplicate names with identical ordered material
  recipes and different selector metadata. Recover the physics, retain every
  candidate and reject any duplicate with different physical properties. Do not
  merge their source contexts or IDs.
- Of 123 ground-wall rows labeled C-factor without a C target, 64 have explicit
  source U targets. Recover their film/insulation adjustment as layered U ground
  constructions. Forty zero source targets invoke upstream insulation removal;
  calculate positive assembly U from the resulting layers and films instead of
  exporting zero physical transmittance. The other 59 remain explicitly blocked
  pending interpretation of the source ground construction model.
- For 166 material instances with missing surface properties, execute the pinned
  source setters/SDK defaults. Ruby `nil.to_f` produces zero; thermal zero is
  rejected by OpenStudio 3.10.0 and retains 0.9, while solar/visible zero is
  accepted. Massless roughness retains SDK `Smooth`. Preserve the original null,
  setter result, constructor/runtime identity and source-default origin.
- Detailed glazing retains optical layers. Absent assembly SHGC/VT summaries are
  distinguishable from missing optical layer operands; do not fabricate simple
  glazing summaries or require mass properties for massless materials.
- Medium Office PVAV's actual caller skips hot-water-loop creation and does not
  forward its heating-type label. Recover its source gas/DX/electric-reheat
  recipe; do not import unrelated `vav_*` fan fields as assigned PVAV values.
  Factory performance, curves and later template adjustments remain unresolved.
- Residential source option expansions recover nominal R/U/SHGC/leakage operands
  and selected HVAC/DHW equipment. Pressure-test leakage keeps 50 Pa; it does not
  become natural infiltration. No reference dwelling surfaces or HVAC sizing are
  generated to hide missing geometry-dependent translation.
- Residential storage/tankless loss and conversion calculations run pinned
  `Defaults`/`Waterheater` methods. Pre-solar heater UA and separate solar equipment
  are retained; any downstream solar adjustment must be applied exactly once.
  Delivered fixture water demand is not copied into system energy or multiplied.

## Boundaries and consequences

Geometry, serving assignment, sizing, ground boundary, weather/mains temperature
and loss hosts are explicit consumer operands. Missing assemblies, component
factory performance, controls and curve assignments are source blockers, not
ordinary user bindings. Seasonal/integrated ratings retain their metric names.

Signed fixture-related room gains and distribution-waste water draws remain
outside program JSON. Equipment recovery does not reintroduce them as program
loads. The source option evidence can preserve distribution selections without
adding a new water demand or claiming a translated distribution-loss model.

Field reviews are keyed by property across applicable model types and preserve
user annotation blocks on regeneration. The machine census retains affected IDs;
its frozen-definition and recovered-field populations are identified separately.

Only focused tests, recovery-schema/physical/provenance/inventory checks and exact
reexecution were run in this pass. Full site builds, GitHub CI and unchanged
program validation were deliberately skipped at the user's request. All normal
release gates remain required before publication. Original work stays unlicensed;
upstream notices remain in `data/releases/v0.2.0/sources/licenses/` and locked archives.

## Remaining source work: concrete next actions

1. Translate residential enclosure recipes into ordered material assemblies with
   explicit geometry operands; retain nominal R-values as evidence until then.
2. Trace the 59 remaining ground rows through their source constructor branch.
   If their model is ordinary layered ground conduction, document that model and
   its soil boundary; do not invent F/C values.
3. Retrieve/pin the exact HVAC factory helpers and template adjustment methods,
   then recover component performance, controls and curve associations. Keep
   capacity-band and rating-date predicates until consumer sizing resolves them.
4. Translate the recovered heater/solar recipes and commercial heater efficiency
   and loss branches. Preserve nominal prototype sizes as source variants rather
   than automatically sizing a mixed consumer building.
5. Finalize the separate consumer schemas and raw/ready behavior after these
   source requirements are explicit; publish through the existing protected-main
   gates in the later publication phase.
