"""Write the apartment units' generation blocks as ResStock multifamily units (rulings 185-187; plan section 8, B7).

python -m scripts.build_apartment_units           # write
python -m scripts.build_apartment_units --check   # compare

Every apartment program of the 90.1 and DOE Ref apartment folders gets a `resstock_unit` block per view
in release 2.2.0's `generation.json` (ADR 0051): the prototype's slots, loads, controls and lighting
timing give way to the block that atlas_schedules/residential/apartment.py reads, from the release and
its inputs:
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
- hot water per person (ruling 185, P2): the program's per-area volume on its schedule over its
  design occupants per area.
The unit's caller water (the building's water service) is assembled from the program itself.
scripts/build_reference_recipes.py writes the DOE Ref apartment blocks through `unit_block` too.
"""
import argparse
import json
from pathlib import Path

from atlas_schedules import programmes
from atlas_schedules.calendar import evaluate_rules
from atlas_schedules.release import Release
from atlas_schedules.residential.apartment import hot_water_m3_per_person
from scripts import atlas_delta
from scripts.common import ROOT

GEOMETRY = ROOT/'data/construction-inputs/geometry-v1.json'
ERAS = {'90.1-2007': ('2007-2009', ['2000s']), '90.1-2013': ('2013-2015', ['2010s']), '90.1-2019': ('2019-', ['2010s']),
        'DOE Ref Pre-1980': ('before 1980', ['<1940', '1940s', '1950s', '1960s', '1970s']),
        'DOE Ref 1980-2004': ('1980-2004', ['1980s', '1990s', '2000s'])}
HVAC = {('Gas', 'Single Speed DX AC'): ['Natural Gas', 'Ducted Heating', 'Central AC', 'None', 'No'],
        ('Water To Air Heat Pump', 'Water To Air Heat Pump'): ['Electricity', 'Ducted Heat Pump', 'Ducted Heat Pump', 'None', 'No']}


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


def unit_block(release, program_id, view, geometry):
    """The `resstock_unit` block of one apartment program in one view."""
    folder, record = release.program(program_id)
    data = programmes.view_record(record, view)
    template = data['template']
    stories, apartments = size(geometry)
    building_type, height = building_classes(stories, apartments)
    era, vintages = ERAS[template]
    pair = system_pair(release.json(f'{folder}/systems.json'))
    water = programmes.caller_water(data, release.services(folder))
    shape = evaluate_rules(release.schedules(folder)[water['schedule']])[0]
    people = programmes.load_of(data, 'occupancy')['value']
    return {
        'building_type': building_type, 'height': height, 'vintages': vintages, 'hvac': HVAC[pair],
        'hot_water_m3_per_person': hot_water_m3_per_person(water, shape, people),
        'source': {'geometry': f"{relative(GEOMETRY)}#{geometry['id']}", 'stories': stories, 'apartments': apartments,
                   'era': f'{template}: {era}', 'systems': relative(release.paths[f'{folder}/systems.json']), 'system_pair': list(pair),
                   'hot_water': {'density': water['density'], 'density_unit': water['density_unit'],
                                 'schedule': water['schedule'], 'full_load_hours': float(shape.sum()),
                                 'design_people_per_m2': people},
                   'program': relative(release.paths[release.program_paths[program_id]])}}


def geometries():
    return {(e['template'], e['building_type']): e for e in json.loads(GEOMETRY.read_text(encoding='utf-8'))['commercial']}


def build(release):
    """{folder: {program ID: block}} of every apartment program with a resstock_unit block."""
    shapes = geometries()
    out = {}
    for folder in release.generation_folders():
        if not folder.endswith('-apartment'):
            continue
        for rid, block in release.generation(folder).get('programs', {}).items():
            if block['method'] != 'resstock_unit':
                continue
            record = release.program(rid)[1]
            geometry = shapes[(record['template'], record['building_type'])]
            views = {view: {'resstock_unit': unit_block(release, rid, view, geometry)} for view in block['views']}
            out.setdefault(folder, {})[rid] = {**block, 'views': views}
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    release = Release(atlas_delta.folder_of('2.2.0'))
    blocks = build(release)
    stale = {folder: programs for folder, programs in blocks.items()
             if any(release.generation(folder)['programs'][rid] != block for rid, block in programs.items())}
    count = sum(len(p) for p in blocks.values())
    if args.check:
        if stale:
            raise SystemExit(f'{sum(len(p) for p in stale.values())} of {count} apartment blocks differ, in {sorted(stale)[:3]}')
        print(f'{count} apartment blocks match')
        return
    docs = {}
    for folder, programs in stale.items():
        doc = release.generation(folder)
        docs[folder] = {**doc, 'programs': {**doc['programs'], **programs}}
    atlas_delta.write_generation(docs)
    print(f'wrote {len(stale)} of {len(blocks)} apartment folders ({count} blocks)')


if __name__ == '__main__':
    main()
