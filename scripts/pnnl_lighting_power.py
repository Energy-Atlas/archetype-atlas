"""Office lighting power from the PNNL 90.1 prototypes: the input of the release 2.4.0 exception (ADR 0060 section 2).

python -m scripts.pnnl_lighting_power            # write data/program-inputs/pnnl-lighting-power-exceptions-v1.json
python -m scripts.pnnl_lighting_power --check    # rebuild from the IDFs and fail unless the committed file equals it
python -m scripts.pnnl_lighting_power --review   # also write docs/reviews/lighting-power-pnnl-vs-90-1.md (every 90.1 program)

The atlas 90.1 programs take their lighting power density from the openstudio-standards space-type rows; the whole-building
office rows give one code value per template (90.1-2019: 0.64 W/ft2, 6.889 W/m2). PNNL's 90.1 office prototypes give every
zone of the office one Lights density that differs from it (90.1-2019 medium office 6.66362 W/m2). The owner decided that
office lighting power follows PNNL (2026-11-01, review round 2, G5), a recorded exception to the reconciliation rule that
prototype against openstudio-standards load differences do not matter (ADR 0037; ADR 0060 section 2).

This script reads, for each 90.1 template the atlas holds (2007, 2013, 2019) and each office prototype (small, medium,
large), the Lights objects of the zones of each whole-building space type (zones grouped as ADR 0044 groups them), and
records their floor-area-weighted density, the objects and the zones; all 19 locations must agree, and the evidence cites
the Buffalo file. `--review` compares every 90.1 program with a PNNL zone group against the atlas release in the tree (a
review for the owner; nothing else changes).
"""
import argparse
import json
import math
from pathlib import Path

from scripts.common import ROOT
from scripts.iecc_commercial_values import zone_objects
from scripts.iecc_commercial_zones import TYPES
from scripts.pnnl_901 import ADR, EXTRACTION_DATE, Extract, Models, YEARS, same_everywhere

OUTPUT = ROOT/'data/program-inputs/pnnl-lighting-power-exceptions-v1.json'
REVIEW = ROOT/'docs/reviews/lighting-power-pnnl-vs-90-1.md'
OFFICES = ('OfficeSmall', 'OfficeMedium', 'OfficeLarge')
WHOLE_BUILDING = 'WholeBuilding'
INTERPRETATION = ('PNNL ASHRAE 90.1 office prototype lighting power, taken in place of the openstudio-standards whole-building '
                  'office density as the owner\'s recorded exception to the reconciliation rule (ADR 0037, ADR 0060 section 2). '
                  'The same density on every zone of the program and in every location; the lighting schedule and heat fractions '
                  'stay.')
TRANSFORMATION = 'Lights Watts per Zone Floor Area (W/m2), weighted by zone floor area x multiplier over the program\'s zones'


def densities(models, quantity='lighting'):
    """{space type: (W/m2, objects, schedules)} of one type and edition, required equal in every location."""
    per_city = {}
    for city, model in models.models.items():
        objects, _ = zone_objects(model, models.geometry)
        out = {}
        for space_type, zones_ in models.groups.items():
            area = models.group_area(zones_)
            items = [(z, objects[z].get(quantity)) for z in zones_]
            watts = math.fsum(models.area(z)*(o['value'] if o else 0.0) for z, o in items)
            out[space_type] = {'W_m2': watts/area if area else None,
                               'objects': sorted(o['object'] for _, o in items if o),
                               'schedules': sorted({o['schedule'] for _, o in items if o}),
                               'zone_values': sorted({o['value'] for _, o in items if o})}
        per_city[city] = out
    return same_everywhere(per_city, f'{models.pnnl} {models.template} {quantity}')


def build(root=None):
    extract = Extract(root)
    out = []
    for year in YEARS:
        for pnnl in OFFICES:
            models = Models(extract, pnnl, year)
            found = densities(models)
            for space_type, zones_ in sorted(models.groups.items()):
                if not space_type.startswith(WHOLE_BUILDING):
                    continue
                value = found[space_type]
                if len(value['zone_values']) != 1 or len(value['schedules']) != 1:
                    raise ValueError(f'{pnnl} {year} {space_type}: zones differ in lighting {value}')
                out.append({'template': models.template, 'building_type': models.building_type, 'space_type': space_type,
                            'folder': models.folder(), 'program_name': f'{space_type}_{models.building_type}',
                            'quantity': 'lighting', 'value_W_m2': value['zone_values'][0], 'unit': 'W/m2',
                            'zones': [models.name(z) for z in zones_], 'objects': value['objects'],
                            'schedule': value['schedules'][0], 'field': 'Watts per Zone Floor Area {W/m2}',
                            'program_floor_area_m2': models.group_area(zones_), 'cities': len(models.models),
                            'source_file': extract.source_files[models.file]})
    return {'schema_version': '1.0.0', 'decision': ADR, 'extraction_date': EXTRACTION_DATE,
            'description': 'Lighting power taken from the PNNL 90.1 office prototypes in place of the openstudio-standards '
                           'whole-building office density (release 2.4.0).',
            'interpretation': INTERPRETATION, 'transformation': TRANSFORMATION, 'exceptions': out}


def review(root=None, release='2.3.0'):
    """Markdown comparing every 90.1 program that a PNNL zone group represents with the atlas release."""
    from scripts import atlas_delta
    from scripts.lighting_controls import space_type as program_space_type
    files = atlas_delta.files(release)
    programs = {}
    for path, data in files.items():
        if path.startswith('commercial/90-1-') and '/programs/source/' in path:
            record = json.loads(data)
            programs[(record['template'], record['building_type'], program_space_type(record))] = record
    extract = Extract(root)
    rows = []
    for year in YEARS:
        for pnnl in TYPES:
            models = Models(extract, pnnl, year)
            for quantity in ('lighting', 'additional_lighting'):
                found = densities(models, quantity)
                for space_type, value in sorted(found.items()):
                    record = programs.get((models.template, models.building_type, space_type))
                    if record is None or value['W_m2'] is None:
                        continue
                    load = next((l for l in record['loads'] if l['quantity'] == quantity), None)
                    atlas = None if load is None else load['value']
                    if atlas is None and load is not None and 'filling' in load:
                        atlas = load['filling']['set'].get('value')
                    if atlas is None:
                        continue
                    pnnl_value = value['W_m2']
                    if math.isclose(atlas, pnnl_value, rel_tol=1e-5, abs_tol=1e-9):
                        continue
                    rel = (pnnl_value-atlas)/atlas if atlas else math.inf
                    rows.append((models.template, models.building_type, space_type, quantity, atlas, pnnl_value, rel))
    office = {'SmallOffice', 'MediumOffice', 'LargeOffice'}
    lines = ['# Lighting power: PNNL 90.1 prototypes against the atlas 90.1 programs', '',
             f'Generated by `python -m scripts.pnnl_lighting_power --review` from the PNNL 90.1 IDFs (Buffalo, every location equal) '
             f'and atlas release {release}. Each row is a program whose PNNL zone group gives a different floor-area-weighted '
             'density (relative difference above 1e-5). The whole-building office rows take the PNNL value in release 2.4.0 '
             '(ADR 0060 section 2); every other row is listed for the owner and is not changed (the reconciliation rule of ADR '
             '0037: prototype against openstudio-standards load differences do not matter).', '',
             '| Template | Building type | Program (space type) | Quantity | Atlas W/m² | PNNL W/m² | PNNL / atlas − 1 | Release 2.4.0 |',
             '| --- | --- | --- | --- | ---: | ---: | ---: | --- |']
    for template, building_type, space_type, quantity, atlas, pnnl_value, rel in rows:
        action = ('takes PNNL' if building_type in office and space_type.startswith(WHOLE_BUILDING) and quantity == 'lighting'
                  else 'owner list')
        lines.append(f'| {template} | {building_type} | {space_type} | {quantity} | {atlas:.4f} | {pnnl_value:.4f} | {rel:+.1%} | {action} |')
    lines += ['', f'{len(rows)} rows; {sum(r[1] in office and r[2].startswith(WHOLE_BUILDING) and r[3] == "lighting" for r in rows)} '
              'take the PNNL value.', '']
    return '\n'.join(lines)


def encode(document):
    return (json.dumps(document, indent=1, sort_keys=True, ensure_ascii=False)+'\n').encode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--review', action='store_true')
    args = parser.parse_args()
    data = encode(build())
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_bytes() != data:
            raise SystemExit(f'{OUTPUT.relative_to(ROOT)} differs from the PNNL IDFs; run python -m scripts.pnnl_lighting_power')
        print(f'{OUTPUT.relative_to(ROOT).as_posix()} reproduces from the PNNL IDFs')
        return
    OUTPUT.write_bytes(data)
    print(f'Wrote {OUTPUT.relative_to(ROOT).as_posix()}: {len(json.loads(data)["exceptions"])} exceptions')
    if args.review:
        REVIEW.write_text(review(), encoding='utf-8', newline='\n')
        print(f'Wrote {REVIEW.relative_to(ROOT).as_posix()}')


if __name__ == '__main__':
    main()
