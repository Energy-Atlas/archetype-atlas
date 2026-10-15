"""Deterministic two-parameter opaque construction approximation, policy 1.0.0.

Linear conduction only. The fixed representation can be inadequate; retain
measured errors rather than adding layers. R is m2 K/W and C is J/(m2 K).
"""
import cmath
import copy
import math
from functools import lru_cache


PERIODS = (6, 24, 168)
CHECK_PERIODS = (12, 72)
POLICY = 'two_mass_one_resistance_1.0.0'


def _number(value, minimum=0, strict=False):
    if (not isinstance(value, (int, float)) or isinstance(value, bool)
            or not math.isfinite(value) or value < minimum or (strict and value == minimum)):
        raise ValueError('Unknown, nonfinite or invalid thermal operand')
    return float(value)


def _multiply(m, n):
    a, b, c, d = m
    e, f, g, h = n
    return a*e+b*g, a*f+b*h, c*e+d*g, c*f+d*h


def _matrix(r, c, omega):
    if c == 0:
        return 1, r, 0, 1
    z = cmath.sqrt(1j*omega*r*c)
    s = cmath.sinh(z)/z
    return cmath.cosh(z), r*s, 1j*omega*c*s, cmath.cosh(z)


def response(layers, period_h, films=(.04, .13)):
    """Return Y00,Y01,Y10,Y11: air temperatures -> inward heat fluxes."""
    omega = 2*math.pi/(_number(period_h, strict=True)*3600)
    re, ri = (_number(x) for x in films)
    m = (1, re, 0, 1)
    for layer in layers:
        m = _multiply(m, _matrix(_number(layer.get('R'), strict=True),
                                 _number(layer.get('C')), omega))
    a, b, _, d = _multiply(m, (1, ri, 0, 1))
    return d/b, -1/b, -1/b, a/b


def _candidate(r, c, x, beta):
    cp = 1000.
    rho = min(1000., c/(cp*.04))
    sides = []
    for fraction in (x, 1-x):
        capacity, resistance = fraction*c, fraction*beta*r
        thickness = capacity/(rho*cp)
        conductivity = thickness/resistance
        if thickness < .003 or not 0 < conductivity <= 5 or conductivity/(rho*cp) > 1e-5:
            return None
        sides.append({'model': 'Material', 'R': resistance, 'C': capacity,
                      'thickness_m': thickness, 'conductivity_W_m_K': conductivity,
                      'density_kg_m3': rho, 'specific_heat_J_kg_K': cp})
    return [sides[0], {'model': 'Material:NoMass', 'R': (1-beta)*r, 'C': 0.}, sides[1]]


def _admittance(layers, h, films, one_sided):
    y = response(layers, h, films)
    return (y[0]-y[1]*y[2]/y[3],) if one_sided else y


@lru_cache(maxsize=8192)
def _reduce(key, films, one_sided):
    sources = [(w, [{'R': r, 'C': c} for r, c in ls]) for w, ls in key]
    c = sum(w*sum(l['C'] for l in ls) for w, ls in sources)
    u = sum(w/(sum(l['R'] for l in ls)+sum(films)) for w, ls in sources)
    r = 1/u-sum(films)
    targets = {'resistance_m2_K_W': r, 'capacity_J_m2_K': c, 'u_reference_W_m2_K': u}
    def target(h):
        responses = [(w, _admittance(ls, h, films, one_sided)) for w, ls in sources]
        return tuple(sum(w*y[j] for w, y in responses) for j in range(1 if one_sided else 4))
    expected = {h: target(h) for h in (*PERIODS, *CHECK_PERIODS)}
    floor = c/86400 if one_sided else u
    def error(ls, h):
        return sum((abs(a-b)/max(abs(b), floor))**2
                   for a, b in zip(_admittance(ls, h, films, one_sided), expected[h]))/len(expected[h])
    if c == 0:
        layers = [{'R': r, 'C': 0., 'model': 'Material:NoMass'}]
        x = beta = None
        loss = 0.
    else:
        candidates = []
        def add(x, beta):
            if not (0 < x < 1 and 0 < beta < 1):
                return
            layers = _candidate(r, c, x, beta)
            if layers:
                candidates.append((sum(error(layers, h) for h in PERIODS)/3, x, beta))
        for ix in range(8, 93, 2):
            for beta in (.005, .01, .02, .04, .08, .16, .32, .64, .8):
                add(ix/100, beta)
        if not candidates:
            return {'status': 'blocked', 'reason': 'no_valid_three_slot_candidate', 'targets': targets,
                    'layers': [], 'quality': 'unresolved', 'fit': {'policy': POLICY}}
        _, x0, b0 = min(candidates)
        for dx in range(-5, 6):
            for db in range(-5, 6):
                add(x0+dx*.002, b0*(1+db*.04))
        loss, x, beta = min(candidates)
        layers = _candidate(r, c, x, beta)
    metrics = []
    for h in (*PERIODS, *CHECK_PERIODS):
        metric = {'period_h': h, 'used_for_fitting': h in PERIODS,
                  'normalized_response_rms': 0. if c == 0 else math.sqrt(error(layers, h))}
        if not one_sided:
            cross = -expected[h][1]
            actual = -response(layers, h, films)[1]
            significant = abs(cross) >= .1*u
            metric.update({'transmission_absolute_error_over_U': abs(actual-cross)/u,
                           'transmission_amplitude_error_percent':
                           100*(abs(actual)/abs(cross)-1) if significant else None,
                           'transmission_phase_error_h':
                           abs(cmath.phase(actual/cross))*h/(2*math.pi) if significant else None})
        metrics.append(metric)
    quality = 'approximation_review' if any(m['normalized_response_rms'] > .1 for m in metrics) else 'within_initial_screen'
    daily = metrics[1]
    if (not one_sided and daily['transmission_amplitude_error_percent'] is not None
            and (abs(daily['transmission_amplitude_error_percent']) > 10
                 or daily['transmission_phase_error_h'] > 1)):
        quality = 'approximation_review'
    return {'status': 'ready', 'layers': layers, 'targets': targets, 'quality': quality,
            'fit': {'policy': POLICY, 'acceptance_policy': 'practical_screen_1.0.0',
                    'films_m2_K_W': list(films), 'one_sided': one_sided,
                    'exterior_capacity_fraction': x, 'mass_layer_resistance_fraction': beta,
                    'normalized_response_rms': math.sqrt(loss), 'metrics': metrics,
                    'limitation': 'Fixed three-slot approximation may inadequately reproduce source responses; errors are retained.'}}


def reduce_opaque(contributors, films=(.04, .13), one_sided=False):
    """Conserve common-film U and capacity; return errors without extra layers."""
    if not contributors:
        raise ValueError('Missing contributors')
    key = []
    for item in contributors:
        w = _number(item.get('weight'))
        if not item.get('layers'):
            raise ValueError('Missing source layers')
        ls = tuple((_number(l.get('R'), strict=True), _number(l.get('C'))) for l in item['layers'])
        key.append((w, ls))
    if not math.isclose(sum(w for w, _ in key), 1., rel_tol=0, abs_tol=1e-8):
        raise ValueError('Contributors must have complete normalized weights')
    f = tuple(_number(v) for v in films)
    if len(f) != 2:
        raise ValueError('Exactly two boundary films required')
    if one_sided and all(c == 0 for _, ls in key for _, c in ls):
        # Zero-capacity one-sided mass stores no energy; never invent a fit.
        return {'status': 'not_applicable', 'layers': [], 'quality': 'source_proven_zero_mass',
                'targets': {'capacity_J_m2_K': 0.}, 'fit': {'policy': POLICY}}
    try:
        return copy.deepcopy(_reduce(tuple(key), f, one_sided))
    except (OverflowError, ZeroDivisionError) as exc:
        raise ValueError('Source response is outside this simple reduction method') from exc
