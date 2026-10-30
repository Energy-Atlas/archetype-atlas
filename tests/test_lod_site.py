"""The zoning-recommendation data drop and its pages (ADR 0050)."""
import gzip
import hashlib
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

import jsonschema

from scripts import lod_site, site_check, site_store, suite_site
from scripts.common import ROOT
from scripts.site_render import Links, Page

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
            for key in ('stage', 'suite', 'run', 'source_sha256', 'source'):
                self.assertTrue(entry.get(key), f'{name}: {key}')
        self.assertEqual(self.provenance['drop'], 2)
        self.assertEqual(files[lod_site.MAIN]['source_sha256'], '7fb9e2124a4be567701366a3a1dd42e770930312a85a18777349dc798071f778')  # BEMGen's provenance
        self.assertEqual(files[lod_site.HT]['source_sha256'], 'c76c78286f2d4b0e9e9e1dacfc5232a3cec774d6ffef72c4a15ef18a4ddf6c2c')
        self.assertEqual(files[lod_site.MAIN]['timing_suite'], 'lod-timing-20261029-080232')
        bemgen = self.provenance['bemgen']
        self.assertEqual(bemgen['report_commit'], '38ff521fbfd85b53ca4611336117a159e5e118a4')
        self.assertEqual((bemgen['run_commit'], bemgen['timing_commit'], bemgen['recheck_commit']), ('2ed856c', 'b29931c', 'd32fa2a'))
        self.assertEqual(bemgen['schema_version'], '1.1.0')
        self.assertEqual(bemgen['schema_sha256'], hashlib.sha256(SCHEMA.read_bytes()).hexdigest())
        self.assertEqual(self.provenance['atlas_inputs'], {**self.provenance['atlas_inputs'], 'release': '2.0.0',
                                                           'commit': '96a2e928ba60be6b54aa68d149e8de4222595035'})
        self.assertEqual(self.provenance['pending'], [])
        stages = self.provenance['stages']
        self.assertEqual(list(stages), ['R3', 'R4', 'R5', 'R5 repeat check', 'R6'])
        self.assertIn('not met', stages['R5']['gate'])
        self.assertEqual(stages['R5']['untimed_prototypes'], ['MediumOffice', 'PrimarySchool'])
        for key in ('report', 'methodology', 'plan', 'results'):
            self.assertTrue(self.provenance['study'][key].startswith(('research/', 'docs/')), key)
        self.assertIn('drop 2', self.provenance['licence'])
        self.assertIn('CC BY 4.0', self.provenance['licence'])

    def test_the_loader_accepts_schema_1_0_0_and_1_1_0(self):
        self.assertEqual(self.schema['properties']['version']['enum'], ['1.0.0', '1.1.0'])
        drop = lod_site.Drop()
        self.assertEqual((drop.main['version'], drop.ht['version']), ('1.1.0', '1.0.0'))  # the sub-study file is still a 1.0.0 document
        validator = jsonschema.Draft202012Validator(self.schema)
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            shutil.copy(lod_site.DROP/lod_site.PROVENANCE, folder/lod_site.PROVENANCE)
            for version, data in (('1.1.0', drop.ht), ('1.0.0', {k: v for k, v in drop.main.items() if k != 'timing'})):
                document = {**data, 'version': version}
                self.assertEqual(sorted(validator.iter_errors(document), key=str), [], version)
                (folder/lod_site.MAIN).write_text(json.dumps(document), encoding='utf-8')
                self.assertEqual(lod_site.Drop(folder).main['version'], version)
        self.assertEqual([list(e.path) for e in validator.iter_errors({**drop.ht, 'version': '1.2.0'})], [['version']])  # the schema admits no other version

    def test_the_main_matrix_carries_the_serial_costs_of_the_timed_cells(self):
        drop = lod_site.Drop()
        timing = drop.timing
        timed = [e for e in drop.main['entries'] if lod_site.timed(e)]
        self.assertEqual(len(timed), 12)
        self.assertEqual(len(timing['test_cases']), 12)
        self.assertEqual({(e['vintage'], e['orientation_degrees']) for e in timed}, {('90.1-2019', 0.0)})
        self.assertEqual({e['climate_zone'] for e in timed}, {'3C', '5A'})
        self.assertEqual(sorted({e['prototype'] for e in timed}), timing['timed_prototypes'])
        self.assertEqual(timing['untimed_prototypes'], ['MediumOffice', 'PrimarySchool'])
        self.assertTrue(all(not lod_site.timed(e) for e in drop.main['entries'] if e['prototype'] in timing['untimed_prototypes']))
        costed = [z for e in drop.main['entries'] for z in e['zonings'] if z.get('cost')]
        self.assertEqual(len(costed), 206)
        self.assertEqual(timing['timed_sites'], 218)  # 12 references + 206 test sites
        self.assertTrue(all(z['succeeded'] for z in costed))
        for z in costed:
            self.assertEqual({k for k in ('cpu_time_ratio', 'wall_clock_ratio', 'memory_peak_commit_ratio', 'cpu_time_s', 'repeats', 'cpu_time_cv_pct') if z['cost'].get(k) is None}, set())
            self.assertEqual(z['cost']['repeats'], 3)
        for e in timed:  # every recommended zoning of a timed cell carries its cost
            by_site = {z['site_name']: z for z in e['zonings']}
            self.assertTrue(all(by_site[p['site_name']].get('cost') for p in e['recommended']), e['id'])
        self.assertEqual((timing['gate']['pass'], timing['gate']['sites'], timing['gate']['verdict']), (192, 218, 'not met'))
        self.assertAlmostEqual(timing['gate']['median_pct'], 2.2, places=1)
        self.assertAlmostEqual(timing['gate']['max_pct'], 12.9, places=1)
        self.assertEqual((timing['recheck']['sites'], timing['recheck']['miss']), (34, 0))
        self.assertEqual(len(timing['by_prototype']), 9)
        self.assertEqual(len(timing['by_zoning']), 23)
        self.assertTrue(drop.costed)
        for e in drop.ht['entries']:  # the sub-study is not timed, and its failed sites now carry their zoning
            self.assertFalse(lod_site.timed(e))
            for z in e['zonings']:
                self.assertIsNotNone(z['zoning'].get('simplifier'), z['site_name'])

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

    def test_cost_cells_show_the_ratios_or_not_timed(self):
        zoning = {'cost': {'cpu_time_ratio': 0.40625, 'wall_clock_ratio': 0.4080959, 'memory_peak_commit_ratio': 0.9013843}}
        self.assertEqual(lod_site.cost_cells(zoning), '<td>0.406</td><td>0.408</td><td>0.901</td>')
        self.assertEqual(lod_site.cost_cells({'cost': {'cpu_time_ratio': 0.5}}), f'<td>0.500</td><td>{lod_site.NULL}</td><td>{lod_site.NULL}</td>')
        self.assertEqual(lod_site.cost_cells({}), lod_site.NOT_TIMED)
        self.assertIn('colspan="3"', lod_site.NOT_TIMED)
        self.assertIn('not timed', lod_site.NOT_TIMED)
        self.assertFalse(lod_site.timed({'reference': {}}))
        self.assertTrue(lod_site.timed({'reference': {'cost': {'cpu_time_s': 19.0}}}))
        self.assertIn('This cell was not timed', lod_site.cost_sentence({'reference': {}}))
        sentence = lod_site.cost_sentence({'reference': {'cost': {'cpu_time_s': 19.0, 'wall_clock_s': 19.25, 'memory_peak_commit_mib': 223.76, 'repeats': 3, 'cpu_time_cv_pct': 2.234}}})
        self.assertIn('processor time 19.0 s, wall clock 19.2 s, peak committed memory 224 MiB, each the median of 3 repeats (processor-time CV 2.2 %)', sentence)
        self.assertEqual(lod_site.writer_label('Conditioned Merge + Stacked Floor Zone Multiplier'), 'Conditioned merge + Stacked floor zone multiplier')
        self.assertEqual(lod_site.writer_label('Perimeter Core 4.57 m + Stack'), 'Perimeter core 4.57 m + Stack')
        self.assertEqual((lod_site.change(1.1514), lod_site.change(0.8288), lod_site.change(0.9553, 1), lod_site.change(None)), ('+15 %', '-17 %', '-4.5 %', lod_site.NULL))
        self.assertEqual((lod_site.pct(2.2213), lod_site.pct(None)), ('2.2 %', lod_site.NULL))


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
        self.assertEqual(self.site.zoning_of['90-1-2007.retail-standalone.source.entry.62d108'],
                         [('Stand-alone retail: robust across orientations in 6 of 6 cell pairs: Conditioned merge + Single zone building (4), '
                           'Semantic merge + Stack (2)', 'zoning/stand-alone-retail/#section-robust')])  # the catalogue page's fact (site_pages)
        overview = self.page(pages['overview'])
        self.assertIn(f'A zoning meets the threshold in {self.result["cells_with_recommendation"]} of 264 cells', overview)
        self.assertIn('href="stand-alone-retail/"', overview)
        self.assertEqual(self.result['cells_with_recommendation'], sum(1 for e in self.drop.main['entries'] if e['recommended']))
        method = self.page(pages['method'])
        self.assertIn('24 zonings of the Small hotel', method)
        self.assertIn('not applicable in their cells (D-201)', method)
        self.assertIn('Conditioned merge + Stack (IWHT off), Conditioned merge + Stack (IWHT off, FHT off)', method)  # the failed sites' zonings, from the file
        self.assertNotIn('no zoning fields for a site that did not run', method)
        heat = self.page(pages['heat_transfer'])
        self.assertEqual(heat.count('not applicable: the EnergyPlus run did not succeed'), 24)
        self.assertIn('<tr class="ea-failed"><td>No simplification + Stack (IWHT off) <code>', heat)
        self.assertNotIn('zoning not recorded', heat)
        self.assertIn('data-filter="prototype"', heat)
        self.assertIn('IWHT off', heat)

    def test_the_summary_and_cell_tables_carry_the_serial_costs_where_timed(self):
        pages = self.result['pages']
        self.assertEqual(self.result['timed_cells'], 12)
        text = self.page(pages['prototype:Outpatient'])
        head = text.split('<section class="ea-section" id="section-recommended">', 1)[1].split('</thead>', 1)[0]
        self.assertTrue(head.endswith('<th>Area change %</th><th>CPU ratio</th><th>Wall ratio</th><th>Memory ratio</th></tr>'), head)
        timed = next(e for e in self.drop.main['entries'] if e['id'] == 'Outpatient|3C|90.1-2019|0.0')
        pick = next(z for z in timed['zonings'] if z['site_name'] == timed['recommended'][0]['site_name'])
        ratios = ''.join(f'<td>{lod_site.num(pick["cost"][k], 3)}</td>' for k in lod_site.COST_KEYS)
        rows = re.findall(r'<tr[^>]*>.*?</tr>', text)
        row = next(r for r in rows if 'data-context="Outpatient|3C|90.1-2019|0.0"' in r)
        self.assertTrue(row.endswith(ratios+'</tr>'), row)
        self.assertIn('<td>0.065</td>', row)  # the outpatient's single zone costs 0.065 of its reference's processor time
        untimed_rows = [r for r in rows if 'class="ea-recommended" data-context' in r
                        and not any(f'data-context="Outpatient|{cz}|90.1-2019|0.0"' in r for cz in ('3C', '5A'))]
        self.assertEqual(len(untimed_rows), sum(len(e['recommended']) for e in self.drop.entries('Outpatient') if not lod_site.timed(e)))
        self.assertTrue(all(r.endswith(lod_site.NOT_TIMED+'</tr>') for r in untimed_rows))
        self.assertIn('Serial cost (R5): processor time 48.9 s', text)  # the timed cell's benchmark sentence
        self.assertIn('This cell was not timed in the serial pass (R5).', text)
        cell = text.split(' id="cell-Outpatient-3C-90.1-2019-0.0"', 1)[1].split('</section>', 1)[0]
        self.assertIn('<th>Peak cooling error %</th><th>CPU ratio</th><th>Wall ratio</th><th>Memory ratio</th><th>Meets the threshold</th>', cell)
        self.assertIn(ratios+'<td><strong>yes, recommended</strong></td>', cell)
        untimed_cell = text.split(' id="cell-Outpatient-3C-90.1-2007-0.0"', 1)[1].split('</section>', 1)[0]
        self.assertNotIn('CPU ratio', untimed_cell)
        self.assertIn('<dt>Serial cost (R5)</dt><dd>timed in 2 of 24 cells (3C 90.1-2019 0°, 5A 90.1-2019 0°)</dd>', text)
        self.assertIn('href="../method/#section-cost"', text)
        office = self.page(pages['prototype:MediumOffice'])
        self.assertIn('<dt>Serial cost (R5)</dt><dd>not timed: the prototype is not among the 12 timed cells of the serial pass</dd>', office)
        self.assertIn('<th>CPU ratio</th>', office)  # the columns stay, every row says not timed
        self.assertEqual(office.count('not timed</em></td></tr>'), office.count('class="ea-recommended" data-context'))  # the summary rows
        self.assertNotIn('Serial cost (R5): processor time', office)
        self.assertNotIn('<th>CPU ratio</th>', self.page(pages['heat_transfer']))  # the sub-study file carries no costs

    def test_the_overview_shows_the_cost_medians_and_the_completed_status(self):
        overview = self.page(self.result['pages']['overview'])
        self.assertIn('<li><a href="#section-cost">Cost</a></li>', overview)
        cost = overview.split('id="section-cost"', 1)[1].split('</section>', 1)[0]
        self.assertIn('<dt>Timed</dt><dd>218 sites of 12 cells (12 test cases of the serial pass), 9 prototypes; not timed: Medium office, Primary school</dd>', cost)
        self.assertIn('192 of 218 sites pass (median 2.2 %, largest 12.9 %); <strong>not met</strong>', cost)
        self.assertIn('34 long sites timed again: 0 at or above the gate (largest CV 4.8 %); absolute times +15 % against the pass, the test sites\' ratios -17 % to +5 % (median -4.5 %)', cost)
        by_prototype = cost.split('<h3>By prototype</h3>', 1)[1].split('<h3>By zoning</h3>', 1)[0]
        self.assertIn('<tr><td>Outpatient</td><td>30</td><td>0.064</td><td>0.066</td><td>0.694</td><td>3.2</td><td>2.1</td></tr>', by_prototype)
        self.assertIn('<tr><td>Medium office</td><td colspan="6" class="ea-unjudged ea-untimed"><em>not timed</em></td></tr>', by_prototype)
        self.assertEqual(by_prototype.count('<tr>'), 1+11)
        by_zoning = cost.split('<h3>By zoning</h3>', 1)[1]
        self.assertIn('<tr><td>Conditioned merge + Stacked floor zone multiplier</td><td>12</td><td>0.331</td>', by_zoning)
        self.assertEqual(by_zoning.count('<tr>'), 1+23)
        status = overview.split('id="section-status"', 1)[1].split('</section>', 1)[0]
        self.assertIn('Every stage of the run plan is complete; nothing is pending.', status)
        self.assertIn('<p>Nothing is pending.</p>', status)
        self.assertIn('<li>Study report (R6): <a href="https://github.com/EnvironmentalSystemsLab/BEMGen/blob/38ff521fbfd85b53ca4611336117a159e5e118a4/'
                      'research/lod-study/report/2026-10-29-lod-study-report.md"><code>research/lod-study/report/2026-10-29-lod-study-report.md</code></a> in BEMGen</li>', status)
        self.assertIn('<code>research/lod-study/report/2026-10-29-lod-study-methodology.md</code>', status)
        self.assertIn('<a href="https://github.com/EnvironmentalSystemsLab/BEMGen/tree/38ff521fbfd85b53ca4611336117a159e5e118a4/research/lod-study/results/">', status)
        self.assertIn('<td>R5 serial timing pass</td><td>lod-timing-20261029-080232</td><td>run_20261029-083427</td>', status)
        self.assertIn('<td>R3 main matrix</td><td>lod-main-20261029-051941</td>', status)
        self.assertIn('drop 2', status)
        self.assertIn('Geometric LOD study · drop 2 · 264 cells', overview)

    def test_the_method_page_states_the_cost_protocol_and_the_reading_cautions(self):
        method = self.page(self.result['pages']['method'])
        self.assertIn('<li><a href="#section-cost">Cost protocol</a></li><li><a href="#section-cautions">Reading the recommendations</a></li>', method)
        cost = method.split('id="section-cost"', 1)[1].split('</section>', 1)[0]
        self.assertIn('BEMGen <code>b29931c</code>', cost)
        self.assertIn('--parallel 1 --timing-repeats 3 --timing-test-cases 12', cost)
        self.assertIn('i7-14700F', cost)
        self.assertIn('<dt>Timed</dt><dd>218 sites of 12 cells: Full-service restaurant 3C 90.1-2019 0°, Strip mall 3C 90.1-2019 0°', cost)  # page order
        self.assertIn('<dt>Not timed</dt><dd>Medium office, Primary school (not among the 12 timed test cases', cost)
        self.assertIn('<dt>Repeats</dt><dd>3</dd>', cost)
        self.assertIn('192 of 218 sites pass; median 2.2 %, P90 5.3 %, largest 12.9 %; 10 misses are short runs', cost)
        self.assertIn('16 are among the 34 sites of at least 4 s', cost)
        self.assertIn('<strong>not met</strong>', cost)
        self.assertIn('BEMGen <code>d32fa2a</code>, run <code>run_20261029-144634</code>, 3 serial repeats', cost)
        self.assertIn('0 of 34 at or above 5.0 % (median CV 2.0 %, largest 4.8 %; the pass had 16 misses among them)', cost)
        self.assertIn('absolute times +15 % against the pass and the 28 test sites\' ratios moved by -17 % to +5 % (median -4.5 %)', cost)
        self.assertIn('reproducible to about ±15 %', cost)
        self.assertIn('The costs shown are therefore medians', cost)
        cautions = method.split('id="section-cautions"', 1)[1].split('</section>', 1)[0]
        self.assertIn('lists off before on, so the kept and recommended site carries <em>off</em>', cautions)
        self.assertIn('the Full-service restaurant in 4A: Perimeter core 4.57 m + Stack, 5 zones against the reference\'s 2 (4 cells)', cautions)
        limits = method.split('id="section-limits"', 1)[1].split('</section>', 1)[0]
        self.assertIn('<strong>Cost precision and scope.</strong> The timing gate was not met, so costs are medians (the cost protocol above); the Medium office, Primary school were not timed; '
                      'costs are measured in 90.1-2019, climate zones 3C, 5A, at 0° only, and on one machine.', limits)
        self.assertIn('32 kW in 15 m²', limits)
        self.assertNotIn('pending', method)
        provenance = method.split('id="section-provenance"', 1)[1]
        self.assertIn('the R5 timing pass at <code>b29931c</code> and its repeat check at <code>d32fa2a</code>', provenance)
        self.assertIn('<dt>Report</dt><dd><a href="https://github.com/EnvironmentalSystemsLab/BEMGen/blob/38ff521fbfd85b53ca4611336117a159e5e118a4/research/lod-study/report/2026-10-29-lod-study-report.md">', provenance)
        self.assertIn('the main matrix is version 1.1.0, the sub-study 1.0.0', provenance)
        self.assertIn('<td>R5 repeat check of the 34 long sites</td>', provenance)
        self.assertIn('<code>7fb9e2124a4b</code>', provenance)
        self.assertIn('<code>be4a859d6318</code>', provenance)

    def test_a_drop_without_costs_renders_without_cost_columns(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            shutil.copy(lod_site.DROP/lod_site.HT, folder/lod_site.MAIN)  # a 1.0.0 document as the main matrix, no sub-study
            shutil.copy(lod_site.DROP/lod_site.PROVENANCE, folder/lod_site.PROVENANCE)
            with tempfile.TemporaryDirectory() as target:
                site = site_stub(target)
                result = lod_site.write_zoning(site, folder)
                self.assertEqual((result['cells'], result['timed_cells'], result['ht_cells']), (22, 0, 0))
                page = (Path(target)/result['pages']['prototype:SmallHotel']/'index.md').read_text(encoding='utf-8')
                self.assertNotIn('CPU ratio', page)
                self.assertNotIn('not timed', page)
                self.assertNotIn('Serial cost', page)
                overview = (Path(target)/result['pages']['overview']/'index.md').read_text(encoding='utf-8')
                self.assertNotIn('id="section-cost"', overview)
                method = (Path(target)/result['pages']['method']/'index.md').read_text(encoding='utf-8')
                self.assertIn('the serial timing pass (R5) has not been applied to this drop', method)
                self.assertIn('<strong>Timing.</strong>', method)

    def test_pages_are_suite_pages_with_summaries_and_stored_json(self):
        for url in self.result['pages'].values():
            self.assertIn('<div class="ea-suite" markdown="0" data-search-exclude>', self.page(url))
            self.assertIn(url, self.site.summaries)
            self.assertNotIn('\n\n', self.page(url).split('---\n\n', 1)[1].strip())
        self.assertGreaterEqual(len(self.site.store.files), 11+3)
        self.assertIn('LOD recommendations 1.1.0, main matrix', self.page(self.result['pages']['overview']))
        descriptor = self.site.store.put(self.drop.main)
        self.assertEqual(site_store.read(self.temporary.name, descriptor)['entries'][0]['id'], self.drop.main['entries'][0]['id'])

    def test_site_check_wants_every_zoning_page(self):
        manifest = {'zoning': self.result}
        self.assertEqual(site_check.check_zoning(self.temporary.name, manifest), [])
        self.assertEqual(site_check.check_zoning(self.temporary.name, {}), [])
        missing = {'zoning': {'pages': {'x': 'zoning/no-such/'}}}
        self.assertEqual(site_check.check_zoning(self.temporary.name, missing), ['Missing zoning page: zoning/no-such/'])


def fields(simplifier, stacker, depth=None):
    return {'simplifier': simplifier, 'join_pieces': False if simplifier in ('SemanticMerge', 'ConditionedMerge') else None,
            'perimeter_depth': depth, 'stacker': stacker, 'iwht': True, 'fht': True}


def row(site, zoning, zones, meets, heating=1.0, cooling=1.0, cvrmse=5.0, nmbe=1.0, area=0.0, duplicate_of=None, cost=None, succeeded=True):
    metrics = {'sensible_heating_kwh_rel_err_pct': heating, 'sensible_cooling_kwh_rel_err_pct': cooling, 'sensible_heating_cvrmse_pct': cvrmse,
               'sensible_cooling_cvrmse_pct': cvrmse, 'sensible_heating_nmbe_pct': nmbe, 'sensible_cooling_nmbe_pct': nmbe}
    r = {'site_name': site, 'zoning': zoning, 'succeeded': succeeded, 'duplicate_of': duplicate_of, 'zone_count': zones, 'conditioned_area_change_pct': area,
         'metrics': metrics, 'flags': {}, 'meets_threshold': bool(meets and succeeded and not duplicate_of), 'misses': []}
    if cost:
        r['cost'] = cost
    return r


def cell(orientation, rows, prototype='Proto', climate='4A', vintage='90.1-2019'):
    """A synthetic cell: the writer's recommendation rule (fewest zones among the kept zonings meeting the threshold, ties all)."""
    meeting = [r for r in rows if r['meets_threshold']]
    counted = [r for r in meeting if r['zone_count'] is not None]
    fewest = min((r['zone_count'] for r in counted), default=None)
    recommended = [{'site_name': r['site_name'], 'zoning': r['zoning'], 'zone_count': r['zone_count']} for r in counted if r['zone_count'] == fewest]
    return {'id': f'{prototype}|{climate}|{vintage}|{orientation}', 'prototype': prototype, 'climate_zone': climate, 'vintage': vintage,
            'orientation_degrees': orientation, 'programs': {}, 'reference': {'zone_count': 10, 'sensible_heating_kwh_m2_conditioned': 20.0,
                                                                                'sensible_cooling_kwh_m2_conditioned': 30.0}, 'zonings': rows, 'recommended': recommended}


SZB, SM, CM, PC3 = fields('ConditionedMerge', 'SingleZoneBuilding'), fields('SemanticMerge', 'Stack'), fields('ConditionedMerge', 'Stack'), fields('PerimeterCore PerimeterDepth=3', 'Stack', 3.0)
THRESHOLD = {'min_reference_kwh_m2': 1.0}


class RobustRuleTests(unittest.TestCase):
    def test_the_same_pick_at_both_orientations_is_the_robust_one(self):
        a = cell(0.0, [row('a/1', SZB, 1, True, heating=-3.0), row('a/2', SM, 4, True, heating=0.5)])
        b = cell(45.0, [row('b/1', SZB, 1, True, heating=2.0, cooling=-7.5), row('b/2', SM, 4, True)])
        r = lod_site.robust({0.0: a, 45.0: b})
        self.assertEqual((r['status'], r['zoning'], r['zone_count'], r['same_pick'], r['ties']), ('robust', SZB, 1, True, []))
        self.assertEqual([z['site_name'] for _, z in r['picks']], ['a/1', 'b/1'])
        self.assertEqual(lod_site.worst('sensible_heating_kwh_rel_err_pct', r['picks'])[1]['site_name'], 'a/1')  # -3.0 is worse than +2.0
        self.assertEqual(lod_site.worst('sensible_cooling_kwh_rel_err_pct', r['picks'])[1]['site_name'], 'b/1')
        self.assertEqual(r['cost'], {})
        self.assertEqual(r['per_orientation'], {0.0: [SZB], 45.0: [SZB]})

    def test_different_picks_take_the_coarsest_zoning_meeting_at_both(self):
        a = cell(0.0, [row('a/1', SZB, 1, True), row('a/2', SM, 4, False), row('a/3', CM, 6, True), row('a/4', PC3, 5, True)])
        b = cell(45.0, [row('b/1', SZB, 1, False), row('b/2', SM, 4, True), row('b/3', CM, 6, True), row('b/4', PC3, 5, False)])
        r = lod_site.robust({0.0: a, 45.0: b})
        self.assertEqual((r['status'], r['zoning'], r['zone_count'], r['same_pick']), ('robust', CM, 6, False))  # SZB fails at 45°, SM at 0°, PC3 at 45°
        self.assertEqual(r['per_orientation'], {0.0: [SZB], 45.0: [SM]})
        self.assertEqual(r['ties'], [])

    def test_no_zoning_meeting_at_both_says_so_and_keeps_each_orientations_pick(self):
        a = cell(0.0, [row('a/1', SZB, 1, True), row('a/2', SM, 4, False)])
        b = cell(45.0, [row('b/1', SZB, 1, False), row('b/2', SM, 4, True)])
        r = lod_site.robust({0.0: a, 45.0: b})
        self.assertEqual(r['status'], 'none')
        self.assertNotIn('zoning', r)
        self.assertEqual(r['per_orientation'], {0.0: [SZB], 45.0: [SM]})
        empty = lod_site.robust({0.0: cell(0.0, [row('a/1', SZB, 1, False)]), 45.0: cell(45.0, [row('b/1', SZB, 1, False)])})
        self.assertEqual((empty['status'], empty['per_orientation']), ('none', {0.0: [], 45.0: []}))

    def test_a_missing_orientation_is_no_pair(self):
        r = lod_site.robust({0.0: cell(0.0, [row('a/1', SZB, 1, True)])})
        self.assertEqual((r['status'], r['orientations'], r['per_orientation']), ('single', [0.0], {0.0: [SZB]}))
        self.assertFalse(lod_site.paired([cell(0.0, [])]))
        self.assertTrue(lod_site.paired([cell(0.0, []), cell(45.0, [])]))
        results = lod_site.robust_results([cell(0.0, [row('a/1', SZB, 1, True)]), cell(45.0, [row('b/1', SZB, 1, True)]), cell(0.0, [row('c/1', SM, 4, True)], climate='5A')])
        self.assertEqual([r['status'] for r in results.values()], ['robust', 'single'])
        self.assertEqual(list(results), [('Proto', '4A', '90.1-2019'), ('Proto', '5A', '90.1-2019')])

    def test_ties_prefer_the_zoning_recommended_at_both_then_the_zoning_order_and_are_named(self):
        a = cell(0.0, [row('a/1', SM, 4, True), row('a/2', CM, 4, True)])
        b = cell(45.0, [row('b/1', SM, 4, True), row('b/2', CM, 4, True)])
        r = lod_site.robust({0.0: a, 45.0: b})
        self.assertEqual((r['zoning'], r['ties'], r['same_pick']), (CM, [SM], True))  # both recommended at both: the writer's order, ConditionedMerge first
        a = cell(0.0, [row('a/1', SM, 4, True), row('a/2', CM, 4, True), row('a/3', SZB, 1, True)])
        b = cell(45.0, [row('b/1', SM, 4, True), row('b/2', CM, 4, False), row('b/3', SZB, 1, False)])
        r = lod_site.robust({0.0: a, 45.0: b})
        self.assertEqual((r['zoning'], r['ties'], r['same_pick']), (SM, [], False))  # SM is 45°'s pick; CM fails there
        a = cell(0.0, [row('a/1', SM, 4, True), row('a/2', CM, 4, True), row('a/3', PC3, 4, True)])
        b = cell(45.0, [row('b/1', SM, 4, True), row('b/2', CM, 4, True), row('b/3', PC3, 4, True, duplicate_of='b/2')])
        r = lod_site.robust({0.0: a, 45.0: b})
        self.assertEqual((r['zoning'], r['ties']), (CM, [SM]))  # a duplicate at one orientation never qualifies and is not named as a tie
        self.assertEqual(lod_site.zoning_order(PC3), ('PerimeterCore PerimeterDepth=3', '', '3.0', 'Stack', 'True', 'True'))
        self.assertLess(lod_site.zoning_order(CM), lod_site.zoning_order(SM))

    def test_failed_duplicate_and_unknown_zone_counts_are_tolerated(self):
        a = cell(0.0, [row('a/1', SZB, 1, True, succeeded=False), row('a/2', SM, None, True), row('a/3', CM, 6, True)])
        b = cell(45.0, [row('b/1', SZB, 1, True), row('b/2', SM, None, True), row('b/3', CM, 6, True)])
        r = lod_site.robust({0.0: a, 45.0: b})
        self.assertEqual((r['zoning'], r['zone_count']), (CM, 6))  # a zoning without a zone count sorts last
        a = cell(0.0, [row('a/2', SM, None, True)])
        b = cell(45.0, [row('b/2', SM, None, True)])
        self.assertEqual(lod_site.robust({0.0: a, 45.0: b})['zone_count'], None)
        self.assertEqual(lod_site.robust({0.0: cell(0.0, [row('a/1', SZB, 1, True)]), 45.0: cell(45.0, [row('b/1', SM, 4, True)])})['status'], 'none')

    def test_the_cost_is_the_median_over_the_timed_sites_of_the_robust_zoning(self):
        timed = {'cpu_time_ratio': 0.4, 'wall_clock_ratio': 0.5, 'memory_peak_commit_ratio': 0.9}
        a = cell(0.0, [row('a/1', SZB, 1, True, cost=timed)])
        b = cell(45.0, [row('b/1', SZB, 1, True)])
        self.assertEqual(lod_site.robust({0.0: a, 45.0: b})['cost'], timed)  # one timed orientation: its ratios
        b = cell(45.0, [row('b/1', SZB, 1, True, cost={'cpu_time_ratio': 0.6, 'wall_clock_ratio': 0.7})])
        self.assertEqual(lod_site.robust({0.0: a, 45.0: b})['cost'], {'cpu_time_ratio': 0.5, 'wall_clock_ratio': 0.6, 'memory_peak_commit_ratio': 0.9})
        self.assertEqual((lod_site.median([3, 1, 2]), lod_site.median([4, 1, 3, 2]), lod_site.median([])), (2, 2.5, None))
        self.assertEqual(lod_site.cost_cells({'cost': lod_site.robust({0.0: cell(0.0, [row('a/1', SZB, 1, True)]), 45.0: cell(45.0, [row('b/1', SZB, 1, True)])})['cost']}), lod_site.NOT_TIMED)

    def test_the_rows_and_the_json_block_say_what_the_rule_found(self):
        page = Page(Links(), 'zoning/proto/')
        a = cell(0.0, [row('a/1', SZB, 1, True, heating=-3.0, cvrmse=12.0, area=0.2)])
        b = cell(45.0, [row('b/1', SZB, 1, True, heating=2.0, cvrmse=4.0, area=-0.5)])
        results = lod_site.robust_results([a, b, cell(0.0, [row('c/1', SZB, 1, True)], climate='5A'), cell(45.0, [row('d/1', SZB, 1, False)], climate='5A'),
                                           cell(0.0, [row('e/1', SZB, 1, True)], climate='7A')])
        rows = lod_site.robust_rows(page, results, THRESHOLD, costed=True)
        self.assertEqual(len(rows), 3)
        self.assertIn('<tr class="ea-robust ea-recommended" data-context="pair:Proto|4A|90.1-2019" data-climate="4A" data-vintage="90.1-2019" data-across="orientation">'
                      '<td>4A</td><td>90.1-2019</td><td>Conditioned merge + Single zone building</td><td>1</td><td>-3.0</td><td>1.0</td><td>12.0</td><td>12.0</td>'
                      '<td>1.0</td><td>1.0</td><td>-0.50</td>'+lod_site.NOT_TIMED+'<td>recommended at both orientations</td></tr>', rows[0])
        self.assertIn('<td colspan="12"><em>none meets the threshold at both orientations</em></td><td><a href="#cell-Proto-5A-90.1-2019-0.0">0°</a>: '
                      'Conditioned merge + Single zone building (1 zone) · <a href="#cell-Proto-5A-90.1-2019-45.0">45°</a>: <em>none</em></td>', rows[1])
        self.assertIn('<td colspan="13"><em>one orientation only (0°): no pair to judge</em></td>', rows[2])
        self.assertEqual(len(lod_site.robust_rows(page, results, THRESHOLD)[1].split('colspan="9"')), 2)
        block = lod_site.robust_block(results)
        self.assertEqual(block['rule'], lod_site.ROBUST_RULE)
        self.assertIn('not a report-writer field', block['computed_by'])
        self.assertEqual([p['status'] for p in block['pairs']], ['robust', 'none', 'single'])
        first = block['pairs'][0]
        self.assertEqual((first['label'], first['zone_count'], first['site_names'], first['recommended_at_every_orientation'], first['ties']),
                         ('Conditioned merge + Single zone building', 1, {'0': 'a/1', '45': 'b/1'}, True, []))
        self.assertEqual(first['worst']['sensible_heating_kwh_rel_err_pct'], {'value': -3.0, 'orientation': 0.0})
        self.assertEqual(first['worst']['conditioned_area_change_pct'], {'value': -0.5, 'orientation': 45.0})
        self.assertIsNone(first['cost'])
        self.assertEqual(block['pairs'][1]['recommended_per_orientation'], {'0': ['Conditioned merge + Single zone building'], '45': []})
        self.assertEqual(lod_site.tally_robust(results), [('Conditioned merge + Single zone building', 1)])
        self.assertEqual(lod_site.program_fact('Proto', results), 'Proto: robust across orientations in 1 of 3 cell pairs: Conditioned merge + Single zone building (1)')
        self.assertEqual(lod_site.program_fact('Proto', {}), 'Proto')
        json.dumps(block)  # serialisable


class RobustPageTests(unittest.TestCase):
    """The robust headline on every page, from the drop in the repository."""

    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.site = site_stub(cls.temporary.name)
        cls.result = lod_site.write_zoning(cls.site)
        cls.drop = lod_site.Drop()
        cls.results = lod_site.robust_results(cls.drop.main['entries'])

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def page(self, url):
        return (Path(self.temporary.name)/url/'index.md').read_text(encoding='utf-8')

    def test_the_drop_has_a_robust_zoning_in_109_of_132_cell_pairs(self):
        self.assertEqual((self.result['cell_pairs'], self.result['robust_pairs']), (132, 109))
        statuses = [r['status'] for r in self.results.values()]
        self.assertEqual((statuses.count('robust'), statuses.count('none'), statuses.count('single')), (109, 23, 0))
        same = 0
        for key, r in self.results.items():
            picks = [{lod_site.zoning_key(p['zoning']) for p in e['recommended']} for e in r['entries']]
            if r['status'] != 'robust':
                self.assertFalse(picks[0] and picks[0] == picks[1], key)  # the same pick at both orientations always gives a robust zoning
                continue
            for entry, zoning in r['picks']:  # the pick is a kept zoning that meets the threshold at each orientation
                self.assertTrue(zoning['succeeded'] and not zoning['duplicate_of'] and zoning['meets_threshold'], key)
                self.assertIn(zoning, entry['zonings'])
                if entry['recommended']:  # never coarser than the orientation's own recommendation
                    self.assertGreaterEqual(r['zone_count'], entry['recommended'][0]['zone_count'], key)
            if picks[0] and picks[0] == picks[1]:
                same += 1
                self.assertIn(r['key'], picks[0], key)
        self.assertEqual(same, 97)
        self.assertEqual(sum(1 for r in self.results.values() if r['status'] == 'robust' and r['same_pick']), 100)
        self.assertEqual(sum(n for _, n in lod_site.tally_robust(self.results)), 109)
        self.assertEqual(lod_site.tally_robust(self.results)[0], ('Conditioned merge + Single zone building', 41))

    def test_every_prototype_page_opens_with_the_robust_table(self):
        for prototype in self.drop.prototypes():
            text = self.page(self.result['pages']['prototype:'+prototype])
            self.assertLess(text.index('id="section-robust"'), text.index('id="section-recommended"'))
            self.assertIn('<li><a href="#section-robust">Robust across orientations</a></li><li><a href="#section-recommended">Recommended zonings</a></li>', text)
            section = text.split('id="section-robust"', 1)[1].split('</section>', 1)[0]
            own = {k: r for k, r in self.results.items() if k[0] == prototype}
            rows = re.findall(r'<tr class="ea-robust[^>]*>.*?</tr>', section)
            self.assertEqual(len(rows), len(own), prototype)
            self.assertEqual(len(own), 12)
            for (_, climate, vintage), r in own.items():
                row_ = next(x for x in rows if f'data-context="pair:{prototype}|{climate}|{vintage}"' in x)
                self.assertIn(f'data-climate="{climate}" data-vintage="{vintage}" data-across="orientation"', row_)
                if r['status'] == 'robust':
                    self.assertIn(f'<td>{lod_site.zoning_label(r["zoning"])}', row_)
                    self.assertIn('ea-recommended', row_)
                else:
                    self.assertIn('none meets the threshold at both orientations', row_)
                    self.assertIn(f'href="#cell-{prototype}-{climate}-{vintage}-0.0"', row_)
            robust_pairs = sum(1 for r in own.values() if r['status'] == 'robust')
            self.assertIn(f'<dt>Robust across orientations</dt><dd>{robust_pairs} of 12 cell pairs', text)
            self.assertIn(f'Robust across orientations in <strong>{robust_pairs} of 12</strong> cell pairs (0° and 45°)', section)
            self.assertIn('<th>Climate zone</th><th>Vintage</th><th>Robust zoning</th><th>Zones</th><th>Heating error %</th><th>Cooling error %</th>'
                          '<th>Heating CV(RMSE) %</th><th>Cooling CV(RMSE) %</th><th>Heating NMBE %</th><th>Cooling NMBE %</th><th>Area change %</th>'
                          '<th>CPU ratio</th><th>Wall ratio</th><th>Memory ratio</th><th>Per orientation</th>', section)
            self.assertIn('href="../method/#section-robust"', section)

    def test_the_robust_rows_show_the_worse_orientation_and_the_timed_cost(self):
        text = self.page(self.result['pages']['prototype:StandAloneRetail'])
        section = text.split('id="section-robust"', 1)[1].split('</section>', 1)[0]
        r = self.results[('StandAloneRetail', '3C', '90.1-2019')]
        self.assertEqual((lod_site.zoning_label(r['zoning']), r['same_pick']), ('Semantic merge + Stack', True))
        row_ = next(x for x in re.findall(r'<tr class="ea-robust[^>]*>.*?</tr>', section) if 'pair:StandAloneRetail|3C|90.1-2019"' in x)
        timed = next(z for e, z in r['picks'] if e['orientation_degrees'] == 0.0)
        self.assertIn(''.join(f'<td>{lod_site.num(timed["cost"][k], 3)}</td>' for k in lod_site.COST_KEYS), row_)  # the 0° site is the only timed one
        for name in lod_site.ERROR_KEYS:
            values = [z['metrics'][name] for _, z in r['picks']]
            self.assertIn(f'>{lod_site.num(max(values, key=abs))}<', row_, name)
        r = self.results[('StandAloneRetail', '3C', '90.1-2007')]  # the orientations disagree: the robust zoning is 0°'s pick, 45°'s 1-zone picks fail at 0°
        self.assertEqual((lod_site.zoning_label(r['zoning']), r['zone_count'], r['same_pick']), ('Semantic merge + Stack', 4, False))
        row_ = next(x for x in re.findall(r'<tr class="ea-robust[^>]*>.*?</tr>', section) if 'pair:StandAloneRetail|3C|90.1-2007"' in x)
        self.assertIn('<a href="#cell-StandAloneRetail-3C-90.1-2007-0.0">0°</a>: Semantic merge + Stack (4 zones) · <a href="#cell-StandAloneRetail-3C-90.1-2007-45.0">45°</a>: '
                      'Conditioned merge + Single zone building (1 zone)', row_)
        self.assertIn(lod_site.NOT_TIMED, row_)
        hospital = self.page(self.result['pages']['prototype:Hospital'])
        self.assertIn('<td>Conditioned merge + Stack <span class="ea-ties">(tie: Conditioned merge + Stacked floor zone multiplier)</span></td>', hospital)
        office = self.page(self.result['pages']['prototype:MediumOffice'])
        self.assertEqual(office.split('id="section-robust"', 1)[1].split('</section>', 1)[0].count(lod_site.NOT_TIMED), 12 - sum(1 for r in self.results.values() if r['status'] == 'none' and r['entries'][0]['prototype'] == 'MediumOffice'))

    def test_the_overview_tallies_the_robust_pairs(self):
        overview = self.page(self.result['pages']['overview'])
        self.assertIn('<h3>Robust across orientations: 109 of 132 cell pairs</h3>', overview)
        self.assertIn('<tr><td>Conditioned merge + Single zone building</td><td>41</td></tr>', overview.split('<h3>Robust across orientations', 1)[1])
        self.assertIn(', and at both orientations of a cell pair in 109 of 132 pairs (robust across orientations). Each prototype page', overview)
        self.assertIn('<th>With a recommended zoning</th><th>Robust across orientations (cell pairs)</th><th>Most often recommended (cells)</th>', overview)
        self.assertIn('<a href="stand-alone-retail/">Stand-alone retail</a></td><td>24</td><td>24</td><td>12 of 12</td>', overview)
        self.assertIn('<a href="supermarket/">Supermarket</a></td><td>24</td><td>16</td><td>8 of 12</td>', overview)
        self.assertIn('each prototype page opens with it', overview)

    def test_the_method_page_states_the_rule_what_the_data_allows_and_the_limits(self):
        method = self.page(self.result['pages']['method'])
        self.assertIn('<li><a href="#section-dedup">Deduplication</a></li><li><a href="#section-robust">Robust across orientations</a></li><li><a href="#section-cost">Cost protocol</a></li>', method)
        section = method.split('id="section-robust"', 1)[1].split('</section>', 1)[0]
        self.assertIn(lod_site.esc(lod_site.ROBUST_RULE), section)
        self.assertIn('<dt>Cell pairs</dt><dd>132: robust in 109, none meeting at both orientations in 23</dd>', section)
        self.assertIn('<dt>Recommended at both orientations</dt><dd>100 of 109 robust pairs', section)
        self.assertIn('<dt>Ties at the fewest zones</dt><dd>38 pairs, named in the row</dd>', section)
        self.assertIn('so the rule compares the zonings themselves at both orientations, not only the two recommendations', section)
        self.assertIn('<code>meets_threshold</code>', section)
        self.assertIn('Robust means robust over the two orientations the study ran, 0° and 45°', section)
        self.assertIn('<code>robust</code> block', section)
        self.assertIn('the headline over the pair is the robust rule below', method)

    def test_the_prototype_json_carries_the_robust_block_and_the_manifest_the_counts(self):
        slice_json = None
        for href in self.site.store.files:  # the store keys by digest; read the stand-alone retail slice back
            document = json.loads(gzip.decompress((Path(self.temporary.name)/href).read_bytes()))
            if isinstance(document, dict) and 'robust' in document and {e['prototype'] for e in document['entries']} == {'StandAloneRetail'}:
                slice_json = document
        self.assertIsNotNone(slice_json)
        block = slice_json['robust']
        self.assertEqual((block['rule'], len(block['pairs'])), (lod_site.ROBUST_RULE, 12))
        self.assertEqual([p['status'] for p in block['pairs']].count('robust'), 12)
        self.assertEqual(block['pairs'][0]['cells'], ['StandAloneRetail|2A|90.1-2007|0.0', 'StandAloneRetail|2A|90.1-2007|45.0'])
        self.assertNotIn('robust', self.drop.main)  # the writer's file is unchanged
        self.assertNotIn('robust', site_store.read(self.temporary.name, self.site.store.put(self.drop.main)))
        self.assertEqual(self.result['cell_pairs'], 132)

    def test_a_drop_with_one_orientation_has_no_robust_headline(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            shutil.copy(lod_site.DROP/lod_site.HT, folder/lod_site.MAIN)  # 0° only
            shutil.copy(lod_site.DROP/lod_site.PROVENANCE, folder/lod_site.PROVENANCE)
            with tempfile.TemporaryDirectory() as target:
                site = site_stub(target)
                result = lod_site.write_zoning(site, folder)
                self.assertEqual((result['cell_pairs'], result['robust_pairs']), (0, 0))
                page = (Path(target)/result['pages']['prototype:SmallHotel']/'index.md').read_text(encoding='utf-8')
                self.assertNotIn('section-robust', page)
                self.assertNotIn('Robust across orientations', page)
                overview = (Path(target)/result['pages']['overview']/'index.md').read_text(encoding='utf-8')
                self.assertNotIn('Robust across orientations', overview)
                self.assertNotIn('robust', overview.split('id="section-prototypes"', 1)[1].split('</section>', 1)[0])
                method = (Path(target)/result['pages']['method']/'index.md').read_text(encoding='utf-8')
                self.assertIn('This drop has one orientation per prototype, climate zone and vintage, so there is no pair to judge', method)
                self.assertTrue(all(url.endswith('/') for pairs_ in site.zoning_of.values() for _, url in pairs_))
        heat = self.page(self.result['pages']['heat_transfer'])
        self.assertNotIn('section-robust', heat)

    def test_the_filter_script_and_the_stylesheet_know_the_robust_rows(self):
        script = (ROOT/'website/assets/suite.js').read_text(encoding='utf-8')
        self.assertIn("(element.dataset.across || '').split(' ').includes(axis) || matches(axis, element.dataset[axis], value)", script)
        css = (ROOT/'website/assets/site.css').read_text(encoding='utf-8')
        self.assertIn('.ea-suite .ea-robust td:nth-child(n+3)', css)
        self.assertIn('.ea-suite .ea-ties', css)


class DigestTests(unittest.TestCase):
    def test_the_site_digest_covers_the_drop_the_schema_and_the_generator(self):
        self.assertIn('data/lod-recommendations', suite_site.DIGEST_INPUTS)
        self.assertIn('schemas', suite_site.DIGEST_INPUTS)
        self.assertIn('scripts.lod_site', suite_site.generator_modules())


if __name__ == '__main__':
    unittest.main()
