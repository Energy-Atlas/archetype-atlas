"""Suite, folder, library and index pages of the site (ADR 0043).

Every page is a Markdown file holding front matter and one raw HTML block, so MkDocs
adds the theme, search and navigation while the record HTML passes through
unchanged. Section headings are written as HTML; each page carries its own short
contents list instead of a generated table of contents.
"""
import json

from scripts.site_render import (Page, esc, evidence, json_buttons, prose, reason_text, render, render_dict, render_list,
                                 schedule, zone)

RECORD_OMIT = ('evidence_ids', 'filling_evidence_ids')
CONTEXT_OMIT = ('evidence', 'assemblies', 'materials', 'metadata', 'schedules', 'id')
SECTION_MIN = 4
# A construction page whose per-context fields render larger than this loads them from the store on demand (ADR 0057).
LAZY_LIMIT = 1_500_000


def markdown(title, body, hide_toc=True):
    """A page: front matter and one raw HTML block without blank lines.

    The block is excluded from MkDocs' full-text search; the search hook gives each
    suite page one entry with its summary instead.
    """
    front = ['---', 'title: '+json.dumps(title, ensure_ascii=False)]
    if hide_toc:
        front += ['hide:', '  - toc']
    front.append('---')
    html = body.replace('\r', '').replace('\n\n', '\n')
    return '\n'.join(front)+'\n\n<div class="ea-suite" markdown="0" data-search-exclude>'+html+'</div>\n'


def section(page, key, title, body, code=None, view=None):
    """A page section; `code` names the export key it shows, `view` the export it belongs to (`source` or `filled`),
    which the version switch hides or keeps (ADR 0057)."""
    heading = esc(title)+(f' <code>{esc(code)}</code>' if code else '')
    attribute = f' data-view="{view}"' if view else ''
    return f'<section class="ea-section"{page.claim("section-"+key)}{attribute}><h2>{heading}</h2>{body}</section>'


def contents(entries):
    if len(entries) < 2:
        return ''
    links = ''.join(f'<li><a href="#section-{esc(k)}">{esc(t)}</a></li>' for k, t in entries)
    return f'<nav class="ea-contents" aria-label="On this page"><ul>{links}</ul></nav>'


def header(page, record_id, facts, release):
    rows = ''.join(f'<dt>{esc(k)}</dt><dd>{v}</dd>' for k, v in facts if v not in (None, ''))
    return (f'<p class="ea-kicker"{page.claim(record_id)}><code>{esc(record_id)}</code> · release {esc(release)}</p>'
            f'<dl class="ea-facts">{rows}</dl>')


def crumbs(page, trail):
    items = ' / '.join(f'<a href="{esc(page.rel(url))}">{esc(text)}</a>' for text, url in trail)
    return f'<nav class="ea-crumbs" aria-label="Location">{items}</nav>'


def split(record, omit):
    """Top-level fields into the overview (short) and their own sections (long or nested)."""
    overview, sections = {}, []
    for key, value in record.items():
        if key in omit:
            continue
        nested = isinstance(value, (list, dict)) and value and (len(value) >= SECTION_MIN or any(isinstance(v, (list, dict)) for v in (value if isinstance(value, list) else value.values())))
        if nested:
            sections.append(key)
        else:
            overview[key] = value
    return overview, sections


def title_of(key):
    return key.replace('_', ' ').capitalize()


VERSION_SWITCH = ('<div class="ea-switch" data-switch="version" role="group" aria-label="Version">Show: '
                  '<a href="./" data-version="">Both exports</a> · <a href="?version=source" data-version="source">Source</a> · '
                  '<a href="?version=filled" data-version="filled">Filled</a></div>')
# A filled block larger than this renders as a size note: it is in the filled JSON (a mix's per-member aggregation).
INLINE_LIMIT = 32_000
# A generation view's parameters larger than this (a ResStock dwelling's executed inputs) stay in the download.
VIEW_LIMIT = 2_000
# Export blocks a program page renders in its own section: schedules render with their plots.
EXPORT_OWN = ('schedules',)
VERSIONS = ('source', 'filled')


def same(a, b):
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def changes(source, filled):
    """The parts of the filled export that differ from the source export, one level down: {top-level key: the filled
    value, or for an object only its members that differ or are new}."""
    out = {}
    for key, value in filled.items():
        before = source.get(key, ABSENT)
        if before is not ABSENT and same(before, value):
            continue
        if isinstance(value, dict) and isinstance(before, dict):
            out[key] = {k: v for k, v in value.items() if k not in before or not same(before[k], v)}
        else:
            out[key] = value
    return out


def bounded(value, page, omit=()):
    size = len(json.dumps(value))
    if size > INLINE_LIMIT:
        return f'<p class="ea-note">{size // 1000:,} kB of JSON, in the download.</p>'
    return render(value, page, omit)


def program_page(site, pid, url, folder, mode, record, exports, schedules, evidence_rows, trail, facts=(), member_rows=None):
    """One program, rendered from its two consumer exports (ADR 0057): the source export with the download's own
    keys, then what the filled export changes, then the release record's fillings and the values no export carries,
    a mix's members, the schedules and the evidence. `exports[version]` holds the descriptor, reason, schema and
    document of each export; `facts` extra (label, HTML) header rows; `member_rows` a mix's members as table rows."""
    page = Page(site.links, url)
    extra = export_schedules(exports, site.release.schedules)
    page.local.update(schedules)
    page.local.update(s['id'] for s in extra)
    page.local.update(evidence_rows)
    source, filled = exports['source'], exports['filled']
    document = source['document'] or {}
    buttons = json_buttons([(f'Program JSON {source["schema"]} source', pid+'.source', source['descriptor'], source['reason']),
                            (f'Program JSON {filled["schema"] or source["schema"]} filled', pid+'.filled', filled['descriptor'], filled['reason'])], page)
    delta = changes(document, filled['document']) if filled['document'] is not None else {}
    own = [k for k in delta if k in EXPORT_OWN]
    delta = {k: v for k, v in delta.items() if k not in EXPORT_OWN}
    overview, keys = split(document, EXPORT_OWN)
    rows = [('Name', esc(record.get('name', pid))), *facts, ('Mode', esc(mode)),
            ('Folder', f'<a href="{esc(page.rel(trail[-1][1]))}">{esc(folder.path)}</a>')]
    if site.zoning_of.get(pid):  # the LOD study used this program (ADR 0050)
        rows.append(('Zoning recommendations', ', '.join(f'<a href="{esc(page.rel(u))}">{esc(t)}</a>' for t, u in site.zoning_of[pid])))
    body = [crumbs(page, trail), header(page, pid, rows, site.release.number), buttons, VERSION_SWITCH]
    toc = [('overview', 'Overview')]+[(k, title_of(k)) for k in keys]+[('filled', 'Filled export'), ('record', 'Release record')]
    if member_rows:
        toc.append(('members', 'Mix members'))
    toc.append(('schedules', 'Schedules'))
    if evidence_rows:
        toc.append(('evidence', 'Evidence'))
    body.append(contents(toc))
    body.append('<p class="ea-note">The sections show the source export under the keys of the downloaded JSON; '
                '<a href="#section-filled">Filled export</a> shows every block the filled export changes.</p>')
    common = {k: v for k, v in overview.items() if k not in delta}
    replaced = {k: v for k, v in overview.items() if k in delta}
    body.append(section(page, 'overview', 'Overview', render_dict(common, page)
                        + (f'<div data-view="source">{render_dict(replaced, page)}</div>' if replaced else '')))
    for key in keys:
        body.append(section(page, key, title_of(key), bounded(document[key], page), code=key, view='source' if key in delta else None))
    body.append(section(page, 'filled', 'Filled export', filled_body(page, filled, delta, own), view='filled'))
    body.append(section(page, 'record', 'Release record', record_body(page, record, [source['document'], filled['document']])))
    if member_rows:
        body.append(section(page, 'members', 'Mix members', listing(page, member_rows, ('Member program', 'Represented area (m²)', 'Weight'))))
    blocks = ''.join(schedule(site.release.schedule(s), page, site.schedule_json.get(s)) for s in schedules)
    blocks += ''.join(schedule(s, page) for s in extra)
    body.append(section(page, 'schedules', 'Schedules', blocks or '<p>None.</p>'))
    if evidence_rows:
        body.append(section(page, 'evidence', 'Evidence', ''.join(evidence(site.release.evidence_row(e), page) for e in evidence_rows)))
    return markdown(record.get('name', pid), ''.join(body))


def export_schedules(exports, stored):
    """The schedules the exports carry that are not release schedules (`stored`: resolved holiday schedules, water
    targets, composed mix schedules), once each, with the export that carries them first. Release schedules link to
    the page that renders them."""
    out = {}
    for version in VERSIONS:
        for sid, row in ((exports[version]['document'] or {}).get('schedules') or {}).items():
            if sid not in stored and sid not in out:
                out[sid] = {**row, 'id': sid, 'in_export': version}
    return list(out.values())


def filled_body(page, filled, delta, own):
    if filled['document'] is None:
        return (f'<p class="ea-notice">No filled export is published for this program: {prose(reason_text(filled["reason"]))} '
                'The source export is its consumer document.</p>')
    if not delta and not own:
        return '<p>The filled export equals the source export in every block.</p>'
    parts = ['<p>The filled export applies the fillings and approved defaults. These blocks differ from the source '
             'export and replace it; every other block is the same.</p>']
    for key, value in delta.items():
        parts.append(f'<h3>{esc(title_of(key))} <code>{esc(key)}</code></h3>'+bounded(value, page))
    if own:
        parts.append(f'<p>Schedules <code>schedules</code>: the filled export carries {len(filled["document"]["schedules"])}; '
                     'those that are not release schedules are drawn under <a href="#section-schedules">Schedules</a>.</p>')
    return ''.join(parts)


def leaves(value, path=''):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from leaves(item, f'{path}/{key}')
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from leaves(item, f'{path}/{index}')
    else:
        yield path, value


def fillings(value, path=''):
    """(path, block) of every `filling` block of a record."""
    if isinstance(value, dict):
        for key, item in value.items():
            if key == 'filling':
                yield f'{path}/filling', item
            else:
                yield from fillings(item, f'{path}/{key}')
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from fillings(item, f'{path}/{index}')


RECORD_OWN = ('/composition',)  # a mix's members render as their own table


def record_body(page, record, documents):
    """The release record's fillings, each at the field it fills, and every other record value no export carries."""
    exported = {json.dumps(v) for d in documents if d for _, v in leaves(d)}
    blocks = list(fillings(record))
    rows = [{'field': path, 'value': value} for path, value in leaves(record)
            if json.dumps(value) not in exported and not any(path.startswith(b) for b, _ in blocks)
            and not path.startswith(RECORD_OWN)]
    parts = ['<p>The release record is what both exports are built from. Its fillings (researcher assumptions and values '
             'from executed upstream code) keep their rules, basis and resolutions here, at the field they fill; the table '
             'lists every other record value that neither export carries, by its path in the record.</p>']
    for path, block in blocks:
        where = path.rsplit('/filling', 1)[0] or '/'
        parts.append(f'<div class="ea-filling" data-view="filled"><h3>Filling at <code>{esc(where)}</code></h3>{render(block, page)}</div>')
    if rows:
        parts.append(render_list(rows, page))
    return ''.join(parts)


def components_table(components, page):
    """Construction components as role, disposition, assemblies and scope; lists render as tables."""
    if not isinstance(components, dict):
        return render(components, page)
    rows = []
    for role, component in components.items():
        if not isinstance(component, dict):
            rows.append({'role': role, 'value': component})
            continue
        assignments = component.get('assignments') or []
        rows.append({'role': role, 'disposition': component.get('disposition'),
                     'assemblies': [a.get('assembly_id') for a in assignments if isinstance(a, dict)],
                     'when': [a.get('when') for a in assignments if isinstance(a, dict) and a.get('when')],
                     **{k: v for k, v in component.items() if k not in ('assignments', 'disposition')}})
    return render_list(rows, page)


def context_facets(key, document):
    """Climate label, zone and the other context axes of one construction context."""
    climate = document.get('climate') if isinstance(document.get('climate'), str) else None
    rest = key.split('.', 1)[1] if '.' in key else ''
    facets = {'climate': climate or zone(key), 'zone': zone(document.get('climate_zone') or climate or key)}
    for axis in ('foundation', 'location'):
        value = document.get(axis) if isinstance(document.get(axis), str) else None
        if value:
            facets[axis] = value
    if rest and not any(facets.get(a) == rest for a in ('foundation', 'location')) and 'foundation' not in facets and 'location' not in facets:
        facets['reference'] = rest
    if 'location' not in facets and isinstance(document.get('source_location'), str) and document['source_location']:
        facets['location'] = document['source_location']
    return {k: v for k, v in facets.items() if v}


def filter_form(contexts):
    axes = {}
    for _, facets, _ in contexts:
        for axis, value in facets.items():
            if axis != 'climate':
                axes.setdefault(axis, set()).add(value)
    climates = sorted({facets.get('climate') for _, facets, _ in contexts if facets.get('climate')})
    zones = sorted({facets.get('zone') for _, facets, _ in contexts if facets.get('zone')})
    selects = []
    options = ['<option value="">All</option>']+[f'<option value="{esc(z)}">Zone {esc(z)}</option>' for z in zones]
    options += [f'<option value="{esc(c)}">{esc(c)}</option>' for c in climates if c not in zones]
    selects.append(f'<label>Climate <select data-filter="climate">{"".join(options)}</select></label>')
    for axis in ('foundation', 'location', 'reference'):
        if axes.get(axis):
            choices = ''.join(f'<option value="{esc(v)}">{esc(v)}</option>' for v in sorted(axes[axis]))
            selects.append(f'<label>{title_of(axis)} <select data-filter="{axis}"><option value="">All</option>{choices}</select></label>')
    return (f'<form class="ea-filters" data-filters hidden>{"".join(selects)}'
            f'<output class="ea-filter-count" aria-live="polite"></output></form>')


def split_shared(documents):
    """Fields (and, one level down, sub-fields) equal in every context, and each context's own remainder."""
    same = lambda values: len({json.dumps(v, sort_keys=True) for v in values}) == 1
    fields = []
    for document in documents:
        fields.extend(f for f in document if f not in fields and f not in CONTEXT_OMIT)
    shared, own = {}, [{} for _ in documents]
    for field in fields:
        values = [d.get(field, ABSENT) for d in documents]
        if ABSENT not in values and same(values):
            shared[field] = values[0]
        elif ABSENT not in values and all(isinstance(v, dict) for v in values):
            keys = []
            for value in values:
                keys.extend(k for k in value if k not in keys)
            common = [k for k in keys if all(k in v for v in values) and same([v[k] for v in values])]
            if common:
                shared[field] = {k: values[0][k] for k in common}
            for target, value in zip(own, values):
                rest = {k: v for k, v in value.items() if k not in common}
                if rest:
                    target[field] = rest
        else:
            for target, value in zip(own, values):
                if value is not ABSENT:
                    target[field] = value
    return shared, own


ABSENT = object()


def construction_page(site, set_id, url, folder, record, contexts, used, trail, facts=()):
    """One construction set: shared fields once, each context's own fields, the assemblies and materials it uses.

    `contexts` is [(key, facets, {'detailed': document, 'descriptors': [...]})]; `used` the
    library IDs its detailed documents reference; `facts` extra (label, HTML) header rows.
    """
    page = Page(site.links, url)
    keys = [k for k, _, _ in contexts]
    documents = [c['document'] for _, _, c in contexts]
    shared, own = split_shared(documents)
    facts = [('Name', esc(record.get('name', set_id))), *facts,
             ('Contexts', str(len(keys))), ('Folder', f'<a href="{esc(page.rel(trail[-1][1]))}">{esc(folder.path)}</a>')]
    body = [crumbs(page, trail), header(page, set_id, facts, site.release.number), filter_form(contexts)]
    index_rows = []
    for key, facets, entry in contexts:
        attrs = ''.join(f' data-{a}="{esc(v)}"' for a, v in facets.items())
        index_rows.append(f'<tr data-context="{esc(key)}"{attrs}><td><a href="#context-{esc(key)}">{esc(key)}</a></td>'
                          f'<td>{esc(facets.get("climate", ""))}</td><td>{esc(" · ".join(v for a, v in facets.items() if a not in ("climate", "zone")))}</td>'
                          f'<td>{json_buttons(entry["descriptors"], page)}</td></tr>')
    toc = [('contexts', 'Contexts'), ('shared', 'Shared fields'), ('by-context', 'By context'), ('library', 'Assemblies and materials')]
    body.append(contents(toc))
    body.append(section(page, 'contexts', 'Contexts', '<div class="ea-table"><table class="ea-context-index"><thead><tr><th>Context</th><th>Climate</th>'
                        '<th>Other axes</th><th>JSON</th></tr></thead><tbody>'+''.join(index_rows)+'</tbody></table></div>'))
    shared_body = render_dict({f: v for f, v in shared.items() if f != 'components'}, page)
    if 'components' in shared:
        shared_body += '<h3>Components</h3>'+components_table(shared['components'], page)
    body.append(section(page, 'shared', 'Shared fields', shared_body))
    inners = []
    for fields in own:
        inner = render_dict({f: v for f, v in fields.items() if f != 'components'}, page) if set(fields) - {'components'} else ''
        if 'components' in fields:
            inner += '<h4>Components</h4>'+components_table(fields['components'], page)
        inners.append(inner)
    lazy = sum(len(i) for i in inners) > LAZY_LIMIT
    if lazy:  # ADR 0057: the largest sets load each context's own fields from the store when asked
        stored = [site.store.put({'set': set_id, 'context': key, 'fields': fields}) for (key, _, _), fields in zip(contexts, own)]
        inners = [f'<div class="ea-lazy" data-json="{esc(json.dumps({**d, "href": page.rel(d["href"])}, sort_keys=True, separators=(",", ":")))}">'
                  '<p class="ea-note">This set is large: each context\'s own fields load when shown. '
                  '<button type="button" class="md-button ea-show" hidden>Show its fields</button> '
                  'Without JavaScript, its complete JSON is in the context table above.</p></div>' for d in stored]
    blocks = []
    for (key, facets, _), inner in zip(contexts, inners):
        attrs = ''.join(f' data-{a}="{esc(v)}"' for a, v in facets.items())
        blocks.append(f'<section class="ea-context"{page.claim("context-"+key)}{attrs}><h3>{esc(key)}</h3>{inner}</section>')
    body.append(section(page, 'by-context', 'By context', ''.join(blocks)))
    library = [(page.link(i, site.release.library[i][2].get('name') if isinstance(site.release.library[i][2], dict) else i),
                f'<code>{esc(i)}</code>', esc(site.release.library[i][0])) for i in sorted(used) if i in site.release.library]
    body.append(section(page, 'library', 'Assemblies and materials', listing(page, library, ('Name', 'ID', 'Table')) if library else '<p>None.</p>'))
    body.append('<p class="ea-note">The page shows the detailed representation; the unified representation, where the set has one, '
                'is in its JSON. Selection decisions and evidence are in the JSON of each context.</p>')
    return markdown(record.get('name', set_id), ''.join(body))


def listing(page, rows, columns):
    head = ''.join(f'<th>{esc(c)}</th>' for c in columns)
    body = ''.join('<tr>'+''.join(f'<td>{c}</td>' for c in row)+'</tr>' for row in rows)
    return f'<div class="ea-table"><table class="ea-listing"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def generation_summary(folder):
    """A folder's generation settings in one line: programs with a block of all, by method; configurations; services."""
    generation = folder.generation
    blocks = generation.get('programs', {})
    methods = {}
    for block in blocks.values():
        methods[block.get('method')] = methods.get(block.get('method'), 0)+1
    by_method = ', '.join(f'{esc(m)} {n}' for m, n in sorted(methods.items(), key=lambda i: str(i[0])))
    return (f'{len(blocks)} of {len(folder.programs)} programs ({by_method}); {len(generation.get("configurations", {}))} '
            f'configurations; {len(generation.get("services", {}))} services')


def generation_section(page, folder, names):
    """A folder's generation.json (ADR 0051, ADR 0057): its download, its programs' methods and views, its building
    configurations and its services, rendered generically; or why the folder has none."""
    generation = folder.generation
    if generation is None:
        return f'<p>This folder has no generation settings: {prose(names.get("generation_reason") or "none is recorded")}</p>'
    parts = [json_buttons([(f'Generation JSON {generation.get("schema_version", "")}'.strip(), folder.path.strip('/').replace('/', '.')+'.generation',
                            names.get('generation_descriptor'))], page),
             f'<p>{generation_summary(folder)}. The <a href="{esc(page.rel("guides/generation-settings/"))}">generation settings guide</a> '
             'explains the methods and how the schedule generator reads them.</p>']
    view = lambda parameters: parameters or 'no parameters' if len(json.dumps(parameters)) <= VIEW_LIMIT else         f'{len(json.dumps(parameters)) // 1000:,} kB of parameters, in the generation JSON'
    rows = [{'program': pid, **{k: v for k, v in block.items() if k != 'views'},
             **{f'{name} view': view(parameters) for name, parameters in sorted(block.get('views', {}).items())}}
            for pid, block in sorted(generation.get('programs', {}).items())]
    parts.append('<h3>Programs</h3>'+render_list(rows, page))
    for cid, configuration in sorted(generation.get('configurations', {}).items()):
        rest = {k: v for k, v in configuration.items() if k != 'people'}
        people = configuration.get('people')
        table = ''
        if isinstance(people, list) and all(isinstance(r, list) and len(r) == 2 for r in people):
            table = '<h4>People: occupancy schedule and design people</h4>'+render_list(
                [{'occupancy schedule': r[0], 'design people': r[1]} for r in people], page)
        elif people is not None:
            rest['people'] = people
        parts.append(f'<section class="ea-row"{page.claim(cid)}><h3>Configuration <code>{esc(cid)}</code></h3>{render_dict(rest, page)}{table}</section>')
    if generation.get('services'):
        parts.append('<h3>Services</h3>'+render_list([{'service': sid, **block} for sid, block in sorted(generation['services'].items())], page))
    other = {k: v for k, v in generation.items() if k not in ('programs', 'configurations', 'services', 'schema_version')}
    if other:
        parts.append(render_dict(other, page))
    return ''.join(parts)


def folder_page(site, folder, url, programs, sets, schedules, evidence_rows, trail, names):
    """One template × building type: its programs and sets, its generation settings, and its mixes, services, systems
    and water. `names` holds the display template and building type, the template's description, the generation
    reason or descriptor and each program's context label."""
    page = Page(site.links, url)
    page.local.update(schedules)
    page.local.update(evidence_rows)
    link = lambda i, text: f'<a href="{esc(page.rel(site.links.pages[i]))}">{esc(text)}</a>'
    generation = generation_summary(folder) if folder.generation is not None else 'none: '+prose(names.get('generation_reason') or 'none is recorded')
    facts = [('Template', esc(names['template'])), ('Building type', esc(names['building_type'])), ('Folder', f'<code>{esc(folder.path)}</code>'),
             ('Generation settings', f'<a href="#section-generation">{generation}</a>' if folder.generation is not None else generation)]
    body = [crumbs(page, trail)]
    if names.get('description'):
        body.append(f'<p>{esc(names["description"])}</p>')
    body.append('<dl class="ea-facts">'+''.join(f'<dt>{esc(k)}</dt><dd>{v}</dd>' for k, v in facts)+'</dl>')
    toc = []
    labels = names.get('labels') or {}
    blocks = (folder.generation or {}).get('programs', {})
    if programs:
        with_labels = any(labels.get(pid) for pid, _, _ in programs)
        rows = [(link(pid, record.get('name', pid)), *((esc(labels.get(pid) or ''),) if with_labels else ()), f'<code>{esc(pid)}</code>', esc(mode),
                 esc((blocks.get(pid) or {}).get('method') or '')) for pid, mode, record in programs]
        columns = ('Program', *(('Dwelling',) if with_labels else ()), 'ID', 'Mode', 'Generation')
        body.append(section(page, 'programs', 'Programs', listing(page, rows, columns)))
        toc.append(('programs', 'Programs'))
        mixes = [(pid, record) for pid, _, record in programs if record.get('composition')]
        if mixes:
            blocks_html = ''.join(f'<h3>{link(pid, record.get("name", pid))}</h3>{render(record["composition"], page)}' for pid, record in mixes)
            body.append(section(page, 'mixes', 'Mixes', blocks_html))
            toc.append(('mixes', 'Mixes'))
    if sets:
        rows = [(link(sid, record.get('name', sid)), f'<code>{esc(sid)}</code>', str(len(record.get('contexts', {})))) for sid, record in sets]
        body.append(section(page, 'constructions', 'Construction sets', listing(page, rows, ('Set', 'ID', 'Contexts'))))
        toc.append(('constructions', 'Construction sets'))
    body.append(section(page, 'generation', 'Generation settings', generation_section(page, folder, names)))
    toc.append(('generation', 'Generation settings'))
    for table in ('services', 'systems', 'components', 'water'):
        rows = folder.tables.get(table)
        if not rows:
            continue
        if table == 'water':
            blocks_html = ''.join(f'<h3>{esc(title_of(part))}</h3>'+''.join(
                f'<section class="ea-row"><h4><code>{esc(rid)}</code></h4>{render_dict(row, page)}</section>' for rid, row in values.items())
                for part, values in rows.items() if values)
        else:
            blocks_html = ''.join(f'<section class="ea-row"{page.claim(rid)}><h3>{esc(row.get("name") or rid)}</h3><p><code>{esc(rid)}</code></p>'
                                  f'{render_dict({k: v for k, v in row.items() if k not in ("id", "name")}, page)}</section>' for rid, row in rows.items())
        body.append(section(page, table, title_of(table), blocks_html))
        toc.append((table, title_of(table)))
    if schedules:
        body.append(section(page, 'schedules', 'Schedules', ''.join(schedule(site.release.schedule(s), page, site.schedule_json.get(s)) for s in schedules)))
        toc.append(('schedules', 'Schedules'))
    if evidence_rows:
        body.append(section(page, 'evidence', 'Evidence', ''.join(evidence(site.release.evidence_row(e), page) for e in evidence_rows)))
        toc.append(('evidence', 'Evidence'))
    body.insert(1, contents(toc))
    return markdown(f'{names["template"]} · {names["building_type"]}', ''.join(body))


def tally(values):
    out = {}
    for value in values:
        out[value] = out.get(value, 0)+1
    return sorted(out.items(), key=lambda item: (-item[1], str(item[0])))


def coverage_page(site, folders, manifest):
    """What the release covers (ADR 0057), counted from this build's index: per family and template, the folders,
    programs by mode, filled exports, generation settings, construction sets, contexts and their unified
    representation, and climate zones; then the reasons for every absence, and one row per folder."""
    page = Page(site.links, 'coverage/')
    release = site.release
    groups = {}
    for path in folders:
        folder = release.folders[path]
        groups.setdefault((folder.family, folder.template), []).append(folder)
    rows, filled_reasons, unified_reasons, generation_reasons = [], [], [], []
    for (family, template), items in sorted(groups.items()):
        programs = [p for f in items for p in f.programs]
        modes = tally(release.programs[p][1] for p in programs)
        missing = [manifest['programs'][p].get('filled_reason') for p in programs if not manifest['programs'][p].get('filled')]
        filled_reasons.extend(reason_text(r) for r in missing)
        contexts = [c for f in items for s in f.sets for c in manifest['construction_sets'][s]['contexts'].values()]
        unified = sum(1 for c in contexts if c.get('unified') and c['unified'] != c.get('detailed'))
        same_document = sum(1 for c in contexts if c.get('unified') and c['unified'] == c.get('detailed'))
        unified_reasons.extend(reason_text(c.get('unified_reason')) for c in contexts if not c.get('unified'))
        generated = [f for f in items if f.generation is not None]
        generation_reasons.extend(manifest['folders'][f.path].get('generation_reason') for f in items if f.generation is None)
        zones = sorted({zone(k) or k.split('.')[0] for f in items for s in f.sets for k in release.sets[s][1].get('contexts', {})} - {None})
        name = esc(next((release.programs[p][2].get('template') for p in programs), template))
        rows.append((esc(family), f'<a href="{esc(page.rel(f"catalogue/{family}/{template}/"))}">{name}</a>', str(len(items)),
                     ', '.join(f'{esc(m)} {n}' for m, n in modes), f'{len(programs) - len(missing)} of {len(programs)}',
                     f'{len(generated)} of {len(items)} folders, {sum(len(f.generation.get("programs", {})) for f in generated)} programs',
                     str(sum(len(f.sets) for f in items)), str(len(contexts)),
                     f'{unified} own, {same_document} same as detailed, {len(contexts) - unified - same_document} none',
                     esc(' '.join(zones))))
    body = [f'<p>Release <strong>{esc(release.number)}</strong>, counted from the site index of this build '
            f'(<a href="{esc(page.rel("site-manifest.json"))}"><code>site-manifest.json</code></a>).'
            + (' <strong>This is a partial build</strong>: it counts the folders it built only.' if manifest.get('partial') else '')
            + ' The catalogue holds the programs and construction sets the sources define; it is not a sample of the building '
            'stock, and an absent export below is absent with its reason, never filled in.</p>']
    body.append(section(page, 'templates', 'By family and template', listing(page, rows, (
        'Family', 'Template', 'Folders', 'Programs by mode', 'Filled exports', 'Generation settings', 'Construction sets',
        'Contexts', 'Unified representation', 'Climate zones'))))
    for key, title, values, unit in (('filled', 'Programs without a filled export', filled_reasons, 'programs'),
                                     ('generation', 'Folders without generation settings', generation_reasons, 'folders'),
                                     ('unified', 'Contexts without a unified representation', unified_reasons, 'contexts')):
        reasons = [(prose(r or 'no reason recorded'), str(n)) for r, n in tally(values)]
        body.append(section(page, key, title, listing(page, reasons, ('Reason', unit.capitalize())) if reasons else '<p>None.</p>'))
    folder_rows = []
    for path in folders:
        folder = release.folders[path]
        entry = manifest['folders'][path]
        contexts = sum(len(manifest['construction_sets'][s]['contexts']) for s in folder.sets)
        folder_rows.append((f'<a href="{esc(page.rel("catalogue/"+path))}">{esc(path)}</a>', str(len(folder.programs)),
                            str(sum(1 for p in folder.programs if manifest['programs'][p].get('filled'))),
                            str(len(entry['compositions'])),
                            generation_summary(folder) if folder.generation is not None else 'none', str(len(folder.sets)), str(contexts)))
    body.append(section(page, 'folders', 'By folder', listing(page, folder_rows, (
        'Folder', 'Programs', 'Filled exports', 'Mixes', 'Generation settings', 'Construction sets', 'Contexts'))))
    toc = contents([('templates', 'By family and template'), ('filled', 'No filled export'), ('generation', 'No generation settings'),
                    ('unified', 'No unified representation'), ('folders', 'By folder')])
    return markdown('Coverage', toc+''.join(body))


def library_page(site, prefix, url, rows, trail):
    page = Page(site.links, url)
    groups = {}
    for rid, (table, _, row) in rows:
        groups.setdefault(table, []).append((rid, row))
    body = [crumbs(page, trail), contents([(t, title_of(t)) for t in groups])]
    for table, items in groups.items():
        blocks = ''.join(f'<section class="ea-library-row"{page.claim(rid)}><h3>{esc(row.get("name") or rid) if isinstance(row, dict) else esc(rid)}</h3>'
                         f'<p><code>{esc(rid)}</code></p>{render(row, page)}</section>' for rid, row in items)
        body.append(section(page, table, title_of(table), blocks))
    return markdown(f'{prefix.strip("/").replace("/", " · ")} library', ''.join(body))


def glossary_page(site, url, glossary):
    page = Page(site.links, url)
    body = [contents([(t, title_of(t)) for t in glossary])]
    for table, rows in glossary.items():
        blocks = ''.join(f'<dt{page.claim(key)}><code>{esc(key)}</code></dt><dd>{render(value, page)}</dd>' for key, value in rows.items())
        body.append(section(page, table, title_of(table), f'<dl class="ea-fields">{blocks}</dl>'))
    return markdown('Evidence glossary', '<p>Texts the evidence rows share: filling rules, unresolved reasons, '
                    'interpretations, transformations and source files.</p>'+''.join(body))
