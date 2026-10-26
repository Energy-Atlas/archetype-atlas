"""Detailed construction documents of the IECC commercial family (ADR 0040 items 6 to 8).

`Documents(inputs)` turns the envelope payloads of data/program-inputs/iecc-commercial-<edition>.json
into one construction set per edition and type, with one context per location keyed by its
atlas climate (`0-a` ... `8-a`), in the detailed construction contract (4.2.0):
- components from the IDF surfaces, with rules by story position and space type where the
  source varies, and surface-level assignments for the surfaces no rule explains;
- the IDF design-flow infiltration as the source method, schedules inline, no natural ACH;
- the 15 whole-building window ratios;
- the internal mass and the interior wall and floor capacity budgets.
The unified representation is deferred (ADR 0040 item 10): the pair's unified member is a
stub that says so, and the consumer export refuses it.
"""
import copy

from scripts.common import ROOT, load_json
from scripts.definition_contract import stable_id
from scripts.iecc_commercial_zones import EDITIONS, FAMILY, template

INPUT = 'data/program-inputs/iecc-commercial-{}.json'
VERSION = '4.2.0'
METHOD = 'source_design_flow'
GEOMETRY = {'area': {'method': 'bem_surface_area', 'unit': 'm2'},
            'layers': {'orientation': 'exterior_to_interior', 'paired_surface_policy': 'reverse_order', 'source_reference_reversed': False}}
OUT, GROUND, INNER = ['Outdoors'], ['Ground', 'GroundFCfactorMethod', 'Foundation'], ['Surface', 'Adiabatic']
TARGETS = {
    'ExteriorWall': {'boundary_conditions': OUT, 'surface_type': 'Wall'}, 'ExteriorRoof': {'boundary_conditions': OUT, 'surface_type': 'Roof'},
    'ExteriorFloor': {'boundary_conditions': OUT, 'surface_type': 'Floor'}, 'ExteriorWindow': {'boundary_conditions': OUT, 'surface_type': 'Window'},
    'ExteriorDoor': {'boundary_conditions': OUT, 'surface_type': 'Door'}, 'GlassDoor': {'boundary_conditions': OUT, 'surface_type': 'GlassDoor'},
    'OverheadDoor': {'boundary_conditions': OUT, 'surface_type': 'OverheadDoor'}, 'Skylight': {'boundary_conditions': OUT, 'surface_type': 'Skylight'},
    'InteriorWall': {'boundary_conditions': INNER, 'surface_type': 'Wall'}, 'InteriorFloor': {'boundary_conditions': INNER, 'surface_type': 'Floor'},
    'InteriorCeiling': {'boundary_conditions': INNER, 'surface_type': 'Ceiling'}, 'InteriorDoor': {'boundary_conditions': INNER, 'surface_type': 'Door'},
    'InteriorWindow': {'boundary_conditions': INNER, 'surface_type': 'Window'}, 'InteriorPartition': {'object_type': 'InternalMass'},
    'TubularDaylightDome': {'surface_type': 'TubularDaylightDome'}, 'TubularDaylightDiffuser': {'surface_type': 'TubularDaylightDiffuser'},
    'SpaceShading': {'object_type': 'Shading', 'shading_scope': 'space'}, 'BuildingShading': {'object_type': 'Shading', 'shading_scope': 'building'},
    'SiteShading': {'object_type': 'Shading', 'shading_scope': 'site'}, 'GroundFloor': {'boundary_conditions': GROUND, 'surface_type': 'Floor'},
    'FoundationWall': {'boundary_conditions': [*GROUND, 'Surface', 'Adiabatic', 'Outdoors'], 'surface_type': 'Wall'},
    'FloorOverFoundation': {'boundary_conditions': INNER, 'surface_type': 'Floor'},
    'RimJoist': {'boundary_conditions': ['Outdoors', 'Surface', 'Adiabatic'], 'surface_type': 'Wall'}}
FOUNDATION = {'FFactorGroundFloorConstruction': ('FFactor', ['surface_area_m2', 'exposed_perimeter_m']),
              'CFactorUndergroundWallConstruction': ('CFactor', ['surface_area_m2', 'foundation_wall_height_m'])}
REQUIRED = {'surface_area_m2': {'description': 'Actual assigned component surface area', 'exclusive_minimum': 0, 'unit': 'm2'},
            'exposed_perimeter_m': {'description': 'Actual direct-ambient exposed edges; exclude zone edges; zero is supported', 'minimum': 0, 'unit': 'm'},
            'foundation_wall_height_m': {'description': 'Actual underground wall height/depth', 'exclusive_minimum': 0, 'unit': 'm'}}
FC_PARAMETERS = {'model': 'FCBoundary', 'monthly_temperature_input': 'fc_monthly_ground_temperature_C'}
POLICY = {'precedence': 'space_type_then_story_then_building_default', 'source_absent_override': 'inherit_building_default',
          'unmatched_or_ambiguous': 'error', 'variant_resolution': 'explicit_assignment_id_or_unique_compatible_rule'}
MIGRATION = {'physics': 'unchanged', 'review_status': 'design_accepted', 'source_contract': 'construction-json/1.0.0', 'translator_owner': 'BEMGen'}
MASS_POLICIES = {
    'added_mass_policy': 'additional source furnishings/partition objects are separate from explicit surfaces',
    'floor_pair_policy': 'one physical slab; do not add both floor and ceiling capacity',
    'paired_face_area_policy': 'mean_zone_weighted_faces',
    'paired_surface_policy': {'adjacent_ceiling': 'reverse the same canonical floor assembly', 'canonical_side': 'InteriorFloor',
                              'unpaired_ceiling': 'use InteriorCeiling recipe'},
    'removed_wall_policy': 'Restore only unrepresented InteriorWall capacity using source or equivalent recipes; exchange equivalence remains approximate',
    'residual_floor_policy': 'Restore only unrepresented InteriorFloor capacity; explicit slabs retain their capacity',
    'residual_policy': 'max(0, reference minus represented); report signed difference and excess; never subtract mass'}
CONSUMER_INPUTS = 'exterior surface or wall area, floor area or volume of each zone, from the consumer geometry'


def set_id(edition, building_type):
    return stable_id('construction', {'template': template(edition), 'building_type': building_type, 'source': 'iecc'})


def context_id(edition, building_type, climate):
    return stable_id('construction-set', {'template': template(edition), 'building_type': building_type, 'climate': climate,
                                          'source': 'iecc'})


class Documents:
    """The construction sets, catalogue rows and detailed documents of the IECC editions."""

    def __init__(self, inputs=None):
        self.inputs = inputs or {e: load_json(ROOT/INPUT.format(e)) for e in EDITIONS}
        self.sets, self.contexts, self.where = {}, {}, {}
        for edition, document in sorted(self.inputs.items()):
            tmpl = template(edition)
            for building_type, payload in sorted(document['envelope'].items()):
                sid = set_id(edition, building_type)
                self.sets[sid] = {'id': sid, 'name': f'{building_type} construction package', 'scope': 'building',
                                  'source': {'building_type': building_type, 'construction_set_id': sid,
                                             'definition_release': f'iecc-commercial-{edition}', 'evidence_view': 'source',
                                             'source_family': FAMILY, 'source_fixture_id': None, 'space_type': None, 'template': tmpl,
                                             'vintage': {'kind': 'source_template', 'status': 'exact', 'value': tmpl}}}
                rows = []
                for climate in sorted(payload['contexts']):
                    cid = context_id(edition, building_type, climate)
                    rows.append({'climate_zone': climate, 'reference_id': f'{tmpl}/{building_type}', 'detailed_context_id': cid})
                    self.where[cid] = (edition, building_type, climate)
                self.contexts[sid] = rows
        self._evidence = {e: {r['id']: r for r in d['provenance']} for e, d in self.inputs.items()}
        self._files = {e: {r['id']: r for r in d['source_files']} for e, d in self.inputs.items()}
        self._schedules = {e: {r['id']: r for r in d['schedules']} for e, d in self.inputs.items()}

    def add_to(self, constructions):
        """Add the sets and catalogue rows to an atlas_constructions.Sources."""
        clash = self.sets.keys() & constructions.sets.keys()
        if clash:
            raise ValueError('IECC construction sets already in the sources: '+', '.join(sorted(clash)[:3]))
        constructions.sets.update(copy.deepcopy(self.sets))
        for sid, rows in self.contexts.items():
            constructions.contexts[sid] = copy.deepcopy(rows)

    def evidence(self, edition, key):
        """A definition evidence row as a construction evidence object."""
        row = self._evidence[edition][key]
        source = self._files[edition][row['source_file_id']]
        out = {'extraction_date': row['extraction_date'], 'interpretation_note': row['interpretation'],
               'original_unit': row['original_unit'] or 'as written', 'original_value': row['original_value'],
               'source_file_sha256': source['sha256'], 'source_locator': f"{source['archive_path']}!{source['path']}#{row['locator']}",
               'source_project': source['project'], 'source_revision': source['version'], 'transformation': row['transformation']}
        return {'id': stable_id('construction-evidence', out), **out}

    def schedule(self, edition, key):
        s = self._schedules[edition][key]
        return {k: s[k] for k in ('source_name', 'schedule_type', 'units', 'time_resolution_minutes', 'rules')}

    def pair(self, cid):
        """(detailed document, unified stub) for one context."""
        edition, building_type, climate = self.where[cid]
        detailed = self.detailed(edition, building_type, climate, cid)
        unified = {'id': stable_id('construction-equivalent', {'context': cid}), 'kind': 'construction_equivalent', 'status': 'deferred',
                   'reason': 'ADR 0040 item 10: the unified representation of the IECC sets needs the pinned-producer equivalence '
                             'pipeline and is deferred; use the detailed document.', 'assemblies': {}, 'materials': {}, 'evidence': {}}
        return detailed, unified

    def detailed(self, edition, building_type, climate, cid):
        document = self.inputs[edition]
        payload = document['envelope'][building_type]
        ctx = payload['contexts'][climate]
        tmpl, sid = template(edition), set_id(edition, building_type)
        library = payload['assemblies']
        evidence = {}

        def cite(key):
            e = self.evidence(edition, key)
            evidence[e['id']] = e
            return e['id']
        file_evidence = cite(ctx['file_evidence_id'])
        assemblies, materials, decisions = {}, {}, []
        methods, parameters = {}, {}

        def use(key):
            record = copy.deepcopy(library[key])
            record['evidence_ids'] = [cite(e) for e in record['evidence_ids']]
            for layer in record.get('layers', []):
                m = copy.deepcopy(payload['materials'][layer['material_id']])
                m['property_evidence'] = {p: cite(e) for p, e in m['property_evidence'].items()}
                materials[m['id']] = m
            assemblies[key] = record
            return record
        components = {}
        for role, target in TARGETS.items():
            rules = ctx['components'].get(role, [])
            assignments = []
            for n, rule in enumerate(rules):
                record = use(rule['assembly'])
                assignment = {'assembly_id': rule['assembly'], 'source_definition_id': sid, 'source_selector': role,
                              'when': dict(rule['when']), 'source_element_ids': sorted(rule['surfaces']), 'geometry': copy.deepcopy(GEOMETRY),
                              'evidence_ids': sorted(set(record['evidence_ids']))}
                if record['model'] in FOUNDATION:
                    model, required = FOUNDATION[record['model']]
                    pid = stable_id('ground-model-parameters', FC_PARAMETERS)
                    mid = stable_id('ground-method', {'model': model, 'model_parameters_id': pid, 'required_geometry': required})
                    parameters[pid] = dict(FC_PARAMETERS)
                    methods[mid] = {'model': model, 'model_parameters_id': pid, 'parameters': {}, 'required_geometry': required}
                    assignment['ground_method_id'] = mid
                    assignment['when'].setdefault('boundary_condition', 'Ground')
                assignment['id'] = stable_id('construction-assignment', {'context': cid, 'role': role, 'index': n, **assignment})
                assignments.append(assignment)
                kind = 'surface_override' if rule.get('override') else rule['when']['scope']
                decisions.append({'source_selector': role, 'assignment_id': assignment['id'], 'rule': kind,
                                  'source_element_count': len(rule['surfaces']), 'evidence_id': file_evidence})
            components[role] = {'assignments': assignments, 'disposition': 'provided' if assignments else 'source_absent',
                                'target': copy.deepcopy(target)}
        counted = payload['reference']['counted_floor_area_m2']
        infiltration = ctx['infiltration']
        fenestration = ctx['fenestration']
        detailed = {
            'schema_version': VERSION, 'kind': 'construction_set', 'export_mode': 'source_ready', 'id': cid,
            'name': f'{building_type} construction package', 'scope': 'building',
            'source': {'construction_set_id': sid, 'definition_release': f'iecc-commercial-{edition}', 'building_type': building_type,
                       'template': tmpl, 'evidence_view': 'source', 'source_family': FAMILY,
                       'climate': {'status': 'exact', 'value': climate}, 'source_climate_label': ctx['source_climate_label'],
                       'vintage': {'kind': 'source_template', 'status': 'exact', 'value': tmpl}, 'space_type': None,
                       'reference_variant_id': f'{tmpl}/{building_type}', 'source_fixture_id': None,
                       'evidence': [copy.deepcopy(evidence[file_evidence])]},
            'components': components,
            'infiltration': {'method': METHOD, 'default_method': METHOD, 'reference_id': f'{tmpl}/{building_type}',
                             'methods': {METHOD: {
                                 'zone_rules': [{'method': r['method'], 'value': r['value'], 'unit': r['unit'], 'coefficients': r['coefficients'],
                                                 'schedule': self.schedule(edition, r['schedule_id']), 'zones': r['zones']}
                                                for r in infiltration['zone_rules']],
                                 'excluded_zones': infiltration['excluded_zones'], 'evidence_id': cite(infiltration['evidence_id']),
                                 'consumer_inputs': CONSUMER_INPUTS}}},
            'fenestration_defaults': {**{k: dict(v) for k, v in fenestration['value'].items()}, 'basis': 'whole_building_zone_surfaces',
                                      'evidence_id': cite(fenestration['evidence_id'])},
            'metadata': {'source_definition_ids': [sid], 'selection_decisions': decisions,
                         'assignment_policy': {**POLICY, 'evidence_id': file_evidence},
                         'input_sha256': {INPUT.format(edition): document_digest(edition)},
                         'source_files': {f"pnnl-prototypes/{f['path']}": {'sha256': f['sha256'], 'source_revision': f['version'],
                                                                             'path': f['path'], 'archive_path': f['archive_path'],
                                                                             'archive_sha256': f['archive_sha256'], 'url': f['url']}
                                          for f in [self._files[edition][ctx['source_file_id']]]},
                         'migration': dict(MIGRATION), 'variant_selections': {}},
            'mass_accounting': self.mass(edition, building_type, ctx, payload, counted, use, cite, file_evidence),
            'foundation_ground': {'configuration': {'type': 'source_native_commercial' if methods else 'no_direct_ground_contact'},
                                  'methods': methods, 'model_parameters': parameters,
                                  'required_geometry': {k: dict(REQUIRED[k]) for m in methods.values() for k in m['required_geometry']}},
        }
        detailed['assemblies'], detailed['materials'], detailed['evidence'] = assemblies, materials, evidence
        return detailed

    def mass(self, edition, building_type, ctx, payload, counted, use, cite, file_evidence):
        profile = payload['reference']['profile_id']
        stories = payload['stories']
        recipes, entries = {}, []
        for item in ctx['mass']:
            record = use(item['assembly'])
            layers = []
            for layer in record['layers']:
                m = payload['materials'][layer['material_id']]
                if m['model'] not in ('StandardOpaqueMaterial', 'MasslessOpaqueMaterial', 'AirGap'):
                    raise ValueError(f'Internal mass layer {m["name"]} is not opaque')
                layers.append({'model': m['model'], 'properties': {**m['properties'], 'name': m['name']}})
            capacity = sum(l['properties'].get('thickness_m', 0)*l['properties'].get('density_kg_m3', 0)*l['properties'].get('specific_heat_J_kg_K', 0)
                           for l in layers if l['model'] == 'StandardOpaqueMaterial')
            recipe = {'capacity_J_m2_K': capacity, 'interpretation': 'Original source mass material layers; no equivalent fitting or added air films.',
                      'layers': layers, 'model': 'opaque_layers', 'source_locator': f'IDF Construction {record["name"]} (InternalMass)'}
            rid = stable_id('reference-mass-recipe', recipe)
            recipes[rid] = recipe
            area = item['area_m2']*item['multiplier']
            entry = {'area_convention': 'IDF InternalMass object area; zone multiplier applied once',
                     'area_per_counted_floor_area': area/counted, 'capacity_per_counted_floor_area_J_m2_K': area/counted*capacity,
                     'recipe_id': rid, 'reference_area_m2': area, 'evidence_id': record['evidence_ids'][0],
                     'scope': {'counted_floor_area': item['counted'], 'kind': 'source_space', 'native_building_type': item['standards_building_type'],
                               'native_space_type': item['space_type'], 'source_space_name': item['zone'], 'source_story': stories[item['zone']]},
                     'source_locator': f'IDF InternalMass {item["object"]} in zone {item["zone"]}',
                     'source_operands': {'area_per_floor_area': None, 'area_per_person_m2': None, 'direct_area_m2': item['area_m2'],
                                         'id': item['object'], 'source_multiplier': item['multiplier']}}
            entry['id'] = stable_id('source-mass-quantity', entry)
            entries.append(entry)
        budgets = {}
        for role, rows in ctx['budgets'].items():
            budgets[role] = []
            for row in rows:
                use(row['assembly'])
                budgets[role].append({'source_assembly_id': row['assembly'], 'area_per_counted_floor_area': row['reference_area_m2']/counted,
                                      'capacity_per_counted_floor_area_J_m2_K': row['reference_area_m2']/counted*row['source_areal_capacity_J_m2_K'],
                                      'reference_area_m2': row['reference_area_m2'], 'source_areal_capacity_J_m2_K': row['source_areal_capacity_J_m2_K'],
                                      'source_locator': f'IDF {role} surfaces, zone multipliers applied; paired wall faces halved'})
        source = self._files[edition][ctx['source_file_id']]
        return {
            **{k: copy.deepcopy(v) for k, v in MASS_POLICIES.items()}, 'schema_version': '1.0.0', 'status': 'ready',
            'reference': {'counted_floor_area_m2': counted, 'profile_id': profile,
                          'quantity_basis': 'multiply normalized quantities by actual counted building floor area'},
            'physical_inventory_profile_id': profile,
            'reference_area_approximation': {'evidence_profile_id': profile, 'unequal_multiplier_pair_counts': {'floor_pairs': 0, 'wall_pairs': 0},
                                             'interpretation': 'Interior wall faces between zones are halved and floors counted once, each with its '
                                                               'zone multiplier; the IDF faces carry no pairing information.'},
            'physical_capacity_budgets': budgets,
            'additional_mass': {'status': 'provided' if entries else 'known_zero', 'entries': entries,
                                'allocation_policy': 'Precomputed source-scope quantities normalized by building counted floor area; preserve '
                                                     'source scopes. If absent in consumer geometry, require an explicit consumer allocation policy.',
                                'legacy_partition_selector_policy': 'InteriorPartition is a retained material selector. Instantiate additional '
                                                                    'mass from this inventory only; never instantiate both representations of the same source object.'},
            'recipes': recipes,
            'provenance': {'extraction_date': '2026-10-26', 'source_project': source['project'], 'source_revision': source['version'],
                           'source_locator': f"{source['archive_path']}!{source['path']}", 'source_file_sha256': {source['path']: source['sha256']},
                           'original_unit': 'm2, SI material properties and dimensionless zone multipliers',
                           'original_value': {'counted_floor_area_m2': counted, 'evidence_id': file_evidence},
                           'transformation': 'IDF zone floor areas and multipliers; InternalMass areas and interior surface areas divided by the counted floor area',
                           'interpretation_note': 'Quantities describe the IECC prototype, not a population weight or consumer geometry.'}}


_DIGESTS = {}


def document_digest(edition):
    import hashlib
    if edition not in _DIGESTS:
        _DIGESTS[edition] = hashlib.sha256((ROOT/INPUT.format(edition)).read_bytes()).hexdigest()
    return _DIGESTS[edition]
