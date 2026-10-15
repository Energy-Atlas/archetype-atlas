"""Build the exact M1 resource set from locked evidence and frozen references."""
import argparse
import copy
import hashlib
import math
from pathlib import Path
import re
import tempfile
import tarfile
from urllib.parse import quote

from atlas_schedules.canonical import canonical
from atlas_schedules.errors import GeneratorError
from atlas_schedules.resources import ResourceSet, strict_json, write_resources
from atlas_schedules.budgets import reference_budget
from atlas_schedules.calendar import evaluate_rules
from scripts.common import ROOT
from scripts.schedule_generator_sources import extract_sources
from scripts.schedule_generator_reference import load_reference_vectors
from scripts.definition_release import read_bundle
from scripts.program_json_v3 import ProgramExporter
from scripts.definition_contract import stable_id
from scripts.schedule_generator_apartment_water import compile_apartment_water_requirement


def _read(path):
    return strict_json(Path(path).read_bytes(), str(path))


def compile_exact_authority_resources(records: dict, source_records: dict) -> dict:
    """Opt-in source preparation; never enable a native context or default scope.

    Existing recipe C5 inventory is independent and retained in full. The locked
    requirement resource and per-programme recipe inventory must agree; caller
    links and generated owners do not participate in this compilation.
    """
    from scripts.schedule_generator_physical_sets import compile_exact_inventory, compile_exact_requirements
    from atlas_schedules.physical_sets import _no_double_listing, _programme_requirement
    inventory = compile_exact_inventory(source_records)
    requirements = compile_exact_requirements(source_records, inventory)
    iid = inventory['payload']['inventory_id']
    inventory_key = 'physical-fixture-inventory__'+iid
    requirements_key = 'physical-fixture-requirements__'+iid
    reference = {'inventory_id': iid, 'inventory_sha256': inventory['inventory_sha256'],
                 'requirements_key': requirements_key, 'qualification_key': 'physical-fixture-qualification__'+iid}
    additions = {('reference', inventory_key): inventory, ('reference', requirements_key): requirements}
    changes = {}
    for programme in source_records['programmes']:
        pid = programme['value']['id']; key = ('program', pid)
        if key not in records or not isinstance(records[key].get('recipe'), dict):
            raise GeneratorError('requires_binding', '/program/'+pid, 'Existing independently compiled programme recipe is required')
        record = copy.deepcopy(records[key]); recipe = record['recipe']
        if not isinstance(recipe.get('required_service_links'), list):
            raise GeneratorError('source_integrity', '/required_service_links', 'Independent complete C5 inventory must be retained')
        own = [r for r in requirements if _programme_requirement(r)['value']['id'] == pid]
        _no_double_listing(recipe['required_service_links'], own)
        for field, value in (('required_service_sets', own), ('exact_source_authority', reference)):
            if field in recipe and canonical(recipe[field]) != canonical(value):
                raise GeneratorError('source_integrity', '/recipe/'+field, 'Existing independent source authority differs')
            recipe[field] = copy.deepcopy(value)
        methods = [m for m in source_records['method_references'] if m['value']['program_id'] == pid]
        if methods:
            if 'original_method_reference' in recipe and canonical(recipe['original_method_reference']) != canonical(methods[0]):
                raise GeneratorError('source_integrity', '/recipe/original_method_reference', 'Existing original method authority differs')
            recipe['original_method_reference'] = copy.deepcopy(methods[0])
        changes[key] = record
    for key, value in additions.items():
        if key in records and canonical(records[key]) != canonical(value):
            raise GeneratorError('source_integrity', '/reference/'+key[1], 'Immutable compiled authority resource already differs')
    records.update(additions); records.update(changes)
    return copy.deepcopy(reference)


def validate_scope(scope: dict, lock: dict | None = None) -> None:
    lock = lock if lock is not None else _read(ROOT/'sources/schedule-generator-lock.json')
    if scope.get('calendar') != lock['calendar'] or scope.get('cases') != lock['scope_cases']:
        raise GeneratorError('scope_mismatch', '/cases', 'M1 case/configuration/weather/template bindings differ from locked scope')
    for case in scope['cases']:
        for receipt in (case['program_definition'], case['configuration']):
            if 'file' in receipt:
                content = (ROOT/receipt['file']).read_bytes()
                if hashlib.sha256(content).hexdigest() != receipt['sha256']:
                    raise GeneratorError('source_integrity', receipt['file'], 'Frozen reference changed')
        program = _read(ROOT/case['program_definition']['file'])[int(case['program_definition']['json_pointer'][1:])]
        if any(program.get(field) != case.get(field) for field in ('id', 'template', 'evidence_view') if field != 'id') or program['id'] != case['program_id']:
            raise GeneratorError('scope_mismatch', case['case_id'], 'Case does not match frozen program identity')


def validate_sampling_audit(audit: dict) -> None:
    lock = _read(ROOT/'sources/schedule-generator-lock.json')
    actual = hashlib.sha256(canonical(audit)).hexdigest()
    expected = hashlib.sha256(canonical(_read(ROOT/'data/schedule-generator/comstock-sampling-audit.json'))).hexdigest()
    disk = hashlib.sha256((ROOT/'data/schedule-generator/comstock-sampling-audit.json').read_bytes()).hexdigest()
    parameters = audit.get('parameters', [])
    if (actual != expected or disk != lock['sampling_audit_sha256'] or audit.get('gate_status') != 'passed'
            or audit.get('conditioning_inputs') != {'building_type': 'medium_office'}
            or audit.get('population_realization_equivalent') is not False
            or not audit.get('weather_independent') or len(parameters) != 10
            or any(p.get('decision') != 'resolved' for p in parameters)):
        raise GeneratorError('sampling_gate', '/commercial', 'Commercial source/conditioning gate is unresolved or differs from approved audit')


def _portable(value):
    """Remove upstream execution-cache paths; source-relative locators stay intact."""
    if isinstance(value, dict):
        return {k: _portable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_portable(v) for v in value]
    if isinstance(value, str) and (re.match(r'^[A-Za-z]:[\\/]', value) or value.startswith(('/kfs', '/tmp/', '/home/'))):
        return None
    return value


def _receipt(file, pointer, note):
    content = (ROOT/file).read_bytes()
    return {'source_path': file, 'source_locator': file+'#'+pointer,
            'source_revision': 'frozen '+file.split('/')[2], 'source_sha256': hashlib.sha256(content).hexdigest(),
            'original_unit': 'versioned JSON with per-field units/evidence', 'original_value': 'value retained in record',
            'transformation': note, 'extraction_date': '2026-10-14',
            'interpretation_note': 'Immutable source/reviewed views remain separate; null remains unknown'}


def event_constants(record):
    """Compile literal source constants without executing Ruby; retain each line."""
    fields = {}
    for line, text in enumerate(record['text'].splitlines(), 1):
        match = re.fullmatch(r"\s+(\w+) = (.+)", text)
        if match is None:
            continue
        key, original = match.groups()
        value = ([float(v) for v in original.strip("'").split(',')]
                 if original.startswith("'") else float(original))
        if 'FlowRate' in key:
            original_unit, si_unit, factor = 'US gal/min', 'm3/s', 0.003785411784/60
        elif 'DurationMean' in key or 'DurationStd' in key or 'MinutesBetweenEventGap' in key:
            original_unit, si_unit, factor = 'min', 's', 60
        else:
            original_unit, si_unit, factor = '1', '1', 1
        si_value = [v*factor for v in value] if isinstance(value,list) else value*factor
        fields[key] = {'value': value, 'unit': original_unit, 'si_value': si_value, 'si_unit': si_unit,
            'provenance': dict(record['provenance'],
            field_locator=f'constants.rb:{line}#{key}', original_value=original,
            original_unit=original_unit,
            transformation=f'Parse source literals; retain original calibration units; SI counterpart multiply by {factor!r}')}
    return {'schema_version': '1.0.0', 'fields': fields, 'provenance': record['provenance']}


def compile_recipes(records, scope):
    """Compile exact M1 physical demands; index every other ID without expansion."""
    bundle = read_bundle(ROOT/'data/definition-releases/v0.1.1')
    exporter = ProgramExporter(bundle)
    recovery_file = 'data/program-inputs/residential-v1.json'
    recovery = _read(ROOT/recovery_file)
    # Source methods are compiled as inspected code evidence, never executed.
    methods = {}
    with tarfile.open(ROOT/'data/raw/resstock/rs.tar.gz') as archive:
        for file, names in {
            'measures/ResStockArguments/measure.rb': ['modify_setpoint_schedule'],
            'resources/hpxml-measures/HPXMLtoOpenStudio/resources/hvac.rb': ['apply_setpoints', 'get_hvac_setpoints'],
        }.items():
            member = next(m for m in archive.getmembers() if m.name.endswith('/'+file))
            content = archive.extractfile(member).read()
            digest = hashlib.sha256(content).hexdigest()
            if digest != recovery['source_files'][file]:
                raise GeneratorError('source_integrity', file, 'Thermostat source differs from locked recovered evidence')
            text = content.decode('utf-8')
            for name in names:
                marker = ('  def ' if name == 'modify_setpoint_schedule' else '  def self.')+name
                start = text.index(marker)
                end = text.find('\n  def ', start+len(marker))
                methods[name] = {'text': text[start:end], 'provenance': {
                    'source_path': file, 'source_locator': file+'#'+name,
                    'source_line': text[:start].count('\n')+1, 'source_revision': recovery['source_revision'],
                    'source_file_sha256': digest, 'source_archive_sha256': recovery['source_archive_sha256'],
                    'original_value': 'verbatim method body', 'original_unit': 'F/C and source arrays',
                    'transformation': 'Compile selected nominal full-year Python translation; retain native correction evidence',
                    'extraction_date': '2026-10-14', 'interpretation_note': 'No equipment unavailability, deadband or fan offset selected in source reference variant'}}
    records['residential', 'thermostat-methods'] = {'schema_version': '1.0.0', 'methods': methods}
    evidence = {r['id']: r for r in bundle['provenance']}
    files = {r['id']: r for r in bundle['source_files']}
    schedules = {r['id']: r for r in bundle['schedules']}
    definitions = {r['id']: r for r in bundle['programs']}
    policies = {'schema_version': '1.0.0', 'programs': []}
    statuses = {}

    def field_evidence(identifier, fallback):
        result = copy.deepcopy(evidence.get(identifier, fallback))
        source = files.get(result.get('source_file_id'))
        if source:
            result['source_file'] = copy.deepcopy(source)
        return result

    def source_schedule(sid, ready):
        # Actual frozen source objects are kept for Standards native transforms.
        if sid in schedules:
            return copy.deepcopy(schedules[sid])
        out = copy.deepcopy(ready['schedules'][sid])
        if out['type'] == 'ruleset':
            out['time_resolution_minutes'] = out.pop('timestep_minutes')
        return out

    for case in scope['cases']:
        pid = case['program_id']
        record = records['program', pid]
        definition = definitions[pid]
        ready = exporter.export(pid, 'defaulted')
        residential = definition.get('scope') == 'whole_dwelling'
        receipt = record['provenance']
        accepted_absence = bool(not ready['loads'] and not ready['shared_services'] and
                                ready['metadata']['absent_demands'] and ready['controls']['conditioning_state'] == 'unconditioned')
        if not ready['loads'] and not accepted_absence:
            raise GeneratorError('unsupported_binding', pid, 'No source-backed active or accepted-inactive recipe')
        slots, demands, controls, companions, sources = [], [], [], {}, {}
        resolved = {'schema_version': '1.0.0', 'program_id': pid, 'recipe_id': 'recipe-'+pid,
                    'source_family': definition['source_family'], 'source': {k: case.get(k) for k in
                    ('building_type', 'template', 'vintage', 'evidence_view', 'climate', 'weather')},
                    'inputs': {}, 'slots': slots, 'demands': demands, 'controls': controls,
                    'shared_services': copy.deepcopy(ready['shared_services']),
                    'evidence': [{'definition': receipt, 'accepted_absence': accepted_absence,
                                 'configuration': record.get('configuration_provenance', case['configuration']),
                                 'ready_policy': ready['default_policy_id'], 'absent_demands': ready['metadata']['absent_demands'],
                                 'resolutions': ready['metadata']['resolutions'],
                                 'aggregation': {k: v for k, v in ready['metadata']['aggregation'].items() if k != 'component_schedules'},
                                 'aggregation_component_schedule_ids': list(ready['metadata']['aggregation'].get('component_schedules', {}))}]}
        resolved['source']['source_id'] = definition['source_id']
        if definition.get('composition_id') is not None:
            composition=records['composition',definition['composition_id']]
            allocation={'parent_program_id':pid,'composition_id':definition['composition_id']}
            composition['source_allocation']=copy.deepcopy(allocation)
            allocation.update(definition=copy.deepcopy(composition['definition']),provenance=copy.deepcopy(composition['provenance']))
            bound={'configuration_id':case['configuration']['sampling_configuration_id'],
                   'carrier_policy':'explicit_single_nonresidential_reference_carrier'}
            record['recipe']={'schema_version':'1.0.0','resolved':resolved,'bound_inputs':bound,
                'variable_inputs':{'composition_basis_mode':['source_reference_area_normalized','caller_parent_floor_area'],
                                  'composition_id':[definition['composition_id']]},
                'required_inputs':['year',*bound,'composition_basis_mode'],'reference_year':scope['calendar']['year'],
                'calendar_year_locked':True,'reference_sources':{},'companion_rules':{},'source_context':{},
                'source_composition':allocation,'aggregate_binding_policy':'actual_original_member_targets_before_rng'}
            # Source parent legacy profiles remain only in its immutable definition.
            statuses[pid]='compiled'
            policies['programs'].append({k:record['recipe'][k] for k in ('schema_version','bound_inputs','required_inputs',
                'reference_year','calendar_year_locked','aggregate_binding_policy','variable_inputs')} | {
                'program_id':pid,'status':'compiled','source_composition':allocation,'source':resolved['source'],
                'slots':slots,'demands':demands,'controls':controls,'shared_services':resolved['shared_services'],'evidence':resolved['evidence']})
            continue

        def add_slot(slot, sid, unit, kind):
            if any(s['slot'] == slot for s in slots):
                return
            slots.append({'slot': slot, 'source_schedule_id': sid, 'unit': unit, 'kind': kind})

        def add_control(slot, sid, unit, quantity, ev):
            add_slot(slot, sid, unit, 'control')
            controls.append({'slot': slot, 'quantity': quantity, 'unit': unit, 'evidence': copy.deepcopy(ev)})

        bound = {}
        context = {'method': 'resstock_time_allocation_with_selected_source_companions' if residential else
                   'atlas_frozen_definition_comstock_v33_standards086_hybrid',
                   'case_id': case['case_id'], 'configuration_id': case['configuration_id']}
        if residential:
            recovered = recovery['records'].get(case['configuration_id'])
            if recovered is None or recovered['unresolved']:
                raise GeneratorError('unsupported_binding', pid, 'Missing source-backed appliance decomposition')
            # Package original recovered fields plus their source checksum/locator.
            records['residential', case['configuration_id']+'-original-inputs'] = {
                'definition': copy.deepcopy(recovered), 'provenance': _receipt(recovery_file,
                '/records/'+case['configuration_id'], 'Original annual evidence before profile fitting; preserve original units'),
                'source_revision': recovery['source_revision'], 'source_archive_sha256': recovery['source_archive_sha256'],
                'source_files': recovery['source_files']}
            metadata = record['configuration']
            args = metadata['arguments']
            installed = {slot: args[key] != 'None' for slot, key in
                [('dishwasher', 'appliance_dishwasher'), ('clothes_washer', 'appliance_clothes_washer'),
                 ('clothes_dryer', 'appliance_clothes_dryer'), ('cooking_range', 'appliance_cooking_range_oven'),
                 ('ceiling_fan', 'ceiling_fans')]}
            installed.update(plug_loads_other=float(args['misc_plug_loads_other_usage_multiplier']) > 0,
                             plug_loads_tv=float(args['misc_plug_loads_television_usage_multiplier']) > 0,
                             garage=metadata['selected_options']['Geometry Garage'] != 'None')
            bound = {k: metadata[k] for k in ('bedrooms', 'state', 'latitude', 'longitude', 'time_zone_utc_offset')}
            bound.update(residents=metadata['occupants'], installed=installed,
                         weather_id=case['weather']['station_filename'].removesuffix('.epw'),
                         thermostat_arguments={k: v for k, v in args.items() if k.startswith('hvac_control_')})
            original_receipt = records['residential', case['configuration_id']+'-original-inputs']['provenance']
            context['original_inputs_resource'] = case['configuration_id']+'-original-inputs'
            context['reference_clock'] = {'TZ': 'UTC', 'variant': 'controlled_no_DST_local_standard_calendar'}
            context['thermostat_methods_resource'] = 'thermostat-methods'
            # Recovered original physical records precede the v3 sum-of-power DTO.
            for original in recovered['loads']:
                ev = dict(copy.deepcopy(original['evidence']), recovered_artifact=original_receipt)
                raw = ev['original_value']
                if 'annual_kwh' in raw:
                    total, annual_unit = raw['annual_kwh']*1000, 'Wh/dwelling'
                    transformation = 'original annual_kwh * 1000; no reference-profile or fitted-W integration'
                    unit = 'W/dwelling'
                elif 'daily_gallons' in raw:
                    total, annual_unit = raw['daily_gallons']*365*0.003785411784, 'm3/dwelling'
                    transformation = 'original daily_gallons * 365 days * 0.003785411784 m3/USgal'
                    unit = 'm3/s/dwelling'
                else:
                    raise GeneratorError('unsupported_binding', pid, 'Unknown original annual operand')
                if total == 0:
                    resolved['evidence'][0].setdefault('recovered_zero_targets', []).append(copy.deepcopy(original))
                    continue
                slot, sid = original['end_use'], original.get('schedule_id')
                if sid is None:
                    raise GeneratorError('unsupported_binding', pid+'/'+slot, 'Missing actual selected schedule')
                # Same slot can bind electricity and gas, retaining distinct demands.
                add_slot(slot, sid, 'fraction', 'load')
                host = 'assigned_zone' if original['host'] == 'conditioned space' else original['host']
                demand = {'demand_id': original.get('demand_id') or stable_id('recovered-demand', {'program': pid, 'end_use': slot,
                          'fuel': original.get('fuel'), 'host': host}), 'slot': slot,
                          'quantity': slot, 'value': original['value'], 'unit': unit,
                          'basis': original['basis'], 'fuel': original.get('fuel', 'water'),
                          'host': host,
                          'evidence': ev, 'annual_target': {'total': total, 'unit': annual_unit,
                          'evidence': dict(ev, annual_target_transformation=transformation)}}
                demands.append(demand)
                if slot in records['residential', 'fixed-background-schedules']['definition']['schedules']:
                    fixed = records['residential', 'fixed-background-schedules']['definition']
                    companions[slot] = {'method': 'fixed_background', 'variant': fixed['variant'], 'source_slot': slot,
                                        'evidence': {'selected_definition': ev, 'shape': fixed['schedules'][slot]['evidence']}}
                elif slot not in {'clothes_washer', 'hot_water_clothes_washer', 'dishwasher', 'hot_water_dishwasher',
                                   'clothes_dryer', 'cooking_range', 'plug_loads_other', 'plug_loads_tv',
                                   'lighting_interior', 'lighting_garage', 'ceiling_fan', 'hot_water_fixtures'}:
                    raise GeneratorError('unsupported_binding', pid+'/'+slot, 'No applicable source kernel for physical demand')
                if 'target_temperature_degC' in original:
                    target_slot = slot+'_target_temperature'
                    target = original['target_temperature_degC']
                    target_sid = stable_id('source-water-target', {'source': pid, 'end_use': slot, 'target': target})
                    add_control(target_slot, target_sid, 'C', 'temperature', ev)
                    companions[target_slot] = {'method': 'constant', 'value': target, 'evidence': ev}
            # The source zero-occupant skip has an explicit adapter occupancy channel.
            sid = next((l['schedule_id'] for l in definition['loads'] if l['quantity'] == 'occupancy'), None)
            if sid is None:
                raise GeneratorError('unsupported_binding', pid, 'No source occupancy reference')
            add_slot('occupants', sid, 'fraction', 'resident_count')
            controls.append({'slot': 'occupants', 'quantity': 'occupancy_fraction', 'unit': 'fraction',
                             'evidence': {'definition': receipt, 'residents': metadata['occupants'],
                                          'zero_skip_adapter': metadata['occupants'] == 0}})
            if metadata['occupants'] > 0:
                activity = recovered['controls']['activity_W_person']
                activity_sid = ready['controls']['activity_schedule_id']
                ev = recovered['metadata']['controls_evidence']
                add_control('activity', activity_sid, 'W/person', 'activity', ev)
                companions['activity'] = {'method': 'constant', 'value': activity, 'evidence': ev}
            thermostat_evidence = {'source_revision': recovery['source_revision'],
                'source_locators': [metadata['provenance']['thermostat_locator']],
                'source_file_sha256': {k: recovery['source_files'][k] for k in
                    ('measures/ResStockArguments/measure.rb', 'resources/hpxml-measures/HPXMLtoOpenStudio/resources/hvac.rb')},
                'original_value': bound['thermostat_arguments'], 'original_unit': 'F and dimensionless offset directions',
                'transformation': 'base + offset*direction; F to C; equal-season overlap midpoint',
                'extraction_date': '2026-10-14', 'interpretation_note': 'Selected nominal full-year source variant; no unavailability overlay'}
            for mode in ('heating', 'cooling'):
                slot = mode+'_setpoint'
                add_control(slot, ready['controls'][slot+'_schedule_id'], 'C', 'temperature', thermostat_evidence)
                companions[slot] = {'method': 'translated_thermostat', 'evidence': thermostat_evidence}
        else:
            restaurant=case['building_type'] in {'FullServiceRestaurant','QuickServiceRestaurant'}
            retail=case['building_type']=='RetailStandalone'
            if retail:
                from scripts.schedule_generator_retail import program_source_context
                bound,context=program_source_context(case)
                resolved['shared_services']=[]
                links=[]
            elif restaurant:
                from scripts.schedule_generator_restaurants import program_source_context
                bound,context=program_source_context(case)
                resolved['shared_services']=[]
                links=[{'source_service_id':load['service_id'],'source_channel':'hot_water_volume','required':True,
                        'original_demand':copy.deepcopy(load),'evidence':field_evidence(load['evidence_id'],receipt)}
                       for load in definition['loads'] if load.get('service_id') and load['status']=='known']
                if {link['source_service_id'] for link in links}!=set(definition['service_ids']):
                    raise GeneratorError('source_integrity',pid,'Exact active programme/service alias set differs')
            else:
                bound = {'configuration_id': case['configuration']['sampling_configuration_id'],
                         'carrier_policy': 'explicit_single_nonresidential_reference_carrier'}
                carrier_case = next(c for c in scope['cases'] if c['building_type'] == case['building_type']
                                    and 'Office_'+case['building_type'] in c['name'] and c['evidence_view'] == case['evidence_view']
                                    and c['template'] == case['template'])
                carrier = definitions[carrier_case['program_id']]
                carrier_load = next(l for l in carrier['loads'] if l['quantity'] == 'occupancy')
                carrier_source = schedules[carrier_load['schedule_id']]
                context.update(configuration_id=bound['configuration_id'], standards_version='0.8.6', steps_per_hour=6,
                    slot_sources={}, slot_modes={}, occupancy_aggregation={'policy': bound['carrier_policy'],
                    'constituents': [{'schedule': carrier_source, 'nominal_people': 1.0, 'residential': False,
                                      'evidence': field_evidence(carrier_load['evidence_id'], receipt)}],
                    'interpretation': ('Declared M1 normalized Office carrier, not geometry or population; Plenum explicitly associated through named MediumOffice configuration' if case['building_type']=='MediumOffice' else
                        'Explicit normalized actual SmallOffice carrier in the same template/view; source-inactive Attic associated with the named SmallOffice configuration; no geometry or population inferred' if case['building_type']=='SmallOffice' else
                        'Exact same-template/view WarehouseOffice normalized carrier; zero local People in Fine/Bulk retained; actual room methods, no inferred geometry or population')},
                    occupancy_adjustment={'peak_occ_frac': 0.231, 'source_key': 'comstock__resources__options_lookup_tsv',
                    'source_options': ['baseline_hvac_sizing=autosize', 'baseline_hvac_sizing=hardsize'],
                    'interpretation': 'Locked common lookup value only; no HVAC sizing inference'},
                    source_clock={'TZ': 'UTC', 'variant': 'controlled_no_DST_local_standard_calendar'},
                    carrier_program_id=carrier_case['program_id'], configuration_association=case['configuration'])
            if scope['milestone_id'] != 'M1':
                context['source_discard_method_evidence'] = {slot:records['reference',key]['provenance'] for slot,key in {
                    'lighting':'comstock__resources__measures__set_interior_lighting_bpr__measure_rb',
                    'electric_equipment':'comstock__resources__measures__set_electric_equipment_bpr__measure_rb'}.items()}
                context['source_rounding_method_evidence'] = records['reference','ruby-float-numeric-c']['provenance']
                context['adaptation'] = {'method':'prototype_budget_preserving_commercial_hybrid',
                    'source_template':case['template'], 'evidence_view':case['evidence_view'],
                    'sampling_selector':case['configuration']['conditioning_inputs'],
                    'sampling_reference_audit_configuration':case['configuration']['conditioning_inputs']['building_type']+'_90_1_2013',
                    'interpretation':'Actual template/view schedules and targets transformed using pinned Standards 0.8.6 and audited ComStock v33 selector closure; no stock population equivalence'}
            if case['building_type']=='Warehouse' or restaurant or retail:
                context['source_default_cleanup_method_evidence']=records['reference','standards086__lib__openstudio-standards__schedules__modify_rb']['provenance']
            original_loads = {l['demand_id']: l for l in definition['loads']}
            for load in ready['loads']:
                slot = load['end_use']
                original = original_loads[load['demand_id']]
                if restaurant and load['type']=='hot_water':continue
                sid = original['schedule_id']
                src = source_schedule(sid, ready)
                sources[slot] = src
                context['slot_sources'][slot] = src
                context['slot_modes'][slot] = 'hours'
                ev = field_evidence(original['evidence_id'], receipt)
                if load['type'] == 'occupancy':
                    add_slot(slot, sid, 'fraction', 'resident_count')
                    controls.append({'slot': slot, 'quantity': 'occupancy_fraction', 'unit': 'fraction',
                                     'evidence': dict(ev, nominal_density={'value': original['value'], 'unit': original['unit'], 'basis': original['basis']})})
                else:
                    add_slot(slot, sid, 'fraction', 'load')
                    demands.append({'demand_id': load['demand_id'], 'slot': slot, 'quantity': slot,
                        'value': original['value'], 'unit': original['unit'], 'basis': original['basis'],
                        'fuel': load.get('fuel', 'water' if load['type'] == 'hot_water' else 'electricity'),
                        'host': load['host'], 'evidence': ev})
                if load['type'] == 'hot_water':
                    tsid = load['target_temperature_schedule_id']
                    src = source_schedule(tsid, ready)
                    target_slot = slot+'_target_temperature'
                    add_control(target_slot, tsid, 'C', 'temperature', {'definition': receipt, 'ready_resolutions': ready['metadata']['resolutions']})
                    companions[target_slot] = {'method': 'source_rules', 'source': src, 'evidence': {'selected_source': receipt}}
            for key in ('heating_setpoint', 'cooling_setpoint', 'activity'):
                sid = ready['controls'].get(key+'_schedule_id')
                if sid is None:
                    continue
                src = source_schedule(sid, ready)
                sources[key] = src
                context['slot_sources'][key] = src
                context['slot_modes'][key] = 'hours' if key == 'activity' else 'tstat'
                unit = 'W/person' if key == 'activity' else 'C'
                ev = field_evidence(definition['parameters'][key+'_schedule_id']['evidence_id'], receipt)
                add_control(key, sid, unit, 'activity' if key == 'activity' else 'temperature', ev)
        recipe = {'schema_version': '1.0.0', 'resolved': resolved, 'bound_inputs': bound,
                  'required_inputs': ['year', *bound], 'reference_year': scope['calendar']['year'],
                  'calendar_year_locked': residential, 'reference_sources': sources,
                  'companion_rules': companions, 'source_context': context,
                  'aggregate_binding_policy': 'source_recovered_physical_demands' if residential else 'original_definition_demands'}
        if not residential and (restaurant or retail):
            recipe.update(required_contract_version='1.1.0',required_service_links=links,
                          calendar_year_locked=True,
                          aggregate_binding_policy='original_definition_local_demands_and_typed_external_service_links')
        record['recipe'] = recipe
        statuses[pid] = 'accepted_inactive' if accepted_absence else 'compiled'
        policies['programs'].append({k: recipe[k] for k in ('schema_version', 'bound_inputs', 'required_inputs',
                    'reference_year', 'calendar_year_locked', 'aggregate_binding_policy')} | {
                    'program_id': pid, 'status': statuses[pid], 'source': resolved['source'],
                    'slots': slots, 'demands': demands, 'controls': controls,
                    'shared_services': resolved['shared_services'], 'evidence': resolved['evidence']})
    compile_source_parent_recipes(records,scope)
    compositions = [{'id': c['id'], 'status': 'compiled' if c['members'] and
                    all(m['program_id'] in statuses for m in c['members']) else 'unsupported_binding',
                    'members': c['members']} for c in bundle['compositions']]
    expanded = scope['milestone_id'] != 'M1'
    index = {'schema_version': '1.0.0', 'programs': [{'id': p['id'], 'status': statuses.get(p['id'], 'requires_binding' if expanded else 'unsupported_binding'),
             'source_family': p['source_family'], 'evidence_view': p['evidence_view'],
             'reason': None if p['id'] in statuses else ('outside_'+scope['milestone_id']+'; source carrier/aggregation and transform certification remain' if expanded else
                 'outside_exact_M1; no extracted source-backed binding certified')}
             for p in bundle['programs']], 'compositions': [{'id': c['id'], 'status': c['status']} for c in compositions],
             'provenance': _receipt('data/definition-releases/v0.1.1/programs.json', '/', 'Compact identity/status index only; no synthetic Cartesian dependencies')}
    coverage = {'schema_version': '1.0.0', 'milestone': scope['milestone_id'], 'cases': [{'case_id': c['case_id'],
                'program_id': c['program_id'], 'status': statuses[c['program_id']]} for c in scope['cases']],
                'catalogue_program_count': len(bundle['programs']), 'catalogue_composition_count': len(compositions),
                'physical_resource_scope': 'exact ten M1 cases' if not expanded else 'exact declared '+str(len(scope['cases']))+' source cases', 'population_weighting': False}
    records['reference', 'catalogue-index'] = index
    records['reference', 'recipe-coverage'] = coverage
    return {'programs': policies, 'compositions': {'schema_version': '1.0.0', 'compositions': compositions,
            'provenance': _receipt('data/definition-releases/v0.1.1/compositions.json', '/', 'Exact recorded membership/weights; no physical expansion outside M1')},
            'catalogue-index': index, 'coverage': coverage}


def compile_source_parent_recipes(records,scope):
    """Declare exact derived slots and original member targets before RNG."""
    from atlas_schedules.source_compositions import source_factors
    for case in scope['cases']:
        recipe=records['program',case['program_id']]['recipe']
        allocation=recipe.get('source_composition')
        if allocation is None:continue
        areas,total,factors=source_factors(allocation)
        groups={};children=[]
        for member,factor in zip(allocation['definition']['members'],factors):
            child=records['program',member['program_id']]['recipe']
            children.append(child)
            if child.get('source_composition') is not None or child['resolved']['shared_services']:
                raise GeneratorError('requires_binding',case['program_id'],'Source nested/service allocation requires exact independently audited ownership')
            for demand in child['resolved']['demands']:
                source=child['reference_sources'][demand['slot']]
                values=copy.deepcopy(source['values']) if source.get('type')=='annual' else evaluate_rules(source,scope['calendar']['year'],[])['values']
                target=reference_budget(demand,values)
                carrier='m3/s' if demand['unit'].startswith('m3/s') else 'W' if demand['unit'].startswith('W') else None
                if carrier is None or demand['basis']!='floor_area':
                    raise GeneratorError('requires_binding',case['program_id'],'Exact source composition physical basis/carrier needs audited conversion')
                key=(demand['quantity'],carrier,demand['fuel'],demand['host'])
                groups.setdefault(key,[]).append({'program_id':member['program_id'],'demand_id':demand['demand_id'],
                    'factor':factor,'original_target':target,'source_demand':copy.deepcopy(demand)})
        resolved=recipe['resolved']
        for (quantity,carrier,fuel,host),components in groups.items():
            slot='load/'+'/'.join(quote(part,safe='') for part in (quantity,carrier,fuel,host))
            target=math.fsum(c['factor']*c['original_target']['total'] for c in components)
            evidence={'method':'sum_original_member_annual_targets_before_rng','components':components,
                'source_composition':copy.deepcopy(allocation),'original_parent_definition':copy.deepcopy(records['program',case['program_id']]['definition']['loads']),
                'interpretation':'Source weights validate represented areas; individually original member targets authoritative, no legacy averaged profile product'}
            resolved['slots'].append({'slot':slot,'source_schedule_id':'generated-member-trajectories','unit':'fraction','kind':'load'})
            resolved['demands'].append({'demand_id':slot,'slot':slot,'quantity':quantity,'value':None,
                'unit':carrier+'/m2','basis':'floor_area','fuel':fuel,'host':host,'evidence':evidence,
                'annual_target':{'total':target,'unit':('m3' if carrier=='m3/s' else 'Wh')+'/m2','evidence':evidence}})
        pairs=[c for c in children if any(x['quantity']=='occupancy_fraction' and x['evidence']['nominal_density']['value']>0 for x in c['resolved']['controls'])]
        if pairs:
            resolved['slots'].append({'slot':'people_heat','source_schedule_id':'generated-member-trajectories','unit':'W/m2','kind':'control'})
            resolved['controls'].append({'slot':'people_heat','quantity':'people_heat','unit':'W/m2',
                'evidence':{'method':'actual_member_density_occupancy_activity_pairs','source_composition':copy.deepcopy(allocation)}})
        for slot in ('heating_setpoint','cooling_setpoint'):
            eligible=[{'program_id':m['program_id'],'factor':factor,'source_control':copy.deepcopy(control)}
                for m,factor,c in zip(allocation['definition']['members'],factors,children)
                for control in c['resolved']['controls'] if control['slot']==slot]
            if not eligible:continue
            resolved['slots'].append({'slot':slot,'source_schedule_id':'generated-member-trajectories','unit':'C','kind':'control'})
            resolved['controls'].append({'slot':slot,'quantity':'temperature','unit':'C',
                'evidence':{'method':'source_represented_area_pointwise_eligible_average','eligible_members':eligible,
                    'interpretation':'ADR0012 representative controls; no thermal conservation claim'}})
        recipe['source_context']={'case_id':case['case_id'],'method':'actual_generated_source_constituents',
                                  'source_composition':copy.deepcopy(allocation)}


def build_resources(destination: Path, scope: str, tables_destination: Path | None = None) -> dict:
    if scope=='restaurants':
        from scripts.schedule_generator_restaurant_build import build_cumulative_resources
        return build_cumulative_resources(destination,tables_destination)
    if scope not in {'pilot', 'residential', 'medium-office', 'small-office','warehouse'}:
        raise GeneratorError('unsupported_scope', '/scope', 'Unknown explicit source family scope')
    lock_file = {'pilot':'sources/schedule-generator-lock.json','residential':'sources/schedule-generator-residential-lock.json','medium-office':'sources/schedule-generator-medium-office-lock.json','small-office':'sources/schedule-generator-small-office-lock.json','warehouse':'sources/schedule-generator-warehouse-lock.json'}[scope]
    scope_file = {'pilot':'sources/schedule-generator-m1-scope.json','residential':'sources/schedule-generator-residential-scope.json','medium-office':'sources/schedule-generator-medium-office-scope.json','small-office':'sources/schedule-generator-small-office-scope.json','warehouse':'sources/schedule-generator-warehouse-scope.json'}[scope]
    lock = _read(ROOT/lock_file)
    manifest_scope = _read(ROOT/scope_file)
    validate_scope(manifest_scope, lock)
    audit = _read(ROOT/'data/schedule-generator/comstock-sampling-audit.json')
    validate_sampling_audit(audit)
    for file, receipt in lock['frozen_files'].items():
        content = (ROOT/file).read_bytes()
        if len(content) != receipt['size_bytes'] or hashlib.sha256(content).hexdigest() != receipt['sha256']:
            raise GeneratorError('source_integrity', file, 'Frozen reference checksum mismatch')
    with tempfile.TemporaryDirectory() as temporary:
        source_manifest = extract_sources(lock, ROOT/'data/raw', Path(temporary)/'resources')
        sources = ResourceSet(Path(temporary)/'resources', source_manifest['resource_set_id'])
        records = {(e['kind'], e['key']): sources.get(e['kind'], e['key']) for e in source_manifest['resources']}
    records['commercial', 'sampling-audit'] = audit
    if scope in {'small-office','warehouse'}:
        records['commercial','small_office__sampling-audit']=_read(ROOT/'data/schedule-generator/small-office-sampling-audit.json')
    if scope=='warehouse':records['commercial','warehouse__sampling-audit']=_read(ROOT/'data/schedule-generator/warehouse-sampling-audit.json')
    if scope in {'medium-office','small-office','warehouse'}:
        receipt = _read(ROOT/'sources/schedule-generator-ruby-float-lock.json')['sources'][0]
        content = (ROOT/receipt['source_path']).read_bytes()
        if hashlib.sha256(content).hexdigest()!=receipt['sha256'] or len(content)!=receipt['size_bytes']:
            raise GeneratorError('source_integrity',receipt['source_path'],'Pinned Ruby Float method differs')
        records['reference','ruby-float-numeric-c'] = {'text':content.decode('utf-8'),'provenance':receipt}
        records['reference','notice-ruby-float'] = {'text':(ROOT/receipt['license_notice']).read_text(encoding='utf-8'),'source_path':receipt['license_notice']}
    records['residential', 'event-constants'] = event_constants(records['residential', 'constants_rb'])
    records['reference', 'm1-scope'] = manifest_scope
    records['reference', 'comparison-policy'] = _read(ROOT/'sources/schedule-generator-policy.json')
    records['reference', 'source-random-rule-vectors'] = load_reference_vectors()
    records['reference', 'notice-ruby-random'] = {'text': (ROOT/'sources/licenses/ruby-random.txt').read_text(encoding='utf-8'),
                                                    'source_path': 'sources/licenses/ruby-random.txt'}
    programs_file = 'data/definition-releases/v0.1.1/programs.json'
    programs = _read(ROOT/programs_file)
    schedule_ids, source_program_ids = set(), set()
    for case in manifest_scope['cases']:
        program = programs[int(case['program_definition']['json_pointer'][1:])]
        source_program_ids.add(program['source_id'])
        for load in program['loads']:
            if load.get('schedule_id'):
                schedule_ids.add(load['schedule_id'])
        for parameter in program['parameters'].values():
            if parameter.get('unit') == 'schedule reference' and parameter.get('value'):
                schedule_ids.add(parameter['value'])
        record = {'definition': program, 'case': case,
                  'provenance': _receipt(programs_file, case['program_definition']['json_pointer'], 'Exact frozen program; no merged views')}
        if 'file' in case['configuration']:
            file = case['configuration']['file']
            profile = _read(ROOT/file)
            record['configuration'] = _portable(profile['metadata'])
            record['configuration_provenance'] = _receipt(file, '/metadata', 'Exact recovered inputs; local execution-cache paths omitted as null; reference seed retained as evidence')
            records['reference', case['configuration_id']+'-profile'] = {
                'metadata': _portable(profile['metadata']), 'series': profile['series'],
                'provenance': _receipt(file, '/', 'Frozen numerical reference; local execution-cache paths omitted')}
        records['program', case['program_id']] = record
    file = 'data/definition-releases/v0.1.1/schedules.json'
    for index, schedule in enumerate(_read(ROOT/file)):
        if schedule['id'] in schedule_ids:
            records['reference', schedule['id']] = {'definition': schedule, 'provenance': _receipt(file, '/'+str(index), 'Exact frozen rules, source order, selectors and design days')}
    file = 'data/definition-releases/v0.1.1/compositions.json'
    allowed = {case['program_id'] for case in manifest_scope['cases']}
    for index, composition in enumerate(_read(ROOT/file)):
        if composition['members'] and all(member['program_id'] in allowed for member in composition['members']):
            records['composition', composition['id']] = {'definition': composition, 'provenance': _receipt(file, '/'+str(index), 'Exact frozen membership and weights')}
    file = 'data/resolution-releases/v0.4.0/resolutions.json'
    resolutions = _read(ROOT/file)
    selected = [r for r in resolutions['resolutions'] if r.get('record_id') in source_program_ids]
    records['reference', 'resolutions'] = {'resolutions': selected, 'provenance': _receipt(file, '/resolutions', 'Select by original source program identity; no implicit absence')}
    file = 'data/definition-releases/v0.1.1/services.json'
    service_ids = {s for case in manifest_scope['cases'] for s in records['program', case['program_id']]['definition']['service_ids']}
    for index, service in enumerate(_read(ROOT/file)):
        if service['id'] in service_ids:
            records['reference', service['id']] = {'definition': service, 'provenance': _receipt(file, '/'+str(index), 'Exact shared service identity, hosts and beneficiaries')}
    def identifiers(value):
        if isinstance(value, dict):
            return set().union(*(identifiers(v) for v in value.values())) if value else set()
        if isinstance(value, list):
            return set().union(*(identifiers(v) for v in value)) if value else set()
        return {value} if isinstance(value, str) and value.startswith(('evidence-', 'sourcefile-')) else set()
    required_ids = identifiers(list(records.values()))
    file = 'data/definition-releases/v0.1.1/provenance.json'
    for index, evidence in enumerate(_read(ROOT/file)):
        if evidence['id'] in required_ids:
            records['reference', evidence['id']] = {'definition': evidence, 'provenance': _receipt(file, '/'+str(index), 'Exact per-field original value, units, source locator and transformation')}
            required_ids.add(evidence['source_file_id'])
    file = 'data/definition-releases/v0.1.1/source_files.json'
    for index, source_file in enumerate(_read(ROOT/file)):
        if source_file['id'] in required_ids:
            records['reference', source_file['id']] = {'definition': source_file, 'provenance': _receipt(file, '/'+str(index), 'Exact upstream source revision and byte checksum')}
    file = 'data/resolution-releases/v0.4.0/fixed-background-schedules.json'
    records['residential', 'fixed-background-schedules'] = {'definition': _read(ROOT/file), 'provenance': _receipt(file, '/', 'Exact frozen source default variants')}
    if scope in {'residential','medium-office','small-office','warehouse'}:
        recovery = _read(ROOT/'data/program-inputs/residential-v1.json')
        fixed = records['residential', 'fixed-background-schedules']['definition']
        for shape in recovery['schedules'].values():
            name = shape['name']
            if name in fixed['schedules']:
                continue
            if shape['source_context']['variant'] != fixed['variant']:
                raise GeneratorError('source_integrity', name, 'Ancillary companion variant differs')
            evidence = shape['source_context']['evidence']
            operands = {}
            for receipt in evidence:
                field = receipt['source_locator'].rsplit('/', 1)[-1]
                operand = {'WeekdayScheduleFractions': 'weekday_fractions',
                           'WeekendScheduleFractions': 'weekend_fractions',
                           'MonthlyScheduleMultipliers': 'monthly_multipliers'}.get(field)
                if operand is None:
                    raise GeneratorError('source_integrity', name, 'Missing actual fixed schedule method operand')
                operands[operand] = [float(v) for v in receipt['original_value'].split(',')]
            if set(operands) != {'weekday_fractions','weekend_fractions','monthly_multipliers'}:
                raise GeneratorError('source_integrity', name, 'Incomplete fixed source shape')
            peak = max(operands['weekday_fractions']+operands['weekend_fractions'])*max(operands['monthly_multipliers'])
            fixed['schedules'][name] = dict(operands, id=name, unit='dimensionless', temperature_dependent=False,
                                          peak_divisor=peak, evidence=evidence)
    for notice in lock['notices']:
        records['reference', 'notice-'+Path(notice).stem] = {'text': (ROOT/notice).read_text(encoding='utf-8'), 'source_path': notice}
    records['reference', 'notice-standards086'] = sources.get('reference', 'standards086__LICENSE_md')
    tables = compile_recipes(records, manifest_scope)
    if scope == 'residential':
        certificate = ROOT/'data/schedule-generator/families/residential/certification.json'
        if certificate.exists():
            records['reference','family-certification'] = _read(certificate)
        native_lock = ROOT/'sources/schedule-generator-residential-family-reference-lock.json'
        if native_lock.exists():
            native = _read(native_lock)
            vectors = (ROOT/native['vectors']['source_path']).read_bytes()
            if hashlib.sha256(vectors).hexdigest() != native['vectors']['sha256'] or len(vectors) != native['vectors']['size_bytes']:
                raise GeneratorError('source_integrity', str(native_lock), 'Independent family native reference differs')
            records['reference','family-native-lock'] = native
    if scope == 'medium-office':
        certificate = ROOT/'data/schedule-generator/families/medium-office/certification.json'
        if certificate.exists(): records['reference','family-certification'] = _read(certificate)
        for key,file in {'family-native-lock':'sources/schedule-generator-medium-office-cumulative-reference-lock.json',
                         'residential-native-lock':'sources/schedule-generator-residential-family-reference-lock.json',
                         'commercial-native-lock':'sources/schedule-generator-medium-office-family-reference-lock.json'}.items():
            native = _read(ROOT/file)
            vectors = (ROOT/native['vectors']['source_path']).read_bytes()
            if hashlib.sha256(vectors).hexdigest()!=native['vectors']['sha256'] or len(vectors)!=native['vectors']['size_bytes']:
                raise GeneratorError('source_integrity',file,'Independent native component differs')
            records['reference',key] = native
    if scope == 'medium-office':
        records['reference','family-native-join'] = _read(ROOT/'data/schedule-generator/medium-office-cumulative-native.json')
    if scope in {'small-office','warehouse'}:
        certificate=ROOT/('data/schedule-generator/families/'+scope+'/certification.json')
        if certificate.exists():records['reference','family-certification']=_read(certificate)
        native_files={'family-native-lock':'sources/schedule-generator-'+scope+'-cumulative-reference-lock.json',
                         'residential-native-lock':'sources/schedule-generator-residential-family-reference-lock.json',
                         'commercial-native-lock':'sources/schedule-generator-medium-office-family-reference-lock.json',
                         'small-office-native-lock':'sources/schedule-generator-small-office-family-reference-lock.json'}
        if scope=='warehouse':native_files['warehouse-native-lock']='sources/schedule-generator-warehouse-family-reference-lock.json'
        for key,file in native_files.items():
            path=ROOT/file
            if not path.exists():continue
            native=_read(path);vectors=(ROOT/native['vectors']['source_path']).read_bytes()
            if hashlib.sha256(vectors).hexdigest()!=native['vectors']['sha256'] or len(vectors)!=native['vectors']['size_bytes']:
                raise GeneratorError('source_integrity',file,'Independent native component differs')
            records['reference',key]=native
        join=ROOT/('data/schedule-generator/'+scope+'-cumulative-native.json')
        if join.exists():records['reference','family-native-join']=_read(join)
    if tables_destination is not None:
        tables_destination.mkdir(parents=True, exist_ok=True)
        for name, table in tables.items():
            (tables_destination/(name+'.json')).write_bytes(canonical(table))
    # Inventory exposes every dependency; generation support is certified by later kernel gates.
    return write_resources(destination, records, {'scope': scope, 'milestone_id': manifest_scope['milestone_id'],
                           'scope_version': manifest_scope['scope_version'], 'source_gate_status': 'passed',
                           'generator_support_status': 'not_shipped', 'cases': manifest_scope['cases'],
                           'dependency_inventory': lock['required_resources'], 'blocked_families': lock['blocked_families']})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scope', default='pilot')
    parser.add_argument('--destination', type=Path, default=ROOT/'build/generator-pilot-resources')
    parser.add_argument('--tables-destination', type=Path)
    args = parser.parse_args()
    manifest = build_resources(args.destination, args.scope, args.tables_destination)
    print(f"Verified {len(manifest['resources'])} dependencies for {len(manifest['cases'])} cases: {manifest['resource_set_id']}")


if __name__ == '__main__':
    main()
