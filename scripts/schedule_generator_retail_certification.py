"""Exact C6 Retail programme/member and physical native source associations."""
import copy
import hashlib

from atlas_schedules.canonical import canonical
from atlas_schedules.commercial.sampling import sample_operating_parameters
from atlas_schedules.errors import GeneratorError
from atlas_schedules.resources import strict_json
from scripts.common import ROOT
from scripts.schedule_generator_retail import (load_context_reference,load_programme_reference,
    compile_service_records,validate_fixed_native_operands)


def _sha(value):return hashlib.sha256(canonical(value)).hexdigest()


def _join(get,scope,context):
    prior=get('reference','c5-family-native-join')
    components=copy.deepcopy(prior['components'])
    for key in ('retail-context-native-lock','retail-programme-native-lock'):
        lock=get('reference',key)
        components.append({'reference_resource_key':key,'reference_resource_sha256':_sha(lock),'lock':lock})
    indexed={c['reference_resource_key']:c for c in components}
    component=indexed['retail-programme-native-lock'];bindings=copy.deepcopy(prior['fixture_bindings'])
    def reference(case_id,pid,member=None):
        item={'program_id':pid,'native_case_id':case_id+'@'+('parent-42' if member is not None else 'native'),
            'public_native_case_ids':([case_id+'@parent-51'] if member is not None else
                [case_id+'@'+kind+'-'+str(seed) for kind in ('instance','full_request') for seed in (42,51)]),
            'reference_resource_key':component['reference_resource_key'],
            'reference_resource_sha256':component['reference_resource_sha256'],
            'native_vectors_sha256':component['lock']['vectors']['sha256']}
        if member is not None:item.update(member_index=member[0],original_member=copy.deepcopy(member[1]))
        return item
    for case in scope['cases'][165:]:
        pid=case['program_id'];allocation=get('program',pid)['recipe'].get('source_composition')
        if allocation:
            binding={'program_id':pid,'configuration_id':case['configuration_id'],
                'composition_id':allocation['composition_id'],'native_members':[
                    reference(case['case_id']+'/member-'+str(i),m['program_id'],(i,m))
                    for i,m in enumerate(allocation['definition']['members'])]}
        else:
            binding=reference(case['case_id'],pid);binding['configuration_id']=case['configuration_id']
        bindings.append(binding)
    services=copy.deepcopy(prior['service_bindings'])
    component=indexed['retail-context-native-lock']
    for case in scope['service_cases'][26:]:
        sid=case['source_service_id'];config=case['source_hoo_configuration_id'];found=[]
        for i,native in enumerate(context['vectors']['cases']):
            if native['source_service_id']==sid and native['configuration_id']==config:
                found.append({'native_case_id':native['case_id'],'pointer':'/cases/'+str(i),
                    'reference_resource_key':component['reference_resource_key'],
                    'reference_resource_sha256':component['reference_resource_sha256'],
                    'native_vectors_sha256':component['lock']['vectors']['sha256']})
        if len(found)!=2:raise ValueError('Exact two-seed Retail native fixture association missing')
        services.append({'case_id':case['case_id'],'owner_kind':'physical_service','source_service_id':sid,
            'source_hoo_configuration_id':config,'resource_key':case['resource_key'],
            'resource_sha256':_sha(get('reference',case['resource_key'])),'public_native_contexts':found})
    return {'schema_version':'1.0.0','components':components,'fixture_bindings':bindings,'service_bindings':services,
        'interpretation':'Inherited actual captures retained once; exact Retail local/member and whole unallocated physical cases close separately to actual native arrays'}


def build_native_join(records):
    context=load_context_reference()
    records['reference','retail-context-native-lock']=context['lock']
    records['reference','retail-programme-native-lock']=strict_json(
        (ROOT/'sources/schedule-generator-retail-programme-reference-lock.json').read_bytes(),'retail-programme-lock')
    join=_join(lambda kind,key:records[kind,key],records['reference','m1-scope'],context)
    records['reference','family-native-join']=join
    return join


def _operating_equal(actual,expected):
    actual=copy.deepcopy(actual);expected=copy.deepcopy(expected)
    for value in (actual,expected):value.get('rng',{}).pop('python_version',None)
    return actual==expected


def validate_native_associations(resources,join):
    """Close actual consumed operands/draws; numerical/certificate gates are separate."""
    try:
        scope=resources.get('reference','m1-scope');context=load_context_reference()
        if len(scope['cases'])!=229 or len(scope.get('service_cases',[]))!=32:
            raise ValueError('Exact C6 programme/physical source scope differs')
        inherited=resources.get('reference','c5-family-native-join')
        original=strict_json((ROOT/'data/schedule-generator/restaurant-cumulative-native.json').read_bytes(),'immutable C5 native join')
        if inherited!=original:
            raise ValueError('Inherited actual C5 native source associations differ from the immutable shipment')
        keys=[c['reference_resource_key'] for c in join['components']]
        expected=[c['reference_resource_key'] for c in inherited['components']]
        if keys!=expected+['retail-context-native-lock','retail-programme-native-lock']:
            raise ValueError('Native component order/identity differs or repeats')
        for component in join['components']:
            actual=resources.get('reference',component['reference_resource_key'])
            if actual!=component['lock'] or _sha(actual)!=component['reference_resource_sha256']:
                raise ValueError('Native component resource identity differs')
        if join!=_join(resources.get,scope,context):
            raise ValueError('Missing/mispointed/duplicate Retail native source association')
        programmes=load_programme_reference()
        if resources.get('reference','retail-programme-native-lock')!=programmes['lock'] or resources.get('reference','retail-context-native-lock')!=context['lock']:
            raise ValueError('Actual native source component differs')
        declarations={c['program_id']:c for c in scope['cases'][165:]};cache={};members=0
        for given in programmes['inputs']:
            parent=given['source_case']['program_id'];declaration=declarations[parent]
            for field in ('program_id','name','building_type','template','evidence_view','configuration_id',
                          'program_definition','configuration','weather'):
                if given['source_case'][field]!=declaration[field]:
                    raise ValueError('Native programme source identity differs: '+parent+'/'+field)
            member=given['source_member_receipt'];pid=member['program_id'] if member else parent
            if member:
                allocation=resources.get('program',parent)['recipe']['source_composition'];index=member['member_index']
                if (member['parent_program_id']!=parent or member['composition_id']!=allocation['composition_id'] or
                        member['original_member']!=allocation['definition']['members'][index] or
                        member['original_member']['program_id']!=pid):
                    raise ValueError('Native ordered parent-member source association differs')
                members+=1
            if pid not in cache:cache[pid]=resources.get('program',pid)
            record=cache[pid]
            if record['recipe']['source_context']!=given['source_context'] or given['schedules']!=record['recipe']['source_context']['slot_sources']:
                raise ValueError('Native programme consumed source/profile association differs: '+pid)
            operating=sample_operating_parameters(declaration['configuration']['conditioning_inputs'],given['source_seed_receipt']['group_seed'],resources)
            if not _operating_equal(operating,given['operating']):
                raise ValueError('Native programme actual source/discrete draws differ: '+given['case_id'])
        if members!=116:raise ValueError('Native parent member scope differs')
        validate_fixed_native_operands(resources.get('reference','retail-fixed-native-operands'),context)
        physical=compile_service_records();observations=0
        for declaration in scope['service_cases'][26:]:
            key=declaration['resource_key']
            if resources.get('reference',key)!=physical['reference',key]:
                raise ValueError('Native physical definition/context/original budget association differs')
        for given in context['inputs']['cases']:
            operating=sample_operating_parameters({'building_type':'retail'},given['group_seed'],resources)
            if (operating['effective_values']!=given['operating']['effective_values'] or
                    operating['draw_receipts']!=given['operating']['draw_receipts']):
                raise ValueError('Native physical source/discrete association differs')
            observations+=given['physical_service'] is not None
        if observations!=12:raise ValueError('Native physical fixture scope differs')
        return {'status':'source_discrete_association_passed','programme_native_cases':336,
            'physical_fixture_observations':12,'parent_member_observations':116,
            'programme_cases':64,'local_programme_cases':44,'source_compositions':20,
            'service_configuration_cases':6,'source_service_definitions':3,'source_hoo_configurations':10,
            'numerical_parity_and_family_certification':'separately_required'}
    except (KeyError,IndexError,TypeError,GeneratorError) as error:
        raise ValueError('Native Retail source association is missing or invalid: '+str(error)) from error


def compare_native_programmes(resources):
    """Compare current packaged operands/methods to all336 actual native local/member cases."""
    import math
    from atlas_schedules.calendar import evaluate_rules
    from atlas_schedules.commercial.parametric import transform_commercial
    captured=load_programme_reference()
    native={c['case_id']:c for c in captured['vectors']['cases']}
    records={};differences=[];hourly=0;profiles=0;tested=0
    def points_equal(actual,expected):
        return (len(actual)==len(expected) and all(len(p)==len(q)==2 and
            all(math.isfinite(a) and abs(a-b)<=1e-8 for a,b in zip(p,q)) for p,q in zip(actual,expected)))
    for given in captured['inputs']:
        member=given['source_member_receipt']
        pid=member['program_id'] if member else given['source_case']['program_id'];key=given['case_id'];expected=native[key]
        if pid not in records:records[pid]=resources.get('program',pid)
        context=copy.deepcopy(records[pid]['recipe']['source_context'])
        original={slot:evaluate_rules(source,2007,[])['values'] for slot,source in context['slot_sources'].items()}
        actual=transform_commercial(original,given['operating'],context);tested+=1
        if set(actual['channels'])!=set(expected['channels']):
            differences.append({'case_id':key,'difference':'channel inventory'});continue
        for slot,values in actual['channels'].items():
            wanted=expected['channels'][slot];hourly+=len(values)
            if len(values)!=len(wanted) or any(not math.isfinite(a) or abs(a-b)>1e-8 for a,b in zip(values,wanted)):
                differences.append({'case_id':key,'slot':slot,'difference':'actual native hourly values'})
            final=expected['final'][slot]
            by_day={day:final['profiles']['default' if rule=='-1' else rule]
                    for rule,days in final['days_used'].items() for day in days}
            daily=actual['source_context']['transforms'][slot]['daily_profiles']
            if len(daily)!=365 or set(by_day)!=set(range(1,366)):
                differences.append({'case_id':key,'slot':slot,'difference':'actual native day/rule selection'})
            for day,points in enumerate(daily,1):
                profiles+=1
                if day not in by_day or not points_equal(points,by_day[day]):
                    differences.append({'case_id':key,'slot':slot,'day':day,'difference':'actual native daily profile'})
            specials=actual['source_context']['special_profiles'][slot]
            if set(specials)!=set(expected['special_profiles'][slot]):
                differences.append({'case_id':key,'slot':slot,'difference':'actual native special selectors'})
            for kind,points in specials.items():
                profiles+=1
                if kind not in expected['special_profiles'][slot] or not points_equal(points,expected['special_profiles'][slot][kind]):
                    differences.append({'case_id':key,'slot':slot,'special':kind,'difference':'actual native special profile'})
    return {'status':'passed' if not differences else 'failed','tested_cases':tested,
        'hourly_values_compared':hourly,'daily_special_profiles_compared':profiles,
        'absolute_tolerance':1e-8,'native_payload_sha256':captured['lock']['vectors']['payload_sha256'],
        'current_program_resource_sha256':{pid:_sha(record) for pid,record in sorted(records.items())},
        'differences':differences}
