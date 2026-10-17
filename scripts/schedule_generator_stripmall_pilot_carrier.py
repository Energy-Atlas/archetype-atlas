"""Reproduce or verify the tracked Stripmall 2013 SOURCE pilot carrier extract.

The extract is an unchanged field subset of the local native pilot output
(seeds 42 and 51). It copies values; it never recomputes them.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

from atlas_schedules.errors import GeneratorError
from scripts.common import ROOT

LOCK = 'sources/schedule-generator-stripmall-pilot-carrier-lock.json'
FIELDS = ('case_id', 'people_objects', 'majority', 'carrier', 'whole_model_original_hoo', 'whole_model_changed_hoo',
          'local_changed_hoo', 'registration', 'registration_events', 'actual_native_fixture_sort', 'native_hoo_route_calls',
          'operating', 'channels', 'original', 'final', 'inferred_original', 'inferred_final', 'fixture_receipts',
          'source_type_receipts', 'source_lookup')
INTERPRETATION = ('Unchanged subset of the original 2013 SOURCE Stripmall native pilot (seeds 42, 51): People, carrier, HOO, '
                  'registration, channel and original/final schedule fields. Values are copied, not recomputed; the pilot '
                  'directory stays the immutable original.')


def _identity(blob): return hashlib.sha256(blob).hexdigest(), len(blob)


def build_extract(raw: bytes, source_path: str) -> bytes:
    """Gzip bytes of the extract, deterministic for fixed pilot bytes."""
    out = json.loads(raw)
    cases = []
    for case in out['cases']:
        missing = [k for k in FIELDS if k not in case]
        if missing: raise GeneratorError('source_integrity', source_path, f'Pilot case lacks carrier fields {missing}')
        cases.append({k: case[k] for k in FIELDS})
    sha, size = _identity(raw)
    payload = {'schema_version': '1.1.0',
               'source': {'path': source_path, 'sha256': sha, 'size_bytes': size,
                          'openstudio_version': out.get('openstudio_version'), 'ruby_description': out.get('ruby_description')},
               'interpretation': INTERPRETATION, 'fields': list(FIELDS), 'cases': cases}
    blob = (json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False)+'\n').encode('utf-8')
    return gzip.compress(blob, mtime=0)


def verify_extract(root=ROOT, rebuild=False) -> dict:
    """Check the tracked extract against its lock; with rebuild, also against the local original pilot."""
    root = Path(root); lock = json.loads((root/LOCK).read_bytes()); entry = lock['extract']
    producer = lock['producer']
    if _identity((root/producer['path']).read_bytes()) != (producer['sha256'], producer['size_bytes']):
        raise GeneratorError('source_integrity', producer['path'], 'Pinned extract producer differs')
    z = (root/entry['path']).read_bytes()
    if _identity(z) != (entry['sha256'], entry['size_bytes']): raise GeneratorError('source_integrity', entry['path'], 'Extract bytes differ')
    if _identity(gzip.decompress(z)) != (entry['decoded_sha256'], entry['decoded_size_bytes']):
        raise GeneratorError('source_integrity', entry['path'], 'Decoded extract differs')
    if rebuild:
        original = lock['original']; raw = (root/original['path']).read_bytes()
        if _identity(raw) != (original['sha256'], original['size_bytes']):
            raise GeneratorError('source_integrity', original['path'], 'Original pilot bytes differ')
        evidence = original['pilot_evidence_lock']
        if _identity((root/evidence['path']).read_bytes()) != (evidence['sha256'], evidence['size_bytes']):
            raise GeneratorError('source_integrity', evidence['path'], 'Pilot evidence lock differs')
        # Compare decoded JSON bytes: gzip framing may differ across zlib builds.
        if gzip.decompress(build_extract(raw, original['path'])) != gzip.decompress(z):
            raise GeneratorError('source_integrity', entry['path'], 'Extract is not reproducible')
    return {'passed': True, 'rebuilt': rebuild, 'sha256': entry['sha256']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rebuild', action='store_true', help='also rebuild from the local original pilot output')
    print(json.dumps(verify_extract(rebuild=parser.parse_args().rebuild), sort_keys=True))


if __name__ == '__main__': main()
