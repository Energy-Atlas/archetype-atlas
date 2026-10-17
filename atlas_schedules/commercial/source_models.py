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


# Stripmall: only the template/view proved by the original native pilot is
# qualified; the other nine await their own native People evidence (S3).
STRIPMALL_CONFIGURATIONS={'strip_mall__90_1_2013__source'}
STRIPMALL_PENDING={'strip_mall__'+template+'__'+view
    for template in ('90_1_2007','90_1_2013','90_1_2019','doe_ref_1980_2004','doe_ref_pre_1980')
    for view in ('source','reviewed')}-STRIPMALL_CONFIGURATIONS
# Native sorted space order and People Ruleset per space in the 2013 SOURCE model.
_STRIP_SPACES={'strip_mall__90_1_2013__source':(('LGstore1','Type1'),('LGstore2','Type3'),('SMstore1','Type1'),
    ('SMstore2','Type2'),('SMstore3','Type2'),('SMstore4','Type2'),('SMstore5','Type3'),('SMstore6','Type3'),
    ('SMstore7','Type3'),('SMstore8','Type3'))}
# Frozen v0.1.1 programme per source People type in that model.
_STRIP_PROGRAMMES={'strip_mall__90_1_2013__source':{'Type1':'program-f9034faffb02f5e77056c6cf',
    'Type2':'program-75cf4ec07b0c6053a2e1ba6d','Type3':'program-e44fc2ec3f865c660176b600'}}


def _fail(field,message):
    raise GeneratorError('invalid_commercial_context','/commercial/retail/'+field,message)


def ruby_float_sum(values):
    """Ruby Array#sum over Floats: Kahan-Babuska compensated summation (array.c ary_sum)."""
    f=0.0;c=0.0
    for x in values:
        if type(x) not in (int,float):raise TypeError('Float operands required')
        x=float(x)
        if math.isnan(f):continue
        if math.isnan(x):f=x;continue
        if math.isinf(x):
            f=math.nan if math.isinf(f) and math.copysign(1,x)!=math.copysign(1,f) else x;continue
        if math.isinf(f):continue
        t=f+x
        if abs(f)>=abs(x):c+=(f-t)+x
        else:c+=(x-t)+f
        f=t
    return f+c


def validate_stripmall_people(context):
    """Exact native space order and ordered People Ruleset groups for a proved Stripmall context.

    Returns (scope, groups, total). Each group keeps the source Ruby Hash
    first-encounter order and accumulates per-space nominal People with plain
    += ; the total is Ruby Array#sum over group weights.
    """
    def fail(field,message):
        raise GeneratorError('invalid_commercial_context','/commercial/stripmall/'+field,message)
    config=context.get('source_hoo_configuration_id')
    if config in STRIPMALL_PENDING:
        raise GeneratorError('requires_binding','/commercial/stripmall/configuration',
            'This Stripmall template/view awaits its own native People evidence')
    if (config not in STRIPMALL_CONFIGURATIONS or context.get('configuration_id')!=config or
            context.get('year')!=2007 or context.get('holidays')!=[] or
            context.get('standards_version')!='0.8.6' or context.get('steps_per_hour')!=6 or
            context.get('source_clock')!={'TZ':'UTC','variant':'controlled_no_DST_local_standard_calendar'}):
        fail('configuration','Exact source/view/calendar/clock/version configuration required')
    policy=context.get('parametric_apply')
    if (not isinstance(policy,dict) or policy.get('error_on_out_of_order') is not False or
            policy.get('source_method')!='create_typical.rb:766'):
        fail('parametric_apply','Explicit pinned selected caller false required')
    view=config.rsplit('__',1)[1];aggregation=context.get('occupancy_aggregation')
    if (not isinstance(aggregation,dict) or aggregation.get('policy')!='explicit_source_model_nonresidential_people' or
            aggregation.get('source_hoo_configuration_id')!=config or aggregation.get('evidence_view')!=view):
        fail('occupancy_aggregation','Exact selected-view source People model required')
    scope=aggregation.get('source_model_scope');parts=aggregation.get('constituents');expected=_STRIP_SPACES[config]
    if (not isinstance(scope,dict) or scope.get('model_family')!='RetailStripmall' or
            scope.get('method')!='explicit_view_specific_model_hoo_reference' or
            scope.get('population_or_whole_prototype_equivalent') is not False or
            scope.get('native_sorted_space_order')!=[name for name,_ in expected] or
            not isinstance(parts,list) or [p.get('source_space_name') if isinstance(p,dict) else None for p in parts]!=[name for name,_ in expected]):
        fail('source_model_scope','Exact native sorted space order and labelled view adaptation required')
    groups=[];by_identity={};by_type={};programmes=_STRIP_PROGRAMMES[config]
    for part,(name,kind) in zip(parts,expected):
        identity=part.get('schedule_identity');schedule=part.get('schedule');nominal=part.get('nominal_people')
        if (part.get('residential') is not False or not isinstance(identity,str) or not identity or not isinstance(schedule,dict) or
                type(nominal) not in (int,float) or not math.isfinite(nominal) or nominal<=0 or
                not isinstance(part.get('program_id'),str) or not isinstance(part.get('source_program_id'),str) or
                not isinstance(part.get('evidence'),dict)):
            fail('constituents','Positive nonresidential native People occurrence with its Ruleset identity required')
        # Bind every operand to its receipts: the frozen programme for this source
        # type, its occupancy definition and schedule, and the native People object
        # whose getNumberOfPeople(floorArea) is exactly area * native density.
        definition=part['evidence'].get('source_people_definition');native=part['evidence'].get('native_people_object')
        area=part.get('source_floor_area_m2')
        if (part['program_id']!=programmes[kind] or type(area) not in (int,float) or not math.isfinite(area) or area<=0 or
                not isinstance(definition,dict) or definition.get('quantity')!='occupancy' or
                definition.get('value')!=part.get('source_density_person_m2') or definition.get('unit')!='person/m2' or
                definition.get('basis')!='floor_area' or definition.get('schedule_id')!=schedule.get('id') or
                not isinstance(native,dict) or native.get('handle')!=part.get('native_people_object_handle') or
                native.get('schedule_handle')!=identity or native.get('program_id')!=part['program_id'] or
                native.get('source_program_id')!=part['source_program_id'] or
                type(native.get('density_person_m2')) is not float or nominal!=area*native['density_person_m2']):
            fail('constituents','Actual nominal/density/programme/schedule operands differ from their source/native receipts')
        # OpenStudio and the frozen definition convert the same people/1000 ft2
        # source value separately; the observed native gap is exactly 2 ulp.
        if abs(native['density_person_m2']-definition['value'])>2*math.ulp(definition['value']):
            fail('constituents','Native People density differs from the frozen definition density')
        if by_type.setdefault(kind,identity)!=identity:
            fail('constituents','Spaces of one source type must share one actual People Ruleset')
        if identity not in by_identity:
            by_identity[identity]={'schedule_identity':identity,'schedule':schedule,'weight':0.0,'spaces':[]};groups.append(by_identity[identity])
        group=by_identity[identity]
        if group['schedule']!=schedule:fail('constituents','One Ruleset identity cannot carry two schedule bodies')
        group['weight']+=nominal;group['spaces'].append(name)
    if len(groups)!=len(set(kind for _,kind in expected)):fail('constituents','Exact source People Ruleset group count required')
    return scope,groups,ruby_float_sum([g['weight'] for g in groups])


LOCAL_HOO_RESOLUTION={'route':'attached_local','resolved_schedule':'building_default_schedule_set_hours_of_operation',
    'source_locator':'Standards0.8.6 parametric.rb:157-165 resets HoursofOperation on every DefaultScheduleSet and sets it only on '
                     'the building set; space.rb:213-215 space_hours_of_operation reads getDefaultSchedule(HoursofOperationSchedule)',
    'interpretation':'The first-registered fixture space resolves the building schedule through the default-schedule-set '
                     'hierarchy; this is a source-code route, not an equality assumption between model and local carriers.'}


def validate_stripmall_local_people(context):
    """Local water carrier: the first-registered fixture's space and its resolved hours of operation.

    A shared water Ruleset takes the hours of operation registered by its first
    fixture in native sort order. That fixture's space resolves its
    HoursofOperation default schedule, which the source sets only on the
    building default schedule set (LOCAL_HOO_RESOLUTION). The carrier therefore
    carries the registration binding, the space and the full model People
    aggregation that produces the building schedule. Returns (registration, model groups, total).
    """
    def fail(field,message):
        raise GeneratorError('invalid_commercial_context','/commercial/stripmall/local/'+field,message)
    config=context.get('source_hoo_configuration_id')
    if config in STRIPMALL_PENDING:
        raise GeneratorError('requires_binding','/commercial/stripmall/configuration',
            'This Stripmall template/view awaits its own native People evidence')
    if (config not in STRIPMALL_CONFIGURATIONS or context.get('configuration_id')!=config or
            context.get('year')!=2007 or context.get('holidays')!=[] or context.get('standards_version')!='0.8.6' or
            context.get('steps_per_hour')!=6 or
            context.get('source_clock')!={'TZ':'UTC','variant':'controlled_no_DST_local_standard_calendar'}):
        fail('configuration','Exact source/view/calendar/clock/version configuration required')
    aggregation=context.get('occupancy_aggregation');view=config.rsplit('__',1)[1]
    if (not isinstance(aggregation,dict) or aggregation.get('policy')!='explicit_source_local_space_people' or
            aggregation.get('source_hoo_configuration_id')!=config or aggregation.get('evidence_view')!=view):
        fail('occupancy_aggregation','Exact selected-view local space People carrier required')
    space=aggregation.get('space');registration=aggregation.get('registration')
    if set(aggregation)!={'policy','source_hoo_configuration_id','evidence_view','space','registration','resolution','model_aggregation'}:
        fail('occupancy_aggregation','Exact local carrier fields required')
    if space not in dict(_STRIP_SPACES[config]):fail('space','Exact native source space required')
    if aggregation.get('resolution')!=LOCAL_HOO_RESOLUTION:fail('resolution','Exact source hours-of-operation resolution route required')
    keys={'schedule_identity','source_schedule_id','fixtures','first_registered_fixture','first_registered_space',
          'native_fixture_order','fixture_spaces'}
    if not isinstance(registration,dict) or set(registration)!=keys:fail('registration','Explicit shared first-registration binding required')
    slots=context.get('slot_sources');water=slots.get('hot_water_volume') if isinstance(slots,dict) else None
    if not isinstance(water,dict) or registration['source_schedule_id']!=water.get('id'):
        fail('registration','The registered Ruleset must be the water slot source schedule')
    order=registration['native_fixture_order'];fixtures=registration['fixtures'];spaces=registration['fixture_spaces']
    if (not isinstance(order,list) or not isinstance(fixtures,list) or not fixtures or not isinstance(spaces,dict) or
            any(not isinstance(f,str) for f in order) or
            len(set(order))!=len(order) or any(f not in order for f in fixtures) or set(spaces)!=set(order) or
            [f for f in order if f in fixtures]!=fixtures or registration['first_registered_fixture']!=fixtures[0] or
            spaces[fixtures[0]]!=registration['first_registered_space'] or registration['first_registered_space']!=space or
            not isinstance(registration['schedule_identity'],str) or not registration['schedule_identity']):
        fail('registration','The first fixture in native sort order registers the shared Ruleset from its own space')
    if any(name not in dict(_STRIP_SPACES[config]) for name in spaces.values()):
        fail('registration','Fixture spaces must be exact native source spaces')
    model=dict(context,occupancy_aggregation=aggregation['model_aggregation'])
    _,groups,total=validate_stripmall_people(model)
    return registration,groups,total


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
