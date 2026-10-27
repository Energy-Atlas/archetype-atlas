"""The site's one content-addressed JSON store (ADR 0043, after ADR 0011 and ADR 0036 section 10).

Every document is canonical JSON, gzip-compressed with a fixed header and stored at
`store/<sha256 of the gzip bytes>.json.gz`. A descriptor names the path, the SHA-256,
the encoded and decoded sizes; browsers verify the checksum before bounded
decompression. Identical documents share one file. Index packets (the viewer's ID
index and the JSON of objects no page renders) hold at most PACKET decoded bytes.
"""
import gzip
import hashlib
import json
from pathlib import Path

PACKET = 131_072
DOCUMENT_LIMIT = 16_000_000


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def compress(data):
    return gzip.compress(data, compresslevel=9, mtime=0)


class Store:
    """Writes documents once each and returns their descriptors."""

    def __init__(self, site):
        self.root = Path(site)/'store'
        self.root.mkdir(parents=True, exist_ok=True)
        self.files = {}

    def put(self, value, limit=DOCUMENT_LIMIT):
        data = canonical(value)
        if len(data) > limit:
            raise ValueError(f'Store document of {len(data)} bytes exceeds {limit}')
        encoded = compress(data)
        digest = hashlib.sha256(encoded).hexdigest()
        href = f'store/{digest}.json.gz'
        if href not in self.files:
            (self.root/f'{digest}.json.gz').write_bytes(encoded)
            self.files[href] = len(encoded)
        return {'href': href, 'sha256': digest, 'encoding': 'gzip', 'size_bytes': len(encoded),
                'decoded_size_bytes': len(data)}

    def packets(self, rows):
        """{key: value} rows split into packets of at most PACKET decoded bytes, in key order.

        Returns (descriptors, the first key of each packet). A single row larger than a packet is stored alone, as a document.
        """
        out, firsts, current, size = [], [], {}, 2
        for key in sorted(rows):
            entry = len(canonical({key: rows[key]})) - 1
            if current and size+entry > PACKET:
                out.append(self.put(current, PACKET if len(current) > 1 else DOCUMENT_LIMIT))
                current, size = {}, 2
            if not current:
                firsts.append(key)
            current[key] = rows[key]
            size += entry
        if current:
            out.append(self.put(current, PACKET if len(current) > 1 else DOCUMENT_LIMIT))
        return out, firsts


def read(site, descriptor):
    """A stored document, verified as a browser verifies it."""
    path = Path(site)/descriptor['href']
    encoded = path.read_bytes()
    if len(encoded) != descriptor['size_bytes'] or hashlib.sha256(encoded).hexdigest() != descriptor['sha256']:
        raise ValueError('Store checksum or size mismatch: '+descriptor['href'])
    data = gzip.decompress(encoded)
    if len(data) != descriptor['decoded_size_bytes']:
        raise ValueError('Store decoded size mismatch: '+descriptor['href'])
    return json.loads(data)
