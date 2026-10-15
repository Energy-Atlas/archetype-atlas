"""Audited standalone adaptation of ordered ComStock conditional selection.

The caller passes the already derived commercial_group_seed. This wrapper
does not reproduce NumPy/Sobol population matrices or their random state.
"""
import copy
import math
import platform
import random

from ..errors import GeneratorError


def select_conditional(table: dict, selectors: dict, uniform: float) -> dict:
    """First original option whose unnormalized raw CDF strictly exceeds draw."""
    if isinstance(uniform, bool) or not isinstance(uniform, (int, float)) or not math.isfinite(uniform) or not 0 <= uniform < 1:
        raise GeneratorError('invalid_draw', '/commercial/uniform', 'Uniform in [0,1) required')
    for dependency in table['dependencies']:
        if dependency not in selectors or selectors[dependency] is None:
            raise GeneratorError('missing_dependency', '/commercial/'+dependency, 'Exact original source selector required')
    matches = [row for row in table['rows'] if all(row['selectors'].get(d) == selectors[d] for d in table['dependencies'])]
    if len(matches) != 1:
        raise GeneratorError('source_selection', '/commercial/selectors', 'Conditional selectors must resolve exactly one source row')
    row = matches[0]
    cdf = []
    cumulative = 0.0
    for probability in row['probabilities']:
        if not math.isfinite(probability) or probability < 0:
            raise GeneratorError('invalid_probability', '/commercial/row', 'Invalid raw probability')
        cumulative += probability
        cdf.append(cumulative)
    if len(cdf) != len(table['options']) or not math.isclose(cumulative, 1, rel_tol=0, abs_tol=1e-6):
        raise GeneratorError('invalid_probability', '/commercial/row', 'Raw probabilities must sum within audited tolerance')
    index = next((i for i, value in enumerate(cdf) if value > uniform), None)
    if index is None:
        raise GeneratorError('source_selection', '/commercial/uniform',
            f'Draw outside raw source CDF; source_row={row["source_row"]}; selectors={selectors!r}; '
            f'raw_cdf_sum={cumulative!r}; uniform={uniform!r}; no selected option, retry or tail fill')
    option = table['options'][index]
    value = table['option_values'][index] if 'option_values' in table else option
    return {'source_row': row['source_row'], 'original_option': option, 'option_index': index,
            'value': value, 'unit': table.get('option_unit'), 'modify': option != 'NA',
            'original_probabilities': copy.deepcopy(row['original_values']),
            'probabilities': list(row['probabilities']), 'raw_cdf': cdf}


def sample_operating_parameters(inputs: dict, group_seed: int, resources) -> dict:
    """Draw exactly once for each of ten source parameters, including constants."""
    selector=inputs.get('building_type') if isinstance(inputs,dict) else None
    if selector not in {'medium_office','small_office','warehouse','full_service_restaurant','quick_service_restaurant'}:
        raise GeneratorError('invalid_conditioning','/commercial/inputs','Exact audited selector required')
    prefix='' if selector=='medium_office' else selector+'__'
    audit = resources.get('commercial', prefix+'sampling-audit')
    if (audit.get('gate_status') != 'passed' or audit.get('population_realization_equivalent') is not False
            or audit.get('conditioning_inputs') != {'building_type':selector}
            or audit.get('configuration_id') != selector+'_90_1_2013'
            or audit.get('tsv_version') != 'v33' or audit.get('stock_year_context') != 2018
            or audit.get('standards_dependency',{}).get('version') != '0.8.6'
            or len(audit.get('parameters',[])) != 10
            or any(p.get('decision') != 'resolved' for p in audit.get('parameters', []))
            or audit.get('standalone_policy', {}).get('name') != 'atlas_conditional_seeded_v1'):
        raise GeneratorError('sampling_gate', '/commercial', 'Passed standalone sampling audit required')
    if not isinstance(inputs, dict) or inputs != audit['conditioning_inputs']:
        raise GeneratorError('invalid_conditioning', '/commercial/inputs', 'Exact audited selectors required; operating values are sampled')
    if isinstance(group_seed, bool) or not isinstance(group_seed, int) or not 0 <= group_seed < 2**256:
        raise GeneratorError('invalid_seed', '/commercial/group_seed', 'Already derived unsigned SHA-256 group seed required')
    rng = random.Random(group_seed)
    selected, values, receipts = {}, {}, []
    selectors = dict(inputs)
    order = audit['standalone_policy']['draw_order']
    if order != audit['selected_parameter_order'] or len(order) != 10:
        raise GeneratorError('sampling_gate', '/commercial/draw_order', 'Audited ten-parameter source order required')
    for parameter in order:
        table = resources.get('commercial', prefix+parameter)
        conditioning = {d: selectors.get(d) for d in table['dependencies']}
        uniform = rng.random()
        selection = select_conditional(table, conditioning, uniform)
        selected[parameter] = selection['original_option']
        selectors[parameter] = selection['original_option']
        values[parameter] = {'value': selection['value'], 'unit': selection['unit'], 'modify': selection['modify']}
        receipts.append({'parameter': parameter, 'selectors': conditioning, 'uniform': uniform,
                         'selection': selection, 'provenance': table['provenance']})
    population=copy.deepcopy(audit['upstream_population_context'])
    population['upstream_cli_modes']=population['sampler_mode']
    population['sampler_mode']=None
    return {'effective_values': values, 'selected_options': selected, 'draw_receipts': receipts,
            'group_seed': group_seed, 'conditioning_inputs': copy.deepcopy(inputs),
            'sampler_policy': copy.deepcopy(audit['standalone_policy']),
            'rng': {'algorithm': audit['standalone_policy']['rng_algorithm'], 'python_version': platform.python_version()},
            'adaptation': audit['standalone_policy']['comparison_boundary'],
            'population_realization_equivalent': False,
            'upstream_population_context': population,
            'configuration': {k: audit[k] for k in ('configuration_id', 'source_revision', 'tsv_version', 'stock_year_context', 'reference_template')}}
