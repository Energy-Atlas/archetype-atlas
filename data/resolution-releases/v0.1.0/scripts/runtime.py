"""Retrieve and extract only explicitly locked official runtime archives."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile
import urllib.request
from urllib.parse import urlsplit

from scripts.common import ROOT, load_json, dump_json


def extract_verified(archive, checksum, destination, include=None):
    archive, destination = Path(archive), Path(destination).resolve()
    if hashlib.sha256(archive.read_bytes()).hexdigest() != checksum:
        raise ValueError('Archive checksum mismatch')
    with tarfile.open(archive) as source:
        members = source.getmembers()
        for member in members:
            name = member.name
            if ('\\' in name or ':' in name or PurePosixPath(name).is_absolute()
                    or '..' in PurePosixPath(name).parts or not (member.isfile() or member.isdir())):
                raise ValueError('Unsafe archive member')
            target = (destination/name).resolve()
            if not target.is_relative_to(destination):
                raise ValueError('Unsafe archive target')
        if destination.exists():
            raise ValueError('Runtime extraction destination already exists; never overwrite')
        destination.mkdir(parents=True)
        selected = members if include is None else [m for m in members if any(
            m.name == prefix.rstrip('/') or m.name.startswith(prefix.rstrip('/')+'/') for prefix in include)]
        if not selected:
            raise ValueError('Declared archive selection is empty')
        source.extractall(destination, members=selected, filter='data')
    return destination


def fetch_runtime(lock, destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    results = {}
    for entry in lock['archives']:
        name = entry['name']
        if not name.replace('-', '').isalnum():
            raise ValueError('Unsafe runtime name')
        url = urlsplit(entry['url'])
        if url.scheme != 'https' or url.hostname not in {'github.com', 'codeload.github.com'} or url.username or url.password:
            raise ValueError('Runtime must use official public HTTPS archive')
        archive = destination/(name+'.tar.gz')
        if not archive.exists():
            request = urllib.request.Request(entry['url'], headers={'User-Agent':'Atlas-Research'})
            with urllib.request.urlopen(request, timeout=60) as response, archive.open('xb') as stream:
                while content := response.read(1024*1024):
                    stream.write(content)
        if archive.stat().st_size != entry['size_bytes'] or hashlib.sha256(archive.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('Runtime archive checksum or size mismatch')
        unpacked = destination/name
        marker = unpacked/'.atlas-extraction.json'
        if not marker.exists():
            extract_verified(archive, entry['sha256'], unpacked, include=entry.get('include'))
            # Verify every upstream file on reuse, including executed Ruby code.
            checksums = {p.relative_to(unpacked).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in unpacked.rglob('*') if p.is_file()}
            dump_json(marker, {'archive_sha256':entry['sha256'], 'files':checksums})
        else:
            inventory = load_json(marker)
            if inventory['archive_sha256'] != entry['sha256']:
                raise ValueError('Runtime extraction revision mismatch')
            for path, expected in inventory['files'].items():
                p = (unpacked/path).resolve()
                if not p.is_relative_to(unpacked.resolve()) or hashlib.sha256(p.read_bytes()).hexdigest() != expected:
                    raise ValueError('Runtime extracted file checksum mismatch')
        results[name] = unpacked/entry['root']
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, default=ROOT/'build/runtime')
    args = parser.parse_args()
    for name, path in fetch_runtime(load_json(ROOT/'sources/runtime-lock.json'), args.destination).items():
        print(name, path)


if __name__ == '__main__':
    main()
