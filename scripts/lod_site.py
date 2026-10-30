"""The zoning-recommendation pages of the site (ADR 0050): the geometric LOD study's data drop.

Reads `data/lod-recommendations/v1/`: the BEMGen report writer's `lod-recommendations.json`
files (schema `schemas/lod-recommendations-v1.schema.json`) and the provenance sidecar, and
writes into the MkDocs input tree, like the suite pages (`scripts.suite_site`):

- `zoning/`: the overview, what the study measured, the threshold, every prototype;
- `zoning/<prototype>/`: one page per prototype: the robust zoning of each climate zone ×
  vintage over both orientations (ADR 0050 section 6), then one row per climate zone ×
  vintage × orientation with the recommended zoning and its errors, then every zoning of
  every cell;
- `zoning/heat-transfer/`: the interior-wall and floor heat-transfer sub-study;
- `zoning/method/`: method, the cost protocol, limits, reading cautions and provenance.

Every table is generated from the files; no value is computed here beyond counts, the robust
rule's choice among the writer's verdicts, the worse of two stored errors and a median of the
stored cost ratios (`ROBUST_RULE`, written into each prototype's JSON as a labelled block). The loader
admits fields a later drop adds: drop 2 (schema 1.1.0) added the serial costs of the R5 timing
pass as a `cost` object on timed references and zonings and a top-level `timing` block, which
the pages show as cost columns and a cost section; a file without them (1.0.0) renders as before.
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

    @property
    def timing(self):
        """The serial timing pass of the main matrix (since schema 1.1.0), or None."""
        return self.main.get('timing')

    @property
    def costed(self):
        return bool(self.timing) or any(timed(e) for e in self.main['entries'])

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


def writer_label(label):
    """The report writer's zoning label (`Conditioned Merge + Stack`) in the pages' case (`Conditioned merge + Stack`)."""
    return ' + '.join(p[:1].upper()+p[1:].lower() for p in str(label).split(' + '))


def pct(value, digits=1):
    return NULL if value is None else f'{value:,.{digits}f} %'


def change(ratio, digits=0):
    """A ratio against an earlier value as a signed percentage change: 1.151 → `+15 %`."""
    return NULL if ratio is None else f'{(ratio-1)*100:+,.{digits}f} %'


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


# Costs (the serial timing pass, since schema 1.1.0).

COST_COLUMNS = ('CPU ratio', 'Wall ratio', 'Memory ratio')
COST_KEYS = ('cpu_time_ratio', 'wall_clock_ratio', 'memory_peak_commit_ratio')
NOT_TIMED = f'<td colspan="{len(COST_COLUMNS)}" class="ea-unjudged ea-untimed"><em>not timed</em></td>'


def timed(entry):
    """Whether the cell's reference was timed in the serial pass (its `cost` object is present)."""
    return bool(entry['reference'].get('cost'))


def cost_cells(zoning):
    """The three ratio cells of a zoning's serial cost (test site over reference), or one `not timed` cell."""
    cost = zoning.get('cost') or {}
    if not any(cost.get(k) is not None for k in COST_KEYS):
        return NOT_TIMED
    return ''.join(f'<td>{num(cost.get(k), 3)}</td>' for k in COST_KEYS)


def cost_sentence(entry):
    """The reference's serial cost in words, or that the cell was not timed."""
    cost = entry['reference'].get('cost')
    if not cost:
        return ' This cell was not timed in the serial pass (R5).'
    return (f' Serial cost (R5): processor time {num(cost.get("cpu_time_s"))} s, wall clock {num(cost.get("wall_clock_s"))} s, peak committed '
            f'memory {num(cost.get("memory_peak_commit_mib"), 0)} MiB, each the median of {cost.get("repeats", "")} repeats (processor-time '
            f'CV {pct(cost.get("cpu_time_cv_pct"))}); a zoning\'s ratios are its own medians over the reference\'s.')


# Cells.

def kept(entry):
    """The zonings in the metric table: succeeded and not a duplicate, fewest zones first."""
    rows = [z for z in entry['zonings'] if z['succeeded'] and not z.get('duplicate_of')]
    return sorted(rows, key=lambda z: (z['zone_count'] if z['zone_count'] is not None else 10**6, zoning_label(z['zoning'])))


def cell_anchor(entry):
    return 'cell-'+entry['id']


# Robust across orientations (ADR 0050 section 6): an atlas rule over the writer's per-zoning verdicts.

ZONING_KEYS = ('simplifier', 'join_pieces', 'perimeter_depth', 'stacker', 'iwht', 'fht')  # the study's zoning order
ERROR_KEYS = tuple(f'sensible_{load}_{m}' for m in ('kwh_rel_err_pct', 'cvrmse_pct', 'nmbe_pct') for load in ('heating', 'cooling'))
AREA_KEY = 'conditioned_area_change_pct'
ROBUST_RULE = ('For each prototype, climate zone and vintage, the robust zoning is the coarsest (fewest modelled zones) that meets the threshold '
               'at every orientation of the cell pair, by the writer\'s own verdict on each zoning at each orientation; a duplicate never meets, '
               'as the writer lists it. Ties at the fewest zones go to a zoning both orientations recommend, else to the first in the study\'s '
               'zoning order (simplifier, join pieces, perimeter depth, stacker, IWHT, FHT); the tied zonings are named. The errors reported are '
               'the worse of the orientations\' values for each metric, so the row is a bound, not a mean; the cost ratios are the medians '
               'over the timed sites of that zoning in the pair.')


def zoning_key(zoning):
    return tuple(zoning.get(k) for k in ZONING_KEYS)


def zoning_order(zoning):
    """The writer's canonical order of a zoning: the text of each field, simplifier first (its deduplication keeps the first)."""
    return tuple('' if zoning.get(k) is None else str(zoning[k]) for k in ZONING_KEYS)


def pair_key(entry):
    return (entry['prototype'], entry['climate_zone'], entry['vintage'])


def pair_id(key):
    return 'pair:'+'|'.join(str(k) for k in key)


def pairs(entries):
    """The cell pairs of a set of entries: (prototype, climate zone, vintage) → {orientation: entry}, in cell order."""
    groups = {}
    for entry in sorted(entries, key=cell_order):
        groups.setdefault(pair_key(entry), {})[entry['orientation_degrees']] = entry
    return groups


def worst(name, picks):
    """The orientation whose value of `name` has the larger magnitude, as (entry, zoning row), or the first with none stored."""
    valued = [(e, z) for e, z in picks if (z.get('metrics', {}).get(name) if name != AREA_KEY else z.get(AREA_KEY)) is not None]
    if not valued:
        return picks[0]
    return max(valued, key=lambda p: abs(p[1]['metrics'][name] if name != AREA_KEY else p[1][AREA_KEY]))


def median(values):
    values = sorted(values)
    if not values:
        return None
    middle = len(values)//2
    return values[middle] if len(values) % 2 else (values[middle-1]+values[middle])/2


def robust_cost(picks):
    """The robust zoning's cost ratios: the median over the pair's timed sites of that zoning, by key; empty when none is timed."""
    cost = {}
    for key in COST_KEYS:
        values = [z['cost'][key] for _, z in picks if z.get('cost') and z['cost'].get(key) is not None]
        if values:
            cost[key] = median(values)
    return cost


def robust(pair):
    """The robust recommendation of a cell pair ({orientation: entry}), by `ROBUST_RULE`.

    Returns a dict: `status` is `robust` (a zoning meets the threshold at every orientation), `none` (none does) or `single` (one
    orientation only, so no pair); with a pick, `zoning`, `zone_count`, `picks` ([(entry, zoning row)] by orientation), `ties`
    (the other zonings with the fewest zones that are kept at every orientation), `same_pick` (every orientation recommends it)
    and `cost`; always `entries` and `per_orientation` ({orientation: the cell's recommended zonings}).
    """
    orientations = sorted(pair)
    entries = [pair[o] for o in orientations]
    result = {'orientations': orientations, 'entries': entries,
              'per_orientation': {o: [p['zoning'] for p in pair[o]['recommended']] for o in orientations}}
    if len(orientations) < 2:
        return {**result, 'status': 'single'}
    rows = [{zoning_key(z['zoning']): z for z in e['zonings']} for e in entries]
    recommended = [{zoning_key(p['zoning']) for p in e['recommended']} for e in entries]
    candidates = [k for k in rows[0] if all(k in r and r[k].get('succeeded') and r[k].get('meets_threshold') for r in rows)]
    if not candidates:
        return {**result, 'status': 'none'}

    def zones(key):
        return max((r[key]['zone_count'] if r[key].get('zone_count') is not None else 10**6) for r in rows)

    def order(key):
        return (zones(key), 0 if all(key in r for r in recommended) else 1, zoning_order(rows[0][key]['zoning']))

    pick = min(candidates, key=order)
    picks = [(e, r[pick]) for e, r in zip(entries, rows)]
    ties = sorted((k for k in candidates if k != pick and zones(k) == zones(pick) and not any(r[k].get('duplicate_of') for r in rows)),
                  key=order)
    return {**result, 'status': 'robust', 'key': pick, 'zoning': rows[0][pick]['zoning'], 'zone_count': zones(pick) if zones(pick) < 10**6 else None,
            'picks': picks, 'ties': [rows[0][k]['zoning'] for k in ties], 'same_pick': all(pick in r for r in recommended),
            'cost': robust_cost(picks)}


def robust_results(entries):
    """The robust result of every cell pair of `entries`, keyed by pair, in cell order."""
    return {key: robust(pair) for key, pair in pairs(entries).items()}


def robust_block(results):
    """The robust results as JSON for the prototype slice: labelled as computed by the site, not by the report writer."""
    pairs_json = []
    for key, r in results.items():
        item = {'prototype': key[0], 'climate_zone': key[1], 'vintage': key[2], 'orientations': r['orientations'], 'status': r['status'],
                'cells': [e['id'] for e in r['entries']],
                'recommended_per_orientation': {f'{o:g}': [zoning_label(z) for z in zs] for o, zs in r['per_orientation'].items()}}
        if r['status'] == 'robust':
            item.update({'zoning': r['zoning'], 'label': zoning_label(r['zoning']), 'zone_count': r['zone_count'],
                         'site_names': {f'{e["orientation_degrees"]:g}': z['site_name'] for e, z in r['picks']},
                         'recommended_at_every_orientation': r['same_pick'], 'ties': [zoning_label(z) for z in r['ties']],
                         'worst': {name: {'value': (z.get('metrics', {}).get(name) if name != AREA_KEY else z.get(AREA_KEY)),
                                          'orientation': e['orientation_degrees']} for name in ERROR_KEYS+(AREA_KEY,) for e, z in [worst(name, r['picks'])]},
                         'cost': r['cost'] or None})
        pairs_json.append(item)
    return {'rule': ROBUST_RULE, 'computed_by': 'scripts/lod_site.py at site build, from the verdicts in this file (ADR 0050 section 6); '
                                                'not a report-writer field', 'pairs': pairs_json}


def tally_robust(results):
    counts = {}
    for r in results.values():
        if r['status'] == 'robust':
            label = zoning_label(r['zoning'])
            counts[label] = counts.get(label, 0)+1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))


ROBUST_COLUMNS = ('Robust zoning', 'Zones', 'Heating error %', 'Cooling error %', 'Heating CV(RMSE) %', 'Cooling CV(RMSE) %',
                  'Heating NMBE %', 'Cooling NMBE %', 'Area change %')


def orientation_picks(page, r):
    """`0°: X (2 zones) · 45°: none`, each orientation linked to its cell."""
    parts = []
    for entry in r['entries']:
        link = f'<a href="#{esc(anchor(cell_anchor(entry)))}">{esc(orientation(entry["orientation_degrees"]))}</a>'
        picks = entry['recommended']
        text = ', '.join(f'{esc(zoning_label(p["zoning"]))} ({num(p.get("zone_count"), 0)} zone{"" if p.get("zone_count") == 1 else "s"})'
                         for p in picks) if picks else '<em>none</em>'
        parts.append(f'{link}: {text}')
    return ' · '.join(parts)


def robust_rows(page, results, threshold, costed=False):
    """One row per cell pair: the robust zoning with the worse of the orientations' errors, or why there is none."""
    rows = []
    span = len(ROBUST_COLUMNS)+(len(COST_COLUMNS) if costed else 0)
    for key, r in results.items():
        _, climate, vintage = key
        attrs = f' data-context="{esc(pair_id(key))}" data-climate="{esc(climate)}" data-vintage="{esc(vintage)}" data-across="orientation"'
        lead = f'<td>{esc(climate)}</td><td>{esc(vintage)}</td>'
        if r['status'] == 'single':
            rows.append(f'<tr class="ea-robust"{attrs}>{lead}<td colspan="{span+1}"><em>one orientation only '
                        f'({", ".join(orientation(o) for o in r["orientations"])}): no pair to judge</em></td></tr>')
            continue
        if r['status'] == 'none':
            rows.append(f'<tr class="ea-robust"{attrs}>{lead}<td colspan="{span}"><em>none meets the threshold at both orientations</em></td>'
                        f'<td>{orientation_picks(page, r)}</td></tr>')
            continue
        label = esc(zoning_label(r['zoning']))
        if r['ties']:
            label += f' <span class="ea-ties">(tie: {esc(", ".join(zoning_label(z) for z in r["ties"]))})</span>'
        cells = [label, num(r['zone_count'], 0)]
        for name in ERROR_KEYS:
            entry, zoning = worst(name, r['picks'])
            cells.append(metric(zoning, name, entry, threshold))
        cells.append(num(worst(AREA_KEY, r['picks'])[1].get(AREA_KEY), 2))
        basis = ('recommended at both orientations' if r['same_pick'] else orientation_picks(page, r))
        rows.append(f'<tr class="ea-robust ea-recommended"{attrs}>{lead}'+''.join(f'<td>{c}</td>' for c in cells)
                    + (cost_cells({'cost': r['cost']}) if costed else '')+f'<td>{basis}</td></tr>')
    return rows


def robust_body(page, results, threshold, costed=False):
    """The robust summary table of a prototype page with its note."""
    columns = ('Climate zone', 'Vintage')+ROBUST_COLUMNS+(COST_COLUMNS if costed else ())+('Per orientation',)
    robust_pairs = sum(1 for r in results.values() if r['status'] == 'robust')
    judged_pairs = sum(1 for r in results.values() if r['status'] != 'single')
    orientations = sorted({o for r in results.values() for o in r['orientations']})
    cost_note = (' The cost ratios are the median over the timed sites of the robust zoning in the pair (in this drop one orientation at most '
                 'is timed, so the ratio is that site\'s); <em>not timed</em> where none is.' if costed else '')
    return (f'<p>Robust across orientations in <strong>{robust_pairs} of {judged_pairs}</strong> cell pairs '
            f'({" and ".join(orientation(o) for o in orientations)}).</p>'
            + table(robust_rows(page, results, threshold, costed), columns, 'ea-listing ea-robust')
            + f'<p class="ea-note">{esc(ROBUST_RULE)} Where both orientations recommend the same zoning it is the robust one. A pair where no '
            'zoning meets the threshold at both orientations says so and names each orientation\'s own recommendation; the per-orientation '
            f'rows below stay the reading for one orientation.{cost_note} <a href="{esc(page.rel(URL+"method/#section-robust"))}">The rule and '
            'its limits</a>.</p>')


def summary_rows(page, entries, axes, threshold, costed=False):
    """One row per recommended zoning of each cell (ties repeat the cell), or one row saying none meets the threshold.

    With `costed` (the document carries the serial timing pass) each row ends with the zoning's cost ratios, or `not timed`.
    """
    rows = []
    span = len(SUMMARY_COLUMNS)-3+(len(COST_COLUMNS) if costed else 0)
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
                        + f'<td colspan="{span}"><em>none meets the threshold</em></td></tr>')
            continue
        for pick in recommended:
            zoning = by_site.get(pick['site_name'], {'metrics': {}, 'flags': {}, 'conditioned_area_change_pct': None})
            cells = lead+[esc(zoning_label(pick['zoning'])), num(pick.get('zone_count'), 0)]
            cells += [metric(zoning, f'sensible_{load}_{m}', entry, threshold) for m in ('kwh_rel_err_pct', 'cvrmse_pct', 'nmbe_pct') for load in ('heating', 'cooling')]
            cells.append(num(zoning.get('conditioned_area_change_pct'), 2))
            rows.append(f'<tr class="ea-recommended" data-context="{esc(entry["id"])}"{attrs}>'+''.join(f'<td>{c}</td>' for c in cells)
                        + (cost_cells(zoning) if costed else '')+'</tr>')
    return rows


SUMMARY_COLUMNS = ('Reference zones', 'Heating kWh/m²', 'Cooling kWh/m²', 'Recommended zoning', 'Zones', 'Heating error %', 'Cooling error %',
                   'Heating CV(RMSE) %', 'Cooling CV(RMSE) %', 'Heating NMBE %', 'Cooling NMBE %', 'Area change %')
ZONING_COLUMNS = ('Zoning', 'Zones', 'Area change %', 'Heating error %', 'Cooling error %', 'Heating CV(RMSE) %', 'Cooling CV(RMSE) %',
                  'Heating NMBE %', 'Cooling NMBE %', 'Peak heating error %', 'Peak cooling error %', 'Meets the threshold')


def cell_section(page, entry, axes, threshold, costed=False):
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
    with_cost = costed and timed(entry)  # the cost columns appear in the timed cells only; an untimed cell says so in the sentence
    if costed:
        benchmark += cost_sentence(entry)
    columns = ZONING_COLUMNS[:-1]+COST_COLUMNS+ZONING_COLUMNS[-1:] if with_cost else ZONING_COLUMNS
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
        klass = ' class="ea-recommended"' if zoning['site_name'] in recommended else ''
        rows.append(f'<tr{klass}>'+''.join(f'<td>{c}</td>' for c in cells)+(cost_cells(zoning) if with_cost else '')+f'<td>{verdict}</td></tr>')
    failed = [z for z in entry['zonings'] if not z['succeeded']]
    for zoning in failed:
        rows.append(f'<tr class="ea-failed"><td>{esc(zoning_label(zoning["zoning"]))} <code>{esc(zoning["site_name"])}</code></td>'
                    f'<td colspan="{len(columns)-1}"><em>not applicable: the EnergyPlus run did not succeed</em></td></tr>')
    body = f'<p>{benchmark}</p>'+table(rows, columns, 'ea-listing ea-zonings')
    duplicates = [z for z in entry['zonings'] if z['succeeded'] and z.get('duplicate_of')]
    if duplicates:
        by_site = {z['site_name']: z for z in entry['zonings']}
        items = ''.join(f'<li>{esc(zoning_label(z["zoning"]))} → {esc(zoning_label(by_site[z["duplicate_of"]]["zoning"]) if z["duplicate_of"] in by_site else z["duplicate_of"])}</li>'
                        for z in duplicates)
        body += (f'<details><summary>{len(duplicates)} zonings write the same model as a listed one and are not shown</summary>'
                 f'<ul class="ea-duplicates">{items}</ul></details>')
    return f'<section class="ea-context"{page.claim(cell_anchor(entry))}{attrs}><h3>{esc(title)}</h3>{body}</section>'


def paired(entries):
    """Whether the cells span two or more orientations, so the robust rule has pairs to judge."""
    return len({e['orientation_degrees'] for e in entries}) > 1


def cells_body(page, entries, axes, threshold, more_toc=(), costed=False, results=None):
    """The summary table and the per-cell sections of a set of cells, with the filter form; the robust table first where there are pairs."""
    columns = tuple(AXES[a] for a in axes)+SUMMARY_COLUMNS+(COST_COLUMNS if costed else ())
    toc = [*([('robust', 'Robust across orientations')] if results else []), ('recommended', 'Recommended zonings'), ('cells', 'Every zoning by cell'), *more_toc]
    cost_note = (' The cost ratios are the serial timing pass (R5): the zoning\'s processor time, wall clock and peak committed memory over '
                 'its reference\'s, each the median of three repeats; <em>not timed</em> marks a cell outside the 12 timed ones (the medium '
                 f'office and the primary school were not timed). <a href="{esc(page.rel(URL+"method/#section-cost"))}">Cost protocol</a>.'
                 if costed else '')
    body = [filter_form(entries, axes), contents(toc),
            *([section(page, 'robust', 'Robust across orientations', robust_body(page, results, threshold, costed))] if results else []),
            section(page, 'recommended', 'Recommended zonings',
                    table(summary_rows(page, entries, axes, threshold, costed), columns, 'ea-listing ea-recommendations')
                    + '<p class="ea-note">The coarsest zonings (fewest modelled zones) meeting the threshold; ties are all listed. '
                    'Errors are the test zoning against the reference: annual sensible load, hourly CV(RMSE) and NMBE, and the change of '
                    'conditioned floor area. A muted value belongs to a load the threshold does not judge; a dash is a value the runner '
                    'did not store; a flagged value carries the runner\'s own flag.'+cost_note+'</p>'),
            section(page, 'cells', 'Every zoning by cell', ''.join(cell_section(page, e, axes, threshold, costed) for e in entries))]
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
    results = robust_results(entries) if paired(entries) else None
    slice_json = slice_of(drop.main, entries)
    if results:
        slice_json['robust'] = robust_block(results)
    descriptor = site.store.put(slice_json)
    buttons = json_buttons([(f'LOD recommendations {drop.main["version"]}, this prototype', f'lod-recommendations-{prototype_slug(prototype)}', descriptor)], page)
    with_pick = sum(1 for e in entries if e['recommended'])
    reference_zones = sorted({e['reference'].get('zone_count') for e in entries if e['reference'].get('zone_count') is not None})
    most = tally(entries)
    robust_most = tally_robust(results) if results else []
    timed_cells = sum(1 for e in entries if timed(e))
    facts = [('Prototype', esc(prototype)), ('Cells', f'{len(entries)}: '+' × '.join(f'{len({axis_values(e)[a] for e in entries})} {AXES[a].lower()}s' for a in axes)),
             ('Cells with a recommended zoning', f'{with_pick} of {len(entries)}'),
             ('Robust across orientations', f'{sum(1 for r in results.values() if r["status"] == "robust")} of {len(results)} cell pairs'
                                            + (f': {esc(robust_most[0][0])} ({robust_most[0][1]})' if robust_most else '') if results else ''),
             ('Reference zoning', esc(zoning_label(entries[0]['reference'].get('zoning', {}))) if entries else ''),
             ('Reference zones', ' to '.join(str(z) for z in (reference_zones[0], reference_zones[-1])) if len(reference_zones) > 1 else (str(reference_zones[0]) if reference_zones else '')),
             ('Most often recommended', f'{esc(most[0][0])} ({most[0][1]} of {len(entries)} cells)' if most else 'none')]
    if drop.costed:
        facts.append(('Serial cost (R5)', f'timed in {timed_cells} of {len(entries)} cells ('+', '.join(
            ' '.join(axis_text(a, axis_values(e)[a]) for a in axes) for e in entries if timed(e))+')' if timed_cells else
            'not timed: the prototype is not among the 12 timed cells of the serial pass'))
    trail = [(TITLE, URL), (name, url)]
    body = [crumbs(page, trail), kicker(page, drop, prototype), facts_html(facts), buttons,
            cells_body(page, entries, axes, threshold, [('programs', 'Atlas programs')], drop.costed, results),
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
            'switches of the zoning varied. The reference keeps both on. A zoning whose EnergyPlus run did not succeed is not applicable in '
            'its cell: it is listed as such, never recommended, and the cell\'s recommendation comes from the zonings that ran (D-201); the '
            f'cause is on the <a href="{esc(page.rel(URL+"method/"))}">method page</a>.</p>'
            '<p class="ea-note">Read a recommendation with a switch off with care: where a zoning has no surface between zones of the kind '
            'the switch pairs (one zone, or one storey for FHT), its on and off settings write the same model, and deduplication keeps the '
            'first in zoning order, which lists off before on, so the kept and recommended site carries <em>off</em> although the setting '
            'changed nothing. Elsewhere an off setting is a tie with the same zoning with both on. The cell\'s duplicate list names the '
            f'twins. <a href="{esc(page.rel(URL+"method/#section-cautions"))}">Reading cautions</a>.</p>']
    body.append(cells_body(page, entries, axes, data['threshold'], costed=bool(data.get('timing')) or any(timed(e) for e in entries)))
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


def bemgen_link(provenance, path):
    """A BEMGen repository path as a link to the file at the report writer's commit, the path shown as code."""
    bemgen = provenance.get('bemgen', {})
    route = 'tree' if path.endswith('/') else 'blob'  # a folder, or a file
    href = f'{bemgen.get("repository", "").rstrip("/")}/{route}/{bemgen.get("report_commit", "")}/{path}'
    return f'<a href="{esc(href)}"><code>{esc(path)}</code></a>'


def stage_rows(provenance):
    """The stages of the sidecar: stage, suite, run, BEMGen build and gate verdict."""
    rows = []
    for stage in provenance.get('stages', {}).values():
        rows.append((esc(stage.get('stage', '')), esc(stage.get('suite') or '') or NULL, esc(stage.get('run') or '') or NULL,
                     f'<code>{esc(str(stage.get("bemgen", "")))}</code>' if stage.get('bemgen') else NULL, esc(stage.get('gate', ''))))
    return rows


def cost_section(page, drop):
    """The overview's cost section: the serial pass in brief and the writer's medians by prototype and by zoning."""
    timing = drop.timing or {}
    gate = timing.get('gate', {})
    recheck = timing.get('recheck') or {}
    cells = {e['id'] for e in drop.main['entries'] if timed(e)}
    columns = ('Test sites', 'CPU ratio', 'Wall ratio', 'Memory ratio', 'CPU median s', 'CPU CV median %')
    by_prototype = {str(r.get('label')): r for r in timing.get('by_prototype', [])}
    rows = []
    for prototype in drop.prototypes():
        r = by_prototype.get(prototype)
        if r:
            rows.append((esc(prototype_name(prototype)), str(r.get('sites', '')), num(r.get('cpu_ratio'), 3), num(r.get('wall_ratio'), 3),
                         num(r.get('commit_ratio'), 3), num(r.get('cpu_s')), num(r.get('cv_median_pct'))))
        else:
            rows.append(f'<tr><td>{esc(prototype_name(prototype))}</td><td colspan="{len(columns)}" class="ea-unjudged ea-untimed"><em>not timed</em></td></tr>')
    zoning_rows = [(esc(writer_label(r.get('label'))), str(r.get('sites', '')), num(r.get('cpu_ratio'), 3), num(r.get('wall_ratio'), 3),
                    num(r.get('commit_ratio'), 3), num(r.get('cpu_s')), num(r.get('cv_median_pct'))) for r in timing.get('by_zoning', [])]
    facts = [('Timed', f'{timing.get("timed_sites", "")} sites of {len(cells)} cells ({len(timing.get("test_cases", []))} test cases of the serial pass), '
                       f'{len(timing.get("timed_prototypes", []))} prototypes; not timed: '
                       + ', '.join(prototype_name(p) for p in timing.get('untimed_prototypes', []))),
             ('Protocol', esc(timing.get('protocol', ''))),
             ('Statistic', 'a site\'s cost is the median of its repeats; its ratio is that median over its reference\'s; a zoning\'s or a prototype\'s cost '
                           'is the median of its test sites\' ratios'),
             ('Gate', f'processor-time CV per site below {gate.get("limit_pct", "")} %: {gate.get("pass", "")} of {gate.get("sites", "")} sites pass '
                      f'(median {pct(gate.get("median_pct"))}, largest {pct(gate.get("max_pct"))}); <strong>{esc(gate.get("verdict", ""))}</strong>'),
             ('Repeat check', f'{recheck.get("sites", "")} long sites timed again: {recheck.get("miss", "")} at or above the gate (largest CV '
                              f'{pct(recheck.get("cv_max_pct"))}); absolute times {change(recheck.get("median_vs_r5"))} against the pass, the test '
                              f'sites\' ratios {change(recheck.get("ratio_vs_r5_min"))} to {change(recheck.get("ratio_vs_r5_max"))} '
                              f'(median {change(recheck.get("ratio_vs_r5_median"), 1)})' if recheck else '')]
    return (facts_html(facts)
            + '<p>Costs are the serial timing pass (R5): one EnergyPlus at a time, three repeats, on an otherwise idle machine. They are '
            'reported as medians, since the gate was not met and a per-site ratio is reproducible to about ±15 % between sessions; the '
            'medians by prototype and by zoning below are the figures to quote, and the per-cell ratios on the prototype pages show the '
            f'spread. <a href="{esc(page.rel(URL+"method/#section-cost"))}">Cost protocol</a>.</p>'
            + '<h3>By prototype</h3>'+table(rows, ('Prototype',)+columns, 'ea-listing ea-costs')
            + '<h3>By zoning</h3>'+table(zoning_rows, ('Zoning',)+columns, 'ea-listing ea-costs')
            + '<p class="ea-note">The report writer\'s medians over the timed test sites of each prototype and zoning: the ratios of processor '
            'time, wall clock and peak committed memory to the reference, the median processor time in seconds and the median per-site CV. '
            'Peak committed memory hardly changes because EnergyPlus\'s own floor dominates; the saving in time follows the zone count only '
            'for large models, since a fixed start-up dominates the small single-storey prototypes.</p>')


def status_section(page, drop):
    provenance = drop.provenance
    study = provenance.get('study', {})
    pending = provenance.get('pending', [])
    links = [(f'Study report (R6)', study.get('report')), ('Methodology', study.get('methodology')), ('Run plan', study.get('plan')),
             ('Results', study.get('results'))]
    items = ''.join(f'<li>{esc(label)}: {bemgen_link(provenance, path)} in BEMGen</li>' for label, path in links if path)
    body = f'<p>{esc(provenance.get("status", ""))}</p>'
    body += '<ul>'+''.join(f'<li>{esc(item)}</li>' for item in pending)+'</ul>' if pending else '<p>Nothing is pending.</p>'
    if items:
        body += f'<ul class="ea-links">{items}</ul>'
    if provenance.get('stages'):
        body += table(stage_rows(provenance), ('Stage', 'Suite', 'Run', 'BEMGen', 'Gate'), 'ea-listing ea-stages')
    return body+f'<p class="ea-note">{esc(provenance.get("licence", ""))}.</p>'


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
    results = robust_results(entries) if paired(entries) else {}
    robust_pairs = sum(1 for r in results.values() if r['status'] == 'robust')
    rows = []
    for prototype in drop.prototypes():
        own = drop.entries(prototype)
        picks = tally(own)
        own_results = {k: r for k, r in results.items() if k[0] == prototype}
        fewest = [p['zone_count'] for e in own for p in e['recommended']]
        reference = [e['reference'].get('zone_count') for e in own if e['reference'].get('zone_count') is not None]
        rows.append((f'<a href="{esc(page.rel(urls[prototype]))}">{esc(prototype_name(prototype))}</a>', str(len(own)),
                     str(sum(1 for e in own if e['recommended'])),
                     *([f'{sum(1 for r in own_results.values() if r["status"] == "robust")} of {len(own_results)}'] if results else []),
                     esc(f'{picks[0][0]} ({picks[0][1]})') if picks else '<em>none</em>',
                     f'{min(fewest)} to {max(fewest)}' if fewest else NULL, f'{min(reference)} to {max(reference)}' if len(set(reference)) > 1 else (str(reference[0]) if reference else NULL)))
    overall = tally(entries)
    robust_overall = tally_robust(results)
    prototype_columns = ('Prototype', 'Cells', 'With a recommended zoning', *(['Robust across orientations (cell pairs)'] if results else []),
                         'Most often recommended (cells)', 'Recommended zones', 'Reference zones')
    robust_tally = (f'<h3>Robust across orientations: {robust_pairs} of {len(results)} cell pairs</h3>'
                    + table([(esc(label), str(count)) for label, count in robust_overall], ('Robust zoning', 'Cell pairs'))
                    + '<p class="ea-note">Counts over the cell pairs (prototype × climate zone × vintage) where one zoning meets the threshold at '
                    f'both orientations; the robust zoning of a pair is the coarsest that does. <a href="{esc(page.rel(URL+"method/#section-robust"))}">'
                    'The rule and its limits</a>.</p>' if results else '')
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
        'where no zoning meets it says so.'
        + (' The <strong>robust</strong> zoning of a prototype, climate zone and vintage is the coarsest that meets the threshold at both '
           'orientations; each prototype page opens with it.' if results else '')+'</p>',
        buttons, contents([('threshold', 'Threshold'), ('prototypes', 'Prototypes'), ('tally', 'Recommended zonings'),
                           *([('cost', 'Cost')] if drop.timing else []), ('status', 'Status')]),
        section(page, 'threshold', 'Threshold', threshold_html(drop.threshold)),
        section(page, 'prototypes', 'Prototypes',
                table(rows, prototype_columns)
                + f'<p>A zoning meets the threshold in {with_pick} of {len(entries)} cells'
                + (f', and at both orientations of a cell pair in {robust_pairs} of {len(results)} pairs (robust across orientations)' if results else '')
                + '. Each prototype page lists every cell, the recommended '
                'zoning with its errors, every zoning\'s metrics and the atlas programs the prototype takes. '
                + (f'The <a href="{esc(page.rel(urls["ht"]))}">heat-transfer sub-study</a> varies the interior-wall and floor heat-transfer switches. ' if 'ht' in urls else '')
                + f'<a href="{esc(page.rel(URL+"method/"))}">Method and caveats</a>.</p>'),
        section(page, 'tally', 'Recommended zonings', table([(esc(label), str(count)) for label, count in overall], ('Zoning', 'Cells'))
                + '<p class="ea-note">Counts over every cell and tie of the main matrix.</p>'+robust_tally),
        *([section(page, 'cost', 'Cost', cost_section(page, drop))] if drop.timing else []),
        section(page, 'status', 'Status', status_section(page, drop)),
    ]
    site.summaries[URL] = 'Zoning recommendations · geometric LOD study · thermal zoning · '+' '.join(prototype_name(p) for p in drop.prototypes())
    site.write(URL+'index.md', markdown(TITLE, ''.join(body)))


def robust_method(page, results):
    """The method page's section on the robust rule: what it is, what the data allows, and its limits."""
    if not results:
        return ('<p>This drop has one orientation per prototype, climate zone and vintage, so there is no pair to judge and no robust headline; '
                'the rule below applies to a drop with two or more orientations.</p><p>'+esc(ROBUST_RULE)+'</p>')
    robust_pairs = sum(1 for r in results.values() if r['status'] == 'robust')
    none_pairs = sum(1 for r in results.values() if r['status'] == 'none')
    single_pairs = sum(1 for r in results.values() if r['status'] == 'single')
    same = sum(1 for r in results.values() if r['status'] == 'robust' and r['same_pick'])
    tied = sum(1 for r in results.values() if r['status'] == 'robust' and r['ties'])
    orientations = sorted({o for r in results.values() for o in r['orientations']})
    return ('<p><strong>The rule</strong> (ADR 0050 section 6, an atlas rule over the writer\'s file). '+esc(ROBUST_RULE)+' Where both orientations '
            'recommend the same zoning it is the robust one, since any coarser zoning meeting the threshold at both would have been recommended at '
            'each. Where no zoning meets the threshold at both orientations the pair says so and names each orientation\'s own recommendation, '
            'which stays the closest reading for that orientation; a prototype, climate zone and vintage with one orientation in the file has no '
            'pair and no robust pick.</p>'
            + facts_html([('Orientations', ' and '.join(orientation(o) for o in orientations)),
                          ('Cell pairs', f'{len(results)}: robust in {robust_pairs}, none meeting at both orientations in {none_pairs}'
                                         + (f', one orientation only in {single_pairs}' if single_pairs else '')),
                          ('Recommended at both orientations', f'{same} of {robust_pairs} robust pairs; in the other {robust_pairs-same} the robust '
                                                                'zoning is one orientation\'s recommendation or finer than both'),
                          ('Ties at the fewest zones', f'{tied} pairs, named in the row')])
            + '<p><strong>What the data allows.</strong> The file lists every kept zoning of every cell with its metrics and the writer\'s verdict, '
            'so the rule compares the zonings themselves at both orientations, not only the two recommendations. It takes the writer\'s '
            '<code>meets_threshold</code> as the verdict and recomputes nothing: a zoning that is a duplicate at one orientation carries the writer\'s '
            '<em>never recommended</em> verdict there and does not qualify, which keeps the robust pick a kept test site at both orientations. The '
            'errors in a robust row are the worse of the two orientations\' stored values for each metric (the larger magnitude, with its sign), '
            'so a row bounds both orientations and is not an average; the orientation each value came from is in the prototype\'s JSON '
            '(<code>robust.pairs[].worst</code>).</p>'
            '<p><strong>Limits.</strong> Robust means robust over the two orientations the study ran, 0° and 45°, not over every orientation; '
            'a later drop with more orientations is judged over all of them by the same rule. The robust zoning is at least as fine as each '
            'orientation\'s own recommendation, never coarser. The cost ratios of a robust row are the median over the timed sites of that '
            'zoning in the pair, which in this drop is one site at most since only 0° cells were timed. The rule is computed at site build by '
            '<code>scripts/lod_site.py</code> and written into each prototype\'s JSON as a <code>robust</code> block labelled as such; the report '
            'writer\'s files are unchanged.</p>')


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
    timing = drop.timing or {}
    gate = timing.get('gate', {})
    recheck = timing.get('recheck') or {}
    timed_cells = sorted((e for e in entries if timed(e)), key=lambda e: (drop.prototypes().index(e['prototype']), cell_order(e)))
    results = robust_results(entries) if paired(entries) else {}
    coarser = {}  # (prototype, climate zone, zoning label, zones, reference zones): cells where the recommendation has more zones than the reference
    for entry in entries:
        for pick in entry['recommended']:
            if pick.get('zone_count') is not None and entry['reference'].get('zone_count') is not None and pick['zone_count'] > entry['reference']['zone_count']:
                key = (prototype_name(entry['prototype']), entry['climate_zone'], zoning_label(pick['zoning']), pick['zone_count'], entry['reference']['zone_count'])
                coarser[key] = coarser.get(key, 0)+1
    coarser_text = '; '.join(f'the {p} in {cz}: {label}, {zones} zones against the reference\'s {ref} ({n} cell{"s" if n > 1 else ""})'
                             for (p, cz, label, zones, ref), n in sorted(coarser.items()))
    file_rows = [(esc(name), esc(f.get('label', '')), esc(f.get('suite', '')), esc(f.get('run', '')), str(f.get('entries', '')), f'<code>{esc(str(f.get("sha256", ""))[:12])}</code>')
                 for name, f in files.items()]
    zoning_rows = [(esc(words(s)), esc(SIMPLIFIERS.get(s, ''))) for s in simplifiers]
    stacker_rows = [(esc(words(s)), esc(STACKERS.get(s, ''))) for s in stackers]
    cost_body = (
        '<p>Energy results do not depend on how many EnergyPlus processes run at once, so the stages ran 20 at a time and their times are '
        'not results (the <code>cpu_time_ratio</code> metric in the files comes from those runs and is not runtime data). Cost was measured '
        f'in a separate serial timing pass (R5, BEMGen <code>{esc(str(bemgen.get("timing_commit", "")))}</code>): {esc(timing.get("protocol", ""))}; '
        f'{esc(bemgen.get("machine", "an otherwise idle machine"))}. Per site the runner records the processor time (user plus kernel), the wall '
        'clock and the peak committed private memory; a site\'s cost is the median over its repeats, its <strong>cost ratio</strong> that median '
        'over its reference\'s median, and a zoning\'s or a prototype\'s cost the median of its test sites\' ratios (D-202).</p>'
        + facts_html([
            ('Timed', f'{timing.get("timed_sites", "")} sites of {len(timed_cells)} cells: '
                      + ', '.join(f'{prototype_name(e["prototype"])} {e["climate_zone"]} {e["vintage"]} {orientation(e["orientation_degrees"])}' for e in timed_cells)),
            ('Not timed', ', '.join(prototype_name(p) for p in timing.get('untimed_prototypes', []))+' (not among the 12 timed test cases, so their costs are not measured)'
                          if timing.get('untimed_prototypes') else ''),
            ('Repeats', ', '.join(sorted({str(e['reference']['cost'].get('repeats', '')) for e in timed_cells})) if timed_cells else ''),
            ('Gate', f'processor-time CV per site below {gate.get("limit_pct", "")} %: {gate.get("pass", "")} of {gate.get("sites", "")} sites pass; '
                     f'median {pct(gate.get("median_pct"))}, P90 {pct(gate.get("p90_pct"))}, largest {pct(gate.get("max_pct"))}; '
                     f'{gate.get("miss_short", "")} misses are short runs (0.8 to 3.3 s, where the 15.6 ms count of processor time is about 2 % of the '
                     f'value) and {gate.get("miss_long", "")} are among the {gate.get("long_sites", "")} sites of at least 4 s, which late in the third '
                     f'repeat took 13 to 24 % more processor time for a reason not established; <strong>{esc(gate.get("verdict", ""))}</strong>'),
            ('Treatment', esc(gate.get('treatment', ''))),
            ('Repeat check', f'the {recheck.get("sites", "")} long sites timed again (BEMGen <code>{esc(str(bemgen.get("recheck_commit", "")))}</code>, '
                             f'run <code>{esc(recheck.get("run", ""))}</code>, {", ".join(str(r) for r in recheck.get("repeats", []))} serial repeats on the idle '
                             f'machine): {recheck.get("miss", "")} of {recheck.get("sites", "")} at or above {gate.get("limit_pct", "")} % (median CV '
                             f'{pct(recheck.get("cv_median_pct"))}, largest {pct(recheck.get("cv_max_pct"))}; the pass had {recheck.get("r5_miss_same_sites", "")} '
                             f'misses among them), the third repeat over the first two median {num(recheck.get("r3_over_r12_median"), 3)}; but absolute times '
                             f'{change(recheck.get("median_vs_r5"))} against the pass and the {recheck.get("test_sites", "")} test sites\' ratios moved by '
                             f'{change(recheck.get("ratio_vs_r5_min"))} to {change(recheck.get("ratio_vs_r5_max"))} (median {change(recheck.get("ratio_vs_r5_median"), 1)})'
                             if recheck else '')])
        + '<p>Within a session the measurement is stable; between sessions a per-site ratio is reproducible to about ±15 %. The costs shown are '
        'therefore medians: the per-cell ratios on the prototype pages are each site\'s median over its repeats, and the medians by zoning and '
        f'by prototype on the <a href="{esc(page.rel(URL+"#section-cost"))}">overview</a> are the figures to quote. No per-site precision below '
        'the stated CV distribution is claimed (D-202).</p>') if timing else (
        '<p>The CPU-time ratios in the files come from runs 20 at a time on a shared machine and are not runtime results; the serial timing '
        'pass (R5) has not been applied to this drop.</p>')
    body = [
        crumbs(page, [(TITLE, URL), ('Method and caveats', URL+'method/')]),
        contents([('design', 'What was compared'), ('metrics', 'Metrics and threshold'), ('dedup', 'Deduplication'), ('robust', 'Robust across orientations'),
                  ('cost', 'Cost protocol'), ('cautions', 'Reading the recommendations'), ('limits', 'Limits and caveats'), ('provenance', 'Provenance')]),
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
                   '(multiplied rooms, or a wing narrower than twice the perimeter depth)' if fewer else '') + '. Orientation is a cell axis: the '
                'two orientations of one prototype, climate zone and vintage are two rows, and the headline over the pair is the robust rule below.</p>'),
        section(page, 'metrics', 'Metrics and threshold',
                '<p>Every value shown is the batch runner\'s own paired metric of a test site against its reference, as the report writer stored it; '
                'nothing is recomputed on this site. The annual error is the relative difference of annual ideal sensible heating or cooling; '
                'CV(RMSE) and NMBE are the hourly coefficient of variation of the root-mean-square error and the normalised mean bias error of '
                'ASHRAE Guideline 14; the peak error is the relative difference of the annual maximum hourly load; the area change is the change of '
                'conditioned floor area against the reference. The JSON files carry further metrics (P99 peaks, load-duration-curve errors, '
                'Kolmogorov–Smirnov distances, conditioned-temperature errors, zone-count ratios and the concurrent runs\' CPU-time ratio) that the '
                'pages do not show; the serial costs are the <code>cost</code> objects, shown as the cost columns.</p>'
                + threshold_html(threshold)
                + '<p>A zoning meets the threshold when every judged load passes all three limits and the area limit holds; a missing metric of a '
                'judged load fails. The recommended zonings of a cell are those meeting it with the fewest modelled zones; ties are all listed.</p>'),
        section(page, 'dedup', 'Deduplication',
                '<p>Two test sites of one cell are duplicates when they have the same zone-geometry signature (each zone\'s multiplier and its floor '
                'polygons, vertices rounded to a millimetre, names left out) and the same annual ideal sensible heating and cooling within a relative '
                'tolerance of 10<sup>−9</sup>. The site kept is the first in zoning order (simplifier, join pieces, perimeter depth, stacker, IWHT, FHT); '
                f'a reference is never dropped. In the main matrix {duplicates:,} of {tests:,} test sites are duplicates of a listed zoning; each cell '
                'names them under its table.</p>'),
        section(page, 'robust', 'Robust across orientations', robust_method(page, results)),
        section(page, 'cost', 'Cost protocol', cost_body),
        section(page, 'cautions', 'Reading the recommendations', '<ul>'
                '<li><strong>A recommendation with IWHT or FHT off is often not a heat-transfer effect.</strong> In the heat-transfer sub-study, '
                'where a zoning has no surface between zones of the kind a switch pairs (one zone, or one storey for FHT), its on and off settings '
                'write the same model; deduplication keeps the first in zoning order, which lists off before on, so the kept and recommended site '
                'carries <em>off</em> (for example Conditioned merge + Single zone building in the full-service restaurant 5A, the outpatient 3C and '
                'the supermarket 3C). Elsewhere the off settings are ties with the same zoning with both on (the medium office, the small hotel 3C). '
                'The count of cells where a recommended zoning has a switch off includes both kinds; the duplicate list under each cell names the '
                'twins, and the report\'s table by setting shows the effect itself: floors and ceilings between zones matter little, interior walls '
                'more.</li>'
                '<li><strong>Coarsest means fewest modelled zones, which can exceed the reference\'s count.</strong> Coarseness is the number of '
                'EnergyPlus zones before multipliers, so a Perimeter core split of a prototype with few rooms has more zones than the reference '
                + (f'and can still be the recommendation: {coarser_text}. ' if coarser else '. ')
                + 'This follows the rule as defined and is reported, not changed; the reference itself is never a test site.</li></ul>'),
        section(page, 'limits', 'Limits and caveats', '<ul>'
                '<li><strong>Ideal loads.</strong> Heating and cooling are ideal-loads sensible demands; HVAC systems, service hot water and latent '
                'loads are outside the comparison. The errors say how a zoning changes the building\'s thermal demand, not its energy use.</li>'
                '<li><strong>Deterministic inputs.</strong> The prototypes\' own geometry, glazing, atlas programs with ruleset schedules, the atlas '
                '90.1 unified construction set and one TMY3 weather file per climate zone; no stochastic schedules, no holidays, no infiltration axis.</li>'
                '<li><strong>Coverage.</strong> The vintages are 90.1-2007 and 90.1-2019 (atlas release 2.0.0 has no 90.1-2004 folders); climate zone 7 '
                'is registered as 7A, the atlas label of International Falls. IECC sets are out of scope.</li>'
                + (f'<li><strong>Zonings that do not apply.</strong> Perimeter core and the single-zone stackers do not support multiplied rooms, and a '
                   f'perimeter depth needs a wing at least twice as deep, so the {", ".join(fewer)} cells list fewer zonings.</li>' if fewer else '')
                + (f'<li><strong>Runs that did not succeed: not applicable in their cells (D-201).</strong> In the heat-transfer sub-study {len(ht_failed)} '
                   f'zonings of the {", ".join(ht_failed_names)}{ht_failed_note} did not complete: EnergyPlus stops in warm-up with an inside surface '
                   'temperature far out of bounds in the unconditioned elevator core (the source\'s elevator load, 32 kW in 15 m², all of it a gain to '
                   'the zone) or the merged mechanical or unconditioned zone, which with adiabatic interior walls (IWHT off) sheds the gain only '
                   'through one short exterior wall and the ground. With IWHT on the same zones run, so this is a limit of adiabatic interior walls '
                   'around an isolated high-gain unconditioned zone, not of the zonings; the program\'s load and the switch are written as given, '
                   'and no BEMGen change was made. Such zonings are not applicable in those cells: each is listed with its zoning as not applicable '
                   'and never recommended, and the cell\'s recommendation comes from the zonings that ran.</li>' if ht_failed else '')
                + f'<li><strong>Main matrix runs.</strong> {failed_main} of {tests:,} test sites did not succeed.</li>'
                + ('<li><strong>Cost precision and scope.</strong> The timing gate was not met, so costs are medians (the cost protocol above); the '
                   + ', '.join(prototype_name(p) for p in timing.get('untimed_prototypes', []))
                   + ' were not timed; costs are measured in '
                   + ', '.join(sorted({e['vintage'] for e in timed_cells}))+', climate zones '+', '.join(sorted({e['climate_zone'] for e in timed_cells}))
                   + ', at '+', '.join(sorted({orientation(e['orientation_degrees']) for e in timed_cells}))+' only, and on one machine.</li>'
                   if timing else
                   '<li><strong>Timing.</strong> The CPU-time ratios in the JSON come from runs 20 at a time on a shared machine and are not runtime '
                   'results; the serial timing pass (R5) is not in this drop.</li>')
                + '<li><strong>Threshold.</strong> The threshold is the report writer\'s default and an owner choice, recorded in every file; the R6 '
                'report kept it. A later drop with another threshold carries the new one in every file.</li>'
                '<li><strong>Not a population statement.</strong> The cells are the prototypes at their own dimensions; nothing here weights them by '
                'stock frequency.</li></ul>'),
        section(page, 'provenance', 'Provenance',
                facts_html([('Study', esc(study.get('title', ''))+(f' ({esc(study.get("name", ""))})' if study.get('name') else '')),
                            ('Run plan', bemgen_link(provenance, study['plan'])+' in BEMGen, decisions '
                                         + esc(', '.join(study.get('decisions') or [study.get('decision', '')])) if study.get('plan') else ''),
                            ('Report', bemgen_link(provenance, study['report'])+' (R6: the results and findings of every stage)' if study.get('report') else ''),
                            ('Methodology', bemgen_link(provenance, study['methodology'])+' (R6: the method, every number with its source)' if study.get('methodology') else ''),
                            ('BEMGen', f'<a href="{esc(bemgen.get("repository", "#"))}">{esc(bemgen.get("repository", ""))}</a>: report writer '
                                       f'<code>{esc(bemgen.get("writer", ""))}</code> and schema {esc(bemgen.get("schema_version", ""))} at '
                                       f'<code>{esc(str(bemgen.get("report_commit", ""))[:12])}</code>; the R3 and R4 runs with the IDF writer at '
                                       f'<code>{esc(str(bemgen.get("run_commit", "")))}</code>'
                                       + (f'; the R5 timing pass at <code>{esc(str(bemgen.get("timing_commit", "")))}</code>' if bemgen.get('timing_commit') else '')
                                       + (f' and its repeat check at <code>{esc(str(bemgen.get("recheck_commit", "")))}</code>' if bemgen.get('recheck_commit') else '')
                                       + f'; EnergyPlus {esc(bemgen.get("energyplus", ""))}'),
                            ('Atlas inputs', f'release {esc(inputs.get("release", ""))} at <code>{esc(str(inputs.get("commit", ""))[:12])}</code>, '
                                             f'{esc(inputs.get("program_version", ""))} programs, {esc(inputs.get("construction_representation", ""))} constructions'),
                            ('Schema', f'<code>{esc(bemgen.get("schema_copy", ""))}</code>, a copy of BEMGen\'s <code>{esc(bemgen.get("schema", ""))}</code>'
                                       f'; the main matrix is version {esc(main.get("version", ""))}'
                                       + (f', the sub-study {esc(drop.ht.get("version", ""))}' if drop.ht else '')),
                            ('Repository files', f'<code>data/lod-recommendations/v1/</code>; drop {esc(provenance.get("drop", ""))}'),
                            ('Licence', esc(provenance.get('licence', '')))])
                + table(file_rows, ('File', 'Stage', 'Suite', 'Run', 'Cells', 'SHA-256'))
                + (table(stage_rows(provenance), ('Stage', 'Suite', 'Run', 'BEMGen', 'Gate'), 'ea-listing ea-stages') if provenance.get('stages') else '')
                + '<p class="ea-note">A later consolidated drop replaces the files in place with the same layout; the pages are regenerated from '
                'them at the next site build (ADR 0050).</p>'),
    ]
    site.summaries[URL+'method/'] = 'Method and caveats · zoning recommendations · geometric LOD study · threshold · deduplication · provenance'
    site.write(URL+'method/index.md', markdown('Method and caveats', ''.join(body)))


def program_fact(name, results):
    """The catalogue page's fact text for a program: its prototype and the robust picks of the cell pairs the program is used in."""
    if not results:
        return name
    picks = tally_robust(results)
    robust_pairs = sum(picks_count for _, picks_count in picks)
    text = f'{name}: robust across orientations in {robust_pairs} of {len(results)} cell pairs'
    return text+(': '+', '.join(f'{label} ({count})' for label, count in picks) if picks else '')


def write_zoning(site, folder=DROP):
    """Every zoning page into the site; returns the manifest entry (pages and counts) and fills `site.zoning_of`."""
    drop = Drop(folder)
    urls = {p: f'{URL}{prototype_slug(p)}/' for p in drop.prototypes()}
    if len(set(urls.values())) != len(urls):
        raise ValueError('Two prototypes share one page path')
    if drop.ht:
        urls['ht'] = URL+'heat-transfer/'
    results = robust_results(drop.main['entries']) if paired(drop.main['entries']) else {}
    by_id = {e['id']: e for e in drop.main['entries']}
    for program, ids in drop.main['by_program'].items():
        prototypes = sorted({i.split('|')[0] for i in ids})
        own = {pair_key(by_id[i]) for i in ids if i in by_id}
        site.zoning_of[program] = [(program_fact(prototype_name(p), {k: r for k, r in results.items() if k in own and k[0] == p}),
                                    urls[p]+('#section-robust' if results else '')) for p in prototypes if p in urls]
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
            'timed_cells': sum(1 for e in drop.main['entries'] if timed(e)),
            'cell_pairs': len(results), 'robust_pairs': sum(1 for r in results.values() if r['status'] == 'robust'),
            'ht_cells': len(drop.ht['entries']) if drop.ht else 0}
