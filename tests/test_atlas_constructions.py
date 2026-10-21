"""ADR 0036 construction suites: one file per set, one library per template, both exports unchanged."""
import hashlib
import json
import re
import unittest

FOLDERS = (('90.1-2019', 'MediumOffice'), ('90.1-2019', 'Office'), ('DOE Ref Pre-1980', 'Warehouse'))


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


class AtlasConstructionSuiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from scripts import atlas_constructions, atlas_format
        from scripts.construction_foundation_release import export_pair
        cls.module, cls.format = atlas_constructions, atlas_format
        cls.sources = atlas_constructions.load_sources()
        cls.built = atlas_constructions.build_folders(cls.sources, FOLDERS)
        cls.suite = atlas_constructions.read_files(cls.built.files)
        cls.documents = {cid: export_pair(cid, release=cls.sources.release) for cid in cls.built.contexts}

    def test_layout_and_canonical_format(self):
        files = self.built.files
        for template, building_type in FOLDERS:
            t, b = self.format.slug(template), self.format.slug(building_type)
            self.assertTrue(any(p.startswith(f'commercial/{t}/{b}/constructions/') for p in files), (t, b))
            self.assertIn(f'evidence/commercial/{t}/{b}.json', files)
            for table in ('assemblies', 'materials'):
                self.assertIn(f'commercial/{t}/library/{table}.json', files)
            self.assertIn(f'evidence/commercial/{t}/library.json', files)
        for path, data in files.items():
            self.assertLess(len(data), 25_000_000, path)
            self.assertNotIn(b'\r', data, path)
            if '/constructions/' in path:
                self.assertEqual(data, (json.dumps(json.loads(data), indent=2, sort_keys=True, ensure_ascii=False)+'\n').encode())
            else:
                lines = data.decode().splitlines()
                self.assertEqual((lines[0], lines[-1]), ('{', '}'))
                for line in lines[1:-1]:
                    self.assertRegex(line, r'^"[^"]+":[\[{"0-9tfn-].*$', path)

    def test_exports_equal_current_documents(self):
        self.assertEqual(len(self.built.contexts), 21+126+19)
        for cid, (set_id, key) in self.built.contexts.items():
            detailed, unified = self.documents[cid]
            ids = self.built.ids[set_id.split('.')[0]]  # IDs are per template: shared materials are copied
            self.assertEqual(self.suite.export(set_id, key, 'detailed'), self.format.translate(detailed, ids), cid)
            self.assertEqual(self.suite.export(set_id, key, 'unified'), self.format.translate(unified, ids), cid)

    def test_readable_ids_hash_their_content(self):
        set_ids = sorted({json.loads(d)['id'] for p, d in self.built.files.items() if '/constructions/' in p}, key=len, reverse=True)
        for path, data in self.built.files.items():
            if '/constructions/' in path:
                record = json.loads(data)
                self.assertRegex(record['id'], r'^[a-z0-9-]+\.[a-z0-9-]+\.[a-z0-9-]+\.[0-9a-f]{6}$')
                self.assertTrue(path.endswith('/'+record['id']+'.json'))
                text = data.decode()
                for set_id in set_ids:  # every set ID, its own or one it cites, hashes as '@set'
                    text = text.replace(set_id, '@set')
                content = json.loads(text)
                content = {k: v for k, v in content.items() if k not in ('id', 'name')}
                self.assertEqual(record['id'][-6:], hashlib.sha256(canonical(content).encode()).hexdigest()[:6])
            elif '/library/' in path:
                template = path.split('/')[1]
                for rid, record in json.loads(data).items():
                    self.assertRegex(rid, '^'+re.escape(template)+r'\.[a-z0-9-]+\.[0-9a-f]{6}$')
                    content = {k: v for k, v in record.items() if k not in ('id', 'name')}
                    self.assertEqual(rid[-6:], hashlib.sha256(canonical(content).encode()).hexdigest()[:6])

    def test_library_is_shared_within_a_template_only(self):
        libraries = {p.split('/')[1]: {**json.loads(self.built.files[p]),
                                        **json.loads(self.built.files[p.replace('assemblies', 'materials')])}
                     for p in self.built.files if p.endswith('/library/assemblies.json')}
        self.assertEqual(set(libraries), {'90-1-2019', 'doe-ref-pre-1980'})
        self.assertFalse(set(libraries['90-1-2019']) & set(libraries['doe-ref-pre-1980']))
        used = {}
        for path, data in self.built.files.items():
            if '/constructions/' in path:
                for ref in set(re.findall(r'"(90-1-2019\.[a-z0-9-]+\.[0-9a-f]{6})"', data.decode())) & set(libraries['90-1-2019']):
                    used.setdefault(ref, set()).add(path.split('/')[2])
        self.assertTrue(any(len(folders) > 1 for folders in used.values()), 'Medium Office and Office share library records')

    def test_set_files_store_common_fields_once(self):
        stored = sum(len(d) for p, d in self.built.files.items() if '/constructions/' in p or '/library/' in p)
        standalone = sum(len(canonical(doc)) for pair in self.documents.values() for doc in pair)
        self.assertLess(stored, standalone * 0.3)
        for path, data in self.built.files.items():
            if '/constructions/' in path:
                record = json.loads(data)
                self.assertEqual(set(record['common']), {'detailed', 'unified'})
                for context in record['contexts'].values():
                    for representation in ('detailed', 'unified'):
                        stored = context[representation]
                        fields = set(stored['fields']) | {path.split('/')[0] for path in stored['refs']}
                        self.assertFalse(fields & set(record['common'][representation]['fields']))
                        for vid in stored['refs'].values():
                            self.assertIn(vid, record['values'])

    def test_build_is_deterministic(self):
        again = self.module.build_folders(self.sources, FOLDERS[2:])
        for path, data in again.files.items():
            self.assertEqual(data, self.built.files[path], path)

    def test_merges_with_the_program_build(self):
        from scripts import atlas_programs
        programs = atlas_programs.build_folder(atlas_programs.load_sources(), '90.1-2019', 'MediumOffice')
        merged = self.format.merge(programs.files, self.built.files)
        evidence = json.loads(merged['evidence/commercial/90-1-2019/medium-office.json'])
        self.assertTrue(any(k.startswith('evidence-') for k in evidence))
        self.assertTrue(any(k.startswith(('construction-evidence-', 'selector-evidence-', 'foundation-evidence-')) for k in evidence))
        glossary = json.loads(merged['evidence/glossary.json'])
        self.assertIn('interpretations', glossary)
        with self.assertRaises(ValueError):
            self.format.merge({'evidence/x.json': b'{\n"a":1\n}\n'}, {'evidence/x.json': b'{\n"a":2\n}\n'})


if __name__ == '__main__':
    unittest.main()
