"""Compose paired complete construction exports from frozen source inputs only."""
import copy
import math
from collections import defaultdict
from functools import lru_cache
from scripts.common import ROOT,load_json
from scripts.definition_contract import stable_id
from scripts.construction_foundation_recovery import sha,DATE
from scripts.construction_foundation import ROLES,TARGETS,validate_foundation_extension
from scripts.construction_foundation_profiles import build_foundation_profile
from scripts.construction_foundation_native import initialization_weights
from scripts.construction_equivalence import reduce_opaque

EXECUTION=ROOT/'data/construction-inputs/foundation-execution-v1.json'
AIRFLOW=ROOT/'data/construction-inputs/foundation-airflow-v1.json'


def clean_material(p):
    return {k:v for k,v in p.items() if k not in {'name','model','sdk_default_flags'} and v is not None}


def _all_refs(obj,keys):
    if isinstance(obj,dict):
        for k,v in obj.items():
            if k in keys:yield v
            else:yield from _all_refs(v,keys)
    elif isinstance(obj,list):
        for v in obj:yield from _all_refs(v,keys)


class ExtensionBuilder:
    def __init__(self,context,profile,proof):
        self.context=context;self.profile=profile;self.proof=proof
        self.assemblies={};self.materials={};self.methods={};self.settings={};self.geometry={}

    def material(self,p,model=None,name=None):
        model=model or p['model'];props=clean_material(p)
        mid=stable_id('foundation-material',{'proof':self.proof,'model':model,'properties':props})
        self.materials[mid]={'id':mid,'name':name or p.get('name') or model,'model':model,'properties':props,
            'property_evidence':{k:self.proof for k in props}}
        return mid

    def assembly(self,face):
        p=face['recipe'];model=p['model']
        data={'model':model,'status':'ready','evidence_ids':[self.proof]}
        if model=='Construction':
            data.update(model='native_opaque_layers',layers=[{'order':i,'material_id':self.material(p)} for i,p in enumerate(p['layers'])],
                        layer_orientation='exterior_to_interior')
        else:data.update({k:v for k,v in p.items() if k!='model'})
        aid=stable_id('foundation-assembly',data);data['id']=aid;self.assemblies[aid]=data
        return aid

    def require(self,key,unit,description,*,positive=False):
        self.geometry[key]={'unit':unit,'description':description}
        if unit!='topology':self.geometry[key]['exclusive_minimum' if positive else 'minimum']=0
        return key

    def ground_settings(self,kind):
        if kind=='Kiva':
            raw=self.profile['kiva_settings']
            soil={dst:raw[src] for src,dst in [('Soil Conductivity','conductivity_W_m_K'),('Soil Density','density_kg_m3'),('Soil Specific Heat','specific_heat_J_kg_K')]}
            matching=[mid for mid,m in self.materials.items() if all(m['properties'].get(k)==v for k,v in soil.items())]
            mid=matching[0] if matching else self.material(soil,model='BulkMaterial',name='Source Kiva soil')
            data={'model':'Kiva','soil_material_id':mid,'initialization_policy':'resstock_source_start_month_1.0.0',
                  'heating_balance_temperature_C':10.,'cooling_balance_temperature_C':15.}
            names={'Ground Solar Absorptivity':'ground_solar_absorptivity','Ground Thermal Absorptivity':'ground_thermal_absorptivity',
                'Ground Surface Roughness':'ground_surface_roughness_m','Far-Field Width':'far_field_width_m',
                'Deep-Ground Boundary Condition':'deep_ground_boundary_condition','Deep-Ground Depth':'deep_ground_depth_m',
                'Minimum Cell Dimension':'minimum_cell_dimension_m','Maximum Cell Growth Coefficient':'maximum_cell_growth_coefficient',
                'Simulation Timestep':'simulation_timestep'}
            data.update({dst:raw[src] for src,dst in names.items()})
        else:
            fc=kind in {'FFactor','CFactor'}
            data={'model':'FCBoundary' if fc else 'LayeredGroundBoundary',
                  'monthly_temperature_input':'fc_monthly_ground_temperature_C' if fc else 'surface_monthly_ground_temperature_C'}
        sid=stable_id('ground-model-parameters',data);self.settings[sid]=data;return sid

    def kiva_parameters(self,kiva,face,face_assemblies):
        raw=kiva['fields'];params={'wall_depth_below_slab_m':raw['Wall Depth Below Slab'],
            'initialization':initialization_weights(kiva['initialization'])}
        walls=[f for f in self.profile['faces'] if f['foundation_id']==face['foundation_id'] and f['role']=='FoundationWall']
        if walls:
            key=self.require('wall_height_above_grade_m','m','Actual foundation wall height above local grade')
            params['wall_height_above_grade']={'geometry_input':key}
        else:
            value=raw['Wall Height Above Grade'];a=self.assemblies[face_assemblies[face['name']]]
            mids=[l['material_id'] for l in a['layers'] if math.isclose(self.materials[l['material_id']]['properties'].get('thickness_m',-1),value,abs_tol=1e-10)
                  and 'concrete' in self.materials[l['material_id']]['name'].lower()]
            params['wall_height_above_grade']={'material_thickness_id':mids[0]} if mids else value
        for side in ('Interior Horizontal','Interior Vertical','Exterior Horizontal','Exterior Vertical'):
            material=raw.get(side+' Insulation Material Name')
            if not material:continue
            if not isinstance(material,dict):raise ValueError('Unresolved native Kiva insulation material')
            part={'material_id':self.material(material['material'])}
            for axis in ('Depth','Width'):
                value=raw.get(side+' Insulation '+axis)
                if isinstance(value,(int,float)):part[axis.lower()+'_m']=value
            params[side.lower().replace(' ','_')+'_insulation']=part
        pairs=list(raw.items());blocks=[]
        for i,(name,value) in enumerate(pairs):
            if not name.startswith('Custom Block Material Name'):continue
            if not isinstance(value,dict):raise ValueError('Unresolved native custom-block material')
            mid=self.material(value['material']);numbers=[v for _,v in pairs[i+1:i+4]]
            if len(numbers)!=3 or not all(isinstance(v,(int,float)) for v in numbers):raise ValueError('Malformed native Kiva custom block')
            depth,x,z=numbers
            block={'material_id':mid,'depth_m':depth,'x_m':x,'z_m':z}
            if walls:
                wall=walls[0];attr=wall['source_attributes'];side='interior' if 'interior' in value['material']['name'] else 'exterior'
                bottom='insulation_'+side+'_distance_to_bottom';top='insulation_'+side+'_distance_to_top'
                if attr.get(bottom+'_isdefaulted') and math.isclose(attr.get(bottom,-1),attr.get('height',-2),abs_tol=1e-8):
                    key=self.require('foundation_wall_height_m','m','Actual full foundation wall height',positive=True)
                    expr={'geometry_input':key};offset=-float(attr.get(top) or 0)*.3048
                    if offset:expr['offset_m']=offset
                    block['depth_m']=expr
                wa=self.assemblies[face_assemblies[wall['name']]]
                wall_thickness=sum(self.materials[l['material_id']]['properties']['thickness_m'] for l in wa['layers'])
                if side=='exterior' and math.isclose(x,wall_thickness,abs_tol=1e-9):block['x_m']={'assembly_thickness_id':wa['id']}
                elif side=='interior' and math.isclose(x,-self.materials[mid]['properties']['thickness_m'],abs_tol=1e-9):block['x_m']={'material_thickness_id':mid,'scale':-1}
            blocks.append(block)
        if blocks:params['custom_blocks']=blocks
        # Footing depth without a footing material is an unused SDK default.
        if raw.get('Footing Material Name') or raw.get('Footing Wall Construction Name'):
            raise ValueError('Source footing requires an explicit supported recipe; no generic footing fallback')
        return params

    def method(self,face,face_assemblies):
        boundary=face['boundary']
        if boundary in {'Surface','Adiabatic','Outdoors'}:return None
        model=face['recipe']['model']
        kind={'FFactorGroundFloorConstruction':'FFactor','CFactorUndergroundWallConstruction':'CFactor'}.get(model,'Kiva' if boundary=='Foundation' else 'LayeredGround')
        required=[self.require('surface_area_m2','m2','Actual assigned component surface area',positive=True)]
        params={}
        if kind in {'FFactor','Kiva'}:
            desc='Actual direct-ambient exposed edges; exclude zone edges; zero is supported' if kind=='FFactor' else 'Actual externally exposed foundation edges, with shared edges cancelled'
            required.append(self.require('exposed_perimeter_m','m',desc))
        if kind=='CFactor':required.append(self.require('foundation_wall_height_m','m','Actual underground wall height/depth',positive=True))
        if kind=='Kiva':
            required.append(self.require('foundation_group_topology','topology','Actual coupled slab/wall hosts and exposed edge grouping'))
            kiva=self.profile['kiva'][face['foundation_id']]
            params=self.kiva_parameters(kiva,face,face_assemblies)
        data={'model':kind,'model_parameters_id':self.ground_settings(kind),'parameters':params,'required_geometry':required}
        identity=stable_id('ground-method',data);self.methods[identity]=data;return identity


def _thermal_layers(recipe):
    result=[]
    for p in recipe['layers']:
        if p['model']=='StandardOpaqueMaterial':result.append({'R':p['thickness_m']/p['conductivity_W_m_K'],
            'C':p['thickness_m']*p['density_kg_m3']*p['specific_heat_J_kg_K']})
        elif p['model'] in {'MasslessOpaqueMaterial','AirGap'}:result.append({'R':p['resistance_m2_K_W'],'C':0.})
        else:raise ValueError('Unsupported ordinary foundation interface material')
    return result


def prepare_foundation_extension(source_context,recovered,profiles,representation='detailed'):
    """Prepare native resources and ordinary source-archetype equivalents."""
    c=source_context;profile=profiles
    if not profile['faces'] and c['configuration_type'] not in {'Above Apartment','Ambient'}:
        raise ValueError('Missing required executable foundation physics; not source-supported absence')
    proof=stable_id('foundation-evidence',{'capture':c['capture_id'],'sha256':c['input_sha256'],
        'airflow_sha256':c.get('airflow_sha256')})
    b=ExtensionBuilder(c,profile,proof)
    face_assemblies={f['name']:b.assembly(f) for f in profile['faces']}
    components={};unified={};equivalents={};exceptions=[]
    for role in ROLES:
        faces=[f for f in profile['faces'] if f['role']==role]
        groups=defaultdict(list)
        for face in faces:
            aid=face_assemblies[face['name']]
            method=b.method(face,face_assemblies) if role in {'GroundFloor','FoundationWall'} else None
            groups[(aid,method,face['boundary'],face['thermal_host'])].append(face)
        rules=[]
        for (aid,mid,boundary,host),members in sorted(groups.items(),key=lambda x:str(x[0])):
            physical_boundary='Ground' if boundary in {'Ground','GroundFCfactorMethod','Foundation'} else boundary
            when={'scope':'whole_dwelling' if c['residential'] else 'building_default','boundary_condition':physical_boundary}
            if c['residential']:when['thermal_host']=host
            rule={'assembly_id':aid,'source_definition_id':c['suite_id'],'source_selector':role,'when':when,
                'source_element_ids':sorted({f['source_element_id'] for f in members}),
                'geometry':{'area':{'method':'bem_surface_area','unit':'m2'},'layers':{'orientation':'exterior_to_interior','paired_surface_policy':'reverse_order','source_reference_reversed':False}},
                'evidence_ids':[proof]}
            if mid:rule['ground_method_id']=mid
            rule['id']=stable_id('construction-assignment',rule);rules.append(rule)
        components[role]={'target':copy.deepcopy(TARGETS[role]),'disposition':'provided' if rules else 'source_absent','assignments':rules}
        if not rules:
            unified[role]={'status':'not_applicable','assembly_id':None,'reason':'Source configuration has no applicable '+role};continue
        if role in {'RimJoist','FloorOverFoundation'}:
            total=sum(f['area_m2'] for f in faces)
            result=reduce_opaque([{'weight':f['area_m2']/total,'layers':_thermal_layers(f['recipe'])} for f in faces],
                films=(.13,.13) if role=='FloorOverFoundation' else (.04,.13))
            result['model']='opaque_layers'
            # Source absorptances are area-weighted at each exposed side, as in the current unified policy.
            surface={}
            for side,index in (('exterior',0),('interior',-1)):
                surface[side]={k:sum(f['area_m2']*f['recipe']['layers'][index][k] for f in faces)/total for k in ('thermal_absorptance','solar_absorptance','visible_absorptance')}
            result['surface_properties']=surface
            identity=stable_id('equivalent-foundation-assembly',result);result['id']=identity;equivalents[identity]=result
            unified[role]={'status':'ready','assembly_id':identity,'derivation':{'weight_basis':'source_archetype_net_component_area','source_reference_area_m2':total,
                'contributors':[{'assembly_id':face_assemblies[f['name']],'weight':f['area_m2']/total,'reference_area_m2':f['area_m2']} for f in faces]}}
        elif len(rules)==1:
            rule=rules[0];unified[role]={'status':'ready','assembly_id':rule['assembly_id'],'when':copy.deepcopy(rule['when'])}
            if rule.get('ground_method_id'):unified[role]['ground_method_id']=rule['ground_method_id']
        else:
            reason='Distinct native coupling, insulation, thermal hosts or soil/interzone boundaries; homogenization is not physically justified'
            unified[role]={'status':'ready','assembly_id':None,'assignments':copy.deepcopy(rules),'native_exception_reason':reason}
            exceptions.append({'role':role,'assignments':len(rules),'reason':reason})
    config={'type':c['configuration_type']}
    if not profile['faces']:config={'type':'no_direct_ground_contact','reason':c['absence_reason']}
    elif c['residential']:
        config['thermal_hosts']=sorted({f['thermal_host'] for f in profile['faces']})
        airflow=c['airflow'];exchange={}
        for host in config['thermal_hosts']:
            if host in {'basement - unconditioned','crawlspace - unvented'}:
                exchange[host]={'model':'constant_ach','ach_per_s':airflow['unvented_ach_per_s']}
            elif host=='crawlspace - vented':
                sla=[f['vented_crawlspace_sla'] for f in profile['source_foundations'] if f.get('vented_crawlspace_sla') is not None]
                if len(set(sla))!=1:raise ValueError('Ambiguous source vented-crawlspace SLA')
                exchange[host]={'model':'source_sla_annual','sla':sla[0],**airflow['vented_crawlspace'],
                    'weather_factor_input':'actual_weather_ashrae_622_wsf'}
                b.require('thermal_host_height_m','m','Actual unconditioned host height',positive=True)
            elif host=='garage':
                keys=('ela_volume_coefficient_s_m','stack_height_coefficient_m_s2_K','wind_reference_height_m','wind_height_exponent','wind_coefficient_scale','engine_site_terrain')
                exchange[host]={'model':'source_garage_sherman_grimsrud','exterior_ach50_per_s':c['exterior_ach50_per_s'],**{k:airflow[k] for k in keys}}
                b.require('thermal_host_height_m','m','Actual garage height',positive=True)
                b.require('foundation_top_height_above_grade_m','m','Actual source-equivalent foundation top height above grade')
        if exchange:
            config['air_exchange']=exchange
            b.require('thermal_host_volume_m3','m3','Actual unconditioned host air volume',positive=True)
    ground={'configuration':config,'methods':b.methods,'model_parameters':b.settings,'required_geometry':b.geometry}
    hashes={'native_capture':c['input_sha256']}
    if c['residential']:hashes['host_airflow']=c['airflow_sha256']
    evidence={'id':proof,'source_project':'ResStock' if c['residential'] else 'OpenStudio Standards',
        'source_revision':c['source_revision'],'source_locator':c['source_locator'],'source_file_sha256':hashes,
        'original_value':{'frozen_native_capture':c['source_locator']},'original_unit':'SI native materials/method parameters; original HPXML/IP evidence retained at the pinned locator',
        'transformation':'Retain native ground methods, selected source interfaces and SI material recipes; ordinary unified interfaces use the existing two-mass/one-resistance approximation',
        'extraction_date':DATE,'interpretation_note':'Consumer supplies actual geometry/environment. Raw inventories, source geometry and verification probes remain internal.'}
    if c['residential']:
        evidence['supporting_inputs']={'host_airflow':{'source_locator':AIRFLOW.relative_to(ROOT).as_posix()+'#/records/'+c['capture_id'],
            'sha256':c['airflow_sha256']}}
    return {'components':components,'unified_components':unified,'assemblies':b.assemblies,'unified_assemblies':equivalents,
        'materials':b.materials,'evidence':{proof:evidence},'foundation_ground':ground,'native_exceptions':exceptions}


def compose_foundation_export(base_document,extension,representation):
    doc=copy.deepcopy(base_document);e=extension
    doc['schema_version']='3.0.0' if representation=='detailed' else '2.0.0'
    doc['foundation_ground']=copy.deepcopy(e['foundation_ground'])
    doc['components'].update(copy.deepcopy(e['components'] if representation=='detailed' else e['unified_components']))
    doc['assemblies'].update(copy.deepcopy(e['assemblies']))
    if representation=='unified':doc['assemblies'].update(copy.deepcopy(e['unified_assemblies']))
    used=set(_all_refs(doc['components'],{'assembly_id'}))-{None}
    # A Kiva placement expression may reference another selected native assembly.
    used.update(_all_refs(doc['foundation_ground'],{'assembly_thickness_id'}))
    doc['assemblies']={k:v for k,v in doc['assemblies'].items() if k in used}
    doc.setdefault('materials',{}).update(copy.deepcopy(e['materials']))
    mids=set(_all_refs(doc['assemblies'],{'material_id'}))|set(_all_refs(doc['foundation_ground'],{'material_id','material_thickness_id','soil_material_id'}))
    doc['materials']={k:v for k,v in doc['materials'].items() if k in mids}
    doc.setdefault('evidence',{}).update(copy.deepcopy(e['evidence']))
    if representation=='detailed':
        needed=set()
        for proof in doc['evidence'].values():
            value=proof.get('source_file_sha256',{});needed.update(value.values() if isinstance(value,dict) else [value])
        doc['metadata']['source_files']={k:v for k,v in doc['metadata']['source_files'].items() if v['sha256'] in needed}
        for key,h in next(iter(e['evidence'].values()))['source_file_sha256'].items():
            doc['metadata']['source_files']['atlas-foundation-'+key]={'sha256':h,'source_revision':'foundation-execution/1.0.0'}
    else:doc['provenance']['foundation_ground']={'source_locator':next(iter(e['evidence'].values()))['source_locator'],'source_sha256':next(iter(e['evidence'].values()))['source_file_sha256']}
    validate_foundation_extension(doc)
    return doc


class ExportSession:
    def __init__(self):
        from scripts.construction_distribution import load_current_release
        from scripts import construction_mass_release as mass
        from scripts.construction_mass_accounting import BatchMassValidationCache
        self.mass=mass;self.source=load_current_release();self.mass_release=mass.load_release();self.index=mass.unified_index();self.cache=BatchMassValidationCache()
        self.data=load_json(EXECUTION);self.census=load_json(ROOT/'data/construction-inputs/foundation-source-v1.json')
        self.airflow=load_json(AIRFLOW)['records'];self.geometry={r['id']:r for r in load_json(ROOT/'data/construction-inputs/geometry-v1.json')['residential']}
        self.input_sha=sha(EXECUTION);self.airflow_sha=sha(AIRFLOW);self.extensions={}

    def extension(self,context_id):
        ctx=self.source['contexts'][context_id];suite=self.source['construction_sets'][ctx['construction_set_id']]
        res=suite['scope']=='whole_dwelling';fid=suite['source']['source_fixture_id']
        capture=fid if res else self.data['commercial_context_cases'][ctx['reference_id']+'/'+ctx['climate_zone']]
        key=(suite['id'],capture)
        if key not in self.extensions:
            row=self.data['residential'][capture] if res else self.data['commercial'][capture]
            c={'suite_id':suite['id'],'capture_id':capture,'residential':res,'input_sha256':self.input_sha,
                'configuration_type':self.census['suites'][suite['id']]['effective_configuration'] if res else 'source_native_commercial',
                'absence_reason':'Effective source configuration: '+str(self.census['suites'][suite['id']]['effective_configuration']),
                'source_locator':EXECUTION.relative_to(ROOT).as_posix()+'#/'+('residential/' if res else 'commercial/')+capture,
                'source_revision':row['provenance']['source_receipts']['source_revision']}
            if res:c.update(airflow=self.airflow[fid],airflow_sha256=self.airflow_sha,exterior_ach50_per_s=self.geometry[fid]['fields']['exterior_ach50_per_s']['value'])
            self.extensions[key]=prepare_foundation_extension(c,row,build_foundation_profile(row))
        return self.extensions[key]

    def export_pair(self,context_id):
        base=self.mass.export_pair(context_id,self.source,self.mass_release,index=self.index,cache=self.cache)
        ext=self.extension(context_id)
        return tuple(compose_foundation_export(d,ext,rep) for d,rep in zip(base,('detailed','unified')))


@lru_cache(maxsize=1)
def session():return ExportSession()


def export_pair(context_id):return session().export_pair(context_id)
