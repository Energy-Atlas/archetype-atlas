"""Consumer exports from the ADR 0036 release folder.

Program JSON 5.0.0 has two versions: `source` (actual values only; the earlier
raw connector form) and `filled` (fillings and approved defaults applied; the
earlier ready form with water heating folded in). Construction sets export as
detailed 4.0.0 and unified 3.0.0. Every export carries the release's readable
IDs. The program documents come from the existing exporters run over records
rebuilt from the release, so their physics and policies are unchanged.

python -m scripts.atlas_exports --schemas                 # write the derived schemas
python -m scripts.atlas_exports --program ID --version filled
python -m scripts.atlas_exports --construction SET --context KEY --representation detailed
"""
import argparse
import copy
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts import atlas_constructions, atlas_programs
from scripts.atlas_format import h6, slug, suite_bytes
from scripts.atlas_release import TARGET
from scripts.common import ROOT, load_json

RELEASE = 'atlas-release-1.0.0'
SCHEMAS = ROOT/'schemas'
PROGRAM_SCHEMA = 'program-json-v5.schema.json'
CONSTRUCTION_SCHEMAS = {'detailed': ('construction-json-v4.schema.json', 'construction-json-v3.schema.json', '4.0.0',
                                     'urn:archetype-atlas:construction-set:4.0.0'),
                        'unified': ('construction-equivalent-v3.schema.json', 'construction-equivalent-v2.schema.json', '3.0.0',
                                    'urn:archetype-atlas:construction-equivalent:3.0.0')}
VERSIONS = ('source', 'filled')


def program_variant(base, version):
    """A Program 5.0.0 variant: `version` replaces `export_mode`, the release replaces the definition view."""
    schema = copy.deepcopy(base)
    for key in ('$schema', 'title', 'description'):
        schema.pop(key, None)
    schema['$id'] = f'urn:archetype-atlas:program-json:5.0.0:{version}'
    props = schema['properties']
    props['schema_version'] = {'const': '5.0.0'}
    props.pop('export_mode')
    props['version'] = {'const': version}
    schema['required'] = ['version' if r == 'export_mode' else r for r in schema['required']]
    source = props['source']
    for key in ('definition_release', 'evidence_view'):
        source['properties'].pop(key)
    source['properties']['release'] = {'const': RELEASE}
    source['required'] = [r for r in source['required'] if r not in ('definition_release', 'evidence_view')] + ['release']
    # The earlier schemas switch the ready rules on export_mode; a version is always one or the other.
    switch = [c for c in schema.get('allOf', []) if 'if' in c]
    schema['allOf'] = [c for c in schema.get('allOf', []) if 'if' not in c] + ([c['then'] for c in switch] if version == 'filled' else [])
    if not schema['allOf']:
        schema.pop('allOf')
    return schema


def derived_schemas():
    """The new majors, derived from the previous ones so the physics rules cannot drift."""
    v3, v4 = load_json(SCHEMAS/'program-json-v3.schema.json'), load_json(SCHEMAS/'program-json-v4.schema.json')
    out = {PROGRAM_SCHEMA: {
        '$schema': 'https://json-schema.org/draft/2020-12/schema', '$id': 'urn:archetype-atlas:program-json:5.0.0',
        'title': 'Self-contained program JSON 5.0.0',
        'description': 'ADR 0036 release export. version "source" holds actual values only (the 3.0.0 raw form); '
                       'version "filled" applies fillings and approved defaults with draw-only water heating (the 4.0.0 form).',
        'oneOf': [{'$ref': 'urn:archetype-atlas:program-json:5.0.0:'+v} for v in VERSIONS],
        '$defs': {'source': program_variant(v3, 'source'), 'filled': program_variant(v4, 'filled')}}}
    for name, previous, version, identity in CONSTRUCTION_SCHEMAS.values():
        schema = load_json(SCHEMAS/previous)
        schema['$id'] = identity
        schema['title'] = f'{schema["title"]} (release major {version})'
        schema['properties']['schema_version'] = {'const': version}
        out[name] = schema
    return out


def decode(eid, row, glossary):
    """An evidence row with its glossary texts restored to the definition-release shape."""
    if str(row.get('interpretation', '')).startswith('i-') and str(row.get('transformation', '')).startswith('t-'):
        return {'extraction_date': row['extraction_date'], 'id': eid,
                'interpretation': glossary['interpretations'][row['interpretation']], 'locator': row['locator'],
                'original_unit': row['original_unit'], 'original_value': row['original_value'],
                'source_file_id': row['source_file'], 'transformation': glossary['transformations'][row['transformation']]}
    return {**row, 'id': eid}


def constants(record, prefix, schedules):
    """Replace filling constants ({"constant": v}) by schedule records the exporters can read."""
    def schedule(value):
        content = {'calendar_independent': True, 'schedule_type': 'fraction', 'units': 'dimensionless',
                   'time_resolution_minutes': 60, 'source_name': 'filling constant', 'evidence_ids': [],
                   'rules': [{'day_types': 'Default', 'start_date': '2000-01-01', 'end_date': '2000-12-31', 'values': [value]}]}
        sid = f'{prefix}.constant-{slug(str(value))}.{h6(content)}'
        schedules[sid] = {**content, 'id': sid}
        return sid
    def walk(value):
        if isinstance(value, dict):
            if set(value) == {'constant'}:
                return schedule(value['constant'])
            return {k: walk(v) for k, v in value.items()}
        if isinstance(value, list):
            return [walk(v) for v in value]
        return value
    return walk(record)


class Release:
    """A written release folder, exported for consumers."""

    def __init__(self, files=None, root=TARGET):
        if files is None:
            root = Path(root)
            files = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}
        self.files = files
        self.programs = {}
        for path, data in files.items():
            if '/programs/' in path:
                program = json.loads(data)
                self.programs[program['id']] = (path.split('/programs/')[0]+'/', program)
        self.constructions = atlas_constructions.read_files(files)
        self._suites, self._bundles, self._exporters = {}, {}, {}

    def program_ids(self):
        return sorted(self.programs)

    def stored_program(self, program_id):
        return copy.deepcopy(self.programs[program_id][1])

    def suite(self, folder):
        if folder not in self._suites:
            self._suites[folder] = atlas_programs.read_folder({p: d for p, d in self.files.items() if p.startswith(folder)})
        return self._suites[folder]

    def bundle(self, version):
        """Definition-shaped records for every program in one version, with release IDs."""
        if version not in self._bundles:
            glossary = json.loads(self.files['evidence/glossary.json'])
            schedules, programs, compositions = {}, [], []
            for pid, (folder, stored) in sorted(self.programs.items()):
                suite = self.suite(folder)
                for sid in suite.table:
                    schedules.setdefault(sid, {**suite.schedule(sid), 'id': sid})
                record = suite.export(pid, version)
                record = constants(record, '.'.join(pid.split('.')[:2]), schedules)
                record.update(kind='program', evidence_view='source' if version == 'source' else 'reviewed')
                if 'composition' in stored:
                    cid = pid+':composition'
                    record['composition_id'] = cid
                    compositions.append({'id': cid, 'name': record['name'], 'mode': record['detail'],
                                         'building_type': record['building_type'], 'template': record['template'],
                                         'evidence_view': record['evidence_view'], 'method': stored['composition']['method'],
                                         'members': copy.deepcopy(stored['composition']['members'])})
                programs.append(record)
            services = [{**row, 'id': sid} for p, d in sorted(self.files.items()) if p.endswith('/services.json')
                        for sid, row in json.loads(d).items()]
            provenance = [decode(eid, row, glossary) for p, d in sorted(self.files.items())
                          if p.startswith('evidence/') and not p.endswith('glossary.json') for eid, row in json.loads(d).items()]
            self._bundles[version] = {'programs': programs, 'schedules': list(schedules.values()), 'services': services,
                                      'compositions': compositions, 'provenance': provenance, 'schedules_by_id': schedules}
        return self._bundles[version]

    def exporter(self, version):
        if version not in self._exporters:
            if version == 'source':
                from scripts.program_json_v3 import ProgramExporter
                self._exporters[version] = ProgramExporter(self.bundle(version))
            else:
                from scripts.program_water_heating import ProgramExporter
                services, programs = self.capped()
                self._exporters[version] = ProgramExporter(self.bundle(version), capped_services=services, capped_programs=programs)
        return self._exporters[version]

    def capped(self):
        """The approved capped-delivery demands (ADR 0018) under release IDs.

        The policy names them by definition-release IDs; services are matched by their water
        path and programs by upstream source ID and name, which the release keeps.
        """
        from scripts.program_water_heating import CAPPED_PROGRAMS, CAPPED_SERVICES
        definitions = ROOT/'data/definition-releases/v0.1.1'
        old_services = {s['id']: s for s in load_json(definitions/'services.json')}
        old_programs = {p['id']: p for p in load_json(definitions/'programs.json')}
        by_path = {row['path_id']: sid for p, d in self.files.items() if p.endswith('/services.json')
                   for sid, row in json.loads(d).items()}
        by_source = {(p['source_id'], p['name']): pid for pid, (_, p) in self.programs.items() if p.get('source_id')}
        source = lambda r: old_programs.get(r.get('source_definition_id'), r)
        services = {by_path[old_services[s]['path_id']] for s in CAPPED_SERVICES if old_services[s]['path_id'] in by_path}
        programs = {by_source[k] for k in ((source(old_programs[p])['source_id'], source(old_programs[p])['name'])
                                           for p in CAPPED_PROGRAMS) if k in by_source}
        return services, programs

    def program(self, program_id, version):
        """Program JSON 5.0.0 in one version."""
        if version not in VERSIONS:
            raise ValueError('Unknown program version: '+version)
        exporter = self.exporter(version)
        document = exporter.export(program_id, 'raw') if version == 'source' else exporter.export(program_id)
        document.pop('export_mode')
        source = document['source']
        for key in ('definition_release', 'evidence_view'):
            source.pop(key)
        source['release'] = RELEASE
        document = {'schema_version': '5.0.0', 'version': version, **{k: v for k, v in document.items() if k != 'schema_version'}}
        document['id'] = program_id
        errors = [e.message for e in validator(PROGRAM_SCHEMA).iter_errors(document)]
        if errors:
            raise ValueError(program_id+': '+'; '.join(errors[:5]))
        return document

    def construction(self, set_id, key, representation):
        """Construction detailed 4.0.0 or unified 3.0.0 for one context of a set."""
        name, _, version, _ = CONSTRUCTION_SCHEMAS[representation]
        document = self.constructions.export(set_id, key, representation)
        document['schema_version'] = version
        errors = [e.message for e in validator(name).iter_errors(document)]
        if errors:
            raise ValueError(f'{set_id} {key}: '+'; '.join(errors[:5]))
        return document


_VALIDATORS = {}


def validator(name):
    if name not in _VALIDATORS:
        _VALIDATORS[name] = Draft202012Validator(load_json(SCHEMAS/name))
    return _VALIDATORS[name]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--schemas', action='store_true', help='write the derived schemas')
    parser.add_argument('--check-schemas', action='store_true', help='fail if a committed schema differs from its derivation')
    parser.add_argument('--program')
    parser.add_argument('--version', choices=VERSIONS, default='filled')
    parser.add_argument('--construction')
    parser.add_argument('--context')
    parser.add_argument('--representation', choices=tuple(CONSTRUCTION_SCHEMAS), default='detailed')
    args = parser.parse_args()
    if args.schemas or args.check_schemas:
        for name, schema in derived_schemas().items():
            path = SCHEMAS/name
            if args.schemas:
                path.write_bytes(suite_bytes(schema))
            elif not path.exists() or load_json(path) != schema:
                raise SystemExit(f'{name} differs from its derivation; run python -m scripts.atlas_exports --schemas')
        print('Program 5.0.0 and construction 4.0.0 / 3.0.0 schemas '+('written' if args.schemas else 'match their derivation'))
        return
    release = Release()
    if args.program:
        document = release.program(args.program, args.version)
    elif args.construction and args.context:
        document = release.construction(args.construction, args.context, args.representation)
    else:
        parser.error('give --schemas, --program, or --construction with --context')
    sys.stdout.write(json.dumps(document, indent=2, ensure_ascii=False)+'\n')


if __name__ == '__main__':
    main()
