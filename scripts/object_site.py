"""Linked energy objects and bounded content-addressed JSON disclosures."""
import gzip
import hashlib
import html
import json
import posixpath
import re
from pathlib import Path

from scripts.definition_contract import PRIMARY, TABLES, canonical
from scripts.definition_site import write
from scripts.program_json import ProgramExporter

PREFIX = '/archetype-atlas/'
PHYSICAL = set(PRIMARY.values()) | {'materials', 'components', 'services', 'compositions', 'schedules'}


def esc(value): return html.escape(str(value), quote=True)


class JSONStore:
    def __init__(self, root): self.root = Path(root)

    def put(self, value):
        raw = canonical(value)
        if len(raw) > 16_000_000: raise ValueError('Object exceeds decoded JSON limit')
        encoded = gzip.compress(raw, mtime=0)
        encoded = encoded[:9] + b'\xff' + encoded[10:]
        digest = hashlib.sha256(encoded).hexdigest()
        href = 'json/' + digest + '.json.gz'
        path = self.root / href
        path.parent.mkdir(exist_ok=True)
        if not path.exists(): path.write_bytes(encoded)
        return {'href': href, 'sha256': digest, 'size_bytes': len(encoded),
                'decoded_size_bytes': len(raw), 'encoding': 'gzip'}


def title(table, row):
    return str(row.get('name') or row.get('source_name') or row.get('source_channel') or
               row.get('role') or row.get('locator') or row.get('path') or row['id'])


def references(value, registry):
    found = set()
    def scan(item):
        if isinstance(item, str) and item in registry: found.add(item)
        elif isinstance(item, dict):
            for k, v in item.items():
                if k != 'id': scan(v)
        elif isinstance(item, list):
            for v in item: scan(v)
    scan(value)
    found.discard(value.get('id'))
    return found


def json_markup(raw, defaulted=None, count=0, reason='Program defaults do not apply to this object kind.'):
    attributes = f'data-raw="{esc(json.dumps(raw,separators=(",",":")))}" data-root="../../"'
    if defaulted: attributes += f' data-defaulted="{esc(json.dumps(defaulted,separators=(",",":")))}"'
    attributes += f' data-assumptions="{count}" data-default-reason="{esc(reason)}"'
    return ('<section class="object-json" ' + attributes + '><button type="button" class="object-copy">Copy JSON</button>'
            '<details class="object-source"><summary>JSON</summary><pre tabindex="0">Expand to load the complete verified JSON.</pre></details>'
            '<p class="object-status" role="status" aria-live="polite"></p></section>')


def schedule_markup():
    return ('<section class="schedule-viewer"><h2>Unique day schedules</h2><p>Exact source profiles; design days remain separate.</p>'
            '<button type="button" class="schedule-load">Load interactive plots</button><p class="schedule-status" role="status"></p>'
            '<div class="schedule-controls" hidden><label>Unique day profile <select class="schedule-profile"></select></label>'
            '<label>Calendar year <input class="schedule-year" type="number" value="2007" min="1" max="9999"></label>'
            '<label>Holiday dates (MM-DD, comma-separated) <input class="schedule-holidays" placeholder="None"></label>'
            '<button type="button" class="schedule-update">Update calendar</button></div>'
            '<div class="schedule-day-chart" aria-label="Unique daily step profiles"></div>'
            '<h2>Annual schedule</h2><p>Day of year × hour of day, in local standard time. Click a day to inspect it. Gaps mean Unknown.</p>'
            '<div class="schedule-annual-chart" aria-label="Annual schedule heatmap"></div>'
            '<details><summary>Exact values for the selected day</summary><div class="schedule-values"></div></details></section>')


def generate_objects(bundle, root):
    root = Path(root); store = JSONStore(root); exporter = ProgramExporter(bundle)
    records = {r['id']: (table, r) for table in TABLES for r in bundle[table]}
    registry = {}
    for identity, (table, row) in records.items():
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', identity): raise ValueError('Unsafe object identity')
        physical = table in PHYSICAL
        path = ('definitions/' if table in PRIMARY.values() else 'objects/') + identity + ('.md' if physical else '/index.html')
        registry[identity] = {'table': table, 'name': title(table, row), 'path': path}
    failures = []
    for identity, (table, row) in records.items():
        info = registry[identity]; path = info['path']; defaulted = None; count = 0
        reason = 'Defaults are defined for program imports; this library object retains its explicit unknowns.'
        if table == 'programs':
            raw = exporter.export(identity, 'raw')
            try:
                ready = exporter.export(identity, 'defaulted'); defaulted = store.put(ready); count = len(ready['assumptions'])
            except ValueError as error:
                reason = 'Default-filled export unavailable: ' + str(error)
                failures.append({'id': identity, 'reason': str(error)})
        else: raw = row
        descriptor = store.put(raw)
        is_markdown = path.endswith('.md')
        def link(ref):
            target = registry[ref]['path']
            if not target.endswith('.md'): return PREFIX + target.removesuffix('index.html')
            if not is_markdown: return PREFIX + target.removesuffix('.md') + '/'
            return posixpath.relpath(target, posixpath.dirname(path))
        text = f'# {esc(info["name"])}\n\n[Catalogue](../catalogue.md)\n\n' if is_markdown else ''
        text += f'<p class="definition-id"><code>{esc(identity)}</code> · {esc(table.replace("_"," "))}</p>\n\n'
        for key in ('building_type', 'template', 'climate', 'role', 'system_type', 'scope', 'assembly_status', 'topology_status', 'unresolved_reason'):
            if row.get(key): text += f'**{key.replace("_"," ").capitalize()}:** {esc(row[key])}\n\n' if is_markdown else f'<p>{esc(key)}: {esc(row[key])}</p>'
        if is_markdown and row.get('parameters'):
            text += '| Parameter | Value | Unit |\n|---|---|---|\n'
            for name, value in row['parameters'].items():
                if not isinstance(value, dict): continue
                v = value.get('value')
                shown = 'Unknown' if v is None else (f'[{esc(registry[v]["name"])}]({link(v)})' if isinstance(v, str) and v in registry else esc(v))
                text += f'| {esc(name)} | {shown} | {esc(value.get("unit",""))} |\n'
            text += '\n'
        if is_markdown and row.get('loads'):
            text += '| Load | Magnitude | Unit | Basis | Schedule |\n|---|---|---|---|---|\n'
            for load in row['loads']:
                sid = load.get('schedule_id')
                schedule = f'[{esc(registry[sid]["name"])}]({link(sid)})' if sid in registry else 'Unknown'
                value = esc(load['value']) if load['value'] is not None else 'Unknown (default: 0)'
                text += f'| {esc(load["quantity"])} | {value} | {esc(load["unit"])} | {esc(load["basis"])} | {schedule} |\n'
            text += '\n'
        if is_markdown and row.get('layers'):
            text += '| Layer (outside → inside) | Material |\n|---|---|\n'
            for i, layer in enumerate(row['layers']):
                mid = layer['material_id'];label = registry[mid]['name'] if mid in registry else 'Unknown'
                text += f'| {i+1} | [{esc(label)}]({link(mid)}) |\n' if mid in registry else f'| {i+1} | Unknown |\n'
            text += '\n'
        if table == 'programs': text += 'Unknown source values stay **Unknown**. Copy with defaults applies labelled experimental assumptions.\n\n'
        text += json_markup(descriptor, defaulted, count, reason) + '\n\n'
        if table == 'schedules': text += schedule_markup() + '\n\n'
        refs = sorted(references(row, registry), key=lambda r: (registry[r]['table'], registry[r]['name']))
        if refs:
            text += '<details class="object-references"><summary>Referenced objects</summary><ul>'
            for ref in refs:
                target = link(ref)
                # Markdown links inside raw HTML are not transformed by MkDocs.
                if target.endswith('.md'): target = PREFIX + registry[ref]['path'].removesuffix('.md') + '/'
                text += f'<li><a href="{esc(target)}">{esc(registry[ref]["name"])} · {esc(registry[ref]["table"])}</a></li>'
            text += '</ul></details>\n'
        if is_markdown: write(root, path, text)
        else:
            document = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                f'<title>{esc(info["name"])}</title><link rel="stylesheet" href="{PREFIX}assets/site.css"></head><body>'
                f'<header class="definition-header"><a href="{PREFIX}catalogue/">Catalogue</a> · <a href="{PREFIX}sources/">Sources</a></header>'
                f'<main class="definition-document"><h1>{esc(info["name"])}</h1>{text}</main><script src="{PREFIX}assets/object.js"></script></body></html>')
            write(root, path, document)
    write(root, 'object-index.json', canonical(registry).decode())
    return {'objects': len(records), 'default_export_failures': failures}
