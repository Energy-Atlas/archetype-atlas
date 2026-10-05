"""Reference static resolver; no backend or BEMGen runtime dependency."""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from urllib.parse import urljoin, urlsplit
from urllib.request import urlopen

from jsonschema import Draft202012Validator, ValidationError
from scripts.common import ROOT, load_json
from scripts.query_delivery import SCHEMA_VERSION, decode_reference, json_bytes, safe_path


class QueryError(ValueError):
    """Stable error codes are part of the consumer contract."""
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code

    def as_json(self):
        return {'schema_version': SCHEMA_VERSION, 'error': {'code': self.code, 'message': str(self)}}


def strict_json(content):
    """Reject nonfinite numbers and duplicate members before interpretation."""
    def members(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON member')
            result[key] = value
        return result

    def nonfinite(_):
        raise ValueError('Nonfinite JSON number')

    def finite_float(value):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError('JSON number exceeds finite numeric range')
        return result

    return json.loads(content.decode('utf-8'), object_pairs_hook=members,
                      parse_constant=nonfinite, parse_float=finite_float)


def same_scalar(left, right):
    """JSON equality: numbers compare numerically, booleans are not numbers."""
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left == right
    return left == right


class QueryClient:
    """Resolve one pinned snapshot, then lazily cache verified JSON resources.

    root is the delivery/v1 directory, a filesystem path or HTTPS URL. HTTP is
    allowed only on loopback for conformance testing. manifest_ref bypasses latest.
    Download statistics expose real transport cost; cached queries add no requests.
    """
    def __init__(self, root, manifest_ref=None):
        self.cache = {}
        self.download_stats = {'requests': 0, 'bytes': 0}
        self.root = str(root)
        parsed = urlsplit(self.root)
        self.remote = parsed.scheme in {'http', 'https'}
        if self.remote:
            if (parsed.username or parsed.password or parsed.query or parsed.fragment
                    or not parsed.hostname or parsed.scheme == 'http' and parsed.hostname not in {'127.0.0.1', 'localhost', '::1'}):
                raise QueryError('unsafe_reference', 'Use a credential-free HTTPS directory URL')
            self.root = self.root.rstrip('/') + '/'
        else:
            self.root = Path(root).resolve()
        self.artifact_validator = Draft202012Validator(load_json(ROOT/'schemas/query-artifact.schema.json'))
        self.request_validator = Draft202012Validator(load_json(ROOT/'schemas/query-request.schema.json'))
        if manifest_ref is None:
            latest = self._parse(self._read('latest.json'))
            self._artifact(latest, 'latest')
            manifest_ref = latest['manifest']
            expected_id = latest['snapshot_id']
        else:
            expected_id = None
        self.manifest_ref = copy.deepcopy(manifest_ref)
        self.manifest = self.fetch(manifest_ref)
        self._artifact(self.manifest, 'manifest')
        unsigned = {k: v for k, v in self.manifest.items() if k != 'snapshot_id'}
        actual_id = hashlib.sha256(json_bytes(unsigned)).hexdigest()
        if actual_id != self.manifest['snapshot_id'] or expected_id is not None and actual_id != expected_id:
            raise QueryError('integrity_error', 'Snapshot identity mismatch')

    def _read(self, href, expected_size=None):
        try:
            # Validate lexical paths before URI resolution, including encoded escapes.
            safe_path(Path.cwd(), href)
        except ValueError as exc:
            raise QueryError('unsafe_reference', str(exc)) from exc
        try:
            limit = (expected_size + 1) if expected_size is not None else 65537
            if self.remote:
                url = urljoin(self.root, href)
                with urlopen(url, timeout=30) as response:
                    final = urlsplit(response.geturl()); base = urlsplit(self.root)
                    if (final.scheme, final.netloc) != (base.scheme, base.netloc) or not final.path.startswith(base.path):
                        raise QueryError('unsafe_reference', 'Resource redirected outside delivery root')
                    content = response.read(limit)
            else:
                with safe_path(self.root, href).open('rb') as stream:
                    content = stream.read(limit)
            self.download_stats['requests'] += 1
            self.download_stats['bytes'] += len(content)
            if expected_size is None and len(content) >= limit:
                raise QueryError('invalid_artifact', 'Latest pointer exceeds 64 KiB')
            return content
        except QueryError:
            raise
        except (OSError, ValueError) as exc:
            raise QueryError('fetch_failed', 'Cannot retrieve resource: ' + href) from exc

    def _parse(self, content):
        try:
            return strict_json(content)
        except (ValueError, UnicodeError) as exc:
            raise QueryError('invalid_artifact', 'Resource is not strict UTF-8 JSON') from exc

    def _artifact(self, value, expected_kind=None):
        if not isinstance(value, dict):
            raise QueryError('invalid_artifact', 'Artifact must be an object')
        if not isinstance(value.get('schema_version'), str) or not re.fullmatch(r'1\.\d+\.\d+', value['schema_version']):
            raise QueryError('unsupported_schema', 'Unsupported delivery schema major')
        try:
            self.artifact_validator.validate(value)
        except ValidationError as exc:
            raise QueryError('invalid_artifact', 'Resource violates artifact schema') from exc
        if expected_kind and value['kind'] != expected_kind:
            raise QueryError('invalid_artifact', 'Unexpected artifact kind')

    def fetch(self, reference):
        """Explicit lazy fetch of a descriptor; JSON artifacts only."""
        if (not isinstance(reference, dict)
                or not {'href', 'sha256', 'size_bytes'} <= set(reference) <= {'href', 'sha256', 'size_bytes', 'encoding', 'decoded_size_bytes'}
                or not isinstance(reference.get('sha256'), str)
                or not re.fullmatch('[a-f0-9]{64}', reference['sha256'])
                or type(reference.get('size_bytes')) is not int or not 0 <= reference['size_bytes'] <= 16_000_000
                or 'encoding' in reference and reference['encoding'] != 'gzip'
                or ('encoding' in reference) != ('decoded_size_bytes' in reference)
                or 'encoding' in reference and (type(reference['decoded_size_bytes']) is not int
                                               or not 0 <= reference['decoded_size_bytes'] <= 16_000_000)):
            raise QueryError('invalid_artifact', 'Malformed resource descriptor')
        try:
            safe_path(Path.cwd(), reference['href'])
        except (ValueError, TypeError) as exc:
            raise QueryError('unsafe_reference', 'Unsafe resource path') from exc
        key = (reference['href'], reference['sha256'], reference['size_bytes'],
               reference.get('encoding'), reference.get('decoded_size_bytes'))
        if key not in self.cache:
            content = self._read(reference['href'], reference['size_bytes'])
            if len(content) != reference['size_bytes'] or hashlib.sha256(content).hexdigest() != reference['sha256']:
                raise QueryError('integrity_error', 'Resource checksum/size mismatch: ' + reference['href'])
            try:
                decoded = decode_reference(content, reference)
            except (ValueError, OSError, EOFError) as exc:
                raise QueryError('integrity_error', 'Invalid declared resource encoding') from exc
            value = self._parse(decoded)
            self._artifact(value)
            self.cache[key] = value
        return copy.deepcopy(self.cache[key])

    def query(self, request):
        """Exact scalar equality AND filters, stable ID ordering, explicit projection."""
        try:
            # Serialization also rejects nonfinite values hidden inside an in-memory request.
            json_bytes(request)
            self.request_validator.validate(request)
        except (ValidationError, ValueError, TypeError) as exc:
            raise QueryError('invalid_request', 'Request violates query-request schema') from exc
        kind = request['record_type']
        if kind not in self.manifest['record_types']:
            raise QueryError('unknown_record_type', 'Unknown record_type: ' + kind)
        info = self.manifest['record_types'][kind]
        unknown = set(request['fields']) - set(info['fields'])
        if unknown:
            raise QueryError('unknown_field', 'Unknown projected field: ' + ', '.join(sorted(unknown)))
        where = request.get('where', {})
        unknown = set(where) - set(info['filter_fields'])
        if unknown:
            raise QueryError('unknown_filter', 'Unknown or non-scalar filter: ' + ', '.join(sorted(unknown)))
        view = request.get('view', 'source')
        index = self.fetch(info['index']); self._artifact(index, 'index')
        if index['record_type'] != kind:
            raise QueryError('invalid_artifact', 'Index record_type mismatch')
        output, ids = [], set()
        for route in index['routes']:
            if 'id' in where and where['id'] not in route['record_ids']:
                continue
            if any(k in where and not same_scalar(v, where[k]) for k, v in route['selectors'].items()):
                continue
            for ref in route['packets']:
                if ref.get('decoded_size_bytes', ref['size_bytes']) > self.manifest['max_packet_bytes']:
                    raise QueryError('invalid_artifact', 'Packet exceeds declared byte bound')
                packet = self.fetch(ref); self._artifact(packet, 'packet')
                if packet['record_type'] != kind:
                    raise QueryError('invalid_artifact', 'Packet record_type mismatch')
                for record in packet['records']:
                    if record['id'] in ids:
                        raise QueryError('invalid_artifact', 'Duplicate record ID')
                    ids.add(record['id'])
                    fields = {**record['fields'], **record['reviewed']} if view == 'reviewed' else record['fields']
                    if any(not same_scalar(record['id'] if k == 'id' else fields[k]['value'], v)
                           if k == 'id' or k in fields else True for k, v in where.items()):
                        continue
                    selected = {field: fields.get(field, {'value': None, 'unit': None, 'status': 'not_reported',
                                                          'evidence_pointer': None}) for field in request['fields']}
                    output.append({'id': record['id'], 'fields': selected, 'evidence': record['evidence']})
        normalized = {'record_type': kind, 'where': where, 'fields': request['fields'], 'view': view}
        return {'schema_version': SCHEMA_VERSION, 'snapshot_id': self.manifest['snapshot_id'],
                'record_type': kind, 'view': view, 'query': copy.deepcopy(normalized),
                'match_count': len(output), 'records': sorted(output, key=lambda r: r['id'])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, help='Delivery/v1 directory path or HTTPS URL')
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--request', type=Path, help='JSON query request')
    parser.add_argument('--manifest', type=Path, help='Saved manifest descriptor; bypass latest')
    action.add_argument('--resource', type=Path, help='Fetch this saved resource descriptor instead of querying')
    args = parser.parse_args()
    try:
        client = QueryClient(args.root, manifest_ref=load_json(args.manifest) if args.manifest else None)
        result = client.fetch(load_json(args.resource)) if args.resource else client.query(strict_json(args.request.read_bytes()))
    except QueryError as exc:
        print(json_bytes(exc.as_json()).decode('utf-8'), end='')
        raise SystemExit(2) from None
    except (OSError, ValueError) as exc:
        print(json_bytes(QueryError('invalid_request', 'Cannot read request/descriptor JSON').as_json()).decode('utf-8'), end='')
        raise SystemExit(2) from None
    sys.stdout.buffer.write(json_bytes(result))


if __name__ == '__main__':
    main()
