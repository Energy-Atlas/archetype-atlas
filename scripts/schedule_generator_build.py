"""Build the exact M1 resource set from locked evidence and frozen references."""
import argparse
import hashlib
from pathlib import Path
import re
import tempfile

from atlas_schedules.canonical import canonical
from atlas_schedules.errors import GeneratorError
from atlas_schedules.resources import ResourceSet, strict_json, write_resources
from scripts.common import ROOT
from scripts.schedule_generator_sources import extract_sources
from scripts.schedule_generator_reference import load_reference_vectors


def _read(path):
    return strict_json(Path(path).read_bytes(), str(path))


def validate_scope(scope: dict) -> None:
    lock = _read(ROOT/'sources/schedule-generator-lock.json')
    if scope.get('calendar') != lock['calendar'] or scope.get('cases') != lock['scope_cases']:
        raise GeneratorError('scope_mismatch', '/cases', 'M1 case/configuration/weather/template bindings differ from locked scope')
    for case in scope['cases']:
        for receipt in (case['program_definition'], case['configuration']):
            if 'file' in receipt:
                content = (ROOT/receipt['file']).read_bytes()
                if hashlib.sha256(content).hexdigest() != receipt['sha256']:
                    raise GeneratorError('source_integrity', receipt['file'], 'Frozen reference changed')
        program = _read(ROOT/case['program_definition']['file'])[int(case['program_definition']['json_pointer'][1:])]
        if any(program.get(field) != case.get(field) for field in ('id', 'template', 'evidence_view') if field != 'id') or program['id'] != case['program_id']:
            raise GeneratorError('scope_mismatch', case['case_id'], 'Case does not match frozen program identity')


def validate_sampling_audit(audit: dict) -> None:
    lock = _read(ROOT/'sources/schedule-generator-lock.json')
    actual = hashlib.sha256(canonical(audit)).hexdigest()
    expected = hashlib.sha256(canonical(_read(ROOT/'data/schedule-generator/comstock-sampling-audit.json'))).hexdigest()
    disk = hashlib.sha256((ROOT/'data/schedule-generator/comstock-sampling-audit.json').read_bytes()).hexdigest()
    parameters = audit.get('parameters', [])
    if (actual != expected or disk != lock['sampling_audit_sha256'] or audit.get('gate_status') != 'passed'
            or audit.get('conditioning_inputs') != {'building_type': 'medium_office'}
            or audit.get('population_realization_equivalent') is not False
            or not audit.get('weather_independent') or len(parameters) != 10
            or any(p.get('decision') != 'resolved' for p in parameters)):
        raise GeneratorError('sampling_gate', '/commercial', 'Commercial source/conditioning gate is unresolved or differs from approved audit')


def _portable(value):
    """Remove upstream execution-cache paths; source-relative locators stay intact."""
    if isinstance(value, dict):
        return {k: _portable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_portable(v) for v in value]
    if isinstance(value, str) and (re.match(r'^[A-Za-z]:[\\/]', value) or value.startswith(('/kfs', '/tmp/', '/home/'))):
        return None
    return value


def _receipt(file, pointer, note):
    content = (ROOT/file).read_bytes()
    return {'source_path': file, 'source_locator': file+'#'+pointer,
            'source_revision': 'frozen '+file.split('/')[2], 'source_sha256': hashlib.sha256(content).hexdigest(),
            'original_unit': 'versioned JSON with per-field units/evidence', 'original_value': 'value retained in record',
            'transformation': note, 'extraction_date': '2026-10-14',
            'interpretation_note': 'Immutable source/reviewed views remain separate; null remains unknown'}


def build_resources(destination: Path, scope: str) -> dict:
    if scope != 'pilot':
        raise GeneratorError('unsupported_scope', '/scope', 'Only exact M1 pilot is source-gated')
    lock = _read(ROOT/'sources/schedule-generator-lock.json')
    manifest_scope = _read(ROOT/'sources/schedule-generator-m1-scope.json')
    validate_scope(manifest_scope)
    audit = _read(ROOT/'data/schedule-generator/comstock-sampling-audit.json')
    validate_sampling_audit(audit)
    for file, receipt in lock['frozen_files'].items():
        content = (ROOT/file).read_bytes()
        if len(content) != receipt['size_bytes'] or hashlib.sha256(content).hexdigest() != receipt['sha256']:
            raise GeneratorError('source_integrity', file, 'Frozen reference checksum mismatch')
    with tempfile.TemporaryDirectory() as temporary:
        source_manifest = extract_sources(lock, ROOT/'data/raw', Path(temporary)/'resources')
        sources = ResourceSet(Path(temporary)/'resources', source_manifest['resource_set_id'])
        records = {(e['kind'], e['key']): sources.get(e['kind'], e['key']) for e in source_manifest['resources']}
    records['commercial', 'sampling-audit'] = audit
    records['reference', 'm1-scope'] = manifest_scope
    records['reference', 'comparison-policy'] = _read(ROOT/'sources/schedule-generator-policy.json')
    records['reference', 'source-random-rule-vectors'] = load_reference_vectors()
    records['reference', 'notice-ruby-random'] = {'text': (ROOT/'sources/licenses/ruby-random.txt').read_text(encoding='utf-8'),
                                                    'source_path': 'sources/licenses/ruby-random.txt'}
    programs_file = 'data/definition-releases/v0.1.1/programs.json'
    programs = _read(ROOT/programs_file)
    schedule_ids, source_program_ids = set(), set()
    for case in manifest_scope['cases']:
        program = programs[int(case['program_definition']['json_pointer'][1:])]
        source_program_ids.add(program['source_id'])
        for load in program['loads']:
            if load.get('schedule_id'):
                schedule_ids.add(load['schedule_id'])
        for parameter in program['parameters'].values():
            if parameter.get('unit') == 'schedule reference' and parameter.get('value'):
                schedule_ids.add(parameter['value'])
        record = {'definition': program, 'case': case,
                  'provenance': _receipt(programs_file, case['program_definition']['json_pointer'], 'Exact frozen program; no merged views')}
        if 'file' in case['configuration']:
            file = case['configuration']['file']
            profile = _read(ROOT/file)
            record['configuration'] = _portable(profile['metadata'])
            record['configuration_provenance'] = _receipt(file, '/metadata', 'Exact recovered inputs; local execution-cache paths omitted as null; reference seed retained as evidence')
            records['reference', case['configuration_id']+'-profile'] = {
                'metadata': _portable(profile['metadata']), 'series': profile['series'],
                'provenance': _receipt(file, '/', 'Frozen numerical reference; local execution-cache paths omitted')}
        records['program', case['program_id']] = record
    file = 'data/definition-releases/v0.1.1/schedules.json'
    for index, schedule in enumerate(_read(ROOT/file)):
        if schedule['id'] in schedule_ids:
            records['reference', schedule['id']] = {'definition': schedule, 'provenance': _receipt(file, '/'+str(index), 'Exact frozen rules, source order, selectors and design days')}
    file = 'data/definition-releases/v0.1.1/compositions.json'
    allowed = {case['program_id'] for case in manifest_scope['cases']}
    for index, composition in enumerate(_read(ROOT/file)):
        if composition['members'] and all(member['program_id'] in allowed for member in composition['members']):
            records['composition', composition['id']] = {'definition': composition, 'provenance': _receipt(file, '/'+str(index), 'Exact frozen membership and weights')}
    file = 'data/resolution-releases/v0.4.0/resolutions.json'
    resolutions = _read(ROOT/file)
    selected = [r for r in resolutions['resolutions'] if r.get('record_id') in source_program_ids]
    records['reference', 'resolutions'] = {'resolutions': selected, 'provenance': _receipt(file, '/resolutions', 'Select by original source program identity; no implicit absence')}
    file = 'data/definition-releases/v0.1.1/services.json'
    service_ids = {s for case in manifest_scope['cases'] for s in records['program', case['program_id']]['definition']['service_ids']}
    for index, service in enumerate(_read(ROOT/file)):
        if service['id'] in service_ids:
            records['reference', service['id']] = {'definition': service, 'provenance': _receipt(file, '/'+str(index), 'Exact shared service identity, hosts and beneficiaries')}
    def identifiers(value):
        if isinstance(value, dict):
            return set().union(*(identifiers(v) for v in value.values())) if value else set()
        if isinstance(value, list):
            return set().union(*(identifiers(v) for v in value)) if value else set()
        return {value} if isinstance(value, str) and value.startswith(('evidence-', 'sourcefile-')) else set()
    required_ids = identifiers(list(records.values()))
    file = 'data/definition-releases/v0.1.1/provenance.json'
    for index, evidence in enumerate(_read(ROOT/file)):
        if evidence['id'] in required_ids:
            records['reference', evidence['id']] = {'definition': evidence, 'provenance': _receipt(file, '/'+str(index), 'Exact per-field original value, units, source locator and transformation')}
            required_ids.add(evidence['source_file_id'])
    file = 'data/definition-releases/v0.1.1/source_files.json'
    for index, source_file in enumerate(_read(ROOT/file)):
        if source_file['id'] in required_ids:
            records['reference', source_file['id']] = {'definition': source_file, 'provenance': _receipt(file, '/'+str(index), 'Exact upstream source revision and byte checksum')}
    file = 'data/resolution-releases/v0.4.0/fixed-background-schedules.json'
    records['residential', 'fixed-background-schedules'] = {'definition': _read(ROOT/file), 'provenance': _receipt(file, '/', 'Exact frozen source default variants')}
    for notice in lock['notices']:
        records['reference', 'notice-'+Path(notice).stem] = {'text': (ROOT/notice).read_text(encoding='utf-8'), 'source_path': notice}
    records['reference', 'notice-standards086'] = sources.get('reference', 'standards086__LICENSE_md')
    # Inventory exposes every dependency; generation support is certified by later kernel gates.
    return write_resources(destination, records, {'scope': 'pilot', 'milestone_id': 'M1',
                           'scope_version': manifest_scope['scope_version'], 'source_gate_status': 'passed',
                           'generator_support_status': 'not_shipped', 'cases': manifest_scope['cases'],
                           'dependency_inventory': lock['required_resources'], 'blocked_families': lock['blocked_families']})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scope', default='pilot')
    parser.add_argument('--destination', type=Path, default=ROOT/'build/generator-pilot-resources')
    args = parser.parse_args()
    manifest = build_resources(args.destination, args.scope)
    print(f"Verified {len(manifest['resources'])} dependencies for {len(manifest['cases'])} cases: {manifest['resource_set_id']}")


if __name__ == '__main__':
    main()
