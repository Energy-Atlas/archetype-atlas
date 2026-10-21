# Combined Construction Suite 1.0.0

Complete detailed construction JSON 3.0.0 and unified JSON 2.0.0 include native
foundation/ground physics alongside their existing above-ground definitions.
The shared mass contract remains 1.0.0. Historical releases are immutable.

Select the existing suite/climate/reference. GroundFloor, FoundationWall,
FloorOverFoundation and RimJoist use normal component/assignment and resource
structures. F/C factors live on assemblies; Kiva parameters live once on the
referenced method; material properties use material resources. No independent
foundation suite, matching system or compatibility object is shipped.

This normalized directory is internal delivery storage. Use export_pair to get
two complete standalone documents, each with its selected dependency closure.
Raw recovery inventories and detailed validation evidence are not copied into
consumer JSON. completeness.json reports the fixed 177-suite/3320-context gate,
source-supported absence and native unified exceptions separately.

Actual BEM geometry, foundation groups/hosts and method-specific weather/site
inputs remain necessary. A no-contact source unit cannot supply an invented
whole-building ground slab. Missing executable physics prevents publication.
Ordinary unified components retain their simplified representations; native
ground assignments are preserved only where homogenization is unjustified.

python -m scripts.construction_foundation_release --check
python -m scripts.construction_foundation_release --examples --check
python -m scripts.validate_construction_foundation --all

Use --context-id ID --representation detailed|unified --output PATH to export.
Native source recovery, program/schedule generation and site publication are
not run by these commands. BEMGen integration/simulation is a separate worker's
responsibility. Preserve LICENSE and notices/. Original Atlas work remains
unlicensed; upstream licenses do not grant MIT relicensing of Atlas originals.
