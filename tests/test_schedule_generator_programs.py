"""Source recipe resolution protects original budgets and physical identities."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from atlas_schedules.errors import GeneratorError
from atlas_schedules.resources import ResourceSet

ROOT = Path(__file__).resolve().parents[1]
OFFICE = 'program-0e670d8dc556f7f5bdd7f1a9'
OCCUPIED = 'program-03fe19ed8968e605f4be3b8d'
VACANT = 'program-e0993499165be6c7b5bf9efa'


class RecipeResourceCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.resources = None

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('atlas_schedules.programs'),
                             'program recipe implementation is missing')
        from atlas_schedules.programs import resolve_program
        self.resolve = resolve_program
        if self.__class__.resources is None:
            from scripts.schedule_generator_build import build_resources
            root = Path(self.temporary.name)/'resources'
            manifest = build_resources(root, 'pilot', root.parent/'tables')
            self.__class__.resources = ResourceSet(root, manifest['resource_set_id'])

    def inputs(self, program_id):
        recipe = self.resources.get('program', program_id)['recipe']
        return dict(copy.deepcopy(recipe['bound_inputs']), year=2007, holidays=[])


class ProgramTests(RecipeResourceCase):

    def test_original_budgets_precede_reference_fitted_magnitudes(self):
        result = self.resolve(OCCUPIED, self.inputs(OCCUPIED), self.resources)
        demand = next(d for d in result['demands'] if d['quantity'] == 'refrigerator')
        self.assertEqual(demand['annual_target']['total'], 434000)
        self.assertEqual(demand['annual_target']['unit'], 'Wh/dwelling')
        self.assertEqual(demand['annual_target']['evidence']['original_value']['annual_kwh'], 434)
        self.assertIn('source_file_sha256', demand['annual_target']['evidence'])
        dryers = [d for d in result['demands'] if d['quantity'] == 'clothes_dryer']
        self.assertEqual({d['fuel'] for d in dryers}, {'electricity', 'natural gas'})
        self.assertEqual(len({d['demand_id'] for d in dryers}), 2)
        self.assertEqual({d['host'] for d in dryers}, {'assigned_zone'})

    def test_reference_commercial_budget_is_pre_sampling(self):
        from atlas_schedules.budgets import bind_budget
        from atlas_schedules.commercial.sampling import sample_operating_parameters
        from atlas_schedules.commercial.parametric import transform_commercial
        result = self.resolve(OFFICE, self.inputs(OFFICE), self.resources)
        context = result['inputs']['source_context']
        self.assertEqual(context['occupancy_aggregation']['constituents'][0]['nominal_people'], 1)
        demand = next(d for d in result['demands'] if d['quantity'] == 'lighting')
        target = result['inputs']['reference_budgets'][demand['demand_id']]
        # 2007 has 261 weekdays, 52 Saturdays and 52 Sundays. Source day sums.
        self.assertAlmostEqual(target['total'], 8.82640654170197 *
                               (261*9.10260484 + 52*2.4902326 + 52*1.11739536), places=7)
        totals = []
        for seed in (42, 51):
            operating = sample_operating_parameters({'building_type': 'medium_office'}, seed, self.resources)
            generated = transform_commercial(result['inputs']['reference_channels'], operating, context)
            totals.append(bind_budget(target, generated['channels'][demand['slot']])['reference_target']['total'])
        self.assertEqual(totals, [target['total'], target['total']])

    def test_missing_appliance_shares_are_unsupported(self):
        recipe = self.resources.get('program', OCCUPIED)['recipe']
        self.assertEqual(recipe['aggregate_binding_policy'], 'source_recovered_physical_demands')
        index = self.resources.get('reference', 'catalogue-index')
        unavailable = next(p['id'] for p in index['programs'] if p['status'] == 'unsupported_binding')
        with self.assertRaises(GeneratorError) as raised:
            self.resolve(unavailable, {'year': 2007}, self.resources)
        self.assertEqual(raised.exception.code, 'unsupported_binding')

    def test_exact_case_inputs_and_catalogue_closure(self):
        scope = self.resources.get('reference', 'm1-scope')
        self.assertEqual(len(scope['cases']), 10)
        index = self.resources.get('reference', 'catalogue-index')
        self.assertEqual(len(index['programs']), 1900)
        self.assertEqual(len(index['compositions']), 378)
        from jsonschema import Draft202012Validator
        validator = Draft202012Validator(json.loads((ROOT/'schemas/schedule-generator-program-v1.schema.json').read_text()))
        for case in scope['cases']:
            with self.subTest(program=case['program_id']):
                resolved = self.resolve(case['program_id'], self.inputs(case['program_id']), self.resources)
                self.assertEqual(list(validator.iter_errors(resolved)), [])
                self.assertEqual(resolved['source']['evidence_view'], case['evidence_view'])
        bad = self.inputs(OCCUPIED)
        bad.pop('installed')
        with self.assertRaises(GeneratorError) as raised:
            self.resolve(OCCUPIED, bad, self.resources)
        self.assertEqual(raised.exception.code, 'missing_input')
        bad = self.inputs(OFFICE)
        bad['carrier_policy'] = 'infer_geometry'
        with self.assertRaises(GeneratorError):
            self.resolve(OFFICE, bad, self.resources)

    def test_accepted_inactive_plenum_has_receipts_without_fabricated_slots(self):
        plenum = 'program-e784bf91b3765d28c5d61368'
        result = self.resolve(plenum, self.inputs(plenum), self.resources)
        self.assertEqual(result['slots'], [])
        self.assertEqual(result['demands'], [])
        self.assertTrue(result['evidence'][0]['accepted_absence'])
        self.assertEqual(result['inputs']['source_context']['configuration_id'], 'medium_office_90_1_2013')

    def test_boolean_presence_and_calendar_operands_are_strict(self):
        for key, value in [('installed', dict(self.inputs(OCCUPIED)['installed'], dishwasher=1)),
                           ('holidays', None), ('residents', True)]:
            with self.subTest(key=key):
                bad = self.inputs(OCCUPIED)
                bad[key] = value
                with self.assertRaises(GeneratorError):
                    self.resolve(OCCUPIED, bad, self.resources)

    def test_unknown_active_cannot_masquerade_as_inactive(self):
        from atlas_schedules.resources import write_resources
        index = self.resources.get('reference', 'catalogue-index')
        record = self.resources.get('program', OCCUPIED)
        record['recipe']['resolved']['slots'] = []
        record['recipe']['resolved']['demands'] = []
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            manifest = write_resources(root, {('reference', 'catalogue-index'): index,
                    ('program', OCCUPIED): record}, {})
            bad = ResourceSet(root, manifest['resource_set_id'])
            with self.assertRaises(GeneratorError) as raised:
                self.resolve(OCCUPIED, self.inputs(OCCUPIED), bad)
            self.assertEqual(raised.exception.code, 'unsupported_binding')

    def test_compiler_reproduces_packaged_resources_and_inspection_tables(self):
        manifest = json.loads((ROOT/'atlas_schedules/data/manifest.json').read_text())
        self.assertEqual(self.resources.manifest, manifest)
        for name in ('programs', 'compositions', 'catalogue-index', 'coverage'):
            self.assertEqual((Path(self.temporary.name)/'tables'/(name+'.json')).read_bytes(),
                             (ROOT/'data/schedule-generator'/(name+'.json')).read_bytes())

    def test_recovered_equipment_keeps_ready_v3_physical_component_ids(self):
        resolved = self.resolve(OCCUPIED, self.inputs(OCCUPIED), self.resources)
        components = [c['load'] for group in resolved['evidence'][0]['aggregation']['groups'] for c in group['components']]
        for component in components:
            demand = next(d for d in resolved['demands'] if d['quantity'] == component['end_use']
                          and d['fuel'] == component['fuel'] and d['host'] == component['host'])
            self.assertEqual(demand['demand_id'], component['demand_id'])

    def test_changed_ready_exporter_dependency_fails_source_integrity(self):
        from scripts import schedule_generator_build as builder
        scope = json.loads((ROOT/'sources/schedule-generator-m1-scope.json').read_text())
        source_lock = json.loads((ROOT/'sources/schedule-generator-lock.json').read_text())
        required = {'sources/schedule-generator-m1-scope.json', 'data/schedule-generator/comstock-sampling-audit.json'}
        for case in scope['cases']:
            required.add(case['program_definition']['file'])
            if 'file' in case['configuration']:
                required.add(case['configuration']['file'])
        for dependency in ('data/releases/v0.2.0/programs.json', 'data/program-inputs/er-triage-v1.json'):
            with self.subTest(dependency=dependency), tempfile.TemporaryDirectory() as d:
                self.assertIn(dependency, source_lock['frozen_files'], 'Ready exporter dependency must be source locked')
                root = Path(d)
                for name in required | {dependency}:
                    target = root/name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(ROOT/name, target)
                lock = copy.deepcopy(source_lock)
                lock['frozen_files'] = {k: v for k, v in lock['frozen_files'].items() if k == dependency}
                (root/'sources/schedule-generator-lock.json').write_text(json.dumps(lock), encoding='utf-8')
                (root/dependency).write_bytes(b'{}\n')
                # Only the filesystem root is redirected; all guards execute real code.
                with patch.object(builder, 'ROOT', root), self.assertRaises(GeneratorError) as raised:
                    builder.build_resources(root/'out', 'pilot')
                self.assertEqual(raised.exception.code, 'source_integrity')
                self.assertEqual(raised.exception.path, dependency)
                self.assertFalse((root/'out').exists())
