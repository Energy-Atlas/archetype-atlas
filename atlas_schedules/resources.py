"""Validate immutable resource directories before exposing records."""
import hashlib
import json
import math
from pathlib import Path, PurePosixPath

from .canonical import canonical
from .errors import GeneratorError

KINDS = {'residential', 'commercial', 'weather', 'program', 'composition', 'reference'}


def safe_path(name: str) -> PurePosixPath:
    if not isinstance(name, str) or not name or '\\' in name or ':' in name:
        raise GeneratorError('unsafe_resource_path', str(name), 'Unsafe resource path')
    path = PurePosixPath(name)
    reserved = {'CON', 'PRN', 'AUX', 'NUL'} | {f'{prefix}{i}' for prefix in ('COM', 'LPT') for i in range(1, 10)}
    if path.is_absolute() or any(p in {'..', '.', ''} or p.endswith(('.', ' ')) or p.split('.')[0].upper() in reserved for p in name.split('/')):
        raise GeneratorError('unsafe_resource_path', name, 'Unsafe resource path')
    return path


def strict_json(content: bytes, path: str):
    def finite_float(token):
        value = float(token)
        if not math.isfinite(value):
            raise ValueError('Nonfinite JSON number')
        return value

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f'Duplicate key {key}')
            result[key] = value
        return result
    try:
        return json.loads(content, object_pairs_hook=pairs, parse_float=finite_float,
                          parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
    except (ValueError, UnicodeError) as error:
        raise GeneratorError('resource_integrity', path, str(error)) from error


def manifest_identity(manifest: dict) -> str:
    payload = {k: v for k, v in manifest.items() if k != 'resource_set_id'}
    return 'resources-' + hashlib.sha256(canonical(payload)).hexdigest()


def write_resources(destination: Path, records: dict, metadata: dict) -> dict:
    destination = Path(destination)
    if destination.exists() and any(destination.iterdir()):
        raise GeneratorError('resource_integrity', str(destination), 'Destination must be empty')
    destination.mkdir(parents=True, exist_ok=True)
    entries = []
    for (kind, key), record in sorted(records.items()):
        if kind not in KINDS:
            raise GeneratorError('unsupported_resource', kind, 'Unknown resource kind')
        path = f'{kind}/{key}.json'
        safe_path(path)
        content = canonical(record)
        target = destination/path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        entries.append({'kind': kind, 'key': key, 'path': path,
                        'sha256': hashlib.sha256(content).hexdigest(), 'size_bytes': len(content)})
    manifest = {'schema_version': '1.0.0', 'resources': entries, **metadata}
    manifest['resource_set_id'] = manifest_identity(manifest)
    (destination/'manifest.json').write_bytes(canonical(manifest))
    ResourceSet(destination, manifest['resource_set_id'])
    return manifest


class ResourceSet:
    def __init__(self, root: Path, expected_id: str):
        self.root = Path(root).resolve()
        self._records = {}
        try:
            manifest = strict_json((self.root/'manifest.json').read_bytes(), 'manifest.json')
            if manifest.get('schema_version') != '1.0.0' or manifest.get('resource_set_id') != expected_id or manifest_identity(manifest) != expected_id:
                raise GeneratorError('resource_integrity', 'manifest.json', 'Resource identity mismatch')
            expected = {'manifest.json'}
            for entry in manifest['resources']:
                name = str(safe_path(entry['path']))
                pair = (entry['kind'], entry['key'])
                if pair in self._records or name in expected or pair[0] not in KINDS:
                    raise GeneratorError('resource_integrity', name, 'Invalid or duplicate inventory entry')
                expected.add(name)
                target = self.root/name
                if target.is_symlink() or not target.resolve().is_relative_to(self.root):
                    raise GeneratorError('resource_integrity', name, 'Resource escapes root')
                content = target.read_bytes()
                if len(content) != entry['size_bytes'] or hashlib.sha256(content).hexdigest() != entry['sha256']:
                    raise GeneratorError('resource_integrity', name, 'Resource checksum mismatch')
                self._records[pair] = strict_json(content, name)
            actual = {p.relative_to(self.root).as_posix() for p in self.root.rglob('*') if p.is_file() or p.is_symlink()}
            if actual != expected:
                raise GeneratorError('resource_integrity', '/', 'Changed resource inventory')
            self.manifest = manifest
            self.resource_set_id = expected_id
        except (OSError, KeyError, TypeError) as error:
            raise GeneratorError('resource_integrity', '/', str(error)) from error

    @classmethod
    def load(cls, resource_set_id: str) -> 'ResourceSet':
        return cls(Path(__file__).parent/'data', resource_set_id)

    def get(self, kind: str, key: str) -> dict:
        import copy
        try:
            return copy.deepcopy(self._records[(kind, key)])
        except KeyError as error:
            raise GeneratorError('missing_resource', f'{kind}/{key}', 'Resource is not in this set') from error
