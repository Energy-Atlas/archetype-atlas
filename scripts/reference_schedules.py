"""Compare DOE reference schedules with the atlas release and openstudio-standards, over a full year.

python -m scripts.reference_schedules --idf-root <extracted doe-reference/v1.4_7.2>
    --standards-root <ashrae_90_1 dir> [--vintage post1980|pre1980] [--out build/reconciliation/schedules-<vintage>.json]

Every Schedule:Compact referenced by People, Lights, electric or gas equipment, a
dual-setpoint thermostat, water-use flow or infiltration is evaluated on the IDF
calendar (scripts.idf_schedules). Its best match is the atlas schedule of the same
template and building type with the fewest differing days, and likewise among all
openstudio-standards schedule rows. Each reference gets a cause:
  identical; holidays only; design days; out of program scope (infiltration,
  elevators, exhaust fans); assignment (openstudio-standards holds the DOE profile
  under another name); source edit (the openstudio-standards row differs); vintage
  variant (openstudio-standards keeps a pre-2004 row next to the DOE profile);
  no atlas counterpart.
"""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from scripts import idf_reader, idf_schedules
from scripts.common import ROOT
from scripts.reference_loads import TYPES, VINTAGES

RELEASE = ROOT/'data/atlas-releases/v1.0.0/commercial'
ROLES = {('people', 2): 'occupancy', ('lights', 2): 'lighting', ('electricequipment', 2): 'plug',
         ('gasequipment', 2): 'gas', ('thermostatsetpoint:dualsetpoint', 1): 'heating setpoint',
         ('thermostatsetpoint:dualsetpoint', 2): 'cooling setpoint', ('wateruse:equipment', 3): 'hot-water flow',
         ('zoneinfiltration:designflowrate', 2): 'infiltration'}


def key_of(values):
    return None if values is None else tuple(round(v, 6) for v in values)


class Index:
    """Rulesets evaluated once on a calendar and indexed by their day profiles."""

    def __init__(self, rulesets, days):
        self.keys = list(days)
        self.days = days
        self.vectors = {}
        self.by_profile = defaultdict(set)
        for name, (rules, profile) in rulesets.items():
            try:
                evaluated = idf_schedules.evaluate_ruleset(rules, profile, days)
            except (KeyError, ValueError, TypeError):
                continue
            vector = tuple(key_of(evaluated[k]) for k in self.keys)
            self.vectors[name] = vector
            for p in set(vector):
                self.by_profile[p].add(name)

    def best(self, evaluated):
        target = tuple(key_of(evaluated[k]) for k in self.keys)
        pool = set().union(*(self.by_profile.get(p, set()) for p in set(target)))
        ranked = []
        for name in pool:
            diff = [k for k, a, b in zip(self.keys, target, self.vectors[name])
                    if not idf_schedules.same(a, b)]
            ranked.append((len(diff), name, diff))
        if not ranked:
            return None
        ranked.sort(key=lambda r: (r[0], r[1]))
        n, name, diff = ranked[0]
        return {'name': name, 'differing_days': n, 'class': idf_schedules.classify(diff, self.days),
                'tied': sorted(r[1] for r in ranked if r[0] == n)[:40]}


def atlas_rulesets(template, folder):
    data = json.loads((RELEASE/template/folder/'schedules.json').read_text(encoding='utf-8'))
    days = {k: (v * 24 if len(v) == 1 else v) for k, v in data['days'].items()}
    return {name: (s['rules'], lambda r, days=days: days[r['day']]) for name, s in data['schedules'].items()}, \
        {name: s.get('source_name') for name, s in data['schedules'].items()}


def standards_rulesets(standards_root):
    grouped = defaultdict(list)
    for row in json.loads((standards_root/'data/ashrae_90_1.schedules.json').read_text())['schedules']:
        grouped[row['name']].append(row)
    profile = lambda r: r['values'] * 24 if len(r['values']) == 1 else r['values']
    return {name: (rows, profile) for name, rows in grouped.items()}


def cause(role, name, atlas, standards):
    if atlas and atlas['class'] == 'identical':
        return 'identical'
    if role == 'infiltration':
        return 'out of program scope: infiltration'
    if 'elevator' in name.lower() or 'exhaust' in name.lower():
        return 'out of program scope: building service'
    if atlas and atlas['class'] == 'holidays only':
        return 'holidays'
    if atlas and atlas['class'] in ('design days only', 'holidays and design days only'):
        return 'design days'
    if standards and standards['class'] in ('identical', 'holidays only'):
        if any('pre2004' in t.lower() for t in standards['tied']) or any('2004' in t for t in standards['tied']):
            return 'vintage variant' if atlas else 'no atlas program uses it'
        return 'assignment' if atlas else 'no atlas program uses it'
    return 'source edit' if atlas else 'no atlas counterpart'


def compare_type(model, template, folder, standards_index_for):
    days = idf_schedules.calendar_days(model.holidays())
    compact = model.schedules()
    roles = defaultdict(set)
    for cls, fields in model.objects:
        for i, value in enumerate(fields):
            if (cls, i) in ROLES and value.lower() in compact:
                roles[value.lower()].add(ROLES[(cls, i)])
    rulesets, source_names = atlas_rulesets(template, folder)
    atlas_index = Index(rulesets, days)
    standards_index = standards_index_for(days)
    rows = []
    for name, role_set in sorted(roles.items()):
        evaluated, subhour = idf_schedules.evaluate_compact(compact[name], days)
        atlas = atlas_index.best(evaluated)
        standards = standards_index.best(evaluated)
        for role in sorted(role_set):
            rows.append({'schedule': compact[name][0], 'role': role, 'subhour': subhour,
                         'atlas': atlas and dict(atlas, source_name=source_names.get(atlas['name'])),
                         'standards': standards, 'cause': cause(role, name, atlas, standards)})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--idf-root', type=Path, required=True)
    parser.add_argument('--standards-root', type=Path, required=True)
    parser.add_argument('--vintage', choices=sorted(VINTAGES), default='post1980')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    template = VINTAGES[args.vintage][0]
    rulesets = standards_rulesets(args.standards_root)
    cache = {}

    def standards_index_for(days):
        signature = tuple(sorted(k for k, (_, kind) in days.items() if kind == 'Hol'))
        if signature not in cache:
            cache[signature] = Index(rulesets, days)
        return cache[signature]

    result = {}
    for key, (building_type, folder) in TYPES.items():
        path = next((args.idf_root/f'refbldg_{key}_{args.vintage}_v1-4_7-2').glob('*5A_USA_IL_CHICAGO-OHARE.idf'))
        result[building_type] = compare_type(idf_reader.Model(path), template, folder, standards_index_for)
    totals = Counter(r['cause'] for rows in result.values() for r in rows)
    out = args.out or ROOT/f'build/reconciliation/schedules-{args.vintage}.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({'vintage': args.vintage, 'template': template, 'types': result,
                               'totals': dict(totals)}, indent=1))
    for c, n in totals.most_common():
        print(f'{n:>4}  {c}')


if __name__ == '__main__':
    main()
