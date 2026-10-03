"""Check every built internal URL/fragment, including project-subpath assets."""
import argparse
from html.parser import HTMLParser
from functools import lru_cache
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

from scripts.common import ROOT


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


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--site', type=Path, default=ROOT/'build/site')
    p.add_argument('--prefix', default='/archetype-atlas/')
    args = p.parse_args()
    errors = check_links(args.site, args.prefix)
    if errors:
        raise SystemExit('\n'.join(errors[:50]) + f'\n{len(errors)} broken references')
    print('All built internal links, fragments and project-subpath assets passed')


if __name__ == '__main__':
    main()
