"""Schema, physical, referential, schedule, provenance and capability checks."""
import argparse
import json
import calendar
import datetime as dt
import math
from pathlib import Path
from jsonschema import Draft202012Validator
from scripts.common import ROOT, load_json
from scripts.definition_contract import (DefinitionError, ValidationReport, PRIMARY, TABLES,
    validate_record, validate_evidence, _validate_parameter, canonical)
from scripts.semantics import profile, DAY_TYPES


def validate(bundle):
    report=ValidationReport()
    report.errors.extend('Bundle schema: '+e.message for e in
        Draft202012Validator(load_json(ROOT/'schemas/definitions.schema.json')).iter_errors(bundle))
    if report.errors:return report
    inventories={table:{r['id']:r for r in bundle.get(table,[])} for table in TABLES}
    for table in TABLES:
        if len(inventories[table]) != len(bundle.get(table,[])):
            report.errors.append('Duplicate IDs in '+table)
    evidence_ids=set(inventories['provenance'])
    schedule_ids=set(inventories['schedules'])
    for row in bundle.get('provenance',[]):
        try:validate_evidence(row)
        except DefinitionError as error:report.errors.append(row['id']+': '+str(error))
        if row.get('source_file_id') is not None and row['source_file_id'] not in inventories['source_files']:
            report.errors.append('Orphan provenance source file: '+row['id'])
    references={'evidence_ids':'provenance','evidence_id':'provenance','provenance_id':'provenance',
        'source_file_id':'source_files','source_geometry_file_id':'source_files',
        'schedule_id':'schedules','schedule_ids':'schedules','curve_ids':'components',
        'performance_rule_ids':'components','component_ids':'components','service_ids':'services',
        'material_id':'materials','composition_id':'compositions','source_package_id':'constructions',
        'source_definition_id':None}
    all_primary=set().union(*(set(inventories[t]) for t in PRIMARY.values()))
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
                if k in references and v is not None:
                    target=all_primary if references[k] is None else inventories[references[k]]
                    refs=v if isinstance(v,list) else [v]
                    if any(isinstance(ref,str) and ref not in target for ref in refs):
                        report.errors.append('Orphan '+k+': '+path)
                if k.endswith('_schedule_id'):
                    ref=v.get('value') if isinstance(v,dict) else v
                    if ref is not None and ref not in schedule_ids:report.errors.append('Orphan control schedule: '+str(ref))
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
            if row.get('composition_id') and row['composition_id'] not in inventories['compositions']:
                report.errors.append('Orphan composition: '+row['id'])
            for load in row.get('loads',[]):
                if load['basis'] not in {'floor_area','dwelling_unit','person','absolute'}:
                    report.errors.append('Invalid load basis: '+row['id'])
    for table in ('components','services','compositions'):
        for row in bundle.get(table,[]):inspect(row,row['id'])
    for material in bundle.get('materials',[]):
        inspect(material,material['id'])
        for key,val in material.items():
            if isinstance(val,(int,float)) and not isinstance(val,bool):
                if any(unit in key for unit in ('_m','_W_','_kg_','_J_')) and val<=0:
                    report.errors.append('Invalid material property: '+material['id']+'/'+key)
                if any(term in key for term in ('absorptance','transmittance','reflectance','emissivity','shgc')) and not 0<=val<=1:
                    report.errors.append('Invalid material optical property: '+material['id']+'/'+key)
    for schedule in bundle.get('schedules',[]):
        def check_values(values):
            if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in values):
                raise DefinitionError('Invalid schedule numeric values')
            if schedule.get('schedule_type')=='fraction' and any(v < -1e-10 or v > 1+1e-10 for v in values):
                raise DefinitionError('Fraction schedule outside [0,1]')
            if schedule.get('schedule_type')=='activity' and any(v<0 for v in values):
                raise DefinitionError('Negative activity schedule')
        if 'rules' in schedule:
            try:
                for rule in schedule['rules']:
                    if len(rule['values']) not in {1,24}:
                        raise DefinitionError('Invalid rule length')
                    if not set(rule['day_types'].split('|')) <= DAY_TYPES:
                        raise DefinitionError('Unknown day selector')
                    for key in ('start_date','end_date'):dt.date.fromisoformat(rule[key][:10])
                    check_values(rule['values'])
                    canonical(rule)
            except (KeyError,ValueError) as error:report.errors.append(schedule['id']+': '+str(error))
        elif 'annual_values' in schedule or 'values' in schedule:
            values=schedule.get('annual_values',schedule.get('values'))
            year=schedule.get('calendar',{}).get('year')
            expected=8784 if year and calendar.isleap(year) else 8760
            if len(values)!=expected or any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in values):
                report.errors.append('Invalid annual realization length/values: '+schedule['id'])
            try:check_values(values)
            except DefinitionError as error:report.errors.append(schedule['id']+': '+str(error))
        inspect(schedule,schedule['id'])
    for recipe in bundle.get('compositions',[]):
        if abs(sum(m['weight'] for m in recipe['members'])-1)>1e-10:
            report.errors.append('Composition weights do not sum to one: '+recipe['id'])
        if any(m['program_id'] not in inventories['programs'] for m in recipe['members']):
            report.errors.append('Orphan composition member: '+recipe['id'])
    for table in PRIMARY.values():
        report.coverage[table]={'records':len(bundle.get(table,[])),
            'assumed':sum(r['derivation']=='assumed' for r in bundle.get(table,[])),
            'fields_known':sum(v['value'] is not None for r in bundle.get(table,[]) for v in r['parameters'].values()),
            'fields_unknown':sum(v['value'] is None for r in bundle.get(table,[]) for v in r['parameters'].values()),
            'required_consumer_inputs':sorted({i for r in bundle.get(table,[]) for i in r['required_inputs']}),
            'composition_modes':sorted({d for r in bundle.get(table,[]) for d in r.get('available_details',[])})}
    try:canonical(bundle)
    except (ValueError,TypeError) as error:report.errors.append(str(error))
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);args=p.parse_args()
    from scripts.definition_release import read_bundle
    report=validate(read_bundle(args.input));print(json.dumps(report.__dict__,indent=2))
    if report.errors:raise SystemExit(1)


if __name__=='__main__':main()
