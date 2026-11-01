"""The 90.1 small-hotel elevator from the PNNL prototypes: the input of the release 2.3.0 exception (ADR 0053 section 2).

python -m scripts.pnnl_point_loads           # write data/program-inputs/pnnl-point-load-exceptions-v1.json from the PNNL IDFs
python -m scripts.pnnl_point_loads --check   # rebuild from the IDFs and fail unless the committed file equals it

openstudio-standards gives the 90.1 small hotel `Elec/MechRoom` space type 198.2 W/ft2 of electric equipment
(2133.4 W/m2): DOE Ref's 32 110 W elevator motor over the 15.05 m2 `ElevatorCoreFlr1` zone. PNNL's 90.1
prototypes put 16 024.3 W in the same zone (`ElevatorCoreFlr1_Elevators_Equip`, STD2004 to STD2019). The owner
took the PNNL value as a recorded exception to the reconciliation rule that prototype and openstudio-standards
load differences do not matter (ADR 0037; ADR 0053 section 2). This script reads, for each template, the
object's design level and the zone's floor area (the sum of its floor surfaces; the IDF leaves the Zone floor
area to EnergyPlus) from the Buffalo file the 90.1 lighting controls cite (ADR 0044), requires every city of the
template to agree, and records the per-area value with the source file. The IDFs sit outside the repository
(`ATLAS_PROTOTYPE_ROOT`, default `D:/Prototype Building Models`, pinned by `sources/reference-models-lock.json`);
the committed input is what the release edit reads (`scripts.atlas_edits`).
"""
import argparse
import json
import math
from pathlib import Path

from scripts import idf_reader
from scripts.common import ROOT
from scripts.lighting_controls import Extract, prototype_root
from scripts.iecc_commercial_zones import BASE_CITY

OUTPUT = ROOT/'data/program-inputs/pnnl-point-load-exceptions-v1.json'
EXTRACTION_DATE = '2026-11-01'
ADR = 'docs/adr/0053-release-2-3-0-data-corrections.md'
FAMILY = 'commercial-ashrae901'
# The release 2.2.0 program each exception replaces a load of (IDs move with the edit; scripts.atlas_edits).
EXCEPTIONS = (
    {'template': '90.1-2007', 'standard': 'STD2007', 'program_id': '90-1-2007.small-hotel.source.elec-mech-room.55e131'},
    {'template': '90.1-2013', 'standard': 'STD2013', 'program_id': '90-1-2013.small-hotel.source.elec-mech-room.9b4216'},
    {'template': '90.1-2019', 'standard': 'STD2019', 'program_id': '90-1-2019.small-hotel.source.elec-mech-room.ac5040'})
PROTOTYPE = 'HotelSmall'
ZONE = 'ElevatorCoreFlr1'
OBJECT = 'ElevatorCoreFlr1_Elevators_Equip'
QUANTITY = 'electric_equipment'
INTERPRETATION = ('PNNL 90.1 prototype elevator lift motor in the ground-floor elevator core, taken in place of the '
                  'openstudio-standards space-type density (DOE Ref\'s 32 110 W motor) as the owner\'s recorded exception to '
                  'the reconciliation rule (ADR 0037, ADR 0053 section 2). The same value in every city of the template. '
                  'openstudio-standards Prototype.SmallHotel.rb adds a second 32 110 W motor and a 125 W lights/fan object '
                  'on this zone; the atlas takes neither (the PNNL prototype has no second motor).')
TRANSFORMATION = 'ElectricEquipment Design Level (W) over the zone floor area (sum of its floor surfaces, m2)'


def floor_area(model, zone):
    return math.fsum(idf_reader.area(s['vertices']) for s in model.surfaces()
                     if s['type'] == 'floor' and s['zone'].lower() == zone.lower())


def read(path):
    """(design level W, zone floor area m2, fractions, schedule, subcategory) of the elevator object."""
    model = idf_reader.Model(path)
    found = [o for o in model.loads('electricequipment') if o['name'].lower() == OBJECT.lower()]
    if len(found) != 1 or found[0]['zones'] != [ZONE.lower()] or found[0]['method'] != 'equipmentlevel':
        raise ValueError(f'{path}: expected one EquipmentLevel {OBJECT} in {ZONE}')
    item = found[0]
    return {'design_level_W': item['values'][0], 'zone_floor_area_m2': floor_area(model, ZONE),
            'fractions': item['fractions'], 'schedule': item['schedule'], 'subcategory': item['subcategory']}


def build(root=None):
    root = Path(root or prototype_root())
    extract = Extract(root)
    folder = root/FAMILY/f'ASHRAE901_{PROTOTYPE}'
    out = []
    for entry in EXCEPTIONS:
        files = sorted(folder.glob(f'ASHRAE901_{PROTOTYPE}_{entry["standard"]}_*.idf'))
        if not files:
            raise SystemExit(f'No {entry["standard"]} {PROTOTYPE} IDFs under {folder}; set ATLAS_PROTOTYPE_ROOT')
        values = {f.stem.rsplit('_', 1)[1]: read(f) for f in files}
        base = values[BASE_CITY]
        for city, value in values.items():
            if value['design_level_W'] != base['design_level_W'] or not math.isclose(value['zone_floor_area_m2'], base['zone_floor_area_m2'], rel_tol=1e-9):
                raise ValueError(f'{entry["template"]} {city}: the elevator or its zone differs from {BASE_CITY}')
        path = folder/f'ASHRAE901_{PROTOTYPE}_{entry["standard"]}_{BASE_CITY}.idf'
        source_file = extract.prototype_file(FAMILY, path)
        out.append({**entry, 'folder': f'commercial/{entry["template"].replace(".", "-")}/small-hotel', 'quantity': QUANTITY,
                    'zone': ZONE, 'object': OBJECT, 'field': 'Design Level {W}', 'design_level_W': base['design_level_W'],
                    'zone_floor_area_m2': base['zone_floor_area_m2'],
                    'value_W_m2': base['design_level_W']/base['zone_floor_area_m2'], 'unit': 'W/m2',
                    'fractions': base['fractions'], 'schedule': base['schedule'], 'end_use_subcategory': base['subcategory'],
                    'cities': len(values), 'source_file': extract.source_files[source_file]})
    return {'schema_version': '1.0.0', 'decision': ADR, 'extraction_date': EXTRACTION_DATE,
            'description': 'Point loads taken from the PNNL 90.1 prototypes in place of the openstudio-standards space-type '
                           'density (release 2.3.0): the small-hotel elevator lift motor.',
            'interpretation': INTERPRETATION, 'transformation': TRANSFORMATION, 'exceptions': out}


def encode(document):
    return (json.dumps(document, indent=1, sort_keys=True, ensure_ascii=False)+'\n').encode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    data = encode(build())
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_bytes() != data:
            raise SystemExit(f'{OUTPUT.relative_to(ROOT)} differs from the PNNL IDFs; run python -m scripts.pnnl_point_loads')
        print(f'{OUTPUT.relative_to(ROOT).as_posix()} reproduces from the PNNL IDFs')
        return
    OUTPUT.write_bytes(data)
    print(f'Wrote {OUTPUT.relative_to(ROOT).as_posix()}: {len(json.loads(data)["exceptions"])} exceptions')


if __name__ == '__main__':
    main()
