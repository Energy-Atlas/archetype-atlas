# Assign inputs to geometry

Keep energy semantics and geometry as separate, versioned inputs.

Your plan generator defines zones, dimensions, adjacency, floors, unit counts,
orientation and conditioned/unconditioned space. The atlas supplies the
source-defined program loads, schedules, envelope evidence and system context.

For each experimental configuration, record the atlas release, selected IDs,
geometry-generator revision, weather file and all downstream resolutions.
Apply per-area and per-person quantities to the appropriate generated geometry.
Never replace unknown area fractions with equal fractions without documenting
and validating that independent modeling choice.

Resolve system assignment and conditioned state explicitly. Benchmark
multiplicity is evidence from a source model and is not necessarily the unit
count or zone count in your generated building.

When comparing zoning abstractions, hold the energy-input selection and
documented resolutions constant so differences remain attributable to the
geometric/zoning changes being studied.
