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
    recipe = resources.get('program', program_id)['recipe']
    if not isinstance(inputs, dict):
        raise GeneratorError('invalid_input', '/inputs', 'Explicit recipe operands required')
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
