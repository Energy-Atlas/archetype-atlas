"""Elevators and kitchen reach-ins of the PNNL 90.1 prototypes: the input of the release 2.4.0 services (ADR 0060 section 3).

python -m scripts.pnnl_services           # write data/program-inputs/pnnl-building-services-v1.json from the PNNL IDFs
python -m scripts.pnnl_services --check   # rebuild from the IDFs and fail unless the committed file equals it

The atlas 90.1 programs take their electric equipment from openstudio-standards space types, which carry the PNNL
elevator lift motors only in the small hotel (ADR 0053 section 2) and the outpatient elevator lights and fan, and no
kitchen reach-in refrigerator or freezer. The PNNL 90.1 prototypes carry them as objects of their own:
- zone `ElectricEquipment` with end-use subcategory ElevatorLift or ElevatorLightsFan (medium office, both apartments,
  small hotel, outpatient, secondary school) and ReachInFreezer or ReachInRefrigerator (the kitchens of both restaurants,
  both schools, the hospital and the large hotel);
- `Exterior:FuelEquipment` Elevators and Elevators_Lights_Fan (hospital, large hotel, large office), with no zone.

The owner decided to add them where the source definitions carry them (2026-11-01, review round 2, G7). The IECC
commercial family already reads the same objects of the PNNL IECC prototypes as building services (ADR 0040 item 9;
`scripts.iecc_commercial_values`), and this script reads the 90.1 ones the same way: a zone object is a service
instantiated once per building in its zone, with its heat fractions, serving the program of that zone's space type; an
exterior object is a building-level service whose power is all lost (no zone heat). Each value, schedule and fraction
must agree in the 19 locations of a template; the evidence cites the Buffalo file. The two objects the atlas programs
already carry are left out with their reason (`EXCLUDED`).
"""
import argparse
import json

from scripts import idf_schedules
from scripts.common import ROOT
from scripts.iecc_commercial_values import ELEVATOR, REACH_IN, other_services, zone_objects
from scripts.iecc_commercial_zones import TYPES
from scripts.pnnl_901 import ADR, EXTRACTION_DATE, Extract, Models, YEARS, same_everywhere
from scripts.reconciliation_values import KINDS, ruleset

OUTPUT = ROOT/'data/program-inputs/pnnl-building-services-v1.json'
SUBCATEGORIES = {s.lower() for s in ('ElevatorLift', 'ElevatorLightsFan', 'ReachInFreezer', 'ReachInRefrigerator')}
# Objects whose load an atlas 90.1 program already carries: (PNNL type, object name) -> reason.
EXCLUDED = {
    ('HotelSmall', 'ElevatorCoreFlr1_Elevators_Equip'):
        'The small-hotel Elec/MechRoom program carries this lift motor as its electric equipment (1064.717 W/m2, the PNNL '
        'value over the zone; ADR 0053 section 2).',
    ('OutPatientHealthCare', 'Elevators_Lights_Fan'):
        'The outpatient ElevatorPumpRoom program carries this lights and fan load as its openstudio-standards electric '
        'equipment density (the PNNL zone has no other electric equipment; ADR 0053 section 2).'}
NOTE = ('PNNL ASHRAE 90.1 prototype building service (ADR 0060 section 3): the same object in all 19 locations, read as the '
        'IECC family reads it (ADR 0040 item 9).')


class Services:
    def __init__(self, extract):
        self.x = extract
        self.schedules, self.excluded = {}, []

    def schedule(self, models, name):
        """A definition schedule from the IDF Schedule:Compact, checked over the year, keyed by its source name."""
        compact = same_everywhere({c: m.schedules().get(name.lower()) for c, m in models.models.items()}, f'schedule {name}')
        if compact is None:
            raise ValueError(f'No Schedule:Compact {name} in {models.pnnl} {models.template}')
        days = idf_schedules.calendar_days(models.base.holidays())
        rules = ruleset(compact)
        expected, _ = idf_schedules.evaluate_compact(compact, days)
        got = idf_schedules.evaluate_ruleset(rules, lambda r: r['values']*(24//len(r['values'])), days)
        if any(not (expected[k] is None and got[k] is None) and not idf_schedules.same(expected[k], got[k]) for k in days):
            raise ValueError(f'Converted {name} differs from its source ({models.pnnl} {models.template})')
        evidence = self.x.cite(models.file, f'Schedule:Compact {compact[0]}', compact[1:], compact[1] or 'schedule type limits',
                               'compact For order to last-specific-wins rules; Until times to hourly energy-conserving means',
                               'PNNL ASHRAE 90.1 prototype source schedule (ADR 0060 section 3); checked over the full year, holidays '
                               'and design days.')
        schedule_type, units = KINDS['fraction']
        key = f'{models.folder()}|{compact[0]}'
        self.schedules[key] = {'source_name': compact[0], 'schedule_type': schedule_type, 'units': units, 'interpolation': 'none',
                               'time_resolution_minutes': 60, 'evidence_ids': [evidence], 'rules': rules}
        return key

    def zone_items(self, models):
        def read(model):
            _, items = zone_objects(model, models.geometry)
            return sorted(({k: v for k, v in i.items()} for i in items if i['subcategory'].lower().replace(' ', '') in SUBCATEGORIES
                           and i['subcategory'].lower().replace(' ', '') in ELEVATOR | REACH_IN), key=lambda i: (i['zone'], i['name']))
        return same_everywhere({c: read(m) for c, m in models.models.items()}, f'{models.pnnl} {models.template} zone services')

    def exterior_items(self, models):
        read = lambda model: sorted((i for i in other_services(model) if i['end_use'] == 'elevator'), key=lambda i: i['name'])
        return same_everywhere({c: read(m) for c, m in models.models.items()}, f'{models.pnnl} {models.template} exterior services')

    def entries(self, models):
        out = []
        for item in self.zone_items(models):
            if (models.pnnl, item['name']) in EXCLUDED:
                self.excluded.append({'folder': models.folder(), 'object': item['name'], 'zone': models.name(item['zone']),
                                      'reason': EXCLUDED[models.pnnl, item['name']]})
                continue
            if item['method'] != 'equipmentlevel':
                raise ValueError(f'{item["name"]}: {item["method"]}')
            watts = item['values'][0]*item['multiplier']
            fractions = {k: v for k, v in item['fractions'].items() if v is not None}
            evidence = self.x.cite(models.file, f'ElectricEquipment {item["name"]} ({item["subcategory"]})',
                                   {k: item[k] for k in ('method', 'values', 'schedule', 'fractions', 'multiplier', 'zone')},
                                   'W or W/m2; fractions', 'design level times the zone multiplier, instantiated once per building', NOTE)
            out.append({'folder': models.folder(), 'template': models.template, 'building_type': models.building_type,
                        'end_use': 'elevator' if item['subcategory'].lower().replace(' ', '') in ELEVATOR else 'refrigeration_equipment',
                        'name': item['name'], 'subcategory': item['subcategory'], 'zone': models.name(item['zone']),
                        'space_type': models.space[item['zone']][1], 'source_zone_multiplier': item['multiplier'],
                        'value_W': watts, 'fractions': fractions, 'fuel': 'Electricity',
                        'schedule': self.schedule(models, item['schedule']), 'evidence_id': evidence})
        for item in self.exterior_items(models):
            if item['fuel'].lower() != 'electricity':
                raise ValueError(f'{item["name"]}: fuel {item["fuel"]}')
            evidence = self.x.cite(models.file, f'Exterior:FuelEquipment {item["name"]}', item, 'W', 'object fields as written in the IDF',
                                   NOTE+' Exterior equipment has no zone: its power is all lost (no zone heat).')
            out.append({'folder': models.folder(), 'template': models.template, 'building_type': models.building_type,
                        'end_use': 'elevator', 'name': item['name'], 'subcategory': item['subcategory'], 'zone': None,
                        'space_type': None, 'value_W': item['design_level_W'], 'fractions': {'lost': 1.0}, 'fuel': item['fuel'],
                        'schedule': self.schedule(models, item['schedule']), 'evidence_id': evidence})
        return out


def build(root=None):
    extract = Extract(root)
    services = Services(extract)
    out = []
    for year in YEARS:
        for pnnl in TYPES:
            out += services.entries(Models(extract, pnnl, year))
    used = {s['schedule'] for s in out}
    evidence = {e for s in out for e in [s['evidence_id']]} | {e for k in used for e in services.schedules[k]['evidence_ids']}
    rows = {k: {f: v for f, v in extract.evidence[k].items() if f != 'id'} for k in sorted(evidence)}
    files = {r['source_file_id'] for r in rows.values()}
    return {'schema_version': '1.0.0', 'decision': ADR, 'extraction_date': EXTRACTION_DATE,
            'description': 'Elevators and kitchen reach-in refrigeration of the PNNL 90.1 prototypes as building services '
                           '(release 2.4.0).',
            'services': sorted(out, key=lambda s: (s['folder'], s['end_use'], s['name'])),
            'excluded': sorted(services.excluded, key=lambda e: (e['folder'], e['object'])),
            'schedules': {k: services.schedules[k] for k in sorted(used)}, 'evidence': rows,
            'source_files': {k: {f: v for f, v in extract.source_files[k].items() if f != 'id'} for k in sorted(files)}}


def encode(document):
    return (json.dumps(document, indent=1, sort_keys=True, ensure_ascii=False)+'\n').encode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    data = encode(build())
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_bytes() != data:
            raise SystemExit(f'{OUTPUT.relative_to(ROOT)} differs from the PNNL IDFs; run python -m scripts.pnnl_services')
        print(f'{OUTPUT.relative_to(ROOT).as_posix()} reproduces from the PNNL IDFs')
        return
    OUTPUT.write_bytes(data)
    document = json.loads(data)
    print(f'Wrote {OUTPUT.relative_to(ROOT).as_posix()}: {len(document["services"])} services in '
          f'{len({s["folder"] for s in document["services"]})} folders, {len(document["excluded"])} objects left out')


if __name__ == '__main__':
    main()
