"""Recover commercial conversion performance only; no model/site simulation.

python -m scripts.recover_dhw_conversion [--check]
"""
import argparse
import hashlib
import subprocess

from scripts.common import ROOT, load_json, dump_json
from scripts.definition_contract import canonical
from scripts.fetch import verify_file
from scripts.recover_program_inputs import RUNTIME
from scripts.energy_source_recovery import operand

OUTPUT = ROOT/'data/program-inputs/dhw-conversion-v1.json'
WORK = ROOT/'build/dhw-recovery'
MODEL = 'lib/openstudio-standards/standards/Standards.Model.rb'
RULE = 'lib/openstudio-standards/standards/Standards.WaterHeaterMixed.rb'
FACTORY = 'lib/openstudio-standards/service_water_heating/create_water_heater.rb'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def recover():
    lock = load_json(ROOT/'sources/dhw-conversion-evidence-lock.json')
    descriptors = {e['path']: e for e in lock['files']}
    extra = load_json(ROOT/'sources/definition-evidence-lock.json')['files']
    descriptors[MODEL] = next(e for e in extra if e['path'] == MODEL)
    sources = {p: verify_file(e) for p, e in descriptors.items()}
    runtime_root = ROOT/'build/runtime/openstudio-windows'
    runtime_marker = load_json(runtime_root/'.atlas-extraction.json')
    if digest(RUNTIME) != runtime_marker['files'][RUNTIME.relative_to(runtime_root).as_posix()]:
        raise ValueError('Modified pinned OpenStudio runtime')
    systems = load_json(ROOT/'data/system-inputs/source-v1.json')
    for path, entry in systems['source_files'].items():
        if path.endswith('.prototype_inputs.json'):
            sources[path] = verify_file(entry)
            descriptors[path] = entry
    rows = []
    for key, heater in systems['water_heaters'].items():
        if not key.startswith('source-water-heater-'):
            continue
        f = heater['fields']
        context = heater['source_context']
        temperature = f.get('service_water_temperature')
        if temperature is None:
            path, fragment = f['water_heater_capacity']['evidence']['source_locator'].split('#')
            index = int(fragment.split('/')[1])
            original = load_json(sources[path])['prototype_inputs'][index]['booster_water_temperature']
            evidence = dict(f['water_heater_capacity']['evidence'],
                            source_locator=path+f'#prototype_inputs/{index}/booster_water_temperature')
            temperature = operand(original, 'degF', 'degC', lambda v: (v-32)*5/9, evidence)
        variant = {'90.1-2007': 'ashrae_90_1_2007', '90.1-2013': 'ashrae_90_1_2013',
                   '90.1-2019': 'ashrae_90_1_2019', 'DOE Ref Pre-1980': 'doe_ref_pre_1980',
                   'DOE Ref 1980-2004': 'doe_ref_1980_2004'}[context['template']]
        table_path = next(p for p in sources if p.endswith('/'+variant+'.water_heaters.json'))
        rows.append({'id': key, **context, 'channel': heater['source_channel'], 'table_path': table_path,
                     'capacity_W': f['water_heater_capacity']['value'],
                     'volume_m3': f['water_heater_volume']['value'], 'fuel': f['water_heater_fuel']['value'],
                     'capacity_Btu_h': f['water_heater_capacity']['evidence']['original_value'],
                     'volume_US_gal': f['water_heater_volume']['evidence']['original_value'],
                     'temperature_degC': temperature['value'], 'temperature_operand': temperature})
    WORK.mkdir(parents=True, exist_ok=True)
    dump_json(WORK/'inputs.json', rows)
    subprocess.run([str(RUNTIME), str(ROOT/'scripts/recover_commercial_dhw.rb'),
                    str(ROOT/'data/raw/openstudio-standards'), str(WORK/'inputs.json'), str(WORK/'execution.json')],
                   cwd=ROOT, check=True, timeout=90, stdout=subprocess.DEVNULL)
    execution = {r['id']: r for r in load_json(WORK/'execution.json')}
    records = {}
    for row in rows:
        result = execution[row['id']]
        records[row['id']] = {'source_context': {k: row[k] for k in ('template', 'building_type', 'channel')},
            'status': 'known' if result['applied'] else 'unresolved_source_lookup',
            'conversion_efficiency': result['conversion_efficiency'],
            'fuel': {'Electricity': 'electricity', 'NaturalGas': 'natural gas'}[result['fuel']],
            'source_execution': result,
            'evidence': {'source_project': 'openstudio-standards',
                'source_revision': descriptors[RULE]['source_revision'], 'extraction_date': '2026-10-12',
                'source_locator': RULE+'#water_heater_mixed_apply_efficiency',
                'source_file_sha256': descriptors[RULE]['sha256'],
                'supporting_source_locators': [MODEL+'#model_find_objects', FACTORY+'#create_water_heater',
                    row['table_path']+'#water_heaters/'+str(result['requirement_index'])],
                'original_value': result['requirement'], 'original_unit': 'source performance rating fields',
                'transformation': 'Execute pinned factory, template lookup and heater thermal-efficiency setter; EF/UEF are not exported as conversion efficiency.',
                'interpretation_note': 'Nominal prototype capacity/volume select performance; not consumer sizing. Failed source lookups remain unknown; factory efficiency is diagnostic only.'},
            'nominal_operands': {**{k: systems['water_heaters'][row['id']]['fields'][k]
                                 for k in ('water_heater_capacity', 'water_heater_volume', 'water_heater_fuel')},
                                 'service_water_temperature': row['temperature_operand']}}
    return {'schema_version': '1.0.0', 'extraction_date': '2026-10-12',
        'input_sha256': {'data/system-inputs/source-v1.json': digest(ROOT/'data/system-inputs/source-v1.json')},
        'source_files': descriptors,
        'runtime': {'executable_sha256': digest(RUNTIME), 'archive_sha256': runtime_marker['archive_sha256'],
                    'bridge_sha256': digest(ROOT/'scripts/recover_commercial_dhw.rb')},
        'records': records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = recover()
    if args.check:
        if canonical(result) != canonical(load_json(OUTPUT)):
            raise SystemExit('DHW recovery differs from tracked artifact')
    else:
        dump_json(OUTPUT, result)
    known = sum(r['status']=='known' for r in result['records'].values())
    print(f'Commercial conversion performance: {known}/{len(result["records"])} source-resolved')


if __name__ == '__main__':
    main()
