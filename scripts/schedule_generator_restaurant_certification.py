"""Development source/native association closure for the exact C5 milestone."""
import copy
import hashlib
import math

from atlas_schedules.canonical import canonical
from atlas_schedules.commercial.sampling import sample_operating_parameters
from atlas_schedules.errors import GeneratorError
from scripts.schedule_generator_reference import (load_restaurant_water_reference,
    load_restaurant_programme_reference,load_restaurant_public_water_reference)
from scripts.schedule_generator_restaurants import (source_model_context,
    validate_fixed_native_operands)

COMPONENTS=(('restaurant-programme-native-lock',load_restaurant_programme_reference),
    ('restaurant-water-native-lock',load_restaurant_water_reference),
    ('restaurant-water-public-native-lock',load_restaurant_public_water_reference))


def _sha(value):return hashlib.sha256(canonical(value)).hexdigest()


def _join(get,scope,prior,captures):
    components=copy.deepcopy(prior['components'])
    for key,_ in COMPONENTS:
        lock=get('reference',key)
        components.append({'reference_resource_key':key,'reference_resource_sha256':_sha(lock),'lock':lock})
    indexed={c['reference_resource_key']:c for c in components}
    bindings=copy.deepcopy(prior['fixture_bindings'])
    for case in scope['cases'][119:]:
        component=indexed['restaurant-programme-native-lock']
        bindings.append({'owner_kind':'program','configuration_id':case['configuration_id'],
            'program_id':case['program_id'],'native_case_id':case['case_id']+'@native',
            'public_native_case_ids':[case['case_id']+'@'+kind+'-'+str(seed)
                for kind in ('instance','full_request') for seed in (42,51)],
            'reference_resource_key':component['reference_resource_key'],
            'reference_resource_sha256':component['reference_resource_sha256'],
            'native_vectors_sha256':component['lock']['vectors']['sha256']})
    services=[]
    for case in scope.get('service_cases',[]):
        sid=case['source_service_id'];config=case['source_hoo_configuration_id']
        item={'case_id':case['case_id'],'owner_kind':'physical_service','source_service_id':sid,
            'source_hoo_configuration_id':config,'resource_key':case['resource_key'],
            'resource_sha256':_sha(get('reference',case['resource_key']))}
        for prefix,key in (('private','restaurant-water-native-lock'),('public','restaurant-water-public-native-lock')):
            found=[];component=indexed[key]
            for i,native in enumerate(captures[key]['native']['cases']):
                if native['source_hoo_configuration_id']!=config:continue
                for j,fixture in enumerate(native['fixtures']):
                    if fixture['source_service_id']==sid:
                        found.append({'native_case_id':native['case_id'],'pointer':'/cases/'+str(i)+'/fixtures/'+str(j),
                            'reference_resource_key':key,'reference_resource_sha256':component['reference_resource_sha256'],
                            'native_vectors_sha256':component['lock']['vectors']['sha256']})
            if len(found)!=2:raise ValueError('Exact two-seed native fixture association missing: '+sid+'/'+config)
            item[prefix+'_native_fixtures']=found
        services.append(item)
    return {'schema_version':'1.0.0','components':components,'fixture_bindings':bindings,
        'service_bindings':services,
        'interpretation':'Actual immutable captures stored once; exact original programme members and typed physical service/configuration cases retain separate native associations'}


def build_native_join(records):
    captures={key:loader() for key,loader in COMPONENTS}
    for key,capture in captures.items():records['reference',key]=capture['lock']
    join=_join(lambda kind,key:records[kind,key],records['reference','m1-scope'],
        records['reference','prior-family-native-join'],captures)
    records['reference','family-native-join']=join
    return join


def _operating_equal(actual,expected):
    actual=copy.deepcopy(actual);expected=copy.deepcopy(expected)
    for value in (actual,expected):value.get('rng',{}).pop('python_version',None)
    return actual==expected


def validate_native_associations(resources,join):
    """Independently close current operands/draws to actual captured inputs.

    This is source/discrete association, not a replacement for current numerical
    native parity, annual conservation, a certificate or own-artifact execution.
    """
    try:
        captures={key:loader() for key,loader in COMPONENTS}
        scope=resources.get('reference','m1-scope')
        if len(scope['cases'])!=165 or len(scope.get('service_cases',[]))!=26:
            raise ValueError('Exact C5 programme/physical-case denominator differs')
        for key,capture in captures.items():
            if resources.get('reference',key)!=capture['lock']:
                raise ValueError('Actual locked native component differs: '+key)
        prior=resources.get('reference','prior-family-native-join')
        for component in prior['components']:
            lock=resources.get('reference',component['reference_resource_key'])
            if lock!=component['lock'] or _sha(lock)!=component['reference_resource_sha256']:
                raise ValueError('Inherited actual native component differs')
        if join!=_join(resources.get,scope,prior,captures):
            raise ValueError('Missing/mispointed/duplicate scoped native source association')
        private=captures['restaurant-water-native-lock']
        validate_fixed_native_operands(resources.get('reference','restaurant-water-fixed-native-operands'),private)
        programmes=captures['restaurant-programme-native-lock']
        by_id={c['program_id']:c for c in scope['cases'][119:]};cached={};seen=set()
        families={name:{'programme_native_cases':0,'service_cases':0,'private_fixture_observations':0,
                       'public_fixture_observations':0} for name in ('FullServiceRestaurant','QuickServiceRestaurant')}
        for given in programmes['inputs']:
            declaration=by_id[given['source_case']['program_id']];pid=declaration['program_id']
            if pid not in cached:cached[pid]=resources.get('program',pid)
            record=cached[pid];context=record['recipe']['source_context'];native_context=given['source_context']
            if record['case']!=declaration or given['schedules']!=context['slot_sources']:
                raise ValueError('Native programme source/profile/case differs: '+pid)
            for field in ('program_id','name','building_type','template','evidence_view','configuration_id',
                          'program_definition','configuration','weather'):
                if given['source_case'][field]!=declaration[field]:
                    raise ValueError('Native programme identity/dependency differs: '+pid+'/'+field)
            # Only this later explicit method-evidence receipt was added after
            # capture; it does not alter any consumed schedule/People operand.
            clean={k:v for k,v in context.items() if k!='source_default_cleanup_method_evidence'}
            if clean!=native_context:
                raise ValueError('Native programme consumed source context differs: '+pid)
            operating=sample_operating_parameters(declaration['configuration']['conditioning_inputs'],
                given['source_seed_receipt']['group_seed'],resources)
            if not _operating_equal(operating,given['operating']):
                raise ValueError('Native programme actual source/discrete draws differ: '+given['case_id'])
            seen.add(given['case_id']);families[declaration['building_type']]['programme_native_cases']+=1
        if len(seen)!=230:raise ValueError('Native programme case denominator differs')
        private_inputs={c['case_id']:c for c in private['inputs']['cases']}
        for declaration in scope['service_cases']:
            record=resources.get('reference',declaration['resource_key']);sid=declaration['source_service_id']
            config=declaration['source_hoo_configuration_id'];variant=record['recipe']['configurations'][config]
            original=next(c for c in private['native']['cases'] if c['source_hoo_configuration_id']==config)
            given=private_inputs[original['case_id']]
            expected=source_model_context(given,original,private['lock']['vectors']['payload_sha256'])
            if (record['definition']['id']!=sid or variant['source_context']!=expected or
                    variant['reference_source']!=given['water_schedule'] or
                    variant['adaptation']['original_source_service_id']!=sid):
                raise ValueError('Native physical source/configuration/profile association differs: '+sid+'/'+config)
            families[declaration['building_type']]['service_cases']+=1
        for key,prefix in (('restaurant-water-native-lock','private'),('restaurant-water-public-native-lock','public')):
            capture=captures[key];inputs={c['case_id']:c for c in capture['inputs']['cases']}
            for native in capture['native']['cases']:
                given=inputs[native['case_id']];config=given['source_hoo_configuration_id']
                selector=config.split('__')[0];seed=given['operating']['source_seed_receipt']['group_seed']
                operating=sample_operating_parameters({'building_type':selector},seed,resources)
                draws=[{k:r[k] for k in ('parameter','uniform','selection')} for r in operating['draw_receipts']]
                if operating['effective_values']!=given['operating']['effective_values'] or draws!=given['operating']['draw_receipts']:
                    raise ValueError('Native physical source/discrete draws differ: '+native['case_id'])
                families[given['family']][prefix+'_fixture_observations']+=len(native['fixtures'])
        return {'status':'source_discrete_association_passed','programme_native_cases':230,
            'public_water_native_cases':40,'private_water_fixture_observations':52,'families':families,
            'numerical_parity_and_family_certification':'separately_required'}
    except (KeyError,TypeError,GeneratorError) as error:
        raise ValueError('Native source association is missing or invalid: '+str(error)) from error


def compare_native_programmes(resources):
    """Compare current packaged operands/methods to all230 actual native cases."""
    from atlas_schedules.calendar import evaluate_rules
    from atlas_schedules.commercial.parametric import transform_commercial
    captured=load_restaurant_programme_reference()
    native={c['case_id']:c for c in captured['native']['cases']}
    records={};differences=[];hourly=0;profiles=0;tested=0
    def points_equal(actual,expected):
        return (len(actual)==len(expected) and all(len(p)==len(q)==2 and
            all(math.isfinite(a) and abs(a-b)<=1e-8 for a,b in zip(p,q)) for p,q in zip(actual,expected)))
    for given in captured['inputs']:
        pid=given['source_case']['program_id'];key=given['case_id'];expected=native[key]
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
