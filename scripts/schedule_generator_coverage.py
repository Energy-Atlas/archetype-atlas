"""Inspect exact M1 case/channel support and the remaining catalogue."""
import argparse
import hashlib
import json
from pathlib import Path

from atlas_schedules.canonical import canonical
from atlas_schedules.resources import ResourceSet

ROOT = Path(__file__).resolve().parents[1]


def build_coverage(resources: ResourceSet, scope: dict | None = None) -> dict:
    scope = scope if scope is not None else resources.get('reference', 'm1-scope')
    index = resources.get('reference', 'catalogue-index')
    programmed = {row['id']: row for row in index['programs']}
    cases = []
    for declaration in scope['cases']:
        case_id, program_id = declaration['case_id'], declaration['program_id']
        record = resources.get('program', program_id)
        recipe = record['recipe']
        resolved = recipe['resolved']
        absent = not resolved['slots']
        expected = 'accepted_inactive' if absent else 'compiled'
        errors = []
        if record['case'] != declaration:
            errors.append('case declaration differs from compiled source')
        if programmed.get(program_id, {}).get('status') != expected:
            errors.append('catalogue status differs from recipe')
        if declaration.get('source_gate_status') != 'passed':
            errors.append('source gate did not pass')
        if absent and not resolved['evidence'][0].get('accepted_absence'):
            errors.append('zero-slot recipe lacks source-backed absence')
        demand_slots = {item['slot'] for item in resolved['demands']}
        control_slots = {item['slot'] for item in resolved['controls']}
        slots = [item['slot'] for item in resolved['slots']]
        if len(slots) != len(set(slots)):
            errors.append('duplicate slot')
        channels = []
        for item in resolved['slots']:
            slot = item['slot']
            source = recipe['reference_sources'].get(slot) or recipe['companion_rules'].get(slot)
            owner = 'load' if slot in demand_slots else 'control' if slot in control_slots else None
            status = ('source_fixed' if slot in recipe['companion_rules'] else 'generated') if item.get('source_schedule_id') and owner else 'requires_binding'
            channels.append({'slot': slot, 'kind': owner, 'status': status,
                             'source_schedule_id': item.get('source_schedule_id'),
                             'source_evidence': (source.get('evidence', source.get('source', {}).get('id'))
                                                 if source else item.get('source_schedule_id'))})
            if status == 'requires_binding':
                errors.append('unbound included channel: ' + slot)
        cases.append({'case_id': case_id, 'program_id': program_id,
                      'configuration_id': declaration['configuration_id'],
                      'template': declaration['template'], 'weather': declaration['weather'],
                      'evidence_view': declaration['evidence_view'], 'status': expected if not errors else 'failed_validation',
                      'expected_slots': slots, 'channels': channels,
                      'accepted_absence': resolved['evidence'][0].get('accepted_absence', False),
                      'absence_evidence': resolved['evidence'][0] if absent else None,
                      'errors': errors})
    declared = {case['program_id'] for case in scope['cases']}
    outside_programs = []
    for item in index['programs']:
        if item['id'] in declared:
            continue
        if item['status'] in {'compiled', 'accepted_inactive'}:
            outside_programs.append(dict(item, catalogue_status=item['status'], status='unsupported_binding',
                                         reason='outside_declared_milestone_scope'))
        else:
            outside_programs.append(item)
    outside_compositions = index['compositions']
    report = {'schema_version': '1.0.0', 'resource_set_id': resources.resource_set_id,
              'scope': {'milestone_id': scope['milestone_id'], 'scope_version': scope['scope_version'],
                        'scope_sha256': hashlib.sha256(canonical(scope)).hexdigest(),
                        'case_count': len(scope['cases']), 'case_ids': [c['case_id'] for c in scope['cases']]},
              'cases': cases,
              'outside_scope': {'program_count': len(outside_programs), 'composition_count': len(outside_compositions),
                                'programs': outside_programs, 'compositions': outside_compositions},
              'catalogue_program_count': len(index['programs']),
              'catalogue_composition_count': len(index['compositions'])}
    return report


def coverage_errors(report: dict) -> list[str]:
    errors = []
    cases = report['cases']
    if [c['case_id'] for c in cases] != report['scope']['case_ids'] or len(cases) != report['scope']['case_count']:
        errors.append('Scope case inventory differs from declared case list')
    if len({c['case_id'] for c in cases}) != len(cases):
        errors.append('Duplicate case')
    for case in cases:
        if case['status'] not in {'compiled', 'accepted_inactive'} or case['errors']:
            errors.append(case['case_id'] + ': incomplete case')
        if [c['slot'] for c in case['channels']] != case['expected_slots']:
            errors.append(case['case_id'] + ': channel inventory differs from resolved slots')
        if case['status'] == 'accepted_inactive' and (case['channels'] or not case['accepted_absence']):
            errors.append(case['case_id'] + ': invalid inactive case')
        for channel in case['channels']:
            if channel['status'] not in {'generated', 'source_fixed'} or channel['kind'] not in {'load', 'control'}:
                errors.append(case['case_id'] + '/' + channel['slot'] + ': unresolved channel')
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--scope', default='m1')
    parser.add_argument('--report', type=Path, default=ROOT / 'docs/validation/schedule-generator-coverage.json')
    args = parser.parse_args(argv)
    if args.scope != 'm1':
        scope = json.loads(Path(args.scope).read_text(encoding='utf-8'))
    else:
        scope = None
    manifest = json.loads((ROOT / 'atlas_schedules/data/manifest.json').read_text(encoding='utf-8'))
    resources = ResourceSet.load(manifest['resource_set_id'])
    if args.scope == 'm1' and resources.get('reference', 'm1-scope') != json.loads((ROOT / 'sources/schedule-generator-m1-scope.json').read_text(encoding='utf-8')):
        raise SystemExit('Authoritative M1 scope differs from packaged resources')
    report = build_coverage(resources, scope)
    errors = coverage_errors(report)
    if args.check:
        frozen = json.loads(args.report.read_text(encoding='utf-8'))
        if frozen != report:
            errors.append('Frozen coverage report differs from current resources')
    else:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_bytes(canonical(report))
    if errors:
        raise SystemExit('\n'.join(errors))
    print(f"{report['scope']['milestone_id']}: {len(report['cases'])} complete cases; "
          f"{report['outside_scope']['program_count']} outside-scope programs and "
          f"{report['outside_scope']['composition_count']} compositions")


if __name__ == '__main__':
    main()
