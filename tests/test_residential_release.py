"""Release 1.4.0: the commercial files of 1.3.0 unchanged, plus the residential tree (ADR 0038, 0041, 0042)."""
import json
import os
import unittest

from scripts import atlas_minor_release
from scripts.common import ROOT

RELEASE = atlas_minor_release.target('1.4.0')
LIMIT = 25_000_000


@unittest.skipUnless((RELEASE/'manifest.json').exists(), 'release 1.4.0 not written')
class Release140Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from scripts.atlas_exports import Release
        cls.listed = atlas_minor_release.verify('1.4.0')
        cls.release = Release(release='1.4.0')

    @classmethod
    def tearDownClass(cls):
        # unittest keeps every test class until the run ends; free the release state.
        del cls.listed, cls.release

    def test_release_holds_release_1_3_0_unchanged(self):
        earlier = json.loads((ROOT/'data/atlas-releases/v1.3.0/manifest.json').read_text())
        changed = [p for p, e in earlier['files'].items() if self.listed['files'].get(p) != e]
        self.assertEqual(sorted(changed), ['README.md', 'evidence/glossary.json'])
        self.assertEqual(self.listed['deleted'], earlier['deleted'])
        glossary = json.loads((RELEASE/'evidence/glossary.json').read_text(encoding='utf-8'))
        before = json.loads((ROOT/'data/atlas-releases/v1.3.0/evidence/glossary.json').read_text(encoding='utf-8'))
        for section, table in before.items():
            self.assertEqual({k: glossary[section][k] for k in table}, table, section)

    def test_residential_tree_counts_and_sizes(self):
        counts = self.listed['counts']
        self.assertEqual((counts['residential_folders'], counts['residential_programs'], counts['residential_construction_sets'],
                          counts['residential_construction_contexts']), (25, 73, 59, 1153))
        self.assertEqual(self.listed['scope'], 'commercial and residential')
        for path, entry in self.listed['files'].items():
            self.assertLess(entry['bytes'], LIMIT, path)
        folders = {p.split('/')[1] for p in self.listed['files'] if p.startswith('residential/')}
        self.assertEqual(folders, {'resstock-sdr', 'hud-code', 'doe-final-rule', *(f'iecc-{e}' for e in
                                                                                  ('2006', '2009', '2012', '2015', '2018', '2021', '2024'))})
        notices = {p for p in self.release.files if p.startswith('notices/')}
        self.assertLessEqual({'notices/resstock.txt', 'notices/pnnl-prototypes.txt'}, notices)

    def test_commercial_programs_export_as_5_2_0(self):
        program_id = next(p for p in self.release.program_ids() if p.startswith('90-1-2019.medium-office.source.'))
        document = self.release.program(program_id, 'filled')
        self.assertEqual((document['schema_version'], document['source']['release']), ('5.2.0', 'atlas-release-1.4.0'))

    def test_dwelling_programs_export_as_5_3_0(self):
        dwellings = self.release.dwellings
        resstock = next(p for p in dwellings.program_ids() if p.startswith('resstock-sdr.multifamily-5-plus-low-rise.'))
        document = self.release.program(resstock, 'filled')
        self.assertEqual((document['schema_version'], document['source']['release']), ('5.3.0', 'atlas-release-1.4.0'))
        self.assertIn('Geometry Building Number Units MF', document['dwelling']['building_context'])
        self.assertTrue(document['water_heating'])
        iecc = next(p for p in dwellings.program_ids() if p.startswith('iecc-2021.single-family.gas-appliances.'))
        document = self.release.program(iecc, 'source')
        roles = {l['end_use']: l.get('role') for l in document['loads']}
        self.assertEqual(roles['iecc_adj'], 'reference_design_adjustment')
        self.assertTrue(any('applies_with' in l for l in document['loads']))
        with self.assertRaises(ValueError):
            self.release.program(iecc, 'filled')
        from scripts.prototype_dwellings import document as resolved
        one = resolved(dwellings, iecc, 'source', {'climate': '1A-tropical-semi-conditioned', 'foundation': 'slab', 'heating': 'gasfurnace'})
        self.assertFalse(any('applies_with' in l for l in one['loads']))
        services = {s['loads'][0]['end_use']: s['loads'][0]['value'] for s in one['shared_services']}
        self.assertAlmostEqual(services['uncond_living_hardwired_lighting'] + services['uncond_living_plug_in_lighting'], 168.995, 3)
        self.assertAlmostEqual(services['addl_iecc_adj'], 252.6998, 3)
        mh = next(p for p in dwellings.program_ids() if p.startswith('doe-final-rule.multi-section.'))
        document = self.release.program(mh, 'source')
        self.assertEqual(document['dwelling']['tier'], 'tier2')
        self.assertEqual({l['basis'] for l in document['loads'] if l['type'] == 'lighting'}, {'floor_area'})

    def test_construction_exports(self):
        dwellings = self.release.dwellings
        resstock = dwellings.stored(next(p for p in dwellings.program_ids() if p.startswith('resstock-sdr.single-family-detached.')))
        set_id = resstock['construction_set_id']
        [key] = self.release.constructions.sets[set_id]['contexts']
        self.assertEqual(self.release.construction(set_id, key, 'detailed')['schema_version'], '4.2.0')
        self.assertEqual(self.release.construction(set_id, key, 'unified')['schema_version'], '3.1.0')
        iecc = dwellings.stored(next(p for p in dwellings.program_ids() if p.startswith('iecc-2018.multifamily.')))
        document = self.release.construction(iecc['construction_set_id'], '5-a.heatedbsmt', 'detailed')
        self.assertEqual((document['schema_version'], document['kind']), ('1.0.0', 'source_model_construction'))
        self.assertEqual(len({r['unit'] for r in document['infiltration']['effective_leakage_area'] if r['unit']}), 18)
        mh = dwellings.stored(next(p for p in dwellings.program_ids() if p.startswith('hud-code.single-section.')))
        contexts = json.loads(next(d for p, d in self.release.files.items() if p.endswith(mh['construction_set_id']+'.json')))['contexts']
        self.assertEqual(sorted(k for k in contexts if k.startswith('3-a')),
                         ['3-a.atlanta', '3-a.birmingham', '3-a.charleston', '3-a.jackson', '3-a.memphis'])


@unittest.skipUnless((RELEASE/'manifest.json').exists() and os.environ.get('ATLAS_RELEASE_CHECK'),
                     'set ATLAS_RELEASE_CHECK=1 to rebuild release 1.4.0 (about 5 minutes)')
class Release140CheckTests(unittest.TestCase):
    def test_release_reproduces_byte_for_byte(self):
        atlas_minor_release.check('1.4.0')


if __name__ == '__main__':
    unittest.main()
