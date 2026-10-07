"""Check every built internal URL/fragment, including project-subpath assets."""
import argparse
import gzip
import hashlib
import json
from html.parser import HTMLParser
from functools import lru_cache
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

from scripts.common import ROOT, load_json

RETIRED = ('releases', 'downloads', 'delivery/v1', 'delivery/v2/history',
           'resolution-supplements', 'commercial-completion',
           'water-reporting')


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.links = set(), []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id'):
            self.ids.add(attrs['id'])
        for key in ['href', 'src']:
            if attrs.get(key):
                self.links.append(attrs[key])
        for key in ['data-raw', 'data-defaulted']:
            if attrs.get(key):
                descriptor = json.loads(attrs[key])
                self.links.append('/archetype-atlas/' + descriptor['href'])


def check_links(root, prefix='/archetype-atlas/'):
    root = Path(root).resolve()
    if not (root/'index.html').is_file():
        return ['Missing site index.html; build is empty or incomplete']
    parsed = {}
    errors = []
    for p in root.rglob('*.html'):
        doc = Links()
        doc.feed(p.read_text(encoding='utf-8'))
        parsed[p.resolve()] = doc
    @lru_cache(maxsize=None)
    def destination(path):
        dst = (root/path[len(prefix):]).resolve()
        if not dst.is_relative_to(root):
            return None, False
        if dst.is_dir():
            dst = dst/'index.html'
        return dst, dst.is_file()

    for p, doc in parsed.items():
        base = 'https://atlas.invalid' + prefix + p.relative_to(root).as_posix()
        for href in set(doc.links):
            if urlsplit(href).scheme or href.startswith('//'):
                continue
            u = urlsplit(urljoin(base, href))
            path = unquote(u.path)
            if not path.startswith(prefix):
                errors.append(f'{p.relative_to(root)}: project prefix missing in {href}')
                continue
            dst, exists = destination(path)
            if dst is None:
                errors.append(f'{p.relative_to(root)}: URL escapes site')
                continue
            if not exists:
                errors.append(f'{p.relative_to(root)}: missing {href}')
            elif u.fragment and dst in parsed and unquote(u.fragment) not in parsed[dst].ids:
                errors.append(f'{p.relative_to(root)}: missing fragment in {href}')
    return errors


def check_size(root,max_bytes=1_000_000_000):
    total=sum(p.stat().st_size for p in Path(root).rglob('*') if p.is_file())
    return [f'Site size {total} exceeds selected publication ceiling {max_bytes} bytes'] if total>max_bytes else []


def check_active(root):
    """Check current-only routes and every full raw/defaulted program export."""
    root = Path(root)
    if not (root / 'object-index.json').exists(): return []  # Research fixture builds.
    errors = [f'Retired route present: {name}' for name in RETIRED if (root / name).exists()]
    manifest, registry = load_json(root / 'site-manifest.json'), load_json(root / 'object-index.json')
    if manifest['objects'] != len(registry): errors.append('Object registry count mismatch')
    if manifest['default_export_failures']: errors.append('Unresolved defaulted program exports: ' + str(len(manifest['default_export_failures'])))
    snapshots = root / 'delivery/v2/snapshots'
    if snapshots.exists():
        current = load_json(root / 'delivery/v2/latest.json')['snapshot_id']
        if {p.name for p in snapshots.iterdir()} != {current}: errors.append('Historical query snapshots remain')
    search = load_json(root / 'search/search_index.json')
    for entry in search['docs']:
        if any(entry['location'].startswith(name + '/') for name in RETIRED):
            errors.append('Retired route in search: ' + entry['location'])
    class Program(HTMLParser):
        def handle_starttag(self, tag, attrs):
            a = dict(attrs)
            if 'object-json' in a.get('class', '').split(): self.descriptors = a
    for identity, entry in registry.items():
        path = entry['path'].removesuffix('.md') + '/index.html' if entry['path'].endswith('.md') else entry['path']
        page = root / path
        if not page.is_file(): errors.append('Missing object page: ' + identity);continue
        if entry['table'] != 'programs': continue
        parser = Program();parser.descriptors = {};parser.feed(page.read_text(encoding='utf-8'))
        for mode in ('raw', 'defaulted'):
            try:
                descriptor = json.loads(parser.descriptors['data-' + mode])
                resource = (root / descriptor['href']).resolve()
                if not resource.is_relative_to(root.resolve()): raise ValueError('Resource path escapes site')
                encoded = resource.read_bytes()
                if len(encoded) != descriptor['size_bytes'] or hashlib.sha256(encoded).hexdigest() != descriptor['sha256']:
                    raise ValueError('Resource checksum or size mismatch')
                if descriptor['decoded_size_bytes'] > 16_000_000: raise ValueError('Decoded resource limit exceeded')
                with gzip.open(resource, 'rb') as stream: decoded = stream.read(descriptor['decoded_size_bytes'] + 1)
                if len(decoded) != descriptor['decoded_size_bytes']: raise ValueError('Decoded resource size mismatch')
                value = json.loads(decoded)
                expected_id = identity if mode == 'raw' else identity + ':defaulted:' + value['default_policy_id']
                if value['id'] != expected_id or value['export_mode'] != mode: raise ValueError('Wrong program payload')
            except (KeyError, OSError, ValueError) as error:
                errors.append(f'{identity} {mode} export: {error}')
    return errors


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--site', type=Path, default=ROOT/'build/site')
    p.add_argument('--prefix', default='/archetype-atlas/')
    args = p.parse_args()
    errors = check_links(args.site, args.prefix)+check_size(args.site)+check_active(args.site)
    if errors:
        raise SystemExit('\n'.join(errors[:50]) + f'\n{len(errors)} broken references')
    print('All built links, fragments, assets, publication size, retirement and complete program exports passed')


if __name__ == '__main__':
    main()
