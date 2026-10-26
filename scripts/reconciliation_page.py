"""Write the site page for the DOE reference reconciliation from its register (ADR 0037).

python -m scripts.reconciliation_page            # write website/content/guides/doe-reference-reconciliation.md
python -m scripts.reconciliation_page --check    # fail if the page differs from the register

The page states the rules, counts every decision by class, lists the reasons, and
gives one table per template and building type with every register row: what the
atlas held, what the DOE model has, and the decision.
"""
import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from scripts.common import ROOT, load_json

REGISTER = ROOT/'data/reconciliation/doe-reference-v1.json'
PAGE = ROOT/'website/content/guides/doe-reference-reconciliation.md'
DECISIONS = ('replace', 'fill', 'add', 'keep', 'leave', 'omit')
CLASSES = {
    'A1-holidays': 'Holiday rules follow the DOE model', 'A3-upstream-edit': 'openstudio-standards edited the row after DOE v1.4',
    'A3-vintage-variant': 'A vintage variant of the same schedule', 'A3-no-atlas-counterpart': 'A DOE schedule with no atlas counterpart',
    'A4-assignment': 'A program used another schedule than its DOE zones', 'A4-slot-assignment': 'A program slot differed from its DOE schedule over the year',
    'A4-slot-conflict': 'Several DOE schedules serve one program slot', 'A4-slot-minority': 'A DOE schedule used by a minority of a program\'s zones',
    'A4-retag': 'A DOE zone group gets a program of its own', 'A5-existing-density': 'An existing-building density differs from DOE',
    'A5-explicitly-wrong': 'A density off by a factor of ten', 'A5-folded-service': 'A building service folded into a space type',
    'A7-rounding': 'The same value within the IDF printing precision', 'A9-design-days': 'Design-day profiles follow DOE',
    'A10-infiltration-schedule': 'A DOE infiltration schedule', 'A10-infiltration-method': 'The DOE design-flow infiltration method',
    'A12-heat-fraction': 'Lighting and equipment heat fractions', 'B1-hot-water': 'Hot water where the atlas had none',
    'B1-hot-water-schedule': 'A DOE hot-water flow schedule', 'B2-additional-lighting': 'Additional lighting',
    'B3-unconditioned-equipment': 'Plenum and attic equipment', 'B4-setpoints': 'Setpoints where the atlas had none',
    'B5-missing-density': 'A density the atlas lacked', 'B7-filling-sourced': 'A filled density re-based on the DOE value',
    'B8-internal-mass': 'Internal mass', 'C1-holiday-calendar': 'The source holiday calendar', 'C2-daylight-saving': 'Daylight-saving time',
    'C3-building-service': 'A building service (elevator, exhaust fan, exterior lights)', 'C3-building-service-schedule': 'A building-service schedule',
    'C4-refrigeration': 'Refrigeration cases and racks', 'C5-water-use-gains': 'Water-use zone gains', 'C6-humidity-setpoint': 'Humidity setpoints',
    'C7-systems': 'HVAC and plant', 'C8-basement-program': 'A basement program', 'C10-program-wwr': 'Program window ratios',
    'C10-building-wwr': 'Building window ratios', 'C10-geometry': 'Plan geometry', 'C11-site-data': 'Site, weather and cost data',
    'C12-comfort-fields': 'Comfort-only People fields', 'C13-replaceable-fraction': 'The lights replaceable fraction',
    'mixed-zone': 'A DOE zone spanning several atlas space types', 'zone-unmapped': 'A DOE zone with no atlas program',
    'midrise-apartment': 'Midrise Apartment'}

HEAD = '''# DOE reference reconciliation

Release 1.1.0 reconciles the DOE Ref templates with the DOE Commercial Reference
Building models (v1.4_7.2, post-1980 and pre-1980, Chicago 5A) under ADR 0037.
Every difference, gap and missing component has one register row with its
decision. This page is generated from
`data/reconciliation/doe-reference-v1.json`; the 90.1 templates are not changed.

## Rules

- The DOE model of the matching vintage is the authority for the DOE Ref
  templates' schedules and loads.
- Where openstudio-standards edited a row after DOE v1.4 (2012-11-13) and
  documented why, the atlas keeps its value and the DOE value becomes an
  alternate.
- An existing-building density is replaced only when it is explicitly wrong: a
  factor of ten or more, a missing value or a contradiction. Otherwise it is
  kept, with the DOE value as an alternate when they differ by more than half.
- Absence in the complete DOE model counts as a source-backed zero.
- Differences within the IDF printing precision (1%) keep the atlas value.

Decisions: **replace** an atlas value with DOE's, **fill** a gap, **add** a
missing component; **keep**, **leave** or **omit** with a reason.
'''


def class_order(klass):
    """A1, A3, ..., A10, then B, C, then the unlettered classes."""
    match = re.match(r'([A-C])(\d+)-(.*)', klass)
    return (match[1], int(match[2]), match[3]) if match else ('Z', 0, klass)


def cell(value, limit=90):
    if value is None:
        return '—'
    if isinstance(value, float):
        text = f'{value:.6g}'
    elif isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    else:
        text = str(value)
    text = text.replace('|', '\\|').replace('\n', ' ')
    return text if len(text) <= limit else text[:limit-1]+'…'


def target(row):
    names = row.get('target') or []
    return ', '.join(str(n).split('.')[-2] if str(n).count('.') >= 3 else str(n) for n in names if n) or '—'


def source(row):
    value = row.get('source_value') or {}
    for key in ('value', 'object', 'zones', 'zone'):
        if value.get(key) is not None:
            return value[key]
    return None


def page(register):
    rows = register['rows']
    lines = [HEAD, '## Decisions by class\n', '| Class | ' + ' | '.join(DECISIONS) + ' |', '| --- |' + ' ---: |' * len(DECISIONS)]
    counts = defaultdict(Counter)
    for r in rows:
        counts[r['klass']][r['decision']] += 1
    for klass in sorted(counts, key=class_order):
        lines.append(f'| {CLASSES.get(klass, klass)} (`{klass}`) | ' + ' | '.join(str(counts[klass][d] or '') for d in DECISIONS) + ' |')
    total = Counter(r['decision'] for r in rows)
    lines.append('| **All** | ' + ' | '.join(f'**{total[d]}**' for d in DECISIONS) + ' |')
    not_listed = register['summary']['not_listed']
    lines += ['', f'Identical schedules are counted, not listed: {not_listed.get("identical schedules", 0)}.', '',
              '## Reasons\n', '| Reason | Meaning |', '| --- | --- |']
    lines += [f'| `{k}` | {v} |' for k, v in sorted(register['reasons'].items())]
    groups = defaultdict(list)
    for r in rows:
        groups[(r['template'], r['building_type'] or 'All building types')].append(r)
    for (template, building_type), items in sorted(groups.items()):
        lines += ['', f'## {template} · {building_type}\n', '| Row | Class | Target | Field | Atlas | DOE | Decision |',
                  '| --- | --- | --- | --- | --- | --- | --- |']
        for r in sorted(items, key=lambda r: (class_order(r['klass']), r['id'])):
            decision = r['decision'] + (f' (`{r["reason_id"]}`)' if r.get('reason_id') else '')
            current = (r.get('current') or {}).get('value')
            lines.append(f'| {r["id"]} | `{r["klass"]}` | {cell(target(r), 60)} | {cell(r.get("field"), 50)} | '
                         f'{cell(current)} | {cell(source(r))} | {decision} |')
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    text = page(load_json(REGISTER))
    if args.check:
        if not PAGE.exists() or PAGE.read_text(encoding='utf-8') != text:
            raise SystemExit(f'{PAGE.relative_to(ROOT)} differs from the register; run python -m scripts.reconciliation_page')
        print('Reconciliation page matches the register')
        return
    PAGE.write_text(text, encoding='utf-8', newline='\n')
    print(f'Wrote {PAGE.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
