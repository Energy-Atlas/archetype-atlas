# Independent source-recovery pilots

These examples validate recovered source inputs. They are not published ready
exports and do not instantiate geometry, size a model or run EnergyPlus.

| Example | Source context | Validation boundary |
| --- | --- | --- |
| [Medium Office construction](medium-office-construction.json) | 90.1-2019, source ClimateZone 4 group, exact MediumOffice package | Nine selected elements, ordered materials and explicit ground geometry operands |
| [Medium Office system](medium-office-system.json) | 90.1-2019, exact PVAV source record and nominal main DHW heater | Source recipe and heater inputs; performance/template/curve/loss translation remains blocked |
| [Residential construction](residential-construction.json) | One unchanged source fixture | Selected enclosure R/U/SHGC/50 Pa leakage evidence; complete assembly translation remains blocked |
| [Residential system](residential-system.json) | The same source fixture, independently exported | Selected HVAC and DHW equipment, source defaults and heater calculations; curves/controls/distribution remain blocked |

The same example fixture is used for comparison only. No automatic match between
program, construction and system contracts is implemented. Neither construction
nor system pilots embed program loads or water demand. Source stock/code context
is retained; the ClimateZone 4 source group is not relabeled as a particular EPW.

For each physical field, inspect `origin`, `evidence`, original value/unit,
conversion and exact source file/revision. `source_default` is an executed
upstream choice, not a new Atlas fallback. The construction recovery retains the
four historical generic assumptions within their existing scope. `unresolved`
lists source physics; `required_bindings` lists simulation consumer operands.

Regenerate source inputs: `python -m scripts.recover_energy_inputs`.
Reexecute/compare: `python -m scripts.recover_energy_inputs --check`.
Validate/regenerate examples: `python -m scripts.energy_recovery_validation`.
Verify examples/receipt: `python -m scripts.energy_recovery_validation --check`.
These commands do not build the site or regenerate program JSON.

See the [validation receipt](../../reviews/energy-source-recovery-validation.json),
[construction field review](../../reviews/construction-json-field-review.md),
[system field review](../../reviews/system-json-field-review.md) and
[source-recovery ADR](../../adr/0017-independent-energy-source-recovery.md).
