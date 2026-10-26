"""Consumer exports of the ADR 0038 residential tree: Program JSON 5.3.0 for dwelling programs.

ResStock dwellings are rebuilt into their definition-release shape (record, annual
schedules, provenance) and their recovered fillings, then exported by the frozen
exporters' whole-dwelling path, so their physics and policies are unchanged:
`source` is the Program 3.0.0 raw form, `filled` the Program 4.0.0 form with the
recovered magnitudes and draw-only water heating. The code-prototype families
(IECC residential, manufactured housing) are complete source models and export
the `source` version only (ADR 0041, ADR 0042).
"""
import copy
import json

from scripts import residential_storage
from scripts.atlas_exports import decode
from scripts.residential_storage import read_annual

RESSTOCK_FAMILY = 'existing_stock_source_fixture'
PROGRAM_MINOR = ('program-json-v5.3.schema.json', '5.3.0')
DWELLING_FIELDS = ('floor_area_bin', 'building_context', 'construction_set_id', 'filling', 'commercial_counterparts')


class Dwellings:
    """The residential programs of a resolved release, exported for consumers."""

    def __init__(self, files, release):
        self.files, self.release = files, release
        self.programs = residential_storage.program_files(files)
        self._bundle, self._exporters, self._annual = None, {}, {}

    def program_ids(self):
        return sorted(self.programs)

    def stored(self, program_id):
        return copy.deepcopy(self.programs[program_id][1])

    def annual(self, folder):
        if folder not in self._annual:
            self._annual[folder] = read_annual(self.files, folder)
        return self._annual[folder]

    # ResStock: the frozen exporters on definition-shaped records.

    def resstock_bundle(self):
        """Definition-shaped records, schedules and provenance of every ResStock dwelling, and their recoveries."""
        if self._bundle is None:
            glossary = json.loads(self.files['evidence/glossary.json'])
            programs, schedules, recovery, recovered_schedules, evidence = [], {}, {}, {}, {}
            for pid, (folder, stored) in sorted(self.programs.items()):
                if stored['source_family'] != RESSTOCK_FAMILY:
                    continue
                record = {k: v for k, v in stored.items() if k not in DWELLING_FIELDS}
                record.update(kind='program', evidence_view='source', detail='SourcePrograms')
                programs.append(record)
                filling = stored['filling']
                recovery[stored['source_id']] = {
                    'loads': [{k: v for k, v in l.items() if k != 'resolutions'} for l in filling['loads']],
                    **{k: filling[k] for k in ('controls', 'climate', 'vintage', 'unresolved', 'metadata')}}
                for sid, series in self.annual(folder).items():
                    if series.get('type') == 'annual':
                        recovered_schedules[sid] = {**series, 'id': sid}
                    else:
                        schedules[sid] = {**series, 'id': sid}
                path = 'evidence/residential/'+folder[len('residential/'):].rstrip('/')+'.json'
                evidence.update(json.loads(self.files[path]))
            provenance = [decode(eid, row, glossary) for eid, row in sorted(evidence.items())]
            self._bundle = ({'programs': programs, 'schedules': list(schedules.values()), 'services': [],
                             'compositions': [], 'provenance': provenance}, recovery, recovered_schedules)
        return self._bundle

    def exporter(self, version):
        if version not in self._exporters:
            bundle, recovery, recovered_schedules = self.resstock_bundle()
            if version == 'source':
                from scripts.program_json_v3 import ProgramExporter
                exporter = ProgramExporter(bundle, recovery=recovery)
                base = exporter
            else:
                from scripts.program_water_heating import ProgramExporter
                exporter = ProgramExporter(bundle)
                base = exporter.base
                base.recovery = recovery
            base.recovered_schedules = recovered_schedules
            self._exporters[version] = exporter
        return self._exporters[version]

    def program(self, program_id, version):
        """Program JSON 5.3.0 of one dwelling program in one version."""
        from scripts import atlas_exports
        if version not in atlas_exports.VERSIONS:
            raise ValueError('Unknown program version: '+version)
        folder, stored = self.programs[program_id]
        if stored['source_family'] != RESSTOCK_FAMILY:
            from scripts import prototype_dwellings
            document = prototype_dwellings.document(self, program_id, version)
        else:
            exporter = self.exporter(version)
            document = exporter.export(program_id, 'raw') if version == 'source' else exporter.export(program_id)
            document.pop('export_mode')
            for key in ('definition_release', 'evidence_view'):
                document['source'].pop(key)
            document = {'schema_version': PROGRAM_MINOR[1], 'version': version,
                        **{k: v for k, v in document.items() if k != 'schema_version'}}
            document['dwelling'] = dwelling(stored)
        document['id'] = program_id
        document['source']['release'] = f'atlas-release-{self.release}'
        errors = [e.message for e in atlas_exports.validator(PROGRAM_MINOR[0]).iter_errors(document)]
        if errors:
            raise ValueError(program_id+': '+'; '.join(errors[:5]))
        return document


def dwelling(stored):
    """The 5.3.0 dwelling block of a stored dwelling program."""
    out = {'family': stored['source_family'], 'climate': stored.get('climate'), 'vintage': stored.get('vintage'),
           'construction_set_id': stored['construction_set_id']}
    for key in ('floor_area_bin', 'building_context', 'commercial_counterparts', 'edition', 'variant',
                'section_type', 'template_key', 'tier'):
        if key in stored:
            out[key] = copy.deepcopy(stored[key])
    return out


def program_schema(minor):
    """Program JSON 5.3.0: 5.2.0 with dwelling programs (ADR 0038, 0041, 0042), all fields optional."""
    schema = json.loads(json.dumps(minor).replace('urn:archetype-atlas:program-json:5.2.0', 'urn:archetype-atlas:program-json:5.3.0'))
    schema['title'] = 'Self-contained program JSON 5.3.0'
    schema['description'] += (' 5.3.0 (release 1.4.0) exports residential dwelling programs on the dwelling_unit basis: '
                              'a dwelling block (family, climate, vintage, floor-area bin, building context, construction '
                              'set), host-zone tags and roles on loads, and dwelling-level services instantiated once; '
                              'every 5.2.0 field keeps its meaning.')
    text = {'type': 'string', 'minLength': 1}
    block = {'type': 'object', 'additionalProperties': False, 'required': ['family', 'construction_set_id'],
             'description': 'The dwelling the program describes. Loads keep the source basis, per dwelling unit where '
                            'the source gives one; rooms, zones and systems are the consumer\'s (ADR 0038).',
             'properties': {'family': text, 'climate': {'anyOf': [text, {'type': 'null'}]},
                            'vintage': {'anyOf': [text, {'type': 'null'}]}, 'construction_set_id': text,
                            'floor_area_bin': text, 'building_context': {'type': 'object'},
                            'commercial_counterparts': {'type': 'array', 'items': text},
                            'edition': text, 'variant': {'type': 'object'}, 'section_type': text,
                            'template_key': text, 'tier': {'anyOf': [text, {'type': 'null'}]}}}
    for version in ('source', 'filled'):
        variant = schema['$defs'][version]
        variant['properties']['schema_version'] = {'const': '5.3.0'}
        variant['properties']['source']['properties']['release'] = {'enum': ['atlas-release-1.4.0']}
        variant['properties']['dwelling'] = copy.deepcopy(block)
        for name in ('load',):  # ready_load refers to load
            if name in variant['$defs']:
                props = variant['$defs'][name]['properties']
                props['host_zone'] = {**text, 'description': 'The source zone hosting the load inside the dwelling '
                                      '(living, garage, attic, crawlspace, basement, breezeway, ...).'}
                props['role'] = {**text, 'description': 'A load with a special meaning, e.g. reference_design_adjustment.'}
                props['applies_with'] = {'type': 'object', 'description': 'Construction-context conditions under '
                                         'which the load applies, e.g. {"foundation": "heated-basement"}.'}
    return schema
