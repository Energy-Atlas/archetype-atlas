# Shared construction mass release 1.0.0

Detailed construction JSON 2.1.0 and unified JSON 1.2.0 embed the same source
mass-accounting contract 1.0.0. Original detailed 2.0.0 / distribution v2.2.0
and equivalent 1.1.0 releases and APIs remain immutable. No thermal refitting,
new ground/system models, program or schedule generation, or BEMGen code.

contexts.json maps source context IDs to deduplicated contracts.json entries.
Each standalone export embeds the selected contract, including original added
mass recipes, quantities, scopes, physical budgets and source provenance.
All three schemas are included. Source assemblies, assignments, infiltration
and equivalent recipes remain unchanged. Legacy InteriorPartition is retained
as material evidence; additional mass is instantiated from the new inventory
once, independently of residual restoration. Known zero is explicit; unknown
quantities/materials fail export instead of becoming zero.

Normalize budgets by actual counted floor area. Count physical paired faces
once using the frozen source area policy, and retain residential inferred
adiabatic object conventions. Restore max(0, reference minus represented)
capacity by category; preserve signed residual/excess diagnostics. Allocation
to geometry and simulation remain BEMGen responsibilities.

python -m scripts.construction_mass_release --check verifies exact reproduction.
Add --validate-all to validate both representations of every supported context.
Use --context-id ID --representation detailed|unified --output PATH for one
standalone export. --examples creates the seven paired review examples under
docs/examples/construction-mass-v1; --examples --check verifies them.

Frozen profiles contain the needed geometry/mass operands; no native runtime
or annual simulation is needed. Preserve original Atlas and upstream notices
from the detailed/equivalent source releases. Atlas original work remains
unlicensed; no publication or BEMGen fixture-transfer permission is implied.
