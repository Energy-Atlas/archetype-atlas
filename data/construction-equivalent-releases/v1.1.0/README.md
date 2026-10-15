# Additive building-level construction equivalents 1.1.0

Precomputed source-archetype shares resolve one assembly per applicable semantic.
Detailed construction v2.2.0 and its historical sources/exports remain unchanged.
Ground, systems and BEMGen translation are outside this release.

Use python -m scripts.construction_equivalent_release --context-id ID --output selected.json
to obtain a standalone document. Source context IDs are retained for selection.
Use --check to rebuild from frozen inputs and compare exact UTF-8/LF bytes.
Construction-only generation; no annual schedules, website or CI/CD build.

catalogue.json stores context metadata, component_sets.json shared semantic recipes
and quantity rules, assemblies.json their thermal/optical data. completeness.json
records source gaps and approximation flags; blocked is never interpreted as zero.
Supporting program-library profiles live in data/program-support/construction-weighting-v1.1.0/.
Recover those once with python -m scripts.construction_weighting --recover --check;
this executes pinned geometry and source mass rules, not an annual energy model.

Opaque fitting uses two massive layers and one massless resistance (or source-
proven massless construction), two fitted parameters and no complexity escalation.
Conserve reference-film U and capacity; keep measured response errors even when
the approximation is poor. Analytical checks/small material smoke runs establish
numerical/input consistency, not annual building-energy accuracy. Systematic
construction-versus-zoning error validation is deferred to the journal work.

Mass quantities describe additional source mass or a residual physical capacity
budget, never an instruction to add slabs already represented by surfaces.
BEMGen reconciles actual geometry; consumer geometry is not a blending input.
Natural ACH is copied unchanged from the selected detailed reference context.
Source overhang dimensions remain evidence; BEMGen supplies actual geometry.
Paired-face budgets use the accepted symmetric mean with unequal-multiplier flags.

Preserve LICENSE and sources/licenses upstream notices. Original Atlas work is
unlicensed by user choice. Local research artefact; no production publication.
