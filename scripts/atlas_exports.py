"""Consumer exports from the ADR 0036 release folder.

Program JSON 5.0.0 has two versions: `source` (actual values only; the earlier
raw connector form) and `filled` (fillings and approved defaults applied; the
earlier ready form with water heating folded in). Construction sets export as
detailed 4.0.0 and unified 3.0.0. Every export carries the release's readable
IDs. The program documents come from the existing exporters run over records
rebuilt from the release, so their physics and policies are unchanged.

Release 1.1.0 (the DOE reference reconciliation, ADR 0037) exports the additive
minors Program JSON 5.1.0 and constructions 4.1.0 / 3.1.0, and building services
1.0.0 per folder: `Release(release='1.1.0')`; release 1.2.0 adds the construction-only folders' programs (ADR 0039).

python -m scripts.atlas_exports --schemas                 # write the derived schemas
python -m scripts.atlas_exports --program ID --version filled
python -m scripts.atlas_exports --construction SET --context KEY --representation detailed
python -m scripts.atlas_exports --release 1.1.0 --building-services doe-ref-1980-2004/hospital
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
MINOR = {'releases': ('1.1.0', '1.2.0'), 'program': ('program-json-v5.1.schema.json', '5.1.0'),
         'detailed': ('construction-json-v4.1.schema.json', '4.1.0', 'urn:archetype-atlas:construction-set:4.1.0'),
         'unified': ('construction-equivalent-v3.1.schema.json', '3.1.0', 'urn:archetype-atlas:construction-equivalent:3.1.0'),
         'services': ('building-services-v1.schema.json', '1.0.0')}
HUMIDITY = ('humidifying_setpoint_schedule_id', 'dehumidifying_setpoint_schedule_id')
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
    out[MINOR['program'][0]] = program_minor(out[PROGRAM_SCHEMA])
    for representation, (name, _, version, _) in CONSTRUCTION_SCHEMAS.items():
        out[MINOR[representation][0]] = construction_minor(out[name], representation)
    out[MINOR['services'][0]] = services_schema()
    return out


NULLABLE_RATIO = {'anyOf': [{'type': 'number', 'minimum': 0, 'maximum': 1}, {'type': 'null'}]}
RATIOS = {'type': 'object', 'additionalProperties': False, 'required': ['N', 'E', 'S', 'W', 'roof'],
          'properties': {d: NULLABLE_RATIO for d in ('N', 'E', 'S', 'W', 'roof')}}
CALENDAR = {'type': 'object', 'additionalProperties': False, 'required': ['holidays', 'daylight_saving', 'evidence_id'],
            'description': 'The source model calendar (ADR 0037): holiday rules to resolve per year, and daylight saving recorded, not applied.',
            'properties': {'holidays': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False, 'required': ['name', 'rule'],
                                                                   'properties': {'name': {'type': 'string'}, 'rule': {'type': 'string'}}}},
                           'daylight_saving': {'anyOf': [{'type': 'null'}, {'type': 'object', 'additionalProperties': False,
                                                                            'required': ['start', 'end', 'applied'],
                                                                            'properties': {'start': {'type': 'string'}, 'end': {'type': 'string'},
                                                                                           'applied': {'const': False}}}]},
                           'evidence_id': {'type': 'string', 'minLength': 1}}}


def program_minor(major):
    """Program JSON 5.1.0: 5.0.0 with the ADR 0037 fields, all optional."""
    schema = json.loads(json.dumps(major).replace('urn:archetype-atlas:program-json:5.0.0', 'urn:archetype-atlas:program-json:5.1.0'))
    schema['title'] = 'Self-contained program JSON 5.1.0'
    schema['description'] += (' 5.1.0 (release 1.1.0) adds window ratios, the source calendar, source spaces, humidity controls, '
                              'alternates, water-use zone gains and building-service IDs; every 5.0.0 field keeps its meaning.')
    spaces = {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False, 'required': ['name', 'floor_area_m2', 'multiplier'],
                                         'properties': {'name': {'type': 'string'}, 'floor_area_m2': {'type': 'number', 'minimum': 0},
                                                        'multiplier': {'type': 'integer', 'minimum': 1}}}}
    added = {
        'fenestration': {'type': 'object', 'additionalProperties': False, 'required': ['basis', 'wwr', 'roof', 'evidence_id'],
                         'description': 'Window over exterior wall area of the program zones by direction; roof is skylight over roof area. '
                                        'null: no exterior surface in that direction; 0: wall without window.',
                         'properties': {'basis': {'const': 'program_zone_surfaces'}, 'roof': NULLABLE_RATIO,
                                        'wwr': {'type': 'object', 'additionalProperties': False, 'required': ['N', 'E', 'S', 'W'],
                                                'properties': {d: NULLABLE_RATIO for d in 'NESW'}},
                                        'evidence_id': {'type': 'string', 'minLength': 1}}},
        'source_calendar': CALENDAR,
        'source_spaces': {**spaces, 'description': 'Source spaces this program represents where it is not their tagged space type.'},
        'excluded_source_spaces': {'type': 'array', 'items': {'type': 'string'},
                                   'description': 'Source spaces of this space type that another program represents.'},
        'alternates': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False,
                                                  'required': ['quantity', 'source_family', 'evidence_id', 'reason_id'],
                                                  'properties': {'quantity': {'type': 'string'}, 'value': {'type': 'number'},
                                                                 'schedule_id': {'type': 'string'}, 'source_family': {'type': 'string'},
                                                                 'evidence_id': {'type': 'string'}, 'reason_id': {'type': 'string'}}},
                       'description': 'Second backed values where two sources disagree; the primary value is unchanged.'},
        'water_use_gains': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False,
                                                       'required': ['demand_id', 'zone_gains', 'sensible_fraction', 'latent_fraction', 'semantics'],
                                                       'properties': {'demand_id': {'type': 'string'}, 'zone_gains': {'const': 'applied'},
                                                                      'sensible_fraction': NULLABLE_RATIO, 'latent_fraction': NULLABLE_RATIO,
                                                                      'semantics': {'type': 'string'}, 'zone_heat_assignment': {'type': 'string'},
                                                                      'evidence_id': {'type': 'string'}}},
                            'description': 'EnergyPlus WaterUse:Equipment gains of this program\'s hot-water demands: sensible = fraction x '
                                           'mass flow x cp x (mixed - zone air temperature); latent = fraction of the evaporable water.'},
        'building_service_ids': {'type': 'array', 'items': {'type': 'string'},
                                 'description': 'Building services (building services 1.0.0) whose source objects sit in this program\'s zones.'}}
    for version in VERSIONS:
        variant = schema['$defs'][version]
        variant['properties']['schema_version'] = {'const': '5.1.0'}
        variant['properties']['source']['properties']['release'] = {'enum': [f'atlas-release-{r}' for r in MINOR['releases']]}
        variant['properties'].update(copy.deepcopy(added))
        controls = variant['$defs']['controls']['properties']
        for field in HUMIDITY:
            controls[field] = {'anyOf': [{'minLength': 1, 'type': 'string'}, {'type': 'null'}]}
        ruleset = variant['$defs']['ruleset']
        ruleset['properties']['unit']['enum'].append('%')  # relative humidity setpoints
        percent = {'items': {'maximum': 100, 'minimum': 0, 'type': 'number'}, 'type': 'array'}
        ruleset['allOf'].append({'if': {'properties': {'unit': {'const': '%'}}, 'required': ['unit']},
                                 'then': {'properties': {'rules': {'items': {'properties': {'values': percent}}}, 'values': percent}}})
    return schema


def construction_minor(major, representation):
    """Constructions 4.1.0 / 3.1.0: the majors with building window ratios, the DOE design-flow
    infiltration method and evidence on internal-mass entries, all optional."""
    name, version, identity = MINOR[representation]
    schema = copy.deepcopy(major)
    schema['$id'] = identity
    schema['title'] = schema['title'].replace('(release major', '(release minor').rsplit('(', 1)[0] + f'(release minor {version})'
    schema['properties']['schema_version'] = {'const': version}
    schema['properties']['fenestration_defaults'] = {
        'type': 'object', 'additionalProperties': False, 'required': ['conditioned', 'unconditioned', 'all', 'basis', 'evidence_id'],
        'description': 'Whole-building window over exterior wall area by direction (roof: skylight over roof) for conditioned, '
                       'unconditioned and all zone surfaces of the source model.',
        'properties': {'conditioned': RATIOS, 'unconditioned': RATIOS, 'all': RATIOS,
                       'basis': {'const': 'whole_building_zone_surfaces'}, 'evidence_id': {'type': 'string', 'minLength': 1}}}
    design_flow = {'type': 'object', 'additionalProperties': False, 'required': ['zone_rules', 'excluded_zones', 'evidence_id'],
                   'properties': {'zone_rules': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False,
                                                                            'required': ['method', 'value', 'unit', 'coefficients', 'schedule', 'zones'],
                                                                            'properties': {'method': {'type': 'string'}, 'value': {'type': 'number', 'minimum': 0},
                                                                                           'unit': {'type': 'string'}, 'coefficients': {'type': 'array', 'items': {'type': 'number'}},
                                                                                           'schedule': {'type': 'object'}, 'zones': {'type': 'array', 'items': {'type': 'string'}}}}},
                                  'excluded_zones': {'type': 'array', 'items': {'type': 'string'}},
                                  'evidence_id': {'type': 'string'}, 'consumer_inputs': {'type': 'string'}}}
    infiltration = schema['$defs'].get('infiltration')
    if infiltration and 'properties' in infiltration:
        infiltration['properties']['default_method'] = copy.deepcopy(infiltration['properties']['method'])
        infiltration['properties']['methods'] = {'type': 'object', 'additionalProperties': False,
                                                 'properties': {'doe_design_flow': design_flow}}
    schema['$defs']['massEntry']['properties']['evidence_id'] = {'type': 'string', 'minLength': 1}
    return schema


def services_schema():
    return {'$schema': 'https://json-schema.org/draft/2020-12/schema', '$id': 'urn:archetype-atlas:building-services:1.0.0',
            'title': 'Building services 1.0.0',
            'description': 'The building-level services of one template x building-type folder (ADR 0037): elevators, exhaust '
                           'fans, exterior lights and equipment, refrigeration cases and racks, each instantiated once, with '
                           'its schedules inlined.',
            'type': 'object', 'additionalProperties': False,
            'required': ['schema_version', 'kind', 'release', 'template', 'building_type', 'services', 'schedules'],
            'properties': {'schema_version': {'const': '1.0.0'}, 'kind': {'const': 'building_services'},
                           'release': {'enum': [f'atlas-release-{r}' for r in MINOR['releases']]}, 'template': {'type': 'string'}, 'building_type': {'type': 'string'},
                           'services': {'type': 'array', 'items': {'type': 'object', 'required': ['id', 'end_use', 'load', 'beneficiary_program_ids']}},
                           'schedules': {'type': 'object'}, 'evidence': {'type': 'object'}}}


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

    def __init__(self, files=None, root=TARGET, release='1.0.0'):
        if release not in ('1.0.0', *MINOR['releases']):
            raise ValueError('Unknown release: '+release)
        if files is None and release == '1.1.0':
            from scripts import atlas_delta_release
            files = atlas_delta_release.files()
        elif files is None and release != '1.0.0':
            from scripts import atlas_minor_release
            files = atlas_minor_release.files(release)
        if files is None:
            root = Path(root)
            files = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}
        self.files, self.release = files, release
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
        schema = PROGRAM_SCHEMA
        if self.release != '1.0.0':
            document, schema = self.program_minor(document, program_id, version), MINOR['program'][0]
        errors = [e.message for e in validator(schema).iter_errors(document)]
        if errors:
            raise ValueError(program_id+': '+'; '.join(errors[:5]))
        return document

    def folder_services(self, folder):
        return json.loads(self.files.get(folder+'services.json', b'{}'))

    def program_minor(self, document, program_id, version):
        """Program JSON 5.1.0 from a 5.0.0 document and the stored program (ADR 0037 fields)."""
        from scripts.schedule_json import normalize_schedule
        folder, stored = self.programs[program_id]
        exported = self.suite(folder).export(program_id, version)
        schedules = self.bundle(version)['schedules_by_id']
        document = {**document, 'schema_version': MINOR['program'][1]}
        document['source']['release'] = f'atlas-release-{self.release}'
        for key in ('fenestration', 'source_calendar', 'source_spaces', 'excluded_source_spaces'):
            if key in stored:
                document[key] = copy.deepcopy(stored[key])
        for field in HUMIDITY:
            value = exported['parameters'].get(field, {}).get('value')
            if value:
                document['controls'][field] = value
                document['schedules'][value] = normalize_schedule(schedules[value])
        alternates = []
        for load in stored['loads']:
            for alternate in load.get('alternates', []):
                alternates.append({'quantity': load['quantity'], **alternate})
                if 'schedule_id' in alternate:
                    document['schedules'][alternate['schedule_id']] = normalize_schedule(schedules[alternate['schedule_id']])
        if alternates:
            document['alternates'] = alternates
        services = self.folder_services(folder)
        demands = {l['demand_id'] for l in document['loads']} | {w['demand_id'] for w in document.get('water_heating') or []}
        gains = []
        for load in [*stored['loads'], *(s['load'] for s in services.values())]:
            effects = load.get('thermal_effects') or {}
            if load.get('demand_id') in demands and effects.get('zone_gains') == 'applied':
                gains.append({'demand_id': load['demand_id'], 'zone_gains': 'applied', 'semantics': effects['semantics'],
                              'sensible_fraction': effects['sensible_fraction']['value'], 'latent_fraction': effects['latent_fraction']['value'],
                              'zone_heat_assignment': load.get('zone_heat_assignment', 'unresolved'),
                              'evidence_id': effects['sensible_fraction']['evidence_id']})
        if gains:
            document['water_use_gains'] = sorted(gains, key=lambda g: g['demand_id'])
        building = sorted(sid for sid, s in services.items() if program_id in s['beneficiary_program_ids']
                          and s['load'].get('quantity') != 'hot_water_volume')
        if building:
            document['building_service_ids'] = building
        return document

    def building_services(self, folder):
        """Building services 1.0.0 for one folder, e.g. `doe-ref-1980-2004/hospital`."""
        from scripts.schedule_json import normalize_schedule
        if self.release == '1.0.0':
            raise ValueError('Building services are exported from release 1.1.0 on')
        services = self.folder_services(f'commercial/{folder}/')
        suite = self.suite(f'commercial/{folder}/')
        added = {sid: s for sid, s in services.items() if s['load'].get('quantity') != 'hot_water_volume'}
        if not added:
            raise ValueError('No building services in '+folder)
        schedules = {}
        for service in added.values():
            for key in ('schedule_id', 'lighting_schedule_id'):
                sid = service['load'].get(key)
                if sid:
                    schedules[sid] = normalize_schedule({**suite.schedule(sid), 'id': sid})
        evidence = json.loads(self.files[f'evidence/commercial/{folder}.json'])
        first = next(iter(added.values()))
        document = {'schema_version': MINOR['services'][1], 'kind': 'building_services', 'release': f'atlas-release-{self.release}',
                    'template': first['template'], 'building_type': first['building_type'],
                    'services': [{**copy.deepcopy(s), 'id': sid} for sid, s in sorted(added.items())], 'schedules': schedules,
                    'evidence': {e: evidence[e] for s in added.values() for e in s['evidence_ids'] if e in evidence}}
        errors = [e.message for e in validator(MINOR['services'][0]).iter_errors(document)]
        if errors:
            raise ValueError(folder+': '+'; '.join(errors[:5]))
        return document

    def construction(self, set_id, key, representation):
        """Construction detailed 4.0.0 or unified 3.0.0 for one context of a set."""
        name, _, version, _ = CONSTRUCTION_SCHEMAS[representation]
        if self.release != '1.0.0':
            name, version, _ = MINOR[representation]
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
    parser.add_argument('--release', choices=('1.0.0', *MINOR['releases']), default='1.0.0')
    parser.add_argument('--building-services', metavar='FOLDER', help='e.g. doe-ref-1980-2004/hospital (release 1.1.0)')
    args = parser.parse_args()
    if args.schemas or args.check_schemas:
        for name, schema in derived_schemas().items():
            path = SCHEMAS/name
            if args.schemas:
                path.write_bytes(suite_bytes(schema))
            elif not path.exists() or load_json(path) != schema:
                raise SystemExit(f'{name} differs from its derivation; run python -m scripts.atlas_exports --schemas')
        print('Program 5.0.0 / 5.1.0, construction 4.0.0 / 4.1.0 / 3.0.0 / 3.1.0 and building services 1.0.0 schemas '
              +('written' if args.schemas else 'match their derivation'))
        return
    release = Release(release=args.release)
    if args.building_services:
        document = release.building_services(args.building_services)
    elif args.program:
        document = release.program(args.program, args.version)
    elif args.construction and args.context:
        document = release.construction(args.construction, args.context, args.representation)
    else:
        parser.error('give --schemas, --program, or --construction with --context')
    sys.stdout.write(json.dumps(document, indent=2, ensure_ascii=False)+'\n')


if __name__ == '__main__':
    main()
