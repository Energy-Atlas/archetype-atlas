"""The zoning-recommendation pages of the site (ADR 0050): the geometric LOD study's data drop.

Reads `data/lod-recommendations/v1/`: the BEMGen report writer's `lod-recommendations.json`
files (schema `schemas/lod-recommendations-v1.schema.json`) and the provenance sidecar, and
writes into the MkDocs input tree, like the suite pages (`scripts.suite_site`):

- `zoning/`: the overview, what the study measured, the threshold, every prototype;
- `zoning/<prototype>/`: one page per prototype, one row per climate zone × vintage ×
  orientation with the recommended zoning and its errors, then every zoning of every cell;
- `zoning/heat-transfer/`: the interior-wall and floor heat-transfer sub-study;
- `zoning/method/`: method, limits and provenance.

Every table is generated from the files; no value is computed here beyond counts. The loader
admits fields a later drop adds (the next consolidated drop replaces the files in place).
"""
import json
import re
from pathlib import Path

from scripts.common import ROOT
from scripts.site_pages import contents, crumbs, markdown, section
from scripts.site_render import Page, anchor, esc, json_buttons

DROP = ROOT/'data/lod-recommendations/v1'
MAIN, HT, PROVENANCE = 'lod-recommendations.json', 'lod-recommendations-ht.json', 'provenance.json'
FORMAT, MAJOR = 'bemgen-lod-recommendations', '1'
URL = 'zoning/'
TITLE = 'Zoning recommendations'
PROTOTYPES = {'MediumOffice': 'Medium office', 'FullServiceRestaurant': 'Full-service restaurant', 'StripMall': 'Strip mall',
              'StandAloneRetail': 'Stand-alone retail', 'Supermarket': 'Supermarket', 'Warehouse': 'Warehouse',
              'PrimarySchool': 'Primary school', 'SmallHotel': 'Small hotel', 'LargeHotel': 'Large hotel', 'Hospital': 'Hospital',
              'Outpatient': 'Outpatient'}
SIMPLIFIERS = {'NoSimplification': 'every room of the prototype is a zone (the reference)',
               'SemanticMerge': 'rooms of one program on one floor merge',
               'ConditionedMerge': 'conditioned rooms of one floor merge; unconditioned rooms stay',
               'PerimeterCore': 'each floor is cut into perimeter zones of the given depth and a core',
               'SingleZonePerFloor': 'each floor is one zone'}
STACKERS = {'Stack': 'every floor is written', 'StackedFloorZoneMultiplier': 'identical middle floors are one floor with a multiplier',
            'SingleZonePerFloorType': 'each floor type (ground, middle, top) is one zone', 'SingleZoneBuilding': 'the building is one zone'}
AXES = {'prototype': 'Prototype', 'climate': 'Climate zone', 'vintage': 'Vintage', 'orientation': 'Orientation'}
ENTRY_KEYS = ('id', 'prototype', 'climate_zone', 'vintage', 'orientation_degrees', 'programs', 'reference', 'zonings', 'recommended')
NULL = '<span class="ea-null">–</span>'


# Loading.

class Drop:
    """The data drop: the main matrix, the heat-transfer sub-study (optional) and the provenance sidecar."""

    def __init__(self, folder=DROP):
        self.folder = Path(folder)
        self.provenance = json.loads((self.folder/PROVENANCE).read_text(encoding='utf-8'))
        self.main = document(self.folder/MAIN)
        self.ht = document(self.folder/HT) if (self.folder/HT).is_file() else None

    @property
    def threshold(self):
        return self.main['threshold']

    def prototypes(self):
        """The prototypes of the main matrix in page order (the known names first, then any new one by name)."""
        seen = sorted({e['prototype'] for e in self.main['entries']}, key=lambda p: (p not in PROTOTYPES, list(PROTOTYPES).index(p) if p in PROTOTYPES else p))
        return seen

    def entries(self, prototype):
        return sorted((e for e in self.main['entries'] if e['prototype'] == prototype), key=cell_order)


def document(path):
    """A recommendations file, checked for the shape the pages need; fields the writer adds later pass through."""
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if data.get('format') != FORMAT or str(data.get('version', '')).split('.')[0] != MAJOR:
        raise ValueError(f'{path.name}: not a {FORMAT} {MAJOR}.x document')
    for key in ('threshold', 'entries', 'by_program', 'metrics'):
        if key not in data:
            raise ValueError(f'{path.name}: missing {key}')
    for entry in data['entries']:
        missing = [k for k in ENTRY_KEYS if k not in entry]
        if missing:
            raise ValueError(f'{path.name}: entry {entry.get("id")} lacks {", ".join(missing)}')
    return data


def cell_order(entry):
    return (entry['climate_zone'], entry['vintage'], entry['orientation_degrees'], entry['prototype'])


# Labels.

def words(camel):
    text = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', str(camel or '')).replace('_', ' ')
    return text[:1].upper()+text[1:].lower()


def prototype_name(prototype):
    return PROTOTYPES.get(prototype) or words(prototype)


def prototype_slug(prototype):
    return re.sub(r'[^a-z0-9]+', '-', prototype_name(prototype).lower()).strip('-')


def zoning_label(zoning, flags=True):
    """`Perimeter core 3 m + Stack (IWHT off)`: the simplifier, its depth, the stacker and any heat-transfer switch off."""
    if not any(zoning.get(k) is not None for k in ('simplifier', 'stacker', 'perimeter_depth', 'iwht', 'fht')):
        return 'zoning not recorded'  # the writer stores no zoning fields for a site that did not run
    simplifier = (zoning.get('simplifier') or '').split(' ')[0]
    name = words(simplifier) if simplifier else 'unknown simplifier'
    if zoning.get('perimeter_depth') is not None:
        name += f' {zoning["perimeter_depth"]:g} m'
    if zoning.get('stacker'):
        name += ' + '+words(zoning['stacker'])
    marks = [m for m, on in (('IWHT off', zoning.get('iwht') is False), ('FHT off', zoning.get('fht') is False),
                             ('joined pieces', zoning.get('join_pieces') is True)) if on]
    return name+(f' ({", ".join(marks)})' if flags and marks else '')


def orientation(degrees):
    return f'{degrees:g}°'


def num(value, digits=1, flag=None, judged=True):
    if value is None:
        return NULL
    text = f'{value:,.{digits}f}'
    if flag:
        text = f'<abbr class="ea-flagged" title="{esc(flag)}">{text}</abbr>'
    return text if judged else f'<span class="ea-unjudged" title="not judged: the reference load is below the threshold\'s minimum">{text}</span>'


def judged(entry, load, threshold):
    intensity = entry['reference'].get(f'{load}_kwh_m2_conditioned')
    return intensity is not None and intensity >= threshold.get('min_reference_kwh_m2', 0)


def metric(zoning, name, entry, threshold, digits=1):
    load = 'sensible_heating' if name.startswith('sensible_heating') else 'sensible_cooling' if name.startswith('sensible_cooling') else None
    return num(zoning['metrics'].get(name), digits, zoning.get('flags', {}).get(name), judged(entry, load, threshold) if load else True)


def facts_html(facts):
    rows = ''.join(f'<dt>{esc(k)}</dt><dd>{v}</dd>' for k, v in facts if v not in (None, ''))
    return f'<dl class="ea-facts">{rows}</dl>'


def table(rows, columns, klass='ea-listing'):
    head = ''.join(f'<th>{esc(c)}</th>' for c in columns)
    body = ''.join(r if isinstance(r, str) else '<tr>'+''.join(f'<td>{c}</td>' for c in r)+'</tr>' for r in rows)
    return f'<div class="ea-table"><table class="{klass}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def axis_values(entry):
    return {'prototype': entry['prototype'], 'climate': entry['climate_zone'], 'vintage': entry['vintage'],
            'orientation': f'{entry["orientation_degrees"]:g}'}


def axis_text(axis, value):
    return prototype_name(value) if axis == 'prototype' else orientation(float(value)) if axis == 'orientation' else value


def filter_form(entries, axes):
    selects = []
    for axis in axes:
        values = sorted({axis_values(e)[axis] for e in entries}, key=lambda v: float(v) if axis == 'orientation' else v)
        if len(values) < 2:
            continue
        options = ''.join(f'<option value="{esc(v)}">{esc(("Zone " if axis == "climate" else "")+axis_text(axis, v))}</option>' for v in values)
        selects.append(f'<label>{esc(AXES[axis])} <select data-filter="{axis}"><option value="">All</option>{options}</select></label>')
    if not selects:
        return ''
    return f'<form class="ea-filters" data-filters data-unit="cells" hidden>{"".join(selects)}<output class="ea-filter-count" aria-live="polite"></output></form>'


# Cells.

def kept(entry):
    """The zonings in the metric table: succeeded and not a duplicate, fewest zones first."""
    rows = [z for z in entry['zonings'] if z['succeeded'] and not z.get('duplicate_of')]
    return sorted(rows, key=lambda z: (z['zone_count'] if z['zone_count'] is not None else 10**6, zoning_label(z['zoning'])))


def cell_anchor(entry):
    return 'cell-'+entry['id']


def summary_rows(page, entries, axes, threshold):
    """One row per recommended zoning of each cell (ties repeat the cell), or one row saying none meets the threshold."""
    rows = []
    for entry in entries:
        values = axis_values(entry)
        attrs = ''.join(f' data-{a}="{esc(v)}"' for a, v in values.items())
        reference = entry['reference']
        lead = [f'<a href="#{esc(anchor(cell_anchor(entry)))}">{esc(axis_text(a, values[a]))}</a>' if i == 0 else esc(axis_text(a, values[a]))
                for i, a in enumerate(axes)]
        lead += [num(reference.get('zone_count'), 0), num(reference.get('sensible_heating_kwh_m2_conditioned')),
                 num(reference.get('sensible_cooling_kwh_m2_conditioned'))]
        by_site = {z['site_name']: z for z in entry['zonings']}
        recommended = entry['recommended']
        if not recommended:
            rows.append(f'<tr data-context="{esc(entry["id"])}"{attrs}>'+''.join(f'<td>{c}</td>' for c in lead)
                        + f'<td colspan="9"><em>none meets the threshold</em></td></tr>')
            continue
        for pick in recommended:
            zoning = by_site.get(pick['site_name'], {'metrics': {}, 'flags': {}, 'conditioned_area_change_pct': None})
            cells = lead+[esc(zoning_label(pick['zoning'])), num(pick.get('zone_count'), 0)]
            cells += [metric(zoning, f'sensible_{load}_{m}', entry, threshold) for m in ('kwh_rel_err_pct', 'cvrmse_pct', 'nmbe_pct') for load in ('heating', 'cooling')]
            cells.append(num(zoning.get('conditioned_area_change_pct'), 2))
            rows.append(f'<tr class="ea-recommended" data-context="{esc(entry["id"])}"{attrs}>'+''.join(f'<td>{c}</td>' for c in cells)+'</tr>')
    return rows


SUMMARY_COLUMNS = ('Reference zones', 'Heating kWh/m²', 'Cooling kWh/m²', 'Recommended zoning', 'Zones', 'Heating error %', 'Cooling error %',
                   'Heating CV(RMSE) %', 'Cooling CV(RMSE) %', 'Heating NMBE %', 'Cooling NMBE %', 'Area change %')
ZONING_COLUMNS = ('Zoning', 'Zones', 'Area change %', 'Heating error %', 'Cooling error %', 'Heating CV(RMSE) %', 'Cooling CV(RMSE) %',
                  'Heating NMBE %', 'Cooling NMBE %', 'Peak heating error %', 'Peak cooling error %', 'Meets the threshold')


def cell_section(page, entry, axes, threshold):
    values = axis_values(entry)
    attrs = ''.join(f' data-{a}="{esc(v)}"' for a, v in values.items())
    title = ' · '.join(axis_text(a, values[a]) for a in axes)
    reference = entry['reference']
    benchmark = (f'Reference <code>{esc(reference.get("site_name", ""))}</code>: {esc(zoning_label(reference.get("zoning", {})))}, '
                 f'{num(reference.get("zone_count"), 0)} zones, {num(reference.get("conditioned_area_m2"), 0)} m² conditioned; '
                 f'annual sensible heating {num(reference.get("sensible_heating_kwh_m2_conditioned"))} and cooling '
                 f'{num(reference.get("sensible_cooling_kwh_m2_conditioned"))} kWh/m²; peak heating {num(reference.get("sensible_heating_max_kw"))} '
                 f'and cooling {num(reference.get("sensible_cooling_max_kw"))} kW.')
    for load in ('heating', 'cooling'):
        if not judged(entry, 'sensible_'+load, threshold):
            benchmark += f' Sensible {load} is below {threshold.get("min_reference_kwh_m2", 0):g} kWh/m² and is not judged.'
    recommended = {p['site_name'] for p in entry['recommended']}
    rows = []
    for zoning in kept(entry):
        meets = zoning['meets_threshold']
        misses = '; '.join(zoning.get('misses', []))
        verdict = ('<strong>yes, recommended</strong>' if zoning['site_name'] in recommended else 'yes') if meets else \
            f'<abbr title="{esc(misses)}">no</abbr>' if misses else 'no'
        cells = [esc(zoning_label(zoning['zoning'])), num(zoning.get('zone_count'), 0), num(zoning.get('conditioned_area_change_pct'), 2)]
        cells += [metric(zoning, f'sensible_{load}_{m}', entry, threshold) for m in ('kwh_rel_err_pct', 'cvrmse_pct', 'nmbe_pct') for load in ('heating', 'cooling')]
        cells += [metric(zoning, f'sensible_{load}_max_kw_rel_err_pct', entry, threshold) for load in ('heating', 'cooling')]
        cells.append(verdict)
        klass = ' class="ea-recommended"' if zoning['site_name'] in recommended else ''
        rows.append(f'<tr{klass}>'+''.join(f'<td>{c}</td>' for c in cells)+'</tr>')
    failed = [z for z in entry['zonings'] if not z['succeeded']]
    for zoning in failed:
        rows.append(f'<tr class="ea-failed"><td>{esc(zoning_label(zoning["zoning"]))} <code>{esc(zoning["site_name"])}</code></td>'
                    f'<td colspan="{len(ZONING_COLUMNS)-1}"><em>not applicable: the EnergyPlus run did not succeed</em></td></tr>')
    body = f'<p>{benchmark}</p>'+table(rows, ZONING_COLUMNS, 'ea-listing ea-zonings')
    duplicates = [z for z in entry['zonings'] if z['succeeded'] and z.get('duplicate_of')]
    if duplicates:
        by_site = {z['site_name']: z for z in entry['zonings']}
        items = ''.join(f'<li>{esc(zoning_label(z["zoning"]))} → {esc(zoning_label(by_site[z["duplicate_of"]]["zoning"]) if z["duplicate_of"] in by_site else z["duplicate_of"])}</li>'
                        for z in duplicates)
        body += (f'<details><summary>{len(duplicates)} zonings write the same model as a listed one and are not shown</summary>'
                 f'<ul class="ea-duplicates">{items}</ul></details>')
    return f'<section class="ea-context"{page.claim(cell_anchor(entry))}{attrs}><h3>{esc(title)}</h3>{body}</section>'


def cells_body(page, entries, axes, threshold, more_toc=()):
    """The summary table and the per-cell sections of a set of cells, with the filter form."""
    columns = tuple(AXES[a] for a in axes)+SUMMARY_COLUMNS
    toc = [('recommended', 'Recommended zonings'), ('cells', 'Every zoning by cell'), *more_toc]
    body = [filter_form(entries, axes), contents(toc),
            section(page, 'recommended', 'Recommended zonings',
                    table(summary_rows(page, entries, axes, threshold), columns, 'ea-listing ea-recommendations')
                    + '<p class="ea-note">The coarsest zonings (fewest modelled zones) meeting the threshold; ties are all listed. '
                    'Errors are the test zoning against the reference: annual sensible load, hourly CV(RMSE) and NMBE, and the change of '
                    'conditioned floor area. A muted value belongs to a load the threshold does not judge; a dash is a value the runner '
                    'did not store; a flagged value carries the runner\'s own flag.</p>'),
            section(page, 'cells', 'Every zoning by cell', ''.join(cell_section(page, e, axes, threshold) for e in entries))]
    return ''.join(body)


def programs_table(page, entries):
    """The atlas programs of each program key, by vintage, linked to their catalogue pages."""
    vintages = sorted({e['vintage'] for e in entries})
    keys = {}
    for entry in entries:
        for key, ids in entry['programs'].items():
            keys.setdefault(key, {}).setdefault(entry['vintage'], set()).update(ids)
    rows = []
    for key in sorted(keys):
        cells = [esc(key)]
        for vintage in vintages:
            ids = sorted(keys[key].get(vintage, ()))
            cells.append('<br>'.join(page.link(i) for i in ids) if ids else NULL)
        rows.append(cells)
    return table(rows, ('Program key',)+tuple(vintages))


# Pages.

def kicker(page, drop, label):
    provenance = drop.provenance
    return (f'<p class="ea-kicker"><code>{esc(label)}</code> · geometric LOD study drop {esc(provenance.get("drop", ""))} · '
            f'atlas inputs release {esc(provenance.get("atlas_inputs", {}).get("release", ""))} · BEMGen '
            f'<code>{esc(str(provenance.get("bemgen", {}).get("report_commit", ""))[:12])}</code></p>')


def tally(entries):
    counts = {}
    for entry in entries:
        for pick in entry['recommended']:
            counts[zoning_label(pick['zoning'])] = counts.get(zoning_label(pick['zoning']), 0)+1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))


def slice_of(data, entries):
    ids = {e['id'] for e in entries}
    by_program = {p: [i for i in ids_ if i in ids] for p, ids_ in data['by_program'].items()}
    return {**data, 'entries': entries, 'by_program': {p: v for p, v in by_program.items() if v}}


def prototype_page(site, drop, prototype, url):
    entries = drop.entries(prototype)
    page = Page(site.links, url)
    name = prototype_name(prototype)
    threshold = drop.threshold
    axes = ('climate', 'vintage', 'orientation')
    descriptor = site.store.put(slice_of(drop.main, entries))
    buttons = json_buttons([(f'LOD recommendations {drop.main["version"]}, this prototype', f'lod-recommendations-{prototype_slug(prototype)}', descriptor)], page)
    with_pick = sum(1 for e in entries if e['recommended'])
    reference_zones = sorted({e['reference'].get('zone_count') for e in entries if e['reference'].get('zone_count') is not None})
    most = tally(entries)
    facts = [('Prototype', esc(prototype)), ('Cells', f'{len(entries)}: '+' × '.join(f'{len({axis_values(e)[a] for e in entries})} {AXES[a].lower()}s' for a in axes)),
             ('Cells with a recommended zoning', f'{with_pick} of {len(entries)}'),
             ('Reference zoning', esc(zoning_label(entries[0]['reference'].get('zoning', {}))) if entries else ''),
             ('Reference zones', ' to '.join(str(z) for z in (reference_zones[0], reference_zones[-1])) if len(reference_zones) > 1 else (str(reference_zones[0]) if reference_zones else '')),
             ('Most often recommended', f'{esc(most[0][0])} ({most[0][1]} of {len(entries)} cells)' if most else 'none')]
    trail = [(TITLE, URL), (name, url)]
    body = [crumbs(page, trail), kicker(page, drop, prototype), facts_html(facts), buttons,
            cells_body(page, entries, axes, threshold, [('programs', 'Atlas programs')]),
            section(page, 'programs', 'Atlas programs', programs_table(page, entries)
                    + '<p class="ea-note">The atlas programs each program key of the prototype takes, as the suite\'s saved inputs name them; '
                    f'the prototype\'s geometry and glazing are BEMGen\'s DOE record. <a href="{esc(page.rel(URL+"method/"))}">Method and caveats</a>.</p>')]
    site.summaries[url] = ' · '.join([name, prototype, 'zoning recommendations', ' '.join(sorted({e['climate_zone'] for e in entries})),
                                      ' '.join(sorted({e['vintage'] for e in entries}))])
    site.write(url+'index.md', markdown(f'{name} zoning', ''.join(body)))


def heat_transfer_page(site, drop, url):
    data = drop.ht
    entries = sorted(data['entries'], key=lambda e: (list(PROTOTYPES).index(e['prototype']) if e['prototype'] in PROTOTYPES else 99, cell_order(e)))
    page = Page(site.links, url)
    axes = ('prototype', 'climate')
    descriptor = site.store.put(data)
    buttons = json_buttons([(f'LOD recommendations {data["version"]}, heat-transfer sub-study', 'lod-recommendations-ht', descriptor)], page)
    failed = [(e, z) for e in entries for z in e['zonings'] if not z['succeeded']]
    with_pick = sum(1 for e in entries if e['recommended'])
    off = sum(1 for e in entries if any(p['zoning'].get('iwht') is False or p['zoning'].get('fht') is False for p in e['recommended']))
    facts = [('Cells', f'{len(entries)}: '+' × '.join(f'{len({axis_values(e)[a] for e in entries})} {AXES[a].lower()}s' for a in axes)
              + '; '+' · '.join(sorted({e['vintage'] for e in entries}))+' · '+' · '.join(sorted({orientation(e['orientation_degrees']) for e in entries}))),
             ('Zonings per cell', 'the main zonings × interior-wall heat transfer (IWHT) on or off × floor heat transfer (FHT) on or off'),
             ('Cells with a recommended zoning', f'{with_pick} of {len(entries)}'),
             ('Cells where a recommended zoning has IWHT or FHT off', f'{off} of {len(entries)}'),
             ('Zonings whose run did not succeed', f'{len(failed)} ({", ".join(sorted({prototype_name(e["prototype"]) for e, _ in failed}))})' if failed else '0')]
    trail = [(TITLE, URL), ('Heat-transfer sub-study', url)]
    body = [crumbs(page, trail), kicker(page, drop, 'R4 heat-transfer sub-study'), facts_html(facts), buttons,
            '<p>The same prototypes and threshold as the main matrix, in two climate zones, with the interior-wall and floor heat-transfer '
            'switches of the zoning varied. The reference keeps both on. A zoning whose EnergyPlus run did not succeed is listed as not '
            f'applicable and is never recommended; the cause is on the <a href="{esc(page.rel(URL+"method/"))}">method page</a>.</p>']
    body.append(cells_body(page, entries, axes, data['threshold']))
    site.summaries[url] = 'Heat-transfer sub-study · IWHT FHT · zoning recommendations · '+' '.join(sorted({e['climate_zone'] for e in entries}))
    site.write(url+'index.md', markdown('Heat-transfer sub-study', ''.join(body)))


def threshold_html(threshold):
    rows = [('Basis', esc(threshold.get('basis', ''))), ('Loads judged', ', '.join(esc(words(l)) for l in threshold.get('loads', []))),
            ('Annual error', f'|error| ≤ {threshold.get("annual_rel_err_pct", "")} %'),
            ('Hourly CV(RMSE)', f'≤ {threshold.get("cvrmse_pct", "")} %'), ('Hourly NMBE', f'|NMBE| ≤ {threshold.get("nmbe_pct", "")} %'),
            ('Conditioned floor area', f'|change| ≤ {threshold.get("conditioned_area_change_pct", "")} %'),
            ('Loads not judged', f'a load whose reference is below {threshold.get("min_reference_kwh_m2", "")} kWh/m² a year'),
            ('Owner choice', 'yes: the default of the report writer; a later drop may carry another' if threshold.get('owner_choice') else 'no')]
    return facts_html(rows)


def overview_page(site, drop, urls):
    page = Page(site.links, URL)
    main, provenance = drop.main, drop.provenance
    entries = main['entries']
    descriptors = [(f'LOD recommendations {main["version"]}, main matrix', 'lod-recommendations', site.store.put(main)),
                   ('Provenance sidecar', 'lod-recommendations-provenance', site.store.put(provenance))]
    if drop.ht:
        descriptors.insert(1, (f'LOD recommendations {drop.ht["version"]}, heat-transfer sub-study', 'lod-recommendations-ht', site.store.put(drop.ht)))
    buttons = json_buttons(descriptors, page)
    with_pick = sum(1 for e in entries if e['recommended'])
    rows = []
    for prototype in drop.prototypes():
        own = drop.entries(prototype)
        picks = tally(own)
        fewest = [p['zone_count'] for e in own for p in e['recommended']]
        reference = [e['reference'].get('zone_count') for e in own if e['reference'].get('zone_count') is not None]
        rows.append((f'<a href="{esc(page.rel(urls[prototype]))}">{esc(prototype_name(prototype))}</a>', str(len(own)),
                     str(sum(1 for e in own if e['recommended'])), esc(f'{picks[0][0]} ({picks[0][1]})') if picks else '<em>none</em>',
                     f'{min(fewest)} to {max(fewest)}' if fewest else NULL, f'{min(reference)} to {max(reference)}' if len(set(reference)) > 1 else (str(reference[0]) if reference else NULL)))
    overall = tally(entries)
    body = [
        f'<p class="ea-kicker">Geometric LOD study · drop {esc(provenance.get("drop", ""))} · {len(entries)} cells · '
        f'atlas inputs release {esc(provenance.get("atlas_inputs", {}).get("release", ""))}</p>',
        '<p>Which thermal zoning of a DOE prototype building is coarse enough to be cheap and fine enough to keep its ideal sensible heating '
        'and cooling loads within a stated error of the prototype\'s full zoning? For each prototype, climate zone, vintage and orientation '
        'the study simulated the prototype\'s own geometry as BEMGen writes it, zoned every room (the <strong>reference</strong>), and then the '
        'same building under each zoning simplification and floor stacker (the <strong>test sites</strong>) with geometry, atlas programs, '
        'envelope and weather fixed. Every test site is scored against its reference with the batch runner\'s paired metrics: the annual '
        'sensible heating and cooling error, the hourly CV(RMSE) and NMBE, the peak errors and the change of conditioned floor area. The '
        '<strong>recommended</strong> zoning of a cell is the coarsest one, by modelled zone count, that meets the threshold below; a cell '
        'where no zoning meets it says so.</p>',
        buttons, contents([('threshold', 'Threshold'), ('prototypes', 'Prototypes'), ('tally', 'Recommended zonings'), ('status', 'Status')]),
        section(page, 'threshold', 'Threshold', threshold_html(drop.threshold)),
        section(page, 'prototypes', 'Prototypes',
                table(rows, ('Prototype', 'Cells', 'With a recommended zoning', 'Most often recommended (cells)', 'Recommended zones', 'Reference zones'))
                + f'<p>A zoning meets the threshold in {with_pick} of {len(entries)} cells. Each prototype page lists every cell, the recommended '
                'zoning with its errors, every zoning\'s metrics and the atlas programs the prototype takes. '
                + (f'The <a href="{esc(page.rel(urls["ht"]))}">heat-transfer sub-study</a> varies the interior-wall and floor heat-transfer switches. ' if 'ht' in urls else '')
                + f'<a href="{esc(page.rel(URL+"method/"))}">Method and caveats</a>.</p>'),
        section(page, 'tally', 'Recommended zonings', table([(esc(label), str(count)) for label, count in overall], ('Zoning', 'Cells'))
                + '<p class="ea-note">Counts over every cell and tie of the main matrix.</p>'),
        section(page, 'status', 'Status', f'<p>{esc(provenance.get("status", ""))}</p>'
                + ('<ul>'+''.join(f'<li>{esc(item)}</li>' for item in provenance.get('pending', []))+'</ul>' if provenance.get('pending') else '')
                + f'<p class="ea-note">{esc(provenance.get("licence", ""))}.</p>'),
    ]
    site.summaries[URL] = 'Zoning recommendations · geometric LOD study · thermal zoning · '+' '.join(prototype_name(p) for p in drop.prototypes())
    site.write(URL+'index.md', markdown(TITLE, ''.join(body)))


def method_page(site, drop, urls):
    page = Page(site.links, URL+'method/')
    main, provenance = drop.main, drop.provenance
    entries = main['entries']
    threshold = drop.threshold
    simplifiers = sorted({(z['zoning'].get('simplifier') or '').split(' ')[0] for e in entries for z in e['zonings']} - {''})
    stackers = sorted({z['zoning'].get('stacker') for e in entries for z in e['zonings'] if z['zoning'].get('stacker')})
    depths = sorted({z['zoning']['perimeter_depth'] for e in entries for z in e['zonings'] if z['zoning'].get('perimeter_depth') is not None})
    per_cell = sorted({len(e['zonings']) for e in entries})
    fewer = sorted({prototype_name(e['prototype']) for e in entries if len(e['zonings']) < max(per_cell)})
    duplicates = sum(1 for e in entries for z in e['zonings'] if z['succeeded'] and z.get('duplicate_of'))
    tests = sum(len(e['zonings']) for e in entries)
    failed_main = sum(1 for e in entries for z in e['zonings'] if not z['succeeded'])
    ht_failed = [(e, z) for e in (drop.ht['entries'] if drop.ht else []) for z in e['zonings'] if not z['succeeded']]
    ht_failed_names = sorted({prototype_name(e['prototype']) for e, _ in ht_failed})
    ht_failed_labels = sorted({zoning_label(z['zoning']) for _, z in ht_failed} - {'zoning not recorded'})
    ht_failed_note = (f' ({", ".join(ht_failed_labels)})' if ht_failed_labels else
                      ' (the file carries no zoning fields for a site that did not run; the run plan, D-193, identifies them as the zonings that keep an '
                      'unconditioned elevator core or mechanical room as its own zone, No simplification, Semantic merge or Conditioned merge with Stack '
                      'or Stacked floor zone multiplier, with IWHT off and FHT on or off)')
    study = provenance.get('study', {})
    bemgen = provenance.get('bemgen', {})
    inputs = provenance.get('atlas_inputs', {})
    files = provenance.get('files', {})
    file_rows = [(esc(name), esc(f.get('label', '')), esc(f.get('suite', '')), esc(f.get('run', '')), str(f.get('entries', '')), f'<code>{esc(str(f.get("sha256", ""))[:12])}</code>')
                 for name, f in files.items()]
    zoning_rows = [(esc(words(s)), esc(SIMPLIFIERS.get(s, ''))) for s in simplifiers]
    stacker_rows = [(esc(words(s)), esc(STACKERS.get(s, ''))) for s in stackers]
    body = [
        crumbs(page, [(TITLE, URL), ('Method and caveats', URL+'method/')]),
        contents([('design', 'What was compared'), ('metrics', 'Metrics and threshold'), ('dedup', 'Deduplication'), ('limits', 'Limits and caveats'),
                  ('provenance', 'Provenance')]),
        section(page, 'design', 'What was compared',
                f'<p>{esc(study.get("design", ""))}</p>'
                '<p>The <strong>reference</strong> of a cell is the prototype\'s full zoning as BEMGen writes it: '
                f'{esc(zoning_label(entries[0]["reference"].get("zoning", {})) if entries else "")}, with interior-wall heat transfer (IWHT) and floor heat '
                'transfer (FHT) on. The <strong>test sites</strong> combine a zoning simplifier with a floor stacker:</p>'
                + table(zoning_rows, ('Simplifier', 'What it does'))
                + (f'<p>Perimeter core is run at {" and ".join(f"{d:g} m" for d in depths)} depth.</p>' if depths else '')
                + table(stacker_rows, ('Stacker', 'What it does'))
                + f'<p>The main matrix has {min(per_cell)} to {max(per_cell)} zonings per cell'
                + (f'; the cells of the {", ".join(fewer)} list fewer because a stacker or a perimeter depth does not apply to that prototype '
                   '(multiplied rooms, or a wing narrower than twice the perimeter depth)' if fewer else '') + '. Orientation is a cell axis and is not '
                'aggregated: the two orientations of one prototype, climate zone and vintage are two rows.</p>'),
        section(page, 'metrics', 'Metrics and threshold',
                '<p>Every value shown is the batch runner\'s own paired metric of a test site against its reference, as the report writer stored it; '
                'nothing is recomputed on this site. The annual error is the relative difference of annual ideal sensible heating or cooling; '
                'CV(RMSE) and NMBE are the hourly coefficient of variation of the root-mean-square error and the normalised mean bias error of '
                'ASHRAE Guideline 14; the peak error is the relative difference of the annual maximum hourly load; the area change is the change of '
                'conditioned floor area against the reference. The JSON files carry further metrics (P99 peaks, load-duration-curve errors, '
                'Kolmogorov–Smirnov distances, conditioned-temperature errors, zone-count ratios and a CPU-time ratio) that the pages do not show.</p>'
                + threshold_html(threshold)
                + '<p>A zoning meets the threshold when every judged load passes all three limits and the area limit holds; a missing metric of a '
                'judged load fails. The recommended zonings of a cell are those meeting it with the fewest modelled zones; ties are all listed.</p>'),
        section(page, 'dedup', 'Deduplication',
                '<p>Two test sites of one cell are duplicates when they have the same zone-geometry signature (each zone\'s multiplier and its floor '
                'polygons, vertices rounded to a millimetre, names left out) and the same annual ideal sensible heating and cooling within a relative '
                'tolerance of 10<sup>−9</sup>. The site kept is the first in zoning order (simplifier, join pieces, perimeter depth, stacker, IWHT, FHT); '
                f'a reference is never dropped. In the main matrix {duplicates:,} of {tests:,} test sites are duplicates of a listed zoning; each cell '
                'names them under its table.</p>'),
        section(page, 'limits', 'Limits and caveats', '<ul>'
                '<li><strong>Ideal loads.</strong> Heating and cooling are ideal-loads sensible demands; HVAC systems, service hot water and latent '
                'loads are outside the comparison. The errors say how a zoning changes the building\'s thermal demand, not its energy use.</li>'
                '<li><strong>Deterministic inputs.</strong> The prototypes\' own geometry, glazing, atlas programs with ruleset schedules, the atlas '
                '90.1 unified construction set and one TMY3 weather file per climate zone; no stochastic schedules, no holidays, no infiltration axis.</li>'
                '<li><strong>Coverage.</strong> The vintages are 90.1-2007 and 90.1-2019 (atlas release 2.0.0 has no 90.1-2004 folders); climate zone 7 '
                'is registered as 7A, the atlas label of International Falls. IECC sets are out of scope.</li>'
                + (f'<li><strong>Zonings that do not apply.</strong> Perimeter core and the single-zone stackers do not support multiplied rooms, and a '
                   f'perimeter depth needs a wing at least twice as deep, so the {", ".join(fewer)} cells list fewer zonings.</li>' if fewer else '')
                + (f'<li><strong>Runs that did not succeed.</strong> In the heat-transfer sub-study {len(ht_failed)} zonings of the {", ".join(ht_failed_names)}'
                   f'{ht_failed_note} did not complete: EnergyPlus stops in warm-up with a zone temperature far out of bounds in an '
                   'unconditioned elevator core or mechanical room whose program carries a large equipment gain and whose interior walls are '
                   'adiabatic with IWHT off. They are reported as not applicable, never recommended, and not changed; whether the IWHT-off setting '
                   'should exclude such zonings is for the owner.</li>' if ht_failed else '')
                + f'<li><strong>Main matrix runs.</strong> {failed_main} of {tests:,} test sites did not succeed.</li>'
                '<li><strong>Timing.</strong> The CPU-time ratios in the JSON come from runs 20 at a time on a shared machine and are not runtime '
                'results; the serial timing pass (R5) is pending and will arrive with the next drop.</li>'
                '<li><strong>Threshold.</strong> The threshold is the report writer\'s default and an owner choice; the R6 report may change it, and a '
                'later drop then carries the new one in every file.</li>'
                '<li><strong>Not a population statement.</strong> The cells are the prototypes at their own dimensions; nothing here weights them by '
                'stock frequency.</li></ul>'),
        section(page, 'provenance', 'Provenance',
                facts_html([('Study', esc(study.get('title', ''))+(f' ({esc(study.get("name", ""))})' if study.get('name') else '')),
                            ('Run plan', f'<code>{esc(study.get("plan", ""))}</code> in BEMGen, decision {esc(study.get("decision", ""))}'),
                            ('BEMGen', f'<a href="{esc(bemgen.get("repository", "#"))}">{esc(bemgen.get("repository", ""))}</a>: report writer '
                                       f'<code>{esc(bemgen.get("writer", ""))}</code> at <code>{esc(str(bemgen.get("report_commit", ""))[:12])}</code>; '
                                       f'runs with the writer at <code>{esc(str(bemgen.get("run_commit", "")))}</code>; EnergyPlus {esc(bemgen.get("energyplus", ""))}'),
                            ('Atlas inputs', f'release {esc(inputs.get("release", ""))} at <code>{esc(str(inputs.get("commit", ""))[:12])}</code>, '
                                             f'{esc(inputs.get("program_version", ""))} programs, {esc(inputs.get("construction_representation", ""))} constructions'),
                            ('Schema', f'<code>{esc(bemgen.get("schema_copy", ""))}</code>, a copy of BEMGen\'s <code>{esc(bemgen.get("schema", ""))}</code>'),
                            ('Repository files', f'<code>data/lod-recommendations/v1/</code>; drop {esc(provenance.get("drop", ""))}'),
                            ('Licence', esc(provenance.get('licence', '')))])
                + table(file_rows, ('File', 'Stage', 'Suite', 'Run', 'Cells', 'SHA-256'))
                + '<p class="ea-note">A later consolidated drop replaces the files in place with the same layout; the pages are regenerated from '
                'them at the next site build (ADR 0050).</p>'),
    ]
    site.summaries[URL+'method/'] = 'Method and caveats · zoning recommendations · geometric LOD study · threshold · deduplication · provenance'
    site.write(URL+'method/index.md', markdown('Method and caveats', ''.join(body)))


def write_zoning(site, folder=DROP):
    """Every zoning page into the site; returns the manifest entry (pages and counts) and fills `site.zoning_of`."""
    drop = Drop(folder)
    urls = {p: f'{URL}{prototype_slug(p)}/' for p in drop.prototypes()}
    if len(set(urls.values())) != len(urls):
        raise ValueError('Two prototypes share one page path')
    if drop.ht:
        urls['ht'] = URL+'heat-transfer/'
    for program, ids in drop.main['by_program'].items():
        prototypes = sorted({i.split('|')[0] for i in ids})
        site.zoning_of[program] = [(prototype_name(p), urls[p]) for p in prototypes if p in urls]
    for prototype in drop.prototypes():
        prototype_page(site, drop, prototype, urls[prototype])
    if drop.ht:
        heat_transfer_page(site, drop, urls['ht'])
    overview_page(site, drop, urls)
    method_page(site, drop, urls)
    pages = {'overview': URL, 'method': URL+'method/', **{f'prototype:{p}': u for p, u in urls.items() if p != 'ht'},
             **({'heat_transfer': urls['ht']} if 'ht' in urls else {})}
    return {'drop': drop.provenance.get('drop'), 'pages': pages, 'cells': len(drop.main['entries']),
            'cells_with_recommendation': sum(1 for e in drop.main['entries'] if e['recommended']),
            'ht_cells': len(drop.ht['entries']) if drop.ht else 0}
