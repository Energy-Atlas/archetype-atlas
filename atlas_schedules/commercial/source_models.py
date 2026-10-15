"""Exactly qualified Retail source/view People context; no arbitrary carrier."""
import math

from ..errors import GeneratorError

RETAIL_CONFIGURATIONS={'retail__'+template+'__'+view
    for template in ('90_1_2007','90_1_2013','90_1_2019','doe_ref_1980_2004','doe_ref_pre_1980')
    for view in ('source','reviewed')}
_SPACES=('Back_Space','Core_Retail','Front_Entry','Front_Retail','Point_Of_Sale')
_GEOMETRY={'90_1_2007':'0522ce179e88b70a0e39ac17b9d29f4f12a6b04fa7b8496ea9a1f3ad0d1212af',
    '90_1_2013':'a08a6503588b40d9c19f169cad7599468298eddf67cfdb613a8983b8431b8b04',
    '90_1_2019':'a08a6503588b40d9c19f169cad7599468298eddf67cfdb613a8983b8431b8b04',
    'doe_ref_1980_2004':'6406ace5785fbee762153b1e22facdd67d01638a90bcdd49965f5db7d52686b5',
    'doe_ref_pre_1980':'6406ace5785fbee762153b1e22facdd67d01638a90bcdd49965f5db7d52686b5'}


def _fail(field,message):
    raise GeneratorError('invalid_commercial_context','/commercial/retail/'+field,message)


def _positive(value,field):
    if type(value) not in (int,float) or not math.isfinite(value) or value<=0:
        _fail(field,'Positive finite original native People operand required')


def validate_retail_people(context):
    """Validate the ten captured c8 SpaceType/inherited-schedule configurations."""
    config=context.get('source_hoo_configuration_id')
    if (config not in RETAIL_CONFIGURATIONS or context.get('configuration_id')!=config or
            context.get('year')!=2007 or context.get('holidays')!=[] or
            context.get('standards_version')!='0.8.6' or context.get('steps_per_hour')!=6 or
            context.get('source_clock')!={'TZ':'UTC','variant':'controlled_no_DST_local_standard_calendar'}):
        _fail('configuration','Exact source/view/calendar/clock/version configuration required')
    policy=context.get('parametric_apply')
    if (not isinstance(policy,dict) or policy.get('error_on_out_of_order') is not False or
            policy.get('source_method')!='create_typical.rb:766'):
        _fail('parametric_apply','Explicit pinned selected caller false required')
    template=config.split('__')[1];view=config.rsplit('__',1)[1]
    aggregation=context.get('occupancy_aggregation')
    if (not isinstance(aggregation,dict) or aggregation.get('policy')!='explicit_source_model_nonresidential_people' or
            aggregation.get('source_hoo_configuration_id')!=config or aggregation.get('evidence_view')!=view):
        _fail('occupancy_aggregation','Exact selected-view source People model required')
    scope=aggregation.get('source_model_scope');parts=aggregation.get('constituents')
    if (not isinstance(scope,dict) or scope.get('model_family')!='RetailStandalone' or
            scope.get('method')!='explicit_view_specific_model_hoo_reference' or
            scope.get('population_or_whole_prototype_equivalent') is not False or
            scope.get('native_sorted_space_order')!=list(_SPACES)):
        _fail('source_model_scope','Exact original source-space order and labelled view adaptation required')
    inventory=scope.get('original_people_inventory')
    if (not isinstance(inventory,list) or len(inventory)!=5 or
            any(not isinstance(p,dict) for p in inventory) or
            [p.get('space_name') for p in inventory]!=list(_SPACES)):
        _fail('original_people_inventory','All five exact original spaces, including source zero, required')
    doe=template.startswith('doe_');split=template in {'90_1_2013','90_1_2019'}
    types={'Back_Space':'Back_Space','Core_Retail':'Core_Retail' if split else 'Retail',
        'Front_Entry':'Entry','Front_Retail':'Front_Retail' if split else 'Retail','Point_Of_Sale':'Point_of_Sale'}
    positive=[];type_handles={};ids=[]
    for original in inventory:
        name=original['space_name'];density=original.get('source_density_person_m2');nominal=original.get('nominal_people')
        definition=original.get('source_definition');field=original.get('source_field_evidence')
        if (original.get('residential') is not False or original.get('source_space_type')!=types[name] or
                not isinstance(definition,dict) or definition.get('quantity')!='occupancy' or
                definition.get('status')!='known' or definition.get('value')!=density or
                definition.get('unit')!='person/m2' or definition.get('basis')!='floor_area' or
                not isinstance(field,dict) or field.get('id')!=definition.get('evidence_id') or
                not isinstance(original.get('program_id'),str) or not isinstance(original.get('source_program_id'),str)):
            _fail('original_people_inventory','Original selected-view type/density/provenance differs')
        ids.append(original['program_id'])
        _positive(original.get('floor_area_m2'),'source_area');_positive(original.get('multiplier'),'source_multiplier')
        if name=='Front_Entry' and not doe:
            if (type(density) not in (int,float) or density!=0 or type(nominal) not in (int,float) or nominal!=0 or
                    original.get('native_people_object_handle') is not None):
                _fail('source_zero','Exact code Entry zero/no original People object required')
            continue
        _positive(density,'source_density');_positive(nominal,'native_nominal_people')
        handle=original.get('native_people_object_handle')
        if not isinstance(handle,str) or not handle:_fail('source_people_object','Actual source SpaceType People identity required')
        prior=type_handles.setdefault(types[name],handle)
        if prior!=handle:_fail('source_people_object','Repeated source spaces must inherit one actual SpaceType People object')
        positive.append(original)
    selected=scope.get('selected_program_ids')
    if (not isinstance(selected,list) or any(not isinstance(value,str) for value in selected) or len(selected)!=len(set(selected)) or set(selected)!=set(ids) or
            scope.get('native_people_object_count')!=len(set(type_handles.values())) or
            len(set(type_handles.values()))!=(4 if doe or split else 3) or
            not isinstance(parts,list) or len(parts)!=len(positive)):
        _fail('source_people_object','Exact selected programmes and shared source object cardinality required')
    total=0.0
    for part,original in zip(parts,positive):
        if not isinstance(part,dict):_fail('constituents','Original native per-space People occurrence required')
        evidence=part.get('evidence')
        if (part.get('source_space_name')!=original['space_name'] or part.get('residential') is not False or
                any(part.get(k)!=original[k] for k in ('program_id','source_program_id','nominal_people')) or
                any(part.get(k)!=original[v] for k,v in (('source_floor_area_m2','floor_area_m2'),('source_multiplier','multiplier'),('source_density_person_m2','source_density_person_m2'))) or
                not isinstance(evidence,dict) or evidence.get('source_people_definition')!=original['source_definition'] or
                evidence.get('source_people_field')!=original['source_field_evidence'] or
                evidence.get('native_nominal_people')!=original['nominal_people'] or
                evidence.get('native_people_object_handle')!=original['native_people_object_handle'] or
                not isinstance(evidence.get('source_geometry'),dict) or evidence['source_geometry'].get('sha256')!=_GEOMETRY[template] or
                not isinstance(part.get('schedule'),dict) or part['schedule'].get('id')!=original['source_definition'].get('schedule_id') or
                part['schedule']!=parts[0].get('schedule')):
            _fail('constituents','Exact ordered source/view People/schedule/geometry/native operands required')
        # Source space.rb accumulates per-space occurrences into the shared
        # Ruleset group with +=. A compensated sum changes a captured boundary.
        total+=part['nominal_people']
    return scope,total
