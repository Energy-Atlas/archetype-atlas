"""Generate the suite-based catalogue of one release (ADR 0043, ADR 0036 section 10).

python -m scripts.suite_site                      # the newest release into build/site-docs
python -m scripts.suite_site --release 1.4.0      # a named release
python -m scripts.suite_site --sample 1           # one folder per family × template (pull requests)
python -m scripts.suite_site --digest             # the input digest CI caches the output under

One page per program and per construction set, one page per template × building
type folder and per template library, the `view/?id=` viewer, and one
content-addressed JSON store (`store/`) for every export. The output is a pure
function of the release and the scripts; `site-manifest.json` records the release,
the input digest, every page and export, and the program and folder index BEMGen reads (ADR 0052). A sample (`--sample N`, `sample_folders`)
builds the site-wide pages and at most N folders of every family × template, chosen by
a fixed rule, and records them in the manifest; like `--only` it cannot be published.
"""
import argparse
import ast
import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path

from scripts.common import ROOT
from scripts.lod_site import write_zoning
from scripts.site_pages import (construction_page, context_facets, folder_page, glossary_page, library_page, markdown,
                                program_page)
from scripts.site_release import FAMILIES, RELEASES, SiteRelease, page_slug, space_type
from scripts.site_render import Links, anchor, esc
from scripts.site_store import Store, canonical

VERSIONS = ('source', 'filled')
REPRESENTATIONS = ('detailed', 'unified')
GUIDES = ('selection.md', 'schedules.md', 'program-json.md', 'construction-json.md', 'definitions.md',
          'doe-reference-reconciliation.md', 'construction-only-programs.md', 'iecc-commercial.md',
          'residential-dwellings.md', 'iecc-residential.md', 'manufactured-housing.md')
# Besides the modules the generator imports (`generator_modules`), and the policy and input files they read.
DIGEST_INPUTS = ('scripts/__init__.py', 'website', 'schemas', 'mkdocs.yml', 'requirements-site.txt',
                 'sources/program-composition-policy.json',
                 'sources/dhw-conversion-evidence-lock.json', 'data/program-inputs/residential-v1.json',
                 'data/program-inputs/er-triage-v1.json', 'data/program-inputs/dhw-conversion-v1.json',
                 'data/system-inputs/source-v1.json', 'data/lod-recommendations')
ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{5,}$')
# Not `library/`: a template library page must never share a path with a building-type folder page.
LIBRARY = 'template-library'


# Exports run in worker processes, each with its own resolved release.

_release = None


def _start(number):
    global _release
    from scripts.atlas_exports import Release
    _release = Release(release=number)


def _programs(ids):
    out = []
    for pid in ids:
        for version in VERSIONS:
            try:
                out.append((pid, version, canonical(_release.program(pid, version)), None))
            except ValueError as error:
                out.append((pid, version, None, str(error)))
    return out


def _construction(set_id):
    record = _release.constructions.sets[set_id]
    out = []
    for key in record['contexts']:
        for representation in REPRESENTATIONS:
            try:
                out.append((key, representation, canonical(_release.construction(set_id, key, representation)), None))
            except ValueError as error:
                out.append((key, representation, None, str(error)))
    return set_id, out


def unordered(executor, function, items, window):
    """Results as they complete, with at most `window` tasks outstanding so large results never pile up."""
    items, running = iter(items), set()
    for item in items:
        running.add(executor.submit(function, item))
        if len(running) >= window:
            break
    while running:
        done, running = concurrent.futures.wait(running, return_when=concurrent.futures.FIRST_COMPLETED)
        for future in done:
            item = next(items, None)
            if item is not None:
                running.add(executor.submit(function, item))
            yield future.result()


# Inputs and placement.

def imported_modules(path):
    """The repository modules a Python file imports by absolute name."""
    out = []
    for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
        names = [node.module] if isinstance(node, ast.ImportFrom) and node.module and not node.level else \
            [alias.name for alias in node.names] if isinstance(node, ast.Import) else []
        out.extend(name for name in names if name.split('.')[0] in ('scripts', 'atlas_schedules'))
    return out


def generator_modules():
    """The repository modules the generator and the MkDocs hooks import, directly or not, sorted: only these
    scripts enter the digest."""
    seen = set()
    todo = ['scripts.suite_site'] + [m for hook in sorted((ROOT/'website/hooks').glob('*.py')) for m in imported_modules(hook)]
    while todo:
        module = todo.pop()
        path = ROOT/(module.replace('.', '/')+'.py')
        if module in seen or not path.is_file():
            continue
        seen.add(module)
        todo.extend(imported_modules(path))
    return sorted(seen)


def inputs_digest(number):
    """SHA-256 over the release manifests and everything the generator and MkDocs read from the checkout."""
    paths = []
    release = RELEASES/f'v{number}'
    manifest = json.loads((release/'manifest.json').read_bytes())
    paths.append(release/'manifest.json')
    if manifest.get('base_release'):
        paths.append(ROOT/manifest['base_release']['path']/'manifest.json')
    paths.extend(ROOT/(module.replace('.', '/')+'.py') for module in generator_modules())
    for name in DIGEST_INPUTS:
        path = ROOT/name
        paths.extend(sorted(p for p in path.rglob('*') if p.is_file() and '__pycache__' not in p.parts) if path.is_dir() else [path])
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.relative_to(ROOT).as_posix().encode()+b'\0'+hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def strings(value, out):
    if isinstance(value, str):
        out.append(value)
    elif isinstance(value, dict):
        for item in value.values():
            strings(item, out)
    elif isinstance(value, list):
        for item in value:
            strings(item, out)
    return out


def referenced(value, pool):
    """IDs from `pool` that a record mentions, in first-mention order."""
    seen = {}
    for text in strings(value, []):
        if text in pool and text not in seen:
            seen[text] = None
    return list(seen)


class Site:
    def __init__(self, release, target):
        self.release, self.target = release, Path(target)
        self.links = Links()
        self.store = Store(target)
        self.schedule_json = {}
        self.urls, self.summaries, self.written = {}, {}, set()
        self.zoning_of = {}  # program ID: [(prototype name, zoning page URL)] (ADR 0050)

    def folder_url(self, folder):
        return 'catalogue/'+folder

    def place(self):
        """Every published object's home page, before any page is written."""
        release, links = self.release, self.links
        for folder in release.folders.values():
            taken = {}
            for kind, ids in (('programs', folder.programs), ('constructions', folder.sets)):
                for rid in ids:
                    taken.setdefault((kind, page_slug(rid, folder.path)), []).append(rid)
            for (kind, slug), ids in taken.items():
                for rid in ids:
                    unique = slug if len(ids) == 1 else slug+'-'+rid.rsplit('.', 1)[1]
                    self.urls[rid] = f'{self.folder_url(folder.path)}{kind}/{unique}/'
                    links.place(rid, self.urls[rid])
        for folder in release.folders.values():
            for table in ('services', 'systems', 'components'):
                for rid in folder.tables.get(table, {}):
                    links.place(rid, self.folder_url(folder.path))
        for rid, (_, prefix, _) in sorted(release.library.items()):
            links.place(rid, library_url(prefix))
        for pid in sorted(release.programs):
            for sid in referenced(release.programs[pid][2], release.schedules):
                links.place(sid, self.urls[pid])
        for folder in release.folders.values():
            for sid in referenced(folder.tables, release.schedules):
                links.place(sid, self.folder_url(folder.path))
        for table, rows in release.glossary.items():
            for key in rows:
                if ID.match(key):
                    links.place(key, 'catalogue/glossary/')
        links.viewer.update(release.evidence)

    def write(self, relative, text):
        if relative in self.written:
            raise ValueError('Two pages share one path: '+relative)
        self.written.add(relative)
        path = self.target/relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode('utf-8'))


def library_url(prefix):
    return f'catalogue/{prefix}{LIBRARY}/'


def trail_of(folder):
    family, template = folder.split('/')[:2]
    return [('Catalogue', 'catalogue/'), (FAMILIES[family], f'catalogue/{family}/'), (template, f'catalogue/{family}/{template}/'),
            (folder.split('/')[2], 'catalogue/'+folder)]


def folder_cost(release, folder):
    """Programs and construction contexts: what a folder's export costs."""
    return len(folder.programs)+sum(len(release.sets[s][1].get('contexts', {})) for s in folder.sets)


def sample_folders(release, per_template=1):
    """At most `per_template` folders of every family × template, by a fixed rule: the folders whose programs span
    the most modes (source, general, department, dwelling) first, then the cheapest, then the first path. One per
    template builds every page kind (and every template index the library pages link to) at a fraction of the cost."""
    groups = {}
    for folder in release.folders.values():
        groups.setdefault((folder.family, folder.template), []).append(folder)
    chosen = []
    for key in sorted(groups):
        ranked = sorted(groups[key], key=lambda f: (-len({release.programs[p][1] for p in f.programs}), folder_cost(release, f), f.path))
        chosen.extend(f.path for f in ranked[:per_template])
    return sorted(chosen)


def generate(target, number=None, jobs=None, only=None, sample=None):
    """Write the MkDocs input tree of one release into `target` (a fresh directory)."""
    release = SiteRelease(number)
    site = Site(release, target)
    site.place()
    zoning = write_zoning(site)  # before the program pages, which link to their prototype's zoning page
    if sample is not None:
        folders = sample_folders(release, sample)
    else:
        folders = sorted(f for f in release.folders if only is None or re.search(only, f))
    program_ids = [p for p in sorted(release.programs) if release.programs[p][0] in folders]
    set_ids = [s for s in sorted(release.sets) if release.sets[s][0] in folders]
    for sid in sorted(release.schedules):
        if release.schedules[sid] in folders:
            site.schedule_json[sid] = site.store.put({'release': release.number, **release.schedule(sid)})
    manifest = {'programs': {}, 'construction_sets': {}, 'folders': {}}
    jobs = jobs or min(os.cpu_count() or 1, 6)
    with concurrent.futures.ProcessPoolExecutor(jobs, initializer=_start, initargs=(release.number,)) as pool:
        chunks = [program_ids[i:i+24] for i in range(0, len(program_ids), 24)]
        exports = {}
        for results in unordered(pool, _programs, chunks, jobs*2):
            for pid, version, data, reason in results:
                entry = exports.setdefault(pid, {})
                descriptor = site.store.put(json.loads(data)) if data else None
                schema = json.loads(data)['schema_version'] if data else None
                entry[version] = {'descriptor': descriptor, 'reason': reason, 'schema': schema}
        for pid in program_ids:
            write_program(site, pid, exports[pid], manifest)
        for set_id, results in unordered(pool, _construction, set_ids, jobs*2):
            write_construction(site, set_id, results, manifest)
    for folder in folders:
        write_folder(site, release.folders[folder], manifest)
    write_libraries(site)
    site.write('catalogue/glossary/index.md', glossary_page(site, 'catalogue/glossary/', release.glossary))
    write_indexes(site, folders)
    write_viewer(site)
    write_guides(site)
    site.write('search-summaries.json', json.dumps(site.summaries, ensure_ascii=False, sort_keys=True, indent=0))
    counts = {**release.counts(), 'program_pages': len(manifest['programs']), 'construction_pages': len(manifest['construction_sets']),
              'folder_pages': len(folders), 'store_files': len(site.store.files), 'store_bytes': sum(site.store.files.values()),
              'zoning_pages': len(zoning['pages'])}
    result = {'kind': 'atlas_site', 'release': release.number, 'generated_by': 'python -m scripts.suite_site',
              'release_manifest_sha256': hashlib.sha256((RELEASES/f'v{release.number}/manifest.json').read_bytes()).hexdigest(),
              'inputs_sha256': inputs_digest(release.number), 'partial': only is not None or sample is not None,
              **({'sample': {'folders_per_template': sample, 'folders': folders}} if sample is not None else {}),
              'counts': counts, 'zoning': zoning, **manifest}
    site.write('site-manifest.json', json.dumps(result, ensure_ascii=False, sort_keys=True, indent=1)+'\n')
    return result


def summary(*parts):
    return ' · '.join(str(p) for p in parts if p)


def write_program(site, pid, exports, manifest):
    release = site.release
    folder_path, mode, record = release.programs[pid]
    folder = release.folders[folder_path]
    url = site.urls[pid]
    schedules = referenced(record, release.schedules)
    evidence_rows = referenced(record, release.evidence)
    site.write(url+'index.md', program_page(site, pid, url, folder, mode, record, exports, schedules, evidence_rows, trail_of(folder_path)))
    site.summaries[url] = summary(record.get('name'), pid, record.get('template'), record.get('building_type'), mode,
                                  record.get('climate'), 'program')
    manifest['programs'][pid] = {'page': url, **{v: (exports[v]['descriptor'] or {}).get('href') for v in VERSIONS},
                                 **({'filled_reason': exports['filled']['reason']} if exports['filled']['reason'] else {}),
                                 **({'source_reason': exports['source']['reason']} if exports['source']['reason'] else {}),
                                 **program_index(folder_path, mode, record)}


def program_index(folder, mode, record):
    """What a consumer needs to place a program without its export (ADR 0052): its space type (explicit null where the
    name is not `<space type>_<building type>`), building type, release folder and mode."""
    return {'space_type': space_type(record), 'building_type': record.get('building_type'), 'folder': folder, 'mode': mode}


def folder_index(site, folder):
    """A folder's entry in the site index (ADR 0052): its programs and its generation.json in the store, or null."""
    generation = site.store.put(folder.generation) if folder.generation is not None else None
    return {'family': folder.family, 'template': folder.template, 'building_type': folder.building_type,
            'programs': sorted(folder.programs), 'generation': generation}


def write_construction(site, set_id, results, manifest):
    release = site.release
    folder_path, record = release.sets[set_id]
    url = site.urls[set_id]
    documents, failures = {}, {}
    for key, representation, data, reason in results:
        if data is None:
            failures[(key, representation)] = reason
            continue
        documents.setdefault(key, {})[representation] = (json.loads(data), site.store.put(json.loads(data)))
    contexts, used, entries = [], set(), {}
    for key in record['contexts']:
        detailed = documents.get(key, {}).get('detailed')
        if detailed is None:
            entries[key] = {'detailed': None, 'reason': failures.get((key, 'detailed'))}
            continue
        document, descriptor = detailed
        unified = documents[key].get('unified')
        same = unified is not None and unified[1]['sha256'] == descriptor['sha256']
        label = f'{document.get("kind", "construction").replace("_", " ")} {document.get("schema_version", "")}'.strip()
        buttons = [(label if same else f'Detailed {document.get("schema_version", "")}', f'{set_id}.{key}.detailed', descriptor)]
        if not same:
            buttons.append((f'Unified {unified[0].get("schema_version", "") if unified else ""}'.strip(), f'{set_id}.{key}.unified',
                            unified[1] if unified else None, failures.get((key, 'unified'), 'no unified representation')))
        for table in ('assemblies', 'materials'):
            used.update(document.get(table) or {})
        contexts.append((key, context_facets(key, document), {'document': document, 'descriptors': buttons}))
        entries[key] = {'detailed': descriptor['href'], 'unified': None if same or not unified else unified[1]['href'],
                        **({'unified_reason': failures[(key, 'unified')]} if (key, 'unified') in failures else {})}
    if contexts:
        site.write(url+'index.md', construction_page(site, set_id, url, release.folders[folder_path], record, contexts, used, trail_of(folder_path)))
    climates = sorted({c[1].get('climate') for c in contexts if c[1].get('climate')})
    site.summaries[url] = summary(record.get('name'), set_id, folder_path, 'construction set', ' '.join(climates[:40]))
    manifest['construction_sets'][set_id] = {'page': url, 'contexts': entries}


def write_folder(site, folder, manifest):
    release = site.release
    url = site.folder_url(folder.path)
    programs = [(pid, release.programs[pid][1], release.programs[pid][2]) for pid in folder.programs]
    sets = [(sid, release.sets[sid][1]) for sid in folder.sets]
    schedules = referenced(folder.tables, release.schedules)
    evidence_rows = referenced(folder.tables, release.evidence)
    site.write(url+'index.md', folder_page(site, folder, url, programs, sets, schedules, evidence_rows, trail_of(folder.path)[:-1]))
    site.summaries[url] = summary(folder.template, folder.building_type, FAMILIES[folder.family], 'folder')
    manifest['folders'][folder.path] = folder_index(site, folder)


def write_libraries(site):
    groups = {}
    for rid, row in site.release.library.items():
        groups.setdefault(row[1], []).append((rid, row))
    for prefix, rows in sorted(groups.items()):
        url = library_url(prefix)
        family, template = prefix.strip('/').split('/')
        trail = [('Catalogue', 'catalogue/'), (FAMILIES[family], f'catalogue/{family}/'), (template, f'catalogue/{prefix}')]
        site.write(url+'index.md', library_page(site, prefix, url, sorted(rows), trail))


def table_html(rows, columns):
    head = ''.join(f'<th>{esc(c)}</th>' for c in columns)
    body = ''.join('<tr>'+''.join(f'<td>{c}</td>' for c in row)+'</tr>' for row in rows)
    return f'<div class="ea-table"><table class="ea-listing"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def write_indexes(site, folders):
    release = site.release
    tree = {}
    for folder in folders:
        family, template, building_type = folder.strip('/').split('/')
        tree.setdefault(family, {}).setdefault(template, []).append(release.folders[folder])
    libraries = {row[1] for row in release.library.values()}
    family_rows = []
    for family, templates in sorted(tree.items()):
        rows = []
        for template, items in sorted(templates.items()):
            rows.append((f'<a href="{template}/">{esc(template)}</a>', str(len(items)), str(sum(len(f.programs) for f in items)),
                         str(sum(len(f.sets) for f in items))))
            type_rows = [(f'<a href="{f.building_type}/">{esc(f.building_type)}</a>', str(len(f.programs)), str(len(f.sets)),
                          str(sum(len(f.tables.get(t, {})) for t in ('services', 'systems'))))
                         for f in items]
            library = (f'<p><a href="{LIBRARY}/">Template library</a>: assemblies, materials and performance rules.</p>'
                       if f'{family}/{template}/' in libraries else '')
            site.write(f'catalogue/{family}/{template}/index.md', markdown(
                f'{FAMILIES[family]} · {template}', f'<nav class="ea-crumbs"><a href="../../">Catalogue</a> / <a href="../">{esc(FAMILIES[family])}</a></nav>'
                + library + table_html(type_rows, ('Building type', 'Programs', 'Construction sets', 'Services and systems'))))
        site.write(f'catalogue/{family}/index.md', markdown(FAMILIES[family], '<nav class="ea-crumbs"><a href="../">Catalogue</a></nav>'
                                                            + table_html(rows, ('Template', 'Building types', 'Programs', 'Construction sets'))))
        family_rows.append((f'<a href="{family}/">{esc(FAMILIES[family])}</a>', str(len(templates)),
                            str(sum(len(f.programs) for items in templates.values() for f in items)),
                            str(sum(len(f.sets) for items in templates.values() for f in items))))
    counts = release.counts()
    site.write('catalogue/index.md', markdown('Catalogue', (
        f'<p>Release <strong>{esc(release.number)}</strong>: {counts["programs"]:,} programs, {counts["construction_sets"]:,} construction sets '
        f'with {counts["contexts"]:,} contexts, in {counts["folders"]:,} template × building type folders. Older releases stay as Git tags and '
        'release folders; this catalogue shows the latest release only.</p>'
        + table_html(family_rows, ('Family', 'Templates', 'Programs', 'Construction sets'))
        + '<p><a href="glossary/">Evidence glossary</a> · <a href="../view/">Look up an ID</a></p>')))
    site.write('index.md', landing(release, counts))


def write_viewer(site):
    """The `view/?id=` index: every ID with its page and anchor, or its own JSON."""
    rows = {}
    for identifier, url in site.links.pages.items():
        rows[identifier] = {'page': url, 'anchor': anchor(identifier)}
    for identifier in site.links.viewer:
        if identifier not in rows:
            rows[identifier] = {'object': site.release.evidence_row(identifier)}
    for identifier, descriptor in site.schedule_json.items():
        rows.setdefault(identifier, {})['json'] = descriptor
    packets, firsts = site.store.packets(rows)
    index = {'release': site.release.number, 'packets': [{'first': f, **d} for f, d in zip(firsts, packets)]}
    site.write('view-index.json', json.dumps(index, sort_keys=True, separators=(',', ':')))
    site.write('view/index.md', markdown('Look up an ID', (
        '<div class="ea-viewer" data-viewer data-index="../view-index.json" data-root="../">'
        '<form class="ea-viewer__form"><label>ID <input name="id" type="search" autocomplete="off" spellcheck="false" size="60"></label> '
        '<button type="submit" class="md-button">Show</button></form><p class="ea-viewer__status" role="status" aria-live="polite"></p>'
        '<div class="ea-viewer__result"></div>'
        '<noscript><p>The viewer needs JavaScript. Every program and construction set has its own page in the '
        '<a href="../catalogue/">catalogue</a>, which reads without JavaScript.</p></noscript></div>'
        '<script src="../assets/view.js"></script>')))


def landing(release, counts):
    return ('---\nhide:\n  - navigation\n  - toc\n---\n\n<div class="ea-hero" markdown>\n\n'
            '# Deterministic energy definitions<br>*for zoning experiments.* { #energy-archetype-atlas }\n\n'
            'One page per program and per construction set of the latest release, with schedules, loads, fillings and '
            'evidence in place, and both consumer exports a click away.\n\n'
            f'Release {release.number} · {counts["programs"]:,} programs · {counts["construction_sets"]:,} construction sets · '
            f'{counts["folders"]:,} folders\n{{ .ea-hero__meta }}\n\n'
            '[Open the catalogue](catalogue/index.md){ .md-button .md-button--primary }\n\n</div>\n\n'
            '## Catalogue { .ea-strip data-index="01" data-note="Two building families" }\n\n'
            '<div class="grid cards icon-cards" markdown>\n\n'
            '-   <span class="ea-card-icon" data-icon="house"></span>[Residential](catalogue/residential/index.md)\n\n'
            '    Dwelling programs and envelopes: ResStock dwellings, IECC residential and manufactured-housing prototypes.\n\n'
            '-   <span class="ea-card-icon" data-icon="office"></span>[Non residential](catalogue/commercial/index.md)\n\n'
            '    Programs, mixes, construction sets, services and systems by template and building type.\n\n'
            '</div>\n\n'
            '## How to use { .ea-strip data-index="02" data-note="Four guides" }\n\n'
            '<div class="grid cards compact icon-cards" markdown>\n\n'
            '1.  <span class="ea-card-icon" data-icon="select-copy"></span>[Selection and copying](guides/selection.md)\n\n'
            '    Find a suite page, switch version and context, and copy or download its JSON.\n\n'
            '2.  <span class="ea-card-icon" data-icon="schedule"></span>[Schedule inspection](guides/schedules.md)\n\n'
            '    Rules and day profiles, and annual series as monthly and typical-day plots.\n\n'
            '3.  <span class="ea-card-icon" data-icon="json-document"></span>[Program JSON contract](guides/program-json.md)\n\n'
            '    The source and filled program exports.\n\n'
            '4.  <span class="ea-card-icon" data-icon="definitions"></span>[Library definitions](guides/definitions.md)\n\n'
            '    What programs, construction sets and folder records supply.\n\n'
            '</div>\n\n'
            '## Zoning recommendations { .ea-strip data-index="03" data-note="Geometric LOD study" }\n\n'
            'Which thermal zoning of each DOE prototype keeps its ideal sensible heating and cooling within a stated error of '
            'the full zoning, per climate zone, vintage and orientation, with the benchmark values and errors behind each pick.\n\n'
            '[Zoning recommendations](zoning/index.md){ .md-button }\n\n'
            '## Sources { .ea-strip data-index="04" data-note="Notices" }\n\n'
            'The library derives from checksum-locked OpenStudio Standards, DOE/PNNL, ComStock and ResStock evidence. '
            'Upstream notices continue to apply.\n\n'
            '[Sources and notices](sources.md){ .md-button }\n')


def write_guides(site):
    for guide in GUIDES:
        site.write('guides/'+guide, (ROOT/'website/content/guides'/guide).read_text(encoding='utf-8'))
    notices = site.target/'notices'
    notices.mkdir(exist_ok=True)
    shutil.copyfile(ROOT/'LICENSE', notices/'original-work.txt')
    links = ['[Original-work notice](notices/original-work.txt)']
    for path in sorted(p for p in site.release.files if p.startswith('notices/')):
        name = path.split('/', 1)[1]
        (notices/name).write_bytes(site.release.files[path])
        links.append(f'[{Path(name).stem}](notices/{name})')
    site.write('sources.md', '# Sources and notices\n\n'
               f'Release {site.release.number} derives from checksum-locked OpenStudio Standards, DOE/PNNL, ComStock and ResStock evidence. '
               'Code/prototype and existing-stock contexts remain distinct. Every page names its record\'s evidence: '
               'source locators, original values and transformations.\n\n' + ' · '.join(links) + '\n\n'
               'Site fonts, SIL Open Font License 1.1: [Geist](assets/fonts/OFL-Geist.txt) · [Geist Mono](assets/fonts/OFL-GeistMono.txt) · '
               '[Cormorant Garamond](assets/fonts/OFL-CormorantGaramond.txt)\n\nOriginal code is MIT-licensed and original data and documentation are CC BY 4.0; upstream notices continue to apply.\n')


def build(target, number=None, jobs=None, only=None, sample=None):
    """Generate into a fresh staging directory beside `target`, then replace it."""
    target = Path(target).resolve()
    build_root = (ROOT/'build').resolve()
    if target in {ROOT.resolve(), build_root} or (target.is_relative_to(ROOT) and not target.is_relative_to(build_root)):
        raise ValueError('Refuse to replace repository sources or the build root')
    if target.exists() and any(target.iterdir()) and not (target/'site-manifest.json').is_file():
        raise ValueError('Existing output must be a generated site tree (site-manifest.json)')
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent) as temporary:
        stage = Path(temporary)/'docs'
        shutil.copytree(ROOT/'website/assets', stage/'assets')
        result = generate(stage, number, jobs, only, sample)
        if target.exists():
            shutil.rmtree(target)
        stage.rename(target)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--release', help='release number, e.g. 1.4.0 (default: the newest under data/atlas-releases)')
    parser.add_argument('--output', type=Path, default=ROOT/'build/site-docs')
    parser.add_argument('--jobs', type=int, help="export worker processes (default: CPU count, at most 6; each holds the resolved release)")
    partial = parser.add_mutually_exclusive_group()
    partial.add_argument('--only', help='regular expression over folders, for a partial preview build')
    partial.add_argument('--sample', type=int, metavar='N', help='at most N folders of every family × template, by a fixed rule (pull requests)')
    parser.add_argument('--digest', action='store_true', help='print the input digest and exit')
    args = parser.parse_args()
    from scripts.site_release import newest
    if args.digest:
        print(inputs_digest(args.release or newest()))
        return
    result = build(args.output, args.release, args.jobs, args.only, args.sample)
    print(json.dumps({k: result[k] for k in ('release', 'inputs_sha256', 'counts', *(['sample'] if 'sample' in result else []))}, indent=1))


if __name__ == '__main__':
    main()
