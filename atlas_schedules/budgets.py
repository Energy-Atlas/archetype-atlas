"""Conserve source annual load integrals while fitting emitted fractions."""
import copy
import math

from .errors import GeneratorError


_UNITS = {
    'W': ('Wh', 1), 'W/m2': ('Wh/m2', 1), 'W/dwelling': ('Wh/dwelling', 1),
    'W/person': ('Wh/person', 1),
    'm3/s': ('m3', 3600), 'm3/s/dwelling': ('m3/dwelling', 3600),
}


def _number(value, path, *, nonnegative=True):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise GeneratorError('invalid_magnitude', path, 'Expected a finite number')
    if nonnegative and value < 0:
        raise GeneratorError('invalid_magnitude', path, 'Expected a nonnegative number')
    return value


def _integral(values, path):
    if not isinstance(values, list) or not values:
        raise GeneratorError('invalid_schedule', path, 'Expected nonempty hourly fractions')
    for i, value in enumerate(values):
        _number(value, f'{path}/{i}')
        if value > 1:
            raise GeneratorError('invalid_schedule', f'{path}/{i}', 'Fraction exceeds one')
    return math.fsum(values)


def reference_budget(demand: dict, reference_values: list[float]) -> dict:
    """Build an annual target from direct evidence or original magnitude and reference shape."""
    if not isinstance(demand, dict):
        raise GeneratorError('invalid_demand', '/demand', 'Expected demand object')
    unit = demand.get('unit')
    if unit not in _UNITS:
        raise GeneratorError('invalid_unit', '/demand/unit', 'Unsupported load magnitude unit')
    annual_unit, seconds = _UNITS[unit]
    for field in ('quantity', 'basis', 'fuel', 'host', 'evidence'):
        if field not in demand or demand[field] is None:
            raise GeneratorError('invalid_demand', f'/demand/{field}', 'Required source semantic is missing')
    direct = demand.get('annual_target')
    if direct is not None:
        if not isinstance(direct, dict) or direct.get('unit') != annual_unit or not direct.get('evidence'):
            raise GeneratorError('invalid_demand', '/demand/annual_target', 'Direct target needs matching unit and evidence')
        total = _number(direct.get('total'), '/demand/annual_target/total')
        method, evidence = 'direct_annual', copy.deepcopy(direct['evidence'])
    else:
        if demand.get('value') is None:
            raise GeneratorError('unresolved_annual_target', '/demand/value', 'No direct annual target or original magnitude')
        magnitude = _number(demand['value'], '/demand/value')
        integral = _integral(reference_values, '/reference_values')
        total = magnitude * integral * seconds
        if not math.isfinite(total):
            raise GeneratorError('invalid_magnitude', '/demand/value', 'Annual integral overflow')
        method, evidence = 'reference_schedule', copy.deepcopy(demand['evidence'])
    target = {'quantity': demand['quantity'], 'total': total, 'unit': annual_unit,
              'basis': demand['basis'], 'method': method, 'magnitude_unit': unit,
              'fuel': demand['fuel'], 'host': demand['host'], 'evidence': evidence,
              'original_magnitude': {'value': demand.get('value'), 'unit': unit,
                                     'evidence': copy.deepcopy(demand['evidence'])}}
    if 'installed_rating' in demand:
        target['installed_rating'] = copy.deepcopy(demand['installed_rating'])
    if 'capacity_constraint' in demand:
        target['capacity_constraint'] = copy.deepcopy(demand['capacity_constraint'])
    return target


def bind_budget(target: dict, values: list[float]) -> dict:
    """Fit a nonnegative effective magnitude to the actual emitted fractional integral."""
    if not isinstance(target, dict):
        raise GeneratorError('invalid_target', '/target', 'Expected target object')
    for field in ('quantity', 'basis', 'method', 'magnitude_unit', 'unit', 'fuel', 'host', 'evidence'):
        if field not in target:
            raise GeneratorError('invalid_target', f'/target/{field}', 'Missing target field')
    if target['magnitude_unit'] not in _UNITS or _UNITS[target['magnitude_unit']][0] != target['unit']:
        raise GeneratorError('invalid_unit', '/target/unit', 'Incompatible annual and magnitude units')
    total = target.get('total')
    if total is None:
        raise GeneratorError('unresolved_annual_target', '/target/total', 'Annual target is unknown')
    _number(total, '/target/total')
    integral = _integral(values, '/values')
    if integral == 0 and total > 0:
        raise GeneratorError('zero_generated_integral', '/values', 'Positive target cannot bind zero schedule')
    seconds = _UNITS[target['magnitude_unit']][1]
    amplitude = total / (integral * seconds) if integral else 0
    if not math.isfinite(amplitude):
        raise GeneratorError('invalid_magnitude', '/target/total', 'Effective magnitude overflow')
    constraint = target.get('capacity_constraint')
    if constraint is not None:
        if not isinstance(constraint, dict) or constraint.get('unit') != target['magnitude_unit']:
            raise GeneratorError('invalid_target', '/target/capacity_constraint', 'Incompatible capacity constraint')
        maximum = _number(constraint.get('maximum'), '/target/capacity_constraint/maximum')
        if amplitude > maximum and not math.isclose(amplitude, maximum, rel_tol=1e-12):
            raise GeneratorError('infeasible_intensity', '/target/capacity_constraint',
                                 'Conserved target exceeds requested physical capacity')
    return {'reference_target': copy.deepcopy(target),
            'effective_magnitude': {'value': amplitude, 'unit': target['magnitude_unit'],
                                    'basis': target['basis']},
            'scaling_receipt': {'generated_integral': integral, 'seconds_per_sample': 3600,
                                'achieved_total': amplitude * integral * seconds,
                                'unit': target['unit'],
                                'capacity_constraint': copy.deepcopy(constraint)}}
