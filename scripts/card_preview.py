"""Build or serve a small UI-only preview; never generate research delivery."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import re
import shutil

from scripts.common import ROOT
from scripts.active_site import landing
from scripts.definition_contract import DefinitionBundle
from scripts.definition_site import generate, write


OUTPUT = ROOT / 'build/card-preview'
NOTICE = ('<p class="ea-hero__meta">LOCAL DESIGN PREVIEW · '
          'Catalogue data and JSON exports are omitted.</p>\n\n')
GUIDES = {
    'selection': 'Select, inspect and copy',
    'schedules': 'Inspect schedules',
    'program-json': 'Program JSON contract',
    'construction-json': 'Construction JSON contract',
    'definitions': 'Library definitions',
}


def build():
    from mkdocs.config import load_config
    from mkdocs.commands.build import build as mkdocs_build

    docs = OUTPUT / 'docs'
    docs.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / 'website/assets', docs / 'assets', dirs_exist_ok=True)
    bundle = DefinitionBundle()
    # Empty finders exercise the production card markup without reading releases,
    # producing exports, fetching vendor assets or rendering any object pages.
    generate(bundle, docs, publish=False, pages=False)
    home = landing(bundle).replace('0 programs · 0 constructions · 0 HVAC systems',
                                   'Local design preview · catalogue data omitted')
    write(docs, 'index.md', home)
    for name, title in GUIDES.items():
        write(docs, f'guides/{name}.md', f'# {title}\n\n'
              'This page is a typography specimen for the local card preview. '
              'The full catalogue and its research artifacts are not included.\n\n'
              '[Back to the catalogue](../catalogue.md)\n\n'
              '## Reading the library\n\n'
              'Programs, constructions and HVAC systems retain their source context. '
              'Unknown values remain explicit.\n\n'
              '!!! note "Layout specimen"\n\n'
              '    Preview the shared typography, links, focus controls and page frame.\n')
    write(docs, 'sources.md', '# Sources and notices\n\n'
          'This local preview includes UI assets only. No research data is shipped.\n\n'
          'Self-hosted fonts retain their SIL Open Font License notices:\n\n'
          '- [Geist](assets/fonts/OFL-Geist.txt)\n'
          '- [Geist Mono](assets/fonts/OFL-GeistMono.txt)\n'
          '- [Cormorant Garamond](assets/fonts/OFL-CormorantGaramond.txt)\n')
    for path in docs.rglob('*.md'):
        text = path.read_text(encoding='utf-8')
        if text.startswith('---\n'):
            front, body = text.split('\n---\n', 1)
            text = front + '\n---\n\n' + NOTICE + body.lstrip('\n')
        else:
            title = re.search(r'^# (.+)$', text, re.M)[1]
            text = f'---\ntitle: {title}\n---\n\n' + NOTICE + text
        path.write_text(text, encoding='utf-8', newline='\n')
    config = load_config(config_file=str(ROOT / 'mkdocs.yml'),
                         docs_dir=str(docs), site_dir=str(OUTPUT / 'www/archetype-atlas'),
                         site_url='http://127.0.0.1:8766/archetype-atlas/')
    mkdocs_build(config)
    pages = len(list((OUTPUT / 'www').rglob('*.html')))
    print(f'Strict display build: {pages} HTML pages; no research exports or record pages.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serve', action='store_true', help='Serve the already-built display preview on loopback only')
    args = parser.parse_args()
    if args.serve:
        if not (OUTPUT / 'www/archetype-atlas/index.html').is_file():
            parser.error('Build the preview first: python -m scripts.card_preview')
        handler = partial(SimpleHTTPRequestHandler, directory=str(OUTPUT / 'www'))
        print('Local card preview: http://127.0.0.1:8766/archetype-atlas/', flush=True)
        ThreadingHTTPServer(('127.0.0.1', 8766), handler).serve_forever()
    else:
        build()


if __name__ == '__main__':
    main()
