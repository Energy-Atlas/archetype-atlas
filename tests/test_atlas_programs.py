"""ADR 0036 commercial program suites: one template x building-type folder end to end."""
import hashlib
import json
import re
import unittest

from scripts.common import load_json

FOLDERS = (('90.1-2019', 'Hospital'), ('90.1-2019', 'Outpatient'), ('90.1-2019', 'SmallHotel'))
DEFINITIONS = 'data/definition-releases/v0.1.1/'
IDENTITY = ('id', 'kind', 'evidence_view', 'source_definition_id', 'reviewed_resolution_ids', 'composition_id')
ID = re.compile(r'^90-1-2019\.[a-z0-9-]+\.[a-z0-9.-]+\.[0-9a-f]{6}$')


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


class AtlasProgramSuiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from scripts import atlas_programs
        cls.module = atlas_programs
        cls.sources = atlas_programs.load_sources()
        cls.built = {f: atlas_programs.build_folder(cls.sources, *f) for f in FOLDERS}
        cls.suites = {f: atlas_programs.read_folder(b.files) for f, b in cls.built.items()}
        programs = load_json(DEFINITIONS + 'programs.json')
        cls.records = {p['id']: p for p in programs}
        cls.twins = {p['source_definition_id']: p for p in programs if p.get('source_definition_id')}
        cls.schedules = {s['id']: s for s in load_json(DEFINITIONS + 'schedules.json')}
        resolutions = load_json('data/resolution-releases/v0.4.0/resolutions.json')
        cls.resolutions = {r['id']: r for r in resolutions['resolutions']}
        cls.unresolved = resolutions['unresolved']

    def folder_sources(self, folder):
        template, building_type = folder
        return [p for p in self.records.values() if p['template'] == template and p['building_type'] == building_type
                and p['evidence_view'] == 'source' and p['source_family'] != 'existing_stock_source_fixture']

    def translate(self, value, ids):
        if isinstance(value, dict):
            return {k: self.translate(v, ids) for k, v in value.items()}
        if isinstance(value, list):
            return [self.translate(v, ids) for v in value]
        return ids.get(value, value) if isinstance(value, str) else value

    def expected(self, record, ids, new_id):
        out = {k: v for k, v in record.items() if k not in IDENTITY}
        if record['derivation'] == 'composed':
            out.pop('source_id', None)
        out = self.translate(out, ids)
        out['id'] = new_id
        out['evidence_ids'] = sorted(out['evidence_ids'])
        return out

    def semantic(self, record, suite):
        """A mix without its view identity: demand and evidence IDs dropped, schedules by content."""
        def schedule(ref):
            if isinstance(ref, str) and ref in suite.table:
                ref = suite.schedule(ref)
            elif isinstance(ref, str) and ref in self.schedules:
                ref = {k: v for k, v in self.schedules[ref].items() if k != 'id'}
            return {k: v for k, v in ref.items() if k != 'evidence_ids'} if isinstance(ref, dict) and 'rules' in ref else ref
        def entry(e):
            out = {k: v for k, v in e.items() if k not in ('demand_id', 'evidence_id')}
            for key in ('schedule_id', 'value'):
                if key in out:
                    out[key] = schedule(out[key])
            return out
        out = {k: v for k, v in record.items() if k != 'evidence_ids'}
        out['loads'] = [entry(l) for l in record['loads']]
        out['parameters'] = {k: entry(p) for k, p in record['parameters'].items()}
        return out

    def test_layout_and_canonical_format(self):
        for (template, building_type), built in self.built.items():
            root = 'commercial/90-1-2019/' + self.module.slug(building_type) + '/'
            self.assertIn(root + 'schedules.json', built.files)
            self.assertIn('evidence/commercial/90-1-2019/' + self.module.slug(building_type) + '.json', built.files)
            self.assertIn('evidence/glossary.json', built.files)
            for path, data in built.files.items():
                self.assertLess(len(data), 25_000_000, path)
                self.assertNotIn(b'\r', data, path)
                self.assertTrue(data.endswith(b'\n'), path)
                if '/programs/' in path:
                    self.assertRegex(path, r'/programs/(source|department|general)/[^/]+\.json$')
                    value = json.loads(data)
                    self.assertEqual(data, (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + '\n').encode())
                else:  # tables: one record per line, inside optional named sections
                    lines = data.decode().splitlines()
                    self.assertEqual((lines[0], lines[-1]), ('{', '}'))
                    for line in lines[1:-1]:
                        self.assertRegex(line, r'^(\},?|"[^"]+": \{|"[^"]+":[\[{"0-9tfn-].*)$', path)
                    json.loads(data)

    def test_readable_ids_hash_their_content(self):
        for built in self.built.values():
            for path, data in built.files.items():
                if '/programs/' not in path:
                    continue
                record = json.loads(data)
                self.assertRegex(record['id'], ID)
                self.assertTrue(path.endswith('/' + record['id'] + '.json'))
                content = {k: v for k, v in record.items() if k not in ('id', 'name')}
                self.assertEqual(record['id'][-6:], hashlib.sha256(canonical(content).encode()).hexdigest()[:6])
            table = json.loads(built.files[next(p for p in built.files if p.endswith('/schedules.json'))])
            for sid, schedule in table['schedules'].items():
                self.assertRegex(sid, ID)
                content = {k: v for k, v in schedule.items() if k not in ('name',)}
                self.assertEqual(sid[-6:], hashlib.sha256(canonical(content).encode()).hexdigest()[:6])

    def test_build_is_deterministic(self):
        folder = FOLDERS[0]
        self.assertEqual(self.built[folder].files, self.module.build_folder(self.sources, *folder).files)

    def test_filled_export_equals_reviewed_definition(self):
        for folder in FOLDERS:
            built, suite = self.built[folder], self.suites[folder]
            for record in self.folder_sources(folder):
                new_id = built.ids[record['id']]
                reviewed = self.twins.get(record['id'], record)
                got, expected = suite.export(new_id, 'filled'), self.expected(reviewed, built.ids, new_id)
                if record['derivation'] == 'composed':  # a mix keeps one identity across versions
                    got, expected = self.semantic(got, suite), self.semantic(expected, suite)
                self.assertEqual(got, expected, record['name'])

    def source_zero_targets(self, record):
        """Targets whose every source-to-reviewed change is a source_zero resolution."""
        reviewed = self.twins.get(record['id'])
        if not reviewed:
            return set()
        bases = {}
        for rid in reviewed.get('reviewed_resolution_ids') or []:
            r = self.resolutions[rid]
            for t in self.module.addressed(r['field']):
                bases.setdefault(t, set()).add(r['basis'])
        return {t for t, b in bases.items() if b == {'source_zero'}}

    def test_source_export_keeps_source_values_except_source_zero(self):
        checked = 0
        for folder in FOLDERS:
            built, suite = self.built[folder], self.suites[folder]
            for record in self.folder_sources(folder):
                if record['derivation'] == 'composed':
                    continue
                new_id = built.ids[record['id']]
                expected = self.expected(record, built.ids, new_id)
                zero = self.source_zero_targets(record)
                if zero:
                    reviewed = self.expected(self.twins[record['id']], built.ids, new_id)
                    loads = {l['quantity']: l for l in reviewed['loads']}
                    expected['loads'] = [loads[l['quantity']] if ('load', l['quantity']) in zero else l for l in expected['loads']]
                    for kind, key in zero:
                        if kind == 'parameter':
                            expected['parameters'][key] = reviewed['parameters'][key]
                    checked += 1
                    expected['evidence_ids'] = sorted(set(expected['evidence_ids']) | {
                        l['evidence_id'] for l in expected['loads']})
                self.assertEqual(suite.export(new_id, 'source'), expected, record['name'])
        self.assertGreater(checked, 0)

    def test_mixes_reference_members_and_store_both_versions(self):
        for folder in FOLDERS:
            built, suite = self.built[folder], self.suites[folder]
            for record in self.folder_sources(folder):
                if record['derivation'] != 'composed':
                    continue
                stored = suite.programs[built.ids[record['id']]]
                members = stored['composition']['members']
                self.assertAlmostEqual(sum(m['weight'] for m in members), 1.0, places=9)
                for m in members:
                    self.assertIn(m['program_id'], suite.programs)
                    self.assertEqual(suite.programs[m['program_id']]['mode'], 'source')
                self.assertNotIn('source_components', json.dumps(stored))
                if folder == FOLDERS[0]:  # Hospital has no source-zero values: the source mix is unchanged
                    expected = self.expected(record, built.ids, stored['id'])
                    self.assertEqual(self.semantic(suite.export(stored['id'], 'source'), suite),
                                     self.semantic(expected, suite), record['name'])
                for version in ('source', 'filled'):
                    for load in suite.export(stored['id'], version)['loads']:
                        ids = [c['program_id'] for c in load['source_components']]
                        self.assertEqual(ids, [m['program_id'] for m in members])

    def test_fillings_carry_rule_basis_and_evidence(self):
        bases = set()
        for built in self.built.values():
            glossary = json.loads(built.files['evidence/glossary.json'])
            evidence = json.loads(built.files[next(p for p in built.files if p.startswith('evidence/commercial/'))])
            for suite_program in self.module.read_folder(built.files).programs.values():
                for filling in self.module.fillings(suite_program):
                    bases.add(filling['basis'])
                    self.assertIn(filling['basis'], ('research_assumption', 'executed_upstream'))
                    for rule in filling['rules']:
                        self.assertIn(rule, {n['rule'] for n in glossary['rule_notes'].values()})
                    for eid in filling.get('evidence', []):
                        self.assertIn(eid, evidence)
        self.assertEqual(bases, {'research_assumption', 'executed_upstream'})

    def test_constant_fillings_are_literals(self):
        hospital = self.built[FOLDERS[0]]
        text = b''.join(d for p, d in hospital.files.items() if '/programs/' in p)
        self.assertIn(b'"constant": 0', text)
        table = json.loads(hospital.files['commercial/90-1-2019/hospital/schedules.json'])
        self.assertFalse(any('resolution' in s.get('name', '') for s in table['schedules'].values()))

    def test_schedule_table_round_trips_definition_schedules(self):
        for built in self.built.values():
            suite = self.module.read_folder(built.files)
            for old, new in built.ids.items():
                if old in self.schedules and isinstance(new, str):
                    original = {k: v for k, v in self.schedules[old].items() if k != 'id'}
                    self.assertEqual(suite.schedule(new), original, old)

    def test_unresolved_fields_keep_null_with_reason(self):
        found = 0
        for folder in FOLDERS:
            built, suite = self.built[folder], self.suites[folder]
            by_source = {p['source_id']: p for p in self.folder_sources(folder)}
            glossary = json.loads(built.files['evidence/glossary.json'])
            for row in self.unresolved:
                record = by_source.get(row['record_id'])
                if not record:
                    continue
                kind, key = self.module.target(row['field'])
                stored = suite.programs[built.ids[record['id']]]
                load = next((l for l in stored['loads'] if l['quantity'] == key), None)
                if load is None:  # no such load: the reason is kept on the record
                    self.assertIn(stored['unresolved'][row['field']], glossary['unresolved'])
                else:
                    self.assertIsNone(load['schedule_id'])
                    self.assertIn(load['unresolved'], glossary['unresolved'])
                found += 1
        self.assertGreater(found, 0)

    def test_evidence_and_references_stay_in_folder(self):
        for (template, building_type), built in self.built.items():
            evidence = json.loads(built.files['evidence/commercial/90-1-2019/' + self.module.slug(building_type) + '.json'])
            glossary = json.loads(built.files['evidence/glossary.json'])
            text = b''.join(d for p, d in built.files.items() if p.startswith('commercial/')).decode()
            for eid in set(re.findall(r'(?:evidence|provenance)-[0-9a-f]{20,24}', text)):
                self.assertIn(eid, evidence)
            for row in evidence.values():
                self.assertIn(row['interpretation'], glossary['interpretations'])
                self.assertIn(row['transformation'], glossary['transformations'])
                if row['source_file']:
                    self.assertIn(row['source_file'], glossary['source_files'])
            prefix = '90-1-2019.' + self.module.slug(building_type) + '.'
            for ref in set(re.findall(r'"(90-1-2019\.[a-z0-9.-]+\.[0-9a-f]{6})"', text)):
                self.assertTrue(ref.startswith(prefix), ref)
            self.assertNotRegex(text, r'"(?:mixed-)?schedule-[0-9a-f]{20,24}"')
            self.assertNotRegex(text, r'"program-[0-9a-f]{24}"')


if __name__ == '__main__':
    unittest.main()
