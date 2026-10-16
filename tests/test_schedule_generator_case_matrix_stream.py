"""Lockstep gzip reference comparison on small synthetic streams.

The comparer never parses the reference; these tests pin its byte accounting,
first-difference reporting and refusal of inauthentic or malformed gzip input.
"""
import gzip
import hashlib
from pathlib import Path
import tempfile
import unittest
import zlib

from atlas_schedules.errors import GeneratorError
from scripts import schedule_generator_case_matrix_stream as stream


def identity(blob):
    return {'size_bytes': len(blob), 'sha256': hashlib.sha256(blob).hexdigest()}


def pieces_of(blob, size, prefix='/piece'):
    return [('%s/%d' % (prefix, n), blob[i:i+size]) for n, i in enumerate(range(0, len(blob), size))]


class StreamComparisonTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='case-matrix-stream-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.decoded = b''.join(b'{"k%05d":[%d,%d.5,"v"]},' % (n, n, n) for n in range(4000)) + b'\n'

    def reference(self, blob=None, *, name='reference.json.gz', raw=None):
        path = self.root/name
        path.write_bytes(raw if raw is not None else gzip.compress(blob if blob is not None else self.decoded, mtime=0))
        return path

    def compare(self, pieces, path, decoded=None, **kwargs):
        decoded = self.decoded if decoded is None else decoded
        return stream.compare_canonical_stream(
            pieces, path, compressed=identity(path.read_bytes()), decoded=identity(decoded),
            read_bytes=kwargs.pop('read_bytes', 7), output_bytes=kwargs.pop('output_bytes', 13), **kwargs)

    def assertCode(self, code, fn, *args, **kwargs):
        with self.assertRaises(GeneratorError) as caught: fn(*args, **kwargs)
        self.assertEqual(caught.exception.code, code, str(caught.exception))

    def test_exact_match_across_chunk_and_piece_boundaries(self):
        path = self.reference()
        for size in (1, 5, 64, 4096, len(self.decoded)):
            with self.subTest(size=size):
                result = self.compare(pieces_of(self.decoded, size), path)
                self.assertEqual(result['status'], 'MATCH')
                self.assertIsNone(result['first_difference'])
                self.assertEqual(result['generated'], {**identity(self.decoded), 'complete': True})
                self.assertEqual(result['reference']['decoded'], identity(self.decoded))
                self.assertEqual(result['reference']['compressed'], identity(path.read_bytes()))
                self.assertEqual(result['pieces'], len(pieces_of(self.decoded, size)))

    def test_first_changed_byte_reports_offset_path_and_windows(self):
        path = self.reference()
        offset = 50001
        changed = bytearray(self.decoded); changed[offset] ^= 1
        result = self.compare(pieces_of(bytes(changed), 1000), path)
        self.assertEqual(result['status'], 'MISMATCH')
        difference = result['first_difference']
        self.assertEqual(difference['offset'], offset)
        self.assertEqual(difference['path'], '/piece/50')
        self.assertEqual(difference['offset_in_piece'], 1)
        self.assertNotEqual(difference['generated_window'], difference['reference_window'])
        self.assertFalse(result['generated']['complete'])
        self.assertIsNone(result['reference']['decoded'])

    def test_generated_longer_or_shorter_than_reference_is_a_mismatch(self):
        path = self.reference()
        longer = self.compare(pieces_of(self.decoded, 999) + [('/extra', b'x')], path)
        self.assertEqual((longer['status'], longer['first_difference']['offset']), ('MISMATCH', len(self.decoded)))
        self.assertEqual((longer['first_difference']['path'], longer['first_difference']['reference_window']), ('/extra', ''))
        shorter = self.compare(pieces_of(self.decoded[:-10], 999), path)
        self.assertEqual((shorter['status'], shorter['first_difference']['offset']), ('MISMATCH', len(self.decoded)-10))
        self.assertEqual(shorter['first_difference']['path'], None)

    def test_reference_identity_is_checked_before_and_after_comparison(self):
        path = self.reference()
        wrong = identity(b'other')
        self.assertCode('source_integrity', stream.compare_canonical_stream, pieces_of(self.decoded, 64), path,
                        compressed=wrong, decoded=identity(self.decoded))
        # A matching byte stream still fails if the declared decoded identity is foreign.
        self.assertCode('source_integrity', stream.compare_canonical_stream, pieces_of(self.decoded, 64), path,
                        compressed=identity(path.read_bytes()), decoded=wrong)

    def test_truncated_trailing_and_multimember_gzip_fail_closed(self):
        whole = gzip.compress(self.decoded, mtime=0)
        cases = {'truncated': whole[:-20], 'trailing': whole+b'\0', 'multimember': whole+gzip.compress(b'x', mtime=0),
                 'not_gzip': zlib.compress(self.decoded)}
        for name, raw in cases.items():
            with self.subTest(name=name):
                path = self.reference(raw=raw, name=name+'.gz')
                self.assertCode('source_integrity', self.compare, pieces_of(self.decoded, 512), path)

    def test_corrupt_gzip_trailer_and_late_trailing_bytes_fail_closed(self):
        whole = bytearray(gzip.compress(self.decoded, mtime=0))
        crc = bytearray(whole); crc[-6] ^= 1
        size = bytearray(whole); size[-2] ^= 1
        cases = {'crc': bytes(crc), 'isize': bytes(size), 'trailer_cut': bytes(whole[:-4]),
                 'late_trailing': bytes(whole)+b'\0'*100000}
        for name, raw in cases.items():
            for read_bytes in (7, 1 << 20):
                with self.subTest(name=name, read_bytes=read_bytes):
                    path = self.reference(raw=raw, name=name+'.gz')
                    self.assertCode('source_integrity', self.compare, pieces_of(self.decoded, 512), path,
                                    read_bytes=read_bytes)

    def test_reference_ending_inside_a_piece_and_piece_errors(self):
        path = self.reference()
        result = self.compare([('/whole', self.decoded+b'tail')], path)
        self.assertEqual((result['status'], result['first_difference']['offset']), ('MISMATCH', len(self.decoded)))
        self.assertEqual(result['first_difference']['offset_in_piece'], len(self.decoded))
        def failing():
            yield '/first', self.decoded[:10]
            raise GeneratorError('matrix_slot_closure', '/x', 'raised while streaming')
        self.assertCode('matrix_slot_closure', self.compare, failing(), path)

    def test_generated_pieces_must_be_bytes_with_string_paths(self):
        path = self.reference()
        for bad in ([('/p', 'text')], [(None, b'{')], [('/p', b'{', 'extra')]):
            with self.subTest(bad=bad):
                self.assertCode('invalid_json', self.compare, bad, path)


class CanonicalPieceTests(unittest.TestCase):
    """The emitter alone, on small synthetic unions: concatenation is canonical()."""

    def union(self):
        return {'schema_version': '1.2.0', 'algorithm_version': 'a',
                'metadata': {'zé': 1, 'a': [1.5, -0.0, 10**20], '日': 'é\n"'},
                'generation': {'k': {'nested': True}}, 'constituents': [{'b': 1, 'a': 2}, {}],
                'bindings': [], 'schedules': {'s/1': {'values': [0.1]}, 's~2': {'values': []},
                                              'é': {'values': [1]}, 'A': {}}}

    def test_concatenation_equals_canonical_including_unicode_and_empty_members(self):
        from atlas_schedules.canonical import canonical
        from scripts import schedule_generator_case_matrix as adapter
        for empty in (False, True):
            value = self.union()
            if empty: value['schedules'] = {}; value['constituents'] = []
            with self.subTest(empty=empty):
                pieces = list(adapter._canonical_pieces(value))
                self.assertEqual(b''.join(blob for _, blob in pieces), canonical(value))
        paths = [path for path, _ in adapter._canonical_pieces(self.union())]
        self.assertIn('/schedules/s~11', paths); self.assertIn('/schedules/s~02', paths)

    def test_chunked_identity_equals_canonical_bytes(self):
        import random
        from atlas_schedules.canonical import canonical
        from scripts import schedule_generator_case_matrix as adapter
        generator = random.Random(145)
        def value(depth):
            if depth == 0: return generator.choice([1, -0.0, 2.5e-300, 'xé"\\\n', None, True, 10**30, 0.1])
            if generator.random() < 0.5:
                return {generator.choice(['b', 'a', 'é', 'A', '~/', 'z'])+str(n): value(depth-1)
                        for n in range(generator.randint(0, 4))}
            return [value(depth-1) for _ in range(generator.randint(0, 4))]
        for _ in range(500):
            item = value(generator.randint(0, 5)); blob = canonical(item)
            self.assertEqual(adapter._identity(item), identity(blob))
        self.assertEqual(adapter._identity(self.union()), identity(canonical(self.union())))
        with self.assertRaises(GeneratorError): adapter._identity({'a': float('inf')})

    def test_wrong_member_set_and_nonfinite_values_fail(self):
        from scripts import schedule_generator_case_matrix as adapter
        value = self.union(); value['extra'] = 1
        with self.assertRaises(GeneratorError) as caught: next(adapter._canonical_pieces(value))
        self.assertEqual(caught.exception.code, 'matrix_union_shape')
        value = self.union(); value['schedules']['s/1']['values'][0] = float('nan')
        pieces = adapter._canonical_pieces(value)
        with self.assertRaises(GeneratorError) as caught: list(pieces)
        self.assertEqual((caught.exception.code, caught.exception.path), ('invalid_json', '/schedules/s~11'))


class QualifyRunnerSafetyTests(unittest.TestCase):
    def test_memory_counters_are_readable_on_windows(self):
        from scripts import schedule_generator_case_matrix_qualify as qualify
        if qualify.os.name != 'nt': self.skipTest('Windows-only counters')
        process, system = qualify.process_memory(), qualify.system_memory()
        self.assertIsNotNone(process); self.assertIsNotNone(system)
        self.assertGreater(process['peak_working_set_bytes'], 0)
        self.assertGreater(system['available_commit_bytes'], 0)

    def test_watchdog_fails_closed_on_floor_or_unreadable_sample(self):
        from unittest.mock import patch
        from scripts import schedule_generator_case_matrix_qualify as qualify
        low = {'available_physical_bytes': 1, 'available_commit_bytes': 1,
               'total_physical_bytes': 2, 'commit_limit_bytes': 2}
        with tempfile.TemporaryDirectory(prefix='qualify-watchdog-') as folder:
            for sample, status in ((None, 'MEMORY_SAMPLE_FAILED'), (low, 'MEMORY_FLOOR_STOP')):
                receipt = Path(folder)/(status+'.json')
                watchdog = qualify.Watchdog(receipt, interval=0.001)
                with self.subTest(status=status), patch.object(qualify, 'system_memory', return_value=sample), \
                        patch.object(qualify.os, '_exit', side_effect=SystemExit(3)):
                    with self.assertRaises(SystemExit): watchdog.run()
                    note = receipt.with_suffix('.memory-stop.json').read_text(encoding='utf-8')
                    self.assertIn(status, note)
            # A failed note write still exits.
            watchdog = qualify.Watchdog(Path(folder)/'missing'/'r.json', interval=0.001)
            with patch.object(qualify, 'system_memory', return_value=low), \
                    patch.object(qualify.os, '_exit', side_effect=SystemExit(3)):
                with self.assertRaises(SystemExit): watchdog.run()


if __name__ == '__main__': unittest.main()
