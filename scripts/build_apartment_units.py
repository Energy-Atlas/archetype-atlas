"""Write the apartment-unit recipes as ResStock multifamily units (rulings 185-187; plan section 8, B7).

python -m scripts.build_apartment_units           # write
python -m scripts.build_apartment_units --check   # compare

Every apartment-unit recipe of release 2.0.0 (`generator.json` of the 90.1 and DOE Ref apartment
folders, source and reviewed views) becomes a ResStock unit recipe: the prototype's slots, loads,
controls and lighting timing give way to the `resstock_unit` block that
atlas_schedules/residential/apartment.py reads, from the release and its inputs:
- building type and height class: the prototype geometry (data/construction-inputs/geometry-v1.json),
  stories and apartments counted from its spaces and multipliers, binned as ResStock's
  `Geometry Building Type Height` bins them (the same classes scripts/residential.py maps back to
  the Midrise and Highrise prototypes);
- vintages: the decades of the template's era (`ERAS`); for a 90.1 edition the years it was the
  newest edition, with 2010s, ResStock's newest bin, for 90.1-2019;
- HVAC: the heating-and-cooling systems of the folder's `systems.json` (one heating and cooling
  pair per folder; the DOE Ref electric unit heaters, one per corridor level, heat no apartment)
  mapped to ResStock's five HVAC characteristics (`HVAC`). ResStock has no water-loop heat pump,
  so the high-rise water-to-air heat pumps become a unit's ducted heat pump;
- hot water per person (ruling 185, P2): the prototype's per-area volume on its schedule over the
  prototype's design occupants per area.
The caller-water block stays: its service and controls describe the building's water service.
Schedules only the replaced recipes used leave `atlas_schedules/data/schedules.json`.
scripts/build_reference_recipes.py writes the DOE Ref apartment recipes through `unit_recipe` too.
Release 2.0.0 keeps the 2.x recipes; the next release carries these.
"""
import argparse
import json
from pathlib import Path

from atlas_schedules import programmes
from atlas_schedules.calendar import evaluate_rules
from atlas_schedules.residential.apartment import hot_water_m3_per_person
from scripts.common import ROOT, load_json

RELEASE = ROOT/'data/atlas-releases/v2.0.0/commercial'
GEOMETRY = ROOT/'data/construction-inputs/geometry-v1.json'
DATA = ROOT/'atlas_schedules/data'
RECIPES = DATA/'recipes'
ERAS = {'90.1-2007': ('2007-2009', ['2000s']), '90.1-2013': ('2013-2015', ['2010s']), '90.1-2019': ('2019-', ['2010s']),
        'DOE Ref Pre-1980': ('before 1980', ['<1940', '1940s', '1950s', '1960s', '1970s']),
        'DOE Ref 1980-2004': ('1980-2004', ['1980s', '1990s', '2000s'])}
HVAC = {('Gas', 'Single Speed DX AC'): ['Natural Gas', 'Ducted Heating', 'Central AC', 'None', 'No'],
        ('Water To Air Heat Pump', 'Water To Air Heat Pump'): ['Electricity', 'Ducted Heat Pump', 'Ducted Heat Pump', 'None', 'No']}
KEPT = ('schema_version', 'program_id', 'name', 'kind', 'source', 'required_services', 'caller_water')


def relative(path):
    return Path(path).relative_to(ROOT).as_posix()


def size(geometry):
    """(stories, apartments) of a prototype geometry entry, multipliers counted once per level."""
    levels = {}
    apartments = 0
    for space in geometry['spaces']:
        level = round(space['z_min_m'], 2)
        levels[level] = max(levels.get(level, 0), space['multiplier'])
        if 'Apartment' in (space['standards_space_type'] or ''):
            apartments += space['multiplier']
    return sum(levels.values()), apartments


def building_classes(stories, apartments):
    if apartments < 5:
        return 'Multi-Family with 2 - 4 Units', None
    height = '1-3' if stories <= 3 else '4-7' if stories <= 7 else '8+'
    return 'Multi-Family with 5+ Units', f'Multi-Family with 5+ Units, {height} Stories'


def system_pair(systems):
    pairs = {(s['source_descriptor']['heating_type'], s['source_descriptor']['cooling_type'])
             for s in systems.values()
             if s['kind'] == 'hvac_system' and 'residential' in s['gate'] and s['source_descriptor'].get('cooling_type')}
    if len(pairs) != 1:
        raise ValueError(f'Expected one heating and cooling pair, found {sorted(pairs)}')
    return next(iter(pairs))


def unit_recipe(recipe, folder, key, view, geometry):
    """The ResStock unit recipe of one release apartment recipe."""
    template = recipe['source']['template']
    stories, apartments = size(geometry)
    building_type, height = building_classes(stories, apartments)
    era, vintages = ERAS[template]
    pair = system_pair(json.loads((folder/'systems.json').read_text(encoding='utf-8')))
    water = recipe['caller_water']
    shape = evaluate_rules(programmes.schedules()[water['schedule']])[0]
    people = next(c for c in recipe['controls'] if c['slot'] == 'occupants')['people']['density']
    block = {
        'building_type': building_type, 'height': height, 'vintages': vintages, 'hvac': HVAC[pair],
        'hot_water_m3_per_person': hot_water_m3_per_person(water, shape, people),
        'source': {'geometry': f"{relative(GEOMETRY)}#{geometry['id']}", 'stories': stories, 'apartments': apartments,
                   'era': f'{template}: {era}', 'systems': relative(folder/'systems.json'), 'system_pair': list(pair),
                   'hot_water': {'density': water['density'], 'density_unit': water['density_unit'],
                                 'schedule': water['schedule'], 'full_load_hours': float(shape.sum()),
                                 'design_people_per_m2': people},
                   'release_recipe': f"{relative(folder/'generator.json')}#{key}/{view}"}}
    return {**{k: recipe[k] for k in KEPT}, 'resstock_unit': block}


def build():
    geometry = {(e['template'], e['building_type']): e
                for e in json.loads(GEOMETRY.read_text(encoding='utf-8'))['commercial']}
    recipes = {}
    for path in sorted(RELEASE.glob('*/*-apartment/generator.json')):
        for key, views in json.loads(path.read_text(encoding='utf-8')).items():
            for view, recipe in views.items():
                if recipe['kind'] != 'apartment_unit':
                    continue
                source = recipe['source']
                recipes[recipe['program_id']] = unit_recipe(recipe, path.parent, key, view,
                                                            geometry[(source['template'], source['building_type'])])
    return recipes


def text(recipe):
    return json.dumps(recipe, indent=1, sort_keys=True) + '\n'


def unused_schedules(recipes):
    """(schedule table, IDs no packaged recipe, configuration or service uses once `recipes` replace theirs)."""
    from scripts.build_reference_recipes import references
    table = load_json(DATA/'schedules.json')
    used = set().union(*(references(r, table) for r in recipes.values()))
    replaced = set()
    for folder in ('recipes', 'configurations', 'services'):
        for path in (DATA/folder).glob('*.json'):
            record = load_json(path)
            if folder == 'recipes' and record['program_id'] in recipes:
                replaced |= references(record, table)
            else:
                used |= references(record, table)
    return table, sorted(replaced - used)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    recipes = build()
    stale = [pid for pid, recipe in recipes.items()
             if not (RECIPES/f'{pid}.json').exists() or (RECIPES/f'{pid}.json').read_text(encoding='utf-8') != text(recipe)]
    table, unused = unused_schedules(recipes)
    if args.check:
        if stale or unused:
            raise SystemExit(f'{len(stale)} of {len(recipes)} apartment recipes differ, e.g. {stale[:3]}; '
                             f'{len(unused)} schedules unused')
        print(f'{len(recipes)} apartment recipes match')
        return
    for pid in stale:
        (RECIPES/f'{pid}.json').write_bytes(text(recipes[pid]).encode('utf-8'))
    for schedule_id in unused:
        del table[schedule_id]
    (DATA/'schedules.json').write_bytes((json.dumps(table, separators=(',', ':'), sort_keys=True)+'\n').encode('utf-8'))
    print(f'wrote {len(stale)} of {len(recipes)} apartment recipes; removed {len(unused)} unused schedules')


if __name__ == '__main__':
    main()
