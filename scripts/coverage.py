"""Audit named typology suites; type coverage does not imply simulation readiness."""
import argparse
import collections
from pathlib import Path

from scripts.common import ROOT, load_json, load_atlas, dump_json


def coverage_report(data, selection=None):
    selection = selection or load_json(ROOT/'sources/selection.json')
    program_counts = collections.Counter((r['template'], r['building_type']) for r in data['programs'])
    mapping_counts = collections.Counter((r['template'], r['building_type']) for r in data['mappings'])
    configurations = data.get('residential_archetypes', [])
    residential_counts = collections.Counter(r['building_type'] for r in configurations)
    suites, combinations, errors = {}, [], []
    if data['coverage_gaps']:
        errors.append('Excluded source spaces prevent complete source-input coverage')
    for suite, expected in selection['coverage_suites'].items():
        observed = set(residential_counts) if suite == 'residential' else {b for _, b in program_counts}
        suites[suite] = {'expected': expected, 'covered': sorted(set(expected) & observed),
                         'missing': sorted(set(expected)-observed)}
        if suites[suite]['missing']:
            errors.append(f'{suite}: missing types {suites[suite]["missing"]}')
    for template in selection['templates']:
        for model in template['models']:
            key = template['template'], model['building_type']
            p, m = program_counts[key], mapping_counts[key]
            combinations.append({'template': key[0], 'building_type': key[1], 'programs': p, 'mappings': m})
            if not p or not m:
                errors.append(f'No mapped program coverage for {key}')
    return {'schema_version': data['schema_version'], 'coverage_basis': 'named_source_input_typologies',
            'typology_coverage_complete': not errors, 'simulation_ready': False,
            'suites': suites, 'commercial_template_type_combinations': combinations,
            'residential_configuration_counts': dict(sorted(residential_counts.items())),
            'residential_configurations': len(configurations),
            'residential_unresolved_option_instances': sum(len(r['unresolved_options']) for r in configurations),
            'residential_base_thermostat_overlaps': sum(r['thermostat_base_overlap'] for r in configurations),
            'excluded_source_spaces': data['coverage_gaps'], 'errors': errors,
            'limitations': ['Standards-derived inputs; direct DOE/PNNL IDF equivalence unverified',
                            'Five selected commercial templates; not every published code edition',
                            'Residential fixture configurations retain unmatched options and unexecuted defaults',
                            'Named suite/class coverage is not all possible building uses or stock combinations']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('path', nargs='?', type=Path, default=ROOT/'data/processed')
    p.add_argument('--report', type=Path, default=ROOT/'docs/validation/coverage.json')
    args = p.parse_args()
    report = coverage_report(load_atlas(args.path))
    dump_json(args.report, report)
    if report['errors']:
        raise SystemExit('\n'.join(report['errors']))
    print('Coverage passed: DOE 16/16, PNNL 16/16, residential 7/7; '
          f'{report["residential_configurations"]} configurations; simulation readiness unresolved')


if __name__ == '__main__':
    main()
