"""Whole-dwelling fixture semantics and already determined residential profiles.

Exact selected lookup arguments are evidence. Autosizing and HPXML defaults are
not executed here; nominal ratings do not establish complete equipment models.
"""
import re
from scripts.common import load_json
from scripts.definition_contract import DefinitionBundle, evidence, parameter, record, stable_id


def build_residential(context):
    bundle=DefinitionBundle()
    options={o['id']:o for o in context.atlas['residential_options']}
    original_evidence={e['id']:e for e in context.atlas['provenance']}
    profile_root=context.root/context.policy['dependencies']['resolution']
    profiles={p['record_id']:p for p in load_json(profile_root/'profile-index.json')}
    for source in context.atlas['residential_archetypes']:
        row=record('program',source,'Whole dwelling / '+source['variant'])
        row.update(gate=['residential'],scope='whole_dwelling',detail='SourcePrograms',
                   available_details=['SourcePrograms'],loads=[],service_ids=[],
                   unresolved_options=source['unresolved_options'],
                   required_inputs=['dwelling_unit_count'],climate=source['source_context'].get('ASHRAE IECC Climate Zone 2004'),
                   vintage=source['source_context'].get('Vintage'),readiness='explicitly_incomplete')
        old=original_evidence[source['provenance_id']]
        def proof(locator,value,unit='source option',transform='identity; exact selected fixture or lookup argument',note=None):
            ev=evidence(context,old['source_file_id'],old['locator']+'/'+locator,value,unit,transform,
                note or 'Source fixture; no substitution of unmatched options or model defaults.')
            bundle['provenance'].append(ev);return ev['id']
        ev=proof('fixture',{k:source[k] for k in ('id','source_context','unresolved_options')})
        row['evidence_ids']=[ev]
        selected=[options[i] for i in source['option_ids']]
        arguments={k:v for option in selected for k,v in option['arguments'].items()}
        option_ev={}
        for option in selected:
            op=original_evidence[option['provenance_id']]
            e=evidence(context,op['source_file_id'],op['locator'],option['arguments'],'source argument strings',
                       'retain exact matched lookup arguments','An option binding is not execution of HPXML defaults.')
            bundle['provenance'].append(e)
            for key in option['arguments']:option_ev[key]=e['id']
        descriptor=profiles[source['id']]
        profile=load_json(profile_root/'profiles'/descriptor['profile_file'])
        meta=profile['metadata']
        pe=proof('determined-profile',{'descriptor':descriptor,'metadata':meta},'source profile metadata',
                 'reuse immutable executed realization; channels separated without resampling',
                 'Pinned resolution release; nominal thermostat and weather-proxy limitations retained.')
        schedule_ids={}
        for channel,values in profile['series'].items():
            sid=stable_id('residential-schedule',{'source':source['id'],'channel':channel,'profile_sha256':descriptor['profile_sha256']})
            schedule={'id':sid,'annual_values':values,'units':'degC' if 'setpoint' in channel else '1',
                      'schedule_type':'temperature' if 'setpoint' in channel else 'fraction',
                      'time_resolution_minutes':60,'evidence_ids':[pe],
                      'calendar':{k:meta[k] for k in ('year','seed','interval_convention','weather','unresolved','profile_boundary')},
                      'realization_status':'determined','source_channel':channel}
            bundle['schedules'].append(schedule);schedule_ids[channel]=sid
        channels=('occupants','plug_loads_other','plug_loads_tv','lighting_interior',
                  'hot_water_clothes_washer','clothes_washer','clothes_dryer',
                  'cooking_range','hot_water_fixtures','heating_setpoint','cooling_setpoint')
        for channel in channels:
            sid=schedule_ids.get(channel)
            if 'setpoint' in channel:
                row['parameters'][channel+'_schedule_id']=parameter(sid,'schedule reference',pe)
                continue
            quantity='occupancy' if channel=='occupants' else channel
            value=source['occupants'] if channel=='occupants' else None
            load=parameter(value,'person/dwelling' if channel=='occupants' else ('m3/s/dwelling' if channel.startswith('hot_water') else 'W/dwelling'),
                           proof(channel,value,'person/dwelling' if channel=='occupants' else 'unknown load magnitude'),
                           required_inputs=['dwelling_unit_count'])
            load.update(quantity=quantity,basis='dwelling_unit',schedule_id=sid,
                        demand_id=stable_id('residential-demand',{'source':source['id'],'channel':channel}),scope='whole_dwelling',
                        unresolved_reason=None if value is not None else 'Normalized profile exists; required magnitude/default operands not resolved by schedule-only execution')
            row['loads'].append(load)
        row['parameters']['conditioned_floor_area']=parameter(None,'m2',ev,required_inputs=['conditioned_floor_area'])
        bundle['programs'].append(row)

        construction=record('construction',source,'Dwelling enclosure / '+source['variant'])
        construction.update(gate=['residential'],climate=row['climate'],vintage=row['vintage'],role='dwelling_enclosure',layers=[],
            evidence_ids=[ev],required_inputs=['assembly_layers','geometry','ground_boundary'],
            unresolved_reason='Options define nominal properties; complete assemblies and natural infiltration are unresolved')
        leakage=arguments.get('enclosure_air_leakage','')
        match=re.fullmatch(r'([0-9.]+) ACH50',leakage)
        le=option_ev.get('enclosure_air_leakage',ev)
        construction['air_exchange']={'pressure_test':{
            'rate':parameter(float(match[1])/3600 if match else None,'1/s',le),
            'reference_pressure':parameter(50 if match else None,'Pa',le)},
            'infiltration':parameter(None,'m3/s',le,required_inputs=['pressure_to_natural_infiltration_model','geometry','weather']),
            'outdoor_air':parameter(None,'m3/s',ev),'total_supply':parameter(None,'m3/s',ev)}
        construction['source_options']={k:v for k,v in source['selected_options'].items()
                                        if k.startswith(('Insulation','Windows','Infiltration','Geometry Foundation'))}
        for key in ('ceiling_insulation_r',):
            value=arguments.get(key)
            if value is not None:
                construction['parameters']['nominal_'+key]=parameter(float(value)*.1761101838,'m2*K/W',
                    proof(key,value,'ft2*h*degF/Btu','multiply by 0.1761101838; nominal insulation only'))
        bundle['constructions'].append(construction)

        system=record('hvac_system',source,'Dwelling HVAC / '+source['variant'])
        system.update(gate=['residential'],climate=row['climate'],vintage=row['vintage'],
            system_type='Residential fixture equipment',component_ids=[],schedule_ids=sorted(schedule_ids[c] for c in schedule_ids if 'setpoint' in c),
            connections=[],topology_status='unresolved',required_inputs=['serving_assignment','equipment_details'],evidence_ids=[ev])
        for key,role in (('hvac_heating_system','heating'),('hvac_cooling_system','cooling'),('hvac_heat_pump','heat_pump')):
            label=arguments.get(key)
            if label is None or label=='None':continue
            cid=stable_id('residential-component',{'source':source['id'],'role':role})
            component={'id':cid,'role':role,'source_equipment':label,'evidence_ids':[option_ev[key]],'ratings':[],
                       'parameters':{'capacity':parameter(None,'W',option_ev[key],required_inputs=['consumer_sizing']),
                                     'cop':parameter(None,'W/W',option_ev[key])},'required_inputs':['curves','controls','fan_performance']}
            for metric in ('AFUE','SEER2','SEER','HSPF2','HSPF'):
                pattern=r'([0-9.]+)% AFUE' if metric=='AFUE' else r'\b'+metric+r' ([0-9.]+)'
                rating=re.search(pattern,label)
                if rating:
                    original=float(rating[1]);factor=.01 if metric=='AFUE' else .2930710701722222
                    rating_ev=proof(key+'/'+metric,label,'percent' if metric=='AFUE' else 'Btu/(W*h)',
                        'percent / 100' if metric=='AFUE' else 'rating x 0.2930710701722222; seasonal metric preserved',
                        'Exact matched option argument rating; seasonal efficiency is not operating COP.')
                    component['ratings'].append({'metric':metric,'value':parameter(original*factor,'1' if metric=='AFUE' else 'W/W',rating_ev)})
            bundle['components'].append(component);system['component_ids'].append(cid)
        system['parameters']['heating_fuel']=parameter(source['selected_options'].get('Heating Fuel'),'fuel',
            proof('Heating Fuel',source['selected_options'].get('Heating Fuel')))
        bundle['hvac_systems'].append(system)
    return DefinitionBundle().merge(bundle)
