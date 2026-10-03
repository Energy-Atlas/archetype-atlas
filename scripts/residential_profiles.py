"""Validate and prepare deterministic inputs for executed residential profiles."""
import calendar
import csv
import hashlib
import math
import argparse
import json
import subprocess
import zipfile
from pathlib import Path
import urllib.request
import uuid

from scripts.common import ROOT, load_json, dump_json
from scripts.runtime import fetch_runtime

PARAMETERS = ['County', 'Heating Setpoint', 'Cooling Setpoint',
              'Heating Setpoint Offset Magnitude', 'Cooling Setpoint Offset Magnitude',
              'Heating Setpoint Offset Period', 'Cooling Setpoint Offset Period',
              'Heating Unavailable Days', 'Cooling Unavailable Days', 'Dishwasher',
              'Clothes Washer', 'Clothes Dryer', 'Cooking Range', 'Ceiling Fan', 'Plug Loads']


def option_binding(path, parameter, option):
    matches = []
    with Path(path).open(encoding='utf-8', newline='') as stream:
        for line, values in enumerate(csv.reader(stream, delimiter='\t'), 1):
            if len(values) >= 2 and values[:2] == [parameter, option]:
                arguments = {}
                for value in values[3:]:
                    if '=' in value:
                        key, val = value.split('=', 1)
                        if key in arguments and arguments[key] != val:
                            raise ValueError('Conflicting exact argument binding')
                        arguments[key] = val
                matches.append({'parameter':parameter, 'option':option, 'line':line,
                                'measure':values[2] if len(values)>2 else None, 'arguments':arguments})
    if len(matches) != 1:
        raise ValueError(f'No unique exact schedule option: {parameter}/{option}')
    return matches[0]


def prepare_inputs(records, source, weather_archive, destination):
    source, destination = Path(source), Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    inputs = build_inputs(records, {'year':2007, 'timestep_minutes':60})
    lookup = source/'resources/options_lookup.tsv'
    mapping = source/'resources/hpxml-measures/HPXMLtoOpenStudio/resources/data/zipcode_weather_stations.csv'
    with mapping.open(encoding='utf-8', newline='') as stream:
        stations = {r['zipcode']:r for r in csv.DictReader(stream)}
    with zipfile.ZipFile(weather_archive) as archive:
        members = {}
        for name in archive.namelist():
            basename = Path(name).name
            if basename in members:
                raise ValueError('Ambiguous weather archive member')
            members[basename] = name
        for item in inputs:
            bindings = [option_binding(lookup, k, item['selected_options'][k]) for k in PARAMETERS]
            args = {}
            for binding in bindings:
                for k, v in binding['arguments'].items():
                    if k in args and args[k] != v:
                        raise ValueError('Conflicting selected schedule arguments')
                    args[k] = v
            station = stations[args['location_zip_code']]
            name = station['station_filename']
            data = archive.read(members[name])
            epw = destination/'weather'/name
            epw.parent.mkdir(exist_ok=True)
            if epw.exists() and epw.read_bytes() != data:
                raise ValueError('Never overwrite changed weather data')
            epw.write_bytes(data)
            item.update({'arguments':args, 'bindings':bindings,
                         'latitude':float(station['zipcode_latitude']),
                         'longitude':float(station['zipcode_longitude']),
                         'time_zone_utc_offset':float(station['zipcode_utc_offset']),
                         'weather':{'variant':'ZIP-mapped TMY3 station proxy; original county EPW unavailable (HTTP 403)',
                                    'original_path':args['location_epw_path'],
                                    'station_filename':name, 'sha256':hashlib.sha256(data).hexdigest(),
                                    'mapping_file':mapping.relative_to(source).as_posix(),
                                    'mapping_sha256':hashlib.sha256(mapping.read_bytes()).hexdigest(),
                                    'mapping_row':station, 'archive_member':members[name]},
                         'epw_path':str(epw.resolve())})
    dump_json(destination/'inputs.json', inputs)
    return inputs


def validate_profiles(path, metadata):
    rows = 0
    with Path(path).open(encoding='utf-8', newline='') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(metadata['columns']):
            raise ValueError('Profile columns do not match declared units')
        for row in reader:
            rows += 1
            for column, unit in metadata['columns'].items():
                value = float(row[column])
                if not math.isfinite(value) or (unit=='dimensionless' and not 0 <= value <= 1):
                    raise ValueError('Invalid profile value')
    days = 366 if calendar.isleap(metadata['year']) else 365
    step = metadata['timestep_minutes']
    if step <= 0 or 60 % step or rows != days*24*60//step:
        raise ValueError('Profile length does not match full calendar')
    return {'rows':rows, 'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest()}


def build_inputs(records, policy):
    inputs = []
    for record in records:
        occupants = record['occupants']
        if occupants < 0 or not math.isfinite(occupants) or occupants != int(occupants):
            raise ValueError('Generator requires explicit nonnegative integer occupants')
        item = {'record_id':record['id'], 'source_building_id':record['source_building_id'],
                'seed':int(record['source_building_id']), 'occupants':occupants,
                'year':policy['year'], 'timestep_minutes':policy['timestep_minutes'],
                'state':record['selected_options']['State'],
                'bedrooms':int(record['selected_options']['Bedrooms']),
                'selected_options':record['selected_options'],
                'heating_base_C':record['heating_base_C'], 'cooling_base_C':record['cooling_base_C']}
        if 'reference_location' in policy:
            item.update(policy['reference_location']); item['reference_context']=True
        inputs.append(item)
    return inputs


def fetch_weather(lock, destination):
    destination = Path(destination)
    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(lock['url'], headers={'User-Agent':'Atlas-Research'})
        with urllib.request.urlopen(request, timeout=60) as response, destination.open('xb') as stream:
            while data := response.read(1024*1024):
                stream.write(data)
    if destination.stat().st_size != lock['size_bytes'] or hashlib.sha256(destination.read_bytes()).hexdigest() != lock['sha256']:
        raise ValueError('Weather archive checksum or size mismatch')
    return destination


def collect_outputs(inputs, output):
    profiles = []
    for item in inputs:
        path = Path(output)/(item['record_id']+'.csv')
        with path.open(encoding='utf-8', newline='') as stream:
            reader = csv.DictReader(stream)
            columns = {k:('degC' if k.endswith('_setpoint') else 'dimensionless') for k in reader.fieldnames}
            series = {k:[] for k in columns}
            for row in reader:
                for k in columns:
                    series[k].append(float(row[k]))
        metadata = {k:v for k,v in item.items() if k != 'epw_path'}
        metadata.update(load_json(Path(output)/(item['record_id']+'.execution.json')))
        metadata.update({'columns':columns, 'interval_convention':'Values apply to hour [h,h+1) in local standard time; no DST/holiday overrides',
                         'profile_boundary':'Executed schedule-only variant; not a complete HPXML/EnergyPlus model',
                         'unresolved':['HVAC unavailable-day placement is not executed; thermostat profiles are nominal',
                                       'EV, refrigerator, freezer, exterior lighting and other non-exported end uses are not generated',
                                       'Source option usage multipliers/load magnitudes remain separate from normalized profile shapes']})
        metadata['provenance'] = {
            'source_project':'ResStock / bundled OpenStudio-HPXML 1.11.0',
            'source_revision':'dd25369f41a83a0767aefeeac0b6f8a0b0edd649',
            'source_locator':'resources/hpxml-measures/BuildResidentialScheduleFile/resources/schedules.rb#ScheduleGenerator.create/export',
            'thermostat_locator':'measures/ResStockArguments/measure.rb#modify_setpoint_schedule; resources/hpxml-measures/HPXMLtoOpenStudio/resources/hvac.rb#HVAC.apply_setpoints',
            'original_value':'Executed upstream CSV (sha256 below); selected_options and exact lookup bindings retained per input',
            'original_units':columns,
            'transformation':'Upstream stochastic normalization/export at 3 significant figures; upstream thermostat conversion F to degC, evaluated at hourly midpoints and rounded to 9 decimal places',
            'extraction_date':'2026-10-03',
            'interpretation':'Deterministic seeded realization with station-proxy weather; nominal setpoints before equipment unavailable-day overrides; original source nulls are unchanged'}
        if item['occupants'] == 0:
            metadata['unresolved'].append('Upstream skips stochastic generation for zero occupants; non-occupancy loads remain unresolved')
        metadata.update(validate_profiles(path, metadata))
        if any(h > c + 1e-8 for h,c in zip(series['heating_setpoint'],series['cooling_setpoint'])):
            raise ValueError('Executed thermostat overlap')
        artifact = {'metadata':metadata, 'series':series}
        # Canonical compact JSON; CSV remains an inspection/upstream execution artifact.
        profile = Path(output)/(item['record_id']+'.json')
        profile.write_text(json.dumps(artifact, separators=(',',':'), ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8', newline='\n')
        profiles.append({'record_id':item['record_id'], 'profile_file':profile.name,
                         'profile_sha256':hashlib.sha256(profile.read_bytes()).hexdigest(),
                         'csv_file':path.name, 'csv_sha256':metadata['sha256'],
                         'status':metadata['status'], 'columns':columns})
    dump_json(Path(output)/'profile-index.json', profiles)
    return profiles


def run_attempt(destination, producer, record_ids):
    """Record an isolated attempt before fetching/executing; publish only success."""
    destination=Path(destination).resolve()
    relative='attempts/'+str(uuid.uuid4())
    attempt=destination/relative
    (attempt/'output').mkdir(parents=True)
    receipt={'status':'running','attempt':relative,'output':relative+'/output',
             'expected_record_ids':record_ids}
    def record():
        dump_json(attempt/'run.json',receipt)
        # A failed/interrupted latest attempt must supersede a previous success.
        dump_json(destination/'latest-run.json',receipt)
    record()
    try:
        index=producer(attempt)
        if [p['record_id'] for p in index]!=record_ids:
            raise ValueError('Attempt record inventory is incomplete')
        receipt['profile_index_sha256']=hashlib.sha256((attempt/'output/profile-index.json').read_bytes()).hexdigest()
        receipt['status']='completed'
        record()
        return attempt/'output'
    except BaseException as error:
        receipt.update(status='failed',error_type=type(error).__name__,error=str(error))
        record()
        raise


def completed_output(destination):
    """Accept only a completed recorded attempt; raw stale output is rejected."""
    destination=Path(destination).resolve()
    receipt_path=destination/'latest-run.json'
    if not receipt_path.is_file():
        raise ValueError('A completed generation attempt is required; raw/stale output cannot be frozen')
    receipt=load_json(receipt_path)
    if receipt.get('status')!='completed':
        raise ValueError('Latest generation attempt must be completed before freezing')
    output=(destination/receipt['output']).resolve()
    if not output.is_relative_to(destination) or output==destination:
        raise ValueError('Unsafe completed attempt output path')
    index=load_json(output/'profile-index.json')
    if ([p['record_id'] for p in index]!=receipt['expected_record_ids'] or
            hashlib.sha256((output/'profile-index.json').read_bytes()).hexdigest()!=receipt['profile_index_sha256']):
        raise ValueError('Completed attempt index inventory/checksum mismatch')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, default=ROOT/'build/residential')
    parser.add_argument('--runtime', type=Path, default=ROOT/'build/runtime')
    parser.add_argument('--pilot', action='store_true')
    args = parser.parse_args()
    records = load_json(ROOT/'data/releases/v0.2.0/residential_archetypes.json')
    records=records[:1] if args.pilot else records
    def generate(attempt):
        runtime=fetch_runtime(load_json(ROOT/'sources/runtime-lock.json'),args.runtime)
        weather=fetch_weather(load_json(ROOT/'sources/weather-lock.json'),ROOT/'build/runtime-archives/usa-tmy3-epw.zip')
        inputs=prepare_inputs(records,runtime['rs'],weather,attempt)
        output=attempt/'output'
        subprocess.run([str(runtime['openstudio-windows']/'bin/openstudio.exe'),'execute_ruby_script',
                        str(ROOT/'scripts/run_residential_profiles.rb'),str(runtime['rs'].resolve()),
                        str((attempt/'inputs.json').resolve()),str(output.resolve())],check=True)
        return collect_outputs(inputs,output)
    output=run_attempt(args.destination,generate,[r['id'] for r in records])
    print(f'Validated {len(records)} annual profiles in completed attempt: {output}')


if __name__ == '__main__':
    main()
