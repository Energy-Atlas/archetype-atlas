"""Versioned, model-independent energy definition contract and locked inputs."""
from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError
from scripts.common import ROOT, load_atlas, load_json
from scripts.fetch import fetch_file

PRIMARY = {'program': 'programs', 'construction': 'constructions', 'hvac_system': 'hvac_systems'}
TABLES = (*PRIMARY.values(), 'materials', 'components', 'services', 'compositions',
          'schedules', 'provenance', 'source_files', 'policies', 'coverage')


class DefinitionError(ValueError):
    pass


class DefinitionBundle(dict):
    def __init__(self, **values):
        super().__init__({table: [] for table in TABLES})
        self.update(values)

    def merge(self, other):
        for table in TABLES:
            existing = {row['id']: row for row in self[table]}
            for row in other.get(table, []):
                if row['id'] in existing and existing[row['id']] != row:
                    raise DefinitionError('Conflicting definition: '+row['id'])
                existing[row['id']] = row
            self[table] = sorted(existing.values(), key=lambda row: row['id'])
        return self


@dataclass
class BuildContext:
    root: Path = ROOT
    scope: str = 'pilot'
    atlas: dict = field(default_factory=dict)
    policy: dict = field(default_factory=dict)
    sources: dict = field(default_factory=dict)
    extraction_date: str = '2026-10-07'
    dependencies: dict = field(default_factory=dict)

    def includes(self, row):
        return self.scope == 'full' or row.get('building_type') == 'MediumOffice'


@dataclass
class ValidationReport:
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    coverage: dict = field(default_factory=dict)


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       separators=(',', ':'), allow_nan=False)+'\n').encode()


def stable_id(namespace: str, payload: dict) -> str:
    return namespace+'-'+hashlib.sha256(canonical(payload)).hexdigest()[:24]


def verify_locked(path, descriptor):
    content = Path(path).read_bytes()
    if (len(content) != descriptor['size_bytes'] or
            hashlib.sha256(content).hexdigest() != descriptor['sha256']):
        raise DefinitionError('Locked input mismatch: '+str(path))
    return content


def parameter(value, unit, evidence_id, *, status=None, required_inputs=None):
    if isinstance(value, float) and not math.isfinite(value):
        raise DefinitionError('Non-finite physical value')
    return {'value': value, 'unit': unit, 'status': status or ('unknown' if value is None else 'known'),
            'evidence_id': evidence_id, 'required_inputs': required_inputs or []}


def validate_record(kind: str, record: dict) -> None:
    if kind not in PRIMARY or record.get('kind') != kind:
        raise DefinitionError('Unsupported primary kind: '+kind)
    schema = load_json(ROOT/'schemas/definitions.schema.json')
    try:
        Draft202012Validator(schema['$defs']['record'], resolver=None).validate(record)
    except ValidationError as error:
        raise DefinitionError(error.message) from error
    for name, value in record.get('parameters', {}).items():
        _validate_parameter(value, name)
    for value in record.get('loads', []):
        _validate_parameter(value, value.get('quantity', 'load'))
        if not {'quantity', 'basis', 'demand_id', 'schedule_id'} <= value.keys():
            raise DefinitionError('Load missing basis/ownership/schedule')


def _validate_parameter(value, name):
    if not {'value', 'unit', 'status', 'evidence_id', 'required_inputs'} <= value.keys():
        raise DefinitionError('Missing physical field evidence: '+name)
    if not value['evidence_id'] or not value['unit']:
        raise DefinitionError('Missing evidence/unit: '+name)
    if value['status'] not in {'known', 'unknown', 'not_reported', 'not_applicable', 'requires_input'}:
        raise DefinitionError('Invalid value status: '+name)
    if (value['value'] is None) == (value['status'] == 'known'):
        raise DefinitionError('Null/status mismatch: '+name)
    canonical(value)


def validate_evidence(row):
    required = {'id', 'source_file_id', 'locator', 'original_value', 'original_unit',
                'transformation', 'extraction_date', 'interpretation'}
    if not required <= row.keys() or any(not row[key] for key in
            ('id', 'locator', 'original_unit', 'transformation', 'extraction_date', 'interpretation')):
        raise DefinitionError('Incomplete field provenance')


def evidence(context, source_file_id, locator, value, unit, transformation, note):
    row = {'source_file_id': source_file_id, 'locator': locator, 'original_value': value,
           'original_unit': unit, 'transformation': transformation,
           'extraction_date': context.extraction_date, 'interpretation': note}
    return {'id': stable_id('evidence', row), **row}


def record(kind, source, name=None, *, derivation='normalized'):
    return {'id': stable_id(kind, {'source_id': source['id'], 'derivation': derivation}),
            'kind': kind, 'name': name or source.get('program', source.get('system_type', source['id'])),
            'source_id': source['id'], 'building_type': source.get('building_type'),
            'template': source.get('template'), 'source_family': source.get('source_family'),
            'gate': ['residential'] if source.get('building_type') in
                    {'MidriseApartment', 'HighriseApartment', 'SingleFamilyDetached',
                     'SingleFamilyAttached', 'Multifamily'} else ['nonresidential'],
            'climate': source.get('climate_zone_set'), 'evidence_view': 'source',
            'derivation': derivation, 'parameters': {}, 'evidence_ids': [], 'required_inputs': []}


def load_context(root: Path = ROOT, scope: str = 'pilot') -> BuildContext:
    root = Path(root)
    if scope not in {'pilot', 'full'}:
        raise DefinitionError('Invalid extraction scope')
    policy = load_json(root/'sources/definition-policy.json')
    dependencies = {}
    for name, relative in policy['dependencies'].items():
        directory = root/relative
        manifest = load_json(directory/'manifest.json')
        for path, descriptor in manifest['files'].items():
            verify_locked(directory/path, descriptor)
        dependencies[name] = hashlib.sha256((directory/'manifest.json').read_bytes()).hexdigest()
    lock = load_json(root/'sources/definition-evidence-lock.json')
    sources = {entry['path']: fetch_file(entry, root/'data/raw') for entry in lock['files']}
    return BuildContext(root, scope, load_atlas(root/policy['dependencies']['atlas']),
                        policy, sources, policy['extraction_date'], dependencies)
