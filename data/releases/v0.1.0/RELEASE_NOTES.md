# v0.1.0 — 2026-10-02

Initial release of the energy-archetype source-input atlas, schema 0.1.0.
Includes 296 deterministic program rows, 319 typed schedules, 2,451 conditional
envelope components, 788 source HVAC definitions, 941 program/system mapping
groups, 707 conditional efficiency rules, 139 ResStock options, 227 ComStock
options, 5,868 field-provenance records and 91 locked raw-source files.

Nine typologies span 43 combinations across DOE reference pre-1980/1980-2004
and standards 90.1-2007/2013/2019 input templates. High-rise apartment is absent
in the two DOE reference selections. Program rows are climate-independent;
envelope components retain 22 source climate-zone sets and applicability
predicates. Weather and geometry are external.

The Medium Office pilot validated source units, named schedules and OSM/HVAC
assignments before expanding. Independent comparisons verify raw source inputs,
not equivalence to final generated EnergyPlus models. Official DOE/PNNL linked
Medium Office benchmark downloads returned 404 and remain a documented gap.

Sixteen pre-1980 mass-floor U=0 inputs are withheld as null with original evidence.
Infiltration, conditioned states, area fractions, HVAC sizing/fuel/terminal/COP
resolution and calendar adaptation require downstream work. This release is
scientifically interpretable source data, not a ready-to-run simulation model.

Canonical JSON tables are diffable; scripts reproduce them from checksum-locked
downloads and validate them. The release contains frozen contracts/selection,
upstream notices and a manifest with per-file SHA-256, length and record counts.
Original work remains unlicensed as requested. No migration is needed for this
initial schema; future breaking changes must provide migration instructions.
