"""Consumer exports from the ADR 0036 release folder.

Program JSON 5.0.0 has two versions: `source` (actual values only; the earlier
raw connector form) and `filled` (fillings and approved defaults applied; the
earlier ready form with water heating folded in). Construction sets export as
detailed 4.0.0 and unified 3.0.0. Every export carries the release's readable
IDs. The program documents come from the existing exporters run over records
rebuilt from the release, so their physics and policies are unchanged.

Release 1.1.0 (the DOE reference reconciliation, ADR 0037) exports the additive
minors Program JSON 5.1.0 and constructions 4.1.0 / 3.1.0, and building services
1.0.0 per folder: `Release(release='1.1.0')`; release 1.2.0 adds the construction-only folders' programs (ADR 0039).
Release 1.3.0 adds the IECC commercial family (ADR 0040) and exports Program JSON 5.2.0
(loads by climate, source zones) and detailed constructions 4.2.0 (the source design-flow
infiltration method); the IECC sets have no unified representation yet.
Release 1.4.0 holds release 1.3.0 and adds the residential tree (ADR 0038): dwelling
programs export as Program JSON 5.3.0 (scripts.residential_exports) and IDF-derived construction sets as source
model constructions 1.0.0 (scripts.prototype_dwellings).
Release 1.5.0 adds the lighting controls (ADR 0044): every program exports as Program JSON 5.4.0, 5.3.0
with `lighting_controls` on commercial programs. Release 1.6.0 adds the unified constructions of the IECC
commercial sets (ADR 0045), exported as construction-equivalent 3.1.0. Release 2.0.0 is the full snapshot of
1.6.0 (ADR 0046) and exports as 1.6.0 does.

Only release 2.0.0 is in the tree (ADR 0046 section 7); releases 1.0.0 to 1.6.0 are read from the tag
`frozen-data-2026-10-27`. The release enums of the schemas keep every release.

python -m scripts.atlas_exports --schemas                 # write the derived schemas
python -m scripts.atlas_exports --program ID --version filled
python -m scripts.atlas_exports --construction SET --context KEY --representation detailed
python -m scripts.atlas_exports --building-services doe-ref-1980-2004/hospital
python -m scripts.atlas_exports --program resstock-sdr.single-family-detached.<...> --version filled
"""
import argparse
import contextlib
import copy
import json
import sys

from jsonschema import Draft202012Validator

from scripts import atlas_constructions, atlas_programs
from scripts.atlas_format import h6, slug, suite_bytes
from scripts.common import ROOT, load_json

RELEASE = 'atlas-release-1.0.0'
SCHEMAS = ROOT/'schemas'
PROGRAM_SCHEMA = 'program-json-v5.schema.json'
MINOR = {'releases': ('1.1.0', '1.2.0', '1.3.0', '1.4.0', '1.5.0', '1.6.0', '2.0.0'), 'program': ('program-json-v5.1.schema.json', '5.1.0'),
         'detailed': ('construction-json-v4.1.schema.json', '4.1.0', 'urn:archetype-atlas:construction-set:4.1.0'),
         'unified': ('construction-equivalent-v3.1.schema.json', '3.1.0', 'urn:archetype-atlas:construction-equivalent:3.1.0'),
         'services': ('building-services-v1.schema.json', '1.0.0')}
HUMIDITY = ('humidifying_setpoint_schedule_id', 'dehumidifying_setpoint_schedule_id')
# Release 1.3.0, the IECC commercial family (ADR 0040): additive minors over 5.1.0 and 4.1.0.
IECC = {'releases': ('1.3.0', '1.4.0', '1.5.0', '1.6.0', '2.0.0'), 'program': ('program-json-v5.2.schema.json', '5.2.0'),
        'detailed': ('construction-json-v4.2.schema.json', '4.2.0', 'urn:archetype-atlas:construction-set:4.2.0')}
# Release 1.5.0, the lighting controls (ADR 0044): Program JSON 5.4.0, an additive minor over 5.3.0, for every program.
LIGHTING = {'releases': ('1.5.0', '1.6.0', '2.0.0'), 'program': ('program-json-v5.4.schema.json', '5.4.0')}
# Release 2.0.0, milestone B (ADR 0046 section 9): detailed constructions 4.3.0, 4.2.0 with the PNNL prototype alternates.
ALTERNATES = {'releases': ('2.0.0',),
              'detailed': ('construction-json-v4.3.schema.json', '4.3.0', 'urn:archetype-atlas:construction-set:4.3.0')}
# The shared mass-accounting contract 1.1.0: 1.0.0 with the internal-mass evidence that 4.1.0 / 3.1.0 embed.
MASS = ('construction-mass-accounting-v1.1.schema.json', '1.1.0', 'urn:archetype-atlas:construction-mass-accounting:1.1.0')
ROLES = ('ExteriorWall','ExteriorRoof', 'ExteriorFloor', 'GroundFloor', 'ExteriorWindow', 'Skylight', 'ExteriorDoor', 'GlassDoor')
# Inputs a full snapshot carries so that its exports read no frozen folder (ADR 0046).
EXPORTER_INPUTS = 'exporter-inputs.json'
SOURCE_METHOD = 'source_design_flow'
NATURAL_ACH = ('fixed_source_reference_natural_ach', 'fixed_source_annual_average_natural_ach')
CONSTRUCTION_SCHEMAS = {'detailed': ('construction-json-v4.schema.json', 'construction-json-v3.schema.json', '4.0.0',
                                     'urn:archetype-atlas:construction-set:4.0.0'),
                        'unified': ('construction-equivalent-v3.schema.json', 'construction-equivalent-v2.schema.json', '3.0.0',
                                    'urn:archetype-atlas:construction-equivalent:3.0.0')}
VERSIONS = ('source', 'filled')


def program_variant(base, version):
    """A Program 5.0.0 variant: `version` replaces `export_mode`, the release replaces the definition view."""
    schema = copy.deepcopy(base)
    for key in ('$schema', 'title', 'description'):
        schema.pop(key, None)
    schema['$id'] = f'urn:archetype-atlas:program-json:5.0.0:{version}'
    props = schema['properties']
    props['schema_version'] = {'const': '5.0.0'}
    props.pop('export_mode')
    props['version'] = {'const': version}
    schema['required'] = ['version' if r == 'export_mode' else r for r in schema['required']]
    source = props['source']
    for key in ('definition_release', 'evidence_view'):
        source['properties'].pop(key)
    source['properties']['release'] = {'const': RELEASE}
    source['required'] = [r for r in source['required'] if r not in ('definition_release', 'evidence_view')] + ['release']
    # The earlier schemas switch the ready rules on export_mode; a version is always one or the other.
    switch = [c for c in schema.get('allOf', []) if 'if' in c]
    schema['allOf'] = [c for c in schema.get('allOf', []) if 'if' not in c] + ([c['then'] for c in switch] if version == 'filled' else [])
    if not schema['allOf']:
        schema.pop('allOf')
    return schema


def derived_schemas():
    """The new majors, derived from the previous ones so the physics rules cannot drift."""
    v3, v4 = load_json(SCHEMAS/'program-json-v3.schema.json'), load_json(SCHEMAS/'program-json-v4.schema.json')
    out = {PROGRAM_SCHEMA: {
        '$schema': 'https://json-schema.org/draft/2020-12/schema', '$id': 'urn:archetype-atlas:program-json:5.0.0',
        'title': 'Self-contained program JSON 5.0.0',
        'description': 'ADR 0036 release export. version "source" holds actual values only (the 3.0.0 raw form); '
                       'version "filled" applies fillings and approved defaults with draw-only water heating (the 4.0.0 form).',
        'oneOf': [{'$ref': 'urn:archetype-atlas:program-json:5.0.0:'+v} for v in VERSIONS],
        '$defs': {'source': program_variant(v3, 'source'), 'filled': program_variant(v4, 'filled')}}}
    for name, previous, version, identity in CONSTRUCTION_SCHEMAS.values():
        schema = load_json(SCHEMAS/previous)
        schema['$id'] = identity
        schema['title'] = f'{schema["title"]} (release major {version})'
        schema['properties']['schema_version'] = {'const': version}
        out[name] = schema
    out[MINOR['program'][0]] = program_minor(out[PROGRAM_SCHEMA])
    for representation, (name, _, version, _) in CONSTRUCTION_SCHEMAS.items():
        out[MINOR[representation][0]] = construction_minor(out[name], representation)
    out[MINOR['services'][0]] = services_schema()
    out[IECC['program'][0]] = program_minor_iecc(out[MINOR['program'][0]])
    out[IECC['detailed'][0]] = construction_minor_iecc(out[MINOR['detailed'][0]])
    out[ALTERNATES['detailed'][0]] = construction_minor_alternates(out[IECC['detailed'][0]])
    out[MASS[0]] = mass_accounting_minor(out[ALTERNATES['detailed'][0]])
    from scripts import prototype_dwellings, residential_exports
    out[residential_exports.PROGRAM_MINOR[0]] = residential_exports.program_schema(out[IECC['program'][0]])
    out[prototype_dwellings.CONSTRUCTION_SCHEMA[0]] = source_model_schema()
    out[LIGHTING['program'][0]] = program_minor_lighting(out[residential_exports.PROGRAM_MINOR[0]])
    return out


def source_model_schema(frozen=None):
    """Source model constructions 1.0.0, its release enum extended to the later releases (additive)."""
    from scripts import prototype_dwellings
    schema = (frozen or prototype_dwellings.construction_schema)()
    schema['properties']['release']['enum'] += [f'atlas-release-{r}' for r in LIGHTING['releases']]
    return schema


RATIO = {'type': 'number', 'minimum': 0, 'maximum': 1}
DAYLIGHTING = {
    'type': 'object', 'additionalProperties': False,
    'required': ['controlled_floor_fraction', 'controlled_lighting_fraction', 'controlled_zones', 'zones', 'illuminance_setpoint_lux',
                 'control_type', 'method', 'availability', 'minimum_input_power_fraction', 'minimum_light_output_fraction',
                 'stepped_control_steps'],
    'description': 'The Daylighting:Controls of the source model zones the program represents (ADR 0044). The fractions are '
                   'the source model values and are applied as given (release 2.0.0, ADR 0046 section 6); the settings are '
                   'those of the zone with the most lighting power.',
    'properties': {
        'controlled_floor_fraction': {**RATIO, 'description': 'Floor area of the zones with controls over the program floor area.'},
        'controlled_lighting_fraction': {**RATIO, 'description': 'Fraction of the program lighting power the reference points control.'},
        'controlled_zones': {'type': 'integer', 'minimum': 1}, 'zones': {'type': 'integer', 'minimum': 1},
        'illuminance_setpoint_lux': {'type': 'number', 'exclusiveMinimum': 0},
        'control_type': {'enum': ['continuous', 'stepped', 'continuous_off']}, 'method': {'enum': ['split_flux', 'delight']},
        'availability': {'enum': ['all_days_except_design_days']},
        'minimum_input_power_fraction': RATIO, 'minimum_light_output_fraction': RATIO,
        'stepped_control_steps': {'type': 'integer', 'minimum': 1},
        'settings_conflict': {'type': 'boolean', 'description': 'Zones of the program differ in their settings.'}}}
LIGHTING_CONTROLS = {
    'type': 'object', 'additionalProperties': False, 'required': ['status', 'source'],
    'description': 'Lighting controls of the program (ADR 0044). `daylighting` null is a source zero: the complete source model '
                   'has no daylighting controls in these zones. Occupancy-sensor credits are inside the lighting schedule.',
    'properties': {
        'status': {'enum': ['known', 'unknown']}, 'source': {'enum': ['pnnl_prototype', 'doe_reference']},
        'geometry_dependent': {'type': 'boolean'}, 'daylighting': {'anyOf': [DAYLIGHTING, {'type': 'null'}]},
        'daylighting_by_climate': {'type': 'object', 'propertyNames': {'pattern': '^[0-8][A-C]$'},
                                   'additionalProperties': {'anyOf': [DAYLIGHTING, {'type': 'null'}]},
                                   'description': 'Daylighting for the climate zones where the source differs from `daylighting`.'},
        'climate_evidence_ids': {'type': 'object', 'additionalProperties': {'type': 'string', 'minLength': 1}},
        'evidence_id': {'type': 'string', 'minLength': 1}, 'reason': {'type': 'string', 'minLength': 1},
        'standards_rule': {'type': 'object', 'additionalProperties': False,
                           'required': ['target_illuminance_setpoint_lux', 'daylighting_appropriate', 'evidence_id'],
                           'description': 'The openstudio-standards space-type daylighting inputs (90.1 templates).',
                           'properties': {'target_illuminance_setpoint_lux': {'anyOf': [{'type': 'number'}, {'type': 'null'}]},
                                          'daylighting_appropriate': {'type': 'boolean'},
                                          'primary_sidelit_nongeometry_fraction': RATIO,
                                          'secondary_sidelit_nongeometry_fraction': RATIO,
                                          'evidence_id': {'type': 'string', 'minLength': 1}}}},
    'allOf': [{'if': {'properties': {'status': {'const': 'known'}}},
               'then': {'required': ['daylighting', 'evidence_id']}, 'else': {'required': ['reason']}}]}


@contextlib.contextmanager
def later_residential(release):
    """Release 1.5.0 on, the residential exporters, which release 1.4.0 pins, write Program JSON 5.4.0 and
    accept the later releases in source model constructions, for the length of one export."""
    if release not in LIGHTING['releases']:
        yield
        return
    from scripts import prototype_dwellings, residential_exports
    saved = residential_exports.PROGRAM_MINOR, prototype_dwellings.construction_schema
    residential_exports.PROGRAM_MINOR = LIGHTING['program']
    prototype_dwellings.construction_schema = lambda: source_model_schema(saved[1])
    try:
        yield
    finally:
        residential_exports.PROGRAM_MINOR, prototype_dwellings.construction_schema = saved


def program_minor_lighting(minor):
    """Program JSON 5.4.0: 5.3.0 with the lighting controls (ADR 0044), optional."""
    schema = json.loads(json.dumps(minor).replace('urn:archetype-atlas:program-json:5.3.0', 'urn:archetype-atlas:program-json:5.4.0'))
    schema['title'] = 'Self-contained program JSON 5.4.0'
    schema['description'] += (' 5.4.0 (release 1.5.0, ADR 0044) adds lighting_controls: the daylighting controls of the source '
                              'model zones, by climate where they differ; every 5.3.0 field keeps its meaning.')
    for version in VERSIONS:
        variant = schema['$defs'][version]
        variant['properties']['schema_version'] = {'const': LIGHTING['program'][1]}
        variant['properties']['source']['properties']['release'] = {'enum': [f'atlas-release-{r}' for r in LIGHTING['releases']]}
        variant['properties']['lighting_controls'] = copy.deepcopy(LIGHTING_CONTROLS)
    return schema


NULLABLE_RATIO = {'anyOf': [{'type': 'number', 'minimum': 0, 'maximum': 1}, {'type': 'null'}]}
RATIOS = {'type': 'object', 'additionalProperties': False, 'required': ['N', 'E', 'S', 'W', 'roof'],
          'properties': {d: NULLABLE_RATIO for d in ('N', 'E', 'S', 'W', 'roof')}}
CALENDAR = {'type': 'object', 'additionalProperties': False, 'required': ['holidays', 'daylight_saving', 'evidence_id'],
            'description': 'The source model calendar (ADR 0037): holiday rules to resolve per year, and daylight saving recorded, not applied.',
            'properties': {'holidays': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False, 'required': ['name', 'rule'],
                                                                   'properties': {'name': {'type': 'string'}, 'rule': {'type': 'string'}}}},
                           'daylight_saving': {'anyOf': [{'type': 'null'}, {'type': 'object', 'additionalProperties': False,
                                                                            'required': ['start', 'end', 'applied'],
                                                                            'properties': {'start': {'type': 'string'}, 'end': {'type': 'string'},
                                                                                           'applied': {'const': False}}}]},
                           'evidence_id': {'type': 'string', 'minLength': 1}}}


def program_minor(major):
    """Program JSON 5.1.0: 5.0.0 with the ADR 0037 fields, all optional."""
    schema = json.loads(json.dumps(major).replace('urn:archetype-atlas:program-json:5.0.0', 'urn:archetype-atlas:program-json:5.1.0'))
    schema['title'] = 'Self-contained program JSON 5.1.0'
    schema['description'] += (' 5.1.0 (release 1.1.0) adds window ratios, the source calendar, source spaces, humidity controls, '
                              'alternates, water-use zone gains and building-service IDs; every 5.0.0 field keeps its meaning.')
    spaces = {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False, 'required': ['name', 'floor_area_m2', 'multiplier'],
                                         'properties': {'name': {'type': 'string'}, 'floor_area_m2': {'type': 'number', 'minimum': 0},
                                                        'multiplier': {'type': 'integer', 'minimum': 1}}}}
    added = {
        'fenestration': {'type': 'object', 'additionalProperties': False, 'required': ['basis', 'wwr', 'roof', 'evidence_id'],
                         'description': 'Window over exterior wall area of the program zones by direction; roof is skylight over roof area. '
                                        'null: no exterior surface in that direction; 0: wall without window.',
                         'properties': {'basis': {'const': 'program_zone_surfaces'}, 'roof': NULLABLE_RATIO,
                                        'wwr': {'type': 'object', 'additionalProperties': False, 'required': ['N', 'E', 'S', 'W'],
                                                'properties': {d: NULLABLE_RATIO for d in 'NESW'}},
                                        'evidence_id': {'type': 'string', 'minLength': 1}}},
        'source_calendar': CALENDAR,
        'source_spaces': {**spaces, 'description': 'Source spaces this program represents where it is not their tagged space type.'},
        'excluded_source_spaces': {'type': 'array', 'items': {'type': 'string'},
                                   'description': 'Source spaces of this space type that another program represents.'},
        'alternates': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False,
                                                  'required': ['quantity', 'source_family', 'evidence_id', 'reason_id'],
                                                  'properties': {'quantity': {'type': 'string'}, 'value': {'type': 'number'},
                                                                 'schedule_id': {'type': 'string'}, 'source_family': {'type': 'string'},
                                                                 'evidence_id': {'type': 'string'}, 'reason_id': {'type': 'string'}}},
                       'description': 'Second backed values where two sources disagree; the primary value is unchanged.'},
        'water_use_gains': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False,
                                                       'required': ['demand_id', 'zone_gains', 'sensible_fraction', 'latent_fraction', 'semantics'],
                                                       'properties': {'demand_id': {'type': 'string'}, 'zone_gains': {'const': 'applied'},
                                                                      'sensible_fraction': NULLABLE_RATIO, 'latent_fraction': NULLABLE_RATIO,
                                                                      'semantics': {'type': 'string'}, 'zone_heat_assignment': {'type': 'string'},
                                                                      'evidence_id': {'type': 'string'}}},
                            'description': 'EnergyPlus WaterUse:Equipment gains of this program\'s hot-water demands: sensible = fraction x '
                                           'mass flow x cp x (mixed - zone air temperature); latent = fraction of the evaporable water.'},
        'building_service_ids': {'type': 'array', 'items': {'type': 'string'},
                                 'description': 'Building services (building services 1.0.0) whose source objects sit in this program\'s zones.'}}
    for version in VERSIONS:
        variant = schema['$defs'][version]
        variant['properties']['schema_version'] = {'const': '5.1.0'}
        variant['properties']['source']['properties']['release'] = {'enum': [f'atlas-release-{r}' for r in MINOR['releases']]}
        variant['properties'].update(copy.deepcopy(added))
        controls = variant['$defs']['controls']['properties']
        for field in HUMIDITY:
            controls[field] = {'anyOf': [{'minLength': 1, 'type': 'string'}, {'type': 'null'}]}
        ruleset = variant['$defs']['ruleset']
        ruleset['properties']['unit']['enum'].append('%')  # relative humidity setpoints
        percent = {'items': {'maximum': 100, 'minimum': 0, 'type': 'number'}, 'type': 'array'}
        ruleset['allOf'].append({'if': {'properties': {'unit': {'const': '%'}}, 'required': ['unit']},
                                 'then': {'properties': {'rules': {'items': {'properties': {'values': percent}}}, 'values': percent}}})
    return schema


def construction_minor(major, representation):
    """Constructions 4.1.0 / 3.1.0: the majors with building window ratios, the DOE design-flow
    infiltration method and evidence on internal-mass entries, all optional."""
    name, version, identity = MINOR[representation]
    schema = copy.deepcopy(major)
    schema['$id'] = identity
    schema['title'] = schema['title'].replace('(release major', '(release minor').rsplit('(', 1)[0] + f'(release minor {version})'
    schema['properties']['schema_version'] = {'const': version}
    schema['properties']['fenestration_defaults'] = {
        'type': 'object', 'additionalProperties': False, 'required': ['conditioned', 'unconditioned', 'all', 'basis', 'evidence_id'],
        'description': 'Whole-building window over exterior wall area by direction (roof: skylight over roof) for conditioned, '
                       'unconditioned and all zone surfaces of the source model.',
        'properties': {'conditioned': RATIOS, 'unconditioned': RATIOS, 'all': RATIOS,
                       'basis': {'const': 'whole_building_zone_surfaces'}, 'evidence_id': {'type': 'string', 'minLength': 1}}}
    design_flow = {'type': 'object', 'additionalProperties': False, 'required': ['zone_rules', 'excluded_zones', 'evidence_id'],
                   'properties': {'zone_rules': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False,
                                                                            'required': ['method', 'value', 'unit', 'coefficients', 'schedule', 'zones'],
                                                                            'properties': {'method': {'type': 'string'}, 'value': {'type': 'number', 'minimum': 0},
                                                                                           'unit': {'type': 'string'}, 'coefficients': {'type': 'array', 'items': {'type': 'number'}},
                                                                                           'schedule': {'type': 'object'}, 'zones': {'type': 'array', 'items': {'type': 'string'}}}}},
                                  'excluded_zones': {'type': 'array', 'items': {'type': 'string'}},
                                  'evidence_id': {'type': 'string'}, 'consumer_inputs': {'type': 'string'}}}
    infiltration = schema['$defs'].get('infiltration')
    if infiltration and 'properties' in infiltration:
        infiltration['properties']['default_method'] = copy.deepcopy(infiltration['properties']['method'])
        infiltration['properties']['methods'] = {'type': 'object', 'additionalProperties': False,
                                                 'properties': {'doe_design_flow': design_flow}}
    schema['$defs']['massEntry']['properties']['evidence_id'] = {'type': 'string', 'minLength': 1}
    return schema


BY_CLIMATE = {'type': 'object', 'propertyNames': {'pattern': '^[0-8][A-C]$'}, 'additionalProperties': {'type': 'number'},
              'description': 'Values for the climate zones where the source differs from `value` (ADR 0040, plan C6).'}
SCHEDULE_BY_CLIMATE = {'type': 'object', 'propertyNames': {'pattern': '^[0-8][A-C]$'}, 'additionalProperties': {'type': 'string', 'minLength': 1},
                       'description': 'Schedules for the climate zones where a mix\'s trajectory differs from `schedule_id`; each is in `schedules`.'}


def program_minor_iecc(minor):
    """Program JSON 5.2.0: 5.1.0 with loads by climate, the source zones and the PNNL type name, all optional."""
    schema = json.loads(json.dumps(minor).replace('urn:archetype-atlas:program-json:5.1.0', 'urn:archetype-atlas:program-json:5.2.0'))
    schema['title'] = 'Self-contained program JSON 5.2.0'
    schema['description'] += (' 5.2.0 (release 1.3.0, ADR 0040) adds value_by_climate and schedule_id_by_climate on loads, window ratios '
                              'by climate, the source zones and the PNNL type name; every 5.1.0 field keeps its meaning.')
    zones = {'type': 'array', 'description': 'The source model zones this program represents, with floor area (one zone) and multiplier.',
             'items': {'type': 'object', 'additionalProperties': False, 'required': ['name', 'floor_area_m2', 'multiplier', 'counted'],
                       'properties': {'name': {'type': 'string'}, 'floor_area_m2': {'type': 'number', 'minimum': 0},
                                      'multiplier': {'type': 'integer', 'minimum': 1}, 'counted': {'type': 'boolean'}}}}
    ratios = {'type': 'object', 'additionalProperties': False, 'required': ['wwr', 'roof'],
              'properties': {'wwr': {'type': 'object', 'additionalProperties': False, 'required': ['N', 'E', 'S', 'W'],
                                     'properties': {d: NULLABLE_RATIO for d in 'NESW'}}, 'roof': NULLABLE_RATIO}}
    for version in VERSIONS:
        variant = schema['$defs'][version]
        variant['properties']['schema_version'] = {'const': IECC['program'][1]}
        variant['properties']['source']['properties']['release'] = {'enum': [f'atlas-release-{r}' for r in IECC['releases']]}
        variant['properties']['source_zones'] = zones
        variant['properties']['pnnl_building_type'] = {'type': 'string', 'description': 'The PNNL prototype type name (plan C3).'}
        variant['properties']['standards_building_type'] = {'type': 'string'}
        variant['properties']['fenestration']['properties']['value_by_climate'] = {
            'type': 'object', 'propertyNames': {'pattern': '^[0-8][A-C]$'}, 'additionalProperties': ratios,
            'description': 'Window ratios for the climate zones where the source differs (skylights in some zones).'}
        for definition in variant['$defs'].values():
            properties = definition.get('properties', {})
            if 'demand_id' in properties and 'value' in properties:
                properties['value_by_climate'] = copy.deepcopy(BY_CLIMATE)
                properties['schedule_id_by_climate'] = copy.deepcopy(SCHEDULE_BY_CLIMATE)
    return schema


def construction_minor_iecc(minor):
    """Detailed constructions 4.2.0: 4.1.0 with the source design-flow infiltration method, which needs no natural ACH."""
    name, version, identity = IECC['detailed']
    schema = copy.deepcopy(minor)
    schema['$id'] = identity
    schema['title'] = schema['title'].rsplit('(', 1)[0] + f'(release minor {version})'
    schema['properties']['schema_version'] = {'const': version}
    infiltration = schema['$defs']['infiltration']
    for key in ('method', 'default_method'):
        infiltration['properties'][key] = {'enum': [*NATURAL_ACH, SOURCE_METHOD]}
    flow = copy.deepcopy(infiltration['properties']['methods']['properties']['doe_design_flow'])
    flow['description'] = ('The source model\'s ZoneInfiltration:DesignFlowRate rules per zone with their schedules inline '
                           '(ADR 0040 item 7); consumers supply each zone\'s exterior surface or wall area, floor area or volume.')
    infiltration['properties']['methods']['properties'][SOURCE_METHOD] = flow
    infiltration['required'] = [r for r in infiltration['required'] if r != 'natural_ach']
    infiltration['allOf'] = [
        {'if': {'properties': {'method': {'enum': list(NATURAL_ACH)}}}, 'then': {'required': ['natural_ach']}},
        {'if': {'properties': {'method': {'const': SOURCE_METHOD}}},
         'then': {'required': ['methods'], 'properties': {'methods': {'required': [SOURCE_METHOD]}}}}]
    return schema


def mass_accounting_minor(detailed):
    """The standalone mass-accounting contract 1.1.0: its definitions taken from the detailed schema that
    embeds them, so the shared contract and the constructions cannot drift (BEMGen handoff, 2026-10-28)."""
    schema = load_json(SCHEMAS/'construction-mass-accounting-v1.schema.json')
    schema['$id'] = MASS[2]
    schema['title'] = f'{schema["title"]} {MASS[1]}'
    schema['description'] = ('1.0.0 with an optional `evidence_id` on additional-mass entries, as detailed constructions 4.1.0 '
                             'and later and unified constructions 3.1.0 embed it; every 1.0.0 field keeps its meaning.')
    schema['$defs'] = {name: copy.deepcopy(detailed['$defs'][name]) for name in schema['$defs']}
    return schema


def construction_minor_alternates(minor):
    """Detailed constructions 4.3.0: 4.2.0 with `alternates`, the PNNL prototype constructions of a role that differ
    from the openstudio-standards building default by more than 1% (user decision P1)."""
    name, version, identity = ALTERNATES['detailed']
    schema = copy.deepcopy(minor)
    schema['$id'] = identity
    schema['title'] = schema['title'].rsplit('(', 1)[0] + f'(release minor {version})'
    schema['properties']['schema_version'] = {'const': version}
    number = {'type': 'number'}
    variant = {'type': 'object', 'additionalProperties': False,
               'required': ['construction', 'area_share', 'values', 'assembly_id', 'evidence_id'],
               'properties': {'construction': {'type': 'string', 'minLength': 1},
                              'area_share': {'type': 'number', 'exclusiveMinimum': 0, 'maximum': 1},
                              'values': {'type': 'object', 'minProperties': 1, 'additionalProperties': number},
                              'assembly_id': {'type': 'string', 'minLength': 1}, 'evidence_id': {'type': 'string', 'minLength': 1}}}
    schema['properties']['alternates'] = {
        'type': 'object', 'propertyNames': {'enum': list(ROLES)},
        'description': 'PNNL prototype constructions of a component role that differ from the building-default assembly by more '
                       'than 1% in layer resistance (without air films), U-factor, SHGC or F-factor. openstudio-standards stays '
                       'the authority; an alternate is the same edition, type and climate as the PNNL prototype builds it, with '
                       'the share of the role\'s net area each variant covers (ADR 0046 section 9).',
        'additionalProperties': {'type': 'object', 'additionalProperties': False, 'required': ['source', 'atlas_values', 'variants'],
                                 'properties': {'source': {'const': 'pnnl_prototype'},
                                                'atlas_values': {'type': 'object', 'additionalProperties': number},
                                                'variants': {'type': 'array', 'minItems': 1, 'items': variant}}}}
    return schema


def services_schema():
    return {'$schema': 'https://json-schema.org/draft/2020-12/schema', '$id': 'urn:archetype-atlas:building-services:1.0.0',
            'title': 'Building services 1.0.0',
            'description': 'The building-level services of one template x building-type folder (ADR 0037): elevators, exhaust '
                           'fans, exterior lights and equipment, refrigeration cases and racks, each instantiated once, with '
                           'its schedules inlined.',
            'type': 'object', 'additionalProperties': False,
            'required': ['schema_version', 'kind', 'release', 'template', 'building_type', 'services', 'schedules'],
            'properties': {'schema_version': {'const': '1.0.0'}, 'kind': {'const': 'building_services'},
                           'release': {'enum': [f'atlas-release-{r}' for r in MINOR['releases']]}, 'template': {'type': 'string'}, 'building_type': {'type': 'string'},
                           'services': {'type': 'array', 'items': {'type': 'object', 'required': ['id', 'end_use', 'load', 'beneficiary_program_ids']}},
                           'schedules': {'type': 'object'}, 'evidence': {'type': 'object'}}}


def decode(eid, row, glossary):
    """An evidence row with its glossary texts restored to the definition-release shape."""
    if str(row.get('interpretation', '')).startswith('i-') and str(row.get('transformation', '')).startswith('t-'):
        return {'extraction_date': row['extraction_date'], 'id': eid,
                'interpretation': glossary['interpretations'][row['interpretation']], 'locator': row['locator'],
                'original_unit': row['original_unit'], 'original_value': row['original_value'],
                'source_file_id': row['source_file'], 'transformation': glossary['transformations'][row['transformation']]}
    return {**row, 'id': eid}


def constants(record, prefix, schedules):
    """Replace filling constants ({"constant": v}) by schedule records the exporters can read."""
    def schedule(value):
        content = {'calendar_independent': True, 'schedule_type': 'fraction', 'units': 'dimensionless',
                   'time_resolution_minutes': 60, 'source_name': 'filling constant', 'evidence_ids': [],
                   'rules': [{'day_types': 'Default', 'start_date': '2000-01-01', 'end_date': '2000-12-31', 'values': [value]}]}
        sid = f'{prefix}.constant-{slug(str(value))}.{h6(content)}'
        schedules[sid] = {**content, 'id': sid}
        return sid
    def walk(value):
        if isinstance(value, dict):
            if set(value) == {'constant'}:
                return schedule(value['constant'])
            return {k: walk(v) for k, v in value.items()}
        if isinstance(value, list):
            return [walk(v) for v in value]
        return value
    return walk(record)


COURTHOUSE_DESIGN_DAYS = {'Courthouse ' + n for n in (
    'CELL_OCC_SCH', 'COURTROOM_LIGHT_SCH', 'GENERAL_LIGHT_SCH', 'JUDGES_CHAMBER_LIGHT_SCH',
    'JUDGES_CHAMBER_OCC_SCH', 'JURY_ASSEMBLY_LIGHT_SCH', 'JURY_ASSEMBLY_OCC_SCH', 'JURY_DELIBERATION_LIGHT_SCH',
    'JURY_DELIBERATION_OCC_SCH', 'OFFICE_OCC_SCH')}


def complete_design_days(schedule):
    """User-approved completion (ADR 0039 F3) of the Courthouse schedules, which give every weekday,
    weekends and holidays but no Default or design-day rule: design days take the Wednesday profile."""
    if schedule.get('source_name') not in COURTHOUSE_DESIGN_DAYS:
        return
    tokens = [set(r['day_types'].split('|')) for r in schedule['rules']]
    if any(t & {'SmrDsn', 'WntrDsn', 'Default'} for t in tokens):
        return  # this template's variant already covers design days
    weekday = [r for r, t in zip(schedule['rules'], tokens) if t & {'Wed', 'Wkdy'}]
    if not weekday or any(r['start_date'][5:10] != '01-01' or r['end_date'][5:10] != '12-31' for r in weekday):
        raise ValueError('Unexpected weekday rules: '+schedule['source_name'])
    schedule['rules'] = [*schedule['rules'], *({**copy.deepcopy(weekday[-1]), 'day_types': d} for d in ('SmrDsn', 'WntrDsn'))]
    schedule['completion'] = 'accepted-design-day-weekday (ADR 0039 F3): design days take the Wednesday profile'


def complete_holidays(schedule):
    """User-approved completion (ADR 0039, 2026-10-26) of Courthouse BLDG_EQUIP_SCH, which has design days
    but no holiday or Default rule: holidays take the Sunday profile, as accepted-holiday-sunday does."""
    if schedule.get('source_name') != 'Courthouse BLDG_EQUIP_SCH':
        return
    tokens = [set(r['day_types'].split('|')) for r in schedule['rules']]
    if any(t & {'Hol', 'Default'} for t in tokens):
        return  # this template's variant already covers holidays
    sunday = [r for r, t in zip(schedule['rules'], tokens) if t == {'Sun'}]
    if len(sunday) != 1 or sunday[0]['start_date'][5:10] != '01-01' or sunday[0]['end_date'][5:10] != '12-31':
        raise ValueError('Unexpected Sunday rule: '+schedule['source_name'])
    schedule['rules'] = [*schedule['rules'], {**copy.deepcopy(sunday[0]), 'day_types': 'Hol'}]
    schedule['completion'] = 'accepted-holiday-sunday (ADR 0039): holidays take the Sunday profile'


class Release:
    """A written release folder, exported for consumers."""

    def __init__(self, files=None, release='2.0.0'):
        if release not in ('1.0.0', *MINOR['releases']):
            raise ValueError('Unknown release: '+release)
        if files is None and release == '2.0.0':
            from scripts import atlas_snapshot
            files = atlas_snapshot.files()
        elif files is None:
            raise ValueError(f'Release {release} is not in the tree; read it from the tag frozen-data-2026-10-27 (ADR 0046)')
        self.files, self.release = files, release
        self.programs = {}
        for path, data in files.items():
            if '/programs/' in path and path.startswith('commercial/'):
                program = json.loads(data)
                self.programs[program['id']] = (path.split('/programs/')[0]+'/', program)
        self.constructions = atlas_constructions.read_files(files)
        self._suites, self._bundles, self._exporters, self._dwellings = {}, {}, {}, None

    @property
    def dwellings(self):
        """The residential tree (ADR 0038, release 1.4.0 on)."""
        if self._dwellings is None:
            from scripts.residential_exports import Dwellings
            self._dwellings = Dwellings(self.files, self.release)
        return self._dwellings

    def program_ids(self):
        return sorted(self.programs)

    def stored_program(self, program_id):
        return copy.deepcopy(self.programs[program_id][1])

    def suite(self, folder):
        if folder not in self._suites:
            self._suites[folder] = atlas_programs.read_folder({p: d for p, d in self.files.items() if p.startswith(folder)})
        return self._suites[folder]

    def bundle(self, version):
        """Definition-shaped records for every program in one version, with release IDs."""
        if version not in self._bundles:
            glossary = json.loads(self.files['evidence/glossary.json'])
            schedules, programs, compositions = {}, [], []
            for pid, (folder, stored) in sorted(self.programs.items()):
                suite = self.suite(folder)
                for sid in suite.table:
                    schedules.setdefault(sid, {**suite.schedule(sid), 'id': sid})
                record = suite.export(pid, version)
                record = constants(record, '.'.join(pid.split('.')[:2]), schedules)
                record.update(kind='program', evidence_view='source' if version == 'source' else 'reviewed')
                if 'composition' in stored:
                    cid = pid+':composition'
                    record['composition_id'] = cid
                    compositions.append({'id': cid, 'name': record['name'], 'mode': record['detail'],
                                         'building_type': record['building_type'], 'template': record['template'],
                                         'evidence_view': record['evidence_view'], 'method': stored['composition']['method'],
                                         'members': copy.deepcopy(stored['composition']['members'])})
                programs.append(record)
            if version == 'filled' and self.release != '1.0.0':
                for schedule in schedules.values():
                    complete_design_days(schedule)
                    complete_holidays(schedule)
            services = [{**row, 'id': sid} for p, d in sorted(self.files.items()) if p.endswith('/services.json')
                        for sid, row in json.loads(d).items()]
            provenance = [decode(eid, row, glossary) for p, d in sorted(self.files.items())
                          if p.startswith('evidence/') and not p.endswith('glossary.json') for eid, row in json.loads(d).items()]
            self._bundles[version] = {'programs': programs, 'schedules': list(schedules.values()), 'services': services,
                                      'compositions': compositions, 'provenance': provenance, 'schedules_by_id': schedules}
        return self._bundles[version]

    def exporter(self, version):
        if version not in self._exporters:
            inactive = self.exporter_inputs()['inactive_controls'] if self.exporter_inputs() else None
            if version == 'source':
                from scripts.program_json_v3 import ProgramExporter
                self._exporters[version] = ProgramExporter(self.bundle(version), inactive_controls=inactive)
            else:
                from scripts.program_water_heating import ProgramExporter
                services, programs = self.capped()
                self._exporters[version] = ProgramExporter(self.bundle(version), capped_services=services, capped_programs=programs,
                                                           inactive_controls=inactive)
        return self._exporters[version]

    @contextlib.contextmanager
    def carried_inputs(self):
        """Exporters built by the pinned residential modules take this release's exporter inputs, for one export."""
        from scripts import program_json_v3
        saved = program_json_v3.INACTIVE_CONTROLS
        if self.exporter_inputs():
            program_json_v3.INACTIVE_CONTROLS = set(self.exporter_inputs()['inactive_controls'])
        try:
            yield
        finally:
            program_json_v3.INACTIVE_CONTROLS = saved

    def exporter_inputs(self):
        """The exporter inputs a full snapshot carries (ADR 0046), or None for a release that reads them from the frozen folders."""
        data = self.files.get(EXPORTER_INPUTS)
        return json.loads(data) if data is not None else None

    def capped(self):
        """The approved capped-delivery demands (ADR 0018) under release IDs.

        The policy names them by definition-release IDs; services are matched by their water
        path and programs by upstream source ID and name, which the release keeps. A full
        snapshot carries the matched IDs.
        """
        inputs = self.exporter_inputs()
        if inputs is None:
            raise ValueError('Only a full snapshot carries the capped-delivery IDs (exporter-inputs.json, ADR 0046)')
        return set(inputs['capped_services']), set(inputs['capped_programs'])

    def program(self, program_id, version):
        """Program JSON 5.0.0 in one version."""
        if version not in VERSIONS:
            raise ValueError('Unknown program version: '+version)
        if program_id not in self.programs and program_id in self.dwellings.programs:
            with later_residential(self.release), self.carried_inputs():
                return self.dwellings.program(program_id, version)
        if version == 'filled' and str(self.programs[program_id][1].get('template', '')).startswith('IECC '):
            raise ValueError(program_id+': IECC programs export as source only. They hold source values with no fillings, and the '
                             'filled version folds water heating into its source heaters, which are deferred with the systems '
                             '(ADR 0040 item 10).')
        exporter = self.exporter(version)
        document = exporter.export(program_id, 'raw') if version == 'source' else exporter.export(program_id)
        document.pop('export_mode')
        source = document['source']
        for key in ('definition_release', 'evidence_view'):
            source.pop(key)
        source['release'] = RELEASE
        document = {'schema_version': '5.0.0', 'version': version, **{k: v for k, v in document.items() if k != 'schema_version'}}
        document['id'] = program_id
        schema = PROGRAM_SCHEMA
        if self.release != '1.0.0':
            document, schema = self.program_minor(document, program_id, version), MINOR['program'][0]
        if self.release in IECC['releases']:
            document, schema = self.program_iecc(document, program_id, version), IECC['program'][0]
        if self.release in LIGHTING['releases']:
            document, schema = self.program_lighting(document, program_id), LIGHTING['program'][0]
        errors = [e.message for e in validator(schema).iter_errors(document)]
        if errors:
            raise ValueError(program_id+': '+'; '.join(errors[:5]))
        return document

    def program_lighting(self, document, program_id):
        """Program JSON 5.4.0 from a 5.2.0 document: the stored lighting controls (ADR 0044)."""
        document = {**document, 'schema_version': LIGHTING['program'][1]}
        stored = self.programs[program_id][1]
        if 'lighting_controls' in stored:
            document['lighting_controls'] = copy.deepcopy(stored['lighting_controls'])
        return document

    def program_iecc(self, document, program_id, version):
        """Program JSON 5.2.0 from a 5.1.0 document: loads by climate (plan C6), source zones and the PNNL type name."""
        from scripts.schedule_json import normalize_schedule
        folder, stored = self.programs[program_id]
        document = {**document, 'schema_version': IECC['program'][1]}
        for key in ('source_zones', 'pnnl_building_type', 'standards_building_type'):
            if key in stored:
                document[key] = copy.deepcopy(stored[key])
        schedules = self.bundle(version)['schedules_by_id']
        services = self.folder_services(folder)
        variants = {}
        for load in [*self.suite(folder).export(program_id, version)['loads'], *(s['load'] for s in services.values())]:
            for item in [load, *(c['load'] for c in load.get('source_components', []))]:
                if item.get('value_by_climate') or item.get('schedule_id_by_climate'):
                    variants[item['demand_id']] = item
        targets = [*document['loads'], *(l for s in document.get('shared_services') or [] for l in s.get('loads', [])),
                   *(document.get('water_heating') or [])]
        for target in targets:
            variant = variants.get(target.get('demand_id'))
            if not variant:
                continue
            if variant.get('value_by_climate'):
                target['value_by_climate'] = dict(variant['value_by_climate'])
            if variant.get('schedule_id_by_climate'):
                target['schedule_id_by_climate'] = dict(variant['schedule_id_by_climate'])
                for sid in variant['schedule_id_by_climate'].values():
                    document['schedules'][sid] = normalize_schedule(schedules[sid])
        return document

    def folder_services(self, folder):
        return json.loads(self.files.get(folder+'services.json', b'{}'))

    def program_minor(self, document, program_id, version):
        """Program JSON 5.1.0 from a 5.0.0 document and the stored program (ADR 0037 fields)."""
        from scripts.schedule_json import normalize_schedule
        folder, stored = self.programs[program_id]
        exported = self.suite(folder).export(program_id, version)
        schedules = self.bundle(version)['schedules_by_id']
        document = {**document, 'schema_version': MINOR['program'][1]}
        document['source']['release'] = f'atlas-release-{self.release}'
        for key in ('fenestration', 'source_calendar', 'source_spaces', 'excluded_source_spaces'):
            if key in stored:
                document[key] = copy.deepcopy(stored[key])
        for field in HUMIDITY:
            value = exported['parameters'].get(field, {}).get('value')
            if value:
                document['controls'][field] = value
                document['schedules'][value] = normalize_schedule(schedules[value])
        alternates = []
        for load in stored['loads']:
            for alternate in load.get('alternates', []):
                alternates.append({'quantity': load['quantity'], **alternate})
                if 'schedule_id' in alternate:
                    document['schedules'][alternate['schedule_id']] = normalize_schedule(schedules[alternate['schedule_id']])
        if alternates:
            document['alternates'] = alternates
        services = self.folder_services(folder)
        demands = {l['demand_id'] for l in document['loads']} | {w['demand_id'] for w in document.get('water_heating') or []}
        gains = []
        for load in [*stored['loads'], *(s['load'] for s in services.values())]:
            effects = load.get('thermal_effects') or {}
            if load.get('demand_id') in demands and effects.get('zone_gains') == 'applied':
                gains.append({'demand_id': load['demand_id'], 'zone_gains': 'applied', 'semantics': effects['semantics'],
                              'sensible_fraction': effects['sensible_fraction']['value'], 'latent_fraction': effects['latent_fraction']['value'],
                              'zone_heat_assignment': load.get('zone_heat_assignment', 'unresolved'),
                              'evidence_id': effects['sensible_fraction']['evidence_id']})
        if gains:
            document['water_use_gains'] = sorted(gains, key=lambda g: g['demand_id'])
        building = sorted(sid for sid, s in services.items() if program_id in s['beneficiary_program_ids']
                          and s['load'].get('quantity') != 'hot_water_volume')
        if building:
            document['building_service_ids'] = building
        return document

    def building_services(self, folder):
        """Building services 1.0.0 for one folder, e.g. `doe-ref-1980-2004/hospital`."""
        from scripts.schedule_json import normalize_schedule
        if self.release == '1.0.0':
            raise ValueError('Building services are exported from release 1.1.0 on')
        services = self.folder_services(f'commercial/{folder}/')
        suite = self.suite(f'commercial/{folder}/')
        added = {sid: s for sid, s in services.items() if s['load'].get('quantity') != 'hot_water_volume'}
        if not added:
            raise ValueError('No building services in '+folder)
        schedules = {}
        for service in added.values():
            for key in ('schedule_id', 'lighting_schedule_id'):
                sid = service['load'].get(key)
                if sid:
                    schedules[sid] = normalize_schedule({**suite.schedule(sid), 'id': sid})
        evidence = json.loads(self.files[f'evidence/commercial/{folder}.json'])
        first = next(iter(added.values()))
        document = {'schema_version': MINOR['services'][1], 'kind': 'building_services', 'release': f'atlas-release-{self.release}',
                    'template': first['template'], 'building_type': first['building_type'],
                    'services': [{**copy.deepcopy(s), 'id': sid} for sid, s in sorted(added.items())], 'schedules': schedules,
                    'evidence': {e: evidence[e] for s in added.values() for e in s['evidence_ids'] if e in evidence}}
        errors = [e.message for e in validator(MINOR['services'][0]).iter_errors(document)]
        if errors:
            raise ValueError(folder+': '+'; '.join(errors[:5]))
        return document

    def construction(self, set_id, key, representation):
        """Construction detailed 4.0.0 or unified 3.0.0 for one context of a set."""
        name, _, version, _ = CONSTRUCTION_SCHEMAS[representation]
        # IDF-derived dwelling sets live under residential/; commercial IECC sets share the `iecc-` prefix.
        if set_id.startswith(('iecc-', 'hud-code.', 'doe-final-rule.')) and any(
                p.startswith('residential/') and p.endswith(f'/constructions/{set_id}.json') for p in self.files):
            from scripts import prototype_dwellings
            with later_residential(self.release):
                return prototype_dwellings.construction(self, set_id, key)
        if self.release != '1.0.0':
            name, version, _ = MINOR[representation]
        if self.release in IECC['releases'] and representation == 'detailed':
            name, version, _ = IECC['detailed']
        if self.release in ALTERNATES['releases'] and representation == 'detailed':
            name, version, _ = ALTERNATES['detailed']
        document = self.constructions.export(set_id, key, representation)
        if document.get('status') == 'deferred':
            raise ValueError(f'{set_id} {key}: no {representation} representation; {document["reason"]}')
        document['schema_version'] = version
        errors = [e.message for e in validator(name).iter_errors(document)]
        if errors:
            raise ValueError(f'{set_id} {key}: '+'; '.join(errors[:5]))
        return document


_VALIDATORS = {}


def validator(name):
    if name not in _VALIDATORS:
        _VALIDATORS[name] = Draft202012Validator(load_json(SCHEMAS/name))
    return _VALIDATORS[name]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--schemas', action='store_true', help='write the derived schemas')
    parser.add_argument('--check-schemas', action='store_true', help='fail if a committed schema differs from its derivation')
    parser.add_argument('--program')
    parser.add_argument('--version', choices=VERSIONS, default='filled')
    parser.add_argument('--construction')
    parser.add_argument('--context')
    parser.add_argument('--representation', choices=tuple(CONSTRUCTION_SCHEMAS), default='detailed')
    parser.add_argument('--release', choices=('2.0.0',), default='2.0.0')
    parser.add_argument('--building-services', metavar='FOLDER', help='e.g. doe-ref-1980-2004/hospital (release 1.1.0)')
    args = parser.parse_args()
    if args.schemas or args.check_schemas:
        for name, schema in derived_schemas().items():
            path = SCHEMAS/name
            if args.schemas:
                path.write_bytes(suite_bytes(schema))
            elif not path.exists() or load_json(path) != schema:
                raise SystemExit(f'{name} differs from its derivation; run python -m scripts.atlas_exports --schemas')
        print('Program 5.0.0 / 5.1.0 / 5.2.0 / 5.3.0 / 5.4.0, construction 4.0.0 / 4.1.0 / 4.2.0 / 4.3.0 / 3.0.0 / 3.1.0, '
              'source model constructions 1.0.0, mass accounting 1.1.0 and building services 1.0.0 schemas '
              +('written' if args.schemas else 'match their derivation'))
        return
    release = Release(release=args.release)
    if args.building_services:
        document = release.building_services(args.building_services)
    elif args.program:
        document = release.program(args.program, args.version)
    elif args.construction and args.context:
        document = release.construction(args.construction, args.context, args.representation)
    else:
        parser.error('give --schemas, --program, or --construction with --context')
    sys.stdout.write(json.dumps(document, indent=2, ensure_ascii=False)+'\n')


if __name__ == '__main__':
    main()
