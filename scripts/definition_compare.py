"""Property-wise comparison; labels and unknown values cannot establish identity."""
import math

METADATA = {'id', 'name', 'source_id', 'source_file_id', 'evidence_id', 'evidence_ids',
            'locator', 'original_value', 'original_unit', 'interpretation', 'extraction_date',
            'building_type', 'template', 'source_family', 'gate', 'climate', 'evidence_view',
            'derivation', 'performance_id', 'source_definition_id', 'applicable_building_types',
            'material_id', 'source_code_defaults', 'source_material_locator'}


def physical_properties(value):
    if isinstance(value, dict):
        if {'value', 'unit', 'status'} <= value.keys():
            return {'value': value['value'], 'unit': value['unit'], 'status': value['status']}
        return {k: physical_properties(v) for k, v in value.items() if k not in METADATA}
    if isinstance(value, list):
        return [physical_properties(v) for v in value]
    return value


def compare_elements(kind, left, right, tolerances=None):
    if kind not in {'construction', 'hvac_system', 'component', 'material'}:
        raise ValueError('Unsupported comparison kind')
    tolerances = tolerances or {}
    if any(not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in tolerances.values()):
        raise ValueError('Tolerances must be finite and nonnegative')
    result = {'identity': True, 'similar': True, 'matches': [], 'differences': [],
              'unknowns': [], 'basis': {'kind': kind, 'tolerances': tolerances}}

    def walk(a, b, path):
        if a is None or b is None:
            result['unknowns'].append(path)
            result['identity'] = result['similar'] = False
        elif isinstance(a, dict) and isinstance(b, dict):
            for key in sorted(a.keys() | b.keys()):
                walk(a.get(key), b.get(key), path+'.'+key if path else key)
        elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
            for i, (av, bv) in enumerate(zip(a, b)):
                walk(av, bv, f'{path}[{i}]')
        elif type(a) is type(b) and a == b:
            result['matches'].append(path)
        else:
            numeric = all(isinstance(x, (float, int)) and not isinstance(x, bool) for x in (a, b))
            within = numeric and path in tolerances and abs(a-b) <= tolerances[path]
            result['differences'].append({'property': path, 'left': a, 'right': b, 'within_tolerance': within})
            result['identity'] = False
            result['similar'] &= within
    walk(physical_properties(left), physical_properties(right), '')
    if not result['matches']:
        result['identity'] = False
    return result
