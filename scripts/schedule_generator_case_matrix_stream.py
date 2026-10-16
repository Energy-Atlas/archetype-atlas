"""Lockstep comparison of canonical union pieces with a gzip reference (R145 Route B).

This is the file-I/O half of Route B; scripts/schedule_generator_case_matrix.py
stays pure and only yields (JSON pointer, bytes) pieces. The reference is never
parsed: its compressed bytes are authenticated first, then decompressed in
bounded chunks and compared byte for byte with the generated pieces. Memory is
bounded by the largest piece plus one decompression window, not by the union.
A first difference is reported, never repaired, retried or tolerated.
"""
import hashlib
from pathlib import Path
import zlib

from atlas_schedules.errors import GeneratorError

READ_BYTES = 1 << 20
OUTPUT_BYTES = 1 << 24
WINDOW_BYTES = 128


def _fail(message):
    raise GeneratorError('source_integrity', '/case_matrix/reference', message)


def _file_identity(path, read_bytes):
    digest = hashlib.sha256(); size = 0
    with Path(path).open('rb') as handle:
        while block := handle.read(read_bytes):
            digest.update(block); size += len(block)
    return {'size_bytes': size, 'sha256': digest.hexdigest()}


class _Reference:
    """Exactly one gzip member, decoded on demand; trailing or missing bytes fail."""

    def __init__(self, handle, read_bytes, output_bytes):
        self.handle, self.read_bytes, self.output_bytes = handle, read_bytes, output_bytes
        self.decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
        self.buffer = bytearray(); self.start = 0; self.ended = False
        self.digest = hashlib.sha256(); self.consumed = 0

    def _pump(self):
        try:
            if self.decoder.unconsumed_tail:
                data = self.decoder.unconsumed_tail
            elif self.decoder.eof:
                if self.decoder.unused_data or self.handle.read(1): _fail('Bytes follow the single gzip member')
                self.ended = True; return
            else:
                data = self.handle.read(self.read_bytes)
                if not data: _fail('Reference gzip stream is truncated')
            self.buffer += self.decoder.decompress(data, self.output_bytes)
        except zlib.error as error:
            _fail('Reference is not one valid gzip member: '+str(error))
        if self.decoder.eof and self.decoder.unused_data: _fail('Bytes follow the single gzip member')

    def available(self):
        return len(self.buffer) - self.start

    def take(self, count):
        while self.available() < count and not self.ended: self._pump()
        blob = bytes(self.buffer[self.start:self.start+count]); self.start += len(blob)
        if self.start >= len(self.buffer) // 2:  # compact rarely: amortized linear, not per piece
            del self.buffer[:self.start]; self.start = 0
        self.digest.update(blob); self.consumed += len(blob)
        return blob

    def drain(self):
        """Consume the rest; returns how many reference bytes followed the generated stream."""
        extra = 0
        while not self.ended or self.available():
            if not self.available(): self._pump(); continue
            extra += len(self.take(self.available()))
        return extra


def _window(blob, index):
    return blob[max(0, index-WINDOW_BYTES):index+WINDOW_BYTES].decode('utf-8', 'backslashreplace')


def compare_canonical_stream(pieces, reference, *, compressed: dict, decoded: dict,
                             read_bytes: int = READ_BYTES, output_bytes: int = OUTPUT_BYTES) -> dict:
    """Compare (pointer, bytes) pieces with the gzip reference's decoded bytes.

    Raises source_integrity if the reference is not the declared file. Returns
    status MATCH only if every byte matched, both streams ended together and
    the decoded reference has the declared size and SHA-256.
    """
    reference = Path(reference)
    actual = _file_identity(reference, read_bytes)
    if actual != compressed: _fail('Compressed reference identity differs: '+repr(actual))
    generated = hashlib.sha256(); generated_size = 0; count = 0; difference = None
    with reference.open('rb') as handle:
        ref = _Reference(handle, read_bytes, output_bytes)
        for item in pieces:
            if not (isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str) and isinstance(item[1], bytes)):
                raise GeneratorError('invalid_json', '/case_matrix/stream', 'Pieces must be (str pointer, bytes) pairs')
            path, blob = item; count += 1
            expected = ref.take(len(blob))
            if expected != blob:
                index = next((i for i, (a, b) in enumerate(zip(blob, expected)) if a != b), len(expected))
                difference = {'offset': generated_size+index, 'path': path, 'offset_in_piece': index,
                              'generated_window': _window(blob, index), 'reference_window': _window(expected, index)}
                break
            generated.update(blob); generated_size += len(blob)
        if difference is None:
            extra = ref.drain()
            if extra:
                difference = {'offset': generated_size, 'path': None, 'offset_in_piece': None,
                              'generated_window': '', 'reference_window': f'{extra} further reference bytes'}
        reference_decoded = None
        if difference is None:
            reference_decoded = {'size_bytes': ref.consumed, 'sha256': ref.digest.hexdigest()}
            if reference_decoded != decoded: _fail('Decoded reference identity differs: '+repr(reference_decoded))
    return {'status': 'MATCH' if difference is None else 'MISMATCH', 'pieces': count,
            'generated': {'size_bytes': generated_size, 'sha256': generated.hexdigest(), 'complete': difference is None},
            'reference': {'compressed': actual, 'decoded': reference_decoded},
            'first_difference': difference}
