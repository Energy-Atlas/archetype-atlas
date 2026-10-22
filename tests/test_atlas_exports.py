"""Consumer exports from the ADR 0036 release: Program JSON 5.0.0, construction 4.0.0 / 3.0.0."""
import copy
import json
import re
import unittest

from jsonschema import Draft202012Validator

from scripts.common import ROOT, load_json

FOLDERS = (('90.1-2019', 'Hospital'), ('90.1-2019', 'MediumOffice'), ('90.1-2019', 'SmallHotel'))
NO_SOURCE_ZERO = {('90.1-2019', 'Hospital'), ('90.1-2019', 'MediumOffice')}
ID = re.compile(r'^(?:[a-z_]+(?:-[a-z_]+)*-[0-9a-f]{20,64}|[a-z0-9-]+(?:\.[a-z0-9-]+)+\.[0-9a-f]{6})(?::.*)?$')


class AtlasExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from scripts import atlas_exports, atlas_release
        from scripts.definition_release import read_bundle
        from scripts.program_json_v3 import ProgramExporter as V3
        from scripts.program_water_heating import ProgramExporter as V4
        cls.module = atlas_exports
        cls.release = atlas_exports.Release(atlas_release.assemble(FOLDERS))
        cls.bundle = read_bundle(ROOT/'data/definition-releases/v0.1.1')
        cls.v3, cls.v4 = V3(cls.bundle), V4(cls.bundle)
        cls.records = {p['id']: p for p in cls.bundle['programs']}
        cls.twins = {p['source_definition_id']: p for p in cls.bundle['programs'] if p.get('source_definition_id')}
        cls.resolutions = {r['id']: r for r in load_json(ROOT/'data/resolution-releases/v0.4.0/resolutions.json')['resolutions']}
        cls.old_schedules = {s['id']: s for s in cls.bundle['schedules']}

    def programs(self, folder):
        """(record, new program ID) for every commercial source record of a folder."""
        by_source = {}
        for pid in self.release.program_ids():
            program = self.release.stored_program(pid)
            if (program['template'], program['building_type']) == folder:
                by_source[(program['name'], program.get('source_id'), program['mode'])] = pid
        out = []
        for record in self.records.values():
            if ((record['template'], record['building_type']) == folder and record['evidence_view'] == 'source'
                    and record['source_family'] != 'existing_stock_source_fixture'):
                mode = {'SourcePrograms': 'source', 'DepartmentMixes': 'department', 'GeneralMix': 'general'}[record['detail']]
                key = (record['name'], record['source_id'] if record['derivation'] != 'composed' else None, mode)
                out.append((record, by_source[key]))
        return out

    def normal(self, document, schedules):
        """A document with every ID replaced: schedule references by the schedule's shape, others by '#'."""
        def shape(schedule):
            return [{k: r.get(k) for k in ('day_types', 'start_date', 'end_date', 'values')} for r in schedule.get('rules', [])] \
                or {k: schedule.get(k) for k in ('annual_values',)}
        lookup = {**schedules, **document.get('schedules', {})}
        def walk(value):
            if isinstance(value, dict):
                if 'rules' in value or 'annual_values' in value:
                    return shape(value)
                if value and all(isinstance(k, str) and ID.match(k) for k in value):
                    # An ID-keyed table is a set: identical filling constants now share one ID.
                    unique = {json.dumps(walk(v), sort_keys=True): walk(v) for v in value.values()}
                    return [unique[k] for k in sorted(unique)]
                return {k: walk(v) for k, v in value.items()}
            if isinstance(value, list):
                return [walk(v) for v in value]
            if isinstance(value, str) and ID.match(value):
                base = value.split(':')[0]
                return shape(lookup[base]) if base in lookup else '#'
            if isinstance(value, str) and value.startswith('composition/composition-'):
                return 'composition/#'  # a mix keeps its source composition's evidence (ADR 0036 section 4)
            return value
        out = walk({k: v for k, v in document.items() if k not in ('schema_version', 'export_mode', 'version', 'id')})
        out['source'] = {k: v for k, v in out['source'].items() if k not in ('definition_release', 'evidence_view', 'release')}
        # Release records keep evidence IDs sorted, so evidence is listed in ID order rather than load order.
        out['source']['evidence'] = sorted(out['source']['evidence'], key=lambda e: json.dumps(e, sort_keys=True))
        # Recipe and aggregation lists follow derived demand IDs, which change with the release's identities.
        for key in ('water_heating', 'shared_services'):
            if key in out:
                out[key] = sorted(out[key], key=lambda v: json.dumps(v, sort_keys=True))
        aggregation = out.get('metadata', {}).get('aggregation')
        if aggregation:
            key = lambda v: json.dumps(v, sort_keys=True)
            for group in aggregation.get('groups', []):
                group['components'] = sorted(group.get('components', []), key=key)
            aggregation['groups'] = sorted(aggregation.get('groups', []), key=key)
        return out

    def assertSame(self, got, expected, label, path=''):
        """Equality that reports the first differing path."""
        if isinstance(got, dict) and isinstance(expected, dict):
            for key in sorted(set(got) | set(expected)):
                self.assertIn(key, got, f'{label}: {path}/{key} missing')
                self.assertIn(key, expected, f'{label}: {path}/{key} extra')
                self.assertSame(got[key], expected[key], label, f'{path}/{key}')
        elif isinstance(got, list) and isinstance(expected, list) and len(got) == len(expected):
            for i, (a, b) in enumerate(zip(got, expected)):
                self.assertSame(a, b, label, f'{path}[{i}]')
        else:
            self.assertEqual(got, expected, f'{label}: {path}')

    def new_schedules(self, version):
        return self.release.bundle(version)['schedules_by_id']

    def test_schemas_are_derived_from_the_previous_majors(self):
        for name, schema in self.module.derived_schemas().items():
            self.assertEqual(load_json(ROOT/'schemas'/name), schema, name)
            Draft202012Validator.check_schema(schema)

    def test_filled_programs_equal_the_v4_export_of_the_reviewed_definition(self):
        validator = Draft202012Validator(load_json(ROOT/'schemas/program-json-v5.schema.json'))
        for folder in FOLDERS:
            for record, pid in self.programs(folder):
                document = self.release.program(pid, 'filled')
                self.assertEqual(list(validator.iter_errors(document)), [], pid)
                self.assertEqual((document['schema_version'], document['version'], document['id']), ('5.0.0', 'filled', pid))
                self.assertNotIn('export_mode', document)
                self.assertFalse(any(l['type'] == 'hot_water' for l in document['loads']))
                reviewed = self.twins.get(record['id'], record)
                expected = self.v4.export(reviewed['id'])
                self.assertSame(self.normal(document, self.new_schedules('filled')), self.normal(expected, self.old_schedules), record['name'])

    def test_source_programs_equal_the_v3_raw_export_of_the_source_definition(self):
        validator = Draft202012Validator(load_json(ROOT/'schemas/program-json-v5.schema.json'))
        patched = self.patched_exporter()
        checked = 0
        for folder in FOLDERS:
            for record, pid in self.programs(folder):
                document = self.release.program(pid, 'source')
                self.assertEqual(list(validator.iter_errors(document)), [], pid)
                self.assertEqual((document['version'], document['default_policy_id']), ('source', None))
                if record['derivation'] == 'composed' and folder not in NO_SOURCE_ZERO:
                    continue  # a mix's source-zero members change it; members themselves are checked
                expected = patched.export(record['id'], 'raw')
                self.assertSame(self.normal(document, self.new_schedules('source')), self.normal(expected, self.old_schedules), record['name'])
                checked += 1
        self.assertGreater(checked, 20)

    def patched_exporter(self):
        """The v3 exporter over definitions whose source-zero values are actual, as the release stores them."""
        from scripts import atlas_programs
        from scripts.program_json_v3 import ProgramExporter as V3
        bundle = copy.deepcopy(self.bundle)
        for record in bundle['programs']:
            reviewed = self.twins.get(record['id'])
            if record['evidence_view'] != 'source' or not reviewed:
                continue
            bases = {}
            for rid in reviewed.get('reviewed_resolution_ids') or []:
                for target in atlas_programs.addressed(self.resolutions[rid]['field']):
                    bases.setdefault(target, set()).add(self.resolutions[rid]['basis'])
            zero = {t for t, b in bases.items() if b == {'source_zero'}}
            loads = {l['quantity']: l for l in reviewed['loads']}
            record['loads'] = [copy.deepcopy(loads[l['quantity']]) if ('load', l['quantity']) in zero else l for l in record['loads']]
            for kind, key in zero:
                if kind == 'parameter':
                    record['parameters'][key] = copy.deepcopy(reviewed['parameters'][key])
        return V3(bundle)

    def test_construction_exports_equal_current_documents_with_new_majors(self):
        from scripts import atlas_constructions
        from scripts.construction_foundation_release import export_pair
        from scripts.atlas_format import translate
        validators = {r: Draft202012Validator(load_json(ROOT/'schemas'/name)) for r, name in
                      (('detailed', 'construction-json-v4.schema.json'), ('unified', 'construction-equivalent-v3.schema.json'))}
        sources = atlas_constructions.load_sources()
        built = atlas_constructions.build_folders(sources, [f for f in FOLDERS])
        checked = 0
        for cid, (set_id, key) in built.contexts.items():
            pair = export_pair(cid, release=sources.release)
            for representation, current, version in zip(('detailed', 'unified'), pair, ('4.0.0', '3.0.0')):
                document = self.release.construction(set_id, key, representation)
                self.assertEqual(list(validators[representation].iter_errors(document)), [], cid)
                expected = translate(current, built.ids[set_id.split('.')[0]])
                expected['schema_version'] = version
                self.assertEqual(document, expected, cid)
                checked += 1
        self.assertEqual(checked, 2 * len(built.contexts))

    def test_release_exports_are_deterministic(self):
        pid = next(iter(self.release.program_ids()))
        again = self.module.Release(self.release.files)
        self.assertEqual(again.program(pid, 'filled'), self.release.program(pid, 'filled'))


if __name__ == '__main__':
    unittest.main()
