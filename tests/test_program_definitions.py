import unittest
import tempfile
from pathlib import Path
from scripts.common import dump_json
from scripts.definition_contract import BuildContext, DefinitionError
from scripts.program_definitions import build_programs, evaluate_load, unique_services


class ProgramTests(unittest.TestCase):
    def test_load_scaling_and_unknown(self):
        load = {'value': 10, 'basis': 'floor_area', 'quantity': 'electricity'}
        self.assertEqual(evaluate_load(load, {'floor_area': 20}, 0.5), 100)
        self.assertIsNone(evaluate_load(dict(load, value=None), {'floor_area': 20}, 0.5))
        with self.assertRaises(DefinitionError):
            evaluate_load(load, {}, 0.5)

    def test_service_references_do_not_duplicate_equipment(self):
        service = {'id': 'lift', 'value': 500}
        self.assertEqual(sum(s['value'] for s in unique_services([service, service])), 500)
        with self.assertRaises(DefinitionError):
            unique_services([service, {'id': 'lift', 'value': 1000}])

    def test_unknown_program_load_is_preserved(self):
        source = {'id': 'p', 'building_type': 'MediumOffice', 'program': 'office',
                  'template': '90.1-2019', 'source_family': 'code_prototype_rules',
                  'lighting_W_m2': 10, 'electric_equipment_W_m2': None,
                  'source_attributes': {}, 'provenance_id': 'pv'}
        context = BuildContext(atlas={'programs': [source], 'schedules': [],
              'provenance': [{'id': 'pv', 'source_file_id': 'sf', 'locator': '/row/1',
                              'fields': {}}]})
        bundle = build_programs(context)
        loads = {r['quantity']: r for r in bundle['programs'][0]['loads']}
        self.assertEqual(loads['lighting']['value'], 10)
        self.assertIsNone(loads['electric_equipment']['value'])
        self.assertIn('floor_area', loads['lighting']['required_inputs'])

    def test_reviewed_schedule_does_not_overwrite_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            dump_json(root/'resolution/resolutions.json', {'resolutions': [
                {'record_table': 'programs', 'record_id': 'p', 'field': 'lighting_schedule_id',
                 'resolved_value': {'constant_value': 0, 'calendar_independent': True},
                 'unit': 'dimensionless', 'id': 'resolution-test', 'note': 'Approved absence'}]})
            source = {'id': 'p', 'program': 'office', 'building_type': 'MediumOffice',
                      'source_family': 'code_prototype_rules', 'template': '90.1-2019',
                      'lighting_W_m2': None, 'source_attributes': {}}
            b = build_programs(BuildContext(root=root, atlas={'programs': [source]},
                              policy={'dependencies': {'resolution': 'resolution'}}))
            views = {r['evidence_view']: r for r in b['programs']}
            self.assertIsNone(views['source']['loads'][1]['schedule_id'])
            self.assertIsNotNone(views['reviewed']['loads'][1]['schedule_id'])
            self.assertIsNone(views['reviewed']['loads'][1]['value'])


if __name__ == '__main__': unittest.main()
