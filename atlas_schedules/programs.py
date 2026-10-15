"""Resolve source-gated recipes without repository or runtime dependencies."""
import copy
import calendar as gregorian

from .budgets import reference_budget
from .calendar import evaluate_rules
from .errors import GeneratorError


def _same_operand(value, bound):
    if isinstance(bound, dict):
        return isinstance(value, dict) and set(value) == set(bound) and all(
            _same_operand(value[k], v) for k, v in bound.items())
    if isinstance(bound, bool):
        return isinstance(value, bool) and value == bound
    return not isinstance(value, bool) and value == bound


def resolve_program(program_id: str, inputs: dict, resources) -> dict:
    """Bind an exact packaged experiment; unknown catalogue recipes fail closed.

    Kernel operands remain explicit. Source targets and original reference arrays
    are prepared here, before the caller samples any commercial operating group.
    Internal prepared operands are returned in inputs, never accepted from callers.
    """
    index = resources.get('reference', 'catalogue-index')
    status = next((p['status'] for p in index['programs'] if p['id'] == program_id), None)
    if status not in {'compiled', 'accepted_inactive'}:
        raise GeneratorError('unsupported_binding', '/program_id',
                             'No source-backed recipe/decomposition for this catalogue identity')
    record = resources.get('program', program_id)
    return _resolve_program_record(program_id, inputs, record, status, resources=resources)


def _resolve_program_record(program_id, inputs, record, status, *, resources=None):
    """Shared engine for an explicitly verified selected executable record."""
    if not isinstance(inputs, dict):
        raise GeneratorError('invalid_input', '/inputs', 'Explicit recipe operands required')
    from .apartment_authority import candidate,resolve_apartment_authority,reconstruct_apartment_programme
    if candidate(record):
        qualification=resolve_apartment_authority(program_id,record,resources)
        return reconstruct_apartment_programme(inputs,record,qualification)
    recipe = record['recipe']
    allowed = set(recipe['bound_inputs']) | set(recipe.get('variable_inputs',{})) | {'year', 'holidays'}
    unknown = set(inputs) - allowed
    if unknown:
        raise GeneratorError('unknown_input', '/inputs/'+sorted(unknown)[0], 'Unknown recipe operand')
    for key in recipe['required_inputs']:
        if key not in inputs:
            raise GeneratorError('missing_input', '/inputs/'+key, 'Required source operand is missing')
    calendar = {'year': inputs['year'], 'clock': 'local_standard_time', 'holidays': inputs.get('holidays', [])}
    year = inputs['year']
    if isinstance(year, bool) or not isinstance(year, int) or not 1 <= year <= 9999:
        raise GeneratorError('invalid_calendar', '/inputs/year', 'Explicit Gregorian year required')
    if gregorian.isleap(year):
        raise GeneratorError('leap_year', '/inputs/year', 'Non-leap Gregorian year required')
    if not isinstance(calendar['holidays'], list):
        raise GeneratorError('invalid_calendar', '/inputs/holidays', 'Explicit holiday date list required')
    if calendar['holidays']:
        raise GeneratorError('unsupported_binding', '/inputs/holidays', 'Declared source clock has no holiday overrides')
    for key, bound in recipe['bound_inputs'].items():
        # Numeric equality alone must not accept True as one resident/coordinate.
        if not _same_operand(inputs[key], bound):
            raise GeneratorError('unsupported_binding', '/inputs/'+key, 'Operand differs from declared source configuration')
    for key,options in recipe.get('variable_inputs',{}).items():
        if key in inputs and not any(_same_operand(inputs[key],option) for option in options):
            raise GeneratorError('unsupported_binding','/inputs/'+key,'Operand is outside explicitly declared recipe choices')
    if recipe['calendar_year_locked'] and inputs['year'] != recipe['reference_year']:
        raise GeneratorError('unsupported_binding', '/inputs/year', 'Annual source case requires its declared reference year')
    return _prepare_program_record(inputs,record,status)


def _validate_apartment_recipe_inputs(inputs: dict, record: dict) -> None:
    from .apartment_authority import SELECTED,CALENDAR
    from .apartment_authority_pins import LOCATIONS
    from .residential.selected import validate_selected_inputs
    recipe=record['recipe'];method=recipe['source_context']['method']
    allowed={'year','holidays','apartment_method'}
    if method==SELECTED:
        allowed.add('N')
        if 'N' not in inputs:raise GeneratorError('missing_input','/inputs/N','Explicit cohort is required')
        if type(inputs['N']) is not int or inputs['N']<0:
            raise GeneratorError('invalid_input','/inputs/N','Strict nonnegative integer cohort required')
        if inputs['N']>0:allowed.update(('state','latitude','longitude','time_zone_utc_offset'))
    unknown=set(inputs)-allowed
    if unknown:raise GeneratorError('unknown_input','/inputs/'+sorted(unknown)[0],'Unknown apartment operand')
    for key in recipe['required_inputs']:
        if key not in inputs:raise GeneratorError('missing_input','/inputs/'+key,'Required original operand missing')
    for key,bound in recipe['bound_inputs'].items():
        if not _same_operand(inputs.get(key),bound):
            raise GeneratorError('unsupported_binding','/inputs/'+key,'Original bound source operand differs')
    if type(inputs['year']) is not int or inputs['year']!=2007 or type(inputs.get('holidays',[])) is not list or inputs.get('holidays',[])!=[]:
        raise GeneratorError('unsupported_binding','/inputs/year','Exact original 2007 local standard calendar required')
    if method==SELECTED:
        consumed={'year':inputs['year'],'holidays':inputs.get('holidays',[]),'residents':inputs['N']}
        if inputs['N']>0:
            for key in ('state','latitude','longitude','time_zone_utc_offset'):
                if key not in inputs:raise GeneratorError('missing_input','/inputs/'+key,'Full original location tuple required')
                consumed[key]=inputs[key]
        validate_selected_inputs(consumed,LOCATIONS)


def _prepare_program_record(inputs,record,status):
    """Pure preparation, after the caller's independent source/input gate."""
    recipe=record['recipe']
    calendar={'year':inputs['year'],'clock':'local_standard_time','holidays':inputs.get('holidays',[])}
    resolved = copy.deepcopy(recipe['resolved'])
    if 'required_service_links' in recipe:
        resolved['required_service_links']=copy.deepcopy(recipe['required_service_links'])
        resolved['required_contract_version']=recipe['required_contract_version']
    # Internal exact-source preparation remains separate from the public 1.2
    # generation gate. Retain original source requirements/methods, never aliases.
    for field in ('required_service_sets', 'exact_source_authority', 'permitted_child_variants', 'original_method_reference'):
        if field in recipe:
            resolved[field] = copy.deepcopy(recipe[field])
    if not resolved['slots'] and 'source_composition' not in recipe and (status != 'accepted_inactive' or not resolved['evidence'][0].get('accepted_absence')):
        raise GeneratorError('unsupported_binding', '/slots', 'Unresolved active recipe cannot masquerade as inactivity')
    resolved['inputs'] = copy.deepcopy(inputs)
    resolved['inputs']['holidays'] = calendar['holidays']
    if 'source_composition' in recipe:
        resolved['inputs']['source_composition']=copy.deepcopy(recipe['source_composition'])
    channels = {}
    for slot, source in recipe['reference_sources'].items():
        channels[slot] = (copy.deepcopy(source['values']) if source.get('type') == 'annual'
                          else evaluate_rules(source, inputs['year'], calendar['holidays'])['values'])
    targets = {d['demand_id']: reference_budget(d, channels.get(d['slot'], [])) for d in resolved['demands']}
    resolved['inputs']['reference_channels'] = channels
    resolved['inputs']['reference_budgets'] = targets
    resolved['inputs']['companion_rules'] = copy.deepcopy(recipe['companion_rules'])
    context = copy.deepcopy(recipe['source_context'])
    context.update(year=inputs['year'], holidays=calendar['holidays'])
    resolved['inputs']['source_context'] = context
    return resolved


def verify_caller_water_programme(instance: dict, resolved: dict, requirement: dict) -> None:
    """Keep a caller programme's water demand as independent non-owning source authority."""
    programme=requirement['programme']['value']
    source=resolved.get('source',{})
    if (instance.get('program_id')!=programme['id'] or resolved.get('program_id')!=programme['id'] or
            resolved.get('required_service_links')!=[] or
            resolved.get('required_service_sets')!=[requirement] or
            any(source.get(k)!=programme.get(v) for k,v in (
                ('source_id','source_id'),('building_type','building_type'),
                ('template','template'),('evidence_view','evidence_view'))) or
            any(d.get('quantity')=='hot_water_volume' for d in resolved.get('demands',[])) or
            any(s.get('slot')=='hot_water_volume' for s in resolved.get('slots',[]))):
        raise GeneratorError('source_integrity','/program_id',
                             'Caller programme must retain one independently compiled water requirement without a local water owner')
