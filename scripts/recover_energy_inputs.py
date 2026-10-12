"""Recover independent construction/system inputs; no site or program rebuild.

python -m scripts.recover_energy_inputs [--check]
The outputs are versioned recovery inputs, not published simulation-ready exports.
"""
import argparse
import copy
import hashlib
import subprocess
from pathlib import Path

from scripts.common import ROOT, load_json, dump_json
from scripts.construction_definitions import normalize_material, U_FACTOR, adjust_layers, film_resistance
from scripts.definition_contract import canonical, stable_id
from scripts.definition_release import read_bundle
from scripts.energy_source_recovery import physical_assembly, operand, normalize_hpxml, readiness, ground_target, assembly_u, BTUH_TO_W, GAL_TO_M3
from scripts.fetch import verify_file
from scripts.recover_program_inputs import SOURCE, RUNTIME, REVISION

DATE = '2026-10-12'
BASE = ROOT/'data/definition-releases/v0.1.1'
CONSTRUCTION = ROOT/'data/construction-inputs/source-v1.json'
SYSTEM = ROOT/'data/system-inputs/source-v1.json'
WORK = ROOT/'build/energy-recovery'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def locked_sources():
    sources = {}
    descriptors = {}
    for name in ('definition', 'water', 'completion'):
        for entry in load_json(ROOT/f'sources/{name}-evidence-lock.json')['files']:
            if entry['path'] in descriptors and descriptors[entry['path']]['sha256'] != entry['sha256']:
                raise ValueError('Conflicting source lock: '+entry['path'])
            descriptors[entry['path']] = entry
    for entry in load_json(ROOT/'data/releases/v0.2.0/source_files.json'):
        if entry['path'].endswith('.construction_properties.json'):
            descriptors[entry['path']] = {**entry,'source_revision':entry['version']}
    # Only source blobs used by this recovery are read/verified here.
    for path, entry in descriptors.items():
        if path.endswith(('.constructions.json', '.materials.json', '.prototype_inputs.json','.construction_properties.json')) or path.endswith(('Prototype.hvac_systems.rb', 'Prototype.Model.hvac.rb','Standards.Model.rb')):
            sources[path] = verify_file(entry)
    return sources, {p: descriptors[p] for p in sources}


def proof(path, descriptors, locator, interpretation):
    d = descriptors[path]
    return {'source_project': d['source_id'], 'source_revision': d['source_revision'],
            'source_file_sha256': d['sha256'], 'source_locator': path+'#'+locator,
            'extraction_date': DATE, 'interpretation_note': interpretation}


def residential_execution():
    WORK.mkdir(parents=True, exist_ok=True)
    source_marker = load_json(SOURCE.parent/'.atlas-extraction.json')
    runtime_root = ROOT/'build/runtime/openstudio-windows'
    runtime_marker = load_json(runtime_root/'.atlas-extraction.json')
    if sha(ROOT/'build/runtime/rs.tar.gz') != source_marker['archive_sha256']:
        raise ValueError('Source archive differs from pinned retrieval')
    if sha(RUNTIME) != runtime_marker['files'][RUNTIME.relative_to(runtime_root).as_posix()]:
        raise ValueError('Runtime executable differs from pinned retrieval')
    files = {}
    for path in SOURCE.rglob('*'):
        if path.is_file() and path.suffix in {'.rb', '.tsv', '.csv'}:
            relative = path.relative_to(SOURCE).as_posix()
            actual = sha(path)
            if actual != source_marker['files'].get(SOURCE.name+'/'+relative):
                raise ValueError('Modified source: '+relative)
            files[relative] = {'source_id': 'resstock', 'source_revision': REVISION, 'sha256': actual}
    original = load_json(ROOT/'data/releases/v0.2.0/residential_archetypes.json')
    options = {r['id']: r for r in load_json(ROOT/'data/releases/v0.2.0/residential_options.json')}
    # CFA here is a pinned source default used by heater nominal defaults only.
    # It is never exported as consumer geometry or used to size HVAC equipment.
    previous = load_json(ROOT/'data/program-inputs/residential-v1.json')
    inputs = [{'record_id': r['id'], 'occupants': r['occupants'],
               'bedrooms': int(r['selected_options']['Bedrooms']),
               'source_cfa_ft2': previous['records'][r['id']]['metadata']['source_cfa_ft2'],
               'arguments': {k: v for oid in r['option_ids'] for k,v in options[oid]['arguments'].items()}}
              for r in original]
    dump_json(WORK/'inputs.json', inputs)
    subprocess.run([str(RUNTIME), str(ROOT/'scripts/recover_residential_energy.rb'), str(SOURCE),
                    str(WORK/'inputs.json'), str(WORK/'execution.json')], cwd=ROOT, check=True,
                   timeout=120)
    return load_json(WORK/'execution.json'), files, {
        'source_archive_sha256': source_marker['archive_sha256'],
        'runtime_archive_sha256': runtime_marker['archive_sha256'],
        'runtime_executable_sha256': sha(RUNTIME), 'input_sha256': sha(WORK/'inputs.json'),
        'source_geometry_default_operand': 'data/program-inputs/residential-v1.json#metadata/source_cfa_ft2',
        'source_geometry_default_artifact_sha256': sha(ROOT/'data/program-inputs/residential-v1.json')}


def material_execution(bundle, sources, descriptors):
    path=next(p for p in sources if p.endswith('Standards.Model.rb'))
    text=sources[path].read_text(encoding='utf-8')
    for token in ("data['thermal_absorptance'].to_f", "data['solar_absorptance'].to_f", "data['visible_absorptance'].to_f"):
        if token not in text:
            raise ValueError('Pinned material setter differs')
    pending=[]
    for row in bundle['materials']:
        if row['model'] not in {'StandardOpaqueMaterial','MasslessOpaqueMaterial'}:
            continue
        missing=[p for p in ('thermal_absorptance','solar_absorptance','visible_absorptance') if row.get(p) is None]
        if row['model']=='MasslessOpaqueMaterial' and row.get('roughness') is None:
            missing.append('roughness')
        if missing:
            pending.append({'id':row['id'],'model':row['model'],'missing':missing})
    WORK.mkdir(parents=True,exist_ok=True)
    dump_json(WORK/'material-inputs.json',pending)
    subprocess.run([str(RUNTIME),str(ROOT/'scripts/recover_material_defaults.rb'),
                    str(WORK/'material-inputs.json'),str(WORK/'material-execution.json')],check=True,cwd=ROOT,timeout=30)
    result={}
    for row in load_json(WORK/'material-execution.json'):
        fields={}
        for name,value in row['properties'].items():
            e=proof(path,descriptors,'Standard.model_add_material/'+name,
                    'Execute upstream nil.to_f absorptance setters or the untouched massless roughness constructor default; retain raw null as evidence.')
            p=operand(value,'source runtime default','category' if name=='roughness' else '1',lambda x:x,e,True)
            p['evidence']['original_value']=None
            p['evidence']['original_unit']='source null'
            accepted=row['setter_results'].get(name)
            p['evidence']['source_setter_accepted']=accepted
            p['evidence']['transformation']=('Pinned OpenStudio massless constructor roughness' if name=='roughness' else
                'Ruby nil.to_f -> 0.0; source setter accepted' if accepted else
                'Ruby nil.to_f -> 0.0; source setter rejected; retain pinned SDK constructor default')
            fields[name]=p
        result[row['id']]={'id':row['id'],'fields':fields}
    return result


def option_evidence(expansions, files):
    """Retain all option bindings as evidence; normalize only explicit units."""
    result={}
    for filename,data in expansions.items():
        path='resources/hpxml-measures/BuildResidentialHPXML/resources/options/'+filename
        e=proof(path,files,'option='+str(data['selected_option']),
                'Exact selected TSV option expansion. Native arguments are evidence; only explicit normalized fields are executable operands.')
        e.update(original_value=data['arguments'],original_unit='native source option columns',transformation='Execute pinned get_option_properties; retain exact column/argument names')
        fields={}
        for name,value in data['arguments'].items():
            if name.endswith('_r_value'):
                native,unit,convert='ft2*h*degF/Btu','m2*K/W',lambda x:x/U_FACTOR
            elif name.endswith('_u_factor'):
                native,unit,convert='Btu/h/ft2/degF','W/m2/K',lambda x:x*U_FACTOR
            elif name.endswith(('_shgc','_fraction_operable','_solar_absorptance','_emittance')):
                native,unit,convert='1','1',lambda x:x
            elif name=='enclosure_air_leakage_house_pressure':
                native,unit,convert='Pa','Pa',lambda x:x
            elif name=='enclosure_air_leakage_value' and data['arguments'].get('enclosure_air_leakage_units')=='ACH':
                native,unit,convert='1/h','1/s',lambda x:x/3600
            else:
                continue
            fields[name]=operand(value,native,unit,convert,{**e,'source_locator':e['source_locator']+'/'+name})
        result[filename]={'selected_option':data['selected_option'],'fields':fields,'evidence':e}
    return result


def recover():
    bundle = read_bundle(BASE)
    sources, descriptors = locked_sources()
    execution, residential_files, runtime = residential_execution()
    inputs = {p.relative_to(ROOT).as_posix(): sha(p) for p in [BASE/'manifest.json',
        BASE/'constructions.json', BASE/'hvac_systems.json', BASE/'components.json',
        ROOT/'data/releases/v0.2.0/residential_archetypes.json',
        ROOT/'data/releases/v0.2.0/residential_options.json', ROOT/'sources/definition-policy.json',
        ROOT/'scripts/recover_energy_inputs.py', ROOT/'scripts/energy_source_recovery.py',
        ROOT/'scripts/recover_residential_energy.rb',ROOT/'scripts/recover_material_defaults.rb']}
    header = {'schema_version': '1.0.0', 'extraction_date': DATE, 'input_sha256': inputs,
              'source_files': descriptors, 'residential_source_files': residential_files,
              'runtime': {**runtime, 'version': execution['runtime_version']},
              'boundary': 'Independent source recovery inputs; not a simulation-ready consumer export or a new frozen definition release.'}
    construction = {**copy.deepcopy(header), 'kind': 'construction_recovery', 'records': {},
                    'materials':material_execution(bundle,sources,descriptors)}
    systems = {**copy.deepcopy(header), 'kind': 'system_recovery', 'records': {}, 'water_heaters': {}}
    cp = next(p for p in sources if p.endswith('ashrae_90_1.constructions.json'))
    raw = load_json(sources[cp])['constructions']
    mp = next(p for p in sources if p.endswith('ashrae_90_1.materials.json'))
    materials = load_json(sources[mp])['materials']
    residential = {r['record_id']: r for r in execution['results']}
    evidence={e['id']:e for e in bundle['provenance']}

    for row in bundle['constructions']:
        recovered = {'id': row['id'], 'source_id': row['source_id'],
                     'representation': row.get('representation', 'dwelling_enclosure'),
                     'source_context': {k: row.get(k) for k in ('name','template','climate','source_family','building_type','role')},
                     'recovered': {}, 'unresolved': [], 'required_bindings': list(row.get('required_inputs', []))}
        status = row.get('assembly_status', '')
        if status.startswith('Expected one physical definition'):
            assembly = physical_assembly(raw, row['name'])
            layers = []
            for i, name in enumerate(assembly['materials']):
                if 'simple glazing' in name.lower():
                    props = normalize_material({'name': name})
                    for key in ('u_W_m2_K', 'shgc', 'visible_transmittance'):
                        target = row['parameters'].get(key, {}).get('value')
                        if target is not None:
                            props[key] = target
                else:
                    props = normalize_material(physical_assembly(materials, name))
                layers.append({'order': i, 'properties': props})
            recovered['recovered']['layers'] = layers
            recovered['recovered']['source_candidates'] = assembly['source_candidates']
            recovered['recovered']['evidence'] = proof(cp, descriptors, 'constructions/name='+row['name'],
                'All duplicate selector rows have identical physical recipes; preserve candidates and source order. Generated simple-glazing VT remains a source-code default.')
        elif row['source_id'] in residential:
            expanded = residential[row['source_id']]['expansions']
            recovered['recovered']['source_options'] = option_evidence({k:v for k,v in expanded.items() if k.startswith('enclosure_')},residential_files)
            recovered['unresolved'] = ['assembly_layers_and_thermal_mass', 'geometry_dependent_enclosure_translation']
            recovered['required_bindings'] = ['geometry', 'ground_boundary', 'weather', 'pressure_to_natural_infiltration_model']
        elif row.get('representation') == 'package':
            recovered['required_bindings'] += ['construction_selection_by_climate_and_role']
        elif status.startswith('unresolved') or not row.get('layers'):
            recovered['unresolved'] = ['source_assembly']
        if row.get('ground_model')=='C-factor underground wall' and row['parameters']['c_W_m2_K']['value'] is None:
            pe=evidence[row['evidence_ids'][0]]
            attr=pe['original_value']
            target=ground_target(attr)
            if target['model']=='layered_U_ground_construction':
                locations=[(p,i) for p in sorted(sources) if p.endswith('.construction_properties.json')
                           for i,v in enumerate(load_json(sources[p])['construction_properties']) if v==attr]
                if not locations:
                    raise ValueError('Ground target source locator unresolved')
                if len({descriptors[p]['source_revision'] for p,_ in locations})!=1:
                    raise ValueError('Ground target crosses source revisions')
                source_path,index=locations[0]
                e=proof(source_path,descriptors,f'construction_properties/{index}/{target["source_field"]}',
                        'Source specifies a U target, not C-factor. Apply source film convention and insulation adjustment; ground boundary/geometry remains consumer input.')
                e['supporting_source_locators']=[f'{p}#/construction_properties/{i}' for p,i in locations]
                recovered['recovered']['ground_model']=target['model']
                recovered['recovered']['parameters']={target['field']:operand(attr[target['source_field']],
                    'Btu/h/ft2/degF','W/m2/K',lambda x:x*U_FACTOR,e)}
                assembly=physical_assembly(raw,row['name'])
                films=film_resistance(row['role'],attr.get('u_value_includes_interior_film_coefficient',True),
                                       attr.get('u_value_includes_exterior_film_coefficient',True))
                layers,adjustment=adjust_layers([l['properties'] for l in row['layers']],target['value'],assembly.get('insulation_layer'),films)
                recovered['recovered']['layers']=[{'order':i,'properties':p} for i,p in enumerate(layers)]
                recovered['recovered']['target_adjustment']={'status':adjustment,'target_u_W_m2_K':target['value'],
                    'films_m2_K_W':films,'evidence':e}
                p=recovered['recovered']['parameters']['u_W_m2_K']
                p['value']=assembly_u(layers,films)
                p['status']='known' if p['value'] is not None else 'unknown'
                p['origin']='source_calculation'
                p['evidence']['transformation']='IP target * 5.678263337; source film/insulation adjustment; U = 1/(sum layer R + source films). A zero source target removes insulation and is not zero physical U.'
                if p['value'] is None:
                    recovered['unresolved'].append('ground_U_resistance')
                recovered['required_bindings']=['geometry','ground_boundary_condition']
                if adjustment.startswith('unresolved'):
                    recovered['unresolved'].append('ground_U_layer_adjustment')
            else:
                recovered['unresolved'].append('ground_factor_target')
        recovered['required_bindings'] = sorted(set(recovered['required_bindings']))
        recovered['readiness'] = readiness(recovered)
        construction['records'][row['id']] = recovered

    for row in bundle['hvac_systems']:
        recovered = {'id': row['id'], 'source_id': row['source_id'],
                     'source_context': {k:row.get(k) for k in ('name','template','climate','source_family','building_type','system_type')},
                     'recovered': {}, 'unresolved': ['source_component_recipe', 'performance_assignment', 'controls_and_curves'],
                     'required_bindings': ['serving_assignment', 'consumer_sizing']}
        if row['source_id'] in residential:
            result = residential[row['source_id']]
            components = []
            for item in result['equipment']:
                role = item['role']
                method = item['producing_method']
                if method not in result['executed_methods']:
                    raise ValueError('Unexecuted equipment producer: '+method)
                path = 'resources/hpxml-measures/BuildResidentialHPXML/measure.rb'
                e = proof(path, residential_files, method,
                          'Executed selected source options. Heater/solar defaults and loss calculations use pinned Defaults/Waterheater routines; no HVAC sizing or simulation.')
                e['supporting_source_locators'] = [p+'#'+m for p,m in [
                    ('resources/hpxml-measures/HPXMLtoOpenStudio/resources/defaults.rb','Defaults.apply_water_heaters; Defaults.apply_solar_thermal_systems'),
                    ('resources/hpxml-measures/HPXMLtoOpenStudio/resources/waterheater.rb','Waterheater.disaggregate_tank_losses_and_burner_efficiency')]]
                if role in {'water_heater','solar_thermal'}:
                    dp='resources/hpxml-measures/HPXMLtoOpenStudio/resources/defaults.rb'
                    wp='resources/hpxml-measures/HPXMLtoOpenStudio/resources/waterheater.rb'
                    e['default_evidence']=proof(dp,residential_files,
                        'Defaults.apply_water_heaters' if role=='water_heater' else 'Defaults.apply_solar_thermal_systems',
                        'Executed source defaults with selected fuel, bedroom/occupant counts and source fixture context; not an Atlas fallback.')
                    e['field_evidence']={}
                    for field,method in [('actual_tank_volume','Waterheater.calc_storage_tank_actual_vol'),
                            ('tank_loss_coefficient','Waterheater.disaggregate_tank_losses_and_burner_efficiency'),
                            ('heating_input_conversion_efficiency','Waterheater.disaggregate_tank_losses_and_burner_efficiency')]:
                        e['field_evidence'][field]=proof(wp,residential_files,method,
                            'Executed source heater loss/conversion calculation. Solar is a separate record; pre-solar tank losses must be adjusted exactly once downstream.')
                    e['field_evidence']['cop']=proof(dp,residential_files,'Defaults.get_water_heater_heat_pump_cop',
                        'Source HPWH COP calibration; does not supply translated compressor/fan curves or controls.')
                component = normalize_hpxml(item['values'], role, e)
                component['id'] = stable_id('recovered-equipment', {'source':row['source_id'], 'role':role, 'native_id':item['values']['id']})
                if role in {'water_heater','solar_thermal'}:
                    systems['water_heaters'][component['id']] = {**component, 'source_id': row['source_id'],
                        'source_context': recovered['source_context'], 'unresolved': ['engine_controls_and_performance_translation'],
                        'readiness':'blocked'}
                else:
                    components.append(component)
            recovered['recovered'] = {'equipment':components, 'selected_option_expansions': {
                **option_evidence({k:v for k,v in result['expansions'].items() if k.startswith(('hvac_','ventilation_'))},residential_files)},
                'executed_methods':result['executed_methods']}
            recovered['unresolved'] = ['performance_curves_and_fan_defaults', 'distribution_and_control_translation'] if components else []
            recovered['equipment_status'] = 'selected_source_equipment' if components else 'explicit_source_no_hvac_equipment'
        else:
            recovered['recovered']['source_descriptor'] = copy.deepcopy(row['source_descriptor'])
            # The MediumOffice caller does not pass heating_type into PVAV, and
            # skips creating a hot-water loop. Preserve the actual gas/DX recipe,
            # rather than importing unrelated vav_* fan fields from prototype input.
            if row.get('building_type') == 'MediumOffice' and row['system_type'] == 'PVAV':
                path = next(p for p in sources if p.endswith('Prototype.hvac_systems.rb'))
                caller = next(p for p in sources if p.endswith('Prototype.Model.hvac.rb'))
                text = sources[path].read_text(encoding='utf-8')
                caller_text = sources[caller].read_text(encoding='utf-8')
                for token in ("'VAV_default'", 'create_coil_cooling_dx_two_speed', 'create_coil_heating_gas', 'AirTerminalSingleDuctVAVReheat', "'ZoneSum'"):
                    if token not in text:
                        raise ValueError('Pinned PVAV recipe differs: '+token)
                if "building_type == 'MediumOffice'" not in caller_text:
                    raise ValueError('Pinned PVAV caller differs')
                recovered['recovered']['source_recipe'] = {
                    'fan_factory': 'create_typical_fan(VAV_default)', 'main_heat_factory':'create_coil_heating_gas',
                    'cooling_factory':'create_coil_cooling_dx_two_speed(OS default)',
                    'terminal_factory':'AirTerminalSingleDuctVAVReheat/electric_reheat',
                    'outdoor_air_method':'ZoneSum', 'night_cycle_control':'CycleOnAny',
                    'evidence':[proof(path,descriptors,'Standard.model_add_pvav', 'Source factory recipe; helper performance and later template adjustments remain unresolved.'),
                                proof(caller,descriptors,'Standard.model_add_hvac/PVAV','MediumOffice skips hot-water-loop creation; caller does not forward heating_type.')]}
                recovered['unresolved'] = ['factory_performance_and_template_adjustments', 'performance_curve_assignment']
        recovered['readiness'] = readiness(recovered)
        systems['records'][row['id']] = recovered

    # Each source prototype equipment selection stays a distinct family/template
    # record. Demand services are not instantiated or embedded as program loads.
    for path in sorted(sources):
        if not path.endswith('.prototype_inputs.json'):
            continue
        for index, row in enumerate(load_json(sources[path])['prototype_inputs']):
            for channel in ('main','laundry','booster'):
                if row.get(channel+'_water_heater_volume') is None and row.get(channel+'_water_heater_capacity') is None:
                    continue
                fields = {}
                for suffix, native, unit, convert in [
                    ('water_heater_volume','US gal','m3',lambda x:x*GAL_TO_M3),
                    ('water_heater_capacity','Btu/h','W',lambda x:x*BTUH_TO_W),
                    ('water_heater_fuel','source fuel','category',lambda x:x),
                    ('service_water_temperature','degF','degC',lambda x:(x-32)*5/9),
                    ('service_water_pump_head','Pa','Pa',lambda x:x),
                    ('service_water_pump_motor_efficiency','1','1',lambda x:x),
                    ('service_water_parasitic_fuel_consumption_rate','Btu/h','W',lambda x:x*BTUH_TO_W),
                    ('off_cycle_parasitic_heat_fraction_to_tank','1','1',lambda x:x),
                    ('water_heater_space_name','source host name','category',lambda x:x)]:
                    field = channel+'_'+suffix
                    if field not in row:
                        continue
                    e = proof(path, descriptors, f'prototype_inputs/{index}/{field}',
                              'Prototype nominal equipment input, not geometry-independent sizing or executed heater efficiency. Host names require consumer assignment.')
                    fields[suffix] = operand(row[field],native,unit,convert,e)
                identity = stable_id('source-water-heater',{'path':path,'index':index,'channel':channel})
                systems['water_heaters'][identity] = {'id':identity, 'role':'water_heater', 'fields':fields,
                    'source_context':{k:row.get(k) for k in ('template','building_type')}, 'source_channel':channel,
                    'unresolved':['heater_efficiency_and_loss_model','source_factory_template_adjustments'],
                    'required_bindings':['water_demand_assignment','loss_host','water_mains_temperature','consumer_sizing'],
                    'readiness':'blocked'}
    return construction, systems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Reexecute and compare exact canonical artifacts')
    args = parser.parse_args()
    outputs = recover()
    for path, value in zip((CONSTRUCTION,SYSTEM),outputs):
        if args.check:
            if load_json(path) != value:
                raise ValueError('Recovery is not reproducible: '+str(path))
        else:
            dump_json(path,value)
    print(f"Verified {len(outputs[0]['records'])} construction dispositions, {len(outputs[1]['records'])} HVAC dispositions and {len(outputs[1]['water_heaters'])} DHW/solar source records")


if __name__ == '__main__':
    main()
