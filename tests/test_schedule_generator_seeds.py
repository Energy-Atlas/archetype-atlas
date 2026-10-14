"""Source order, unsigned master domain, and explicit commercial adaptation."""
import math
import unittest
from atlas_schedules.errors import GeneratorError
try:
    from atlas_schedules.seeds import assign_unit_seeds, commercial_group_seed, source_streams
except ImportError:
    assign_unit_seeds = commercial_group_seed = source_streams = None

class SeedTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(assign_unit_seeds, 'source seed implementation is missing')

    def test_master_seed_domain_and_unique_keys(self):
        for invalid in [True, False, -1, 2**64, 42.0, None]:
            with self.subTest(seed=invalid), self.assertRaises(GeneratorError):
                assign_unit_seeds(invalid, ['a'])
        for keys in [['a','a'], [''], [4], 'ab']:
            with self.subTest(keys=keys), self.assertRaises(GeneratorError):
                assign_unit_seeds(42, keys)
        self.assertEqual(assign_unit_seeds(2**64-1, ['a'])['a'], 2**64-1)

    def test_native_multifamily_seed_sequence(self):
        self.assertEqual(list(assign_unit_seeds(42, ['a','b','c']).values()), [42,84,252])
        self.assertEqual(list(assign_unit_seeds(0, ['a','b','c']).values()), [0,0,0])
        keys = [str(i) for i in range(30)]
        self.assertEqual(assign_unit_seeds(42,keys)['29'], 42*math.factorial(30))
        self.assertEqual(assign_unit_seeds(42, ['c','a'])['a'], 84)
        self.assertEqual(assign_unit_seeds(42, []), {})

    def test_enduse_reservation_and_coupling(self):
        streams = source_streams(42)
        self.assertEqual(list(streams), ['main','hygiene','dishwasher','clothes_washer','clothes_dryer','ev','cooking'])
        # These are actual Ruby3.2.2 rand(2**32) values; EV still consumes slot 5.
        self.assertEqual([streams[k].getstate()['seed'] for k in list(streams)[1:]],
                         [1608637542,3421126067,4083286876,787846414,3143890026,3348747335])
        self.assertEqual(streams['main'].random(), 0.3745401188473625)

    def test_commercial_group_seed_full_digest(self):
        import hashlib
        expected = int.from_bytes(hashlib.sha256(b'["atlas_conditional_seeded_v1",42,"office-group"]\n').digest(),'big')
        self.assertEqual(commercial_group_seed(42, 'office-group'), expected)
        self.assertNotEqual(commercial_group_seed(42, 'a'), commercial_group_seed(42, 'b'))
        for bad in [None,'',True]:
            with self.assertRaises(GeneratorError): commercial_group_seed(42,bad)
        with self.assertRaises(GeneratorError): commercial_group_seed(2**64,'a')

    def test_all_captured_enduse_allocations(self):
        import json
        from pathlib import Path
        vectors=json.loads(Path('data/schedule-generator/reference-vectors.json').read_bytes())
        for vector in vectors['enduse_vectors']:
            with self.subTest(seed=vector['unit_seed']):
                streams=source_streams(vector['unit_seed'])
                self.assertEqual([{'key':key,'seed':streams[key].getstate()['seed']} for key in list(streams)[1:]],vector['slots'])
