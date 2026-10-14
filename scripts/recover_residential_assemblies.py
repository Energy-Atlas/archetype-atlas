"""Recover pinned ResStock above-ground ordered engine constructions only.

Run python -m scripts.recover_residential_assemblies [--check]. Native pilot
validation precedes the complete 41-fixture expansion. No systems/site build or
EnergyPlus execution is performed; source reference geometry is evidence only.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import tarfile

from scripts.recover_program_inputs import ROOT, SOURCE, RUNTIME, REVISION
from scripts.energy_json_review import material_requirements

DATE = '2026-10-14'
OUTPUT = ROOT / 'data/construction-inputs/residential-assemblies-v1.json'
WORK = ROOT / 'build/residential-assembly-recovery'
RESOURCES = 'resources/hpxml-measures/HPXMLtoOpenStudio/resources/'
R_SI = 0.1761  # Pinned unit_conversions.rb; intentionally not modernized.
SOURCE_UNITS = {'thickness_in': 'in', 'conductivity_Btu_h_ft_F': 'Btu/(h*ft*F)',
    'density_lb_ft3': 'lbm/ft3', 'specific_heat_Btu_lb_F': 'Btu/(lbm*F)',
    'resistance_h_ft2_F_Btu': 'h*ft2*F/Btu', 'thermal_absorptance': '1', 'solar_absorptance': '1',
    'ufactor_Btu_h_ft2_F': 'Btu/(h*ft2*F)', 'shgc': '1'}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n',
                    encoding='utf-8', newline='\n')


def parallel_r(recipe):
    """Independent parallel-path R check of source operands (films included)."""
    conductance = 0.0
    for i, fraction in enumerate(recipe['path_fractions']):
        path_r = sum(layer[0 if len(layer) == 1 else i]['resistance_m2_K_W']
                     for layer in recipe['layers'])
        conductance += fraction / path_r
    return 1 / conductance


def proof(original, locator, hashes, transformation, note, unit=None):
    return {'source_project': 'ResStock', 'source_revision': REVISION,
        'source_locator': locator, 'source_file_sha256': hashes,
        'extraction_date': DATE, 'original_value': original,
        'original_unit': unit or SOURCE_UNITS, 'transformation': transformation,
        'interpretation_note': note}


def normalized_recipe(recipe):
    return {'path_fractions': recipe['path_fractions'],
        'assembly_r_m2_K_W': None if recipe['assembly_r_h_ft2_F_Btu'] is None else recipe['assembly_r_h_ft2_F_Btu']*R_SI,
        'layers': [[dict(m, resistance_m2_K_W=None if m.get('resistance_h_ft2_F_Btu') is None
                       else m['resistance_h_ft2_F_Btu']*R_SI) for m in layer] for layer in recipe['source_layers']],
        'source_layer_names': recipe['source_layer_names']}


def normalize(raw, receipts):
    hashes = {p: receipts[p]['sha256'] for p in receipts if p.startswith('resstock/') and p.endswith('.rb')
              and any(p.endswith(n) for n in ['constructions.rb', 'materials.rb', 'model.rb', 'geometry.rb', 'defaults.rb', 'unit_conversions.rb'])}
    # Source shape is original HPXML evidence; remove SDK-generated area noise only.
    context = {s['id']: s for s in raw['source_context']}
    assemblies = []
    for a in raw['assemblies']:
        if a['name'].startswith('Adiabatic') and a['role'] in {'Window', 'Door', 'Skylight'}:
            continue  # Parent-buffer surfaces are geometry harness artifacts.
        model = 'simple_glazing' if a['layers'][0]['model'] == 'SimpleGlazing' else 'opaque_layers'
        surface_ids = [s['id'] for s in a['surfaces']]
        source_ids = sorted({s.split(':')[0] for s in surface_ids})
        source_rows = [context[k] for k in source_ids if k in context]
        attributes = [s['attributes'] for s in source_rows]
        if a['role'] == 'FloorCeiling':
            role = 'Ceiling' if attributes and attributes[0]['floor_or_ceiling'] == 'ceiling' else 'Floor'
        elif a['role'] == 'Wall':
            role = 'ExteriorWall' if attributes and attributes[0]['exterior_adjacent_to'] == 'outside' else 'InteriorWall'
        else:
            role = a['role']
        trace = [{'source_locator': Path(c['path']).relative_to(SOURCE).as_posix()+'#line='+str(c['line']),
                  'method': c['method']} for c in a['recipe']['caller_locations']]
        recipe = normalized_recipe(a['recipe'])
        evidence = proof(a['recipe'], RESOURCES+'constructions.rb#Construction/create_and_assign_constructions; '+
            RESOURCES+'geometry.rb#apply_'+a['role'].lower(), hashes,
            'Execute pinned source methods; preserve outside-to-inside layer order; films are calculation operands and excluded from engine layers.',
            'Source stock fixture, not a new code/prototype assembly. SDK getters record actual accepted engine properties.')
        evidence['original_value'] = {k: v for k, v in a['recipe'].items() if k != 'caller_locations'}
        evidence['parallel_recipe'] = recipe
        evidence['executed_source_branches'] = trace
        evidence['source_assignment_retained'] = a['source_assignment_retained']
        if not a['source_assignment_retained']:
            evidence['assignment_note'] = 'SDK drops this source adiabatic attached door SubSurface assignment. Exact source-constructed material object recovered independently; delivered consumer assigns its own valid surface.'
        layers = []
        for i, p in enumerate(a['layers']):
            p = dict(p)
            # SDK material sharing/suffixes depend on object handle iteration.
            # Source material names and physical properties are deterministic.
            p['name'] = a['recipe']['effective_materials'][i]['name']
            p.pop('sdk_default_flags', None)
            lp = proof(a['recipe']['effective_materials'][i], RESOURCES+
                'constructions.rb#Construction/get_parallel_material; Construction/create_os_material; '+RESOURCES+
                'materials.rb#Material; BaseMaterial; '+RESOURCES+'model.rb#add_opaque_material; add_simple_glazing', hashes,
                'Pinned UnitConversions: in*0.0254; Btu/(h*ft*F)*1.731; lbm/ft3*16.02; Btu/(lbm*F)*4187; U*5.678. SDK material/default getters are SI.',
                'Parallel layer density = sum(path_fraction*density); heat capacity is density-weighted. No mass inferred from R-value.')
            if p['model'] == 'SimpleGlazing' and p['visible_transmittance'] is None:
                p['visible_transmittance_mode'] = 'energyplus_autocalculate_from_shgc'
                lp['source_locator'] += '; EnergyPlus/Energy+.idd#WindowMaterial:SimpleGlazingSystem/Visible Transmittance'
                lp['source_file_sha256']['EnergyPlus/Energy+.idd'] = receipts['EnergyPlus/Energy+.idd']['sha256']
                lp['interpretation_note'] = 'Pinned source sets U and SHGC only. Native VT field is optional and remains unset; engine resolves visible optics from solar optics. No numerical VT is invented.'
            layers.append({'order': i+1, 'properties': p, 'evidence': lp})
        parameters = {}
        if model == 'opaque_layers':
            p = [l['properties'] for l in layers]
            r_layers = sum(m['thickness_m']/m['conductivity_W_m_K'] for m in p)
            film_r = sum(m[0]['resistance_m2_K_W'] for m in recipe['layers'] if m[0]['name'] == 'AirFilm')
            parameters = {'engine_layer_r_m2_K_W': r_layers,
                'source_film_r_m2_K_W': film_r,
                'u_W_m2_K_including_source_films': 1/(r_layers+film_r),
                'source_assembly_r_m2_K_W': recipe['assembly_r_m2_K_W'],
                'mass_per_area_kg_m2': sum(m['thickness_m']*m['density_kg_m3'] for m in p),
                'heat_capacity_per_area_J_m2_K': sum(m['thickness_m']*m['density_kg_m3']*m['specific_heat_J_kg_K'] for m in p)}
        binding = ['surface_area_m2', 'surface_adjacency']
        applicability = {'source_layer_orientation': 'exterior_to_interior',
                         'reverse_for_adjacent_surface': any(s['adjacent_reverse_construction'] for s in a['surfaces']),
                         'consumer_adjacent_surface_rule': 'Assign the reverse ordered construction to a paired adjacent surface, as pinned Construction.create_and_assign_constructions does. The boolean describes the source reference assignment only.'}
        if role == 'Roof':
            applicability['source_roof_pitch_rad'] = math.atan(attributes[0]['pitch']/12)
            applicability['roof_pitch_policy'] = 'Use this material recipe at the source pitch; rerun pinned roof film/insulation selection when binding a different pitch.'
            applicability['source_film_rule'] = 'Roof film R = (0.002*exp(0.0398*pitch_degrees)+0.608 + 0.32*exp(-0.0154*pitch_degrees)+0.6)/2 h*ft2*F/Btu; exterior R=0.197. Pinned Material.AirFilmRoof.'
            binding.append('compatible_roof_pitch_rad')
        if role == 'InteriorPartition':
            applicability.update(area_per_conditioned_floor_area=raw['partition_wall_mass']['area_fraction'],
                                 area_convention='source exposed partition area, both sides')
            binding = ['conditioned_floor_area_m2']
        if role == 'OrdinaryInteriorFloor':
            applicability.update(boundary='Adiabatic',
                source_reference_area_per_cfa=float(format(sum(s['area_m2'] for s in a['surfaces'])/
                    (raw['conditioned_floor_area_ft2']*0.09290304), '.9g')),
                consumer_area_rule='CFA minus floor/slab areas adjacent to conditioned space/basement; paired floor and ceiling each receive the remaining area; source threshold >1 ft2.')
            binding = ['ordinary_interstory_floor_area_m2']
        digest = hashlib.sha256(json.dumps({'record': raw['record_id'], 'name': a['name'],
            'role': role, 'source_ids': surface_ids, 'layers': [l['properties'] for l in layers]},
            sort_keys=True).encode()).hexdigest()[:20]
        assemblies.append({'id': 'residential-assembly-'+digest, 'name': a['name'], 'role': role,
            'model': model, 'layers': layers, 'source_surface_ids': surface_ids,
            'source_adjacency': [{'source_id': s['id'], 'interior': s['attributes'].get('interior_adjacent_to'),
                'exterior': s['attributes'].get('exterior_adjacent_to')} for s in source_rows],
            'required_bindings': binding, 'applicability': applicability, 'evidence': evidence,
            'parameters': parameters,
            'interpretation': 'Ordered pinned source engine assembly; source fixture reference geometry is provenance only. Consumer assigns compatible surfaces and areas.'})
        if role in {'Window', 'Skylight'}:
            modifiers = []
            for attrs in attributes:
                sf = {}
                for season in ('summer', 'winter'):
                    exterior = attrs.get('exterior_shading_factor_'+season)
                    exterior = 1.0 if exterior is None else exterior  # Exact source nil branch.
                    if attrs.get('exterior_shading_type') in {'external overhangs', 'awnings'} and (attrs.get('overhangs_depth') or 0) > 0:
                        exterior = 1.0
                    if attrs.get('exterior_shading_type') == 'building':
                        raise ValueError('Building exterior shading needs source neighbor binding')
                    screen = attrs.get('insect_screen_factor_'+season) if attrs.get('insect_screen_present') else 1.0
                    interior = attrs.get('interior_shading_factor_'+season)
                    if interior is None or screen is None:
                        raise ValueError('Missing active shading operand')
                    sf[season] = interior*exterior*screen
                if sf['summer'] != sf['winter']:
                    raise ValueError('Seasonal shade requires explicit source-date/weather recipe')
                shade = {'model': 'constant', 'value': sf['winter'],
                    'engine_object': 'SurfaceProperty:IncidentSolarMultiplier',
                    'evidence': proof(sf, RESOURCES+'constructions.rb#apply_window_skylight_shading; '+
                        RESOURCES+'defaults.rb#apply_windows; get_window_interior_shading_factors', hashes,
                        'Source summer/winter multiplier = interior_factor*exterior_factor*screen_factor. Both values are equal, so source produces a constant schedule independent of seasonal dates.',
                        'Apply this incident solar multiplier in addition to bare-glazing SHGC. Do not multiply U or reduce SHGC as a substitute.', '1')}
                overhang = {k.removeprefix('overhangs_')+'_m': None if attrs.get(k) is None else attrs[k]*0.3048
                            for k in ['overhangs_depth', 'overhangs_distance_to_top_of_window', 'overhangs_distance_to_bottom_of_window']}
                overhang['evidence'] = proof({k: attrs.get(k) for k in attrs if k.startswith('overhangs_') and not k.endswith('isdefaulted')},
                    RESOURCES+'geometry.rb#apply_windows', hashes, 'Source explicit lengths ft*0.3048; source window height = bottom distance minus top distance.',
                    'Geometry is a consumer input. Preserve source overhang geometry prescription; do not fold geometric shading into SHGC or the interior multiplier.', 'ft')
                modifiers.append({'incident_solar_multiplier': shade, 'overhang_geometry': overhang})
            if not modifiers:
                raise ValueError('Missing source glazing context')
            if any(m != modifiers[0] for m in modifiers):
                raise ValueError('Source glazing modifier ambiguity')
            assemblies[-1]['solar_modifiers'] = modifiers[0]
            if (attributes[0].get('overhangs_depth') or 0) > 0:
                assemblies[-1]['required_bindings'].append('source_compatible_overhang_geometry')
    # Deduplicate only identical physical/adjacency recipes within one fixture.
    # Source construction aliases/surface IDs survive; separate fixtures never merge.
    compact = {}
    for a in assemblies:
        key = json.dumps({'role': a['role'], 'model': a['model'],
            'properties': [l['properties'] for l in a['layers']], 'parameters': a['parameters'],
            'applicability': a['applicability'], 'bindings': a['required_bindings'],
            'adjacency': sorted({(s['interior'], s['exterior']) for s in a['source_adjacency']}),
            'solar_modifiers': a.get('solar_modifiers')}, sort_keys=True)
        if key not in compact:
            compact[key] = a
            a['source_construction_names'] = [a['name']]
        else:
            first = compact[key]
            first['source_surface_ids'].extend(a['source_surface_ids'])
            first['source_adjacency'].extend(a['source_adjacency'])
            first['source_construction_names'].append(a['name'])
    assemblies = list(compact.values())
    return {'id': raw['record_id'], 'assemblies': assemblies,
        'deferred_elements': [dict(e, disposition='combined_foundation_ground_deferred') for e in raw['deferred_elements']],
        'source_context': {'source_surface_attributes': context,
            'partition_wall_mass': raw['partition_wall_mass'],
            'context_provenance': proof('source_surface_attributes and partition_wall_mass hold original HPXML field values',
                'resources/hpxml-measures/BuildResidentialHPXML/measure.rb#set_roofs; set_walls; set_floors; set_windows; set_skylights; set_doors; '+
                RESOURCES+'defaults.rb#apply_roofs; apply_walls; apply_floors; apply_windows; apply_skylights; apply_doors; apply_partition_wall_mass',
                {p: receipts[p]['sha256'] for p in receipts if p in {
                    'resstock/resources/hpxml-measures/BuildResidentialHPXML/measure.rb',
                    'resstock/'+RESOURCES+'defaults.rb'}},
                'Original expanded/defaulted HPXML values, with *_isdefaulted flags. No geometry delivered; deterministic Index/vertex secondary sort only stabilizes generated evidence names.',
                'Geometry and native HPXML values are source reference evidence only; normalized executable SI engine materials are in assemblies[].layers[].properties.',
                {'area': 'ft2', 'azimuth': 'degree', 'pitch': 'inch rise per 12 inch run',
                 'interior_finish_thickness': 'in', 'insulation_assembly_r_value': 'h*ft2*F/Btu',
                 'r_value': 'h*ft2*F/Btu', 'ufactor': 'Btu/(h*ft2*F)',
                 'overhangs_depth': 'ft', 'overhangs_distance_to_top_of_window': 'ft',
                 'overhangs_distance_to_bottom_of_window': 'ft',
                 'shading_factors_coverage_shgc_absorptance_emittance': '1',
                 'source_types_ids_flags': 'categorical identifiers and boolean default flags'}),
            'reference_geometry_evidence': 'data/construction-inputs/geometry-v1.json#/residential/id='+raw['record_id'],
            'warnings': raw['warnings'], 'scope': 'above_ground_enclosure_only'}, 'unresolved': []}


def validate(packet):
    ids = set()
    for rid, r in packet['records'].items():
        if rid != r['id'] or r['unresolved'] or not r['assemblies']:
            raise ValueError('Incomplete residential fixture '+rid)
        for a in r['assemblies']:
            if a['id'] in ids:
                raise ValueError('Duplicate assembly')
            ids.add(a['id'])
            if a['role'] in {'FoundationWall', 'Slab', 'RimJoist', 'FloorOverFoundation'}:
                raise ValueError('Ground boundary violation')
            if a['role'] in {'Floor', 'Ceiling'} and any(
                any(v and (v.startswith(('basement', 'crawlspace')) or v in {'ground', 'manufactured home underbelly'})
                    for v in (s['interior'], s['exterior'])) for s in a['source_adjacency']):
                raise ValueError('Ground boundary adjacency violation')
            if a['role'] in {'Window', 'Skylight'}:
                modifier = a['solar_modifiers']['incident_solar_multiplier']
                original = modifier['evidence']['original_value']
                if (modifier['model'] != 'constant' or modifier['value'] != original['summer'] or
                        modifier['value'] != original['winter'] or not 0 <= modifier['value'] <= 1):
                    raise ValueError('Changed source shading factor')
            if [l['order'] for l in a['layers']] != list(range(1, len(a['layers'])+1)):
                raise ValueError('Invalid source layer order')
            for layer in a['layers']:
                p = layer['properties']
                required = material_requirements(p)
                if p['model'] == 'SimpleGlazing' and p.get('visible_transmittance_mode') == 'energyplus_autocalculate_from_shgc':
                    required = required-{'visible_transmittance'}
                for k in required:
                    if p.get(k) is None:
                        raise ValueError('Missing '+k)
                    if isinstance(p[k], (float, int)) and not math.isfinite(p[k]):
                        raise ValueError('Nonfinite '+k)
                for k in ('thickness_m', 'conductivity_W_m_K', 'density_kg_m3', 'specific_heat_J_kg_K', 'u_W_m2_K'):
                    if k in p and p[k] <= 0:
                        raise ValueError('Invalid '+k)
                for k in ('thermal_absorptance', 'solar_absorptance', 'visible_absorptance', 'shgc', 'visible_transmittance'):
                    if p.get(k) is not None and not 0 <= p[k] <= 1:
                        raise ValueError('Invalid '+k)
                if not layer['evidence']['source_file_sha256']:
                    raise ValueError('Missing provenance')
                original = layer['evidence']['original_value']
                conversions = {'thickness_m': ('thickness_in', .0254),
                    'conductivity_W_m_K': ('conductivity_Btu_h_ft_F', 1.731),
                    'density_kg_m3': ('density_lb_ft3', 16.02),
                    'specific_heat_J_kg_K': ('specific_heat_Btu_lb_F', 4187),
                    'u_W_m2_K': ('ufactor_Btu_h_ft2_F', 5.678)}
                for field, (native, factor) in conversions.items():
                    if field in p and not math.isclose(p[field], original[native]*factor, rel_tol=1e-12, abs_tol=0.0001):
                        raise ValueError('Engine/source '+field+' mismatch')
            if a['model'] == 'opaque_layers':
                recipe = a['evidence']['parallel_recipe']
                if not math.isclose(sum(recipe['path_fractions']), 1, abs_tol=1e-12):
                    raise ValueError('Invalid source path fractions')
                if not math.isclose(parallel_r(recipe), recipe['assembly_r_m2_K_W'], rel_tol=1e-12):
                    raise ValueError('Parallel source R mismatch')
                p = a['parameters']
                # Upstream R and conductivity use slightly inconsistent rounded
                # conversion constants (.1761 and 1.731); preserve their parity.
                if not math.isclose(p['engine_layer_r_m2_K_W']+p['source_film_r_m2_K_W'],
                                    p['source_assembly_r_m2_K_W'], rel_tol=0.0002):
                    raise ValueError('Engine/source R mismatch')
    return packet


def prepare():
    marker = read(SOURCE.parent/'.atlas-extraction.json')
    if sha(ROOT/'build/runtime/rs.tar.gz') != marker['archive_sha256']:
        raise ValueError('Residential archive checksum mismatch')
    receipts = {}
    with tarfile.open(ROOT/'build/runtime/rs.tar.gz') as archive:
        for member, local in [('resources/buildstock.rb', 'register-value.rb'),
                              ('measures/ResStockArgumentsPostHPXML/measure.rb', 'post-hpxml.rb')]:
            original = archive.extractfile(SOURCE.name+'/'+member).read()
            receipts['resstock/'+member] = {'sha256': hashlib.sha256(original).hexdigest(), 'source_revision': REVISION}
            if local == 'register-value.rb':
                start = original.index(b'def register_value(')
                original = original[start:original.index(b'\nend', start)+4]
            # Recover the same reviewed helpers in this task's private build
            # directory, so reproduction never requires the commercial harness.
            WORK.mkdir(parents=True, exist_ok=True)
            helper = WORK/local
            if helper.exists() and helper.read_bytes() != original:
                raise ValueError('Modified assembly helper '+local)
            helper.write_bytes(original)
    for p in SOURCE.rglob('*'):
        if not p.is_file() or p.suffix not in {'.rb', '.tsv', '.csv'}:
            continue
        rel = p.relative_to(SOURCE).as_posix()
        digest = sha(p)
        if digest != marker['files'].get(SOURCE.name+'/'+rel):
            raise ValueError('Modified residential source '+rel)
        receipts['resstock/'+rel] = {'sha256': digest, 'source_revision': REVISION}
    base = ROOT/'build/runtime/openstudio-windows'
    runtime = read(base/'.atlas-extraction.json')
    for p in [RUNTIME, RUNTIME.parent.parent/'EnergyPlus/Energy+.idd']:
        rel = p.relative_to(base).as_posix()
        if sha(p) != runtime['files'][rel]:
            raise ValueError('Modified runtime '+rel)
    receipts['EnergyPlus/Energy+.idd'] = {'sha256': sha(RUNTIME.parent.parent/'EnergyPlus/Energy+.idd'),
                                        'source_revision': 'OpenStudio-3.10.0+86d7e215a1/EnergyPlus-25.1.0'}
    return receipts, {'version': '3.10.0', 'runtime_executable_sha256': sha(RUNTIME),
                     'residential_archive_sha256': marker['archive_sha256']}


def native(inputs, name):
    write(WORK/(name+'-inputs.json'), inputs)
    subprocess.run([str(RUNTIME), str(ROOT/'scripts/recover_residential_assemblies.rb'), str(SOURCE),
        str(WORK/(name+'-inputs.json')), str(WORK/(name+'.json')),
        str(WORK/'register-value.rb'), str(WORK/'post-hpxml.rb'),
        str(ROOT/'scripts/recover_construction_geometry.rb')], check=True, cwd=ROOT, timeout=120)
    return read(WORK/(name+'.json'))


def recover():
    receipts, runtime = prepare()
    rows = read(ROOT/'data/releases/v0.2.0/residential_archetypes.json')
    options = {r['id']: r for r in read(ROOT/'data/releases/v0.2.0/residential_options.json')}
    inputs = [{'record_id': r['id'], 'arguments': {k: v for oid in r['option_ids']
        for k, v in options[oid]['arguments'].items()}} for r in rows]
    # Verify selected-option expansion against the already-validated harness input.
    previous_input = ROOT/'build/geometry-recovery/inputs.json'
    if previous_input.exists() and inputs != read(previous_input):
        raise ValueError('Selected fixture inputs differ from verified geometry recovery')
    pilot = native(inputs[:1], 'pilot')
    validate({'records': {pilot['results'][0]['record_id']: normalize(pilot['results'][0], receipts)}})
    all_raw = native(inputs, 'all')
    if all_raw['results'][0] != pilot['results'][0]:
        raise ValueError('Pilot differs after expansion')
    paths = ['data/releases/v0.2.0/residential_archetypes.json', 'data/releases/v0.2.0/residential_options.json',
             'scripts/recover_residential_assemblies.py', 'scripts/recover_residential_assemblies.rb',
             'scripts/recover_construction_geometry.rb', 'data/construction-inputs/geometry-v1.json']
    packet = {'schema_version': '1.0.0', 'kind': 'residential_above_ground_assembly_recovery',
        'extraction_date': DATE, 'input_sha256': {p: sha(ROOT/p) for p in paths},
        'source_files': receipts, 'runtime': runtime,
        'records': {r['record_id']: normalize(r, receipts) for r in all_raw['results']},
        'boundary': 'No foundation walls, slabs, rim joists or foundation-dependent floors; no systems or simulation.',
        'precision': 'Literal source tables preserved. SDK-derived roof-pitch degrees and reference area ratios use nine significant digits; no material physics is rounded. Source engine material suffix/default-flag metadata is excluded because SDK equivalent-material reuse order is nondeterministic.',
        'pilot': {'id': inputs[0]['record_id'], 'checks': ['parallel R', 'engine/source R', 'ordered SI layers', 'mass operands', 'boundary'],
                  'status': 'validated_before_expansion'}}
    validate(packet)
    return packet


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    packet = recover()
    if args.check:
        if packet != read(OUTPUT):
            raise ValueError('Residential assembly recovery is not reproducible')
    else:
        write(OUTPUT, packet)
    print(f"Verified {len(packet['records'])} residential fixtures / "+
          f"{sum(len(r['assemblies']) for r in packet['records'].values())} above-ground assemblies")


if __name__ == '__main__':
    main()
