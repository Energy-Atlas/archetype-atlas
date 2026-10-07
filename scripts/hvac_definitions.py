"""Fixed library HVAC component descriptors and explicitly conditional ratings."""
import copy
from scripts.common import load_json
from scripts.definition_contract import DefinitionBundle, parameter, record, stable_id, evidence
from scripts.definition_compare import physical_properties
from scripts.program_definitions import source_evidence

BTUH_TO_W = .2930710701722222
ANCILLARY = {'Refrigeration_system', 'Exhaust Fan', 'Zone Ventilation'}


def normalize_rule(source, rating_date):
    attr = copy.deepcopy(source['source_attributes'])
    predicates = {k:v for k,v in attr.items() if k not in source['metrics']}
    for key in ('minimum_capacity','maximum_capacity'):
        value = predicates.pop(key, None)
        predicates[key+'_W'] = value*BTUH_TO_W if value is not None else None
    metrics = {}
    for name,value in source['metrics'].items():
        if value is None:
            continue
        # EER/SEER are ratings, not instantaneous COP. Retain their metric names.
        native_ip = 'energy_efficiency_ratio' in name or 'seasonal_energy_efficiency_ratio' in name
        metrics[name] = {'value': value*BTUH_TO_W if native_ip else value,
                         'unit': 'W/W' if native_ip else '1', 'original_value': value,
                         'original_unit': 'Btu/Wh' if native_ip else 'dimensionless source rating',
                         'transformation': 'Btu/Wh to W/W; metric unchanged' if native_ip else 'identity'}
    return {'id': stable_id('performance-rule', {'source':source['id']}),
            'role': 'conditional_performance_rule', 'source_id':source['id'],
            'template':source['template'], 'equipment_table':source['equipment_table'],
            'predicates':predicates, 'metrics':metrics, 'rating_date':rating_date,
            'status':'conditional_unassigned', 'required_inputs':['rating_capacity_W',
                 'source_equipment_subtype', 'applicable_rating_conditions'],
            'interpretation':'No capacity is selected by the atlas; do not treat seasonal or integrated ratings as COP.'}


def build_hvac(context):
    bundle = DefinitionBundle()
    templates = {r['template'] for r in context.atlas.get('systems',[]) if context.includes(r)}
    rule_ids = {}
    for source in context.atlas.get('efficiency_rules',[]):
        if source['template'] not in templates:
            continue
        row = normalize_rule(source,context.policy.get('rating_date',context.extraction_date))
        eid = source_evidence(context,source,'metrics','source efficiency rating',bundle)
        row['evidence_ids'] = [eid]
        bundle['components'].append(row)
        rule_ids.setdefault(source['template'],[]).append(row['id'])
    for source in context.atlas.get('systems',[]):
        if not context.includes(source):
            continue
        row=record('hvac_system',source)
        row.update(system_type=source['system_type'], component_ids=[], connections=[],
                   topology_status='source_roles_only; consumer graph assignment unresolved',
                   serving_scope='source_package; consumer assignment required',
                   required_inputs=['serving_assignment'],
                   representation='ancillary_equipment' if source['system_type'] in ANCILLARY else 'system_package')
        for field,unit in [('heating_fuel','source fuel'),('efficiency_or_cop','1'),
                           ('zone_terminal_type','source technology'),('ventilation_strategy','source strategy')]:
            eid=source_evidence(context,source,field,unit,bundle)
            row['parameters'][field]=parameter(source.get(field),unit,eid)
            row['evidence_ids'].append(eid)
        attributes=source['source_attributes']
        for role,key in [('fan','fan_type'),('heating','heating_type'),('cooling','cooling_type'),
                         ('terminal','zone_terminal_type')]:
            if attributes.get(key) is None:
                continue
            eid=evidence(context, None, source['id']+'/source_attributes/'+key,
                         attributes[key], 'source technology', 'identity; no inferred performance',
                         'Source descriptor identifies a component role, not a fully instantiated model.')
            bundle['provenance'].append(eid)
            component={'role':role,'technology':attributes[key],
                       'parameters':{name:parameter(None,unit,eid['id']) for name,unit in
                           ([('pressure_rise','Pa'),('efficiency','1')] if role=='fan' else
                            [('efficiency_or_cop','1'),('rated_capacity','W')])},
                       'curve_ids':[], 'performance_rule_ids':rule_ids.get(source['template'],[]) if role in {'heating','cooling'} else [],
                       'performance_assignment':'unresolved source-specific subtype/rating selection',
                       'evidence_ids':[eid['id']]}
            component['performance_id']=stable_id('component-performance',physical_properties(component))
            component['id']=stable_id('component',{'source':source['id'],'role':role})
            row['component_ids'].append(component['id']);bundle['components'].append(component)
        row['source_descriptor']=copy.deepcopy(attributes)
        row['schedule_ids']=[source[k] for k in ('system_schedule_id','oa_schedule_id') if source.get(k)]
        row['performance_id']=stable_id('hvac-performance',physical_properties({
            'system_type':row['system_type'],'parameters':row['parameters'],
            'components':[c for c in bundle['components'] if c['id'] in row['component_ids']]}))
        if source['system_type'] in ANCILLARY:
            row['role']='ancillary_equipment'
            bundle['components'].append(row)
            bundle['coverage'].append({'id':'coverage-'+source['id'],'source_id':source['id'],
                'status':'supporting_ancillary_equipment','reason':'Exhaust, ventilation or refrigeration descriptor is not a complete HVAC system',
                'definition_id':row['id']})
        else:bundle['hvac_systems'].append(row)
    path='lib/openstudio-standards/standards/ashrae_90_1/data/ashrae_90_1.curves.json'
    if path in context.sources:
        for index,curve in enumerate(load_json(context.sources[path])['curves']):
            eid=evidence(context,stable_id('sourcefile',{'path':path}),path+f'#/curves/{index}',
                         curve,'source curve coefficients and independent-variable units',
                         'identity; retain coefficients, variable/output limits and original domains',
                         'Supporting curve is available, not assigned without source component evidence.')
            bundle['provenance'].append(eid)
            bundle['components'].append({'id':stable_id('curve',{'path':path,'index':index}),
                'role':'performance_curve','definition':curve,'assignment_status':'unassigned',
                'evidence_ids':[eid['id']]})
    wanted={sid for r in bundle['hvac_systems']+bundle['components'] for sid in r.get('schedule_ids',[])}
    bundle['schedules']=[s for s in context.atlas.get('schedules',[]) if s['id'] in wanted]
    return DefinitionBundle().merge(bundle)
