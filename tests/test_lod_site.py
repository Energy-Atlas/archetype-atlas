"""The zoning-recommendation data drop and its pages (ADR 0050)."""
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
        self.assertEqual(self.site.zoning_of['90-1-2007.retail-standalone.source.entry.62d108'], [('Stand-alone retail', 'zoning/stand-alone-retail/')])
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


class DigestTests(unittest.TestCase):
    def test_the_site_digest_covers_the_drop_the_schema_and_the_generator(self):
        self.assertIn('data/lod-recommendations', suite_site.DIGEST_INPUTS)
        self.assertIn('schemas', suite_site.DIGEST_INPUTS)
        self.assertIn('scripts.lod_site', suite_site.generator_modules())


if __name__ == '__main__':
    unittest.main()
