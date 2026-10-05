"""Generate a static research catalogue from verified, immutable atlas releases."""
import argparse
import copy
from collections import defaultdict
import csv
import hashlib
import html
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
import time
import zipfile

from scripts.common import ROOT, load_atlas, load_json, stable_id, table_names
from scripts.catalogue_names import BUILDING_LABELS, building_label, program_label, program_title
from scripts.release import verify_release
from scripts.resolve import DEFAULT as RESOLUTION_RELEASE, validate_bundle
from scripts.water_equivalent import DEFAULT as WATER_RELEASE, validate_bundle as validate_water


def write_site_json(path,data):
    """Compact generated presentation packets; never rewrite frozen download files."""
    content=json.dumps(data,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n'
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(content,encoding='utf-8',newline='\n')


def presentation_scope(value, excluded_ids=()):
    """Remove excluded end-use fields from generated views; retain frozen evidence."""
    if isinstance(value,dict):
        return {k:presentation_scope(v,excluded_ids) for k,v in value.items()
                if not k.lower().replace('_',' ').replace('.',' ').startswith(('electric vehicle','in electric vehicle'))}
    if isinstance(value,list):
        return [presentation_scope(v,excluded_ids) for v in value
                if not isinstance(v,str) or v not in excluded_ids]
    return copy.deepcopy(value)


def completion_page(path):
    return 'commercial-completion/paths/'+stable_id('fixture_path',path['path_id'])+'.md'


def completion_links(packet, record_id):
    """A physical heater location does not establish a program beneficiary."""
    return {'release':'v'+packet['release_version'],
            'assigned_path_ids':[d['path_id'] for d in packet['draw_paths']
                                 if record_id in d['beneficiary_program_ids']],
            'missing_program_evidence':next((g for g in packet['missing_program_evidence']
                                            if g['program_id']==record_id),None),
            'download':'commercial-completion/v'+packet['release_version']+'/snapshot.zip'}


def generate_completion(root, packet, path, data, pilot=False):
    """Publish fixture components and both conserved curve representations."""
    version='v'+packet['release_version'];destination=root/'commercial-completion'/version
    destination.mkdir(parents=True)
    with zipfile.ZipFile(destination/'snapshot.zip','w',compression=zipfile.ZIP_STORED) as archive:
        for src in sorted(path.rglob('*'),key=lambda p:p.relative_to(path).as_posix()):
            if not src.is_file():continue
            name=src.relative_to(path).as_posix()
            info=zipfile.ZipInfo(name,date_time=(2026,10,4,0,0,0));info.create_system=3
            info.compress_type=zipfile.ZIP_STORED;info.external_attr=0o644<<16
            archive.writestr(info,src.read_bytes())
            if src.name in {'manifest.json','LICENSE'}:
                shutil.copyfile(src,destination/src.name)
    write_site_json(destination/'catalogue.json',packet)
    programs={r['id']:r for r in data['programs']}
    selected=[d for d in packet['draw_paths'] if not pilot or
              (d['building_type'],d['template'])==('MediumOffice','90.1-2013')]
    schedules={s['source_name']:s for s in packet['schedules']}
    for s in packet['schedules']:
        for key in ['source_schedule','equivalent_schedule']:
            row=s[key]
            write_site_json(root/f'releases/v0.2.0/records/{row["id"]}.json',{'record':row})
            current=f'releases/v0.2.0/schedules/{row["id"]}.md'
            page=page_header(row['source_name'],'v0.2.0',row['id'],False)
            page+='Commercial-completion '+version+' supplies this source-ordered schedule variant; base atlas tables remain unchanged.\n\n'
            page+=explorer_html(current,'v0.2.0',{'draw_variant':row['id']})+'\n\n'
            page+=display_value(row)+'\n\n'+anchor(current,'commercial-completion/index.md','Fixture catalogue and flow scaling')+'\n'
            write_text(root,current,page)
    index='# Commercial fixture-demand catalogue\n\n'
    index+='Source fixture components are attached to existing programs only when serving relationships are supported. Unallocated services remain building-level evidence. Apply each fixture once, with represented area and multiplier once.\n\n'
    index+=display_value(packet['summary'])+'\n\n'+anchor('commercial-completion/index.md',f'commercial-completion/{version}/snapshot.zip','Complete canonical bundle, schema, provenance and notices')+' · '+anchor('commercial-completion/index.md',f'commercial-completion/{version}/manifest.json','Manifest and checksums')+'\n\n'
    index+='<div class="atlas-table"><table><thead><tr><th>Building</th><th>Template</th><th>Fixture path</th><th>Allocation</th><th>Programs</th></tr></thead><tbody>'
    for d in selected:
        current=completion_page(d);s=schedules[d['source_schedule_name']]
        beneficiaries=[]
        for record_id in d['beneficiary_program_ids']:
            if record_id in programs:
                r=programs[record_id]
                beneficiaries.append(anchor(current,f'releases/v0.2.0/programs/{record_id}.md',r['program']))
        page=page_header(friendly(d['building_type'])+' / '+d['end_use']+' · '+d['template'],version,d['path_id'],False)
        page+='Source fixture path; not a new program. Allocation status: **'+display_value(d['allocation_status'])+'**.\n\n'
        page+='Serving programs: '+(' · '.join(beneficiaries) or 'Unknown; not assigned to a program')+'.\n\n'
        page+=explorer_html(current,'v0.2.0',{'source_fixture_draw':s['source_schedule']['id'],
                                             'conserved_peak_normalized_draw':s['equivalent_schedule']['id']})+'\n\n'
        page+='## Flow scaling and source conditions\n\n'+display_value(d)+'\n\n'
        page+='The normalized fraction is source fraction divided by its peak '+str(s['peak_divisor'])+'. Its compatible rated flow is original rated flow multiplied by that peak; both representations preserve draw at every interval. An always-zero source retains zero.\n\n'
        page+='Fixture draw is distinct from heater energy and circulation. A booster heat exchanger does not create an additional copy of the main fixture draw. Unallocated laundry/booster services block unsupported program zeros.\n\n'
        page+='## Evidence\n\n'
        for evidence_id in d['evidence_ids']:
            proof=packet['evidence'][evidence_id]
            page+='<details><summary>'+display_value(proof['source_locator'])+'</summary>'+display_value(proof)+'</details>\n'
        page+='\n'+anchor(current,'commercial-completion/index.md','Fixture-demand catalogue')+' · '+anchor(current,f'commercial-completion/{version}/snapshot.zip','Canonical packet with complete evidence')+'\n'
        write_text(root,current,page)
        index+='<tr>'+''.join('<td>'+v+'</td>' for v in [display_value(friendly(d['building_type'])),display_value(d['template']),anchor('commercial-completion/index.md',current,d['path_id']),display_value(d['allocation_status']),display_value(d['beneficiary_program_ids'])])+'</tr>'
    write_text(root,'commercial-completion/index.md',index+'</tbody></table></div>\n')


def shared_profile_downloads(bundle,history):
    """Preserve direct v0.1/v0.2 URLs and stable aliases for subsequent snapshots."""
    version=lambda p:tuple(map(int,p.name[1:].split('.')))
    if version(bundle)<(0,3,0):
        return {}
    downloads={}
    older=sorted((p for p in history if version(p)<version(bundle)),key=version)
    for p in load_json(bundle/'profile-index.json'):
        for field,hash_field in [('profile_file','profile_sha256'),('csv_file','csv_sha256')]:
            name=p[field]
            for previous in older:
                candidate=previous/'profiles'/name
                if candidate.is_file() and hashlib.sha256(candidate.read_bytes()).hexdigest()==p[hash_field]:
                    downloads[name]='resolution-supplements/'+previous.name+'/profiles/'+name
                    break
    return downloads

RECORD_TABLES = [t for t in table_names('0.2.0') if t not in {'provenance', 'source_files'}]
AXES = {'building': 'Building type', 'program': 'Program', 'template': 'Vintage / template',
        'climate': 'Climate context', 'system': 'System', 'source': 'Source / family',
        'status': 'Data status', 'kind': 'Record kind', 'stock_vintage': 'Residential stock vintage'}
FAMILIES = {'code_prototype_rules': 'Code / prototype rules (Standards-derived)',
            'existing_stock_benchmark_rules': 'Existing-stock benchmark rules (Standards-derived)',
            'existing_stock_benchmark': 'Existing-stock benchmark rules (Standards-derived)',
            'existing_stock_source_fixture': 'Existing-stock source fixture (ResStock)'}
PROJECT_LABELS = {'openstudio-standards': 'OpenStudio Standards', 'resstock': 'ResStock', 'ComStock': 'ComStock'}
LABELS = BUILDING_LABELS


def friendly(value):
    return LABELS.get(value, re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', value).replace('_', ' '))


def display_value(value):
    """Escape all source strings; retain null distinctly from numerical zero."""
    if value is None:
        return 'Unknown / not reported'
    if isinstance(value, (dict, list)):
        return '<pre>' + html.escape(json.dumps(value, indent=2, ensure_ascii=False)) + '</pre>'
    if isinstance(value, bool):
        return 'Yes' if value else 'No'
    return html.escape(str(value), quote=True).replace('|', '&#124;')


def read_release(path):
    path = Path(path)
    errors = verify_release(path)
    if errors:
        raise ValueError('Release integrity / validation failure: ' + '; '.join(errors[:8]))
    manifest = load_json(path/'manifest.json')
    version = 'v' + manifest['release_version']
    if not re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+', version):
        raise ValueError('Unsupported release version')
    return load_atlas(path), manifest, version


def title(table, row):
    if table == 'buildings':
        return friendly(row['building_type']) + ' · ' + row['template']
    if table == 'programs':
        return building_label(row['building_type']) + ' / ' + program_title(row) + ' · ' + row['template']
    if table == 'schedules':
        return row['source_name']
    if table == 'residential_archetypes':
        return friendly(row['building_type']) + ' · ' + row['variant']
    if table == 'envelope_components':
        return ' / '.join(row[k] for k in ['surface_type', 'construction_type', 'building_category', 'climate_zone_set', 'template'])
    if table == 'systems':
        return friendly(row['building_type']) + ' / ' + row['system_type'] + ' · ' + row['template']
    if table in {'commercial_options', 'residential_options'}:
        return row['parameter'] + ' / ' + row['option']
    if table == 'efficiency_rules':
        return row['equipment_table'] + ' · ' + row['template'] + ' · ' + row['id'][-6:]
    if table == 'specialized_rules':
        return row['rule_type'] + ' · ' + row['template'] + ' · ' + row['id'][-6:]
    return friendly(row.get('building_type', table)) + ' · ' + row['id']


def overview_rows(data):
    groups = sorted({(r['building_type'], r['template']) for r in data['programs']})
    return [{'id': stable_id('building', b, t), 'building_type': b, 'template': t,
             'source_family': next(r['source_family'] for r in data['programs']
                                   if r['building_type'] == b and r['template'] == t)}
            for b, t in groups]


def catalogue_entries(data, version):
    """Index only source-defined records; never expand programs across climates."""
    entries = []
    tables = {'buildings': overview_rows(data), **{t: data.get(t, []) for t in RECORD_TABLES}}
    prov = {r['id']: r for r in data['provenance']}
    sources = {r['id']: r for r in data['source_files']}
    programs = {r['id']: r for r in data['programs']}
    systems = {r['id']: r for r in data['systems']}
    uses = defaultdict(lambda: {'building': set(), 'template': set(), 'contexts': set()})
    for t in ['programs', 'systems']:
        for r in data[t]:
            for k, v in r.items():
                if k.endswith('_schedule_id') and v:
                    uses[v]['building'].add(r['building_type'])
                    uses[v]['template'].add(r['template'])
                    uses[v]['contexts'].add((r['building_type'], r['template']))
    for t, rows in tables.items():
        for r in rows:
            if t in {'residential_options','commercial_options'} and r.get('parameter','').startswith('Electric Vehicle'):
                continue
            context = r.get('source_context', {})
            src = sources.get(prov.get(r.get('provenance_id'), {}).get('source_file_id'), {})
            family = r.get('source_family')
            if not family and r.get('template') and t not in {'residential_archetypes'}:
                family = 'existing_stock_benchmark_rules' if r['template'].startswith('DOE Ref') else 'code_prototype_rules'
            # Keep legacy browsing labels as aliases; canonical research records are unchanged.
            project = src.get('project', 'openstudio-standards' if t == 'buildings' else 'Unknown source')
            original_source = project
            original_family = r.get('source_family') or family
            if original_family:
                old_family = ('existing_stock_benchmark' if original_family == 'existing_stock_benchmark'
                              else FAMILIES.get(original_family, original_family))
                original_source += ' · ' + old_family
            source = PROJECT_LABELS.get(project, project) + (' · ' + FAMILIES.get(family, family) if family else '')
            if t == 'envelope_components':
                climate, basis = r['climate_zone_set'], 'Conditional envelope applicability'
            elif context.get('ASHRAE IECC Climate Zone 2004'):
                climate = context['ASHRAE IECC Climate Zone 2004']
                basis = 'Reported residential source context'
            else:
                climate = 'Unspecified; program is climate-independent' if t == 'programs' else 'Unspecified'
                basis = 'No climate-specific assignment'
            original_climate = climate
            climate_match = re.fullmatch(r'Climate\s*Zone\s+([0-8](?:[ABC])?)', climate, re.IGNORECASE)
            if climate_match:
                climate = climate_match[1].upper()
            elif t == 'programs':
                climate = 'Climate-independent'
            facet_aliases = {k: [old] for k, old, new in
                             [('climate', original_climate, climate), ('source', original_source, source)] if old != new}
            original_building = r.get('building_type', 'Shared / not assigned')
            building = building_label(original_building)
            original_program = programs[r['program_id']]['program'] if t == 'mappings' else r.get('program', 'Not applicable')
            program = program_label(original_program)
            for key, old, new in [('building', original_building, building), ('program', original_program, program)]:
                if old != new:
                    facet_aliases[key] = [old]
            # Shared schedules use exactly the same browsing vocabulary as their
            # parent programs/systems; paired contexts remain paired.
            referenced_buildings = sorted({building_label(b) for b in uses[r['id']]['building']})
            previous_title = (friendly(r['building_type']) + ' / ' + r['program'] + ' · ' + r['template']) if t == 'programs' else title(t, r)
            status = ('Source-input bundle; assembly unresolved' if t == 'buildings' else
                      'Source fixture; runtime gaps' if t == 'residential_archetypes' else
                      'Conditional / unassigned' if t in {'efficiency_rules', 'envelope_components', 'specialized_rules'} else
                      'Option arguments; configuration required' if t.endswith('_options') else
                      'Source rules; calendar required' if t == 'schedules' else 'Source inputs; missing fields explicit')
            entries.append({
                'id': r['id'], 'kind': t, 'name': title(t, r),
                'building': building,
                'program': program,
                'template': r.get('template', 'Shared / not assigned'),
                'stock_vintage': context.get('Vintage', 'Not applicable / not reported'),
                'climate': climate, 'climate_basis': basis,
                'system': (systems[r['system_id']]['system_type'] if r.get('system_id') else 'Unassigned / not reported')
                          if t == 'mappings' else r.get('system_type', 'Not applicable'),
                'source': source, 'status': status,
                'facet_aliases': facet_aliases,
                'search_aliases': [original_building, original_program, previous_title, *sorted(uses[r['id']]['building'])],
                'referenced_buildings': referenced_buildings,
                'referenced_templates': sorted(uses[r['id']]['template']),
                'referenced_contexts': [{'building': building_label(b), 'template': t}
                                        for b, t in sorted(uses[r['id']]['contexts'])],
                'path': f'releases/{version}/{t}/{r["id"]}.md',
                'download': f'releases/{version}/records/{r["id"]}.json',
            })
    return sorted(entries, key=lambda r: (r['kind'], r['name'], r['id']))


def html_url(current, destination):
    """Raw HTML URLs are relative to the final directory URL, not Markdown."""
    cur = PurePosixPath(current)
    base = cur.parent if cur.name == 'index.md' else cur.with_suffix('')
    dst = PurePosixPath(destination)
    if dst.suffix == '.md':
        dst = dst.parent if dst.name == 'index.md' else dst.with_suffix('')
        suffix = '/'
    else:
        suffix = ''
    return os.path.relpath(str(dst), str(base)).replace('\\', '/') + suffix


def anchor(current, destination, label):
    return '<a href="' + html.escape(html_url(current, destination), quote=True) + '">' + display_value(label) + '</a>'


def render_fields(row, units, refs, current='index.md'):
    rows = []
    for k, v in row.items():
        if k in {'id', 'provenance_id'}:
            continue
        if isinstance(v, str) and v in refs:
            val = anchor(current, refs[v]['path'], refs[v]['name'])
        elif isinstance(v, list) and v and all(isinstance(x, str) and x in refs for x in v):
            val = '<ul>' + ''.join('<li>' + anchor(current, refs[x]['path'], refs[x]['name']) + '</li>' for x in v) + '</ul>'
        else:
            val = display_value(v)
        unit = units.get(k, 'C' if k.endswith('_base_C') else 'person' if k == 'occupants' else
                         'm2' if k == 'conditioned_floor_area_m2' else '—')
        rows.append(f'<tr id="field-{k}"><th scope="row">{display_value(friendly(k))}<br><code>{k}</code></th>'
                    f'<td>{val}</td><td>{display_value(unit)}</td>'
                    f'<td><a href="#evidence-{k}">Evidence</a></td></tr>')
    return '<div class="atlas-table"><table><thead><tr><th>Field</th><th>Value</th><th>Unit / basis</th><th>Trace</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>'


def provenance_html(prov, source, current, version):
    out = ['## Provenance', '<div class="atlas-evidence">',
           '<p><strong>Source locator:</strong> ' + display_value(prov['locator']) + '</p>',
           '<p><strong>Extraction date:</strong> ' + display_value(prov['extraction_date']) + '</p>',
           '<p><strong>Interpretation:</strong> ' + display_value(prov['notes']) + '</p>',
           '<p><strong>Source revision:</strong> <code>' + display_value(source['version']) + '</code></p>',
           '<p><strong>Source file:</strong> <a href="' + html.escape(source['url'], quote=True) + '">' +
           display_value(source['project'] + '/' + source['path']) + '</a></p>',
           '<p><strong>SHA-256:</strong> <code>' + source['sha256'] + '</code></p>',
           '<p>' + anchor(current, f'releases/{version}/downloads/{source["license_path"]}', 'Upstream license notice') + '</p>']
    for key, field in prov['fields'].items():
        out += [f'<details id="evidence-{key}"><summary>{display_value(friendly(key))} · {display_value(field["status"])}</summary>',
                '<dl><dt>Original field</dt><dd>' + display_value(field['original_field']) + '</dd>',
                '<dt>Original unit</dt><dd>' + display_value(field['original_units']) + '</dd>',
                '<dt>Original value</dt><dd>' + display_value(field['original_value']) + '</dd>',
                '<dt>Transformation</dt><dd>' + display_value(field['transformation']) + '</dd></dl></details>']
    return '\n'.join(out + ['</div>'])


def table_html(rows, current, columns=('name', 'template', 'climate', 'status')):
    head = ''.join('<th scope="col">' + display_value(friendly(c)) + '</th>' for c in columns)
    body = []
    for r in rows:
        body.append('<tr>' + ''.join('<td>' + (anchor(current, r['path'], r[c]) if c == 'name' else display_value(r[c])) + '</td>' for c in columns) + '</tr>')
    return '<div class="atlas-table"><table><thead><tr>' + head + '</tr></thead><tbody>' + ''.join(body) + '</tbody></table></div>'


def page_header(name, version, identity, searchable=True):
    fm = '' if searchable else 'search:\n  exclude: true\n'
    # JSON scalar quoting is valid YAML and safely handles punctuation.
    return f'---\ntitle: {json.dumps(name, ensure_ascii=False)}\n{fm}---\n\n# {html.escape(name)}\n\n' + (
        f'<div class="atlas-meta"><span>Release {version}</span><span>Schema {version[1:]}</span>'
        f'<code>{html.escape(identity)}</code></div>\n\n')


def explorer_html(current, version, ids):
    path = html_url(current, f'releases/{version}/records/')
    return ('<section class="atlas-explorer" data-records-base="' + html.escape(path, quote=True) +
            '" data-schedule-ids="' + html.escape(json.dumps(ids), quote=True) + '">'
            '<h2>Schedule explorer</h2><p>Source-faithful daily inspection. Select a concrete day and month/day; '
            'the final matching specific rule wins, with default fallback. This is not an annual calendar.</p>'
            '<div class="atlas-controls"><label>Day type<select class="atlas-day">'
            + ''.join(f'<option value="{v}">{label}</option>' for v, label in
                      [('Mon', 'Monday'), ('Tue', 'Tuesday'), ('Wed', 'Wednesday'), ('Thu', 'Thursday'),
                       ('Fri', 'Friday'), ('Sat', 'Saturday'), ('Sun', 'Sunday'), ('Hol', 'Holiday'),
                       ('WntrDsn', 'Winter design day'), ('SmrDsn', 'Summer design day')]) +
            '</select></label><label>Month / day<input class="atlas-date" type="date" value="2000-01-15" min="2000-01-01" max="2000-12-31"></label>'
            '<button type="button" class="atlas-csv">Export selected profiles CSV</button></div>'
            '<div class="atlas-chart-status" role="status" aria-live="polite">Loading schedule records…</div>'
            '<div class="atlas-charts"></div><details open><summary>Selected profiles and matching source rules</summary>'
            '<div class="atlas-profile-table"></div></details>'
            '<p class="atlas-note">DummySmrDsn retains its source label and matches summer design days, following the pinned generator. '
            'Units remain separate; unavailable profiles are never filled with zero.</p>'
            '<noscript>Interactive plots require JavaScript. Source rule tables and JSON downloads remain available below.</noscript></section>')


def pilot_data(data):
    """Select a closed representative subset, including actual referenced schedules."""
    result = dict(data)
    result['programs'] = [r for r in data['programs'] if r['building_type'] == 'MediumOffice' and r['template'] == '90.1-2013']
    result['systems'] = [r for r in data['systems'] if r['building_type'] == 'MediumOffice' and r['template'] == '90.1-2013']
    result['mappings'] = [r for r in data['mappings'] if r['building_type'] == 'MediumOffice' and r['template'] == '90.1-2013']
    result['residential_archetypes'] = data.get('residential_archetypes', [])[:1]
    options = {v for r in result['residential_archetypes'] for v in r['option_ids']}
    result['residential_options'] = [r for r in data['residential_options'] if r['id'] in options]
    result['commercial_options'] = []
    for t in ['envelope_components', 'efficiency_rules', 'specialized_rules']:
        result[t] = [r for r in data.get(t, []) if r['template'] == '90.1-2013'][:1]
    ids = {v for t in ['programs', 'systems'] for r in result[t]
           for k, v in r.items() if k.endswith('_schedule_id') and v}
    result['schedules'] = [r for r in data['schedules'] if r['id'] in ids]
    return result


def write_text(root, path, text):
    p = root/path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text.rstrip() + '\n', encoding='utf-8', newline='\n')


def axis_path(version, axis, value):
    return f'releases/{version}/axes/{axis}/{stable_id("category", axis, value)}.md'


def catalogue_page(entries, version, versions):
    current = f'releases/{version}/catalogue.md'
    base = page_header('Catalogue', version, 'catalogue')
    base += ('<p class="atlas-intro">Find source-defined energy inputs. Browse the same records by different axes; '
             'inspect applicability and unresolved inputs before reuse.</p>\n\n')
    base += '<div class="atlas-version-links">' + ' · '.join(
        anchor(current, f'releases/{v}/catalogue.md', v) for v in versions) + '</div>\n\n'
    base += ('<section id="atlas-catalogue" data-index="' + html_url(current, f'releases/{version}/catalogue.json') + '">'
             '<h2>Find an entry</h2><div class="atlas-controls">'
             '<label class="atlas-search-label">Search<input id="atlas-query" type="search" placeholder="Building, program, ID, source…"></label>')
    for k in ['kind', 'building', 'program', 'template', 'stock_vintage', 'climate', 'system', 'source', 'status']:
        base += f'<label>{AXES[k]}<select id="atlas-filter-{k}"><option value="">All</option></select></label>'
    base += ('<button type="button" id="atlas-reset">Reset filters</button></div>'
             '<p id="atlas-results-count" role="status" aria-live="polite">Use the linked tables below, or enable JavaScript for filtering.</p>'
             '<div id="atlas-results"></div><div class="atlas-pagination"><button id="atlas-prev" type="button">Previous</button>'
             '<span id="atlas-page"></span><button id="atlas-next" type="button">Next</button></div></section>\n\n')
    base += '## Building and residential entries\n\n' + table_html(
        [r for r in entries if r['kind'] in {'buildings', 'residential_archetypes'}], current)
    for axis, label in AXES.items():
        groups = defaultdict(list)
        for r in entries:
            groups[r[axis]].append(r)
        base += f'\n\n## Browse by {label.lower()}\n\n'
        base += '<div class="atlas-table"><table><thead><tr><th>Category</th><th>Entries</th></tr></thead><tbody>'
        for value, group in sorted(groups.items()):
            base += '<tr><td>' + anchor(current, axis_path(version, axis, value), friendly(value)) + '</td><td>' + str(len(group)) + '</td></tr>'
        base += '</tbody></table></div>\n'
    return base


def resolution_html(current, rows, profile, supplement_base):
    page='## Resolution supplement '+supplement_base.split('/')[-1]+'\n\nSource values below are unchanged. These separately labelled resolutions require an explicit consumer choice.\n\n'
    page+='<div class="atlas-table"><table><thead><tr><th>Field</th><th>Original</th><th>Resolved</th><th>Unit</th><th>Basis / rule</th></tr></thead><tbody>'
    for row in rows:
        page+='<tr>'+''.join('<td>'+display_value(v)+'</td>' for v in [row['field'],row['original_value'],row['resolved_value'],row['unit'],row['basis']+' / '+row['rule']])+'</tr>'
    page+='</tbody></table></div>\n\n'
    for row in rows:
        page+='<details><summary>'+display_value(row['field']+' — '+row['note'])+'</summary>'+display_value(row['evidence'])+'</details>\n'
    fixed=[r['resolved_value']['fixed_schedule_id'] for r in rows if r['rule']=='fixed_background_default']
    if fixed:
        page+='\n\n### Fixed source default profiles\n\nUser-selected refrigeration and dwelling exterior-lighting shapes with no temperature feedback. Selected end-use presence is checked; magnitudes and shared/common-area loads remain separate.\n\n'
        page+='<section class="atlas-residential-profile" data-fixed="true" data-columns="'+','.join(fixed)+'" data-profile="'+html_url(current,supplement_base+'/fixed-background-annual.json')+'">'
        page+='<div class="atlas-controls"><label>View <select class="atlas-res-view"><option value="day">Selected day</option><option value="annual">Annual</option></select></label>'
        page+='<label>Calendar date <input class="atlas-res-date" type="date" min="2007-01-01" max="2007-12-31" value="2007-01-01"></label>'
        page+='<label>Series <select class="atlas-res-columns" multiple size="2"></select></label></div>'
        page+='<p class="atlas-res-status" role="status">Loading fixed profiles.</p><div class="atlas-res-charts"></div><div class="atlas-res-table"></div></section>\n\n'
        page+=anchor(current,supplement_base+'/fixed-background-schedules.json','Canonical fixed tables and field provenance')+'\n\n'
    if profile:
        packet=load_json(profile['source_path']); meta=packet['metadata']
        page+='\n\n### Executed residential profiles\n\n**Station-proxy variant; nominal thermostat profiles. Complete simulation readiness remains unresolved.**\n\n'
        page+=display_value(meta['profile_boundary'])+'\n\n'
        page+=f'Calendar {meta["year"]}; {meta["timestep_minutes"]}-minute intervals; seed {meta["seed"]}; '+display_value(meta['status'])+'.\n\n'
        page+=display_value(meta['interval_convention'])+'\n\n'
        page+='Weather: '+display_value(meta['weather']['station_filename'])+'; '+display_value(meta['weather']['variant'])+'.\n\n'
        page+='Current release scope excludes sampled HVAC equipment-unavailability overlays. These desired-temperature profiles remain nominal. Archived source options and historical execution notes are retained in the download.\n\n'
        page+='<section class="atlas-residential-profile" data-profile="'+html_url(current,profile['download'])+'">'
        page+='<div class="atlas-controls"><label>View <select class="atlas-res-view"><option value="day">Selected day</option><option value="annual">Annual</option></select></label>'
        page+='<label>Calendar date <input class="atlas-res-date" type="date" min="2007-01-01" max="2007-12-31" value="2007-01-01"></label>'
        page+='<label>Series <select class="atlas-res-columns" multiple size="5"></select></label></div>'
        page+='<p class="atlas-res-status" role="status" aria-live="polite">Loading executed profiles; exact data available in downloads.</p><div class="atlas-res-charts"></div><div class="atlas-res-table"></div></section>\n\n'
        page+=anchor(current,profile['download'],'Annual canonical JSON with execution provenance')+' · '+anchor(current,profile['csv_download'],'Upstream execution CSV')+'\n\n'
        page+='The original execution packet retains historical runner notes. Current fixed defaults and reviewed zeros are supplied by this separately versioned overlay; complete load magnitudes remain downstream.\n\n'
    page+=anchor(current,supplement_base+'/snapshot.zip','Complete supplement, schema, provenance, locks and upstream notices')+'\n\n'
    return page


def generate_release(root, release_path, data, manifest, version, versions, pilot=False, supplement=None, water=None, completion=None, water_reporting=None):
    entries = catalogue_entries(data, version)
    resolution_rows=defaultdict(list)
    profile_index={}
    supplement_base='resolution-supplements/'+supplement['version'] if supplement else ''
    if supplement:
        for r in supplement['data']['resolutions']:
            resolution_rows[r['record_id']].append(r)
        for p in supplement['index']:
            downloads=supplement.get('profile_downloads',{})
            profile_index[p['record_id']]={**p,'download':downloads.get(p['profile_file'],supplement_base+'/profiles/'+p['profile_file']),
                'csv_download':downloads.get(p['csv_file'],supplement_base+'/profiles/'+p['csv_file']),
                'source_path':supplement['path']/'profiles'/p['profile_file']}
        for entry in entries:
            if entry['id'] in profile_index:
                entry['status']='Executed profile supplement; model gaps remain'
            elif entry['id'] in resolution_rows:
                entry['status']='Selective resolution supplement; source nulls retained'
    refs = {r['id']: r for r in entries}
    rows = {r['id']: (t, r) for t in RECORD_TABLES for r in data.get(t, [])}
    rows.update({r['id']: ('buildings', r) for r in overview_rows(data)})
    reporting_programs={p['program_id']:p for p in water_reporting['programs']} if water_reporting else {}
    prov = {r['id']: r for r in data['provenance']}
    sources = {r['id']: r for r in data['source_files']}
    excluded_ids={r['id'] for t in ['commercial_options','residential_options'] for r in data.get(t,[])
                  if r.get('parameter','').startswith('Electric Vehicle')}
    # Retain historical public addresses as non-indexed archive pointers, while
    # removing excluded options from active catalogue and parameter presentation.
    for record_id in sorted(excluded_ids):
        table,_=rows[record_id]
        current=f'releases/{version}/{table}/{record_id}.md'
        page=page_header('Archived out-of-scope option',version,record_id,False)
        page+='This source option is outside the active schedule catalogue. Its original evidence remains in the immutable frozen snapshot.\n\n'
        page+=anchor(current,f'releases/{version}/downloads/snapshot.zip','Original complete source snapshot')+'\n'
        write_text(root,current,page)
        write_site_json(root/f'releases/{version}/records/{record_id}.json',
                        {'release':version,'record_kind':'archived_out_of_scope_option','id':record_id,
                         'snapshot':f'releases/{version}/downloads/snapshot.zip'})
    write_site_json(root/f'releases/{version}/catalogue.json', {'release': version, 'pilot': pilot, 'entries': entries})
    write_site_json(root/f'releases/{version}/schedule-index.json', [
        {'id': r['id'], 'name': r['source_name'], 'units': r['units']} for r in data['schedules']])
    write_text(root, f'releases/{version}/catalogue.md', catalogue_page(entries, version, versions))
    for axis, label in AXES.items():
        groups = defaultdict(list)
        for r in entries:
            groups[r[axis]].append(r)
        for value, group in sorted(groups.items()):
            current = axis_path(version, axis, value)
            note = ('Climate grouping aligns equivalent label spellings. Envelope sets are conditional rules; residential climates are reported fixture context. '
                    'Thermal-only and moisture-specific sets are not silently merged.') if axis == 'climate' else (
                    'Stock vintage and code/prototype editions have different meanings. Historical code rules are not calibrated existing stock.') if axis == 'template' else (
                    'These entries share a browsing label; compatibility and unresolved dependencies remain on each detail page.')
            write_text(root, current, page_header(label + ': ' + friendly(value), version, 'category', False) +
                       note + '\n\n' + table_html(group, current, ('name', 'kind', 'template', 'climate_basis', 'status')))
        aliases = defaultdict(set)
        for r in entries:
            for old in r.get('facet_aliases', {}).get(axis, []):
                aliases[old].add(r[axis])
        for old, values in sorted(aliases.items()):
            if old in groups or len(values) != 1:
                continue
            current = axis_path(version, axis, old)
            value = next(iter(values))
            write_text(root, current, page_header(label + ': ' + friendly(old), version, 'category-alias', False) +
                       'This browsing label is now aligned with ' + anchor(current, axis_path(version, axis, value), value) +
                       '. Original source fields remain unchanged.\n')
    for entry in entries:
        t, r = rows[entry['id']]
        r=presentation_scope(r,excluded_ids)
        current = entry['path']
        page = page_header(entry['name'], version, r['id'], t in {'buildings', 'programs', 'residential_archetypes', 'schedules'})
        page += '<p class="atlas-status">' + display_value(entry['status']) + '</p>\n\n'
        page += '## Applicability\n\n' + display_value(entry['source']) + ' · ' + display_value(entry['climate']) + '\n\n'
        page += display_value(entry['climate_basis']) + '. No complete simulation model is implied.\n\n'
        page += anchor(current, f'releases/{version}/catalogue.md', 'Back to catalogue') + '\n\n'
        if t == 'buildings':
            matched = [e for e in entries if e['kind'] in {'programs', 'systems', 'mappings'}
                       and e['building'] == building_label(r['building_type']) and e['template'] == r['template']]
            page += ('## Assembly status\n\nSource-input overview. Area fractions, conditioned state, infiltration, '
                     'HVAC sizing and generator overrides require downstream resolution.\n\n')
            for kind in ['programs', 'systems', 'mappings']:
                page += '## ' + friendly(kind) + '\n\n' + table_html([e for e in matched if e['kind'] == kind], current)
            for kind in ['envelope_components', 'efficiency_rules', 'specialized_rules']:
                e = next((e for e in entries if e['kind'] == kind and e['template'] == r['template']), None)
                if e:
                    dest = axis_path(version, 'template', r['template'])
                    page += '\n\n' + anchor(current, dest, 'Inspect ' + friendly(kind) + ' by template; choose predicates before assignment')
            packet = {'release': version, 'record_kind': t, 'record': r,
                      'related_record_ids': [e['id'] for e in matched],
                      'interpretation': 'Generated overview of source inputs; not a complete simulation configuration'}
        else:
            ids = {k: v for k, v in r.items() if k.endswith('_schedule_id') and v in refs}
            if water and r['id'] == water['program_id']:
                ids['fixture_draw_equivalent_peak_normalized'] = water['equivalent_schedule']['id']
            if r['id'] in reporting_programs:
                ids['attributed_hot_water_reporting']=reporting_programs[r['id']]['reporting_schedule_id']
            if t == 'schedules':
                ids = {'source_profile': r['id']}
            if ids:
                page += '\n\n' + explorer_html(current, version, ids) + '\n\n'
            if t == 'residential_archetypes':
                page += ('## Profiles unavailable in the frozen source snapshot\n\nThermostat bases are reported inputs before offsets, seasons and overrides. '
                         'Effective daily and annual profiles require generator execution and an explicit calendar. '
                         'No commercial apartment profiles have been substituted.\n\n')
            page += '## Parameters and source conditions\n\n' + render_fields(r, data['units'], refs, current) + '\n\n'
            p = presentation_scope(prov[r['provenance_id']],excluded_ids)
            s = sources[p['source_file_id']]
            page += provenance_html(p, s, current, version) + '\n\n'
            packet = {'release': version, 'record_kind': t, 'record': r, 'provenance': p, 'source_file': s}
        if water and r['id'] == water['program_id']:
            page += '\n\n## Fixture draw equivalent\n\n'
            page += 'Optional source-conserving variant attached to this existing office program. No new restroom program is created. The schedule explorer includes both the original draw fractions and the peak-normalized equivalent.\n\n'
            page += 'The source maximum is 0.57. Divide its fractions by 0.57 and multiply its rated flow by 0.57 to preserve demand. Apply once per represented office area; never add another building-wide copy. This is fixture draw at the source target temperature, not heater energy or circulation.\n\n'
            page += display_value(water['interpretation'])+'\n\n'
            page += anchor(current,'water-equivalents/v0.1.0/water-equivalent.json','Canonical equivalent, SI scaling and field evidence')+' · '+anchor(current,'guides/hot-water.md','Allocation and conservation method')+'\n\n'
            packet['water_equivalent'] = water
        if completion and t in {'programs','buildings'}:
            attached=[d for d in completion['draw_paths'] if
                      (r['id'] in d['beneficiary_program_ids'] if t=='programs' else
                       (r['building_type'],r['template'])==(d['building_type'],d['template']))]
            links=completion_links(completion,r['id'])
            if attached or links['missing_program_evidence']:
                page+='\n\n## Complete source water-demand paths\n\n'
                page+='Conserved fixture components use existing programs where source serving relationships are explicit. Shared services remain unallocated; no new restroom program is created.\n\n'
                for draw in attached:
                    page+=anchor(current,completion_page(draw),draw['end_use']+' / '+draw['source_schedule_name'])+' · '+display_value(draw['allocation_status'])+'\n\n'
                if links['missing_program_evidence']:
                    page+=display_value(links['missing_program_evidence'])+'\n\n'
                page+=anchor(current,'commercial-completion/index.md','Commercial fixture-demand catalogue')+'\n\n'
                packet['commercial_completion']=links
        if r['id'] in reporting_programs:
            from scripts.site_water_reporting import program_html
            report_row=reporting_programs[r['id']]
            page+='\n\n'+program_html(current,report_row,water_reporting)
            packet['water_reporting']={'version':'v'+water_reporting['release_version'],
                                      'record':report_row,
                                      'download':'water-reporting/v'+water_reporting['release_version']+'/water-reporting.json'}
        if r['id'] in resolution_rows:
            profile=profile_index.get(r['id'])
            page+='\n\n'+resolution_html(current,presentation_scope(resolution_rows[r['id']],excluded_ids),profile,supplement_base)
            packet['resolution_supplement']={'version':supplement['version'],'base_manifest_sha256':supplement['base_hash'],
                'resolutions':presentation_scope(resolution_rows[r['id']],excluded_ids)}
            if profile:
                packet['resolution_supplement']['profile']={k:v for k,v in profile.items() if k!='source_path'}
        page += '## Download and cite\n\n' + anchor(current, entry['download'], 'Record JSON with provenance') + '\n\n'
        page += anchor(current, f'releases/{version}/downloads/manifest.json', 'Frozen release manifest and checksums') + '\n\n'
        page += '<pre>' + display_value(f'Energy Archetype Atlas {version}; {t}/{r["id"]}; schema {data["schema_version"]}. '
                                             'See field provenance for upstream attribution and licensing.') + '</pre>\n'
        write_text(root, current, page)
        write_site_json(root/entry['download'], packet)
    # MkDocs renders .md files instead of copying them verbatim. Preserve the
    # exact frozen tree in a deterministic archive, plus direct non-Markdown files.
    downloads_root = root/f'releases/{version}/downloads'
    downloads_root.mkdir(parents=True)
    with zipfile.ZipFile(downloads_root/'snapshot.zip', 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for src in sorted(release_path.rglob('*')):
            if not src.is_file():
                continue
            relative = src.relative_to(release_path).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(2026, 10, 2, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, src.read_bytes())
            if src.suffix != '.md':
                dst = downloads_root/relative
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
    downloads = f'releases/{version}/downloads.md'
    page = page_header('Downloads and release identity', version, 'downloads')
    page += ('The JSON snapshot is canonical. CSV files are generated inspection exports; nested values remain JSON text. '
             'Original work is unlicensed. Upstream source terms and notices apply.\n\n')
    for t in table_names(data['schema_version']):
        # CSV is generated from the full release even when the presentation is a pilot.
        canonical = load_json(release_path/(t+'.json'))
        keys = sorted({k for r in canonical for k in r})
        stream = io.StringIO(newline='')
        writer = csv.DictWriter(stream, fieldnames=keys, lineterminator='\n')
        writer.writeheader()
        for row in canonical:
            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else
                             'null' if v is None else v for k, v in row.items()})
        write_text(root, f'releases/{version}/downloads/{t}.csv', stream.getvalue())
        page += '<p>' + display_value(t) + ': ' + anchor(downloads, f'releases/{version}/downloads/{t}.json', 'Canonical JSON') + ' · ' + anchor(
            downloads, f'releases/{version}/downloads/{t}.csv', 'Inspection CSV') + '</p>\n'
    for name in ['snapshot.zip', 'manifest.json', 'metadata.json', 'LICENSE', 'sources/lock.json']:
        page += '<p>' + anchor(downloads, f'releases/{version}/downloads/{name}', name) + '</p>\n'
    write_text(root, downloads, page)
    return {'entries': len(entries), 'commercial_overviews': len(overview_rows(data)),
            'residential_configurations': len(data.get('residential_archetypes', [])),
            'manifest_sha256': hashlib.sha256((release_path/'manifest.json').read_bytes()).hexdigest(),
            'counts': manifest['counts']}


def validate_output(target, release_paths):
    """Limit replacement to a marked generated directory under repository build."""
    target = Path(target).resolve()
    root, build = ROOT.resolve(), (ROOT/'build').resolve()
    if target.is_relative_to(root) and not target.is_relative_to(build):
        raise ValueError('Site output cannot modify repository sources')
    if target in {root, build} or any(target.is_relative_to(Path(p).resolve()) or
                                     Path(p).resolve().is_relative_to(target) for p in release_paths):
        raise ValueError('Unsafe site output path')
    if target.exists() and (not target.is_relative_to(build) or not (target/'site-manifest.json').is_file()):
        raise ValueError('Existing output must be a marked generated directory within repository build/')
    return target


def rename_generated(source, target):
    # Windows antivirus/file indexing may briefly hold a newly written tree.
    # Retry the same validated rename only; persistent permission errors still fail.
    for attempt in range(4):
        try:
            return source.rename(target)
        except PermissionError:
            if attempt == 3:
                raise
            time.sleep(0.2 * (attempt + 1))


def generate_site(release_paths, target, pilot=False, supplement_path=RESOLUTION_RELEASE, water_path=WATER_RELEASE, water_reporting_path=ROOT/'data/water-reporting-releases/v0.1.0'):
    """Verify everything before writing; atomically replace only the supplied output."""
    loaded = sorted([(Path(p), *read_release(p)) for p in release_paths],
                    key=lambda x: tuple(int(n) for n in x[-1][1:].split('.')))
    versions = [v for _, _, _, v in loaded]
    if len(set(versions)) != len(versions):
        raise ValueError('Duplicate release version')
    supplement=None
    completion=None
    reporting=None
    water = validate_water(water_path) if water_path is not None and 'v0.2.0' in versions else None
    if supplement_path is not None and 'v0.2.0' in versions:
        supplement_path=Path(supplement_path)
        base=next(p for p,_,_,v in loaded if v=='v0.2.0')
        supplement={'path':supplement_path,'data':validate_bundle(supplement_path,base),
                    'version':'v'+load_json(supplement_path/'manifest.json')['release_version'],
                    'index':load_json(supplement_path/'profile-index.json'),
                    'base_hash':hashlib.sha256((base/'manifest.json').read_bytes()).hexdigest()}
        policy=load_json(supplement_path/'sources/resolution-policy.json')
        if policy.get('commercial_completion_release'):
            from scripts.resolve import load_completion
            completion=load_completion(policy)
            if supplement['version']=='v0.4.0' and water_reporting_path is not None:
                from scripts.water_reporting import validate_bundle as validate_reporting
                reporting=validate_reporting(water_reporting_path)
    target = validate_output(target, [p for p, *_ in loaded])
    target.parent.mkdir(parents=True, exist_ok=True)
    summary = {'pilot': pilot, 'releases': {}}
    with tempfile.TemporaryDirectory(dir=target.parent) as d:
        stage = Path(d)/'docs'
        stage.mkdir()
        curated = ROOT/'website/content'
        if curated.exists():
            shutil.copytree(curated, stage, dirs_exist_ok=True)
        assets = ROOT/'website/assets'
        if assets.exists():
            shutil.copytree(assets, stage/'assets')
        vendor = ROOT/'build/vendor'
        if vendor.exists():
            from scripts.site_assets import verify_asset
            for entry in load_json(ROOT/'website/assets.lock.json')['assets']:
                src = verify_asset(vendor, entry)
                dst = stage/'assets/vendor'/entry['path']
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
        if completion:
            completion_path=ROOT/'data/completion-releases'/policy['commercial_completion_release']
            full_data=next(data for _,data,_,v in loaded if v=='v0.2.0')
            generate_completion(stage,completion,completion_path,pilot_data(full_data) if pilot else full_data,pilot)
        else:
            write_text(stage,'commercial-completion/index.md','# Commercial fixture-demand catalogue\n\nThe selected historical supplement does not include the commercial-completion bundle.')
        if reporting:
            from scripts.site_water_reporting import generate as generate_reporting
            full_data=next(data for _,data,_,v in loaded if v=='v0.2.0')
            generate_reporting(stage,reporting,water_reporting_path,full_data,pilot)
        else:
            write_text(stage,'water-reporting/index.md','# Complete water reporting catalogue\n\nThe selected historical supplement does not include the optional complete reporting variant.')
        if water:
            destination = stage/'water-equivalents/v0.1.0'
            destination.mkdir(parents=True)
            # Store the small pilot without zlib-dependent bytes, and fix all
            # host-dependent metadata/order for identical Windows/Linux delivery.
            with zipfile.ZipFile(destination/'snapshot.zip','w',compression=zipfile.ZIP_STORED) as archive:
                for src in sorted(Path(water_path).rglob('*'),
                                  key=lambda p:p.relative_to(water_path).as_posix()):
                    if not src.is_file():
                        continue
                    name = src.relative_to(water_path).as_posix()
                    info = zipfile.ZipInfo(name,date_time=(2026,10,4,0,0,0))
                    info.compress_type = zipfile.ZIP_STORED
                    info.create_system = 3
                    info.external_attr = 0o644<<16
                    archive.writestr(info,src.read_bytes())
                    if src.suffix in {'.json','.txt'} or src.name == 'LICENSE':
                        dst = destination/name
                        dst.parent.mkdir(parents=True,exist_ok=True)
                        shutil.copyfile(src,dst)
            write_site_json(stage/f'releases/v0.2.0/records/{water["equivalent_schedule"]["id"]}.json',
                            {'record':water['equivalent_schedule'],'water_equivalent':water})
            derived_id = water['equivalent_schedule']['id']
            current = f'releases/v0.2.0/schedules/{derived_id}.md'
            page = page_header('Medium Office fixture draw equivalent','v0.2.0',derived_id,False)
            page += 'Optional water-equivalent pilot v0.1.0, schema 0.1.0, attached to the existing office program. The original source schedule remains unchanged.\n\n'
            page += explorer_html(current,'v0.2.0',{'source_fixture_draw':water['source_schedule_id'],
                                                   'fixture_draw_equivalent_peak_normalized':derived_id})+'\n\n'
            page += '## Conservation and interpretation\n\n'+display_value(water['conservation'])+'\n\n'+display_value(water['interpretation'])+'\n\n'
            page += '## Field evidence\n\n'+display_value(water['evidence'])+'\n\n'
            page += anchor(current,f'releases/v0.2.0/programs/{water["program_id"]}.md','Existing office program')+' · '+anchor(current,'water-equivalents/v0.1.0/water-equivalent.json','Canonical equivalent and provenance')+' · '+anchor(current,'water-equivalents/v0.1.0/snapshot.zip','Frozen pilot snapshot')+'\n\n'
            write_text(stage,current,page)
        if 'v0.2.0' in versions:
            from scripts.schedule_coverage import build as schedule_coverage
            coverage_base = next(data for _,data,_,v in loaded if v == 'v0.2.0')
            write_site_json(stage/'schedule-coverage.json',schedule_coverage(coverage_base,
                supplement['data'] if supplement else {'resolutions':[]},
                supplement_version=supplement['version'] if supplement else None,water_reporting=reporting))
        if supplement:
            history=[supplement['path']]
            for older in sorted(supplement['path'].parent.glob('v*')):
                if older!=supplement['path'] and older.is_dir() and re.fullmatch(r'v\d+\.\d+\.\d+',older.name):
                    if tuple(map(int,older.name[1:].split('.'))) < tuple(map(int,supplement['version'][1:].split('.'))):
                        validate_bundle(older,base)
                        history.append(older)
            downloads=[]
            # Reuse identical current profile downloads at already-published historical
            # URLs. Every complete snapshot ZIP still contains its own exact inventory.
            supplement['profile_downloads']=shared_profile_downloads(supplement['path'],history)
            for bundle in history:
                aliases=shared_profile_downloads(bundle,history)
                meta=load_json(bundle/'manifest.json'); ver='v'+meta['release_version']
                destination=stage/'resolution-supplements'/ver
                destination.mkdir(parents=True)
                stamp=tuple(map(int,meta['generation_date'].split('-')))+(0,0,0)
                with zipfile.ZipFile(destination/'snapshot.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
                    for src in sorted(bundle.rglob('*')):
                        if not src.is_file():
                            continue
                        name=src.relative_to(bundle).as_posix()
                        info=zipfile.ZipInfo(name,date_time=stamp);info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16
                        if tuple(map(int,ver[1:].split('.')))>=(0,4,0):
                            info.create_system=3
                        archive.writestr(info,src.read_bytes())
                        if src.suffix in {'.json','.csv','.txt'} or src.name=='LICENSE':
                            if name.startswith('profiles/') and src.name in aliases:
                                continue
                            # New bundles expose exact large canonical tables in
                            # the complete ZIP, avoiding redundant Pages storage.
                            # Previously published direct URLs remain unchanged.
                            if tuple(map(int,ver[1:].split('.')))>=(0,4,0) and name not in {
                                    'manifest.json','fixed-background-schedules.json','profile-index.json','LICENSE'}:
                                continue
                            dst=destination/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
                if tuple(map(int,ver[1:].split('.')))>=(0,3,0):
                    write_site_json(destination/'profile-download-map.json',aliases)
                    if (bundle/'fixed-background-schedules.json').exists():
                        from scripts.fixed_background import annual_packet
                        write_site_json(destination/'fixed-background-annual.json',annual_packet(load_json(bundle/'fixed-background-schedules.json')))
                downloads.append(anchor('resolution-supplements/index.md','resolution-supplements/'+ver+'/snapshot.zip','Download '+ver+' with notices'))
            write_text(stage,'resolution-supplements/index.md','# Selective resolutions and executed profiles\n\n'+
                'Supplement '+supplement['version']+' explicitly overlays v0.2.0; frozen source values and older versions are unchanged.\n\n'+
                '\n\n'.join(downloads)+'\n\nCurrent identical profile downloads reuse historical URLs listed in `profile-download-map.json`. Download a complete snapshot ZIP to reproduce its manifest inventory.\n\n'+
                display_value(supplement['data']['summary']))
        for path, data, manifest, version in loaded:
            summary['releases'][version] = generate_release(stage, path, pilot_data(data) if pilot else data,
                                                          manifest, version, versions, pilot, supplement if version=='v0.2.0' else None,
                                                          water if version=='v0.2.0' else None,completion if version=='v0.2.0' else None,
                                                          reporting if version=='v0.2.0' else None)
        latest = versions[-1]
        latest_data = loaded[-1][1]
        source_page = '# Sources and licensing\n\n'
        source_page += ('The actual extracted inputs come from the pinned projects below. DOE reference and PNNL prototype '
                        'coverage is interpreted through OpenStudio Standards; this is not a claim that every official '
                        'DOE/PNNL model package has been ingested or simulated.\n\n')
        projects = {}
        for r in latest_data['source_files']:
            projects.setdefault(r['project'], r)
        for project, r in sorted(projects.items()):
            source_page += '## ' + display_value(project) + '\n\n'
            source_page += '<p><a href="' + html.escape(r['repository'], quote=True) + '">' + display_value(r['repository']) + '</a></p>\n'
            source_page += '<p>Pinned revision: <code>' + display_value(r['version']) + '</code></p>\n'
            source_page += anchor('sources.md', f'releases/{latest}/downloads/{r["license_path"]}', 'Upstream license notice') + '\n\n'
        source_page += ('## Interpretation and primary references\n\n'
                        '- [ComStock](https://comstock.nrel.gov/) — existing commercial stock and model-generation evidence.\n'
                        '- [ResStock](https://resstock.nrel.gov/) — residential source-fixture configurations and option arguments.\n'
                        '- [DOE reference buildings](https://www.energy.gov/eere/buildings/commercial-reference-buildings) — legacy benchmark context.\n'
                        '- [PNNL prototype models](https://www.energycodes.gov/prototype-building-models) — code/prototype context.\n\n'
                        'Source-file locators, hashes and transformations appear on every record page. '
                        'Nulls and specialized unit uncertainties remain explicit.\n\n'
                        '## Original work and software assets\n\n'
                        'Original atlas/site code and documentation are unlicensed by user choice. Upstream data retains '
                        'its own terms; no blanket relicensing is implied. '
                        + anchor('sources.md', f'releases/{latest}/downloads/LICENSE', 'Original-work notice') + ' · '
                        + anchor('sources.md', 'assets/vendor/plotly-LICENSE.txt', 'Plotly.js MIT license') + '\n\n'
                        'MkDocs (BSD), Material for MkDocs (MIT), and their dependencies retain the notices '
                        'distributed with their pinned packages. The repository build guide explains dependency retrieval.\n')
        write_text(stage, 'sources.md', source_page)
        current = 'index.md'
        home = page_header('Energy Archetype Atlas', latest, 'home')
        home += ('<div class="atlas-hero"><p class="atlas-eyebrow">INPUTS FOR ZONING-LOD RESEARCH</p>'
                 '<p class="atlas-intro">Explore the energy semantics behind building archetypes.</p>'
                 '<p>Source-defined programs, schedules, envelope conditions and systems—versioned, inspectable and traceable.</p>'
                 + anchor(current, f'releases/{latest}/catalogue.md', 'Explore the catalogue →') + '</div>\n\n')
        info = summary['releases'][latest]
        home += ('<div class="atlas-stats">' + ''.join('<div><strong>' + str(n) + '</strong><span>' + label + '</span></div>'
            for label, n in [('commercial building / template entries', info['commercial_overviews']),
                             ('residential configurations', info['residential_configurations']),
                             ('program records', info['counts']['programs']), ('schedule records', info['counts']['schedules'])]) + '</div>\n\n')
        if pilot:
            home += '**Pilot presentation: counts of canonical records refer to the full frozen release; only representative pages are generated.**\n\n'
        home += ('## Find → inspect → reuse\n\nStart with a building or program. Inspect source applicability, '
                 'controls and missing inputs. Follow provenance, then download exact versioned records.\n\n'
                 'Typology coverage is not simulation readiness. This atlas supplies deterministic energy semantics; '
                 'geometry, population weights and simulation results are outside its scope.\n\n## Releases\n\n')
        for version in versions:
            home += '<p>' + anchor(current, f'releases/{version}/catalogue.md', version + ' catalogue') + ' · ' + anchor(
                current, f'releases/{version}/downloads.md', 'Downloads and citation') + '</p>\n'
        write_text(stage, 'index.md', home)
        write_text(stage, 'catalogue.md', '# Catalogue\n\n' + '\n\n'.join(anchor('catalogue.md', f'releases/{v}/catalogue.md', v + ' catalogue') for v in versions))
        write_text(stage, 'downloads.md', '# Downloads and releases\n\n' + '\n\n'.join(anchor('downloads.md', f'releases/{v}/downloads.md', v + ' snapshot, manifest and CSV') for v in versions))
        write_site_json(stage/'site-manifest.json', summary)
        # target is checked above and contains generated files only.
        if target.exists():
            shutil.rmtree(target)
        rename_generated(stage,target)
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--release', type=Path, action='append', help='Repeat to preserve multiple release URLs')
    p.add_argument('--output', type=Path, default=ROOT/'build/site-docs')
    p.add_argument('--pilot', action='store_true')
    args = p.parse_args()
    from scripts.site_assets import fetch_assets
    fetch_assets()
    result = generate_site(args.release or [ROOT/'data/releases/v0.1.0', ROOT/'data/releases/v0.2.0'],
                           args.output, args.pilot)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
