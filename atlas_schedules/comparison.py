"""Numerical and scientific equality for emitted bundles, independent of JSON bytes."""
import math
from .owners import owner_identity


def _close(actual, expected, tolerance, quant_digits=None):
    if isinstance(actual, bool) or isinstance(expected, bool):
        return False  # continuous numeric comparisons never admit Boolean flags
    if not isinstance(actual, (int, float)) or not isinstance(expected, (int, float)):
        return False
    if not math.isfinite(actual) or not math.isfinite(expected):
        return False
    extra = 0
    if quant_digits is not None and expected != 0:
        extra = 0.5 * 10 ** (math.floor(math.log10(abs(expected))) - quant_digits + 1)
    return abs(actual - expected) <= max(tolerance['abs_tol'], tolerance['rel_tol'] * abs(expected)) + extra


def _binding_key(binding):
    return (binding.get('instance_key'), owner_identity(binding),
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
    tkey = ('temperature_C' if unit == 'C' else 'activity_W_person' if unit == 'W/person' else
            'source_arithmetic' if unit and unit.startswith('W/') else 'fraction')
    av, ev = actual.get('values', []), expected.get('values', [])
    if len(av) != len(ev):
        differences.append(f'{path}/schedule/length')
        return
    digits = expected.get('source_precision_significant_digits')
    for i, (x, y) in enumerate(zip(av, ev)):
        if (isinstance(x,bool) or isinstance(y,bool) or
                (x != y if unit in {'person', 'count'} else not _close(x, y, tolerances[tkey], digits))):
            differences.append(f'{path}/schedule/values/{i}')
            break


def _scientific_equal(actual, expected, tolerances, path=(), derived=False, integral_tolerance='annual_energy_integral'):
    """Exact source/RNG/discrete receipts, named tolerances for emitted arithmetic.

    Only known generated receipt fields are continuous. Original source operands,
    evidence, selections, draws, event timing and state checkpoints stay exact.
    Administrative wrapper runtime versions never identify a scientific sample.
    """
    if isinstance(expected,dict):
        if not isinstance(actual,dict): return False
        derived = derived or expected.get('generation',{}).get('method')=='conserved_constituent_mixture'
        if derived and isinstance(expected.get('unit'),str) and expected['unit'].startswith('m3'):
            integral_tolerance='annual_volume_m3'
        ignored={'python_version'} if path and path[-1]=='rng' else set()
        ignored |= {'destination','cache_path','retrieval_timestamp'}
        ak,ek=set(actual)-ignored,set(expected)-ignored
        return ak==ek and all(_scientific_equal(actual[k],expected[k],tolerances,path+(k,),derived,integral_tolerance) for k in ek)
    if isinstance(expected,list):
        return isinstance(actual,list) and len(actual)==len(expected) and all(
            _scientific_equal(x,y,tolerances,path+(i,),derived,integral_tolerance) for i,(x,y) in enumerate(zip(actual,expected)))
    if type(actual) is bool or type(expected) is bool:
        return type(actual) is type(expected) and actual==expected
    tolerance=None
    if derived and 'evidence' not in path and len(path)>1:
        if path[-2]=='heat_fractions': tolerance='fraction'
        elif path[-2:] == ('annual_target','total'): tolerance=integral_tolerance
    if 'source_context' in path:
        # Generated daily points are [until_hour, value]; their shape/times remain
        # structurally intact, while arithmetic may vary within declared bounds.
        if ('transforms' in path and 'daily_profiles' in path) or 'special_profiles' in path:
            if path[-1]==0:
                tolerance='source_arithmetic'
            else:
                tolerance=('temperature_C' if any(s in path for s in ('heating_setpoint','cooling_setpoint')) else
                           'activity_W_person' if 'activity' in path else 'fraction')
        elif 'inference' in path and 'daily_profiles' in path:
            tolerance='source_arithmetic' if path[-1]==0 else 'fraction'
        elif ('inference' in path and 'daily_hoo' in path) or 'operations' in path:
            tolerance='source_arithmetic'
        elif 'event_segments' in path and path[-1]==2:
            tolerance='source_arithmetic'  # native minute power/flow; starts/lengths exact
        elif 'fixture_component_integrals' in path:
            tolerance='fraction'
    if tolerance and type(expected) in (int,float) and type(actual) in (int,float):
        return _close(actual,expected,tolerances[tolerance])
    return actual==expected


def _reference_projection(bundle):
    """Replace only generated references with their scientific ownership keys."""
    schedules={sid:(c['instance_key'],owner_identity(c),slot)
               for c in bundle.get('constituents',[]) for slot,sid in c.get('schedule_ids',{}).items()}
    bindings={i:_binding_key(b) for i,b in enumerate(bundle.get('bindings',[]))}
    def project(value):
        if isinstance(value,dict):
            return {k:bindings.get(v,v) if k=='binding_index' and type(v) is int else project(v)
                    for k,v in value.items()}
        if isinstance(value,list): return [project(v) for v in value]
        if isinstance(value,str): return schedules.get(value,value)
        return value
    return project({k:v for k,v in bundle.items() if k!='schedules'})


def compare_bundles(actual: dict, expected: dict, policy: dict) -> list[str]:
    """Return human-readable differences at source-significant reference paths."""
    differences = []
    tolerances = policy['tolerances']
    a_science,e_science=_reference_projection(actual),_reference_projection(expected)
    for field in ('schema_version', 'algorithm_version'):
        if actual.get(field) != expected.get(field):
            differences.append(field)
    for field in ('calendar', 'resource_set_id'):
        if actual.get('metadata', {}).get(field) != expected.get('metadata', {}).get(field):
            differences.append(f'metadata/{field}')
    if not _scientific_equal(a_science.get('generation'),e_science.get('generation'),tolerances):
        differences.append('generation/source_decisions')
    try:
        a_bindings, e_bindings = _map_bindings(actual), _map_bindings(expected)
        a_projected,e_projected=_map_bindings(a_science),_map_bindings(e_science)
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
                if not _scientific_equal(a_projected[key]['reference_target'].get(field),
                                        e_projected[key]['reference_target'].get(field),tolerances):
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
            key = (item.get('instance_key'), owner_identity(item))
            result[key] = {k: v for k, v in item.items() if k not in {'schedule_ids', 'binding_indices'}}
        return result
    if not _scientific_equal(scientific_constituents(a_science),scientific_constituents(e_science),tolerances):
        differences.append('constituents/source_parameters_or_decisions')
    def constituent_schedules(bundle):
        return {(item.get('instance_key'), owner_identity(item), slot): sid
                for item in bundle.get('constituents', [])
                for slot, sid in item.get('schedule_ids', {}).items()}
    a_refs, e_refs = constituent_schedules(actual), constituent_schedules(expected)
    if a_refs.keys() != e_refs.keys():
        differences.append('constituents/included_channels')
    bound_slots = {(b['instance_key'], owner_identity(b), b['slot']) for b in e_bindings.values()}
    for key in (a_refs.keys() & e_refs.keys()) - bound_slots:
        _compare_schedule(actual.get('schedules', {}).get(a_refs[key]),
                          expected.get('schedules', {}).get(e_refs[key]),
                          tolerances, f'constituents/{key}', differences)
    return differences
