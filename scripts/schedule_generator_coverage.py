"""Inspect exact M1 case/channel support and the remaining catalogue."""
import argparse
import hashlib
import json
from pathlib import Path

from atlas_schedules.canonical import canonical
from atlas_schedules.resources import ResourceSet

ROOT = Path(__file__).resolve().parents[1]

COMMERCIAL_SELECTORS = {
    'FullServiceRestaurant': 'full_service_restaurant', 'Hospital': 'hospital',
    'LargeHotel': 'large_hotel', 'LargeOffice': 'large_office', 'MediumOffice': 'medium_office',
    'Outpatient': 'outpatient', 'PrimarySchool': 'primary_school',
    'QuickServiceRestaurant': 'quick_service_restaurant', 'RetailStandalone': 'retail',
    'RetailStripmall': 'strip_mall', 'SecondarySchool': 'secondary_school',
    'SmallHotel': 'small_hotel', 'SmallOffice': 'small_office', 'SuperMarket': 'supermarket',
    'Warehouse': 'warehouse',
}


def build_catalogue_inventory(resources: ResourceSet | None = None) -> dict:
    """Inventory actual source operands independently of a certified runtime scope.

    A known frozen realization is evidence, not stochastic method certification.
    Shared services retain allocation operands; exclusions never count as complete.
    """
    base = ROOT / 'data/definition-releases/v0.1.1'
    read = lambda path: json.loads(Path(path).read_text(encoding='utf-8'))
    definitions, compositions = read(base/'programs.json'), read(base/'compositions.json')
    services = {s['id']: s for s in read(base/'services.json')}
    recovery = read(ROOT/'data/program-inputs/residential-v1.json')
    if resources is None:
        manifest = read(ROOT/'atlas_schedules/data/manifest.json')
        resources = ResourceSet.load(manifest['resource_set_id'])
    compiled = {p['id']: p['status'] for p in resources.get('reference', 'catalogue-index')['programs']}
    programs = []
    for index, definition in enumerate(definitions):
        pid = definition['id']
        residential = definition.get('scope') == 'whole_dwelling'
        original = recovery['records'].get(definition['source_id']) if residential else None
        compiled_record = (resources.get('program', pid)
                           if compiled.get(pid) in {'compiled', 'accepted_inactive'} else None)
        recipe = compiled_record['recipe'] if compiled_record else None
        certified = ({s['slot']: ('source_fixed' if s['slot'] in recipe['companion_rules'] else 'generated')
                      for s in recipe['resolved']['slots']} if recipe else {})
        channels = []
        def channel(slot, value, state, pointer, evidence, required, identity=None, source_sid=None):
            runtime_slot = slot if slot in certified else None
            if recipe and 'source_composition' in recipe and identity is not None and runtime_slot is None:
                matches=[d['slot'] for d in recipe['resolved']['demands'] if d['quantity']==slot and
                    any(original['demand_id']==identity and original['quantity']==slot for original in
                        d['evidence'].get('original_parent_definition',[]))]
                if len(matches)==1:runtime_slot=matches[0]
            if recipe and runtime_slot is None and source_sid is not None:
                matches = [s['slot'] for s in recipe['resolved']['slots'] if s['source_schedule_id'] == source_sid]
                if len(matches) == 1:
                    runtime_slot = matches[0]
            status = certified.get(runtime_slot, 'absent' if state == 'absent' else 'requires_binding')
            if state == 'excluded':
                status = 'unsupported'
            absence = None
            if status=='requires_binding' and recipe and not residential:
                selected=recipe['resolved']['evidence'][0]
                resolutions=selected['resolutions']
                proofs=[]
                for i,resolution in enumerate(resolutions):
                    if (identity is not None and resolution.get('demand_id')==identity
                            and resolution.get('field')=='value' and resolution.get('original_value') is None
                            and resolution.get('replacement_value')==0 and resolution.get('rule')=='accepted-absence'
                            and resolution.get('decision')=='ADR 0016'
                            and any(d['demand_id']==identity and d['end_use']==slot and d['value']==0 for d in selected['absent_demands'])):
                        proofs.append(('/recipe/resolved/evidence/0/resolutions/'+str(i),resolution))
                    disabled={'heating_setpoint':'heating_enabled','cooling_setpoint':'cooling_enabled'}.get(slot)
                    if (disabled and selected['accepted_absence'] and resolution.get('field')==disabled
                            and resolution.get('value') is False and resolution.get('rule')=='accepted-support-space-inactive-conditioning'):
                        proofs.append(('/recipe/resolved/evidence/0/resolutions/'+str(i),resolution))
                if slot=='activity' and selected['accepted_absence']:
                    for i,demand in enumerate(selected['absent_demands']):
                        if demand['end_use']=='occupancy' and demand['value']==0:
                            proofs.append(('/recipe/resolved/evidence/0/absent_demands/'+str(i),demand))
                conditioning=definition['parameters'].get('conditioning',{})
                disabled={'heating_setpoint':'heating_enabled','cooling_setpoint':'cooling_enabled'}.get(slot)
                if (disabled and conditioning.get('status')=='known'
                        and isinstance(conditioning.get('value'),dict)
                        and conditioning['value'].get(disabled) is False):
                    proofs.append(('/definition/parameters/conditioning',conditioning))
                if proofs:
                    entry=next(e for e in resources.manifest['resources'] if e['kind']=='program' and e['key']==pid)
                    absence={'programme_id':pid,'evidence_view':definition['evidence_view'],
                        'interpretation':'Exact previously approved scoped absence/disabled-control receipt; original unknown/null retained, no magnitude inserted',
                        'resolution_receipts':[{'resource_kind':'program','resource_key':pid,'resource_sha256':entry['sha256'],
                            'pointer':pointer,'receipt':receipt,'receipt_sha256':hashlib.sha256(canonical(receipt)).hexdigest()} for pointer,receipt in proofs]}
                    status='absent'
            if status == 'requires_binding' and recipe and original:
                zero = [l for l in original['loads'] if l['end_use']==slot and l['value']==0]
                presence = {'hot_water_clothes_washer':'clothes_washer',
                            'hot_water_dishwasher':'dishwasher'}.get(slot,slot)
                if zero:
                    absence = {'original_zero_demands':zero}
                elif recipe['bound_inputs']['residents']==0:
                    absence = {'configuration':compiled_record['configuration_provenance'],
                        'original_residents':0,'source_method':'BuildResidentialScheduleFile/measure.rb zero-occupant skip',
                        'interpretation':'Original unknown is retained; the actual selected source branch omits stochastic channels'}
                elif recipe['bound_inputs']['installed'].get(presence) is False:
                    absence = {'configuration':compiled_record['configuration_provenance'],
                        'installed_operand':presence,'original_value':False,
                        'source_arguments':compiled_record['configuration']['arguments'],
                        'source_method':'ScheduleGenerator.create_stochastic_schedules actual HPXML appliance presence',
                        'interpretation':'Selected source absence; no unknown value was substituted with zero'}
                if absence is not None:
                    status = 'absent'
            resolved_rows = ([r for kind in ('demands','controls') for r in recipe['resolved'][kind]
                              if r['slot'] == runtime_slot] if recipe and runtime_slot is not None else [])
            channels.append({'slot': slot, 'runtime_slot': runtime_slot, 'demand_id': identity, 'source_state': state,
                'status': status, 'complete': status in {'generated','source_fixed','absent'} and state != 'excluded',
                'original_value': value, 'source_locator': pointer, 'evidence': evidence,
                'resolved_source_evidence': [r['evidence'] for r in resolved_rows],
                'resolved_absence_evidence':absence,
                'resolved_physical_targets': [{k: r.get(k) for k in
                    ('demand_id','quantity','fuel','host','basis','annual_target')} for r in resolved_rows if 'demand_id' in r],
                'required_inputs': required,
                'reason': None if status in {'generated','source_fixed','absent'} else
                    ('existing_scope_exclusion' if state == 'excluded' else
                     'recoverable_exact_fixture_inputs_weather_and_source_branch_certification' if residential else
                     'source_occupancy_carrier_aggregation_and_transform_applicability_not_yet_certified')})
        for i, load in enumerate(definition['loads']):
            state = 'unknown' if load['value'] is None else 'absent' if load['value'] == 0 else 'known'
            channel(load['quantity'], load['value'], state, f'programs.json#/{index}/loads/{i}',
                    load.get('evidence_id'), load.get('required_inputs', []), load['demand_id'], load.get('schedule_id'))
        for name, parameter in definition['parameters'].items():
            if parameter['unit'] != 'schedule reference':
                continue
            slot = name.removesuffix('_schedule_id')
            channel(slot, parameter['value'], 'unknown' if parameter['value'] is None else 'known',
                    f'programs.json#/{index}/parameters/{name}', parameter.get('evidence_id'),
                    parameter.get('required_inputs', []), source_sid=parameter['value'])
        for sid in definition['service_ids']:
            service = services[sid]
            channel(service['load']['quantity'], service['load']['value'], 'shared',
                    'services.json#'+sid, service['evidence_ids'],
                    service['load']['required_inputs'], sid)
            channels[-1]['shared_service'] = {k: service.get(k) for k in
                ('id','ownership','assignment','beneficiary_program_ids','path_id')}
        if original:
            original_slots = {c['slot'] for c in channels}
            for i, load in enumerate(original['loads']):
                if load['end_use'] not in original_slots:
                    channel(load['end_use'], load['evidence']['original_value'],
                            'absent' if load['value'] == 0 else 'known',
                            f'residential-v1.json#/records/{definition["source_id"]}/loads/{i}',
                            load['evidence'], [], load.get('demand_id'), load.get('schedule_id'))
            for slot in [*original['metadata']['excluded_channels'], 'hvac_equipment_unavailability']:
                channel(slot, None, 'excluded', 'binding-constraints.md#retained-exclusions',
                        {'original_exclusions': original['metadata']['excluded_channels']}, [])
        if recipe:
            represented = {c['runtime_slot'] for c in channels if c['status'] in {'generated','source_fixed'}}
            for resolved_slot in recipe['resolved']['slots']:
                slot = resolved_slot['slot']
                if slot not in represented:
                    rows = [r for kind in ('demands','controls') for r in recipe['resolved'][kind] if r['slot'] == slot]
                    rule = recipe['companion_rules'].get(slot,{})
                    channel(slot,rule.get('value'),'known',f'packaged-program/{pid}#/recipe/resolved/slots',
                            [r['evidence'] for r in rows],[],source_sid=resolved_slot['source_schedule_id'])
        dependencies = {'template': definition['template'], 'evidence_view': definition['evidence_view'],
                        'source_family': definition['source_family'], 'source_id': definition['source_id']}
        if original:
            dependencies.update(state=original['metadata']['original_selected_options']['State'],
                weather=original['metadata']['weather'], configuration_id=definition['source_id'],
                climate_policy='exact_fixture_station_proxy_and_original_region')
        else:
            dependencies.update(climate_policy='shared_source_rules_no_fabricated_climate_records',
                comstock_selector=COMMERCIAL_SELECTORS.get(definition['building_type']),
                carrier_requirement='same_building_template_source_view_occupancy_aggregate_or_verified_single_carrier',
                clock='controlled_no_DST_local_standard_calendar')
        programs.append({k: definition.get(k) for k in ('id','name','building_type','template','climate','source_family','evidence_view','scope')} |
            {'scope': definition.get('scope', 'program'), 'dependencies': dependencies, 'channels': channels,
             'absence_evidence': recipe['resolved']['evidence'] if recipe and not certified else None,
             'runtime_status': compiled.get(pid), 'declared_recipe_complete':bool(recipe),
             'full_record_complete':bool(recipe) and all(c['complete'] for c in channels)})
    by_id = {p['id']: p for p in programs}
    composition_inventory = [{k: copy_value for k, copy_value in c.items()} |
        {'member_coverage': [{'program_id': m['program_id'], 'complete': by_id[m['program_id']]['full_record_complete']}
                             for m in c['members']],
         'complete': bool(c['members']) and all(by_id[m['program_id']]['full_record_complete'] for m in c['members'])}
        for c in compositions]
    return {'schema_version': '1.0.0', 'programs': programs, 'compositions': composition_inventory,
        'full_extraction_complete': all(p['full_record_complete'] for p in programs),
        'doe_locations': [{'climate_zone': '3B', 'location': location, 'variant': variant,
            'weather_binding': None, 'program_ids': [], 'status': 'requires_binding',
            'source_locator': 'DOE Commercial Reference Buildings report Table 2',
            'source_sha256': '39520427c39c4a424d8b0d072c47d5bfdc248631632e880501866aae6b0d131a',
            'missing_operand': 'exact named DOE EPW member and checksum; no catalogue climate-specific program exists'}
            for location, variant in [('Los Angeles','coastal'), ('Las Vegas','inland')]]}


def _pointer_value(record: dict, pointer: str):
    if not isinstance(pointer, str) or not pointer.startswith('/'):
        raise ValueError('Invalid evidence pointer')
    value = record
    for token in pointer[1:].split('/'):
        token = token.replace('~1', '/').replace('~0', '~')
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def _channel_evidence(resources: ResourceSet, resource_entries: dict, program_id: str,
                      recipe: dict, slot: str, schedule_id: str) -> dict | None:
    if ('reference', schedule_id) in resource_entries:
        wrapper = resources.get('reference', schedule_id)
        definition, provenance = wrapper.get('definition', {}), wrapper.get('provenance', {})
        source = recipe['reference_sources'].get(slot)
        if (definition.get('id') != schedule_id or not isinstance(provenance, dict) or
                not provenance.get('source_locator') or
                (source and (source.get('id') != schedule_id or
                             source.get('provenance_id') != definition.get('provenance_id')))):
            return None
        kind, key, pointer = 'reference', schedule_id, '/provenance'
    elif slot in recipe['companion_rules']:
        kind, key = 'program', program_id
        pointer = '/recipe/companion_rules/' + slot.replace('~', '~0').replace('/', '~1') + '/evidence'
    else:
        matches = [(kind, index, row) for kind in ('demands', 'controls')
                   for index, row in enumerate(recipe['resolved'][kind]) if row['slot'] == slot]
        if not matches:
            return None
        kind, index, _ = matches[0]
        kind, key, pointer = 'program', program_id, f'/recipe/resolved/{kind}/{index}/evidence'
    try:
        receipt = _pointer_value(resources.get(kind, key), pointer)
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    if not isinstance(receipt, dict) or not receipt:
        return None
    entry = resource_entries[(kind, key)]
    return {'resource_kind': kind, 'resource_key': key, 'pointer': pointer,
            'resource_sha256': entry['sha256'],
            'receipt_sha256': hashlib.sha256(canonical(receipt)).hexdigest()}


def build_coverage(resources: ResourceSet, scope: dict | None = None) -> dict:
    scope = scope if scope is not None else resources.get('reference', 'm1-scope')
    index = resources.get('reference', 'catalogue-index')
    programmed = {row['id']: row for row in index['programs']}
    resource_entries = {(entry['kind'], entry['key']): entry for entry in resources.manifest['resources']}
    evidence_inventory = {}
    cases = []
    for declaration in scope['cases']:
        case_id, program_id = declaration['case_id'], declaration['program_id']
        record = resources.get('program', program_id)
        recipe = record['recipe']
        resolved = recipe['resolved']
        absent = not resolved['slots']
        expected = 'accepted_inactive' if absent else 'compiled'
        errors = []
        if record['case'] != declaration:
            errors.append('case declaration differs from compiled source')
        if programmed.get(program_id, {}).get('status') != expected:
            errors.append('catalogue status differs from recipe')
        if declaration.get('source_gate_status') != 'passed':
            errors.append('source gate did not pass')
        if absent and not resolved['evidence'][0].get('accepted_absence'):
            errors.append('zero-slot recipe lacks source-backed absence')
        demand_slots = {item['slot'] for item in resolved['demands']}
        control_slots = {item['slot'] for item in resolved['controls']}
        slots = [item['slot'] for item in resolved['slots']]
        if len(slots) != len(set(slots)):
            errors.append('duplicate slot')
        channels = []
        for item in resolved['slots']:
            slot = item['slot']
            owner = 'load' if slot in demand_slots else 'control' if slot in control_slots else None
            status = ('source_fixed' if slot in recipe['companion_rules'] else 'generated') if item.get('source_schedule_id') and owner else 'requires_binding'
            source_evidence = _channel_evidence(resources, resource_entries, program_id, recipe,
                                                slot, item.get('source_schedule_id')) if status != 'requires_binding' else None
            channels.append({'slot': slot, 'kind': owner, 'status': status,
                             'source_schedule_id': item.get('source_schedule_id'),
                             'source_evidence': source_evidence})
            if status == 'requires_binding':
                errors.append('unbound included channel: ' + slot)
            elif source_evidence is None:
                errors.append('missing or dangling source evidence: ' + slot)
            else:
                evidence_inventory[(source_evidence['resource_kind'], source_evidence['resource_key'],
                                    source_evidence['pointer'])] = source_evidence
        cases.append({'case_id': case_id, 'program_id': program_id,
                      'configuration_id': declaration['configuration_id'],
                      'template': declaration['template'], 'weather': declaration['weather'],
                      'evidence_view': declaration['evidence_view'], 'status': expected if not errors else 'failed_validation',
                      'expected_slots': slots, 'channels': channels,
                      'accepted_absence': resolved['evidence'][0].get('accepted_absence', False),
                      'absence_evidence': resolved['evidence'][0] if absent else None,
                      'errors': errors})
    declared = {case['program_id'] for case in scope['cases']}
    outside_programs = []
    for item in index['programs']:
        if item['id'] in declared:
            continue
        if item['status'] in {'compiled', 'accepted_inactive'}:
            outside_programs.append(dict(item, catalogue_status=item['status'], status='unsupported_binding',
                                         reason='outside_declared_milestone_scope'))
        else:
            outside_programs.append(item)
    declared_compositions=[]
    for case in scope['cases']:
        recipe=resources.get('program',case['program_id'])['recipe']
        allocation=recipe.get('source_composition')
        if allocation is None:continue
        key=allocation['composition_id'];entry=resource_entries['composition',key]
        record=resources.get('composition',key)
        declared_compositions.append({'id':key,'parent_program_id':case['program_id'],
            'member_program_ids':[m['program_id'] for m in record['definition']['members']],
            'source_evidence':{'resource_kind':'composition','resource_key':key,'pointer':'/provenance',
                'resource_sha256':entry['sha256'],'receipt_sha256':hashlib.sha256(canonical(record['provenance'])).hexdigest()}})
    declared_ids={c['id'] for c in declared_compositions}
    outside_compositions = [c for c in index['compositions'] if c['id'] not in declared_ids]
    report = {'schema_version': '1.0.0', 'resource_set_id': resources.resource_set_id,
              'scope': {'milestone_id': scope['milestone_id'], 'scope_version': scope['scope_version'],
                        'scope_sha256': hashlib.sha256(canonical(scope)).hexdigest(),
                        'case_count': len(scope['cases']), 'case_ids': [c['case_id'] for c in scope['cases']]},
              'cases': cases,
              'evidence_inventory': [evidence_inventory[key] for key in sorted(evidence_inventory)],
              'outside_scope': {'program_count': len(outside_programs), 'composition_count': len(outside_compositions),
                                'programs': outside_programs, 'compositions': outside_compositions},
              'catalogue_program_count': len(index['programs']),
              'catalogue_composition_count': len(index['compositions'])}
    if declared_compositions:
        report['scope'].update(composition_count=len(declared_compositions),composition_ids=[c['id'] for c in declared_compositions])
        report['declared_compositions']=declared_compositions
    return report


def coverage_errors(report: dict, resources: ResourceSet | None = None) -> list[str]:
    errors = []
    inventory = {(entry['resource_kind'], entry['resource_key'], entry['pointer']): entry
                 for entry in report.get('evidence_inventory', [])}
    if len(inventory) != len(report.get('evidence_inventory', [])):
        errors.append('Duplicate evidence inventory entry')
    resource_entries = ({(entry['kind'], entry['key']): entry
                         for entry in resources.manifest['resources']} if resources else {})
    cases = report['cases']
    if report.get('declared_compositions'):
        compositions=report['declared_compositions']
        if (len(compositions)!=report['scope'].get('composition_count') or
                [c['id'] for c in compositions]!=report['scope'].get('composition_ids') or
                len({c['id'] for c in compositions})!=len(compositions)):
            errors.append('Declared source composition denominator differs')
        for composition in compositions:
            label=composition['id']
            if composition['parent_program_id'] not in {c['program_id'] for c in cases}:
                errors.append(label+': parent outside declared cases')
            if resources:
                record=resources.get('composition',label);receipt=composition['source_evidence']
                entry=resource_entries['composition',label]
                parent=resources.get('program',composition['parent_program_id'])['recipe'].get('source_composition')
                if (parent is None or parent['composition_id']!=label or parent['definition']!=record['definition'] or
                        [m['program_id'] for m in record['definition']['members']]!=composition['member_program_ids'] or
                        receipt!={'resource_kind':'composition','resource_key':label,'pointer':'/provenance',
                            'resource_sha256':entry['sha256'],'receipt_sha256':hashlib.sha256(canonical(record['provenance'])).hexdigest()}):
                    errors.append(label+': source composition membership/evidence does not close')
    if [c['case_id'] for c in cases] != report['scope']['case_ids'] or len(cases) != report['scope']['case_count']:
        errors.append('Scope case inventory differs from declared case list')
    if len({c['case_id'] for c in cases}) != len(cases):
        errors.append('Duplicate case')
    for case in cases:
        recipe = resources.get('program', case['program_id'])['recipe'] if resources else None
        if case['status'] not in {'compiled', 'accepted_inactive'} or case['errors']:
            errors.append(case['case_id'] + ': incomplete case')
        if [c['slot'] for c in case['channels']] != case['expected_slots']:
            errors.append(case['case_id'] + ': channel inventory differs from resolved slots')
        if case['status'] == 'accepted_inactive':
            absence = case.get('absence_evidence')
            if (case['channels'] or not case['accepted_absence'] or
                    not isinstance(absence, dict) or not absence.get('accepted_absence') or
                    (resources and absence != recipe['resolved']['evidence'][0])):
                errors.append(case['case_id'] + ': invalid inactive case')
        for channel in case['channels']:
            if channel['status'] not in {'generated', 'source_fixed'} or channel['kind'] not in {'load', 'control'}:
                errors.append(case['case_id'] + '/' + channel['slot'] + ': unresolved channel')
            evidence = channel.get('source_evidence')
            label = case['case_id'] + '/' + channel['slot']
            if not isinstance(evidence, dict) or not evidence:
                errors.append(label + ': missing source evidence')
                continue
            key = (evidence.get('resource_kind'), evidence.get('resource_key'), evidence.get('pointer'))
            if inventory.get(key) != evidence or evidence.get('resource_kind') not in {'program', 'reference'}:
                errors.append(label + ': dangling evidence reference')
                continue
            if ((key[0] == 'program' and key[1] != case['program_id']) or
                    (key[0] == 'reference' and key[1] != channel['source_schedule_id'])):
                errors.append(label + ': evidence points to another channel')
                continue
            if resources:
                entry = resource_entries.get(key[:2])
                try:
                    receipt = _pointer_value(resources.get(*key[:2]), key[2])
                    valid = (entry is not None and entry['sha256'] == evidence['resource_sha256'] and
                             isinstance(receipt, dict) and bool(receipt) and
                             hashlib.sha256(canonical(receipt)).hexdigest() == evidence['receipt_sha256'] and
                             evidence == _channel_evidence(resources, resource_entries,
                                                           case['program_id'], recipe, channel['slot'],
                                                           channel['source_schedule_id']))
                except (KeyError, IndexError, TypeError, ValueError):
                    valid = False
                if not valid:
                    errors.append(label + ': evidence does not resolve in packaged resources')
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--scope', default='m1')
    parser.add_argument('--resources-root', type=Path)
    parser.add_argument('--inventory', action='store_true')
    parser.add_argument('--report', type=Path, default=ROOT / 'docs/validation/schedule-generator-coverage.json')
    args = parser.parse_args(argv)
    if args.scope != 'm1':
        scope_path = ROOT/'sources/schedule-generator-residential-scope.json' if args.scope == 'residential' else Path(args.scope)
        scope = json.loads(scope_path.read_text(encoding='utf-8'))
    else:
        scope = None
    resource_root = args.resources_root if args.resources_root is not None else ROOT/'atlas_schedules/data'
    manifest = json.loads((resource_root/'manifest.json').read_text(encoding='utf-8'))
    resources = ResourceSet(resource_root, manifest['resource_set_id'])
    if args.scope == 'm1' and resources.get('reference', 'm1-scope') != json.loads((ROOT / 'sources/schedule-generator-m1-scope.json').read_text(encoding='utf-8')):
        raise SystemExit('Authoritative M1 scope differs from packaged resources')
    report = build_catalogue_inventory(resources) if args.inventory else build_coverage(resources, scope)
    errors = [] if args.inventory else coverage_errors(report, resources)
    if args.check:
        frozen = json.loads(args.report.read_text(encoding='utf-8'))
        if frozen != report:
            errors.append('Frozen coverage report differs from current resources')
    else:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_bytes(canonical(report))
    if errors:
        raise SystemExit('\n'.join(errors))
    if args.inventory:
        print(f"Inventoried {len(report['programs'])} programs and {len(report['compositions'])} compositions; full extraction complete={report['full_extraction_complete']}")
        return
    print(f"{report['scope']['milestone_id']}: {len(report['cases'])} complete cases; "
          f"{report['outside_scope']['program_count']} outside-scope programs and "
          f"{report['outside_scope']['composition_count']} compositions")


if __name__ == '__main__':
    main()
