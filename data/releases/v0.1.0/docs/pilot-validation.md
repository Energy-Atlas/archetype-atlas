# Medium Office pilot evidence

The `90.1-2013` Medium Office pipeline was built and validated before full
extraction. Command: `python -m scripts.build --pilot --output data/interim/medium-office-pilot`.

The pinned `ashrae_90_1_2013.spc_typ.json` row `Office / WholeBuilding - Md Office`
reports 5 people/1,000 ft², 0.82 W/ft² lighting and 0.75 W/ft² electric equipment.
Tests verify their SI values independently using 1 ft² = 0.09290304 m².
Gas equipment remains null. Nine typed referenced schedules retain source rules.
OSM semantics provide 15 office spaces, plus three plenums; HVAC maps provide
three PVAV source systems. Grouped mappings preserve counts and shared programs.

The pilot had 2 programs, 9 schedules, 378 conditional envelope components,
3 systems, 4 program/system mapping groups and 184 equipment efficiency rules.
Schema, bounds, schedule lengths and dates, all-date thermostat deadbands,
foreign keys, field provenance and raw checksums passed. Mutation tests reject
negative densities/U-values/infiltration, invalid SHGC, schedule bounds/length,
thermostat crossover, duplicates, orphan schedules, inconsistent labels and
missing provenance. A rebuild test verifies byte equality and CSV generation.

This verifies source-input normalization and model-tag/system-map consistency.
No EnergyPlus/OpenStudio runtime simulation was executed. Direct DOE/PNNL IDF
or published-scorecard validation remains unavailable as described in the source
inventory; it is not counted as a passing benchmark comparison.
