"""Extract and freeze the finite, reviewed Medium Office fixture-draw equivalent."""
import argparse
import copy
import hashlib
import math
from pathlib import Path
import shutil

import jsonschema

from scripts.common import ROOT, dump_json, load_atlas, load_json, stable_id
from scripts.fetch import verify_file
from scripts.release import verify_release
from scripts.semantics import osm_objects, profile

BASE = ROOT/'data/releases/v0.2.0'
DEFAULT = ROOT/'data/water-releases/v0.1.0'
LOCK = ROOT/'sources/water-evidence-lock.json'
PROGRAM = 'program-29f8fa7a1d5e5afcf1f0'
SCHEDULE = 'schedule-1a7eda5cfd8f681cc7d7'
PROTOTYPE = 'lib/openstudio-standards/standards/ashrae_90_1/ashrae_90_1_2013/data/ashrae_90_1_2013.prototype_inputs.json'
RECIPE = 'lib/openstudio-standards/standards/Standards.ServiceWaterHeating.rb'
GEOMETRY = 'data/geometry/ASHRAEMediumOffice.osm'
SCHEMA = ROOT/'schemas/water-equivalent.schema.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(data=None, lock_path=LOCK, cache_root=ROOT/'data/raw'):
    data = data or load_atlas(BASE)
    lock = load_json(lock_path)
    files = {e['path']:e for e in lock['files']}
    paths = {p:verify_file(e, cache_root) for p,e in files.items()}
    row = next(p for p in data['programs'] if p['id'] == PROGRAM)
    if (row['building_type'], row['template'], row['source_space_type'], row['service_water_heating_schedule_id']) != (
            'MediumOffice', '90.1-2013', 'WholeBuilding - Md Office', SCHEDULE):
        raise ValueError('Unreviewed or conflicting program water mapping')
    attrs = row['source_attributes']
    flow = attrs['service_water_heating_peak_flow_per_area']
    if type(flow) not in (int, float) or not math.isfinite(flow) or flow <= 0:
        raise ValueError('Missing or invalid source water flow')
    inputs = load_json(paths[PROTOTYPE])['prototype_inputs']
    matches = [(i,r) for i,r in enumerate(inputs)
               if r['template'] == row['template'] and r['building_type'] == row['building_type']]
    if len(matches) != 1:
        raise ValueError('Ambiguous prototype input')
    input_index, prototype = matches[0]
    if (prototype['main_water_heater_volume'] is None
            or prototype['main_service_water_peak_flowrate'] is not None
            or prototype['main_service_water_flowrate_schedule'] != attrs['service_water_heating_schedule']
            or prototype['booster_water_heater_volume'] is not None
            or prototype['laundry_water_heater_volume'] is not None):
        raise ValueError('Prototype no longer follows the reviewed space-type draw path')
    spaces = sorted({n for m in data['mappings'] if m['program_id'] == PROGRAM
                     for n in m['source_space_names']})
    objects = osm_objects(paths[GEOMETRY].read_text(encoding='utf-8'))
    handles = {o['fields']['Handle'] for o in objects if o['kind'] == 'OS:SpaceType'
               and o['fields']['Standards Space Type'] == row['source_space_type']}
    tagged = sorted(o['fields']['Name'] for o in objects if o['kind'] == 'OS:Space'
                    and o['fields']['Space Type Name'] in handles)
    if spaces != tagged or len(spaces) != 15:
        raise ValueError('Source space-to-program mapping mismatch')
    source = next(s for s in data['schedules'] if s['id'] == SCHEDULE)
    if source['units'] != 'dimensionless' or source['interpolation'] != 'none':
        raise ValueError('Unsupported draw schedule units/interpolation')
    divisor = max(v for r in source['rules'] for v in r['values'])
    if not math.isfinite(divisor) or divisor <= 0 or any(
            not math.isfinite(v) or not 0 <= v <= 1 for r in source['rules'] for v in r['values']):
        raise ValueError('Invalid fractional draw schedule')
    equivalent = copy.deepcopy(source)
    equivalent.pop('provenance_id')
    equivalent['id'] = stable_id('water_schedule', PROGRAM, SCHEDULE, 'peak_normalized')
    equivalent['source_name'] = 'Medium Office fixture draw equivalent (peak normalized)'
    for rule in equivalent['rules']:
        rule['values'] = [v/divisor for v in rule['values']]
    # US gallon and international square foot, matching the upstream gal/h.ft2 path.
    rated = flow * 0.003785411784 / 3600 / 0.09290304
    provenance = {p['id']:p for p in data['provenance']}
    source_files = {s['id']:s for s in data['source_files']}
    def proof(path, locator, original, unit, transform, note):
        e = files[path]
        return {'source_locator':path+'#'+locator, 'source_revision':e['source_revision'],
                'source_file_sha256':e['sha256'], 'original_value':original,
                'original_unit':unit, 'transformation':transform,
                'extraction_date':lock['retrieval_date'], 'interpretation_note':note}
    p = provenance[row['provenance_id']]
    spcpath = source_files[p['source_file_id']]['path']
    s = provenance[source['provenance_id']]
    schpath = source_files[s['source_file_id']]['path']
    basis = 'Source space-type fixture draw path; aggregated to the existing office program. No new restroom program or physical fixture location is inferred.'
    packet = {'schema_version':'0.1.0', 'release_version':'0.1.0', 'base_release':'v0.2.0',
              'program_id':PROGRAM, 'building_type':row['building_type'], 'template':row['template'],
              'variant':'source_conserving_fixture_draw_equivalent', 'status':'allocation_equivalent',
              'source_schedule_id':SCHEDULE, 'source_space_names':spaces,
              'allocation_weight':1, 'physical_fixture_locations':[],
              'rated_flow_m3_s_m2':rated, 'equivalent_peak_flow_m3_s_m2':rated*divisor,
              'peak_divisor':divisor, 'target_temperature_degC':(attrs['service_water_heating_target_temperature']-32)/1.8,
              'equivalent_schedule':equivalent,
              'interpretation':basis+' Draw is mixed fixture water at the source target temperature, not water-heater energy, heater firing, circulation or the hot/cold mixing fraction. Apply once per represented office floor area, including each zone multiplier once; never also add a building-wide copy.',
              'conservation':'For every source selector/date/hour and represented office area A, A * rated_flow * source_fraction = A * equivalent_peak_flow * normalized_fraction. Distinct source spaces are deduplicated across HVAC mappings; area is supplied by the geometry atlas.',
              'newly_resolved_missing_schedules':0}
    rateproof = proof(spcpath,p['locator']+'/service_water_heating_peak_flow_per_area',flow,'US gal/h/ft2',
                      'Multiply by 0.003785411784 / 3600 / 0.09290304 to obtain m3/s/m2',basis)
    ruleproof = proof(schpath,s['locator'],source['rules'],'dimensionless fractions; dates/day selectors/order retained',
                      'Divide every rule value by the maximum source fraction 0.57; multiply rated flow by the same divisor to conserve source draw',basis)
    recipeproof = proof(RECIPE,'model_add_swh and model_add_swh_end_uses_by_space',
                        'Iterate source space-type map; flow_per_area * space.floorArea * space.multiplier; create_water_use',
                        'code', 'Follow the pinned default is_flow_per_area=true branch; deduplicate space identities',basis)
    packet['evidence'] = [rateproof,ruleproof,recipeproof,
        proof(PROTOTYPE,f'/prototype_inputs/{input_index}',prototype,'mixed source units',
              'Confirm MediumOffice/90.1-2013 main water loop and per-space path; no booster/laundry',basis),
        proof(GEOMETRY,'OS:SpaceType/Standards Space Type and OS:Space/Space Type Name',spaces,
              'source space names', 'Match exact source tags to existing mapping IDs; no geometry inferred',basis),
        proof(spcpath,p['locator']+'/service_water_heating_target_temperature',attrs['service_water_heating_target_temperature'],
              'degF','Convert (degF - 32) / 1.8 to degC',basis)]
    packet['field_provenance'] = {k:[0,1,2,3,4] for k in packet if k not in {'schema_version','release_version','base_release','evidence'}}
    packet['field_provenance']['target_temperature_degC'] = [5]
    # Exhaustive day-selector comparisons include both design days and holidays.
    for day in ['Mon','Tue','Wed','Thu','Fri','Sat','Sun','Hol','SmrDsn','WntrDsn']:
        for date in ['01-01','06-15','12-31']:
            for a,b in zip(profile(source['rules'],day,date),profile(equivalent['rules'],day,date)):
                if not math.isclose(rated*a,rated*divisor*b,rel_tol=1e-12,abs_tol=1e-16):
                    raise ValueError('Water draw conservation failed')
    return packet


def validate_bundle(path=DEFAULT):
    path = Path(path)
    manifest = load_json(path/'manifest.json')
    if verify_release(BASE) or manifest['base_manifest_sha256'] != sha(BASE/'manifest.json'):
        raise ValueError('Base release integrity mismatch')
    actual = {p.relative_to(path).as_posix() for p in path.rglob('*') if p.is_file()}
    if actual != set(manifest['files']) | {'manifest.json'}:
        raise ValueError('Water supplement inventory mismatch')
    for name,e in manifest['files'].items():
        p = (path/name).resolve()
        if not p.is_relative_to(path.resolve()) or sha(p) != e['sha256'] or p.stat().st_size != e['size_bytes']:
            raise ValueError('Water supplement checksum/path mismatch')
    packet = load_json(path/'water-equivalent.json')
    jsonschema.validate(packet,load_json(path/'schemas/water-equivalent.schema.json'))
    if packet != build(lock_path=path/'sources/water-evidence-lock.json'):
        raise ValueError('Water equivalent does not reproduce pinned sources')
    if manifest['release_version'] != packet['release_version'] or manifest['schema_version'] != packet['schema_version']:
        raise ValueError('Water manifest metadata mismatch')
    return packet


def freeze(target=DEFAULT):
    target = Path(target)
    if target.exists():
        raise ValueError('Never overwrite a frozen water release')
    if verify_release(BASE):
        raise ValueError('Base release integrity mismatch')
    packet = build()
    jsonschema.validate(packet,load_json(SCHEMA))
    dump_json(target/'water-equivalent.json',packet)
    for name in ['schemas/water-equivalent.schema.json','sources/water-evidence-lock.json',
                 'sources/licenses/openstudio-standards.txt','scripts/water_equivalent.py',
                 'docs/adr/0007-program-water-equivalents.md','LICENSE']:
        dst = target/name
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,dst)
    dump_json(target/'manifest.json',{'release_version':'0.1.0','schema_version':'0.1.0',
        'base_release':'v0.2.0','base_manifest_sha256':sha(BASE/'manifest.json'),
        'generation_date':load_json(LOCK)['retrieval_date'],
        'files':{p.relative_to(target).as_posix():{'sha256':sha(p),'size_bytes':p.stat().st_size}
                 for p in sorted(target.rglob('*')) if p.is_file()}})
    return validate_bundle(target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify',action='store_true')
    parser.add_argument('--target',type=Path,default=DEFAULT)
    args = parser.parse_args()
    packet = validate_bundle(args.target) if args.verify else freeze(args.target)
    print('Water pilot verified: existing office program; peak divisor',packet['peak_divisor'],
          '; 15 deduplicated source spaces; 0 newly missing schedules resolved')


if __name__ == '__main__':
    main()
