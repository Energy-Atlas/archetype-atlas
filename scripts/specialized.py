"""Record generator-declared refrigeration units without assuming source intent."""
import re

from scripts.common import stable_id

GENERATOR = 'lib/openstudio-standards/prototypes/common/objects/Prototype.refrigeration.rb'


def unit_interpretations(raw, raw_root):
    text = (raw_root/'openstudio-standards'/GENERATOR).read_text(encoding='utf-8')
    declarations = {}
    for number, line in enumerate(text.splitlines(), 1):
        for field, unit in re.findall(r"OpenStudio\.convert\(props\['([^']+)'\], '([^']+)'", line):
            declarations.setdefault(field, []).append((unit, number))
    result = {}
    for key, value in raw.items():
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            continue
        matches = declarations.get(key, [])
        units = {unit for unit, _ in matches}
        declared = next(iter(units)) if len(units) == 1 else None
        result[key] = {'source_units': declared,
                       'status': 'generator_declared_source_intent_unverified' if declared else 'unresolved_no_unique_conversion_unit',
                       'generator_source_file_id': stable_id('sourcefile', 'openstudio-standards', GENERATOR),
                       'generator_lines': sorted({line for _, line in matches}),
                       'notes': 'First conversion input unit in generator, not proof of upstream numeric intent. '
                                'Further curve/geometry operations may change dimensions. No normalization applied.'}
    return result
