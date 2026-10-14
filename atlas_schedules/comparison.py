"""Numerical and scientific equality for emitted bundles, independent of JSON bytes."""
import math


def _close(actual, expected, tolerance, quant_digits=None):
    if isinstance(actual, bool) or isinstance(expected, bool):
        return actual == expected
    if not isinstance(actual, (int, float)) or not isinstance(expected, (int, float)):
        return False
    if not math.isfinite(actual) or not math.isfinite(expected):
        return False
    extra = 0
    if quant_digits is not None and expected != 0:
        extra = 0.5 * 10 ** (math.floor(math.log10(abs(expected))) - quant_digits + 1)
    return abs(actual - expected) <= max(tolerance['abs_tol'], tolerance['rel_tol'] * abs(expected)) + extra


def _binding_key(binding):
    return (binding.get('instance_key'), binding.get('program_id'),
            binding.get('demand_id', binding.get('control_quantity')), binding.get('slot'), binding.get('kind'))


def _map_bindings(bundle):
    result = {}
    for binding in bundle.get('bindings', []):
        key = _binding_key(binding)
        if key in result:
            raise ValueError(f'Duplicate binding {key}')
        result[key] = binding
    return result


def _compare_schedule(actual, expected, tolerances, path, differences):
    if not actual or not expected:
        differences.append(f'{path}/schedule_missing')
        return
    for field in ('unit', 'year', 'clock', 'timestep_minutes', 'source_precision_significant_digits'):
        if actual.get(field) != expected.get(field):
            differences.append(f'{path}/schedule/{field}')
    unit = expected.get('unit')
    tkey = 'temperature_C' if unit == 'C' else 'activity_W_person' if unit == 'W/person' else 'fraction'
    av, ev = actual.get('values', []), expected.get('values', [])
    if len(av) != len(ev):
        differences.append(f'{path}/schedule/length')
        return
    digits = expected.get('source_precision_significant_digits')
    for i, (x, y) in enumerate(zip(av, ev)):
        if (x != y if unit in {'person', 'count'} else not _close(x, y, tolerances[tkey], digits)):
            differences.append(f'{path}/schedule/values/{i}')
            break


def compare_bundles(actual: dict, expected: dict, policy: dict) -> list[str]:
    """Return human-readable differences at source-significant reference paths."""
    differences = []
    tolerances = policy['tolerances']
    for field in ('schema_version', 'algorithm_version'):
        if actual.get(field) != expected.get(field):
            differences.append(field)
    for field in ('calendar', 'resource_set_id'):
        if actual.get('metadata', {}).get(field) != expected.get('metadata', {}).get(field):
            differences.append(f'metadata/{field}')
    if actual.get('generation') != expected.get('generation'):
        differences.append('generation/source_decisions')
    try:
        a_bindings, e_bindings = _map_bindings(actual), _map_bindings(expected)
    except ValueError as error:
        return differences + [str(error)]
    if a_bindings.keys() != e_bindings.keys():
        differences.append('bindings/included_channels')
    for key in e_bindings.keys() & a_bindings.keys():
        a, e = a_bindings[key], e_bindings[key]
        path = f'bindings/{key}'
        for field in ('fuel', 'host', 'budget_method', 'control_quantity'):
            if a.get(field) != e.get(field):
                differences.append(f'{path}/{field}')
        if e['kind'] == 'load':
            at, et = a['reference_target'], e['reference_target']
            for field in ('quantity', 'unit', 'basis', 'method', 'magnitude_unit', 'fuel', 'host',
                          'evidence', 'original_magnitude', 'installed_rating', 'capacity_constraint'):
                if at.get(field) != et.get(field):
                    differences.append(f'{path}/reference_target/{field}')
            tkey = 'annual_volume_m3' if et['unit'].startswith('m3') else 'annual_energy_integral'
            if not _close(at.get('total'), et.get('total'), tolerances[tkey]):
                differences.append(f'{path}/reference_target/total')
            am, em = a['effective_magnitude'], e['effective_magnitude']
            for field in ('unit', 'basis'):
                if am.get(field) != em.get(field):
                    differences.append(f'{path}/effective_magnitude/{field}')
            if not _close(am.get('value'), em.get('value'), tolerances[tkey]):
                differences.append(f'{path}/effective_magnitude/value')
        _compare_schedule(actual.get('schedules', {}).get(a['schedule_id']),
                          expected.get('schedules', {}).get(e['schedule_id']),
                          tolerances, path, differences)
    def scientific_constituents(bundle):
        result = {}
        for item in bundle.get('constituents', []):
            key = (item.get('instance_key'), item.get('program_id'))
            result[key] = {k: v for k, v in item.items() if k not in {'schedule_ids', 'binding_indices'}}
        return result
    if scientific_constituents(actual) != scientific_constituents(expected):
        differences.append('constituents/source_parameters_or_decisions')
    def constituent_schedules(bundle):
        return {(item.get('instance_key'), item.get('program_id'), slot): sid
                for item in bundle.get('constituents', [])
                for slot, sid in item.get('schedule_ids', {}).items()}
    a_refs, e_refs = constituent_schedules(actual), constituent_schedules(expected)
    if a_refs.keys() != e_refs.keys():
        differences.append('constituents/included_channels')
    bound_slots = {(b['instance_key'], b['program_id'], b['slot']) for b in e_bindings.values()}
    for key in (a_refs.keys() & e_refs.keys()) - bound_slots:
        _compare_schedule(actual.get('schedules', {}).get(a_refs[key]),
                          expected.get('schedules', {}).get(e_refs[key]),
                          tolerances, f'constituents/{key}', differences)
    return differences
