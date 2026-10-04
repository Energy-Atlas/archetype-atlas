"""Retrieve checksum-locked public source blobs; never execute downloaded code."""
import argparse
import hashlib
import os
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

from scripts.common import ROOT, load_json

ALLOWED_HOSTS = {'raw.githubusercontent.com', 'www.energycodes.gov', 'www.energy.gov'}


def cache_path(entry, cache_root):
    source = entry['source_id']
    path = entry['path']
    if not source or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in source):
        raise ValueError('Unsafe source ID')
    if '\\' in path or ':' in path or Path(path).is_absolute() or '..' in Path(path).parts:
        raise ValueError('Unsafe source path')
    base = Path(cache_root).resolve()
    result = (base/source/path).resolve()
    if not result.is_relative_to(base/source):
        raise ValueError('Source path escapes cache')
    return result


def verify_file(entry, cache_root=ROOT/'data/raw'):
    path = cache_path(entry, cache_root)
    if path.stat().st_size != entry['size_bytes']:
        raise ValueError(f'Source size mismatch: {entry["path"]}')
    if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
        raise ValueError(f'Source checksum mismatch: {entry["path"]}')
    return path


def safe_url(url):
    u = urllib.parse.urlsplit(url)
    if u.scheme != 'https' or u.hostname not in ALLOWED_HOSTS or u.username or u.password or u.query:
        raise ValueError('Source URL must be public HTTPS on an allowed host')


def fetch_file(entry, cache_root):
    path = cache_path(entry, cache_root)
    if path.exists():
        return verify_file(entry, cache_root)
    safe_url(entry['url'])
    request = urllib.request.Request(entry['url'], headers={'User-Agent': 'archetype-atlas/0.1.0'})
    with urllib.request.urlopen(request, timeout=60) as response:
        safe_url(response.geturl())
        content = response.read(entry['size_bytes'] + 1)
    if len(content) != entry['size_bytes'] or hashlib.sha256(content).hexdigest() != entry['sha256']:
        raise ValueError(f'Download integrity failure: {entry["path"]}')
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
            temporary = Path(f.name)
            f.write(content)
        # An existing cache blob is never silently overwritten.
        if path.exists():
            return verify_file(entry, cache_root)
        os.replace(temporary, path)
        return verify_file(entry, cache_root)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-only', action='store_true')
    parser.add_argument('--cache-root', type=Path, default=ROOT/'data/raw')
    parser.add_argument('--lock', type=Path, default=ROOT/'sources/lock.json')
    args = parser.parse_args()
    lock = load_json(args.lock)
    for entry in lock['files']:
        if args.verify_only:
            verify_file(entry, args.cache_root)
        else:
            fetch_file(entry, args.cache_root)
    print(f'Verified {len(lock["files"])} locked source files')


if __name__ == '__main__':
    main()
