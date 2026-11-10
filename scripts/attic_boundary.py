"""Unconditioned attics in the unified constructions: boundary semantics and an attic-omitted roof (ADR 0065).

python -m scripts.attic_boundary --inventory DIR          # attic_inventory.csv / .json over every unified context
python -m scripts.attic_boundary --export DIR             # unified 4.1.0 of every context with an attic, SHA256SUMS
python -m scripts.attic_boundary --export DIR --set ID --context KEY

A unified construction (4.0.0) gives each role one equivalent assembly. Where the source puts an unconditioned
attic between the occupied zones and the roof, `ExteriorRoof` is the attic's roof deck, and the occupied zones'
thermal boundary is the attic floor, in series with the attic air and the deck. Unified 4.1.0 states this:

- `attics`: one entry per source attic, with its exterior parts (roof deck, soffit, gable walls: role, source
  contributors, reference areas, their own common-film U), the conditioned boundary (the role and contributor whose
  layers separate the attic from the occupied zones, and the orientation the zone side takes), other interior
  adjacencies of the attic (a garage ceiling), the roof-to-boundary area ratio and `attic_omitted_roof`: a derived
  assembly for the top of the occupied zones when a consumer does not instantiate the attic;
- `components.<role>.attics`: which part of the role's source reference area belongs to which attic;
- `export_corrections`: a stored value the export corrects, with the stored and the corrected value.

Families (how the attic is recognised; no geometry is guessed):
- `openstudio_standards_rules` (90.1 and DOE Ref; source families code_prototype_rules and existing_stock_benchmark):
  the openstudio-standards construction set of the `Attic` standards space type (Standards.Model.rb,
  model_add_construction_set: "insulation is actually on the floor and the roof itself is uninsulated"): the component
  assignments whose `when` is that space type. The conditioned boundary is the attic
  `InteriorFloor` contributor, its layers reversed on the zone side.
- `pnnl_idf` (IECC, from the PNNL IDFs): the `ExteriorRoof` contributors named attic roof deck and the
  `InteriorFloor` / `ExteriorFloor` assignments whose source surfaces are the attic's.
- `resstock` (ResStock dwellings): assignments whose `when` names an `attic - vented` or `attic - unvented` space;
  the conditioned boundary is the `InteriorCeiling` contributor between that attic and conditioned space, already in
  ceiling orientation.

The attic-omitted roof (method `attic_series_stack_1.0.0`): per m2 of conditioned boundary, outside to inside, the roof
deck layers with R/n and C*n (n = A_roof / A_boundary, the source reference areas), one massless layer for the two attic
air films and the area correction of the exterior film, R = (R_ai + R_se)/n + R_ai - R_se, and the boundary layers in
zone-side orientation. With the package films (R_se 0.04, R_ai = R_si 0.13) its common-film U is the ASHRAE ceiling-roof
combination, 1/U = 1/U_boundary + 1/(n U_roof), of a sealed attic whose only exterior part is the deck. It is fitted to
the package's three-slot form with the existing policy (scripts.construction_equivalence), its errors retained. Attic
ventilation and the attic's other exterior parts are not in it; `u_bounds_W_m2_K` gives U with all exterior parts (sealed)
and U of the boundary alone (attic air at outdoor temperature, the full-ventilation limit).

openstudio-standards corrections (ADR 0065 section 3): OpenStudio gives the occupied zones' ceilings of an attic-floor pair the
attic floor's construction reversed (the space-type set's search distance 2 beats the building default's 4;
ForwardTranslator::resolveMatchedSurfaceConstructionConflicts). The stored InteriorCeiling counted those ceilings as
the building default interior ceiling; the 4.1.0 export removes that paired area from the InteriorCeiling derivation.

From release 2.6.0 (ADR 0066) the records carry that correction: the stored InteriorCeiling derivation is the corrected
one, and the unified record's `provenance.interior_ceiling_correction` keeps the derivation it replaced (releases 2.0.0
to 2.5.0), the paired area, the reason and the evidence (`record_correction`). The export then states the correction
from the record (`export_corrections`, `stored` being the replaced derivation) after checking that the rule gives the
stored value from the replaced one, and does not apply it a second time.
"""
import argparse
import copy
import csv
import hashlib
import io
import json
import math
from pathlib import Path

from scripts.atlas_contracts import UNIFIED_ATTICS as CONTRACT
from scripts.atlas_format import h6, slug
from scripts.common import ROOT, load_json
from scripts.construction_equivalence import reduce_opaque
from scripts.construction_equivalent_export import source_layers

ADR = 'docs/adr/0065-unconditioned-attic-boundaries.md'
METHOD = 'attic_series_stack_1.0.0'
DATE = '2026-11-09'
ATTIC_SPACE_TYPES = ('Attic',)
# The 90.1 prototypes and the DOE Ref templates are both built by the openstudio-standards construction-set rules.
OPENSTUDIO_STANDARDS_FAMILIES = ('code_prototype_rules', 'existing_stock_benchmark')
RESSTOCK_ATTICS = ('attic - vented', 'attic - unvented')
EXTERIOR_FILMS = (.04, .13)
INTERIOR_FILMS = (.13, .13)
R_SE, R_AI = EXTERIOR_FILMS[0], INTERIOR_FILMS[0]
EXTERIOR_ROLES = ('ExteriorRoof', 'ExteriorFloor', 'ExteriorWall')
STANDARDS_REVISION = 'c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907'
INTERZONE_LOCK = 'sources/construction-interzone-lock.json'
# The unified record's provenance member that carries the InteriorCeiling correction from release 2.6.0 (ADR 0066).
CARRIED = 'interior_ceiling_correction'


class AtticError(ValueError):
    pass


# Recognition -------------------------------------------------------------------------------------------------

def family(detailed):
    sid = detailed['source']['construction_set_id']
    if sid.startswith('resstock-'):
        return 'resstock'
    if sid.startswith('iecc-'):
        return 'pnnl_idf'
    if detailed['source'].get('source_family') in OPENSTUDIO_STANDARDS_FAMILIES:
        return 'openstudio_standards_rules'
    return None


def _attic_key(fam, assignment, role, detailed):
    """The attic an assignment belongs to, with its part, or None."""
    w = assignment['when']
    if fam == 'openstudio_standards_rules':
        if w.get('scope') == 'space_type' and w.get('space_type') in ATTIC_SPACE_TYPES:
            part = 'conditioned_boundary' if role == 'InteriorFloor' else 'exterior' if role in EXTERIOR_ROLES else 'other_interior'
            return w['space_type'], part
        return None
    if fam == 'resstock':
        inside, outside = w.get('interior_space_type'), w.get('exterior_space_type')
        if role in EXTERIOR_ROLES and inside in RESSTOCK_ATTICS and outside == 'outside':
            return inside, 'exterior'
        if outside in RESSTOCK_ATTICS and role == 'InteriorCeiling':
            return outside, 'conditioned_boundary' if inside == 'conditioned space' else 'other_interior'
        if inside in RESSTOCK_ATTICS or outside in RESSTOCK_ATTICS:
            return (inside if inside in RESSTOCK_ATTICS else outside), 'other_interior'
        return None
    if fam == 'pnnl_idf':
        elements = ' '.join(assignment.get('source_element_ids') or []).lower()
        name = (detailed['assemblies'][assignment['assembly_id']].get('name') or '').lower()
        if role == 'ExteriorRoof' and 'attic' in name:
            return 'Attic', 'exterior'
        if role == 'ExteriorFloor' and 'attic' in elements:
            return 'Attic', 'exterior'
        if role == 'InteriorFloor' and 'attic' in elements:
            return 'Attic', 'conditioned_boundary'
        return None
    return None


def _contributors(unified, role, assembly_ids):
    component = unified['components'].get(role) or {}
    rows = (component.get('derivation') or {}).get('contributors') or []
    return [r for r in rows if r['assembly_id'] in assembly_ids]


def recognise(detailed, unified):
    """{attic name: {part: {role: [unified contributor rows]}}} from the detailed rules and the unified areas.

    An assembly a non-attic rule of the same role also selects would mix areas; that is an error, not a guess.
    """
    fam = family(detailed)
    if fam is None:
        return fam, {}
    found = {}
    for role, component in detailed['components'].items():
        own, other = {}, set()
        for a in component.get('assignments', []):
            key = _attic_key(fam, a, role, detailed)
            if key:
                own.setdefault(key, set()).add(a['assembly_id'])
            else:
                other.add(a['assembly_id'])
        for (name, part), ids in own.items():
            shared = ids & other
            if shared:
                raise AtticError(f'{role}: assemblies {sorted(shared)} serve the attic and other spaces')
            rows = _contributors(unified, role, ids)
            if rows:
                found.setdefault(name, {}).setdefault(part, {})[role] = rows
    # An attic needs a roof over it and a boundary under it in the reference.
    return fam, {n: p for n, p in found.items() if p.get('exterior', {}).get('ExteriorRoof') and p.get('conditioned_boundary')}


# Physics -----------------------------------------------------------------------------------------------------

def _u(layers, films):
    return 1/(math.fsum(l['R'] for l in layers)+sum(films))


def _role_films(role):
    return INTERIOR_FILMS if role.startswith('Interior') else EXTERIOR_FILMS


def _material_face(detailed, assembly_id, index):
    material = detailed['materials'][detailed['assemblies'][assembly_id]['layers'][index]['material_id']]
    p = material['properties']
    face = {k: p[k] for k in ('roughness', 'thermal_absorptance', 'solar_absorptance', 'visible_absorptance')}
    if any(face[k] is None or not 0 <= face[k] <= 1 for k in ('thermal_absorptance', 'solar_absorptance', 'visible_absorptance')):
        raise AtticError('Unknown or invalid source surface absorptance')
    return face


def _single(parts, role):
    rows = [r for r in parts.get(role, [])]
    if len(rows) != 1:
        raise AtticError(f'{role}: {len(rows)} attic contributors; the series stack needs exactly one')
    return rows[0]


def boundary_orientation(fam, role):
    """`reverse_layers` where the boundary is the attic floor seen from the attic (its outside faces the zone)."""
    return 'as_listed' if (fam == 'resstock' and role == 'InteriorCeiling') else 'reverse_layers'


def series_stack(detailed, fam, parts):
    """The attic-omitted series stack per m2 of conditioned boundary, outside to inside, with its operands."""
    roof = _single(parts['exterior'], 'ExteriorRoof')
    (boundary_role, boundary_rows), = parts['conditioned_boundary'].items()
    if len(boundary_rows) != 1:
        raise AtticError(f'{boundary_role}: {len(boundary_rows)} boundary contributors; the series stack needs exactly one')
    boundary = boundary_rows[0]
    a_roof, a_boundary = roof['reference_area_m2'], boundary['reference_area_m2']
    if not (a_roof > 0 and a_boundary > 0):
        raise AtticError('Zero source reference area for the attic roof or boundary')
    n = a_roof/a_boundary
    deck = source_layers(detailed, detailed['assemblies'][roof['assembly_id']])
    floor = source_layers(detailed, detailed['assemblies'][boundary['assembly_id']])
    orientation = boundary_orientation(fam, boundary_role)
    zone_side = list(reversed(floor)) if orientation == 'reverse_layers' else floor
    air = (R_AI+R_SE)/n+R_AI-R_SE
    stack = ([{'R': l['R']/n, 'C': l['C']*n} for l in deck] + [{'R': air, 'C': 0.}] + [dict(l) for l in zone_side])
    return {'stack': stack, 'n': n, 'roof': roof, 'boundary': boundary, 'boundary_role': boundary_role,
            'orientation': orientation, 'deck': deck, 'floor': floor, 'air_R': air}


def attic_omitted_roof(detailed, fam, parts):
    """The fitted attic-omitted roof assembly (unnamed) and its statement, from the series stack."""
    s = series_stack(detailed, fam, parts)
    recipe = reduce_opaque([{'weight': 1., 'layers': s['stack']}], films=EXTERIOR_FILMS)
    if recipe['status'] != 'ready':
        raise AtticError('No valid three-slot fit of the attic series stack')
    roof, boundary = s['roof'], s['boundary']
    zone_index = 0 if s['orientation'] == 'reverse_layers' else -1
    recipe['model'] = 'opaque_layers'
    recipe['surface_properties'] = {'exterior': _material_face(detailed, roof['assembly_id'], 0),
                                    'interior': _material_face(detailed, boundary['assembly_id'], zone_index)}
    u_roof = _u(s['deck'], EXTERIOR_FILMS)
    u_boundary = _u(s['floor'], INTERIOR_FILMS)
    # Every exterior part of the attic, each with its own common-film U, in parallel (sealed attic).
    ua = 0.
    for role, rows in parts['exterior'].items():
        for row in rows:
            ua += row['reference_area_m2']*_u(source_layers(detailed, detailed['assemblies'][row['assembly_id']]), EXTERIOR_FILMS)
    a = boundary['reference_area_m2']
    u_all = 1/(1/u_boundary+a/ua)
    u_equivalent = recipe['targets']['u_reference_W_m2_K']
    others = sorted(parts.get('other_interior', {}))
    shared = (f' The attic also adjoins {", ".join(others)} contributors (other_interior_parts); their exchange with the '
              'attic is not represented and the whole roof is referred to the conditioned boundary.') if others else ''
    statement = {
        'method': METHOD, 'status': 'ready',
        'applies_to': ('the top surfaces of the occupied zones when the consumer does not instantiate this attic, in place of '
                       'ExteriorRoof over it; per m2 of the conditioned boundary (the zone ceiling), outside to inside'),
        'area_basis': 'conditioned_boundary', 'area_ratio_roof_to_boundary': s['n'],
        'stack': {'roof_contributor': roof['assembly_id'], 'boundary_contributor': boundary['assembly_id'],
                  'boundary_role': s['boundary_role'], 'boundary_orientation': s['orientation'],
                  'roof_layers_scaled': 'R/n, C*n', 'attic_air_layer_R_m2_K_W': s['air_R'],
                  'attic_air_layer_rule': '(R_ai + R_se)/n + R_ai - R_se', 'films_m2_K_W': {'R_se': R_SE, 'R_ai': R_AI, 'R_si': INTERIOR_FILMS[1]},
                  'layers': [{'R': l['R'], 'C': l['C']} for l in s['stack']]},
        'u_bounds_W_m2_K': {'equivalent_sealed_roof_only': u_equivalent, 'sealed_all_exterior_parts': u_all,
                            'boundary_only_attic_at_outdoor_temperature': u_boundary,
                            'roof_deck_alone': u_roof},
        'capacity_J_m2_K': {'equivalent': recipe['targets']['capacity_J_m2_K'],
                            'roof_deck_scaled': math.fsum(l['C'] for l in s['deck'])*s['n'],
                            'boundary': math.fsum(l['C'] for l in s['floor'])},
        'approximation': ('Steady conduction of the sealed attic path through the deck only; attic air capacity, attic '
                          'ventilation and infiltration, the attic\'s other exterior parts, radiant exchange beyond the '
                          'combined 0.13 m2 K/W films, pitch and the deck\'s solar aperture (A_roof, tilted) are not '
                          'represented. Ventilation moves U from the equivalent towards boundary_only; the other exterior '
                          'parts move it to sealed_all_exterior_parts. Solar absorbed on the deck is applied per m2 of '
                          'boundary by the consumer\'s own geometry.'+shared),
        'mass_accounting': ('The equivalent instantiates the boundary contributor\'s capacity once; deduct that contributor '
                            'from FloorDistributedMass / physical_capacity_budgets.InteriorFloor where the boundary is an '
                            'InteriorFloor (mass accounting: count a represented slab once).')}
    return recipe, statement


def source_default_roof(detailed, fam):
    """The source's own rule for a roof over a non-attic space: the building-default ExteriorRoof assignment (openstudio-
    standards sets only). It has no reference area in an all-attic building, so the unified ExteriorRoof omits it."""
    if fam != 'openstudio_standards_rules':
        return None
    rules = [a for a in detailed['components']['ExteriorRoof']['assignments'] if a['when'].get('scope') == 'building_default']
    if len(rules) != 1:
        return None
    aid = rules[0]['assembly_id']
    assembly = detailed['assemblies'][aid]
    layers = source_layers(detailed, assembly)
    return {'assembly_id': aid, 'name': assembly.get('name'), 'when': copy.deepcopy(rules[0]['when']),
            'layer_resistance_m2_K_W': math.fsum(l['R'] for l in layers), 'capacity_J_m2_K': math.fsum(l['C'] for l in layers),
            'u_reference_W_m2_K': _u(layers, EXTERIOR_FILMS),
            'note': ('The source rule for a roof directly over an occupied space (no reference area here); a source assembly '
                     'in the detailed document, not fitted in this unified document.')}


# Document ----------------------------------------------------------------------------------------------------

def _lock_sha(path, lock=None):
    for name in ([lock] if lock else sorted(p.relative_to(ROOT).as_posix() for p in (ROOT/'sources').glob('*lock*.json'))):
        data = load_json(ROOT/name)
        for row in data.get('files', []) if isinstance(data.get('files'), list) else []:
            if isinstance(row, dict) and row.get('path') == path and 'sha256' in row:
                return row['sha256']
    raise AtticError('No locked SHA-256 for '+path)


def evidence_rows(fam, corrected):
    """The evidence rows the 4.1.0 additions cite (ADR 0054 shape), by ID."""
    rows = {}
    def add(prefix, row):
        rid = f'{prefix}-{h6(row)}'
        rows[rid] = {'id': rid, **row}
        return rid
    method = add('attic-evidence', {
        'source_project': 'Energy Archetype Atlas', 'source_revision': 'ADR 0065',
        'source_locator': ADR+'#section-2.1', 'source_file_sha256': None,
        'original_value': {'method': METHOD, 'films_m2_K_W': {'R_se': R_SE, 'R_ai': R_AI, 'R_si': INTERIOR_FILMS[1]}},
        'original_unit': 'R m2 K/W; C J/(m2 K); areas m2',
        'transformation': 'Series stack per m2 of boundary: roof deck R/n and C*n, attic air films (R_ai+R_se)/n+R_ai-R_se, '
                          'boundary in zone-side orientation; fitted with two_mass_one_resistance_1.0.1',
        'extraction_date': DATE,
        'interpretation_note': 'Derived approximation for a consumer that omits the attic; not a source construction.'})
    ids = [method]
    if fam == 'openstudio_standards_rules':
        ids.append(add('attic-evidence', {
            'source_project': 'OpenStudio Standards', 'source_revision': STANDARDS_REVISION,
            'source_locator': 'lib/openstudio-standards/standards/Standards.Model.rb#model_add_construction_set (spc_type == Attic)',
            'source_file_sha256': _lock_sha('lib/openstudio-standards/standards/Standards.Model.rb'),
            'original_value': {'Attic exterior roof': 'Typical Uninsulated Wood Joist Attic Roof',
                               'Attic exterior floor': 'Typical Attic Soffit',
                               'Attic interior floor': "the 'ExteriorRoof' construction of the set's roof type (insulated to the roof requirement)"},
            'original_unit': 'source construction names',
            'transformation': 'Assignments scoped to the Attic standards space type are the attic parts',
            'extraction_date': DATE,
            'interpretation_note': 'Source comment: the insulation is on the attic floor and the roof itself is uninsulated; '
                                   'the attic is served by no HVAC system (data/program-inputs/conditioning-sides-v1.json, ADR 0063).'}))
    if corrected:
        ids.append(add('attic-evidence', {
            'source_project': 'OpenStudio', 'source_revision': '86d7e215a145557e4e029732628f5e3281898d35',
            'source_locator': 'src/energyplus/ForwardTranslator.cpp#ForwardTranslator::resolveMatchedSurfaceConstructionConflicts',
            'source_file_sha256': _lock_sha('src/energyplus/ForwardTranslator.cpp', INTERZONE_LOCK),
            'original_value': {'rule': 'surfaces of a matched pair with different default constructions take the one with the '
                                       'lower search distance; the other surface takes its reverse',
                               'search_distance': {'space': 1, 'space_type': 2, 'building_story': 3, 'building': 4,
                                                   'building_space_type': 5}},
            'original_unit': 'ordinal search distance',
            'transformation': 'Zone ceilings paired with an Attic-space-type floor (distance 2) take the attic floor reversed, '
                              'not the building default interior ceiling (distance 4)',
            'extraction_date': DATE,
            'interpretation_note': 'Space_Impl::getDefaultConstructionWithSearchDistance (src/model/Space.cpp) gives the distances; '
                                   'the PNNL SmallOffice IDFs (nonres_roof on the zone ceilings) and the DOE reference '
                                   'SmallOffice IDFs (Attic Non-res Floor) agree.'}))
    return rows, ids


def _ceiling_correction(fam, unified, detailed, attics, evidence_id):
    """The InteriorCeiling derivation without the attic-paired ceilings (code prototypes), or None."""
    if fam != 'openstudio_standards_rules':
        return None
    component = unified['components'].get('InteriorCeiling') or {}
    rows = (component.get('derivation') or {}).get('contributors') or []
    if component.get('status') != 'ready' or not rows:
        return None
    paired = math.fsum(row['reference_area_m2'] for parts in attics.values() for rs in parts['conditioned_boundary'].values() for row in rs)
    scopes = {a['when'].get('scope') for a in detailed['components']['InteriorCeiling']['assignments']}
    if len(rows) != 1 or not scopes <= {'building_default', 'story'}:
        return {'pointer': '/components/InteriorCeiling/derivation', 'status': 'unresolved',
                'reason': 'several InteriorCeiling contributors or a space-type ceiling rule: the attic-paired area cannot be '
                          'attributed without the source spaces', 'paired_ceiling_area_m2': paired, 'evidence_ids': [evidence_id]}
    before = copy.deepcopy(component['derivation'])
    rest = rows[0]['reference_area_m2']-paired
    if rest < -1e-6*max(paired, 1.):
        raise AtticError('Attic-paired ceiling area exceeds the InteriorCeiling reference area')
    if abs(rest) <= 1e-6*max(paired, 1.):
        after = {'contributors': [{'assembly_id': rows[0]['assembly_id'], 'weight': 1., 'reference_area_m2': 0.}],
                 'source_reference_area_m2': 0., 'weight_basis': 'unique_source_recipe_without_reference_exposure'}
    else:
        after = {'contributors': [{'assembly_id': rows[0]['assembly_id'], 'weight': 1., 'reference_area_m2': rest}],
                 'source_reference_area_m2': rest, 'weight_basis': before['weight_basis']}
    return {'pointer': '/components/InteriorCeiling/derivation', 'status': 'corrected', 'stored': before, 'corrected': after,
            'paired_ceiling_area_m2': paired,
            'reason': 'The source gives the zone ceilings paired with the attic floor the attic floor reversed (OpenStudio '
                      'interzone resolution), not the building default interior ceiling; those ceilings are the conditioned '
                      'boundary of the attic (attics[].conditioned_boundary). The InteriorCeiling recipe is unchanged.',
            'evidence_ids': [evidence_id]}


def record_correction(correction, decision):
    """The provenance member a release record keeps for a correction it carries (ADR 0066): the replaced value, not the
    corrected one, which is the stored value itself."""
    if correction['status'] != 'corrected':
        raise AtticError('Only a corrected value is carried in the record')
    return {'decision': decision, 'evidence_ids': list(correction['evidence_ids']), 'paired_ceiling_area_m2': correction['paired_ceiling_area_m2'],
            'pointer': correction['pointer'], 'reason': correction['reason'], 'replaced': copy.deepcopy(correction['stored']),
            'status': 'corrected'}


def carried_correction(fam, unified, detailed, found, carried, evidence_id):
    """The export_corrections entry of a correction the record carries, after checking it: the rule applied to the
    replaced derivation gives the stored one, with the same paired area and evidence."""
    pointer = '/components/InteriorCeiling/derivation'
    if carried.get('pointer') != pointer or carried.get('status') != 'corrected':
        raise AtticError(f'Unknown carried correction {carried.get("pointer")} {carried.get("status")}')
    replaced = copy.deepcopy(unified)
    replaced['components']['InteriorCeiling'] = {**unified['components']['InteriorCeiling'], 'derivation': carried['replaced']}
    expected = _ceiling_correction(fam, replaced, detailed, found, evidence_id)
    current = unified['components']['InteriorCeiling']['derivation']
    if (expected is None or expected['status'] != 'corrected' or expected['corrected'] != current
            or expected['paired_ceiling_area_m2'] != carried['paired_ceiling_area_m2'] or carried['evidence_ids'] != [evidence_id]):
        raise AtticError('The carried InteriorCeiling correction does not follow from the replaced derivation')
    return {'pointer': pointer, 'status': 'corrected', 'stored': copy.deepcopy(carried['replaced']), 'corrected': copy.deepcopy(current),
            'paired_ceiling_area_m2': carried['paired_ceiling_area_m2'], 'reason': carried['reason'],
            'evidence_ids': list(carried['evidence_ids'])}


def augment(detailed, unified):
    """Unified 4.1.0 from a validated unified 4.0.0 document and its detailed document. Returns (document, attics).

    A record that carries its InteriorCeiling correction (release 2.6.0 on, `provenance.interior_ceiling_correction`)
    is stated from the record and not corrected again."""
    fam, found = recognise(detailed, unified)
    out = copy.deepcopy(unified)
    out['schema_version'] = CONTRACT[1]
    carried = (out.get('provenance') or {}).pop(CARRIED, None)
    if carried is not None and not (fam == 'openstudio_standards_rules' and found):
        raise AtticError('A carried InteriorCeiling correction in a context without an openstudio-standards attic')
    if not found:
        return out, {}
    prefix = unified['id'].split('.')[0]
    corrected_needed = fam == 'openstudio_standards_rules'
    rows, evidence_ids = evidence_rows(fam, corrected_needed)
    attics, notes = [], {}
    for name, parts in sorted(found.items()):
        aid = slug(name)
        entry = {'id': aid, 'kind': 'unconditioned_attic',
                 'source': {'family': fam, 'space': name,
                            'ventilation': 'vented' if name == 'attic - vented' else 'unvented' if name == 'attic - unvented' else 'not_stated'},
                 'exterior_parts': [], 'conditioned_boundary': None, 'other_interior_parts': [],
                 'evidence_ids': list(evidence_ids)}
        def part(role, rs, kind):
            total = math.fsum(r['reference_area_m2'] for r in rs)
            role_total = (unified['components'][role]['derivation'].get('source_reference_area_m2')
                          or math.fsum(r['reference_area_m2'] for r in unified['components'][role]['derivation']['contributors']))
            share = total/role_total if role_total else None
            row = {'role': role, 'contributors': [{'assembly_id': r['assembly_id'], 'reference_area_m2': r['reference_area_m2'],
                                                   'u_reference_W_m2_K': _u(source_layers(detailed, detailed['assemblies'][r['assembly_id']]), _role_films(role))}
                                                  for r in rs],
                   'reference_area_m2': total, 'share_of_component_reference_area': share}
            notes.setdefault(role, []).append({'attic_id': aid, 'part': kind, 'assembly_ids': [r['assembly_id'] for r in rs],
                                               'reference_area_m2': total, 'share_of_component_reference_area': share})
            return row
        for role, rs in sorted(parts['exterior'].items()):
            entry['exterior_parts'].append(part(role, rs, 'exterior'))
        (brole, brs), = parts['conditioned_boundary'].items()
        entry['conditioned_boundary'] = {**part(brole, brs, 'conditioned_boundary'),
                                         'zone_side': {'orientation': boundary_orientation(fam, brole),
                                                       'zone_role': 'InteriorCeiling'}}
        for role, rs in sorted(parts.get('other_interior', {}).items()):
            entry['other_interior_parts'].append(part(role, rs, 'other_interior'))
        roof_area = math.fsum(r['reference_area_m2'] for r in parts['exterior']['ExteriorRoof'])
        entry['area_ratio_roof_to_boundary'] = roof_area/entry['conditioned_boundary']['reference_area_m2']
        default = source_default_roof(detailed, fam)
        if default:
            entry['source_default_exterior_roof'] = default
        try:
            recipe, statement = attic_omitted_roof(detailed, fam, parts)
            body = json.loads(json.dumps(recipe, sort_keys=True))
            asm_id = f'{prefix}.attic-omitted-roof.{h6(body)}'
            out['assemblies'][asm_id] = {**body, 'id': asm_id}
            entry['attic_omitted_roof'] = {'assembly_id': asm_id, **statement}
        except (AtticError, ValueError, KeyError) as exc:
            entry['attic_omitted_roof'] = {'assembly_id': None, 'method': METHOD, 'status': 'blocked', 'reason': str(exc)}
        attics.append(entry)
    out['attics'] = attics
    for role, items in notes.items():
        out['components'][role]['attics'] = items
    if carried is not None:
        correction = carried_correction(fam, unified, detailed, found, carried, evidence_ids[-1])
    else:
        correction = _ceiling_correction(fam, unified, detailed, found, evidence_ids[-1]) if corrected_needed else None
    if correction:
        if correction['status'] == 'corrected':
            out['components']['InteriorCeiling']['derivation'] = correction['corrected']
        out['export_corrections'] = [correction]
    clash = sorted(k for k in rows if k in out['evidence'] and out['evidence'][k] != rows[k])
    if clash:
        raise AtticError(f'Stored evidence rows differ from the attic rows of the same ID: {clash}')
    out['evidence'] = {**out['evidence'], **rows}
    out['evidence'] = dict(sorted(out['evidence'].items()))
    out['assemblies'] = dict(sorted(out['assemblies'].items()))
    return out, found


# Release-level -------------------------------------------------------------------------------------------------

def contexts(release):
    """(set ID, context key) of every unified context in the release, sorted."""
    return [(sid, key) for sid, rec in sorted(release.constructions.sets.items())
            for key in sorted(rec['contexts']) if 'unified' in rec['contexts'][key]]


def export(release, set_id, key):
    """Unified 4.1.0 of one context, validated; with its recognised attics."""
    from scripts import atlas_exports
    unified = release.construction(set_id, key, 'unified', attics=False)
    detailed = release.constructions.export(set_id, key, 'detailed')
    document, found = augment(detailed, unified)
    errors = atlas_exports.schema_errors(CONTRACT[0], document)
    if errors:
        raise AtticError(f'{set_id} {key}: '+'; '.join(errors[:5]))
    return document, found


def document_bytes(document):
    return (json.dumps(document, indent=2, ensure_ascii=False)+'\n').encode('utf-8')


INVENTORY_FIELDS = ('building_type', 'template', 'climate_zone', 'set_id', 'context', 'family', 'attic_id',
                    'package_file', 'package_sha256_4_0_0', 'roof_assembly_ids', 'roof_reference_area_m2', 'roof_u_W_m2_K',
                    'roof_share_of_exterior_roof', 'unified_exterior_roof_u_W_m2_K', 'other_exterior_parts',
                    'boundary_role', 'boundary_assembly_ids', 'boundary_reference_area_m2', 'boundary_u_W_m2_K',
                    'unified_boundary_role_u_W_m2_K', 'area_ratio_roof_to_boundary', 'attic_omitted_status',
                    'attic_omitted_assembly_id', 'attic_omitted_u_W_m2_K', 'u_sealed_all_exterior_W_m2_K',
                    'interior_ceiling_correction', 'interior_ceiling_paired_area_m2')


def candidates(release, only=None):
    """(set ID, context key) of the unified contexts with a recognised attic, from the stored records (no validation)."""
    out = []
    for sid, key in contexts(release):
        if only and not only(sid, key):
            continue
        stored = release.constructions
        if recognise(stored.export(sid, key, 'detailed'), stored.export(sid, key, 'unified'))[1]:
            out.append((sid, key))
    return out


def inventory_rows(release, only=None):
    """One row per (context, attic): what the consumer sees as ExteriorRoof and what the source boundary is."""
    out = []
    for sid, key in candidates(release, only):
        unified = release.construction(sid, key, 'unified', attics=False)
        detailed = release.constructions.export(sid, key, 'detailed')
        fam, found = recognise(detailed, unified)
        document, _ = augment(detailed, unified)
        package = f'{sid}.{key}.unified.json'
        sha = hashlib.sha256(document_bytes(unified)).hexdigest()
        correction = (document.get('export_corrections') or [{}])[0]
        def u_of(role):
            c = unified['components'].get(role) or {}
            return unified['assemblies'][c['assembly_id']]['targets']['u_reference_W_m2_K'] if c.get('status') == 'ready' else None
        for entry in document['attics']:
            roof = next(p for p in entry['exterior_parts'] if p['role'] == 'ExteriorRoof')
            b = entry['conditioned_boundary']
            eq = entry['attic_omitted_roof']
            out.append({
                'building_type': detailed['source']['building_type'], 'template': detailed['source']['template'],
                'climate_zone': unified['climate_zone'], 'set_id': sid, 'context': key, 'family': fam,
                'attic_id': entry['id'], 'package_file': package, 'package_sha256_4_0_0': sha,
                'roof_assembly_ids': ' '.join(c['assembly_id'] for c in roof['contributors']),
                'roof_reference_area_m2': roof['reference_area_m2'],
                'roof_u_W_m2_K': roof['contributors'][0]['u_reference_W_m2_K'] if len(roof['contributors']) == 1 else None,
                'roof_share_of_exterior_roof': roof['share_of_component_reference_area'],
                'unified_exterior_roof_u_W_m2_K': u_of('ExteriorRoof'),
                'other_exterior_parts': ' '.join(f"{p['role']}:{p['reference_area_m2']:.3f}" for p in entry['exterior_parts'] if p['role'] != 'ExteriorRoof'),
                'boundary_role': b['role'], 'boundary_assembly_ids': ' '.join(c['assembly_id'] for c in b['contributors']),
                'boundary_reference_area_m2': b['reference_area_m2'],
                'boundary_u_W_m2_K': b['contributors'][0]['u_reference_W_m2_K'] if len(b['contributors']) == 1 else None,
                'unified_boundary_role_u_W_m2_K': u_of(b['role']),
                'area_ratio_roof_to_boundary': entry['area_ratio_roof_to_boundary'],
                'attic_omitted_status': eq['status'], 'attic_omitted_assembly_id': eq.get('assembly_id'),
                'attic_omitted_u_W_m2_K': (eq.get('u_bounds_W_m2_K') or {}).get('equivalent_sealed_roof_only'),
                'u_sealed_all_exterior_W_m2_K': (eq.get('u_bounds_W_m2_K') or {}).get('sealed_all_exterior_parts'),
                'interior_ceiling_correction': correction.get('status'),
                'interior_ceiling_paired_area_m2': correction.get('paired_ceiling_area_m2')})
    return out


def write_inventory(rows, folder, meta):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=INVENTORY_FIELDS, lineterminator='\n')
    writer.writeheader()
    for row in rows:
        writer.writerow({k: ('' if row[k] is None else repr(row[k]) if isinstance(row[k], float) else row[k]) for k in INVENTORY_FIELDS})
    (folder/'attic_inventory.csv').write_bytes(buffer.getvalue().encode('utf-8'))
    (folder/'attic_inventory.json').write_bytes(document_bytes({**meta, 'rows': rows}))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--inventory', type=Path, metavar='DIR')
    parser.add_argument('--export', type=Path, metavar='DIR')
    parser.add_argument('--set')
    parser.add_argument('--context')
    parser.add_argument('--release', default=None)
    args = parser.parse_args(argv)
    from scripts import atlas_exports
    release = atlas_exports.Release(release=args.release or atlas_exports.IN_TREE[-1])
    only = (lambda s, k: s == args.set and (args.context is None or k == args.context)) if args.set else None
    if args.inventory:
        rows = inventory_rows(release, only)
        write_inventory(rows, args.inventory, {'release': f'atlas-release-{release.release}', 'method': METHOD, 'adr': ADR,
                                               'contexts_scanned': len([c for c in contexts(release) if not only or only(*c)])})
        print(f'{len(rows)} attic rows over {len({(r["set_id"], r["context"]) for r in rows})} contexts')
    if args.export:
        args.export.mkdir(parents=True, exist_ok=True)
        sums = []
        for sid, key in candidates(release, only):
            document, _ = export(release, sid, key)
            name = f'{sid}.{key}.unified.json'
            data = document_bytes(document)
            (args.export/name).write_bytes(data)
            sums.append(f'{hashlib.sha256(data).hexdigest()}  {name}')
        (args.export/'SHA256SUMS').write_bytes(('\n'.join(sorted(sums, key=lambda s: s.split('  ')[1]))+'\n').encode('utf-8'))
        print(f'{len(sums)} unified 4.1.0 documents written')


if __name__ == '__main__':
    main()
