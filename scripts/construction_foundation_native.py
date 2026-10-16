"""Normalize native ground capture into internal recipes, retaining source evidence."""
import copy
import math
from scripts.definition_contract import stable_id

from scripts.construction_foundation_recovery import DATE


def group_commercial_cases(rows):
    """Intern equal physical lookup results only within one reference archetype.

    Query inventory includes a climate key whenever source geometry uses/forwards
    climate, conservatively disabling cross-climate geometry sharing in that case.
    """
    groups={}
    for row in rows:
        if row.get('status')!='source_queries_recovered':
            raise ValueError('Unresolved source query: '+row.get('error','unknown'))
        key=stable_id('foundation-case',{'template':row['template'],
            'building_type':row['building_type'],'physics':row['physics_signature']})
        entry=groups.setdefault(key,{'representative':copy.deepcopy(row),'contexts':[]})
        entry['contexts'].append(row['climate_zone'])
    return groups


def initialization_weights(spec):
    """Pinned constructions.rb#apply_kiva_initial_temperature, SI affine form."""
    host=spec['host'];ceiling=spec['ceiling_insulated'];wall=spec['walls_insulated']
    if host in {'conditioned space','basement - conditioned','crawlspace - conditioned'}:
        return {'outdoor':0.,'ground':0.,'indoor':1.,'offset_K':0.}
    if host=='basement - unconditioned':
        g,o,i=(.75,.25,0.) if ceiling else ((.5,0.,.5) if wall else (.5,.2,.3))
    elif host=='crawlspace - vented':
        g=0.;o,i=(.9,.1) if ceiling else ((.25,.75) if wall else (.5,.5))
    elif host=='crawlspace - unvented':
        g=0.;o,i=(.85,.15) if ceiling else ((.25,.75) if wall else (.4,.6))
    elif host=='garage':
        return {'outdoor':1.,'ground':0.,'indoor':0.,'offset_K':11*5/9}
    else:raise ValueError('Unhandled source foundation host: '+host)
    return {'outdoor':o,'ground':g,'indoor':i,'offset_K':0.}


def initial_temperature_C(spec,outdoor,ground,heat,cool,controls):
    weights=initialization_weights(spec)
    if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (outdoor,ground)):
        raise ValueError('Missing source initialization weather')
    indoor=outdoor
    if controls:
        if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (heat,cool)) or heat>cool:
            raise ValueError('Missing/invalid conditioned setpoints')
        if outdoor<10:indoor=heat
        elif outdoor>15:indoor=cool
        else:indoor=heat*(15-outdoor)/5+cool*(outdoor-10)/5
    return weights['outdoor']*outdoor+weights['ground']*ground+weights['indoor']*indoor+weights['offset_K']


def validate_achieved_factors(row,signature):
    # Existing source table SI conversion precision is a comparison tolerance,
    # not a replacement for the full-precision native values in the capture.
    for face in row['surfaces']:
        recipe=face['recipe'];model=recipe['model']
        if model=='FFactorGroundFloorConstruction':
            props=signature.get('explicit_floor') or {}
            target=props.get('assembly_maximum_f_factor');value=recipe['f_W_m_K'];scale=1.730734667
        elif model=='CFactorUndergroundWallConstruction':
            props=signature.get('explicit_wall') or {}
            target=props.get('assembly_maximum_c_factor');value=recipe['c_W_m2_K'];scale=5.678263337
        else:continue
        if target is None or not math.isclose(value,target*scale,rel_tol=1e-8,abs_tol=1e-10):
            raise ValueError('Native source factor differs from its source lookup target')


def validate_execution(data,census):
    expected={c['reference_id']+'/'+c['climate_zone'] for c in census['contexts'].values() if c['candidate_elements']}
    if set(data['commercial_context_cases'])!=expected:
        raise ValueError('Incomplete commercial execution context census')
    if set(data['commercial_context_cases'].values())!=set(data['commercial']):
        raise ValueError('Orphan/missing native commercial context case')
    for identity,row in data['commercial'].items():
        if row.get('status')!='recovered' or not row['surfaces']:
            raise ValueError('Unresolved commercial executable physics')
        validate_achieved_factors(row,data['commercial_query_groups'][identity]['representative']['physics_signature'])
    suites=[s for s in census['suites'].values() if s['scope']=='whole_dwelling']
    if {s['source_fixture_id'] for s in suites}!=set(data['residential']):
        raise ValueError('Incomplete residential source context census')
    for suite in suites:
        row=data['residential'][suite['source_fixture_id']]
        expected={e['id'] for e in suite['deferred_elements']}
        actual={e['attributes']['id'] for e in row['source_elements']}
        if actual!=expected:raise ValueError('Missing/unexpected deferred source object')
        if bool(row['surfaces'])!=(suite['disposition']!='source_supported_no_contact'):
            raise ValueError('Source-supported absence/executable physics contradiction')
        for kiva in row['kiva']:
            spec=kiva['initialization']
            if len(spec['numerical_verification'])!=6:raise ValueError('Missing source initialization verification')
            for p in spec['numerical_verification']:
                t=initial_temperature_C(spec,p['outdoor_C'],p['ground_C'],p['heat_C'],p['cool_C'],p['controls'])
                if not math.isclose(t,p['result_C'],abs_tol=1e-10):raise ValueError('Source initialization mismatch')


def normalize_foundation_execution(native: dict, source_receipts: dict) -> dict:
    if native.get('status')!='recovered':
        raise ValueError('Native foundation recovery blocked: '+native.get('error','unknown source failure'))
    result=copy.deepcopy(native)
    for face in result.get('surfaces',[]):
        recipe=face.pop('construction')
        model=recipe['model']
        if model in {'FFactorGroundFloorConstruction','CFactorUndergroundWallConstruction'}:
            if face['boundary']!='GroundFCfactorMethod':
                raise ValueError('Native F/C factor has incompatible source boundary')
            factor=recipe['f_W_m_K' if model.startswith('F') else 'c_W_m2_K']
            if not math.isfinite(factor) or factor<=0:
                raise ValueError('Invalid native ground factor')
        elif model!='Construction':
            raise ValueError('Unsupported native construction: '+model)
        geometry={k.removeprefix('reference_'):recipe.pop(k) for k in list(recipe) if k.startswith('reference_')}
        face['recipe']=recipe
        face['reference_geometry']=geometry
    result['provenance']={'source_receipts':copy.deepcopy(source_receipts),
        'extraction_date':DATE,'original_value':copy.deepcopy(native),
        'original_unit':'native SDK SI operands and categorical boundary identifiers',
        'transformation':'Preserve executed native physics; separate source-reference geometry from reusable recipe',
        'interpretation_note':'Internal source execution evidence, not a consumer-ready release receipt'}
    if 'source_elements' in native:
        result['provenance']['original_unit']={
            'engine_surfaces_materials_kiva':'SDK SI: m, m2, W/(m K), kg/m3, J/(kg K), C; dimensionless absorptances',
            'source_elements':{'area':'ft2','azimuth':'degree',
                'depth_below_grade':'ft','exposed_perimeter':'ft','height':'ft',
                'thickness':'in','interior_finish_thickness':'in',
                'insulation_exterior_distance_to_bottom':'ft','insulation_exterior_distance_to_top':'ft',
                'insulation_interior_distance_to_bottom':'ft','insulation_interior_distance_to_top':'ft',
                'perimeter_insulation_depth':'ft','under_slab_insulation_width':'ft',
                'exterior_horizontal_insulation_depth_below_grade':'ft','exterior_horizontal_insulation_width':'ft',
                '*_r_value':'h ft2 F/Btu',
                'carpet_fraction/emittance/solar_absorptance':'1',
                'ids/types/adjacency/orientation/colors/flags':'categorical identifiers or booleans'},
            'source_foundations.vented_crawlspace_sla':'1',
            'host_airflow.unvented_ach':'1/h','host_airflow.reference_height_ft':'ft',
            'captures.recipe.source_layers':'Units explicitly encoded in field names; path fractions dimensionless'}
    return result
