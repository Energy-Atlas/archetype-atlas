"""Execute pinned residential formula methods and normalize program operands.

python -m scripts.recover_program_inputs
Inputs are immutable source releases plus checksum-locked ResStock/OpenStudio.
No EnergyPlus simulation is run; source CFA defaults size semantic loads only.
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

from scripts.definition_contract import stable_id

REVISION = 'dd25369f41a83a0767aefeeac0b6f8a0b0edd649'
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'build/runtime/rs' / ('resstock-' + REVISION)
RUNTIME = ROOT / 'build/runtime/openstudio-windows/OpenStudio-3.10.0+86d7e215a1-Windows/bin/openstudio.exe'
RESOLUTION = ROOT / 'data/resolution-releases/v0.4.0'
DATE = '2026-10-11'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8', newline='\n')


def annual_shape(name, shape):
    values = []
    for day in range(365):
        date = dt.date(2007, 1, 1) + dt.timedelta(days=day)
        values.extend(v * shape['monthly_multipliers'][date.month - 1] / shape['peak_divisor']
                      for v in shape['weekend_fractions' if date.weekday() > 4 else 'weekday_fractions'])
    return {'id': stable_id('recovered-schedule', {'name': name, 'shape': shape}), 'name': name,
            'type': 'annual', 'unit': '1', 'year': 2007, 'timestep_minutes': 60,
            'clock': 'local_standard_time', 'values': values,
            'source_context': {'variant': 'fixed_source_default_no_temperature_feedback', 'evidence': shape.get('evidence', [])}}


def prepare(source, work):
    rows = read(ROOT / 'data/releases/v0.2.0/residential_archetypes.json')
    options = {x['id']: x for x in read(ROOT / 'data/releases/v0.2.0/residential_options.json')}
    marker = read(source.parent / '.atlas-extraction.json')
    files = {}
    archive = ROOT / 'build/runtime/rs.tar.gz'
    if digest(archive) != marker['archive_sha256']:
        raise ValueError('Modified source retrieval archive')
    # Earlier schedule extraction omitted the post-HPXML usage calibration.
    # Retrieve this exact file from the locked archive without mutating it.
    post_path = 'measures/ResStockArgumentsPostHPXML/measure.rb'
    with tarfile.open(archive) as tar:
        post_bytes = tar.extractfile(source.name + '/' + post_path).read()
    files[post_path] = hashlib.sha256(post_bytes).hexdigest()
    (work / 'post-hpxml.rb').write_bytes(post_bytes)
    # Every loaded upstream Ruby method and option table is checked against the
    # checksum-locked archive extraction, not merely trusted because it exists.
    for path in source.rglob('*'):
        if path.is_file() and (path.suffix in {'.rb', '.tsv'} or path.name == 'default_schedules.csv'):
            relative = path.relative_to(source).as_posix()
            sha = digest(path)
            if marker['files'][source.name + '/' + relative] != sha:
                raise ValueError('Modified pinned source: ' + relative)
            files[relative] = sha
    prepared = []
    profiles = {}
    descriptors = {x['record_id']: x for x in read(RESOLUTION / 'profile-index.json')}
    for row in rows:
        profile_path = RESOLUTION / 'profiles' / (row['id'] + '.json')
        if digest(profile_path) != descriptors[row['id']]['profile_sha256']:
            raise ValueError('Modified frozen schedule: ' + row['id'])
        profile = read(profile_path)
        profiles[row['id']] = profile
        weather = profile['metadata']['weather']
        epw = ROOT / 'build/residential/weather' / weather['station_filename']
        if digest(epw) != weather['sha256']:
            raise ValueError('Modified frozen weather proxy: ' + str(epw))
        arguments = {k: v for oid in row['option_ids'] for k, v in options[oid]['arguments'].items()}
        prepared.append({'record_id': row['id'], 'occupants': row['occupants'],
                         'bedrooms': int(row['selected_options']['Bedrooms']), 'arguments': arguments,
                         'epw_path': str(epw), 'weather_sha256': weather['sha256']})
    write(work / 'inputs.json', prepared)
    return rows, profiles, files, marker['archive_sha256']


def normalize(rows, profiles, execution, files, archive_sha):
    descriptors = {x['record_id']: x for x in read(RESOLUTION / 'profile-index.json')}
    fixed = read(RESOLUTION / 'fixed-background-schedules.json')['schedules']
    schedules = {k: annual_shape(k, v) for k, v in fixed.items()}
    # Additional refrigerator has its own source table, even when the numerical
    # values happen to equal the primary refrigerator fixed variant.
    with (SOURCE / 'resources/hpxml-measures/HPXMLtoOpenStudio/resources/data/default_schedules.csv').open(encoding='utf-8') as stream:
        defaults = list(csv.reader(stream))
    default_file = 'resources/hpxml-measures/HPXMLtoOpenStudio/resources/data/default_schedules.csv'
    for name in ['extra_refrigerator', 'plug_loads_well_pump', 'fuel_loads_grill', 'fuel_loads_lighting', 'fuel_loads_fireplace', 'pool_pump', 'pool_heater', 'permanent_spa_pump', 'permanent_spa_heater']:
        table = {r[1]: [float(x) for x in r[2].split(',')] for r in defaults if r[0] == name}
        shape = {out_key: table[in_key] for out_key, in_key in [('weekday_fractions', 'WeekdayScheduleFractions'), ('weekend_fractions', 'WeekendScheduleFractions'), ('monthly_multipliers', 'MonthlyScheduleMultipliers')]}
        shape['peak_divisor'] = max(shape['weekday_fractions'] + shape['weekend_fractions']) * max(shape['monthly_multipliers'])
        shape['evidence'] = [{'source_locator': default_file + f'#row={i}/{r[1]}', 'source_revision': REVISION,
                             'source_file_sha256': files[default_file], 'original_value': r[2], 'original_unit': '1',
                             'transformation': 'parse 24-hour or 12-month fractions in source order; multiply month/day shapes and peak-normalize',
                             'extraction_date': DATE, 'interpretation_note': 'Native fixed source schedule; extra refrigeration extends the approved fixed background variant.'}
                            for i, r in enumerate(defaults, 1) if r[0] == name and r[1] in ['WeekdayScheduleFractions', 'WeekendScheduleFractions', 'MonthlyScheduleMultipliers']]
        schedules[name] = annual_shape(name, shape)
    out = {'schema_version': '1.0.0', 'source_revision': REVISION, 'extraction_date': DATE,
           'source_repository': 'https://github.com/NatLabRockies/ResStock',
           'source_archive_url': 'https://codeload.github.com/NatLabRockies/ResStock/tar.gz/' + REVISION,
           'source_archive_sha256': archive_sha, 'source_files': files,
           'runtime_version': execution['runtime_version'], 'records': {}, 'schedules': {s['id']: s for s in schedules.values()}}
    original = {x['id']: x for x in rows}
    options = {x['id']: x for x in read(ROOT / 'data/releases/v0.2.0/residential_options.json')}
    provenance = {x['id']: x for x in read(ROOT / 'data/releases/v0.2.0/provenance.json')}
    for result in execution['results']:
        rid = result['record_id']; row = original[rid]
        profile = profiles[rid]
        record = {'loads': [], 'controls': result['controls'],
                  'climate': row['source_context'].get('ASHRAE IECC Climate Zone 2004'), 'vintage': row['source_context'].get('Vintage'),
                  'unresolved': [], 'metadata': {'source_cfa_ft2': result['source_cfa_ft2'], 'source_garage_area_ft2': result['source_garage_area_ft2'],
                    'original_selected_options': row['selected_options'], 'expanded_source_arguments': result['expanded_arguments'],
                    'water_supply_degF': result['water_supply_degF'],
                    'weather': profile['metadata']['weather'], 'excluded_channels': ['electric_vehicle'],
                    'scope_note': 'Preserves prior schedule-release exclusions. Source geometry defaults only size program loads, not delivered geometry.'}}
        control_file = 'resources/hpxml-measures/HPXMLtoOpenStudio/resources/internal_gains.rb'
        record['metadata']['controls_evidence'] = {'source_locator': control_file + '#InternalGains.apply_building_occupants; defaults.rb#Defaults.get_occupancy_values',
              'source_revision': REVISION, 'source_file_sha256': files[control_file], 'original_value': {'sensible_Btu_person_day': 3716, 'latent_Btu_person_day': 2884, 'hours_per_day': 16.5},
              'original_unit': 'Btu/person/day and hours/day', 'transformation': '(3716+2884)/16.5 * pinned Btu/hr-to-W; sensible=3716/6600; native People radiant field=0.558*sensible',
              'extraction_date': DATE, 'interpretation_note': 'Native People assignment; no People object is required for zero occupants.'}
        record['metadata']['source_option_disabled'] = ([{'option': 'Misc Hot Tub Spa', 'selected_value': 'Other Fuel', 'resolved_argument': 'misc_permanent_spa=None',
                                                       'interpretation_note': 'Pinned options_lookup explicitly models this stock selection with no spa object; not a physical zero assertion.'}]
                                                     if row['selected_options'].get('Misc Hot Tub Spa') == 'Other Fuel' else [])
        record['metadata']['option_bindings'] = [{'parameter': options[oid]['parameter'], 'option': options[oid]['option'],
              'arguments': options[oid]['arguments'], 'source_locator': provenance[options[oid]['provenance_id']]['locator']}
              for oid in row['option_ids']]
        for item in result['loads']:
            name = item['end_use']
            schedule = schedules.get(name)
            values = profile['series'].get(name)
            sid = None
            if values is not None:
                sid = stable_id('residential-schedule', {'source': rid, 'channel': name, 'profile_sha256': descriptors[rid]['profile_sha256']})
            elif schedule is not None:
                sid = schedule['id']; values = schedule['values']
            energy = item.get('annual_kwh')
            amount = energy if energy is not None else item['daily_gallons'] * 365 * 0.003785411784
            eflh = sum(values) if values is not None else 0
            if amount > 0 and eflh <= 0:
                record['unresolved'].append({'end_use': name, 'reason': 'Positive source demand has no positive resolved schedule', 'annual_amount': amount})
                continue
            value = 0 if amount == 0 else (amount * 1000 / eflh if energy is not None else amount / (eflh * 3600))
            method = item['method']
            file = 'resources/hpxml-measures/HPXMLtoOpenStudio/resources/' + ('hotwater_appliances.rb' if method.startswith('HotWater') else 'lighting.rb' if method.startswith('Lighting') else 'hvac.rb' if method.startswith('HVAC') else 'defaults.rb')
            evidence = {'source_project': 'ResStock', 'source_revision': REVISION,
                        'source_locator': file + '#' + method, 'source_file_sha256': files[file],
                        'original_value': {k: v for k, v in item.items() if k in {'annual_kwh', 'annual_therm', 'daily_gallons', 'heat_fractions', 'target_temperature_degC'}},
                        'original_unit': 'kWh/year' if energy is not None else 'US gal/day',
                        'transformation': 'annual kWh * 1000 / schedule EFLH' if energy is not None else 'gal/day * 365 * 0.003785411784 / (schedule EFLH * 3600)',
                        'equivalent_full_load_hours': eflh, 'extraction_date': DATE,
                        'supporting_source_locators': ['resources/options_lookup.tsv', 'measures/ResStockArguments/measure.rb#run', 'measures/ResStockArgumentsPostHPXML/measure.rb#296-356',
                                                      'resources/hpxml-measures/BuildResidentialHPXML/measure.rb#set_*', 'resources/hpxml-measures/HPXMLtoOpenStudio/resources/defaults.rb',
                                                      'resources/hpxml-measures/HPXMLtoOpenStudio/resources/model.rb', 'resources/hpxml-measures/HPXMLtoOpenStudio/resources/misc_loads.rb'],
                        'interpretation_note': 'Executed source operational branch with exact options and source defaults; fixed background schedule variant; per dwelling unit. Source option/default inputs are retained in record metadata.'}
            load = {'end_use': name, 'type': 'water' if energy is None else 'lighting' if name.startswith('lighting_') else 'equipment',
                    'value': value, 'unit': 'm3/s' if energy is None else 'W', 'basis': 'dwelling_unit',
                    'host': item['host'], 'schedule_id': sid, 'evidence': evidence}
            for key in ['fuel', 'heat_fractions', 'target_temperature_degC']:
                if key in item:
                    load[key] = item[key]
            record['loads'].append(load)
        out['records'][rid] = record
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'data/program-inputs/residential-v1.json')
    parser.add_argument('--work', type=Path, default=ROOT / 'build/program-recovery')
    args = parser.parse_args()
    args.work.mkdir(parents=True, exist_ok=True)
    rows, profiles, files, archive = prepare(SOURCE, args.work)
    runtime_lock = read(ROOT / 'build/runtime/openstudio-windows/.atlas-extraction.json')
    runtime_key = RUNTIME.relative_to(ROOT / 'build/runtime/openstudio-windows').as_posix()
    if digest(RUNTIME) != runtime_lock['files'][runtime_key]:
        raise ValueError('Modified pinned OpenStudio runtime')
    subprocess.run([str(RUNTIME), str(ROOT / 'scripts/recover_residential_inputs.rb'), str(SOURCE), str(args.work / 'inputs.json'), str(args.work / 'execution.json'), str(args.work / 'post-hpxml.rb')], check=True, cwd=ROOT)
    result = normalize(rows, profiles, read(args.work / 'execution.json'), files, archive)
    result['runtime_archive_sha256'] = runtime_lock['archive_sha256']
    result['runtime_executable_sha256'] = digest(RUNTIME)
    write(args.output, result)
    print(f"Recovered {len(result['records'])} residential programs; {sum(len(x['unresolved']) for x in result['records'].values())} unresolved channels")


if __name__ == '__main__':
    main()
