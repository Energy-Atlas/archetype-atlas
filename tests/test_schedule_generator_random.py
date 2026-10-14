"""Exact vectors captured from locked Ruby, never from the Python port."""
import copy
import json
from pathlib import Path
import unittest
from atlas_schedules.errors import GeneratorError
try:
    from atlas_schedules.ruby_random import SourceRandom
except ImportError:
    SourceRandom = None

GOLDEN = Path('data/schedule-generator/reference-vectors.json')
class RandomTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(SourceRandom, 'Ruby source RNG implementation is missing')

    def test_source_random_matches_golden_draws(self):
        fixture = json.loads(GOLDEN.read_bytes())
        for case in fixture['random_vectors']:
            with self.subTest(seed=case['seed']):
                rng = SourceRandom(case['seed'])
                self.assertEqual(rng.getstate()['state'],case['initial_state']['state'])
                self.assertEqual(rng.getstate()['index'],case['initial_state']['index'])
                for draw in case['draws']:
                    actual = rng.random() if draw['limit'] is None else rng.randbelow(draw['limit'])
                    self.assertEqual(actual,draw['value'])
                self.assertEqual(rng.getstate()['state'],case['final_state']['state'])
                self.assertEqual(rng.getstate()['index'],case['final_state']['index'])
                self.assertEqual([rng.random(),rng.randbelow(97),rng.randbelow(2**72+3)],case['restoration_draws'])

    def test_random_state_roundtrip(self):
        for seed in [0,42,2**64-1,42*265252859812191058636308480000000]:
            rng=SourceRandom(seed)
            for _ in range(625):rng.random()
            state=rng.getstate()
            expected=[rng.randbelow(97),rng.random(),rng.randbelow(2**72+3)]
            restored=SourceRandom(0);restored.setstate(json.loads(json.dumps(state)))
            self.assertEqual([restored.randbelow(97),restored.random(),restored.randbelow(2**72+3)],expected)
            state['state'][0]=0
            self.assertNotEqual(state,restored.getstate())

    def test_invalid_seed_limit_and_state_are_rejected(self):
        for seed in [True,-1,None,1.5]:
            with self.assertRaises(GeneratorError):SourceRandom(seed)
        rng=SourceRandom(42)
        state=rng.getstate()
        for limit in [True,0,-1,2.0,None]:
            with self.assertRaises(GeneratorError):rng.randbelow(limit)
        self.assertEqual(rng.getstate(),state)
        for invalid in [{},dict(state,index=625),dict(state,index=True),dict(state,state=[0]*624),dict(state,state=[-1]+state['state'][1:]),dict(state,seed=False),dict(state,algorithm='python')]:
            with self.assertRaises(GeneratorError):rng.setstate(invalid)
            self.assertEqual(rng.getstate(),state)

    def test_randbelow_one_consumes_no_draw(self):
        rng=SourceRandom(42);state=rng.getstate()
        self.assertEqual(rng.randbelow(1),0)
        self.assertEqual(rng.getstate(),state)

class ReferenceTests(unittest.TestCase):
    def test_reference_loader_checks_locked_capture_bytes(self):
        try:
            from scripts.schedule_generator_reference import load_reference_vectors
        except ImportError:
            self.fail('reference capture verification is missing')
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'vectors.json';file.write_bytes(GOLDEN.read_bytes())
            self.assertEqual(load_reference_vectors(file)['runtime']['ruby_version'],'3.2.2')
            file.write_bytes(file.read_bytes()+b' ')
            with self.assertRaises(GeneratorError):load_reference_vectors(file)

    def test_reference_vectors_are_packaged_and_offline(self):
        from atlas_schedules.resources import ResourceSet
        manifest=json.loads(Path('atlas_schedules/data/manifest.json').read_bytes())
        resources=ResourceSet.load(manifest['resource_set_id'])
        self.assertEqual(resources.get('reference','source-random-rule-vectors')['random_vectors'],json.loads(GOLDEN.read_bytes())['random_vectors'])
        self.assertIn('Makoto Matsumoto',resources.get('reference','notice-ruby-random')['text'])
