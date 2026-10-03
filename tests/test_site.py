"""Site boundaries: reject tampering, preserve values, escape evidence and URLs."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from scripts.common import ROOT, load_atlas, load_json


class SiteTests(unittest.TestCase):
    def test_executed_profiles_are_separate_from_frozen_source_values(self):
        site=self.site_module()
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'docs'
            site.generate_site([ROOT/'data/releases/v0.2.0'],target,pilot=True)
            index=load_json(target/'releases/v0.2.0/catalogue.json')
            residential=next(r for r in index['entries'] if r['kind']=='residential_archetypes')
            packet=load_json(target/residential['download'])
            self.assertFalse(packet['record']['simulation_ready'])
            self.assertIn('resolution_supplement',packet)
            self.assertIn('profile',packet['resolution_supplement'])
            page=(target/residential['path']).read_text()
            self.assertIn('atlas-residential-profile',page)
            self.assertIn('Station-proxy',page)
            profile=packet['resolution_supplement']['profile']
            self.assertTrue((target/profile['download']).exists())
            self.assertIn('nominal',page)

    def site_module(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.site'),
                             'The verified site generator has not been implemented')
        from scripts import site
        return site

    def test_tampered_release_is_rejected_before_output(self):
        site = self.site_module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/'metadata.json').write_text('{}')
            (root/'manifest.json').write_text(json.dumps({'files': {
                'metadata.json': {'sha256': '0'*64, 'size_bytes': 2}}}))
            with self.assertRaisesRegex(ValueError, 'integrity'):
                site.read_release(root)

    def test_pilot_values_provenance_and_static_downloads(self):
        site = self.site_module()
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)/'docs'
            result = site.generate_site([ROOT/'data/releases/v0.2.0'], target, pilot=True)
            index = load_json(target/'releases/v0.2.0/catalogue.json')
            office = next(r for r in index['entries'] if r['kind'] == 'programs'
                          and r['building'] == 'MediumOffice' and r['program'] == 'office')
            page = (target/office['path']).read_text()
            self.assertIn('0.82', page)  # Original W/ft2 in field provenance
            self.assertIn('W/m2', page)
            self.assertIn('Unknown', page)
            self.assertIn('Original value', page)
            self.assertIn('Extraction date', page)
            self.assertIn('Source locator', page)
            record = load_json(target/office['download'])
            self.assertAlmostEqual(record['record']['lighting_W_m2'], 0.82/0.09290304)
            self.assertEqual(record['release'], 'v0.2.0')
            self.assertTrue(record['provenance']['fields'])
            self.assertEqual(result['releases']['v0.2.0']['commercial_overviews'], 1)
            residential = next(r for r in index['entries'] if r['kind'] == 'residential_archetypes')
            rp = (target/residential['path']).read_text()
            self.assertIn('Profiles unavailable', rp)
            self.assertIn('runtime_gaps', rp)
            with zipfile.ZipFile(target/'releases/v0.2.0/downloads/snapshot.zip') as archive:
                manifest = load_json(ROOT/'data/releases/v0.2.0/manifest.json')
                for name in manifest['files']:
                    self.assertEqual(archive.read(name), (ROOT/'data/releases/v0.2.0'/name).read_bytes())

    def test_full_index_counts_and_climate_semantics(self):
        site = self.site_module()
        a = load_atlas(ROOT/'data/releases/v0.2.0')
        entries = site.catalogue_entries(a, 'v0.2.0')
        self.assertEqual(sum(r['kind'] == 'buildings' for r in entries), 83)
        self.assertEqual(sum(r['kind'] == 'residential_archetypes' for r in entries), 41)
        self.assertEqual(sum(r['kind'] == 'programs' for r in entries), 768)
        self.assertEqual(sum(r['kind'] == 'schedules' for r in entries), 569)
        self.assertEqual(len({r['path'] for r in entries}), len(entries))
        p = next(r for r in entries if r['kind'] == 'programs')
        self.assertEqual(p['climate'], 'Unspecified; program is climate-independent')
        e = next(r for r in entries if r['kind'] == 'envelope_components')
        self.assertTrue(e['climate'].startswith('ClimateZone '))
        self.assertEqual(e['climate_basis'], 'Conditional envelope applicability')

    def test_source_text_is_escaped_and_null_is_not_zero(self):
        site = self.site_module()
        self.assertEqual(site.display_value(None), 'Unknown / not reported')
        self.assertIn('0', site.display_value(0))
        self.assertNotIn('<script>', site.display_value('<script>alert(1)</script>'))
        row = {'id': 'program-abc', 'building_type': '<script>', 'program': 'a|b',
               'template': '90.1-2013', 'source_family': 'code_prototype_rules',
               'lighting_W_m2': None}
        out = site.render_fields(row, {'lighting_W_m2': 'W/m2'}, {})
        self.assertNotIn('<script>', out)
        self.assertIn('Unknown', out)

    def test_generator_does_not_modify_frozen_data(self):
        site = self.site_module()
        a = load_atlas(ROOT/'data/releases/v0.2.0')
        original = copy.deepcopy(a)
        site.catalogue_entries(a, 'v0.2.0')
        self.assertEqual(a, original)

    def test_output_guard_protects_sources_and_unrelated_build_files(self):
        site = self.site_module()
        self.assertTrue(hasattr(site, 'validate_output'), 'Output guard is not implemented')
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            protected = root/'build/screenshots'
            protected.mkdir(parents=True)
            (protected/'keep.png').write_bytes(b'keep')
            with patch.object(site, 'ROOT', root):
                for target in [root/'data/releases/v0.2.0/site', root/'website/new', protected, root/'build']:
                    with self.assertRaises(ValueError):
                        site.validate_output(target, [root/'data/releases/v0.2.0'])
                site.validate_output(root/'build/site-docs', [root/'data/releases/v0.2.0'])
                self.assertEqual((protected/'keep.png').read_bytes(), b'keep')

    def test_shared_schedule_context_preserves_exact_source_pairs(self):
        site = self.site_module()
        entries = site.catalogue_entries(load_atlas(ROOT/'data/releases/v0.2.0'), 'v0.2.0')
        row = next(r for r in entries if r['id'] == 'schedule-9841fa9f62ff202db619')
        self.assertIn('referenced_contexts', row)
        pairs = {(r['building'], r['template']) for r in row['referenced_contexts']}
        self.assertIn(('HighriseApartment', '90.1-2007'), pairs)
        self.assertIn(('MidriseApartment', '90.1-2019'), pairs)
        self.assertNotIn(('HighriseApartment', '90.1-2019'), pairs)


if __name__ == '__main__':
    unittest.main()
