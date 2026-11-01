"""HTML fragments of the suite site (ADR 0043).

Records render generically: objects as definition lists, lists of objects as tables,
null as an explicit null, and any string that is the ID of a published object as a
link to it (an anchor on the same page, its suite page, or the viewer). Blocks the
renderer has never seen (a new optional Program JSON block) therefore render
without code changes. Fillings keep their place on the field they fill and are
marked so the version switch can hide or highlight them. Schedules render their
rules and day profiles, or an annual series as monthly and typical-day plots.
"""
import functools
import html
import json
import posixpath
import re
from urllib.parse import quote

from scripts.common import ROOT

ZONE = re.compile(r'^([0-8])(?:-?([A-Ca-c]))?(?![0-9])')
CLIMATE_KEY = re.compile(r'^[0-8][A-C]?$')
MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
MONTH_DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
WIDE = 12
REPOSITORY = 'https://github.com/Energy-Atlas/archetype-atlas/blob/main/'
ADR = re.compile(r'\bADRs? \d{4}(?:(?:, | and )\d{4})*')


def esc(value):
    return html.escape(str(value), quote=True)


def zone(label):
    """The climate zone (`4A`, `7`) at the start of an atlas climate label or context key."""
    match = ZONE.match(str(label or ''))
    return match[1]+(match[2] or '').upper() if match else None


@functools.cache
def adr_files():
    """{ADR number: its path in the repository}; the site digest covers these names (suite_site.inputs_digest)."""
    return {path.name[:4]: 'docs/adr/'+path.name for path in sorted((ROOT/'docs/adr').glob('[0-9][0-9][0-9][0-9]-*.md'))}


def prose(text):
    """Escaped text in which every `ADR NNNN` links to the decision record in the repository."""
    def link(number):
        path = adr_files().get(number)
        return f'<a href="{esc(REPOSITORY+path)}">{number}</a>' if path else number

    def replace(match):
        numbers = re.split(r'(, | and )', match[0].split(' ', 1)[1])
        return match[0].split(' ', 1)[0]+' '+''.join(part if part in (', ', ' and ') else link(part) for part in numbers)
    return ADR.sub(replace, esc(text))


def reason_text(reason):
    """An exporter's reason without the record ID (and context key) it starts with."""
    return re.sub(r'^[A-Za-z0-9][A-Za-z0-9._:-]{5,}(?: [A-Za-z0-9._-]+)?: ', '', reason or '')


def anchor(identifier):
    return re.sub(r'[^A-Za-z0-9._:-]', '-', identifier)


class Links:
    """Where every published object lives: a page (with an anchor) or the viewer only."""

    def __init__(self, release=None):
        self.pages = {}
        self.viewer = set()
        self.release = release

    def place(self, identifier, url):
        self.pages.setdefault(identifier, url)

    def known(self, identifier):
        return identifier in self.pages or identifier in self.viewer


class Page:
    """One page being written: its URL and the anchors it already holds."""

    def __init__(self, links, url):
        self.links, self.url, self.anchors, self.local = links, url, set(), set()

    def here(self, identifier):
        """Whether the object renders on this page: its home, or a local copy (`local`)."""
        return identifier in self.local or self.links.pages.get(identifier) == self.url

    def rel(self, target):
        """A link from this page to a site path (`catalogue/x/` or `store/y.json.gz`)."""
        path = posixpath.relpath(target.rstrip('/') or '.', self.url.rstrip('/') or '.')
        return path+'/' if target.endswith('/') else path

    def claim(self, identifier):
        """An `id` attribute for an object rendered here, once per page."""
        if identifier in self.anchors:
            return ''
        self.anchors.add(identifier)
        return f' id="{esc(anchor(identifier))}"'

    def href(self, identifier):
        if identifier in self.anchors or identifier in self.local:
            return '#'+anchor(identifier)
        url = self.links.pages.get(identifier)
        if url is not None:
            return ('' if url == self.url else self.rel(url))+'#'+anchor(identifier)
        if identifier in self.links.viewer:
            return self.rel('view/')+'?id='+quote(identifier, safe='')
        return None

    def link(self, identifier, text=None):
        target = self.href(identifier)
        label = f'<code>{esc(text or identifier)}</code>'
        return f'<a href="{esc(target)}">{label}</a>' if target else label


def scalar(value, page):
    if value is None:
        return '<span class="ea-null">null</span>'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (int, float)):
        return esc(json.dumps(value))
    text = str(value)
    if page.links.known(text):
        return page.link(text)
    return esc(text)


def is_scalar(value):
    return value is None or isinstance(value, (str, int, float, bool))


def render(value, page, omit=()):
    """Any JSON value as HTML."""
    if is_scalar(value):
        return scalar(value, page)
    if isinstance(value, list):
        return render_list(value, page, omit)
    return render_dict(value, page, omit)


def render_list(items, page, omit=()):
    if not items:
        return '<span class="ea-empty">[]</span>'
    if all(is_scalar(item) for item in items):
        return ', '.join(scalar(item, page) for item in items)
    if all(isinstance(item, dict) for item in items):
        columns = []
        for item in items:
            columns.extend(k for k in item if k not in columns and k not in omit)
        if len(columns) <= WIDE:
            return table(items, columns, page, omit)
    return '<ol class="ea-list">'+''.join(f'<li>{render(item, page, omit)}</li>' for item in items)+'</ol>'


def row_anchor(item, page):
    """Rows of objects published on this page, or only here (loads by demand ID), carry their anchor."""
    for key in ('id', 'demand_id'):
        identifier = item.get(key)
        if isinstance(identifier, str) and (page.here(identifier) or not page.links.known(identifier)):
            return page.claim(identifier)
    return ''


def table(items, columns, page, omit=()):
    head = ''.join(f'<th>{esc(c)}</th>' for c in columns)
    rows = []
    for item in items:
        cells = ''.join(cell(item, c, page, omit) for c in columns)
        rows.append(f'<tr{row_anchor(item, page)}>{cells}</tr>')
    return f'<div class="ea-table"><table><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def cell(item, column, page, omit):
    if column not in item:
        return '<td class="ea-absent"></td>'
    value = item[column]
    if column == 'filling':
        return f'<td class="ea-filling">{render(value, page, omit)}</td>'
    return f'<td>{render(value, page, omit)}</td>'


def by_climate(value, page):
    head = ''.join(f'<th data-climate="{esc(k)}">{esc(k)}</th>' for k in value)
    cells = ''.join(f'<td data-climate="{esc(k)}">{scalar(v, page) if is_scalar(v) else render(v, page)}</td>' for k, v in value.items())
    return f'<div class="ea-table"><table class="ea-climates"><thead><tr>{head}</tr></thead><tbody><tr>{cells}</tr></tbody></table></div>'


def render_dict(value, page, omit=()):
    if not value:
        return '<span class="ea-empty">{}</span>'
    if len(value) > 1 and all(CLIMATE_KEY.match(k) for k in value):
        return by_climate(value, page)
    anchor_attr = ''
    if isinstance(value.get('id'), str) and page.here(value['id']):
        anchor_attr = page.claim(value['id'])
    parts = []
    for key, item in value.items():
        if key in omit:
            continue
        body = render(item, page, omit)
        if key == 'filling':
            parts.append(f'<dt class="ea-filling">filling</dt><dd class="ea-filling">{body}</dd>')
        else:
            parts.append(f'<dt>{esc(key)}</dt><dd>{body}</dd>')
    return f'<dl class="ea-fields"{anchor_attr}>{"".join(parts)}</dl>'


# Plots: inline SVG, readable without JavaScript and coloured by the page theme.

def short(value):
    """A short axis label; the exact values are in the list beside the plot."""
    return f'{value:.4g}'


def plot(values, labels, step=True, width=480, height=130, unit=None, x_title='hour'):
    """A step or bar plot of a short series; nulls leave gaps. `labels` are spread over the series (24 hour labels
    over 96 quarter-hour values). The axes carry their titles (the hour and the unit) and the minimum and maximum. A
    series of one value is a constant and is said so instead of plotted."""
    known = [v for v in values if isinstance(v, (int, float))]
    if not known:
        return '<p class="ea-note">No known values.</p>'
    if len(values) == 1:
        return f'<p class="ea-constant">Constant {esc(json.dumps(values[0]))}{" "+esc(unit) if unit else ""} all day.</p>'
    low, high = min(0, min(known)), max(known)
    span = (high-low) or 1
    pad, top, left, n = 4, 14, 40, len(values)
    x = lambda i: left+(width-left-pad)*i/n
    y = lambda v: top+(height-top-pad)*(1-(v-low)/span)
    paths, current = [], []
    for i, v in enumerate(values):
        if isinstance(v, (int, float)):
            current.append(f'{x(i):.1f},{y(v):.1f} {x(i+1):.1f},{y(v):.1f}' if step else f'{x(i+0.5):.1f},{y(v):.1f}')
        elif current:
            paths.append(current)
            current = []
    if current:
        paths.append(current)
    lines = ''.join(f'<polyline points="{" ".join(p)}"/>' for p in paths)
    per = n/len(labels) if labels else 1
    ticks = ''.join(f'<text x="{x((i+0.5)*per):.1f}" y="{height+12}">{esc(text)}</text>' for i, text in enumerate(labels) if text)
    title = f'{n} values from {json.dumps(min(known))} to {json.dumps(max(known))}'+(f' {unit}' if unit else '')
    axes = (f'<text x="0" y="{top+4}" class="ea-scale">{esc(short(high))}</text>'
            f'<text x="0" y="{y(low):.1f}" class="ea-scale">{esc(short(low))}</text>'
            + (f'<text x="0" y="9" class="ea-scale ea-axis-title">{esc(unit)}</text>' if unit else '')
            + f'<text x="{(left+width)/2:.0f}" y="{height+25}" class="ea-axis-title">{esc(x_title)}</text>')
    return (f'<svg class="ea-plot" viewBox="0 0 {width} {height+28}" role="img" aria-label="{esc(title)}">'
            f'<title>{esc(title)}</title><line x1="{left}" x2="{width-pad}" y1="{y(low):.1f}" y2="{y(low):.1f}" class="ea-axis"/>'
            f'{axes}{lines}{ticks}</svg>')


HOURS = [str(h) if h % 3 == 0 else '' for h in range(24)]


def day_values(values):
    text = ', '.join('null' if v is None else json.dumps(v) for v in values)
    return f'<details class="ea-values"><summary>Values</summary><p>{esc(text)}</p></details>'


def annual_summary(values):
    """Monthly means and the typical day (mean of each hour) of an 8,760-value year."""
    months, start = [], 0
    days = MONTH_DAYS if len(values) < 8784 else (31, 29, *MONTH_DAYS[2:])
    for count in days:
        chunk = [v for v in values[start*24:(start+count)*24] if isinstance(v, (int, float))]
        months.append(sum(chunk)/len(chunk) if chunk else None)
        start += count
    hours = []
    for h in range(24):
        chunk = [v for v in values[h::24] if isinstance(v, (int, float))]
        hours.append(sum(chunk)/len(chunk) if chunk else None)
    return months, hours


def rounded(values):
    return [None if v is None else float(f'{v:.6g}') for v in values]


def inline_days(record):
    """An export's schedule (Program JSON: rules with their `values` inline) as a stored schedule: rules naming day
    profiles (`#1`, `#2`, ... in first-use order; the `#` marks a profile without a release ID) and the profiles."""
    rules, days, ids = [], {}, {}
    for rule in record.get('rules', []):
        if 'values' not in rule:
            rules.append(rule)
            continue
        key = json.dumps(rule['values'])
        if key not in ids:
            ids[key] = f'#{len(ids)+1}'
            days[ids[key]] = rule['values']
        rules.append({**{k: v for k, v in rule.items() if k != 'values'}, 'day': ids[key]})
    return {**{k: v for k, v in record.items() if k != 'rules'}, 'rules': rules, 'days': days}


def schedule(record, page, descriptor=None):
    """A schedule: rule table and day profiles, or an annual series summary. A schedule in export form (rules with
    inline values) renders the same way."""
    if any('values' in rule for rule in record.get('rules', [])):
        record = inline_days(record)
    sid = record['id']
    unit = record.get('units') or record.get('unit') or ''
    meta = {k: v for k, v in record.items() if k not in ('id', 'rules', 'days') and not (isinstance(v, list) and len(v) > 48)}
    parts = [f'<section class="ea-schedule"{page.claim(sid)}><h3>{esc(record.get("source_name") or record.get("name") or sid)}</h3>',
             f'<p><code>{esc(sid)}</code></p>', json_buttons([('Schedule JSON', sid, descriptor)], page) if descriptor else '',
             render_dict(meta, page)]
    series = next((v for v in record.values() if isinstance(v, list) and len(v) >= 8760), None)
    if series is not None:
        months, hours = annual_summary(series)
        parts.append(f'<h4>Monthly mean ({esc(unit)})</h4>'+plot(months, MONTHS, step=False, unit=unit, x_title='month')+
                     '<div class="ea-table"><table><thead><tr>'+''.join(f'<th>{m}</th>' for m in MONTHS)+
                     '</tr></thead><tbody><tr>'+''.join(f'<td>{scalar(v, page)}</td>' for v in rounded(months))+'</tr></tbody></table></div>')
        parts.append(f'<h4>Typical day: mean of each hour ({esc(unit)})</h4>'+plot(hours, HOURS, unit=unit)+day_values(rounded(hours)))
        parts.append(f'<p class="ea-note">{len(series):,} hourly values; the complete series is in the JSON.</p>')
    else:
        days, order = record.get('days', {}), []
        for rule in record.get('rules', []):
            if rule.get('day') in days and rule['day'] not in order:
                order.append(rule['day'])
        label = {d: f'P{i+1}' for i, d in enumerate(order)}
        rules = [{**{k: v for k, v in r.items() if k != 'day'}, **({'profile': label[r['day']]} if 'day' in r else {})}
                 for r in record.get('rules', [])]
        if rules:
            parts.append('<h4>Rules, in source order</h4>'+render_list(rules, page))
        for day in order:
            code = '' if day.startswith('#') else f' <code>{esc(day)}</code>'
            parts.append(f'<div class="ea-day"><h4>{label[day]}{code} ({esc(unit)})</h4>'
                         f'{plot(days[day], HOURS, unit=unit)}{day_values(days[day])}</div>')
    parts.append('</section>')
    return ''.join(parts)


def evidence(row, page):
    return f'<section class="ea-evidence"{page.claim(row["id"])}><h3><code>{esc(row["id"])}</code></h3>{render_dict({k: v for k, v in row.items() if k != "id"}, page)}</section>'


def json_buttons(entries, page, notices=()):
    """Copy and download controls for stored documents: (label, file stem, descriptor or None, reason). Each control
    names the release and the SHA-256 of the JSON file Download saves (the canonical bytes, `json_sha256`)."""
    out = []
    for entry in entries:
        label, stem, descriptor = entry[:3]
        if descriptor is None:
            out.append(f'<span class="ea-json ea-json--absent">{esc(label)}: <em>{prose(reason_text(entry[3]) if len(entry) > 3 and entry[3] else "not exported")}</em></span>')
            continue
        data = esc(json.dumps({**descriptor, 'href': page.rel(descriptor['href'])}, sort_keys=True, separators=(',', ':')))
        release = f'release {esc(page.links.release)} · ' if page.links.release else ''
        out.append(f'<span class="ea-json" data-json="{data}" data-file="{esc(stem)}.json">'
                   f'<span class="ea-json__label">{esc(label)}</span> '
                   f'<button type="button" class="md-button ea-copy" hidden>Copy</button> '
                   f'<a class="md-button" href="{esc(page.rel(descriptor["href"]))}" download="{esc(stem)}.json.gz">Download</a>'
                   f'<span class="ea-json__meta">{release}SHA-256 <code>{esc(descriptor["json_sha256"])}</code></span></span>')
    return '<div class="ea-exports">'+''.join(out)+''.join(notices)+'</div>'
