"""Retrieve checksum-locked browser assets; never use a runtime CDN."""
import argparse
import hashlib
from pathlib import Path
import urllib.request

from scripts.common import ROOT, load_json


def asset_path(root, entry):
    root = Path(root).resolve()
    target = (root/entry['path']).resolve()
    if not target.is_relative_to(root):
        raise ValueError('Asset path escape')
    return target


def verify_asset(root, entry):
    target = asset_path(root, entry)
    if not target.is_file() or target.stat().st_size != entry['size_bytes'] or (
            hashlib.sha256(target.read_bytes()).hexdigest() != entry['sha256']):
        raise ValueError('Asset checksum failure: ' + entry['path'])
    return target


def fetch_assets(root=ROOT/'build/vendor'):
    for entry in load_json(ROOT/'website/assets.lock.json')['assets']:
        target = asset_path(root, entry)
        if not target.exists():
            if not entry['url'].startswith('https://'):
                raise ValueError('Asset download requires HTTPS')
            content = urllib.request.urlopen(entry['url'], timeout=60).read()
            if len(content) != entry['size_bytes'] or hashlib.sha256(content).hexdigest() != entry['sha256']:
                raise ValueError('Downloaded asset checksum failure: ' + entry['path'])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        verify_asset(root, entry)
    return Path(root)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--verify', action='store_true')
    args = p.parse_args()
    if args.verify:
        for entry in load_json(ROOT/'website/assets.lock.json')['assets']:
            verify_asset(ROOT/'build/vendor', entry)
    else:
        fetch_assets()
    print('Pinned browser assets verified')


if __name__ == '__main__':
    main()
