"""Field-based construction/system reviews with preserved user annotations."""
import argparse
from collections import Counter, defaultdict
import hashlib
import re

from scripts.common import ROOT, load_json, dump_json
from scripts.definition_release import read_bundle
from scripts.recover_energy_inputs import BASE, CONSTRUCTION, SYSTEM

DATE = '2026-10-12'
BLOCK = re.compile(r'<!-- annotation:([^\n]+):begin -->\n(.*?)\n<!-- annotation:\1:end -->', re.S)
OPAQUE = {'roughness','thermal_absorptance','solar_absorptance','visible_absorptance'}
GLASS = {'optical_data_type','thickness_m','conductivity_W_m_K','solar_transmittance_at_normal_incidence',
         'front_side_solar_reflectance_at_normal_incidence','back_side_solar_reflectance_at_normal_incidence',
         'visible_transmittance_at_normal_incidence','front_side_visible_reflectance_at_normal_incidence',
         'back_side_visible_reflectance_at_normal_incidence','infrared_transmittance_at_normal_incidence',
         'front_side_infrared_hemispherical_emissivity','back_side_infrared_hemispherical_emissivity',
         'dirt_correction_factor_for_solar_and_visible_transmittance','solar_diffusing'}


def material_requirements(row):
    model = row.get('model')
    if model == 'StandardOpaqueMaterial':
        return OPAQUE|{'thickness_m','conductivity_W_m_K','density_kg_m3','specific_heat_J_kg_K'}
    if model == 'MasslessOpaqueMaterial':
        return OPAQUE|{'resistance_m2_K_W'}
    if model == 'SimpleGlazing':
        return {'u_W_m2_K','shgc','visible_transmittance'}
    if model == 'Gas':
        return {'gas_type','thickness_m'}
    if model == 'StandardGlazing':
        return GLASS
    return set()


def collect(bundle, constructions, systems):
    stats = {k:defaultdict(lambda:{'eligible':0,'known':0,'unresolved':0,'consumer_binding':0,
                                 'source_recoverable':0,'patterns':Counter(),'affected_ids':set(),
                                 'examples':[],'proposal':''}) for k in ('construction','system')}

    def observe(family, field, row, status, pattern, proposal):
        item = stats[family][field]
        item['eligible'] += 1
        item[status] += 1
        item['proposal'] = proposal
        if status != 'known':
            item['patterns'][str(pattern)] += 1
            item['affected_ids'].add(row['id'])
            if len(item['examples']) < 3:
                item['examples'].append(row['id'])

    def observe_recovery(family, rows):
        for row in rows.values():
            ctx = row.get('source_context', {})
            pattern = ctx.get('role') or ctx.get('system_type') or ctx.get('building_type') or row.get('role','unknown')
            for field in row.get('required_bindings', []):
                observe(family,'required_bindings.'+field,row,'consumer_binding',pattern,
                        'Retain an explicit consumer operand; no Atlas value is substituted. Bind it when assigning this independent object to a simulation.')
            for field in row.get('unresolved', []):
                observe(family,'unresolved.'+field,row,'unresolved',pattern,
                        'Keep blocked until the pinned source calculation/recipe and its operands are recovered. No new physical fallback is approved.')

    observe_recovery('construction',constructions['records'])
    observe_recovery('system',systems['records'])
    observe_recovery('system',systems['water_heaters'])

    for row in bundle['constructions']:
        rec = constructions['records'].get(row['id'], {})
        if row.get('representation') != 'package':
            layers = rec.get('recovered', {}).get('layers', row.get('layers'))
            observe('construction','layers',row,'known' if layers else 'unresolved',row.get('role'),
                    'Recover ordered source layers and thermal mass. Twelve selector-only glazing collisions are resolved in the recovery sidecar; 41 residential enclosure translations remain blocked.')
        for field in ('u_W_m2_K','shgc','visible_transmittance','f_W_m_K','c_W_m2_K'):
            if field not in row.get('parameters',{}):
                continue
            # U/F/C and optical requirements are alternatives, not one universal tuple.
            role = row.get('role','')
            if field in {'shgc','visible_transmittance'} and role != 'ExteriorWindow':
                continue
            if field == 'u_W_m2_K' and (row.get('ground_model','').startswith(('F-factor','C-factor')) or role == 'package'):
                continue
            if field == 'f_W_m_K' and row.get('ground_model') != 'F-factor ground floor':
                continue
            if field == 'c_W_m2_K' and row.get('ground_model') != 'C-factor underground wall':
                continue
            ground_model=rec.get('recovered',{}).get('ground_model',row.get('ground_model'))
            if field=='c_W_m2_K' and ground_model=='layered_U_ground_construction':
                continue
            value = rec.get('recovered',{}).get('parameters',{}).get(field,row['parameters'][field])['value']
            layers = rec.get('recovered',{}).get('layers',row.get('layers',[]))
            recovered = any(layer['properties'].get(field) is not None for layer in layers)
            if field == 'u_W_m2_K' and layers and value is None and role != 'ExteriorWindow':
                status = 'source_recoverable'
            elif field in {'shgc','visible_transmittance'} and any(l['properties'].get('model')=='StandardGlazing' for l in layers):
                status='known' if value is not None else 'source_recoverable'
            else:
                status = 'known' if value is not None or recovered else 'unresolved'
            observe('construction','parameters.'+field,row,status,role,
                    'Use the applicable source material/assembly model. Glazing source-code VT defaults stay labeled; opaque U can be calculated from layers with an explicit film convention. F/C models retain geometry operands; do not fill inapplicable optical fields.')
        if row.get('derivation') == 'assumed':
            observe('construction','existing_assumptions',row,'source_recoverable',row.get('role'),
                    'Retain the four existing internal/ground-contact generic assumptions and their policy scope; no new default is introduced. Review applicability before using them.')

    for row in bundle['materials']:
        required = material_requirements(row)
        for field in sorted(required):
            restored=constructions.get('materials',{}).get(row['id'],{}).get('fields',{}).get(field)
            status='known' if row.get(field) is not None else 'source_recoverable' if restored is not None else 'unresolved'
            observe('construction','materials.'+field,row,status,row.get('model'),
                    'Require this property only for applicable material models. 166 material instances have source/runtime defaults recovered with raw null retained: solar/visible nil.to_f setters produce zero; rejected thermal zero retains SDK 0.9; massless roughness retains SDK Smooth. No fabricated mass is added.')

    for row in bundle['hvac_systems']:
        for field, param in row.get('parameters',{}).items():
            if field == 'efficiency_or_cop':
                status = 'known' if param['value'] is not None else 'source_recoverable'
                proposal = 'Replace the ambiguous aggregate with component-level rating metrics and conditional predicates. Missing operating performance still blocks equipment; do not convert SEER/EER/AFUE into one system COP.'
            else:
                status = 'known' if param['value'] is not None else 'unresolved'
                proposal = 'Recover exact source component/recipe semantics; descriptor categories alone do not specify fuel conversion, terminals or ventilation controls. Keep unresolved when no exact source binding is available.'
            observe('system','parameters.'+field,row,status,row.get('system_type'),proposal)
    for row in bundle['components']:
        role = row.get('role')
        for field, param in row.get('parameters',{}).items():
            if field in {'rated_capacity','capacity'} and param.get('value') is None:
                status = 'consumer_binding'
            else:
                status = 'known' if param.get('value') is not None else 'unresolved'
            observe('system','components.'+role+'.'+field,row,status,role,
                    'Sizing is a consumer operand. Recover efficiency, fan performance, curves and controls from exact source helpers/rating conditions; no common fallback performance is approved.')
        for field in row.get('required_inputs',[]):
            status = 'consumer_binding' if field in {'rating_capacity_W','consumer_sizing'} else 'unresolved'
            observe('system','components.required_inputs.'+field,row,status,role,
                    'Preserve capacity-band/date predicates and original metrics. Capacity can come from sizing; source subtype, rating conditions and curve/control assignment require exact source evidence.')
        if role == 'performance_curve':
            observe('system','components.curve_assignment',row,'unresolved',role,
                    '726 source curves are available but unassigned. Recover exact component association and independent-variable domains; similarity of names is insufficient.')

    def observe_component(component):
        for name,param,status in _component_observations(component):
            observe('system','recovered.'+component['role']+'.'+name,component,status,component['role'],
                    'Use the recovered SI source field with its exact metric and default provenance. Unknown capacities are sizing operands; active missing physical fields remain blocked. Alternative HPXML fields are not universally required.')

    for row in systems['records'].values():
        for component in row.get('recovered',{}).get('equipment',[]):
            observe_component(component)
    for row in systems['water_heaters'].values():
        observe_component(row)

    def finish(family, count):
        fields = []
        for name,item in sorted(stats[family].items()):
            fields.append({'field':name,**{k:v for k,v in item.items() if k not in {'affected_ids','patterns'}},
                           'affected_ids':sorted(item['affected_ids']),'patterns':dict(sorted(item['patterns'].items()))})
        return {'records':count,'fields':fields}
    return {'schema_version':'1.0.0','date':DATE,
            'construction':finish('construction',len(constructions['records'])),
            'system':finish('system',len(systems['records'])+len(systems['water_heaters']))}

def _component_observations(component):
    """Yield model-applicable recovered operands, retaining explicit unknowns."""
    role = component['role']
    fields = component['fields']
    heater_type = fields.get('water_heater_type',{}).get('value')
    for name,param in fields.items():
        if name == 'tank_volume' and heater_type == 'instantaneous water heater':
            continue
        if param['value'] is None:
            # HPXML includes all alternative rating/backup/solar fields; absence
            # of an alternative is not a requirement for every equipment type.
            if name not in {'heating_capacity','cooling_capacity','temperature','location'}:
                continue
            status = 'consumer_binding' if name.endswith('_capacity') or name=='location' else 'unresolved'
        else:
            status = 'known'
        yield name,param,status


def render(title, review, previous=''):
    annotations = {}
    for match in BLOCK.finditer(previous):
        if match[1] in annotations:
            raise ValueError('Duplicate annotation '+match[1])
        annotations[match[1]] = match[2]
    if previous.count('<!-- annotation:') != len(annotations)*2:
        raise ValueError('Malformed annotation markers')
    lines = [f'# {title} JSON field review','',f'Updated: {DATE}. Reviewed objects: {review["records"]}.','',
             'One entry per field/property across applicable records. Counts are field occurrences;',
             'the JSON census retains every affected ID. Model-inapplicable properties are excluded.',
             'Unprefixed definition fields describe the frozen baseline; `recovered.*` fields describe',
             'the new source sidecars. They are separate populations, not additive gap counts.',
             'Source recovery inputs remain separate from published program JSON and frozen definitions.',
             'A recovered recipe is not proof that an engine model is ready. No new Atlas physical defaults are applied.','',
             '**Scope:** source-defined defaults and prior approved assumptions only. Unresolved physics',
             'blocks readiness; geometry, sizing and assignment are explicit consumer inputs.','',
             '**Evidence:** [coverage census](energy-json-field-coverage.json),',
             '[work record](json-completion-work-record.md), and',
             '[source-recovery decisions](../adr/0017-independent-energy-source-recovery.md).','',
             '| Field | Applicable | Known | Unresolved | Consumer input | Recoverable / reviewed policy |',
             '| --- | ---: | ---: | ---: | ---: | ---: |']
    shown=[]
    for f in review['fields']:
        if not any(f.get(k,0) for k in ('unresolved','consumer_binding','source_recoverable')):
            continue
        shown.append(f)
        lines.append(f'| `{f["field"]}` | {f["eligible"]} | {f["known"]} | {f["unresolved"]} | {f["consumer_binding"]} | {f.get("source_recoverable",0)} |')
    for f in shown:
        key=f['field']
        patterns='; '.join(f'{k} ({v})' for k,v in sorted(f['patterns'].items(),key=lambda x:(-x[1],x[0])))
        lines += ['',f'## `{key}`','',f'**Pattern:** {patterns}.','',f'**Proposal / resolution:** {f["proposal"]}','',
                  '**Representative IDs:** '+', '.join('`'+i+'`' for i in f['examples'])+'.','',
                  '**User comments / decision:**','',f'<!-- annotation:{key}:begin -->',
                  annotations.pop(key,'<!-- Write here. -->'),f'<!-- annotation:{key}:end -->']
    for key,comment in sorted(annotations.items()):
        lines += ['',f'## Prior annotation: `{key}`','', 'This field is no longer an active gap; its annotation is retained.',
                  '',f'<!-- annotation:{key}:begin -->',comment,f'<!-- annotation:{key}:end -->']
    return '\n'.join(lines)+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    result=collect(read_bundle(BASE),load_json(CONSTRUCTION),load_json(SYSTEM))
    paths=[BASE/'manifest.json',CONSTRUCTION,SYSTEM,ROOT/'scripts/energy_json_review.py']
    result['input_sha256']={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    census=ROOT/'docs/reviews/energy-json-field-coverage.json'
    if args.check:
        if load_json(census)!=result:
            raise ValueError('Field coverage differs')
    else:
        dump_json(census,result)
    for family,title in [('construction','Construction'),('system','HVAC and hot-water system')]:
        path=ROOT/f'docs/reviews/{family}-json-field-review.md'
        previous=path.read_text(encoding='utf-8') if path.exists() else ''
        text=render(title,result[family],previous)
        if args.check:
            if previous!=text:
                raise ValueError('Field review differs: '+family)
        else:
            path.write_text(text,encoding='utf-8',newline='\n')
    print('Construction/system field reviews and annotation preservation verified')


if __name__=='__main__':
    main()
