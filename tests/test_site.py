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
    def test_presentation_scope_filters_nested_options_and_keeps_source_immutable(self):
        site=self.site_module()
        row={'selected_options':{'Electric Vehicle':'None','Lighting':'100% LED'},
             'source_attributes':{'Electric Vehicle Charger':'None','Vintage':'1980s'},
             'option_ids':['excluded','retained']}
        original=copy.deepcopy(row)
        shown=site.presentation_scope(row,{'excluded'})
        self.assertEqual(shown['selected_options'],{'Lighting':'100% LED'})
        self.assertEqual(shown['source_attributes'],{'Vintage':'1980s'})
        self.assertEqual(shown['option_ids'],['retained'])
        self.assertEqual(row,original)

    def test_commercial_paths_attach_only_source_supported_beneficiaries(self):
        site=self.site_module()
        packet=load_json(ROOT/'data/completion-releases/v0.1.0/commercial-completion.json')
        p=next(d for d in packet['draw_paths'] if d['beneficiary_program_ids'])
        links=site.completion_links(packet,p['beneficiary_program_ids'][0])
        self.assertIn(p['path_id'],links['assigned_path_ids'])
        self.assertFalse(set(links['assigned_path_ids']) &
                         {d['path_id'] for d in packet['draw_paths'] if not d['beneficiary_program_ids']})
        self.assertTrue(site.completion_page(p).startswith('commercial-completion/paths/'))

    def test_active_catalogue_excludes_out_of_scope_end_uses_without_mutating_source(self):
        site=self.site_module();data=load_atlas(ROOT/'data/releases/v0.2.0');original=copy.deepcopy(data)
        entries=site.catalogue_entries(data,'v0.2.0')
        self.assertFalse(any('Electric Vehicle' in e['name'] for e in entries))
        self.assertEqual(data,original)

    def test_coverage_matches_the_selected_historical_supplement(self):
        site=self.site_module()
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'docs'
            site.generate_site([ROOT/'data/releases/v0.2.0'],target,pilot=True,
                               supplement_path=ROOT/'data/resolution-releases/v0.1.0')
            report=load_json(target/'schedule-coverage.json')
            self.assertEqual(report['resolution_supplement'],'v0.1.0')
            self.assertEqual(report['commercial']['missing_schedule_fields'],1208)
            self.assertEqual(report['residential']['missing_profile_fields'],107)

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
            self.assertEqual(packet['resolution_supplement']['version'],'v0.4.0')
            self.assertIn('profile',packet['resolution_supplement'])
            page=(target/residential['path']).read_text()
            self.assertIn('atlas-residential-profile',page)
            self.assertIn('Station-proxy',page)
            profile=packet['resolution_supplement']['profile']
            self.assertTrue((target/profile['download']).exists())
            self.assertTrue(profile['download'].startswith('resolution-supplements/v0.1.0/'))
            self.assertTrue((target/'resolution-supplements/v0.1.0/manifest.json').exists())
            self.assertTrue((target/'resolution-supplements/v0.2.0/manifest.json').exists())
            self.assertTrue((target/'resolution-supplements/v0.3.0/profile-download-map.json').exists())
            self.assertFalse((target/'resolution-supplements/v0.3.0/profiles').exists())
            fixed=load_json(target/'resolution-supplements/v0.3.0/fixed-background-annual.json')
            self.assertEqual(len(fixed['series']['refrigerator']),8760)
            self.assertEqual(max(fixed['series']['freezer']),1)
            self.assertIn('nominal',page)
            current=load_json(target/'resolution-supplements/v0.4.0/fixed-background-annual.json')
            self.assertEqual(len(current['series']['lighting_exterior']),8760)
            self.assertNotIn('Electric Vehicle',page)
            data=load_atlas(ROOT/'data/releases/v0.2.0')
            archived=next(r for r in site.pilot_data(data)['residential_options']
                          if r['parameter'].startswith('Electric Vehicle'))
            archive_page=target/f'releases/v0.2.0/residential_options/{archived["id"]}.md'
            self.assertIn('Archived out-of-scope option',archive_page.read_text())
            self.assertNotIn('Electric Vehicle',archive_page.read_text())
            self.assertIn('commercial-completion',
                          (target/'releases/v0.2.0/programs/program-29f8fa7a1d5e5afcf1f0.md').read_text())
            self.assertFalse((target/'resolution-supplements/v0.4.0/resolutions.json').exists())
            with zipfile.ZipFile(target/'resolution-supplements/v0.4.0/snapshot.zip') as archive:
                self.assertTrue(all(i.create_system==3 for i in archive.infolist()))
                self.assertEqual(archive.read('resolutions.json'),
                                 (ROOT/'data/resolution-releases/v0.4.0/resolutions.json').read_bytes())

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
            self.assertEqual(record['water_equivalent']['program_id'],office['id'])
            self.assertEqual(record['water_equivalent']['peak_divisor'],0.57)
            derived_id=record['water_equivalent']['equivalent_schedule']['id']
            self.assertIn(derived_id,page)
            self.assertIn('Fixture draw equivalent',page)
            self.assertTrue((target/'water-equivalents/v0.1.0/manifest.json').exists())
            self.assertEqual(load_json(target/f'releases/v0.2.0/records/{derived_id}.json')['record'],
                             record['water_equivalent']['equivalent_schedule'])
            self.assertTrue((target/f'releases/v0.2.0/schedules/{derived_id}.md').exists())
            # The public archive must have identical bytes on Windows and Linux:
            # names, creator metadata and compression defaults cannot depend on host.
            with zipfile.ZipFile(target/'water-equivalents/v0.1.0/snapshot.zip') as archive:
                names=archive.namelist()
                self.assertEqual(names,sorted(names))
                expected=ROOT/'data/water-releases/v0.1.0'
                self.assertEqual(set(names),{p.relative_to(expected).as_posix()
                                            for p in expected.rglob('*') if p.is_file()})
                for item in archive.infolist():
                    self.assertEqual(item.create_system,3)
                    self.assertEqual(item.compress_type,zipfile.ZIP_STORED)
                    self.assertEqual(item.date_time,(2026,10,4,0,0,0))
                    self.assertEqual(archive.read(item.filename),(expected/item.filename).read_bytes())
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
        self.assertEqual(p['climate'], 'Climate-independent')
        e = next(r for r in entries if r['kind'] == 'envelope_components')
        self.assertFalse(e['climate'].startswith('ClimateZone '))
        self.assertEqual(e['climate_basis'], 'Conditional envelope applicability')

    def test_equivalent_filter_labels_share_categories_without_merging_climate_sets(self):
        site = self.site_module()
        data = load_atlas(ROOT/'data/releases/v0.2.0')
        entries = site.catalogue_entries(data, 'v0.2.0')
        envelope_id = next(r['id'] for r in data['envelope_components'] if r['climate_zone_set'] == 'ClimateZone 2B')
        envelope = next(r for r in entries if r['id'] == envelope_id)
        dwelling = next(r for r in entries if r['kind'] == 'residential_archetypes' and r['climate'] == '2B')
        self.assertEqual(envelope['climate'], dwelling['climate'])
        self.assertEqual(envelope['facet_aliases']['climate'], ['ClimateZone 2B'])
        climates = {r['climate'] for r in entries}
        self.assertTrue({'2', '2A', '2B', '7AK', '8AK', 'Climate-independent', 'Unspecified'} <= climates)
        self.assertFalse(any(c.startswith('ClimateZone ') for c in climates))
        families = {r['source'] for r in entries}
        self.assertFalse(any('existing_stock_benchmark' in f or f.startswith('resstock') for f in families))
        self.assertIn('OpenStudio Standards · Existing-stock benchmark rules (Standards-derived)', families)

    def test_mapping_filters_follow_explicit_program_and_system_references(self):
        site = self.site_module()
        entries = site.catalogue_entries(load_atlas(ROOT/'data/releases/v0.2.0'), 'v0.2.0')
        mapping = next(r for r in entries if r['id'] == 'mapping-130635e6a30d1f7353a1')
        self.assertEqual(mapping['program'], 'office')
        self.assertEqual(mapping['system'], 'PVAV')
        attic = next(r for r in entries if r['id'] == 'mapping-0108ff9fd80d9d9a3496')
        self.assertEqual(attic['program'], 'attic')
        self.assertEqual(attic['system'], 'Unassigned / not reported')

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
