"""Suite, folder, library and index pages of the site (ADR 0043).

Every page is a Markdown file holding front matter and one raw HTML block, so MkDocs
adds the theme, search and navigation while the record HTML passes through
unchanged. Section headings are written as HTML; each page carries its own short
contents list instead of a generated table of contents.
"""
import json

from scripts.site_render import (Page, esc, evidence, json_buttons, render, render_dict, render_list, schedule,
                                 zone)

RECORD_OMIT = ('evidence_ids', 'filling_evidence_ids')
CONTEXT_OMIT = ('evidence', 'assemblies', 'materials', 'metadata', 'schedules', 'id')
SECTION_MIN = 4


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


def section(page, key, title, body):
    return f'<section class="ea-section"{page.claim("section-"+key)}><h2>{esc(title)}</h2>{body}</section>'


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


VERSION_SWITCH = ('<div class="ea-switch" data-switch="version" role="group" aria-label="Version">Version: '
                  '<a href="./" data-version="">Source and fillings</a> · <a href="?version=source" data-version="source">Source</a> · '
                  '<a href="?version=filled" data-version="filled">Filled</a></div>')


def program_page(site, pid, url, folder, mode, record, exports, schedules, evidence_rows, trail):
    """One program: its fields with fillings in place, its schedules and its evidence."""
    page = Page(site.links, url)
    page.local.update(schedules)
    page.local.update(evidence_rows)
    source, filled = exports['source'], exports['filled']
    notice = ''
    if filled['descriptor'] is None:
        notice = (f'<p class="ea-notice" data-when-version="filled" hidden>The filled version is not exported for this program: '
                  f'{esc(filled["reason"])} The source version is shown.</p>')
    buttons = json_buttons([(f'Program JSON {source["schema"]} source', pid+'.source', source['descriptor'], source['reason']),
                            (f'Program JSON {filled["schema"] or source["schema"]} filled', pid+'.filled', filled['descriptor'], filled['reason'])], page)
    facts = [('Name', esc(record.get('name', pid))), ('Template', esc(record.get('template', folder.template))),
             ('Building type', esc(record.get('building_type', folder.building_type))), ('Mode', esc(mode)),
             ('Folder', f'<a href="{esc(page.rel(trail[-1][1]))}">{esc(folder.path)}</a>')]
    if site.zoning_of.get(pid):  # the LOD study used this program (ADR 0050)
        facts.append(('Zoning recommendations', ', '.join(f'<a href="{esc(page.rel(u))}">{esc(t)}</a>' for t, u in site.zoning_of[pid])))
    overview, keys = split(record, RECORD_OMIT+('name', 'id'))
    body = [crumbs(page, trail), header(page, pid, facts, site.release.number), buttons, VERSION_SWITCH, notice]
    toc = [('overview', 'Overview')]+[(k, title_of(k)) for k in keys]
    if schedules:
        toc.append(('schedules', 'Schedules'))
    if evidence_rows:
        toc.append(('evidence', 'Evidence'))
    body.append(contents(toc))
    body.append(section(page, 'overview', 'Overview', render_dict(overview, page)))
    for key in keys:
        value = record[key]
        rendered = render(value, page, RECORD_OMIT)
        if key == 'filling':
            rendered = f'<div class="ea-filling">{rendered}</div>'
        body.append(section(page, key, title_of(key), rendered))
    ids = {k: record[k] for k in RECORD_OMIT if record.get(k)}
    if ids:
        body.append(section(page, 'cited', 'Cited evidence', render_dict(ids, page)))
    if schedules:
        body.append(section(page, 'schedules', 'Schedules', ''.join(schedule(site.release.schedule(s), page, site.schedule_json.get(s)) for s in schedules)))
    if evidence_rows:
        body.append(section(page, 'evidence', 'Evidence', ''.join(evidence(site.release.evidence_row(e), page) for e in evidence_rows)))
    return markdown(record.get('name', pid), ''.join(body))


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


def construction_page(site, set_id, url, folder, record, contexts, used, trail):
    """One construction set: shared fields once, each context's own fields, the assemblies and materials it uses.

    `contexts` is [(key, facets, {'detailed': document, 'descriptors': [...]})]; `used` the
    library IDs its detailed documents reference.
    """
    page = Page(site.links, url)
    keys = [k for k, _, _ in contexts]
    documents = [c['document'] for _, _, c in contexts]
    shared, own = split_shared(documents)
    facts = [('Name', esc(record.get('name', set_id))), ('Template', esc(folder.template)), ('Building type', esc(folder.building_type)),
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
    blocks = []
    for (key, facets, _), fields in zip(contexts, own):
        attrs = ''.join(f' data-{a}="{esc(v)}"' for a, v in facets.items())
        inner = render_dict({f: v for f, v in fields.items() if f != 'components'}, page) if set(fields) - {'components'} else ''
        if 'components' in fields:
            inner += '<h4>Components</h4>'+components_table(fields['components'], page)
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


def folder_page(site, folder, url, programs, sets, schedules, evidence_rows, trail):
    """One template × building type: its programs and sets, and its mixes, services, systems and water."""
    page = Page(site.links, url)
    page.local.update(schedules)
    page.local.update(evidence_rows)
    link = lambda i, text: f'<a href="{esc(page.rel(site.links.pages[i]))}">{esc(text)}</a>'
    body = [crumbs(page, trail)]
    toc = []
    if programs:
        rows = [(link(pid, record.get('name', pid)), f'<code>{esc(pid)}</code>', esc(mode)) for pid, mode, record in programs]
        body.append(section(page, 'programs', 'Programs', listing(page, rows, ('Program', 'ID', 'Mode'))))
        toc.append(('programs', 'Programs'))
        mixes = [(pid, record) for pid, _, record in programs if record.get('composition')]
        if mixes:
            blocks = ''.join(f'<h3>{link(pid, record.get("name", pid))}</h3>{render(record["composition"], page)}' for pid, record in mixes)
            body.append(section(page, 'mixes', 'Mixes', blocks))
            toc.append(('mixes', 'Mixes'))
    if sets:
        rows = [(link(sid, record.get('name', sid)), f'<code>{esc(sid)}</code>', str(len(record.get('contexts', {})))) for sid, record in sets]
        body.append(section(page, 'constructions', 'Construction sets', listing(page, rows, ('Set', 'ID', 'Contexts'))))
        toc.append(('constructions', 'Construction sets'))
    for table in ('services', 'systems', 'components', 'water'):
        rows = folder.tables.get(table)
        if not rows:
            continue
        if table == 'water':
            blocks = ''.join(f'<h3>{esc(title_of(part))}</h3>'+''.join(
                f'<section class="ea-row"><h4><code>{esc(rid)}</code></h4>{render_dict(row, page)}</section>' for rid, row in values.items())
                for part, values in rows.items() if values)
        else:
            blocks = ''.join(f'<section class="ea-row"{page.claim(rid)}><h3>{esc(row.get("name") or rid)}</h3><p><code>{esc(rid)}</code></p>'
                             f'{render_dict({k: v for k, v in row.items() if k not in ("id", "name")}, page)}</section>' for rid, row in rows.items())
        body.append(section(page, table, title_of(table), blocks))
        toc.append((table, title_of(table)))
    if schedules:
        body.append(section(page, 'schedules', 'Schedules', ''.join(schedule(site.release.schedule(s), page, site.schedule_json.get(s)) for s in schedules)))
        toc.append(('schedules', 'Schedules'))
    if evidence_rows:
        body.append(section(page, 'evidence', 'Evidence', ''.join(evidence(site.release.evidence_row(e), page) for e in evidence_rows)))
        toc.append(('evidence', 'Evidence'))
    body.insert(1, contents(toc))
    return markdown(f'{folder.template} · {folder.building_type}', ''.join(body))


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
