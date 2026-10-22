"""ADR 0036 systems: HVAC systems, services and water records in their folder, curves and rules per template."""
import hashlib
import json
import re
import unittest

from scripts.common import load_json

FOLDERS = (('90.1-2019', 'Outpatient'), ('90.1-2019', 'SmallHotel'), ('90.1-2019', 'HighriseApartment'))
DEFINITIONS = 'data/definition-releases/v0.1.1/'


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


class AtlasSystemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from scripts import atlas_format, atlas_programs, atlas_systems
        cls.format, cls.module = atlas_format, atlas_systems
        cls.sources = atlas_systems.load_sources()
        program_sources = atlas_programs.load_sources()
        cls.programs = {f: atlas_programs.build_folder(program_sources, *f) for f in FOLDERS}
        cls.built = {f: atlas_systems.build_folder(cls.sources, *f, cls.programs[f]) for f in FOLDERS}
        cls.suites = {f: atlas_systems.read_files(cls.format.merge(cls.programs[f].files, b.files)) for f, b in cls.built.items()}
        cls.hvac = [h for h in load_json(DEFINITIONS + 'hvac_systems.json')]
        cls.components = {c['id']: c for c in load_json(DEFINITIONS + 'components.json')}
        cls.services = load_json(DEFINITIONS + 'services.json')
        cls.water = load_json('data/water-reporting-releases/v0.1.0/water-reporting.json')
        cls.schedules = {s['id']: s for s in load_json(DEFINITIONS + 'schedules.json')}
        cls.schedules.update({s['id']: s for s in cls.water['schedules']})

    def in_folder(self, rows, folder):
        return [r for r in rows if (r['template'], r['building_type']) == folder]

    def test_layout(self):
        for (template, building_type), built in self.built.items():
            t, b = self.format.slug(template), self.format.slug(building_type)
            for table in ('systems', 'components', 'services', 'water', 'schedules'):
                self.assertIn(f'commercial/{t}/{b}/{table}.json', built.files)
            for table in ('curves', 'performance-rules'):
                self.assertIn(f'commercial/{t}/library/{table}.json', built.files)
            self.assertIn(f'evidence/commercial/{t}/{b}.json', built.files)

    def test_records_equal_the_definition_and_water_records(self):
        for folder in FOLDERS:
            built, suite = self.built[folder], self.suites[folder]
            hvac = self.in_folder(self.hvac, folder)
            self.assertTrue(hvac)
            for system in hvac:
                self.assertEqual(suite.record('systems', built.ids[system['id']]), self.format.translate(system, built.ids))
            closure = {c for s in hvac for c in self.closure(s)}
            for component in closure:
                self.assertEqual(suite.record('components', built.ids[component]),
                                 self.format.translate(self.components[component], built.ids), component)
            for service in self.in_folder(self.services, folder):
                self.assertEqual(suite.record('services', built.ids[service['id']]), self.format.translate(service, built.ids))
            for row in self.in_folder(self.water['programs'], folder):
                self.assertEqual(suite.water('programs', built.ids[row['program_id']]), self.format.translate(row, built.ids))
                reference = self.water['reference_programs'].get(row['program_id'])
                if reference:
                    self.assertEqual(suite.water('references', built.ids[row['program_id']]), self.format.translate(reference, built.ids))
            for row in self.in_folder(self.water['services'], folder):
                self.assertEqual(suite.water('services', row['path_id']), self.format.translate(row, built.ids))

    def closure(self, system):
        todo, seen = set(system['component_ids']), set()
        while todo:
            c = todo.pop()
            if c not in seen:
                seen.add(c)
                todo |= set(re.findall(r'(?:component|curve|performance-rule)-[0-9a-f]{20,24}', json.dumps(self.components[c]))) & self.components.keys()
        return seen

    def test_curves_and_rules_live_in_the_template_library(self):
        for (template, building_type), built in self.built.items():
            t, b = self.format.slug(template), self.format.slug(building_type)
            library = {**json.loads(built.files[f'commercial/{t}/library/curves.json']),
                       **json.loads(built.files[f'commercial/{t}/library/performance-rules.json'])}
            local = json.loads(built.files[f'commercial/{t}/{b}/components.json'])
            self.assertTrue(library)
            self.assertFalse(any(r['role'] in ('performance_curve', 'conditional_performance_rule') for r in local.values()))
            for rid, record in library.items():
                self.assertRegex(rid, '^'+re.escape(t)+r'\.[a-z0-9-]+\.[0-9a-f]{6}$')
                self.assertEqual(rid[-6:], hashlib.sha256(canonical({k: v for k, v in record.items() if k not in ('id', 'name')}).encode()).hexdigest()[:6])
        tables = ('curves', 'performance-rules')
        per_folder = [{k for t in tables for k in json.loads(b.files[f'commercial/90-1-2019/library/{t}.json'])} for b in self.built.values()]
        merged = self.format.merge(*[b.files for b in self.built.values()])
        self.assertEqual({k for t in tables for k in json.loads(merged[f'commercial/90-1-2019/library/{t}.json'])}, set().union(*per_folder))
        self.assertTrue(any(a & b for i, a in enumerate(per_folder) for b in per_folder[i+1:]), 'Library records are shared between folders')

    def test_readable_ids_hash_their_content(self):
        for (template, building_type), built in self.built.items():
            t, b = self.format.slug(template), self.format.slug(building_type)
            systems = set(json.loads(built.files[f'commercial/{t}/{b}/systems.json']))
            for table in ('systems', 'components', 'services'):
                for rid, record in json.loads(built.files[f'commercial/{t}/{b}/{table}.json']).items():
                    self.assertRegex(rid, '^'+re.escape(f'{t}.{b}.')+r'[a-z0-9-]+\.[0-9a-f]{6}$')
                    # A record's own ID hashes as '@self'; a component's back-reference to its system as '@system'.
                    text = canonical({k: v for k, v in record.items() if k not in ('id', 'name')}).replace(rid, '@self')
                    if table == 'components':
                        for system in systems:
                            text = text.replace(system, '@system')
                    self.assertEqual(rid[-6:], hashlib.sha256(text.encode()).hexdigest()[:6], rid)

    def test_programs_and_schedules_are_referenced_by_their_new_ids(self):
        for folder in FOLDERS:
            built, suite = self.built[folder], self.suites[folder]
            programs = {json.loads(d)['id'] for p, d in self.programs[folder].files.items() if '/programs/' in p}
            for service in self.in_folder(self.services, folder):
                stored = suite.record('services', built.ids[service['id']])
                self.assertTrue(set(stored['beneficiary_program_ids']) <= programs)
            for old, new in built.ids.items():
                if old in self.schedules and isinstance(new, str):
                    original = {k: v for k, v in self.schedules[old].items() if k != 'id'}
                    self.assertEqual(suite.schedule(new), original, old)
            text = b''.join(d for p, d in built.files.items() if p.startswith('commercial/')).decode()
            self.assertNotRegex(text, r'"(?:hvac_system|component|curve|performance-rule|service)-[0-9a-f]{20,24}"')
            self.assertNotRegex(text, r'"(?:schedule|water_reporting_schedule)-[0-9a-f]{20,24}"')

    def test_evidence_is_complete_and_merges_with_programs(self):
        for (template, building_type), built in self.built.items():
            t, b = self.format.slug(template), self.format.slug(building_type)
            merged = self.format.merge(self.programs[(template, building_type)].files, built.files)
            evidence = {**json.loads(merged[f'evidence/commercial/{t}/{b}.json']), **json.loads(merged[f'evidence/commercial/{t}/library.json'])}
            text = b''.join(d for p, d in built.files.items() if p.startswith('commercial/')).decode()
            for eid in set(re.findall(r'(?:evidence|provenance|completion_evidence)-[0-9a-f]{20,24}', text)):
                self.assertIn(eid, evidence)
            glossary = json.loads(merged['evidence/glossary.json'])
            for row in evidence.values():
                if 'interpretation' in row:
                    self.assertIn(row['interpretation'], glossary['interpretations'])

    def test_build_is_deterministic(self):
        folder = FOLDERS[0]
        self.assertEqual(self.built[folder].files, self.module.build_folder(self.sources, *folder, self.programs[folder]).files)


if __name__ == '__main__':
    unittest.main()
