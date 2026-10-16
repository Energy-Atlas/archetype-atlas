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

    def test_generated_pieces_must_be_bytes_with_string_paths(self):
        path = self.reference()
        for bad in ([('/p', 'text')], [(None, b'{')], [('/p', b'{', 'extra')]):
            with self.subTest(bad=bad):
                self.assertCode('invalid_json', self.compare, bad, path)


if __name__ == '__main__': unittest.main()
