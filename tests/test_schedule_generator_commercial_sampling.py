import importlib.util
import json
import random
from pathlib import Path
import unittest

from atlas_schedules.errors import GeneratorError
from atlas_schedules.resources import ResourceSet
from scripts.schedule_generator_reference import load_commercial_reference

ROOT = Path(__file__).resolve().parents[1]


class CommercialSamplingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resources = ResourceSet.load(json.loads((ROOT/'atlas_schedules/data/manifest.json').read_text())['resource_set_id'])

    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('atlas_schedules.commercial'), 'Commercial kernel is missing')
        from atlas_schedules.commercial.sampling import sample_operating_parameters, select_conditional
        self.sample, self.select = sample_operating_parameters, select_conditional

    def test_standalone_sampling_policy_and_context_are_explicit(self):
        result = self.sample({'building_type': 'medium_office'}, 42, self.resources)
        self.assertEqual(result['sampler_policy']['name'], 'atlas_conditional_seeded_v1')
        self.assertEqual(result['conditioning_inputs'], {'building_type': 'medium_office'})
        self.assertEqual(result['group_seed'], 42)
        self.assertEqual(len(result['draw_receipts']), 10)
        self.assertIsNone(result['upstream_population_context']['sample_index'])
        self.assertIsNone(result['upstream_population_context']['sampler_mode'])
        self.assertIn('CLI Sobol',result['upstream_population_context']['upstream_cli_modes'])
        self.assertIn('Python', result['rng']['algorithm'])

    def test_wrapper_seed_reproducibility(self):
        a = self.sample({'building_type': 'medium_office'}, 42, self.resources)
        self.assertEqual(a, self.sample({'building_type': 'medium_office'}, 42, self.resources))
        rng = random.Random(42)
        self.assertEqual([r['uniform'] for r in a['draw_receipts']], [rng.random() for _ in range(10)])
        self.assertNotEqual(a['draw_receipts'], self.sample({'building_type': 'medium_office'}, 43, self.resources)['draw_receipts'])

    def test_no_population_equivalence_claim(self):
        self.assertIs(self.sample({'building_type': 'medium_office'}, 1, self.resources)['population_realization_equivalent'], False)

    def test_operating_sample_matches_conditional_row(self):
        # Native pinned _com_execute_samples determines these expected options,
        # independently of this wrapper's seed and selection implementation.
        for vector in load_commercial_reference()['conditional_vectors']:
            selected=self.select(self.resources.get('commercial',vector['parameter']),vector['selectors'],vector['uniform'])
            self.assertEqual(selected['source_row'],vector['source_row'])
            self.assertEqual(selected['original_option'],vector['selected_option'])
        result = self.sample({'building_type': 'medium_office'}, 42, self.resources)
        for receipt in result['draw_receipts']:
            table = self.resources.get('commercial', receipt['parameter'])
            selected = self.select(table, receipt['selectors'], receipt['uniform'])
            self.assertEqual(selected, receipt['selection'])
            self.assertEqual(receipt['selection']['original_option'], result['selected_options'][receipt['parameter']])

    def test_cumulative_probability_boundaries(self):
        table = {'dependencies': ['building_type'], 'options': ['a', 'b'],
                 'rows': [{'source_row': 4, 'selectors': {'building_type': 'medium_office'},
                           'original_values': ['0.25', '0.749999999'], 'probabilities': [.25, .749999999]}]}
        for draw, expected in [(0, 'a'), (.24999999, 'a'), (.25, 'b'), (.9, 'b')]:
            self.assertEqual(self.select(table, {'building_type': 'medium_office'}, draw)['original_option'], expected)
        with self.assertRaises(GeneratorError) as error:
            self.select(table, {'building_type': 'medium_office'}, .9999999995)
        self.assertEqual(error.exception.code, 'source_selection')

    def test_na_flags_and_missing_dependencies(self):
        table = {'dependencies': ['building_type', 'mode'], 'options': ['NA'], 'option_values': [None], 'option_unit': '1',
                 'rows': [{'source_row': 2, 'selectors': {'building_type': 'medium_office', 'mode': 'off'},
                           'original_values': ['1'], 'probabilities': [1.0]}]}
        selection = self.select(table, {'building_type': 'medium_office', 'mode': 'off'}, .5)
        self.assertIsNone(selection['value']); self.assertIs(selection['modify'], False)
        for selectors in ({'building_type': 'medium_office'}, {'building_type': 'unknown', 'mode': 'off'}):
            with self.assertRaises(GeneratorError): self.select(table, selectors, .5)
        for inputs in ({}, {'building_type': 'office'}, {'building_type': 'medium_office', 'weekday_duration': 8}):
            with self.assertRaises(GeneratorError): self.sample(inputs, 42, self.resources)
        for seed in (True, -1, 1.2):
            with self.assertRaises(GeneratorError): self.sample({'building_type': 'medium_office'}, seed, self.resources)

    def test_unresolved_or_changed_audit_cannot_sample(self):
        original=self.resources
        class ChangedAudit:
            def __init__(self,audit): self.audit=audit
            def get(self,kind,key):
                return self.audit if (kind,key)==('commercial','sampling-audit') else original.get(kind,key)
        for change in ({'stock_year_context':None},{'tsv_version':'v32'},{'conditioning_inputs':{'building_type':'large_office'}}):
            audit=self.resources.get('commercial','sampling-audit');audit.update(change)
            with self.assertRaises(GeneratorError):
                self.sample(audit['conditioning_inputs'],42,ChangedAudit(audit))
