"""Schema, physical, referential, schedule, provenance and capability checks."""
import argparse
import json
from pathlib import Path
from scripts.definition_contract import (DefinitionError, ValidationReport, PRIMARY, TABLES,
    validate_record, validate_evidence, _validate_parameter, canonical)
from scripts.semantics import profile, DAY_TYPES


def validate(bundle):
    report=ValidationReport()
    inventories={table:{r['id']:r for r in bundle.get(table,[])} for table in TABLES}
    for table in TABLES:
        if len(inventories[table]) != len(bundle.get(table,[])):
            report.errors.append('Duplicate IDs in '+table)
    evidence_ids=set(inventories['provenance'])
    schedule_ids=set(inventories['schedules'])
    for row in bundle.get('provenance',[]):
        try:validate_evidence(row)
        except DefinitionError as error:report.errors.append(row['id']+': '+str(error))
    def inspect(value,path):
        if isinstance(value,dict):
            if {'value','unit','status'} <= value.keys():
                try:_validate_parameter(value,path)
                except DefinitionError as error:report.errors.append(str(error))
                if value.get('evidence_id') not in evidence_ids:
                    report.errors.append('Orphan field evidence: '+path)
                val=value['value'];unit=value['unit']
                if isinstance(val,(float,int)) and not isinstance(val,bool):
                    if unit in {'W','W/m2','m3/s','m3/s/m2','m3/s/person','1/h','person/m2','m','kg/m3','J/kg/K','W/m/K','W/m2/K'} and val < 0:
                        report.errors.append('Negative physical value: '+path)
                    if any(k in path for k in ('shgc','visible_transmittance','fraction_')) and unit=='1' and not 0<=val<=1:
                        report.errors.append('Physical fraction out of range: '+path)
            for k,v in value.items():
                if k=='evidence_ids' and any(e not in evidence_ids for e in v):
                    report.errors.append('Orphan evidence: '+path)
                if k=='schedule_id' and v is not None and v not in schedule_ids:
                    report.errors.append('Orphan schedule: '+str(v))
                if k.endswith('_schedule_id') and isinstance(v,dict) and v.get('value') is not None and v['value'] not in schedule_ids:
                    report.errors.append('Orphan control schedule: '+str(v['value']))
                inspect(v,path+'/'+k)
        elif isinstance(value,list):
            for i,v in enumerate(value):inspect(v,path+f'/{i}')
    for kind,table in PRIMARY.items():
        for row in bundle.get(table,[]):
            try:validate_record(kind,row)
            except DefinitionError as error:report.errors.append(row['id']+': '+str(error))
            inspect(row,row['id'])
            for key,target in [('component_ids','components'),('service_ids','services')]:
                if any(i not in inventories[target] for i in row.get(key,[])):
                    report.errors.append('Orphan '+key+': '+row['id'])
            for layer in row.get('layers',[]):
                if layer['material_id'] not in inventories['materials']:
                    report.errors.append('Orphan material: '+row['id'])
            for ids in row.get('elements',{}).values():
                if any(i not in inventories['constructions'] for i in ids):
                    report.errors.append('Orphan construction element: '+row['id'])
    for table in ('components','services'):
        for row in bundle.get(table,[]):inspect(row,row['id'])
    for schedule in bundle.get('schedules',[]):
        if 'rules' in schedule:
            try:
                for rule in schedule['rules']:
                    if len(rule['values']) not in {1,24}:
                        raise DefinitionError('Invalid rule length')
                    if not set(rule['day_types'].split('|')) <= DAY_TYPES:
                        raise DefinitionError('Unknown day selector')
                    canonical(rule)
            except (KeyError,ValueError) as error:report.errors.append(schedule['id']+': '+str(error))
        elif 'values' in schedule and len(schedule['values']) not in {8760,8784}:
            report.errors.append('Invalid annual realization length: '+schedule['id'])
    for recipe in bundle.get('compositions',[]):
        if abs(sum(m['weight'] for m in recipe['members'])-1)>1e-10:
            report.errors.append('Composition weights do not sum to one: '+recipe['id'])
        if any(m['program_id'] not in inventories['programs'] for m in recipe['members']):
            report.errors.append('Orphan composition member: '+recipe['id'])
    for table in PRIMARY.values():
        report.coverage[table]={'records':len(bundle.get(table,[])),
            'assumed':sum(r['derivation']=='assumed' for r in bundle.get(table,[])),
            'fields_known':sum(v['value'] is not None for r in bundle.get(table,[]) for v in r['parameters'].values()),
            'fields_unknown':sum(v['value'] is None for r in bundle.get(table,[]) for v in r['parameters'].values())}
    try:canonical(bundle)
    except (ValueError,TypeError) as error:report.errors.append(str(error))
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);args=p.parse_args()
    from scripts.definition_release import read_bundle
    report=validate(read_bundle(args.input));print(json.dumps(report.__dict__,indent=2))
    if report.errors:raise SystemExit(1)


if __name__=='__main__':main()
