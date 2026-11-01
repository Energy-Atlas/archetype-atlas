"""Release 2.3.0's record edits over release 2.2.0 (ADR 0053), and its exports in the 2.3.0 contracts (ADR 0054)."""
import json
import math
import os
import unittest
from collections import Counter, defaultdict
from functools import cached_property
from pathlib import Path

from atlas_schedules import programmes
from atlas_schedules.release import Release as Reader, TreeStore
from scripts import atlas_constructions, atlas_contracts, atlas_delta, atlas_edits, release_editor
from scripts.atlas_exports import Release
from scripts.common import ROOT, load_json
from scripts.construction_equivalent_export import mass_agrees

SMALL_HOTEL = ('90-1-2007', '90-1-2013', '90-1-2019')


class MemoryStore(TreeStore):
    """A resolved release held in memory, for the generator's reader (no delta folder is written before REL-A)."""

    def __init__(self, files):
        self.folder = Path('memory')
        self.files = files
        self.manifest = {'release': atlas_edits.RELEASE, 'generation': {'schema_version': atlas_delta.GENERATION_SCHEMA}, 'files': {}}
        self.manifest_sha256 = '0'*64
        self.version = atlas_edits.RELEASE
        self.base = None
        self.removed = set()

    @cached_property
    def paths(self):
        return {p: p for p in self.files}

    def json(self, path):
        return json.loads(self.files[path])

    def describe(self):
        return 'release 2.3.0 in memory'


class EditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = atlas_delta.files(atlas_edits.BASE)
        cls.edited = atlas_edits.edit(cls.base)
        cls.files = cls.edited.resolved(cls.base)
        cls.points = load_json(atlas_edits.POINT_LOADS)
        cls.names = load_json(atlas_edits.NAMES)

    @classmethod
    def tearDownClass(cls):
        del cls.base, cls.edited, cls.files

    def records(self, files=None):
        files = files or self.files
        return {json.loads(d)['id']: (p, json.loads(d)) for p, d in files.items() if p.startswith('commercial/') and '/programs/' in p}

    def test_ids_follow_their_rules_and_no_file_cites_a_moved_id(self):
        self.assertEqual(release_editor.program_ids(self.files), {})
        self.assertEqual(release_editor.set_ids(self.files, {}), {})
        moved = release_editor.Substitution({old: '@moved@' for old in self.edited.ids})
        stale = [p for p, d in self.files.items() if p.endswith('.json') and not p.startswith('residential/') and p != 'id-map.json'
                 and '@moved@' in moved(d.decode('utf-8'))]
        self.assertEqual(stale, [])
        self.assertEqual(set(self.edited.removed), {p for p in self.base if p not in self.files})
        kinds = Counter('set' if '.construction-' in i else 'program' for i in self.edited.ids)
        self.assertEqual(kinds['set'], 12)
        self.assertGreater(kinds['program'], 1500)
        self.assertEqual(json.loads(atlas_edits.id_map_bytes(self.edited.ids))['ids'], self.edited.ids)

    def test_every_edited_file_meets_its_release_record_schema(self):
        from scripts import release_schemas
        self.assertEqual(release_schemas.errors(self.edited.files), [])

    def test_every_file_keeps_its_storage_format(self):
        scope = [p for p in self.base if p.endswith('.json') and not p.startswith('residential/') and p != 'id-map.json'
                 and '/library/' not in p]
        self.assertEqual([p for p in scope if atlas_edits.encode(p, json.loads(self.base[p])) != self.base[p]], [])
        for path, data in self.edited.files.items():
            with self.subTest(path=path):
                self.assertEqual(atlas_edits.encode(path, json.loads(data)), data)

    def test_unified_internal_mass_counts_the_whole_inventory(self):
        suite = atlas_constructions.read_files(self.files)
        checked = 0
        for sid, record in suite.sets.items():
            if 'common' not in record:
                continue
            for key in record['contexts']:
                if 'unified' in record['contexts'][key]:
                    self.assertTrue(mass_agrees(suite.export(sid, key, 'unified')), f'{sid} {key}')
                    checked += 1
        self.assertEqual(checked, 5138)
        self.assertEqual(len(self.edited.summary['internal_mass']), 8)
        warehouse = next(s for s in suite.sets if s.startswith('doe-ref-pre-1980.warehouse.'))
        component = suite.export(warehouse, '4-a', 'unified')['components']['InternalMass']
        self.assertAlmostEqual(component['quantity']['area_per_counted_floor_area'], 2.0, places=6)

    def test_the_small_hotel_elevator_takes_the_pnnl_value_and_its_mixes_follow(self):
        records = self.records()
        for entry in self.points['exceptions']:
            new = self.edited.ids[entry['program_id']]
            path, record = records[new]
            load = next(l for l in record['loads'] if l['quantity'] == 'electric_equipment')
            self.assertEqual(load['value'], entry['design_level_W']/entry['zone_floor_area_m2'])
            self.assertAlmostEqual(load['value'], 1064.717, places=3)
            evidence = json.loads(self.files['evidence/'+entry['folder']+'.json'])[load['evidence_id']]
            self.assertEqual(evidence['locator'], 'ElevatorCoreFlr1_Elevators_Equip/Design Level {W}')
            self.assertEqual(evidence['original_value']['design_level_W'], 16024.3)
            glossary = json.loads(self.files['evidence/glossary.json'])
            self.assertEqual(glossary['source_files'][evidence['source_file']]['sha256'], entry['source_file']['sha256'])
            mixes = [r for _, r in records.values() if r.get('composition') and new in {m['program_id'] for m in r['composition']['members']}]
            support = next(r for r in mixes if r['name'] == 'Support_Mixed_SmallHotel')
            mixed = next(l for l in support['loads'] if l['quantity'] == 'electric_equipment')
            members = {m['program_id']: m['weight'] for m in support['composition']['members']}
            expected = math.fsum(w*next(l['value'] for l in records[pid][1]['loads'] if l['quantity'] == 'electric_equipment')
                                 for pid, w in members.items())
            self.assertAlmostEqual(mixed['value'], expected, places=12)
            self.assertAlmostEqual(mixed['value'], 67.88, places=2)
            table = json.loads(self.files[entry['folder']+'/schedules.json'])
            self.assertIn(mixed['schedule_id'], table['schedules'])

    def test_the_mix_recomposition_reproduces_the_stored_mixes(self):
        tree = atlas_edits.Tree(self.base)
        for template in SMALL_HOTEL:
            folder = f'commercial/{template}/small-hotel'
            for path in atlas_edits.folder_paths(tree, folder):
                mix = tree[path]
                if 'composition' not in mix:
                    continue
                for load in mix['loads']:
                    if load['value'] is None:
                        continue
                    value, mixed, _ = atlas_edits.mixed_load(tree, folder, mix, load['quantity'])
                    self.assertTrue(math.isclose(value, load['value'], rel_tol=1e-12), f'{mix["id"]} {load["quantity"]}')
                    stored = atlas_edits.schedule_of(tree, folder, load['schedule_id'])
                    self.assertEqual([(r['day_types'], r['start_date'][5:10], r['values']) for r in stored['rules']],
                                     [(r['day_types'], r['start_date'][5:10], r['values']) for r in mixed['rules']])

    def test_every_unknown_load_has_its_reason_and_source_unknowns_their_filling(self):
        glossary = json.loads(self.files['evidence/glossary.json'])
        for pid, (path, record) in self.records().items():
            for load in record['loads']:
                filled = atlas_edits.filled_entry(load, True)
                if load['value'] is None:
                    self.assertIn(load.get('unresolved'), glossary['unresolved'], f'{pid} {load["quantity"]}')
                if record['mode'] == 'source':
                    self.assertIsNotNone(filled['value'], f'{pid} {load["quantity"]}: unknown in the filled view')
        self.assertGreaterEqual(sum(len(v) for v in self.edited.summary['accepted_absence'].values()), 1596)

    def test_names_tell_records_apart(self):
        groups = Counter((p.split('/programs/')[0], r['mode'], r['name']) for p, r in self.records().values())
        self.assertEqual([k for k, c in groups.items() if c > 1], [])
        suite = atlas_constructions.read_files({p: d for p, d in self.files.items() if p.startswith('commercial/') and '/constructions/' in p})
        sets = Counter((sid.rsplit('.', 2)[0], r['name']) for sid, r in suite.sets.items())
        self.assertEqual([k for k, c in sets.items() if c > 1], [])
        renamed = self.records()[self.edited.ids.get('90-1-2007.super-tall-building.source.corridor.609e28',
                                                     '90-1-2007.super-tall-building.source.corridor.609e28')][1]
        self.assertEqual(renamed['name'], 'Corridor (LargeHotel)_SuperTallBuilding')

    def test_the_generator_assembles_the_edited_small_hotel(self):
        reader = Reader(MemoryStore(self.files))
        views = 0
        for template in SMALL_HOTEL:
            folder = f'commercial/{template}/small-hotel'
            document = reader.generation(folder)
            for rid, block in document['programs'].items():
                for view in block['views']:
                    programmes.assemble(reader, rid, view)
                    views += 1
        self.assertGreater(views, 30)
        recipe_ids = set(reader.generation('commercial/90-1-2019/small-hotel')['programs'])
        self.assertTrue(recipe_ids <= set(reader.program_paths))

    def test_exports_take_the_2_3_0_contracts(self):
        release = Release(files=self.files, release='2.3.0')
        records = self.records()
        sample = [self.edited.ids[e['program_id']] for e in self.points['exceptions']]
        sample += sorted(i for i in release.program_ids() if '.small-hotel.' in i and i.startswith('90-1-2019'))[:6]
        sample += [next(i for i in release.program_ids() if i.startswith('iecc-2021.medium-office.source.'))]
        for pid in sample:
            for version in ('source', 'filled') if not pid.startswith('iecc-') else ('source',):
                with self.subTest(program=pid, version=version):
                    document = release.program(pid, version)
                    self.assertEqual((document['schema_version'], document['source']['release']), ('6.0.0', 'atlas-release-2.3.0'))
                    ids = {e['id'] for e in document['source']['evidence']}
                    self.assertEqual(atlas_contracts.cited({k: v for k, v in document.items() if k not in ('source', 'metadata')}) - ids, set())
                    self.assertEqual(set(document['nulls']), set(p for k, v in document.items() if k not in ('metadata', 'schedules', 'source', 'nulls')
                                                                  for p in atlas_contracts.null_pointers(v, '/'+k)))
                    for load in document['loads']:
                        self.assertIn(load['status'], ('known', 'unknown', 'filled'))
                        self.assertEqual(load['status'] == 'unknown', load['value'] is None)
        source = release.program(sample[2], 'source')
        unknown = [l for l in source['loads'] if l['status'] == 'unknown']
        self.assertTrue(unknown and all(l['reason'] and l['reason_id'].startswith('u-') for l in unknown))
        filled = release.program(sample[2], 'filled')
        self.assertTrue(any(a['status'] == 'filled' and 'accepted_absence' in a['filling']['rules']
                            for a in filled['metadata']['absent_demands']))
        elevator = next(l for l in filled['loads'] if l['end_use'] == 'electric_equipment')
        self.assertAlmostEqual(elevator['value'], 1064.717, places=3)
        warehouse = next(s for s in sorted(release.constructions.sets) if s.startswith('doe-ref-pre-1980.warehouse.'))
        unified = release.construction(warehouse, '4-a', 'unified')
        detailed = release.construction(warehouse, '4-a', 'detailed')
        self.assertEqual((unified['schema_version'], unified['release']), ('4.0.0', 'atlas-release-2.3.0'))
        self.assertEqual(unified['provenance']['construction_delivery_release'], 'v2.2.0')
        self.assertNotIn('detailed_release', unified['provenance'])
        self.assertEqual((detailed['schema_version'], detailed['release']), ('5.0.0', 'atlas-release-2.3.0'))
        self.assertNotIn('export_mode', detailed)
        self.assertEqual(detailed['source']['construction_definition_release'], 'v0.1.1')
        services = release.building_services('doe-ref-1980-2004/hospital')
        self.assertEqual((services['schema_version'], services['release']), ('1.0.1', 'atlas-release-2.3.0'))

    def test_filled_values_change_only_where_the_edits_change_them(self):
        before, after = self.records(self.base), self.records()
        changed = {e['program_id'] for e in self.points['exceptions']}
        differ = set()
        for old, (_, record) in before.items():
            if record['mode'] != 'source':
                continue  # a mix's filled export recomputes from its members; its new fillings record that value
            new = after[self.edited.ids.get(old, old)][1]
            values = lambda r: sorted((l['demand_id'], atlas_edits.filled_entry(l, True)['value'] or 0) for l in r['loads'])
            if values(record) != values(new):
                differ.add(old)
        self.assertEqual(differ, changed)


class InputTests(unittest.TestCase):
    """The committed inputs reproduce from their sources where the sources are on this machine."""

    def test_point_loads_reproduce_from_the_pnnl_idfs(self):
        from scripts import pnnl_point_loads
        from scripts.lighting_controls import prototype_root
        if not (prototype_root()/'commercial-ashrae901/ASHRAE901_HotelSmall').is_dir():
            self.skipTest('PNNL prototype IDFs not on this machine (ATLAS_PROTOTYPE_ROOT)')
        self.assertEqual(pnnl_point_loads.encode(pnnl_point_loads.build()), pnnl_point_loads.OUTPUT.read_bytes())

    def test_the_point_load_input_is_the_small_hotel_elevator(self):
        document = load_json(atlas_edits.POINT_LOADS)
        self.assertEqual([e['template'] for e in document['exceptions']], ['90.1-2007', '90.1-2013', '90.1-2019'])
        for entry in document['exceptions']:
            self.assertEqual((entry['design_level_W'], entry['zone'], entry['cities']), (16024.3, 'ElevatorCoreFlr1', 19))
            self.assertAlmostEqual(entry['zone_floor_area_m2'], 15.0503, places=4)
            self.assertIn('second 32 110 W motor', document['interpretation'])

    def test_names_reproduce_from_their_sources(self):
        from scripts import distinguishing_names
        entry = load_json(ROOT/'data/atlas-releases/v2.0.0/evidence/glossary.json')['source_files']['sourcefile-9ff206ef97eb739f22a8']
        if not (distinguishing_names.raw_root()/'openstudio-standards'/entry['path']).is_file():
            self.skipTest('openstudio-standards cache not on this machine (ATLAS_RAW_ROOT)')
        self.assertEqual(distinguishing_names.encode(distinguishing_names.build()), distinguishing_names.OUTPUT.read_bytes())


if __name__ == '__main__':
    unittest.main()
