"""The consumer contracts of data release 2.3.0 on (ADR 0054): Program JSON 6.0.0, detailed constructions 5.0.0,
unified constructions 4.0.0 and source model constructions 2.0.0.

`scripts.atlas_exports` derives the schemas here from the previous ones (`--schemas`) and turns each export of a
release in `RELEASES` into its new form after the previous form validated. What changes, each in ADR 0054:

1. **One evidence shape** (section 2). Every evidence row of every family is the row constructions already use:
   `id`, `source_project`, `source_revision`, `source_locator` (`<file path>#<locator>`), `source_file_sha256`,
   `original_value`, `original_unit`, `transformation`, `extraction_date`, `interpretation_note`, plus
   `source_url` where the file has one. A program's `source.evidence` holds every row the document cites, so each
   `evidence_id` resolves in the document; the water-heating stage rows gain their `id`.
2. **Status beside every value that can be null** (section 3). Program loads carry `status` (`known`,
   `unknown`, `filled`), with `reason` (and `reason_id`) when unknown and `filling` (rules, basis, evidence) when
   filled, and `evidence_id`. `nulls` maps the JSON pointer of every null outside `metadata`, `schedules` and
   `source` to its meaning: `unknown` (the source does not give it), `none` (known: there is none) or
   `not_applicable` (the field does not apply), with the reason. `NULLS` is that table, which the guide prints.
3. **The release in construction exports** (section 4): `release` (`atlas-release-<version>`); the old delivery
   labels are renamed (`source.construction_definition_release`, `provenance.construction_delivery_release`) and
   the retired `export_mode` and `source.evidence_view` leave the detailed form.
4. **Window ratios that vary with a dwelling's context** (section 5) are `fenestration.variants` with their
   `applies_with`, in place of `metadata.fenestration`.
5. **The origin of the daylighting fractions** (ADR 0059 section 4, review F5c): `lighting_controls.daylighting_origin`
   says whether the fractions are geometry-derived from a PNNL prototype zone set or a DOE reference scan, which
   prototype climates give them, and which climate's model the evidence row cites (a copy where all agree).

Release 2.4.0 on exports Program JSON **6.1.0** (ADR 0061): 6.0.0 with the optional
`lighting_controls.unoccupied_lighting_cap` (`{rule, evidence_id}`; the rule null where the source model has none, its
reason in `nulls`). `PROGRAM_BY_RELEASE` names each release's Program JSON contract; the construction and building
services contracts of 2.3.0 hold for 2.4.0.
"""
import copy
import fnmatch
import json
import re

from scripts.definition_contract import stable_id
from scripts.iecc_commercial_zones import CITIES

RELEASES = ('2.3.0', '2.4.0')
PROGRAM = ('program-json-v6.schema.json', '6.0.0', 'urn:archetype-atlas:program-json:6.0.0')
PROGRAM_6_1 = ('program-json-v6.1.schema.json', '6.1.0', 'urn:archetype-atlas:program-json:6.1.0')
PROGRAM_BY_RELEASE = {'2.3.0': PROGRAM, '2.4.0': PROGRAM_6_1}
CAP_FIELD = 'unoccupied_lighting_cap'
DETAILED = ('construction-json-v5.schema.json', '5.0.0', 'urn:archetype-atlas:construction-set:5.0.0')
UNIFIED = ('construction-equivalent-v4.schema.json', '4.0.0', 'urn:archetype-atlas:construction-equivalent:4.0.0')
SOURCE_MODEL = ('construction-source-model-v2.schema.json', '2.0.0', 'urn:archetype-atlas:source-model-construction:2.0.0')
RELEASE_LABEL = {'type': 'string', 'pattern': r'^atlas-release-\d+\.\d+\.\d+$'}
ATLAS = 'Energy Archetype Atlas'
SHA = {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}
TEXT = {'type': 'string'}
EVIDENCE = {
    'type': 'object', 'additionalProperties': True,
    'description': 'One evidence row (ADR 0054 section 2), the same in every family: the source project and pinned revision, '
                   'the locator in the file (`<path>#<locator>`) and the file\'s SHA-256 (null for an atlas record or decision '
                   'with no file), the original value and unit, the transformation, the extraction date and the interpretation.',
    'required': ['id', 'source_project', 'source_revision', 'source_locator', 'source_file_sha256', 'original_value',
                 'original_unit', 'transformation', 'extraction_date', 'interpretation_note'],
    'properties': {
        'id': {'type': 'string', 'minLength': 1}, 'source_project': {'type': 'string', 'minLength': 1},
        'source_revision': {'type': 'string', 'minLength': 1}, 'source_locator': {'type': 'string', 'minLength': 1},
        'source_file_sha256': {'anyOf': [SHA, {'type': 'object', 'minProperties': 1, 'additionalProperties': SHA}, {'type': 'null'}]},
        'source_url': TEXT, 'original_value': {},
        'original_unit': {'anyOf': [TEXT, {'type': 'object', 'additionalProperties': TEXT}, {'type': 'null'}]},
        'transformation': TEXT, 'extraction_date': {'type': 'string', 'format': 'date'}, 'interpretation_note': TEXT}}
REASON = {'type': 'string', 'minLength': 1}
NULL_ENTRY = {'type': 'object', 'additionalProperties': False, 'required': ['status', 'reason'],
              'properties': {'status': {'enum': ['unknown', 'none', 'not_applicable']}, 'reason': REASON,
                             'reason_id': {'type': 'string', 'minLength': 1}}}
FILLING = {'type': 'object', 'additionalProperties': False, 'required': ['rules', 'basis', 'evidence_ids'],
           'properties': {'rules': {'type': 'array', 'items': TEXT}, 'basis': TEXT,
                          'evidence_ids': {'type': 'array', 'items': TEXT}}}
LOAD_STATUS = {
    'status': {'enum': ['known', 'unknown', 'filled'],
               'description': 'known: the source value (a source zero included); unknown: the source does not give it (value '
                              'null, with its reason); filled: a stored filling (filled version only).'},
    'reason': REASON, 'reason_id': {'type': 'string', 'minLength': 1}, 'filling': FILLING,
    'evidence_id': {'type': 'string', 'minLength': 1}}
LOAD_RULES = [{'if': {'properties': {'status': {'const': 'unknown'}}, 'required': ['status']}, 'then': {'required': ['reason']}},
              {'if': {'properties': {'status': {'const': 'filled'}}, 'required': ['status']}, 'then': {'required': ['filling']}}]

ORIGIN_KINDS = {
    'prototype_zone_set': 'geometry-derived from the Daylighting:Controls of the PNNL prototype zones the program was '
                          'extracted from: the floor fraction of those zones with controls and the reference-point fractions '
                          'weighted by zone lighting power, for the prototype geometry',
    'reference_model_scan': 'no DOE Commercial Reference Building model has Daylighting:Controls (every IDF scanned): '
                            'a source zero, independent of geometry and climate'}
DAYLIGHTING_ORIGIN = {
    'type': 'object', 'additionalProperties': False, 'required': ['kind', 'note'],
    'description': 'Where the daylighting fractions come from (6.0.0, ADR 0059 section 4). They are the source model values, '
                   'applied as given (ADR 0046 section 6); this says which source model and climates they are.',
    'properties': {
        'kind': {'enum': sorted(ORIGIN_KINDS),
                 'description': '; '.join(f'{k}: {v}' for k, v in sorted(ORIGIN_KINDS.items()))+'.'},
        'climates': {'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': {'type': 'string', 'minLength': 1},
                     'description': 'The prototype climate zones (of the 19 PNNL prototype locations) whose model gives '
                                    '`daylighting`; the others are in `daylighting_by_climate`.'},
        'cited_climate': {'type': 'string', 'minLength': 1,
                          'description': 'The climate zone of the prototype model the evidence row cites. Where several '
                                         'climates give the same controls it is a copy of them, the first in climate order, '
                                         'not a choice of climate.'},
        'note': {'type': 'string', 'minLength': 1}},
    'allOf': [{'if': {'properties': {'kind': {'const': 'prototype_zone_set'}}},
               'then': {'required': ['climates', 'cited_climate']}}]}
CITED_CLIMATE = re.compile(r'climate zone \S+ \((\w+)\)')
POSITIVE = {'type': 'number', 'exclusiveMinimum': 0}
CAP_RULE = {
    'type': 'object', 'additionalProperties': False,
    'required': ['cap_W_m2', 'lighting_threshold_W_m2', 'source_values', 'condition', 'comparison', 'action', 'calling_point',
                 'zones', 'controlled_zones'],
    'description': 'The PNNL prototype rule (an EMS program per zone, ADR 0060 section 1): at every timestep, in each controlled '
                   'zone, while the condition holds and the zone lighting power per floor area is at least the threshold, the '
                   "zone's lighting power is set to the cap; otherwise the scheduled lighting applies.",
    'properties': {
        'cap_W_m2': {**POSITIVE, 'description': 'The lighting power per zone floor area the zone is set to: 0.02 W/ft2 (0.2153 W/m2).'},
        'lighting_threshold_W_m2': {**POSITIVE, 'description': 'The rule acts only while the zone lighting power (every Lights '
                                    'object of the zone) per floor area is at least this: 0.02 W/ft2 as the program converts it '
                                    '(x 0.093), 0.2151 W/m2.'},
        'source_values': {'type': 'object', 'additionalProperties': False,
                          'required': ['cap', 'threshold', 'unit', 'cap_conversion_m2_per_ft2', 'threshold_conversion_m2_per_ft2'],
                          'description': 'The values as the EMS program writes them.',
                          'properties': {'cap': POSITIVE, 'threshold': POSITIVE, 'unit': {'const': 'W/ft2'},
                                         'cap_conversion_m2_per_ft2': POSITIVE, 'threshold_conversion_m2_per_ft2': POSITIVE}},
        'condition': {'enum': ['zone_occupant_count_zero', 'other_zone_occupant_count_zero'],
                      'description': "zone_occupant_count_zero: the People Occupant Count of the zone's People object is 0. "
                                     'other_zone_occupant_count_zero: the count of the People object of `condition_zone` is 0 '
                                     "(the warehouse storage zones read the office's)."},
        'condition_zone': {'type': 'string', 'minLength': 1, 'description': 'The source zone whose occupant count the rule reads.'},
        'comparison': {'const': 'zone_lighting_power_density_at_least_threshold'},
        'action': {'const': 'set_lights_to_cap', 'description': "The zone's general Lights object is set to the cap."},
        'additional_lighting_when_capped_W_m2': {'type': 'number', 'minimum': 0,
                                                 'description': 'Where present, the additional (display) lighting object is set '
                                                                'to this while the cap acts (the strip mall stores: 0).'},
        'calling_point': {'enum': ['BeginTimestepBeforePredictor', 'AfterPredictorAfterHVACManagers'],
                          'description': 'The EnergyPlus EMS calling point of the programs.'},
        'zones': {'type': 'integer', 'minimum': 1, 'description': 'Source zones the program represents.'},
        'controlled_zones': {'type': 'integer', 'minimum': 1, 'description': 'Of them, the zones with the rule.'},
        'zone_conditions': {'type': 'array', 'minItems': 1, 'items': {
            'type': 'object', 'additionalProperties': False, 'required': ['zone', 'condition'],
            'properties': {'zone': {'type': 'string', 'minLength': 1},
                           'condition': {'type': 'string', 'minLength': 1, 'description': "A further condition of that zone's "
                                         'program, as the EMS writes it (Hour, DaylightSavings and named sensors).'},
                           'sensors': {'type': 'object', 'additionalProperties': {'type': 'string'}}}},
            'description': "Source zones whose program adds a condition (PNNL's own variants, kept as written)."}},
    'allOf': [{'if': {'properties': {'condition': {'const': 'other_zone_occupant_count_zero'}}},
               'then': {'required': ['condition_zone']}}]}
UNOCCUPIED_LIGHTING_CAP = {
    'type': 'object', 'additionalProperties': False, 'required': ['rule', 'evidence_id'],
    'description': 'The unoccupied lighting cap of the source model zones (6.1.0, ADR 0061): `rule` is the rule, or null where '
                   'the complete source model has none in these zones (a source zero; the reason is in `nulls`). '
                   '`evidence_id` cites the EMS programs or the scan that found none.',
    'properties': {'rule': {'anyOf': [CAP_RULE, {'type': 'null'}]}, 'evidence_id': {'type': 'string', 'minLength': 1}}}


def daylighting_origin(controls, rows):
    """The origin label of a known `lighting_controls` block; `rows` holds its evidence rows (shared shape)."""
    row = rows.get(controls.get('evidence_id')) or {}
    if controls['source'] == 'doe_reference':
        scan = row.get('original_value') or {}
        return {'kind': 'reference_model_scan',
                'note': f'No DOE Commercial Reference Building model of this vintage has Daylighting:Controls '
                        f'({scan.get("models_scanned")} IDFs scanned, {scan.get("with_controls")} with controls): '
                        'daylighting is a source zero for any geometry and climate.'}
    found = CITED_CLIMATE.search(row.get('interpretation_note') or '')
    if found is None or found[1] not in CITIES:
        raise ValueError(f'No prototype climate in the daylighting evidence {controls.get("evidence_id")}')
    cited, city = CITIES[found[1]][1], found[1]
    others = set(controls.get('daylighting_by_climate') or {})
    climates = [climate for _, climate in CITIES.values() if climate not in others]
    if cited not in climates:
        raise ValueError(f'Daylighting evidence {controls["evidence_id"]} cites {cited}, a climate with other controls')
    if len(climates) == len(CITIES):
        where = (f'All {len(CITIES)} prototype climates give the same controls for these zones; the evidence cites the '
                 f'climate {cited} ({city}) model as one copy of them, not as a choice of climate.')
    else:
        where = (f'{len(climates)} of the {len(CITIES)} prototype climates give these controls, the evidence citing the '
                 f'climate {cited} ({city}) model as one copy of them; {", ".join(sorted(others))} differ and are in '
                 'daylighting_by_climate, each citing its own model.')
    what = (f'The fractions are {ORIGIN_KINDS["prototype_zone_set"]}.' if controls.get('daylighting') is not None else
            'None of the PNNL prototype zones the program was extracted from has Daylighting:Controls (a source zero for '
            'that zone set).')
    return {'kind': 'prototype_zone_set', 'climates': climates, 'cited_climate': cited, 'note': f'{what} {where}'}


# The meaning of a null, by JSON pointer pattern (`*` one path segment), in order; the first match wins. A null
# with no row stops the export, so the table covers every null a document can hold. Loads and controls take the
# record's status and reason where the record has one (`record`).
NULLS = [
    ('/loads/*/value', 'unknown', 'record', 'The source does not give the magnitude.'),
    ('/shared_services/*/loads/*/value', 'unknown', 'record', 'The source does not give the magnitude.'),
    ('/loads/*/schedule_id', 'unknown', None, 'No schedule: the load\'s magnitude is unknown, or the source gives no schedule for it.'),
    ('/shared_services/*/loads/*/schedule_id', 'unknown', None, 'No schedule: the load\'s magnitude is unknown, or the source gives no schedule for it.'),
    ('/loads/*/heat_fractions/*', 'unknown', None, 'The source gives no heat fraction; the filled version applies the EnergyPlus default.'),
    ('/shared_services/*/loads/*/heat_fractions/*', 'unknown', None, 'The source gives no heat fraction; the filled version applies the EnergyPlus default.'),
    ('/loads/*/*', 'none', None, 'The source object leaves this field blank (no such input).'),
    ('/shared_services/*/loads/*/*', 'none', None, 'The source object leaves this field blank (no such input).'),
    ('/controls/people_radiant_fraction', 'unknown', None, 'The source gives no people radiant fraction; the filled version applies the EnergyPlus default (0.3).'),
    ('/controls/people_sensible_fraction', 'unknown', None, 'The source gives no people sensible fraction; the filled version autocalculates it (EnergyPlus).'),
    ('/controls/heating_enabled', 'unknown', None, 'The source states no conditioning; setpoint schedules, where given, imply it (the filled version resolves it).'),
    ('/controls/cooling_enabled', 'unknown', None, 'The source states no conditioning; setpoint schedules, where given, imply it (the filled version resolves it).'),
    ('/controls/*', 'unknown', 'record', 'The source gives no value for this control.'),
    ('/default_policy_id', 'none', None, 'No default policy: the source version applies none.'),
    ('/fenestration/wwr/*', 'not_applicable', None, 'No exterior wall faces this direction in the program\'s source zones.'),
    ('/fenestration/roof', 'not_applicable', None, 'No exterior roof over the program\'s source zones.'),
    ('/fenestration/value_by_climate/*/wwr/*', 'not_applicable', None, 'No exterior wall faces this direction in the program\'s source zones.'),
    ('/fenestration/value_by_climate/*/roof', 'not_applicable', None, 'No exterior roof over the program\'s source zones.'),
    ('/fenestration/variants/*/wwr/*', 'not_applicable', None, 'No exterior wall faces this direction in the dwelling\'s source zones.'),
    ('/fenestration/variants/*/roof', 'not_applicable', None, 'No exterior roof over the dwelling\'s source zones.'),
    ('/lighting_controls/daylighting', 'none', None, 'A source zero: the complete source model has no daylighting controls in these zones.'),
    ('/lighting_controls/daylighting_by_climate/*', 'none', None, 'A source zero: the complete source model has no daylighting controls in these zones in that climate.'),
    ('/lighting_controls/standards_rule/target_illuminance_setpoint_lux', 'none', None, 'openstudio-standards gives no target; its default of 375 lux applies (space_add_daylighting_controls).'),
    ('/lighting_controls/unoccupied_lighting_cap/rule', 'none', 'record', 'A source zero: the complete source model has no unoccupied lighting cap in these zones.'),
    ('/water_use_gains/*/sensible_fraction', 'unknown', None, 'The source gives no sensible fraction for the water use.'),
    ('/water_use_gains/*/latent_fraction', 'unknown', None, 'The source gives no latent fraction for the water use.'),
    ('/water_heating/*/service_id', 'none', None, 'A draw of the program itself, served by no shared building service.'),
    ('/water_heating/*/draw/value', 'unknown', 'record', 'The source does not give the magnitude.'),
    ('/water_heating/*/draw/heat_fractions/*', 'unknown', None, 'The source gives no heat fraction; the filled version applies the EnergyPlus default.'),
    ('/water_heating/*/draw/*', 'none', None, 'The source object leaves this field blank (no such input).'),
    ('/water_heating/*/*', 'none', None, 'The water heating has no such part.'),
    ('/water_heating/*/stages/*/*', 'none', None, 'The water-heating stage has no such part.'),
    ('/dwelling/climate', 'not_applicable', None, 'A code-prototype dwelling spans climates; entries that depend on climate carry applies_with.'),
    ('/dwelling/vintage', 'not_applicable', None, 'A code-prototype dwelling has a code template, not a stock vintage.'),
    ('/dwelling/*', 'unknown', None, 'The source dwelling records no value for this field.'),
    ('/dwelling/*/*', 'unknown', None, 'The source dwelling records no value for this field.'),
    ('/source_calendar/daylight_saving', 'none', None, 'The source model has no daylight saving period.'),
]


def matches(pointer, pattern):
    return len(pointer.split('/')) == len(pattern.split('/')) and all(
        b == '*' or a == b for a, b in zip(pointer.split('/'), pattern.split('/')))


def meaning(pointer):
    return next(((status, source, text) for pattern, status, source, text in NULLS if matches(pointer, pattern)), None)


EVIDENCE_KEYS = ('conversion_evidence', 'temperature_evidence', 'fuel_evidence', 'evidence')   # evidence rows: their nulls are upstream data


def null_pointers(value, path=''):
    if value is None:
        yield path
    elif isinstance(value, dict):
        for key, item in value.items():
            if key not in EVIDENCE_KEYS:
                yield from null_pointers(item, f'{path}/{key}')
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from null_pointers(item, f'{path}/{index}')


# Evidence -------------------------------------------------------------------------------------------------

def revision(source_file):
    return source_file.get('version') or (f'{source_file["archive_path"]} retrieved {source_file["retrieval_date"]}'
                                          if source_file.get('archive_path') else f'retrieved {source_file["retrieval_date"]}')


def shared_row(eid, row, source_files, release_label):
    """A program-shaped evidence row (`source_file_id`, `locator`, `interpretation`) in the shared shape."""
    source_file = source_files.get(row.get('source_file_id')) if row.get('source_file_id') else None
    out = {'id': eid}
    if source_file:
        out.update(source_project=source_file['project'], source_revision=revision(source_file),
                   source_locator=f'{source_file["path"]}#{row.get("locator") or ""}', source_file_sha256=source_file['sha256'])
        if source_file.get('url'):
            out['source_url'] = source_file['url']
    else:
        out.update(source_project=ATLAS, source_revision=release_label, source_locator=row.get('locator') or 'record',
                   source_file_sha256=None)
    out.update(original_value=copy.deepcopy(row.get('original_value')), original_unit=row.get('original_unit'),
               transformation=row.get('transformation') or '', extraction_date=row['extraction_date'],
               interpretation_note=row.get('interpretation') or '')
    return out


def stage_row(row):
    """A water-heating stage's construction-shaped evidence row, with the `id` the shared shape needs."""
    return {'id': stable_id('evidence', row), **copy.deepcopy(row)}


def cited(value):
    """Evidence IDs a document cites outside its `source` and `metadata` (`evidence_id`, `evidence_ids`, `*_evidence_ids`)."""
    out = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key == 'evidence_id' and isinstance(item, str):
                out.add(item)
            elif key.endswith('evidence_ids') and isinstance(item, (list, dict)):
                out |= {i for i in (item.values() if isinstance(item, dict) else item) if isinstance(i, str)}
            else:
                out |= cited(item)
    elif isinstance(value, list):
        for item in value:
            out |= cited(item)
    return out


# Schemas --------------------------------------------------------------------------------------------------

def program_schema(previous):
    """Program JSON 6.0.0 from 5.4.0."""
    name, version, identity = PROGRAM
    schema = json.loads(json.dumps(previous).replace('urn:archetype-atlas:program-json:5.4.0', identity))
    schema['title'] = f'Self-contained program JSON {version}'
    schema['description'] = (
        'Release 2.3.0 export (ADR 0054). version "source" holds actual values only; version "filled" applies the stored '
        'fillings and the exporter defaults with draw-only water heating. 6.0.0 changes from 5.4.0: evidence rows take the '
        'shape constructions use, with an id, and the document holds every row it cites; loads carry status, reason, filling '
        'and evidence_id; nulls gives the meaning of every null; dwelling window ratios that depend on context are '
        'fenestration.variants; lighting_controls.daylighting_origin labels where the daylighting fractions come from. '
        'Every other 5.4.0 field keeps its meaning.')
    for variant_name in ('source', 'filled'):
        variant = schema['$defs'][variant_name]
        props = variant['properties']
        props['schema_version'] = {'const': version}
        props['source']['properties']['release'] = dict(RELEASE_LABEL)
        variant['$defs']['evidence'] = copy.deepcopy(EVIDENCE)
        props['nulls'] = {'type': 'object', 'propertyNames': {'pattern': '^/'}, 'additionalProperties': NULL_ENTRY,
                          'description': 'The meaning of every null outside metadata, schedules and source, by JSON pointer '
                                         '(ADR 0054 section 3; the consumer guide tabulates the meanings).'}
        variant['required'] = [*variant['required'], 'nulls']
        load = variant['$defs']['load']
        load['properties'].update(copy.deepcopy(LOAD_STATUS))
        load['required'] = [*load.get('required', []), 'status']
        load.setdefault('allOf', []).extend(copy.deepcopy(LOAD_RULES))
        plain = props['fenestration']
        plain_properties = plain['properties']
        variants = {'type': 'object', 'additionalProperties': False, 'required': ['basis', 'variants'],
                    'description': 'Window ratios of a dwelling that depend on its context (climate, foundation): each variant '
                                   'applies with its applies_with, as the dwelling\'s loads do.',
                    'properties': {'basis': plain_properties['basis'],
                                   'variants': {'type': 'array', 'minItems': 2, 'items': {
                                       'type': 'object', 'additionalProperties': False,
                                       'required': ['applies_with', 'wwr', 'roof', 'evidence_id'],
                                       'properties': {'applies_with': {'type': 'object'}, 'wwr': plain_properties['wwr'],
                                                      'roof': plain_properties['roof'], 'evidence_id': plain_properties['evidence_id'],
                                                      'model_count': {'type': 'integer', 'minimum': 1}}}}}}
        props['fenestration'] = {'oneOf': [plain, variants]}
        controls = props['lighting_controls']
        controls['properties']['daylighting_origin'] = copy.deepcopy(DAYLIGHTING_ORIGIN)
        controls['description'] += (' 6.0.0: `daylighting_origin` says where the fractions come from (the prototype zone set '
                                    'and climates, or the reference model scan); the exporter gives it on every known block.')
        if 'water_stage' in variant['$defs']:
            stage = variant['$defs']['water_stage']['properties']
            for key in ('conversion_evidence', 'temperature_evidence', 'fuel_evidence'):
                stage[key] = {'$ref': '#/$defs/evidence'}
    return schema


def program_schema_6_1(previous):
    """Program JSON 6.1.0 from 6.0.0: the optional unoccupied lighting cap (ADR 0061)."""
    name, version, identity = PROGRAM_6_1
    schema = json.loads(json.dumps(previous).replace(PROGRAM[2], identity))
    schema['title'] = f'Self-contained program JSON {version}'
    schema['description'] = (
        'Release 2.4.0 export (ADR 0061). 6.1.0 adds lighting_controls.unoccupied_lighting_cap: the unoccupied lighting cap '
        'rule of the source model zones, or null where they have none, with its evidence. Every 6.0.0 field keeps its meaning. '
        + previous['description'])
    for variant_name in ('source', 'filled'):
        props = schema['$defs'][variant_name]['properties']
        props['schema_version'] = {'const': version}
        controls = props['lighting_controls']
        controls['properties'][CAP_FIELD] = copy.deepcopy(UNOCCUPIED_LIGHTING_CAP)
        controls['description'] += (" 6.1.0: `unoccupied_lighting_cap` gives the source model's unoccupied lighting cap "
                                    '(the rule or null); the exporter gives it on every known block.')
    return schema


def construction_schema(previous, representation):
    """Detailed constructions 5.0.0 from 4.3.0, unified 4.0.0 from 3.1.0."""
    name, version, identity = DETAILED if representation == 'detailed' else UNIFIED
    schema = copy.deepcopy(previous)
    schema['$id'] = identity
    schema['title'] = ('Detailed construction set' if representation == 'detailed' else
                       'Additional building-level equivalent construction') + f' {version}'
    schema['description'] = ('Release 2.3.0 export (ADR 0054). Names its atlas release; evidence rows in the shape every family uses. '
                             + ('5.0.0 changes from 4.3.0: release added; source.definition_release renamed '
                                'source.construction_definition_release; export_mode and source.evidence_view removed.'
                                if representation == 'detailed' else
                                '4.0.0 changes from 3.1.0: release added; provenance.detailed_release renamed '
                                'provenance.construction_delivery_release.'))
    props = schema['properties']
    props['schema_version'] = {'const': version}
    props['release'] = dict(RELEASE_LABEL)
    schema['required'] = [r for r in schema['required'] if r != 'export_mode'] + ['release']
    schema['$defs']['evidence'] = copy.deepcopy(EVIDENCE)
    if representation == 'detailed':
        props.pop('export_mode', None)
        source = schema['$defs']['source']
        source['properties'].pop('evidence_view', None)
        source['properties']['construction_definition_release'] = source['properties'].pop('definition_release')
        source['required'] = ['construction_definition_release' if r == 'definition_release' else r
                              for r in source.get('required', []) if r != 'evidence_view']
    else:
        props['provenance'] = {'type': 'object', 'required': ['construction_delivery_release'],
                               'properties': {'construction_delivery_release': {'type': 'string', 'minLength': 1},
                                              'detailed_release': False}}
    return schema


def source_model_schema(previous):
    """Source model constructions 2.0.0 from 1.0.0: evidence rows in the shared shape, the release by pattern."""
    name, version, identity = SOURCE_MODEL
    schema = copy.deepcopy(previous)
    schema['$id'] = identity
    schema['title'] = f'Source model constructions {version}'
    schema['description'] = ('Release 2.3.0 export (ADR 0054): 1.0.0 with evidence rows in the shape every family uses and '
                             'the release by pattern.')
    schema['properties']['schema_version'] = {'const': version}
    schema['properties']['release'] = dict(RELEASE_LABEL)
    schema['properties']['evidence'] = {'type': 'object', 'additionalProperties': copy.deepcopy(EVIDENCE)}
    return schema


# Documents ------------------------------------------------------------------------------------------------

def construction_document(document, representation, release_label):
    out = {**document, 'schema_version': (DETAILED if representation == 'detailed' else UNIFIED)[1], 'release': release_label}
    if representation == 'detailed':
        out.pop('export_mode', None)
        source = dict(out['source'])
        source.pop('evidence_view', None)
        source['construction_definition_release'] = source.pop('definition_release')
        out['source'] = source
    else:
        provenance = dict(out['provenance'])
        provenance['construction_delivery_release'] = provenance.pop('detailed_release')
        out['provenance'] = provenance
    return out


def source_model_document(document, source_files):
    out = {**document, 'schema_version': SOURCE_MODEL[1]}
    out['evidence'] = {eid: shared_row(eid, row, source_files, document['release']) for eid, row in document['evidence'].items()}
    return out


class ProgramContext:
    """What a 6.0.0 program document needs from the release beyond its 5.4.0 form."""

    def __init__(self, release_label, source_files, reasons, evidence, entries, ordered_evidence_ids, record=None):
        self.release_label = release_label
        self.source_files = source_files      # {source file ID: glossary entry}
        self.reasons = reasons                # {reason ID: text}
        self.evidence = evidence              # {evidence ID: program-shaped row} of the folder
        self.entries = entries                # {demand ID: stored load entry} of the folder
        self.ordered = ordered_evidence_ids   # the IDs of the 5.4.0 source.evidence rows, in order
        self.record = record                  # the stored program (commercial), for control statuses


def load_status(load, entry, filled, aggregation, context):
    """status, reason, filling and evidence_id of one exported load."""
    out = {}
    if entry is not None and entry.get('evidence_id'):
        out['evidence_id'] = entry['evidence_id']
    if load.get('value') is None:
        reason_id = (entry or {}).get('unresolved')
        out['status'] = 'unknown'
        out['reason'] = context.reasons.get(reason_id) or (entry or {}).get('unresolved_reason') or NULLS[0][3]
        if reason_id:
            out['reason_id'] = reason_id
        return out
    fillings = []
    if entry is not None:
        fillings = [entry['filling']] if filled and 'filling' in entry else []
    else:
        group = next((g for g in aggregation if g.get('demand_id') == load.get('demand_id')), None)
        for component in (group or {}).get('components', []):
            member = context.entries.get(component['load'].get('demand_id'))
            if filled and member is not None and 'filling' in member:
                fillings.append(member['filling'])
    if fillings:
        out['status'] = 'filled'
        out['filling'] = {'rules': sorted({r for f in fillings for r in f['rules']}),
                          'basis': ' + '.join(sorted({f['basis'] for f in fillings})),
                          'evidence_ids': sorted({e for f in fillings for e in f.get('evidence', [])})}
    else:
        out['status'] = 'known'
    return out


def contract(release_label):
    """The Program JSON contract (file, version, $id) of a release label such as atlas-release-2.4.0."""
    return PROGRAM_BY_RELEASE[release_label.rsplit('-', 1)[1]]


def program_document(document, version, context):
    """Program JSON 6.0.0 or 6.1.0 (by the release) from a validated 5.4.0 document."""
    out = copy.deepcopy(document)
    out['schema_version'] = contract(context.release_label)[1]
    stored_controls = (context.record or {}).get('lighting_controls') or {}
    if CAP_FIELD in stored_controls:
        if contract(context.release_label) is PROGRAM:
            raise ValueError(f'{out["id"]}: Program JSON 6.0.0 has no {CAP_FIELD}')
        out['lighting_controls'][CAP_FIELD] = copy.deepcopy(stored_controls[CAP_FIELD])
    filled = version == 'filled'
    aggregation = ((out.get('metadata') or {}).get('aggregation') or {}).get('groups', [])
    draws = [w['draw'] for w in out.get('water_heating') or [] if isinstance(w.get('draw'), dict)]
    for load in [*out['loads'], *(l for s in out.get('shared_services') or [] for l in s.get('loads', [])), *draws]:
        load.update(load_status(load, context.entries.get(load.get('demand_id')), filled, aggregation, context))
    for absent in (out.get('metadata') or {}).get('absent_demands', []):
        absent.update(load_status(absent, context.entries.get(absent.get('demand_id')), filled, aggregation, context))
    # Evidence: every row the document cites, in the shared shape, with its id.
    rows = out['source']['evidence']
    if len(rows) != len(context.ordered):
        raise ValueError(f'{out["id"]}: {len(rows)} evidence rows for {len(context.ordered)} evidence IDs')
    shared = {eid: shared_row(eid, row, context.source_files, context.release_label) for eid, row in zip(context.ordered, rows)}
    citing = {**{k: v for k, v in out.items() if k not in ('source', 'metadata')},
              'absent_demands': (out.get('metadata') or {}).get('absent_demands', [])}
    for eid in sorted(cited(citing) - set(shared)):
        if eid not in context.evidence:
            raise ValueError(f'{out["id"]}: cites evidence {eid}, which the release does not hold')
        shared[eid] = shared_row(eid, context.evidence[eid], context.source_files, context.release_label)
    for heating in out.get('water_heating') or []:
        policy = heating.get('delivery_policy')
        if isinstance(policy, dict) and isinstance(policy.get('evidence'), dict):
            policy['evidence'] = stage_row(policy['evidence'])
        for stage in heating.get('stages', []):
            for key in ('conversion_evidence', 'temperature_evidence', 'fuel_evidence'):
                if isinstance(stage.get(key), dict):
                    stage[key] = stage_row(stage[key])
    out['source']['evidence'] = [shared[eid] for eid in sorted(shared)]
    # Dwelling window ratios that depend on the context (ADR 0054 section 5).
    metadata = out.get('metadata') or {}
    fenestration = metadata.pop('fenestration', None)
    if fenestration and 'fenestration' not in out:
        out['fenestration'] = {'basis': 'program_zone_surfaces',
                               'variants': [{'applies_with': f.get('applies_with', {}), 'wwr': f['wwr'], 'roof': f.get('roof'),
                                             'evidence_id': f['evidence_id'], **({'model_count': f['model_count']} if 'model_count' in f else {})}
                                            for f in fenestration]}
        for f in fenestration:
            if f['evidence_id'] not in shared and f['evidence_id'] in context.evidence:
                shared[f['evidence_id']] = shared_row(f['evidence_id'], context.evidence[f['evidence_id']], context.source_files, context.release_label)
        out['source']['evidence'] = [shared[eid] for eid in sorted(shared)]
    controls = out.get('lighting_controls')
    if isinstance(controls, dict) and controls.get('status') == 'known':
        controls['daylighting_origin'] = daylighting_origin(controls, shared)
    out['nulls'] = nulls(out, context)
    return out


def nulls(document, context):
    """{pointer: meaning} of every null outside metadata, schedules and source."""
    out = {}
    parameters = (context.record or {}).get('parameters', {})
    for key in sorted(document):
        if key in ('metadata', 'schedules', 'source', 'nulls'):
            continue
        for pointer in null_pointers(document[key], '/'+key):
            found = meaning(pointer)
            if found is None:
                raise ValueError(f'{document["id"]}: no meaning for the null at {pointer} (atlas_contracts.NULLS)')
            status, source, text = found
            entry = {'status': status, 'reason': text}
            parts = pointer.split('/')
            if source == 'record' and parts[1] in ('loads', 'shared_services', 'water_heating'):
                load = (document['loads'][int(parts[2])] if parts[1] == 'loads' else
                        document['water_heating'][int(parts[2])]['draw'] if parts[1] == 'water_heating' else
                        document['shared_services'][int(parts[2])]['loads'][int(parts[4])])
                entry['reason'] = load.get('reason', text)
                if load.get('reason_id'):
                    entry['reason_id'] = load['reason_id']
            elif source == 'record' and parts[1] == 'lighting_controls':
                eid = document['lighting_controls'][CAP_FIELD]['evidence_id']
                row = next(r for r in document['source']['evidence'] if r['id'] == eid)
                entry['reason'] = row['interpretation_note'] or text
            elif source == 'record' and parts[1] == 'controls':
                parameter = parameters.get(parts[2]) or {}
                if parameter.get('status') == 'known':
                    entry = {'status': 'none', 'reason': 'Known: the source has no such schedule or value for this program.'}
                elif (context.record or {}).get('unresolved', {}).get(parts[2]):
                    reason_id = context.record['unresolved'][parts[2]]
                    entry.update(reason=context.reasons.get(reason_id, text), reason_id=reason_id)
            out[pointer] = entry
    return out


RECORD_NOTE = " (or the record's)"


def guide_table():
    """The null meanings as the consumer guide prints them (Markdown rows)."""
    rows = ['| JSON pointer (`*` one segment) | Meaning of null | Reason |', '| --- | --- | --- |']
    for pattern, status, source, text in NULLS:
        rows.append(f'| `{pattern}` | `{status}`{RECORD_NOTE if source else ""} | {text} |')
    return '\n'.join(rows)
