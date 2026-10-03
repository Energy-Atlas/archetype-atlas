import copy
import json
import pathlib
import tempfile
import unittest

from scripts import build, validate, fetch

ROOT = pathlib.Path(__file__).resolve().parents[1]


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.atlas = build.build_atlas(pilot=True)

    def test_medium_office_pilot_values_and_assignments(self):
        a = self.atlas
        p = next(p for p in a['programs'] if p['program'] == 'office')
        self.assertAlmostEqual(p['people_per_m2'], 5 / 92.90304)
        self.assertAlmostEqual(p['lighting_W_m2'], 0.82 / 0.09290304)
        self.assertAlmostEqual(p['electric_equipment_W_m2'], 0.75 / 0.09290304)
        self.assertIsNone(p['gas_equipment_W_m2'])
        self.assertEqual(sum(m['multiplicity'] for m in a['mappings'] if m['program_id'] == p['id']), 15)
        self.assertTrue(a['envelope_components'])
        self.assertTrue(a['efficiency_rules'])
        self.assertEqual(validate.validate_atlas(a), [])

    def test_byte_reproducibility_and_csv_exports(self):
        with tempfile.TemporaryDirectory() as d:
            one, two = pathlib.Path(d)/'one', pathlib.Path(d)/'two'
            build.write_atlas(self.atlas, one)
            build.write_atlas(build.build_atlas(pilot=True), two)
            self.assertEqual({p.name: p.read_bytes() for p in one.iterdir()},
                             {p.name: p.read_bytes() for p in two.iterdir()})
            self.assertTrue((one/'programs.csv').is_file())

    def mutate(self, change, message):
        a = copy.deepcopy(self.atlas)
        change(a)
        errors = validate.validate_atlas(a)
        self.assertTrue(any(message in e for e in errors), errors)

    def test_required_fields_and_duplicates(self):
        self.mutate(lambda a: a['programs'][0].pop('template'), 'schema')
        self.mutate(lambda a: a['programs'].append(a['programs'][0]), 'duplicate')

    def test_bad_units_and_impossible_values(self):
        self.mutate(lambda a: a['units'].__setitem__('lighting_W_m2', 'W/ft2'), 'units')
        self.mutate(lambda a: a['programs'][0].__setitem__('people_per_m2', -1), 'schema')
        self.mutate(lambda a: a['envelope_components'][0].__setitem__('u_W_m2_K', -1), 'schema')
        self.mutate(lambda a: a['envelope_components'][0].__setitem__('shgc', 1.1), 'schema')
        self.mutate(lambda a: a['programs'][0].__setitem__('infiltration_m3_s_m2', -1), 'schema')

    def test_schedule_bounds_length_and_deadband(self):
        p = next(p for p in self.atlas['programs'] if p['program'] == 'office')
        def set_values(a, sid, value):
            s = next(s for s in a['schedules'] if s['id'] == sid)
            for r in s['rules']:
                r['values'] = [value]*len(r['values'])
        self.mutate(lambda a: set_values(a, p['occupancy_schedule_id'], 1.1), 'schedule bounds')
        self.mutate(lambda a: a['schedules'][0]['rules'][0]['values'].append(0), 'schedule length')
        self.mutate(lambda a: set_values(a, p['heating_setpoint_schedule_id'], 40), 'deadband')

    def test_orphans_mapping_labels_and_provenance(self):
        self.mutate(lambda a: a['programs'][0].__setitem__('lighting_schedule_id', 'missing'), 'orphan')
        self.mutate(lambda a: a['mappings'][0].__setitem__('building_type', 'Other'), 'mapping')
        self.mutate(lambda a: a['programs'][0].__setitem__('template', 'unknown'), 'template')
        self.mutate(lambda a: a['envelope_components'][0].__setitem__('climate_zone_set', 'unknown'), 'climate')
        self.mutate(lambda a: a['provenance'][0]['fields'].clear(), 'provenance')
        self.mutate(lambda a: a['climate_zone_sets'].append('invented'), 'climate')

    def test_numeric_source_comparison_rejects_plausible_but_wrong_value(self):
        from scripts.compare import compare_sources
        a = copy.deepcopy(self.atlas)
        self.assertEqual(compare_sources(a)['errors'], [])
        p = next(p for p in a['programs'] if p['program'] == 'office')
        p['lighting_W_m2'] += 0.1
        self.assertTrue(compare_sources(a)['errors'])

    def test_raw_checksum_corruption_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            entry = {'source_id': 'test', 'path': 'blob', 'size_bytes': 4, 'sha256': '0'*64}
            p = pathlib.Path(d)/'test/blob'
            p.parent.mkdir()
            p.write_bytes(b'fake')
            with self.assertRaises(ValueError):
                fetch.verify_file(entry, pathlib.Path(d))

    def test_raw_path_traversal_rejected(self):
        with self.assertRaises(ValueError):
            fetch.cache_path({'source_id': 'test', 'path': '../escape'}, ROOT/'data/raw')

    def test_original_row_evidence_is_retained(self):
        p = self.atlas['programs'][0]
        prov = next(r for r in self.atlas['provenance'] if r['id'] == p['provenance_id'])
        self.assertEqual(prov['fields']['source_attributes']['original_value'], p['source_attributes'])

    def test_source_lock_metadata_cannot_be_forged(self):
        self.mutate(lambda a: a['source_files'][0].__setitem__('version', 'unverified'), 'source lock')

    def test_expansion_quarantines_impossible_legacy_u_values(self):
        a = build.build_atlas()
        invalid = [r for r in a['envelope_components']
                   if r['source_attributes'].get('assembly_maximum_u_value') == 0]
        self.assertEqual(len(invalid), 16)
        self.assertTrue(all(r['u_W_m2_K'] is None for r in invalid))
        self.assertTrue(a['commercial_options'])
        self.assertTrue(a['residential_options'])
        self.assertEqual(validate.validate_atlas(a), [])


if __name__ == '__main__':
    unittest.main()
