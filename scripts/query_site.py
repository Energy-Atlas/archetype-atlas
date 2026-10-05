"""Publish generic machine artifacts and executable consumer examples with MkDocs."""
from pathlib import Path

from scripts.common import ROOT
from scripts.query_delivery import frozen_inputs, generate_delivery, json_bytes, validate_delivery
from scripts.query_client import QueryClient
from scripts.query_history import restore_history, export_history

EXAMPLES = {
    'medium-office-source': {
        'record_type': 'program', 'where': {'building_type': 'MediumOffice', 'program': 'office',
                                          'template': '90.1-2013', 'source_family': 'code_prototype_rules'},
        'fields': ['people_per_m2', 'lighting_W_m2', 'electric_equipment_W_m2', 'ventilation_m3_s_m2',
                   'gas_equipment_W_m2', 'occupancy_schedule_id', 'heating_setpoint_schedule_id']},
    'medium-office-reviewed': {
        'record_type': 'program', 'view': 'reviewed',
        'where': {'building_type': 'MediumOffice', 'program': 'office', 'template': '90.1-2013'},
        'fields': ['gas_equipment_W_m2', 'gas_equipment_schedule_id', 'infiltration_m3_s_m2']},
    'apartment-variants': {
        'record_type': 'program', 'where': {'building_type': 'HighriseApartment', 'program': 'apartment_unit',
                                          'template': '90.1-2013'}, 'fields': ['variant', 'lighting_W_m2']},
    'climate-envelope': {
        'record_type': 'envelope_component',
        'where': {'template': '90.1-2013', 'climate_zone_set': 'ClimateZone 5',
                  'surface_type': 'ExteriorRoof', 'building_category': 'Nonresidential'},
        'fields': ['construction_type', 'u_W_m2_K', 'value_basis']},
    'climate-subzone-absent': {
        'record_type': 'envelope_component',
        'where': {'template': '90.1-2013', 'climate_zone_set': 'ClimateZone 5A'},
        'fields': ['construction_type', 'u_W_m2_K', 'value_basis']},
    'no-match': {'record_type': 'program', 'where': {'building_type': 'UnsupportedBuilding'},
                 'fields': ['lighting_W_m2']},
    'water-attribution': {
        'record_type': 'water_reporting', 'where': {'building_type': 'MediumOffice', 'template': '90.1-2013'},
        'fields': ['local_draw_status', 'reporting_status', 'reporting_schedule_id', 'building_service_path_ids']},
    'residential-profile': {
        'record_type': 'residential_archetype', 'view': 'reviewed',
        'where': {'id': 'residential_archetype-0157cd8578ba44bf8a77'},
        'fields': ['occupants', 'reported_climate_zone', 'stock_vintage', 'profile:occupants']},
}


def publish_query_delivery(site_root, inputs=None, history=None):
    """Use verified frozen inputs, not catalogue presentation JSON, as the source."""
    data, deps, supplement, reporting, profiles, notices, completion = inputs or frozen_inputs()
    target = Path(site_root)/'delivery/v1'
    if history is not None and (Path(history)/'latest.json').exists():
        restore_history(history, target)
    manifest = generate_delivery(target, data, deps, supplement, reporting, profiles, notices, completion)
    client = QueryClient(target)
    directory = target/'examples'; directory.mkdir(exist_ok=True)
    cases = []
    for name, request in EXAMPLES.items():
        # A pilot may omit whole domains; retain only executable cases for that pilot.
        if request['record_type'] not in manifest['record_types']:
            continue
        if not set(request['fields']) <= set(manifest['record_types'][request['record_type']]['fields']):
            continue
        response = client.query(request)
        (directory/(name + '.request.json')).write_bytes(json_bytes(request))
        (directory/(name + '.response.json')).write_bytes(json_bytes(response))
        cases.append({'name': name, 'request': request, 'response': response})
    (directory/'manifest-reference.json').write_bytes(json_bytes(client.manifest_ref))
    (directory/'conformance.json').write_bytes(json_bytes({'schema_version': '1.0.0',
                                                        'manifest': client.manifest_ref, 'cases': cases}))
    export_history(target)
    errors = validate_delivery(target)
    if errors:
        raise ValueError('Published query delivery invalid: ' + '; '.join(errors))
    sizes = [p.stat().st_size for p in target.rglob('*') if p.is_file()]
    return {'snapshot_id': manifest['snapshot_id'], 'program_count': manifest['record_types']['program']['record_count'],
            'files': len(sizes), 'size_bytes': sum(sizes), 'conformance_cases': len(cases)}
