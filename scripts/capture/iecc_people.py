"""Capture the People of the PNNL IECC commercial prototypes as an answer key (ADR 0055).

python -m scripts.capture.iecc_people --idf-root "<commercial-iecc dir>" [--manifest <SOURCES-prototypes.json>]

For each IECC edition and building type the generator samples, the Buffalo (5A) IDF the release's
climate-independent values cite (scripts.iecc_commercial_zones.BASE_CITY): every zone with its
multiplier, floor area, the design people of its People objects (number of people, or people per
area or area per person times the floor area; scripts.iecc_commercial_values.density) and whether
its standards space type is residential (openstudio-standards `space_residential?`, the rule
scripts.build_reference_recipes applies). The key is what the hours-of-operation inference reads
from the source model; tests/test_zone_recipes.py checks the IECC building configurations of
scripts.build_zone_recipes against it: total design people with multipliers within 1e-6, the dominant
group and the rule-day inversion exactly. Writes tests/answer_keys/commercial/iecc-people.json.
"""
import argparse
import hashlib
import json
from pathlib import Path

from atlas_schedules.programmes import SAMPLING
from scripts import idf_reader
from scripts.build_reference_recipes import residential
from scripts.common import ROOT
from scripts.iecc_commercial_values import density, layered, zones
from scripts.iecc_commercial_zones import BASE_CITY, EDITIONS, TYPES, Lookup

OUTPUT = ROOT/'tests/answer_keys/commercial/iecc-people.json'


def capture(idf_root, members=None):
    lookup = Lookup()
    cases = {}
    for edition in EDITIONS:
        for pnnl, building_type in sorted(TYPES.items()):
            if building_type not in SAMPLING:
                continue
            path = Path(idf_root)/f'IECC_{pnnl}'/f'IECC_{pnnl}_STD{edition}_{BASE_CITY}.idf'
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            member = 'commercial-iecc/'+path.relative_to(idf_root).as_posix()
            if members is not None and members.get(member) != digest:
                raise ValueError(f'IDF differs from its archive member record: {member}')
            model = idf_reader.Model(path)
            geometry = zones(model)
            people = {}
            for item in model.loads('people'):
                for z in item['zones']:
                    people[z] = people.get(z, 0.0) + density(item, 'people', geometry[z]['floor_m2'], 0)*geometry[z]['floor_m2']
            rows = []
            for key, zone in sorted(geometry.items(), key=lambda kv: kv[1]['name']):
                _, space_type = lookup(building_type, zone['name'])
                rows.append({'zone': zone['name'], 'multiplier': zone['multiplier'], 'floor_area_m2': round(zone['floor_m2'], 9),
                             'design_people': round(people.get(key, 0.0), 9), 'residential': residential(space_type)})
            cases[f'IECC {edition}/{building_type}'] = {'idf': path.name, 'sha256': digest, 'zones': rows}
    return {'schema_version': '1.0.0', 'source': {'family': 'commercial-iecc', 'lock': 'sources/reference-models-lock.json',
                                                   'city': BASE_CITY, 'capture': 'scripts/capture/iecc_people.py'},
            'cases': cases}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--idf-root', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, help='SOURCES-prototypes.json with the archive member checksums')
    args = parser.parse_args()
    members = None
    if args.manifest:
        records = json.loads(args.manifest.read_text(encoding='utf-8'))
        members = {f['path']: f['sha256'] for a in records['archives'] if a['family'] == 'commercial-iecc' for f in a['files']}
    key = capture(Path(args.idf_root), members)
    OUTPUT.write_text(layered(key, 4)+'\n', encoding='utf-8', newline='\n')   # one zone per line
    print(f'{len(key["cases"])} IECC cases written to {OUTPUT.relative_to(ROOT).as_posix()}')


if __name__ == '__main__':
    main()
