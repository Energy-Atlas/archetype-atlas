"""Small design probe, not a catalogue exporter or EnergyPlus validation suite.

Run from repository root with .venv/Scripts/python.exe -m
scripts.experiments.construction_equivalence_probe --output <json path>.
Only the Python standard library is required. Frequency-domain quadrupoles solve
linear one-dimensional diffusion exactly within each homogeneous source layer.
"""

import argparse
import cmath
import hashlib
import json
import math
import platform
from pathlib import Path

from scripts.construction_distribution import load_current_release


PERIODS_H = (6, 24, 168)
FILMS = (0.04, 0.13)  # Atlas probe reference, not a simulation film prescription.
IDENTITY = (1, 0, 0, 1)


def multiply(left, right):
    a, b, c, d = left
    e, f, g, h = right
    return a * e + b * g, a * f + b * h, c * e + d * g, c * f + d * h


def matrix(resistance, capacity, omega):
    if capacity == 0:
        return 1, resistance, 0, 1
    z = cmath.sqrt(1j * omega * resistance * capacity)
    s = cmath.sinh(z) / z
    return cmath.cosh(z), resistance * s, 1j * omega * capacity * s, cmath.cosh(z)


def response(layers, period_h):
    omega = 2 * math.pi / (period_h * 3600)
    m = multiply(IDENTITY, matrix(FILMS[0], 0, omega))
    for layer in layers:
        m = multiply(m, matrix(layer['R'], layer['C'], omega))
    a, b, _, d = multiply(m, matrix(FILMS[1], 0, omega))
    # Inward flux at each air boundary; order Y00, Y01, Y10, Y11.
    return d / b, -1 / b, -1 / b, a / b


def properties(release, assembly_id):
    result = []
    for layer in release['assemblies'][assembly_id]['layers']:
        material = release['materials'][layer['material_id']]
        p = material['properties']
        if material['model'] == 'StandardOpaqueMaterial':
            r = p['thickness_m'] / p['conductivity_W_m_K']
            c = p['thickness_m'] * p['density_kg_m3'] * p['specific_heat_J_kg_K']
        elif material['model'] in ('MasslessOpaqueMaterial', 'AirGap'):
            r, c = p['resistance_m2_K_W'], 0
        else:
            raise ValueError(f"Unsupported probe material {material['model']}")
        assert r > 0 and c >= 0
        result.append({'R': r, 'C': c, 'material_id': layer['material_id']})
    return result


def equivalent(r, c, x, beta):
    # Fixed per-case numerical gauge; not a claim about actual material identity.
    cp = 1000.0
    rho = min(1000.0, c / (cp * 0.04))
    layers = []
    for fraction in (x, 1 - x):
        capacity, resistance = fraction * c, fraction * beta * r
        thickness = capacity / (rho * cp)
        conductivity = thickness / resistance
        if thickness < 0.003 or not 0 < conductivity <= 5:
            return None
        if conductivity / (rho * cp) > 1e-5:
            return None
        layers.append({'R': resistance, 'C': capacity,
                       'thickness_m': thickness, 'conductivity_W_m_K': conductivity,
                       'density_kg_m3': rho, 'specific_heat_J_kg_K': cp})
    return [layers[0], {'R': (1 - beta) * r, 'C': 0}, layers[1]]


def fit(contributors):
    c = sum(w * sum(l['C'] for l in ls) for w, ls in contributors)
    u = sum(w / (sum(l['R'] for l in ls) + sum(FILMS)) for w, ls in contributors)
    r = 1 / u - sum(FILMS)
    target = [tuple(sum(w * response(ls, h)[j] for w, ls in contributors)
                    for j in range(4)) for h in PERIODS_H]

    def score(layers):
        return sum((abs(y - t) / max(abs(t), u)) ** 2
                   for h, expected in zip(PERIODS_H, target)
                   for y, t in zip(response(layers, h), expected)) / 12

    candidates = []
    for ix in range(8, 93, 2):
        for beta in (0.005, 0.01, 0.02, 0.04, 0.08, 0.16, 0.32, 0.64, 0.8):
            x = ix / 100
            layers = equivalent(r, c, x, beta)
            if layers is not None:
                candidates.append((score(layers), x, beta))
    assert candidates, 'No physically admissible three-slot candidate'
    _, x0, b0 = min(candidates)
    for dx in range(-5, 6):
        for db in range(-5, 6):
            x, beta = x0 + dx * 0.002, b0 * (1 + db * 0.04)
            if not (0 < x < 1 and 0 < beta < 1):
                continue
            layers = equivalent(r, c, x, beta)
            if layers is not None:
                candidates.append((score(layers), x, beta))
    loss, x, beta = min(candidates)  # Lexicographic x, beta break exact ties.
    layers = equivalent(r, c, x, beta)
    assert math.isclose(sum(l['R'] for l in layers), r, rel_tol=1e-12)
    assert math.isclose(sum(l['C'] for l in layers), c, rel_tol=1e-12)
    metrics = []
    for h in (*PERIODS_H, 12, 72):
        expected = tuple(sum(w * response(ls, h)[j] for w, ls in contributors)
                         for j in range(4))
        actual = response(layers, h)
        cross, cross_fit = -expected[1], -actual[1]
        phase = abs(cmath.phase(cross_fit / cross)) * h / (2 * math.pi)
        metrics.append({'period_h': h, 'used_for_fitting': h in PERIODS_H,
                        'normalized_response_rms': math.sqrt(sum(
                            (abs(y - t) / max(abs(t), u)) ** 2
                            for y, t in zip(actual, expected)) / 4),
                        'transmission_amplitude_error_percent': 100 * (abs(cross_fit) / abs(cross) - 1),
                        'transmission_phase_error_h': phase,
                        'transmission_absolute_error_over_U': abs(cross_fit - cross) / u,
                        'target_transmission_over_U': abs(cross) / u})
    return {'U_with_reference_films_W_m2_K': u, 'layer_R_m2_K_W': r,
            'capacity_J_m2_K': c, 'exterior_capacity_fraction': x,
            'mass_layer_resistance_fraction': beta,
            'normalized_response_rms': math.sqrt(loss),
            'equivalent_layers': layers, 'metrics': metrics}


def checks():
    # Independent limiting solutions: pure resistor; uniform slab subdivision;
    # reversal swaps self-admittances, preserving cross-boundary transmission.
    resistor = response([{'R': 2, 'C': 0}], 24)
    u = 1 / (2 + sum(FILMS))
    assert all(abs(a - b) < 1e-12 for a, b in zip(resistor, (u, -u, -u, u)))
    m = matrix(2, 80000, 2 * math.pi / 86400)
    half = matrix(1, 40000, 2 * math.pi / 86400)
    assert all(abs(a - b) < 1e-10 for a, b in zip(m, multiply(half, half)))
    # Bare layer matrices have unit determinant (reciprocity).
    assert abs(m[0] * m[3] - m[1] * m[2] - 1) < 1e-10
    a, b = matrix(0.7, 10000, 2 * math.pi / 86400), m
    forward, reverse = multiply(a, b), multiply(b, a)
    assert all(abs(v - w) < 1e-10 for v, w in zip(
        forward, (reverse[3], reverse[1], reverse[2], reverse[0])))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    checks()
    release = load_current_release(Path('data/construction-releases/v2.2.0'))
    geometry_path = Path('data/construction-inputs/geometry-v1.json')
    geometry = json.loads(geometry_path.read_text(encoding='utf-8'))
    cases = []
    for ref, role in [('90.1-2019/MediumOffice', 'ExteriorWall'),
                      ('90.1-2019/Warehouse', 'ExteriorWall'),
                      ('90.1-2019/MediumOffice', 'ExteriorRoof')]:
        matches = [c for c in release['contexts'].values()
                   if c['reference_id'] == ref and c['climate_zone'] == '3B'
                   and release['construction_sets'][c['construction_set_id']]['source']['building_type']
                   == ref.split('/')[1]]
        configurations = {c['configuration_id'] for c in matches}
        assert len(configurations) == 1
        component = release['component_configurations'][configurations.pop()]['components'][role]
        if 'Warehouse' in ref:
            spaces = next(g['spaces'] for g in geometry['commercial'] if g['id'] == ref)
            area = {}
            for space in spaces:
                key = space['standards_space_type']
                area[key] = area.get(key, 0) + space['outdoor_wall_area_m2'] * space['multiplier']
            assignments = [a for a in component['assignments'] if a['when']['scope'] == 'space_type']
            assert set(area) == {a['when']['space_type'] for a in assignments}
            entries = [(a['assembly_id'], area[a['when']['space_type']] / sum(area.values()))
                       for a in assignments]
            basis = 'source archetype gross wall area, diagnostic only (net openings not recovered)'
        else:
            assert len(component['assignments']) == 1
            entries = [(component['assignments'][0]['assembly_id'], 1.0)]
            basis = 'single source assembly'
        assert math.isclose(sum(w for _, w in entries), 1)
        contributors = [(w, properties(release, aid)) for aid, w in entries]
        cases.append({'reference_id': ref, 'climate_zone': '3B', 'semantic': role,
                      'weight_basis': basis,
                      'sources': [{'assembly_id': aid, 'weight': w, 'layers': ls}
                                  for (aid, w), (_, ls) in zip(entries, contributors)],
                      **fit(contributors)})
    paths = [geometry_path, Path(__file__), Path('scripts/construction_distribution.py'),
             *[Path(f'data/construction-releases/{v}/manifest.json')
                                            for v in ('v2.0.0', 'v2.1.0', 'v2.2.0')]]
    report = {'kind': 'construction_equivalence_design_probe', 'schema_version': '1.0.0',
              'inspection_date': '2026-10-15', 'python_version': platform.python_version(),
              'scope': 'linear opaque conduction only; not EnergyPlus or annual energy validation',
              'input_sha256': {p.as_posix() if not p.is_absolute() else 'scripts/experiments/' + p.name:
                               hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
              'reference_film_R_m2_K_W': list(FILMS), 'fitting_periods_h': list(PERIODS_H),
              'cases': cases}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes((json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + '\n').encode('utf-8'))
    for c in cases:
        daily = c['metrics'][1]
        print(c['reference_id'], c['semantic'],
              f"RMS={c['normalized_response_rms']:.4f}",
              f"daily amplitude={daily['transmission_amplitude_error_percent']:.2f}%",
              f"daily phase={daily['transmission_phase_error_h']:.3f}h")


if __name__ == '__main__':
    main()
