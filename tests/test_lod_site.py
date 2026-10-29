"""The zoning-recommendation data drop and its pages (ADR 0050)."""
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import jsonschema

from scripts import lod_site, site_check, site_store, suite_site
from scripts.common import ROOT
from scripts.site_render import Links

SCHEMA = ROOT/'schemas/lod-recommendations-v1.schema.json'


def site_stub(target):
    site = suite_site.Site.__new__(suite_site.Site)
    site.target, site.written, site.links, site.summaries, site.store, site.zoning_of = Path(target), set(), Links(), {}, site_store.Store(target), {}
    return site


class DataDropTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA.read_text(encoding='utf-8'))
        cls.provenance = json.loads((lod_site.DROP/lod_site.PROVENANCE).read_text(encoding='utf-8'))

    def test_files_validate_against_the_bemgen_schema(self):
        validator = jsonschema.Draft202012Validator(self.schema)
        for name in (lod_site.MAIN, lod_site.HT):
            data = json.loads((lod_site.DROP/name).read_text(encoding='utf-8'))
            self.assertEqual(sorted(validator.iter_errors(data), key=str), [], name)

    def test_provenance_names_every_file_with_its_digest_and_the_pins(self):
        files = self.provenance['files']
        self.assertEqual(set(files), {lod_site.MAIN, lod_site.HT})
        for name, entry in files.items():
            data = (lod_site.DROP/name).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), entry['sha256'], name)
            self.assertNotIn(b'\r\n', data)
            self.assertEqual(len(json.loads(data)['entries']), entry['entries'], name)
            for key in ('stage', 'suite', 'run', 'source_sha256'):
                self.assertTrue(entry.get(key), f'{name}: {key}')
        self.assertEqual(self.provenance['drop'], 1)
        self.assertEqual(self.provenance['bemgen']['report_commit'], 'b29931c80254d15fa8362b57a9404d7e4da6c5ab')
        self.assertEqual(self.provenance['bemgen']['schema_sha256'], hashlib.sha256(SCHEMA.read_bytes()).hexdigest())
        self.assertEqual(self.provenance['atlas_inputs'], {**self.provenance['atlas_inputs'], 'release': '2.0.0',
                                                           'commit': '96a2e928ba60be6b54aa68d149e8de4222595035'})
        self.assertIn('CC BY 4.0', self.provenance['licence'])

    def test_the_threshold_is_the_one_recorded_in_every_file(self):
        drop = lod_site.Drop()
        self.assertEqual(drop.main['threshold'], self.provenance['threshold'])
        self.assertEqual(drop.ht['threshold'], self.provenance['threshold'])
        self.assertEqual((drop.threshold['cvrmse_pct'], drop.threshold['nmbe_pct'], drop.threshold['annual_rel_err_pct'],
                          drop.threshold['conditioned_area_change_pct']), (30.0, 10.0, 10.0, 1.0))

    def test_the_main_matrix_is_the_full_factorial(self):
        drop = lod_site.Drop()
        entries = drop.main['entries']
        self.assertEqual(len(entries), 264)
        self.assertEqual(len({e['id'] for e in entries}), 264)
        self.assertEqual(len(drop.prototypes()), 11)
        self.assertEqual({e['climate_zone'] for e in entries}, {'2A', '2B', '3C', '4A', '5A', '7A'})
        self.assertEqual({e['vintage'] for e in entries}, {'90.1-2007', '90.1-2019'})
        self.assertEqual({e['orientation_degrees'] for e in entries}, {0.0, 45.0})
        for entry in entries:  # a recommended zoning is a kept zoning that meets the threshold, with the fewest zones
            meeting = [z for z in entry['zonings'] if z['meets_threshold']]
            self.assertTrue(all(z['succeeded'] and not z['duplicate_of'] for z in meeting), entry['id'])
            fewest = min((z['zone_count'] for z in meeting), default=None)
            self.assertEqual({p['site_name'] for p in entry['recommended']}, {z['site_name'] for z in meeting if z['zone_count'] == fewest}, entry['id'])

    def test_the_loader_admits_added_fields_and_refuses_another_format(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            data = json.loads((lod_site.DROP/lod_site.HT).read_text(encoding='utf-8'))
            data['timing'] = {'cpu_s': 1}
            data['entries'][0]['reference']['cpu_time_s'] = 2.5
            data['entries'][0]['zonings'][0]['later_metric'] = 1
            (folder/lod_site.MAIN).write_text(json.dumps(data), encoding='utf-8')
            shutil.copy(lod_site.DROP/lod_site.PROVENANCE, folder/lod_site.PROVENANCE)
            drop = lod_site.Drop(folder)
            self.assertEqual(drop.main['timing'], {'cpu_s': 1})
            self.assertIsNone(drop.ht)
            (folder/lod_site.MAIN).write_text(json.dumps({**data, 'format': 'other'}), encoding='utf-8')
            with self.assertRaises(ValueError):
                lod_site.Drop(folder)
            (folder/lod_site.MAIN).write_text(json.dumps({**data, 'version': '2.0.0'}), encoding='utf-8')
            with self.assertRaises(ValueError):
                lod_site.Drop(folder)


class LabelTests(unittest.TestCase):
    def test_zoning_labels_read_the_simplifier_depth_stacker_and_switches(self):
        self.assertEqual(lod_site.zoning_label({'simplifier': 'ConditionedMerge', 'join_pieces': False, 'perimeter_depth': None,
                                                'stacker': 'SingleZoneBuilding', 'iwht': True, 'fht': True}), 'Conditioned merge + Single zone building')
        self.assertEqual(lod_site.zoning_label({'simplifier': 'PerimeterCore PerimeterDepth=4.57', 'join_pieces': None, 'perimeter_depth': 4.57,
                                                'stacker': 'StackedFloorZoneMultiplier', 'iwht': False, 'fht': True}),
                         'Perimeter core 4.57 m + Stacked floor zone multiplier (IWHT off)')
        self.assertEqual(lod_site.zoning_label({'simplifier': None, 'stacker': None, 'iwht': None, 'fht': None}), 'zoning not recorded')
        self.assertEqual(lod_site.zoning_label({'simplifier': None, 'stacker': 'Stack', 'iwht': True}), 'unknown simplifier + Stack')
        self.assertEqual(lod_site.prototype_name('StandAloneRetail'), 'Stand-alone retail')
        self.assertEqual(lod_site.prototype_name('LaterPrototype'), 'Later prototype')
        self.assertEqual(lod_site.prototype_slug('FullServiceRestaurant'), 'full-service-restaurant')

    def test_unjudged_loads_and_flags_are_marked(self):
        threshold = {'min_reference_kwh_m2': 1.0}
        entry = {'reference': {'sensible_heating_kwh_m2_conditioned': 0.2, 'sensible_cooling_kwh_m2_conditioned': 40.0}}
        zoning = {'metrics': {'sensible_heating_cvrmse_pct': 120.0, 'sensible_cooling_cvrmse_pct': 12.345, 'sensible_cooling_nmbe_pct': None},
                  'flags': {'sensible_heating_cvrmse_pct': 'NearZeroReference'}}
        self.assertIn('ea-unjudged', lod_site.metric(zoning, 'sensible_heating_cvrmse_pct', entry, threshold))
        self.assertIn('title="NearZeroReference"', lod_site.metric(zoning, 'sensible_heating_cvrmse_pct', entry, threshold))
        self.assertEqual(lod_site.metric(zoning, 'sensible_cooling_cvrmse_pct', entry, threshold), '12.3')
        self.assertEqual(lod_site.metric(zoning, 'sensible_cooling_nmbe_pct', entry, threshold), lod_site.NULL)


class PageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.site = site_stub(cls.temporary.name)
        cls.site.links.place('90-1-2007.retail-standalone.source.entry.62d108', 'catalogue/commercial/90-1-2007/retail-standalone/programs/source/entry/')
        cls.result = lod_site.write_zoning(cls.site)
        cls.drop = lod_site.Drop()

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def page(self, url):
        return (Path(self.temporary.name)/url/'index.md').read_text(encoding='utf-8')

    def test_every_cell_has_its_section_and_summary_row_on_its_prototype_page(self):
        pages = self.result['pages']
        self.assertEqual(self.result['cells'], 264)
        self.assertEqual(len([k for k in pages if k.startswith('prototype:')]), 11)
        for prototype in self.drop.prototypes():
            text = self.page(pages['prototype:'+prototype])
            for entry in self.drop.entries(prototype):
                anchor = lod_site.cell_anchor(entry).replace('|', '-')
                self.assertIn(f' id="{anchor}"', text, entry['id'])
                self.assertIn(f'href="#{anchor}"', text, entry['id'])  # the summary row links to the cell's section
                self.assertIn(f'data-context="{entry["id"]}"', text)
                if not entry['recommended']:
                    self.assertIn('none meets the threshold', text)
            self.assertEqual(text.count('<section class="ea-context"'), len(self.drop.entries(prototype)))
            self.assertIn('data-filter="climate"', text)
            self.assertIn('data-filter="vintage"', text)
            self.assertIn('data-filter="orientation"', text)
        self.assertTrue(self.site.written >= {u+'index.md' for u in pages.values()})

    def test_the_pages_say_what_the_data_says(self):
        pages = self.result['pages']
        text = self.page(pages['prototype:StandAloneRetail'])
        entry = next(e for e in self.drop.main['entries'] if e['id'] == 'StandAloneRetail|7A|90.1-2007|0.0')
        self.assertIn('Conditioned merge + Single zone building', text)
        self.assertIn(f'{entry["reference"]["sensible_heating_kwh_m2_conditioned"]:,.1f}', text)
        self.assertIn('href="../../catalogue/commercial/90-1-2007/retail-standalone/programs/source/entry/#90-1-2007.retail-standalone.source.entry.62d108"', text)
        self.assertEqual(self.site.zoning_of['90-1-2007.retail-standalone.source.entry.62d108'], [('Stand-alone retail', 'zoning/stand-alone-retail/')])
        overview = self.page(pages['overview'])
        self.assertIn(f'A zoning meets the threshold in {self.result["cells_with_recommendation"]} of 264 cells', overview)
        self.assertIn('href="stand-alone-retail/"', overview)
        self.assertEqual(self.result['cells_with_recommendation'], sum(1 for e in self.drop.main['entries'] if e['recommended']))
        method = self.page(pages['method'])
        self.assertIn('24 zonings of the Small hotel', method)
        self.assertIn('no zoning fields for a site that did not run', method)
        self.assertIn('R5', method)
        heat = self.page(pages['heat_transfer'])
        self.assertEqual(heat.count('not applicable: the EnergyPlus run did not succeed'), 24)
        self.assertIn('data-filter="prototype"', heat)
        self.assertIn('IWHT off', heat)

    def test_pages_are_suite_pages_with_summaries_and_stored_json(self):
        for url in self.result['pages'].values():
            self.assertIn('<div class="ea-suite" markdown="0" data-search-exclude>', self.page(url))
            self.assertIn(url, self.site.summaries)
            self.assertNotIn('\n\n', self.page(url).split('---\n\n', 1)[1].strip())
        self.assertGreaterEqual(len(self.site.store.files), 11+3)
        descriptor = self.site.store.put(self.drop.main)
        self.assertEqual(site_store.read(self.temporary.name, descriptor)['entries'][0]['id'], self.drop.main['entries'][0]['id'])

    def test_site_check_wants_every_zoning_page(self):
        manifest = {'zoning': self.result}
        self.assertEqual(site_check.check_zoning(self.temporary.name, manifest), [])
        self.assertEqual(site_check.check_zoning(self.temporary.name, {}), [])
        missing = {'zoning': {'pages': {'x': 'zoning/no-such/'}}}
        self.assertEqual(site_check.check_zoning(self.temporary.name, missing), ['Missing zoning page: zoning/no-such/'])


class DigestTests(unittest.TestCase):
    def test_the_site_digest_covers_the_drop_the_schema_and_the_generator(self):
        self.assertIn('data/lod-recommendations', suite_site.DIGEST_INPUTS)
        self.assertIn('schemas', suite_site.DIGEST_INPUTS)
        self.assertIn('scripts.lod_site', suite_site.generator_modules())


if __name__ == '__main__':
    unittest.main()
