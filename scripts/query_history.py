"""Preserve immutable query snapshots across clean static-site publications."""
import argparse
import io
from pathlib import Path
import tempfile
from urllib.error import HTTPError
from urllib.parse import urljoin
from urllib.request import urlopen
import zipfile

from scripts.common import ROOT, load_json
from scripts.query_delivery import (checked_target, check_reference, descriptor, json_bytes,
                                    safe_path, sha, validate_delivery)
from scripts.query_client import strict_json


def export_history(root):
    """Publisher-only archive; ordinary queries never request it."""
    root = Path(root)
    errors = validate_delivery(root)
    if errors:
        raise ValueError('; '.join(errors))
    content = io.BytesIO()
    with zipfile.ZipFile(content, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(root.rglob('*')):
            if path.is_file() and path.relative_to(root).parts[0] in {'resources', 'snapshots'}:
                name = path.relative_to(root).as_posix()
                info = zipfile.ZipInfo(name, date_time=(2026, 10, 5, 0, 0, 0))
                info.create_system = 3; info.external_attr = 0o644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, path.read_bytes(), compresslevel=9)
    archive_bytes = content.getvalue()
    (root/'history.zip').write_bytes(archive_bytes)
    latest = load_json(root/'latest.json')
    latest['history'] = descriptor('history.zip', archive_bytes)
    (root/'latest.json').write_bytes(json_bytes(latest))
    return latest['history']


def restore_history(source, target, allow_missing=False):
    """Restore only verified publisher output; never silently discard bad history.

    source is a delivery/v1 directory path or HTTPS root. An initial 404 is allowed
    only explicitly, before the machine interface has ever been published.
    """
    target = checked_target(target)
    if str(source).startswith('https://'):
        try:
            with urlopen(str(source).rstrip('/') + '/latest.json', timeout=30) as response:
                latest_bytes = response.read(65537)
        except HTTPError as exc:
            if allow_missing and exc.code == 404:
                return False
            raise
        latest = strict_json(latest_bytes)
        ref = latest.get('history')
        if not ref:
            raise ValueError('Published snapshot lacks required retention archive')
        if type(ref.get('size_bytes')) is not int or not 0 <= ref['size_bytes'] <= 100_000_000:
            raise ValueError('Retention archive exceeds publisher transport limit')
        safe_path(Path.cwd(), ref['href'])
        with urlopen(urljoin(str(source).rstrip('/') + '/', ref['href']), timeout=60) as response:
            archive_bytes = response.read(ref['size_bytes'] + 1)
        if len(archive_bytes) != ref['size_bytes'] or sha(archive_bytes) != ref['sha256']:
            raise ValueError('History checksum/size mismatch')
    else:
        source = Path(source)
        if allow_missing and not (source/'latest.json').exists():
            return False
        latest_bytes = (source/'latest.json').read_bytes()
        latest = strict_json(latest_bytes)
        archive_bytes = check_reference(source, latest['history'])
    if len(archive_bytes) > 100_000_000:
        raise ValueError('Retention archive exceeds publisher transport limit')
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent) as d:
        stage = Path(d)/'delivery'; stage.mkdir()
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            if sum(info.file_size for info in archive.infolist()) > 500_000_000:
                raise ValueError('Retention archive exceeds expanded limit')
            names = set()
            for info in archive.infolist():
                if info.filename in names or info.is_dir():
                    raise ValueError('Duplicate/unexpected archive member')
                names.add(info.filename)
                path = safe_path(stage, info.filename)
                if info.filename.split('/')[0] not in {'resources', 'snapshots'}:
                    raise ValueError('Unexpected retention archive namespace')
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(archive.read(info))
        (stage/'latest.json').write_bytes(latest_bytes)
        (stage/'history.zip').write_bytes(archive_bytes)
        errors = validate_delivery(stage)
        if errors:
            raise ValueError('Invalid restored history: ' + '; '.join(errors[:4]))
        # The manifest schema references are content-addressed and retained too.
        target.mkdir(exist_ok=True)
        for path in sorted(stage.rglob('*')):
            if path.is_file():
                dest = target/path.relative_to(stage)
                if dest.exists() and dest.name != 'latest.json' and dest.read_bytes() != path.read_bytes():
                    raise ValueError('Retained path collision')
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(path.read_bytes())
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--restore', help='Previously published delivery/v1 HTTPS root')
    parser.add_argument('--target', type=Path, default=ROOT/'build/query-history')
    parser.add_argument('--allow-missing', action='store_true')
    args = parser.parse_args()
    if args.restore:
        restored = restore_history(args.restore, args.target, args.allow_missing)
        print('Query history restored' if restored else 'Initial publication: no earlier query history')
    else:
        ref = export_history(args.target)
        print('Query history archived: ' + str(ref['size_bytes']) + ' bytes')


if __name__ == '__main__':
    main()
