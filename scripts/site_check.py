"""Check a built suite site (ADR 0043) before publication.

python -m scripts.site_check                     # build/site against its site-manifest.json
python -m scripts.site_check --require-complete  # publication: no partial build, inputs unchanged

Every internal URL and fragment resolves under the project prefix; every store file
is named by its SHA-256 and every JSON descriptor matches its file; every program and
construction set of the release has a page and its exports; retired routes are absent
from the output and from search; the site stays under the publication ceiling.
"""
import argparse
import gzip
import hashlib
import json
from functools import lru_cache
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

from scripts.common import ROOT

RETIRED = ('definitions', 'objects', 'json', 'delivery', 'releases', 'downloads', 'resolution-supplements',
           'commercial-completion', 'water-reporting', 'contracts', 'examples')
CEILING = 1_000_000_000


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.links, self.descriptors = set(), [], []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id'):
            self.ids.add(attrs['id'])
        for key in ('href', 'src'):
            if attrs.get(key):
                self.links.append(attrs[key])
        if attrs.get('data-json'):
            descriptor = json.loads(attrs['data-json'])
            self.descriptors.append(descriptor)
            self.links.append(descriptor['href'])


def parse(root):
    pages = {}
    for path in sorted(Path(root).rglob('*.html')):
        page = Page()
        page.feed(path.read_text(encoding='utf-8'))
        pages[path.resolve()] = page
    return pages


def check_links(root, pages, prefix='/archetype-atlas/'):
    root = Path(root).resolve()
    if not (root/'index.html').is_file():
        return ['Missing site index.html; the build is empty or incomplete']
    errors = []

    @lru_cache(maxsize=None)
    def destination(path):
        target = (root/path[len(prefix):]).resolve()
        if not target.is_relative_to(root):
            return None, False
        if target.is_dir():
            target = target/'index.html'
        return target, target.is_file()

    for path, page in pages.items():
        base = 'https://atlas.invalid'+prefix+path.relative_to(root).as_posix()
        for href in set(page.links):
            if urlsplit(href).scheme or href.startswith('//'):
                continue
            url = urlsplit(urljoin(base, href))
            target_path = unquote(url.path)
            if not target_path.startswith(prefix):
                errors.append(f'{path.relative_to(root)}: project prefix missing in {href}')
                continue
            target, exists = destination(target_path)
            if target is None:
                errors.append(f'{path.relative_to(root)}: URL escapes the site: {href}')
            elif not exists:
                errors.append(f'{path.relative_to(root)}: missing {href}')
            elif url.fragment and target in pages and unquote(url.fragment) not in pages[target].ids:
                errors.append(f'{path.relative_to(root)}: missing fragment in {href}')
    return errors


def check_store(root, pages):
    """Store files are named by their checksum; descriptors match their files and decode within bounds."""
    root = Path(root).resolve()
    errors, sizes = [], {}
    for path in sorted((root/'store').glob('*')):
        data = path.read_bytes()
        if path.name != hashlib.sha256(data).hexdigest()+'.json.gz':
            errors.append('Store file not named by its SHA-256: '+path.name)
        sizes[path.name] = len(data)
    for path, page in pages.items():
        for descriptor in page.descriptors:
            name = descriptor['href'].rsplit('/', 1)[-1]
            if name != descriptor['sha256']+'.json.gz' or sizes.get(name) != descriptor['size_bytes']:
                errors.append(f'{path.relative_to(root)}: descriptor does not match its store file: {name}')
            elif not 0 < descriptor['decoded_size_bytes'] <= 16_000_000:
                errors.append(f'{path.relative_to(root)}: decoded size out of bounds: {name}')
    return errors


def decoded(root, descriptor):
    data = (Path(root)/descriptor['href']).read_bytes()
    if hashlib.sha256(data).hexdigest() != descriptor['sha256']:
        raise ValueError('checksum mismatch: '+descriptor['href'])
    value = gzip.decompress(data)
    if len(value) != descriptor['decoded_size_bytes']:
        raise ValueError('decoded size mismatch: '+descriptor['href'])
    return json.loads(value)


def check_coverage(root, manifest, release_ids=None):
    """Every program and construction set of the release has a page and its exports."""
    root = Path(root)
    errors = []
    if release_ids is None:
        from scripts.site_release import SiteRelease
        release = SiteRelease(manifest['release'])
        release_ids = (set(release.programs), {s: set(r.get('contexts', {})) for s, (_, r) in release.sets.items()})
    programs, sets = release_ids
    if not manifest.get('partial'):
        missing = sorted(programs - set(manifest['programs']))+sorted(set(sets) - set(manifest['construction_sets']))
        errors.extend('No page for '+i for i in missing[:20])
    for pid, entry in manifest['programs'].items():
        if not (root/entry['page']/'index.md').is_file() and not (root/entry['page']/'index.html').is_file():
            errors.append('Missing program page: '+pid)
        if not entry.get('source'):
            errors.append(f'{pid}: no source export ({entry.get("source_reason")})')
        if not entry.get('filled') and not entry.get('filled_reason'):
            errors.append(f'{pid}: no filled export and no reason')
    for sid, entry in manifest['construction_sets'].items():
        if not (root/entry['page']/'index.md').is_file() and not (root/entry['page']/'index.html').is_file():
            errors.append('Missing construction set page: '+sid)
        if sid in sets and set(entry['contexts']) != sets[sid]:
            errors.append(f'{sid}: contexts differ from the release')
        errors.extend(f'{sid} {key}: no detailed export ({c.get("reason")})' for key, c in entry['contexts'].items() if not c.get('detailed'))
    return errors


def check_zoning(root, manifest):
    """Every zoning page the manifest names is built (ADR 0050); an older manifest without the section passes."""
    root = Path(root)
    pages = manifest.get('zoning', {}).get('pages', {})
    return [f'Missing zoning page: {url}' for url in pages.values()
            if not (root/url/'index.md').is_file() and not (root/url/'index.html').is_file()]


def check_retired(root):
    root = Path(root)
    errors = [f'Retired route present: {name}/' for name in RETIRED if (root/name).exists()]
    index = root/'search/search_index.json'
    if index.exists():
        for entry in json.loads(index.read_text(encoding='utf-8'))['docs']:
            if entry['location'].split('/', 1)[0] in RETIRED:
                errors.append('Retired route in search: '+entry['location'])
    return errors


def check_search(root, manifest):
    """Every suite page is one search entry."""
    index = Path(root)/'search/search_index.json'
    if not index.exists():
        return ['Missing search index']
    locations = {entry['location'] for entry in json.loads(index.read_text(encoding='utf-8'))['docs']}
    pages = [e['page'] for e in [*manifest['programs'].values(), *manifest['construction_sets'].values()]]
    missing = [p for p in pages if p not in locations]
    return [f'{len(missing)} suite pages missing from search, e.g. {missing[0]}'] if missing else []


def check_viewer(root):
    errors = []
    index = json.loads((Path(root)/'view-index.json').read_text(encoding='utf-8'))
    previous = ''
    for packet in index['packets']:
        try:
            rows = decoded(root, packet)
        except (OSError, ValueError) as error:
            errors.append('Viewer packet: '+str(error))
            continue
        if min(rows) != packet['first'] or packet['first'] <= previous:
            errors.append('Viewer packets out of order at '+packet['first'])
        previous = max(rows)
    return errors


def check_size(root, ceiling=CEILING):
    total = sum(p.stat().st_size for p in Path(root).rglob('*') if p.is_file())
    return [f'Site size {total:,} bytes exceeds the publication ceiling of {ceiling:,}'] if total > ceiling else []


def check_inputs(manifest):
    from scripts.suite_site import inputs_digest
    current = inputs_digest(manifest['release'])
    return [] if current == manifest['inputs_sha256'] else [
        f'Generated site inputs changed since generation ({manifest["inputs_sha256"][:12]} vs {current[:12]}); regenerate']


def check(site, prefix='/archetype-atlas/', complete=False):
    site = Path(site)
    manifest = json.loads((site/'site-manifest.json').read_text(encoding='utf-8'))
    pages = parse(site)
    errors = check_links(site, pages, prefix)+check_store(site, pages)+check_retired(site)
    errors += check_coverage(site, manifest)+check_zoning(site, manifest)+check_search(site, manifest)+check_viewer(site)+check_size(site)
    if complete:
        if manifest.get('partial'):
            errors.append('Partial build (--only) cannot be published')
        errors += check_inputs(manifest)
    return errors, manifest, len(pages)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--site', type=Path, default=ROOT/'build/site')
    parser.add_argument('--prefix', default='/archetype-atlas/')
    parser.add_argument('--require-complete', action='store_true', help='publication: a full build of unchanged inputs')
    args = parser.parse_args()
    errors, manifest, count = check(args.site, args.prefix, args.require_complete)
    if errors:
        raise SystemExit('\n'.join(errors[:50])+f'\n{len(errors)} errors')
    size = sum(p.stat().st_size for p in args.site.rglob('*') if p.is_file())
    print(f'Release {manifest["release"]}: {count:,} HTML pages, {len(manifest["programs"]):,} programs and '
          f'{len(manifest["construction_sets"]):,} construction sets with pages and exports; links, fragments, store, '
          f'search, viewer and retirement checks passed; {size:,} bytes')


if __name__ == '__main__':
    main()
