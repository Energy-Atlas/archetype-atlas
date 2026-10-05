"""Inventory finite schedule availability within the user-selected release scope."""
import argparse
from collections import Counter
from pathlib import Path

from scripts.common import ROOT, dump_json, load_atlas, load_json

FIELDS = ['occupancy_schedule_id','lighting_schedule_id','electric_equipment_schedule_id',
          'gas_equipment_schedule_id','heating_setpoint_schedule_id','cooling_setpoint_schedule_id',
          'service_water_heating_schedule_id']
COLUMNS = ['occupants','lighting_interior','plug_loads_other','plug_loads_tv','cooking_range',
           'clothes_washer','clothes_dryer','dishwasher','hot_water_fixtures','hot_water_dishwasher',
           'hot_water_clothes_washer','ceiling_fan','refrigerator','freezer']
EXTENSIONS = ['electric_vehicle','lighting_exterior']


def build(data=None, resolutions=None, scope=None, supplement_version='v0.4.0'):
    data = data or load_atlas(ROOT/'data/releases/v0.2.0')
    if resolutions is None:
        resolutions = load_json(ROOT/'data/resolution-releases/v0.4.0/resolutions.json')
    scope = scope or load_json(ROOT/'sources/schedule-release-scope.json')
    extensions = [c for c in EXTENSIONS if c not in scope.get('excluded_residential_end_uses', [])]
    applied = {(r['record_id'],r['field']):r for r in resolutions['resolutions']}
    excluded = set(scope['excluded_commercial_space_types'])
    programs = [p for p in data['programs'] if p['source_space_type'] not in excluded]
    missing, statuses = [], Counter()
    for p in programs:
        for field in FIELDS:
            resolved = applied.get((p['id'],field))
            disabled = applied.get((p['id'],'conditioning'))
            if p[field] is not None:
                statuses['source'] += 1
            elif resolved is not None:
                statuses['explicit_resolution'] += 1
            elif field.endswith('setpoint_schedule_id') and disabled:
                statuses['disabled_conditioning'] += 1
            else:
                statuses['unknown'] += 1
                missing.append({'record_id':p['id'],'building_type':p['building_type'],
                                'template':p['template'],'program':p['program'],
                                'source_space_type':p['source_space_type'],'field':field})
    residential_missing, extension_missing = [], []
    for row in data['residential_archetypes']:
        for col in COLUMNS + extensions:
            if (row['id'],'profile:'+col) not in applied:
                target = residential_missing if col in COLUMNS else extension_missing
                target.append({'record_id':row['id'],'source_building_id':row['source_building_id'],
                               'building_type':row['building_type'],'column':col,
                               'reason':'No executed or explicit resolved profile column; raw absence selections are evidence for a future reviewed zero, not an applied profile.'})
    return {'schema_version':'0.1.0','base_release':'v0.2.0','resolution_supplement':supplement_version,
            'scope':scope,'near_full_coverage_claim':False,
            'commercial':{'active_program_records':len(programs),'excluded_program_records':len(data['programs'])-len(programs),
                'required_fields':FIELDS,'required_schedule_fields':len(programs)*len(FIELDS),
                'statuses':dict(sorted(statuses.items())), 'missing_schedule_fields':len(missing),
                'missing_by_field':dict(sorted(Counter(m['field'] for m in missing).items())),
                'missing_by_building':dict(sorted(Counter(m['building_type'] for m in missing).items())),
                'missing_records':missing},
            'residential':{'record_count':len(data['residential_archetypes']),
                'assessed_columns':COLUMNS,'assessed_profile_fields':len(COLUMNS)*len(data['residential_archetypes']),
                'missing_profile_fields':len(residential_missing),
                'missing_by_column':dict(sorted(Counter(m['column'] for m in residential_missing).items())),
                'missing_records':residential_missing,
                'additional_end_uses':{'columns':extensions,'missing_by_column':dict(sorted(Counter(m['column'] for m in extension_missing).items())),
                                       'missing_records':extension_missing}},
            'limitations':['Counts describe source-input records and explicit variants, not all stock combinations or simulation readiness.',
                           'Residential defaults and reviewed absences are finite record-specific variants, not inferred from missing stochastic columns.',
                           'Additional end uses are assessed only when explicitly in the selected release scope.',
                           'Shared commercial water services require a supported beneficiary allocation; a heater location alone is insufficient.',
                           'HVAC unavailability and complete magnitudes/control application are excluded from the current schedule milestone.',
                           'Reference-location fan/lighting variants and exact DOE/PNNL generated-model equivalence remain separate evidence tasks.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,default=ROOT/'docs/validation/schedule-coverage.json')
    args = parser.parse_args()
    report = build()
    dump_json(args.report,report)
    print('Active commercial gaps:',report['commercial']['missing_schedule_fields'],
          '; residential assessed-column gaps:',report['residential']['missing_profile_fields'],
          '; HVAC unavailability excluded')


if __name__ == '__main__':
    main()
