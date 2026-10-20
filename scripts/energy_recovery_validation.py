"""Focused recovery validation and independent pilot exports; no site/CI work."""
import argparse
import copy
from collections import Counter
import hashlib
import math

from jsonschema import Draft202012Validator
from scripts.common import ROOT,load_json,dump_json
from scripts.definition_release import read_bundle
from scripts.energy_source_recovery import readiness
from scripts.energy_json_review import material_requirements
from scripts.recover_energy_inputs import BASE,CONSTRUCTION,SYSTEM

SCHEMA=ROOT/'schemas/energy-source-recovery-v1.schema.json'
RECEIPT=ROOT/'docs/reviews/energy-source-recovery-validation.json'
PILOTS=ROOT/'docs/examples/energy-recovery'
UNITS={'1','category','W','W/W','m3','degC','m2','W/m2/K','W/K','rad','Pa','W/(m3/s)','m2*K/W','1/s'}
FRACTIONS={'shgc','visible_transmittance','solar_absorptance','thermal_absorptance','visible_absorptance',
           'fraction_heat_load_served','fraction_cool_load_served','fraction_dhw_load_served',
           'collector_rated_optical_efficiency','solar_fraction','water_heating_efficiency'}


def operands(value):
    if isinstance(value,dict):
        if {'value','unit','status','origin','evidence'}<=value.keys():
            yield value
        else:
            for v in value.values():
                yield from operands(v)
    elif isinstance(value,list):
        for v in value:
            yield from operands(v)


def validate(c,s,bundle,check_inputs=True):
    schema=load_json(SCHEMA)
    validator=Draft202012Validator(schema)
    count=0
    layer_fields=0
    for data,table in [(c,'constructions'),(s,'hvac_systems')]:
        validator.validate(data)
        if set(data['records'])!={r['id'] for r in bundle[table]}:
            raise ValueError('Inventory has missing/orphan recovery records')
        if check_inputs:
            for path,expected in data['input_sha256'].items():
                actual=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
                if actual!=expected:
                    raise ValueError('Stale recovery input: '+path)
        sources={**data['source_files'],**data['residential_source_files']}
        for p in operands(data):
            Draft202012Validator({'$ref':'#/$defs/operand','$defs':schema['$defs']}).validate(p)
            count+=1
            if p['unit'] not in UNITS or (p['value'] is None)!=(p['status']=='unknown'):
                raise ValueError('Invalid physical unit/status')
            val=p['value']
            if val is not None and p['unit']!='category':
                if isinstance(val,bool) or not isinstance(val,(int,float)) or not math.isfinite(val):
                    raise ValueError('Invalid physical value')
                if p['unit']!='degC' and val<0:
                    raise ValueError('Negative physical value')
                field=p['evidence']['source_locator'].split('/')[-1]
                if field in FRACTIONS and val>1:
                    raise ValueError('Invalid physical fraction')
            e=p['evidence']
            source_path=e['source_locator'].split('#')[0]
            if source_path not in sources or sources[source_path]['sha256']!=e['source_file_sha256'] or sources[source_path]['source_revision']!=e['source_revision']:
                raise ValueError('Invalid field provenance')
        for rows in [data['records'],data.get('water_heaters',{})]:
            for identity,row in rows.items():
                if row['id']!=identity or row['readiness']!=readiness(row):
                    raise ValueError('Invalid identity/readiness disposition')
        baseline={r['id']:r for r in bundle[table]}
        for identity,row in data['records'].items():
            if row['source_id']!=baseline[identity]['source_id']:
                raise ValueError('Recovery source identity mismatch')
    for row in c['records'].values():
        layers=row['recovered'].get('layers',[])
        if layers and [l['order'] for l in layers]!=list(range(len(layers))):
            raise ValueError('Construction layer order changed')
        for layer in layers:
            props=layer['properties']
            required=material_requirements(props)
            if not required or any(props.get(k) is None for k in required):
                raise ValueError('Recovered construction has missing physical material properties')
            for field in required-{'model','roughness','gas_type','optical_data_type'}:
                value=props[field]
                if field=='solar_diffusing':
                    if not isinstance(value,bool):
                        raise ValueError('Invalid physical glazing flag')
                    continue
                if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
                    raise ValueError('Invalid physical layer value: '+field)
                fraction=field in FRACTIONS or field=='solar_heat_gain_coefficient' or any(
                    part in field for part in ('transmittance_at','reflectance_at','emissivity','dirt_correction'))
                if (fraction and not 0<=value<=1) or (not fraction and value<=0):
                    raise ValueError('Invalid physical layer range: '+field)
                layer_fields+=1
    material_ids={r['id'] for r in bundle['materials']}
    for identity,row in c['materials'].items():
        if row['id']!=identity or identity not in material_ids:
            raise ValueError('Orphan material default recovery')
    return {'schema_version':'1.0.0','date':'2026-10-12','validation_scope':'Recovery schema, physical fields, provenance, inventory and source identity; no simulation/site build.',
            'construction_records':len(c['records']),'hvac_records':len(s['records']),
            'dhw_solar_records':len(s['water_heaters']),'validated_operands':count,
            'validated_layer_physical_fields':layer_fields,
            'recovered_glazing_assemblies':sum('source_candidates' in r['recovered'] for r in c['records'].values()),
            'ground_U_recoveries':sum(r['recovered'].get('ground_model')=='layered_U_ground_construction' for r in c['records'].values()),
            'material_default_instances':len(c['materials']),
            'construction_source_dispositions':dict(sorted(Counter(r['readiness'] for r in c['records'].values()).items())),
            'hvac_source_dispositions':dict(sorted(Counter(r['readiness'] for r in s['records'].values()).items())),
            'dhw_solar_source_dispositions':dict(sorted(Counter(r['readiness'] for r in s['water_heaters'].values()).items()))}


def pilot_exports(c,s,bundle):
    by={r['id']:r for r in bundle['constructions']}
    package=by['construction-93cb2afe2fe44c8e084b9b99']
    selected={}
    for role,identities in package['elements'].items():
        matches=[i for i in identities if by[i].get('climate') in {None,'ClimateZone 4'}]
        if len(matches)!=1:
            raise ValueError('Pilot construction selection is ambiguous: '+role)
        selected[role]=matches[0]
    # Explicit source pilot choices, never an automatic construction/system match.
    medium_system='hvac_system-391c926cf557a50df9f3d0f8'
    residential=next(r for r in bundle['constructions'] if r.get('role')=='dwelling_enclosure')
    residential_system=next(r for r in bundle['hvac_systems'] if r['source_id']==residential['source_id'])

    def construction_pilot(identities,context):
        objects=[]
        for identity in identities:
            raw=copy.deepcopy(by[identity])
            raw.pop('air_exchange',None)  # Source program ventilation is not copied into this independent pilot.
            objects.append({'definition':raw,'source_recovery':c['records'][identity]})
        mids={l['material_id'] for obj in objects for l in obj['definition'].get('layers',[])}
        return {'schema_version':'1.0.0','kind':'construction','stage':'source_recovery_pilot',
                'source_context':context,'objects':objects,
                'material_default_recovery':{i:c['materials'][i] for i in sorted(mids) if i in c['materials']},
                'unresolved':sorted({v for i in identities for v in c['records'][i]['unresolved']}),
                'required_bindings':sorted({v for i in identities for v in c['records'][i]['required_bindings']}),
                'boundary':'Independent pilot; source definitions plus recovery, not final ready export. Program loads/ventilation and consumer geometry are outside this payload.'}

    def system_pilot(identity,water):
        row=s['records'][identity]
        return {'schema_version':'1.0.0','kind':'system','stage':'source_recovery_pilot',
                'source_context':row['source_context'],'hvac_source_recovery':row,'dhw_solar_source_recovery':water,
                'unresolved':sorted(set(row['unresolved'])|{v for r in water for v in r['unresolved']}),
                'required_bindings':sorted(set(row['required_bindings'])|{v for r in water for v in r['required_bindings']}),
                'boundary':'Independent nominal source equipment pilot; no program demand, geometry or sizing is embedded. Unknown performance/controls blocks ready export.'}
    medium_water=[r for r in s['water_heaters'].values() if r['source_context'].get('building_type')=='MediumOffice' and r['source_context'].get('template')=='90.1-2019']
    residential_water=[r for r in s['water_heaters'].values() if r.get('source_id')==residential['source_id']]
    return {'medium-office-construction':construction_pilot(list(selected.values()),
                {'building_type':'MediumOffice','template':'90.1-2019','source_climate_group':'ClimateZone 4','source_package_id':package['id'],'selected_elements':selected}),
            'medium-office-system':system_pilot(medium_system,medium_water),
            'residential-construction':construction_pilot([residential['id']],c['records'][residential['id']]['source_context']),
            'residential-system':system_pilot(residential_system['id'],residential_water)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    c,s,bundle=load_json(CONSTRUCTION),load_json(SYSTEM),read_bundle(BASE)
    receipt=validate(c,s,bundle)
    outputs={PILOTS/(name+'.json'):value for name,value in pilot_exports(c,s,bundle).items()}
    receipt['artifact_sha256']={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [CONSTRUCTION,SYSTEM,SCHEMA]}
    outputs[RECEIPT]=receipt
    for path,value in outputs.items():
        if args.check:
            if load_json(path)!=value:
                raise ValueError('Pilot/receipt differs: '+str(path))
        else:
            dump_json(path,value)
    print(f'Recovery schema/physical/provenance/inventory checks passed; {receipt["validated_operands"]} operands, four independent pilots')


if __name__=='__main__':
    main()
