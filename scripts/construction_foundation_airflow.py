"""Pinned foundation-host airflow in SI; source recovery is explicit only."""
import argparse
import math
import subprocess
from scripts.common import ROOT,load_json,dump_json
from scripts.construction_foundation_recovery import sha,DATE
from scripts.recover_program_inputs import RUNTIME,SOURCE

OUTPUT=ROOT/'data/construction-inputs/foundation-airflow-v1.json'


def garage_coefficients(parameters,*,volume_m3,height_m,foundation_top_m,exterior_ach50_per_s):
    values=(volume_m3,height_m,foundation_top_m,exterior_ach50_per_s)
    if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in values):raise ValueError('Missing garage airflow geometry/pressure input')
    if volume_m3<=0 or height_m<=0 or height_m+foundation_top_m<=0 or exterior_ach50_per_s<0:raise ValueError('Invalid garage airflow operands')
    return {'effective_leakage_area_m2':parameters['ela_volume_coefficient_s_m']*exterior_ach50_per_s*volume_m3,
        'stack_coefficient_m2_s2_K':parameters['stack_height_coefficient_m_s2_K']*height_m,
        'wind_coefficient':parameters['wind_coefficient_scale']*((height_m+foundation_top_m)/parameters['wind_reference_height_m'])**parameters['wind_height_exponent']}


def validate(packet):
    for r in packet['records'].values():
        for p in r['probes']:
            got=garage_coefficients(r,volume_m3=1,height_m=p['height_m'],foundation_top_m=p['foundation_top_m'],exterior_ach50_per_s=1/3600)
            if not math.isclose(got['wind_coefficient'],p['wind_coefficient'],abs_tol=1e-12):raise ValueError('Source garage wind coefficient mismatch')
            if not math.isclose(got['stack_coefficient_m2_s2_K'],p['stack_coefficient_m2_s2_K'],abs_tol=1e-12):raise ValueError('Source garage stack coefficient mismatch')


def recover():
    # Verify the complete source tree and runtime against their locked archives.
    from scripts.recover_construction_geometry import prepare_sources
    prepare_sources()
    work=ROOT/'build/foundation-recovery'
    rows=load_json(ROOT/'data/releases/v0.2.0/residential_archetypes.json')
    options={r['id']:r for r in load_json(ROOT/'data/releases/v0.2.0/residential_options.json')}
    inputs=[{'record_id':r['id'],'arguments':{k:v for oid in r['option_ids'] for k,v in options[oid]['arguments'].items()}} for r in rows]
    dump_json(work/'airflow-input.json',inputs)
    subprocess.run([str(RUNTIME),str(ROOT/'scripts/recover_foundation_airflow.rb'),str(SOURCE),str(work/'airflow-input.json'),str(work/'airflow-native.json'),
        str(ROOT/'build/geometry-recovery/register-value.rb'),str(ROOT/'build/geometry-recovery/post-hpxml.rb'),str(ROOT/'scripts/recover_construction_geometry.rb')],check=True,cwd=ROOT,timeout=120)
    native=load_json(work/'airflow-native.json')
    paths=[ROOT/'scripts/construction_foundation_airflow.py',ROOT/'scripts/recover_foundation_airflow.rb',
        ROOT/'sources/foundation-ground-source-lock.json',ROOT/'data/construction-inputs/geometry-v1.json']
    packet={'schema_version':'1.0.0','kind':'internal_foundation_host_airflow','extraction_date':DATE,
        'records':{r['record_id']:r for r in native['results']},
        'input_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in paths},
        'provenance':{'source_project':'ResStock','source_revision':'dd25369f41a83a0767aefeeac0b6f8a0b0edd649',
            'source_locator':'resources/hpxml-measures/HPXMLtoOpenStudio/resources/airflow.rb#set_wind_speed_correction; get_infiltration_SLA_from_ACH50; calc_wind_stack_coeffs; apply_infiltration_to_garage; apply_infiltration_to_unconditioned_space',
            'source_file_sha256':sha(SOURCE/'resources/hpxml-measures/HPXMLtoOpenStudio/resources/airflow.rb'),
            'original_value':'Each record retains explicit source constants and numerical SI probes',
            'original_unit':'source constants have native units in their names; SI coefficient units in exported names; SLA and wind coefficients dimensionless',
            'transformation':'Execute pinned source helpers at declared unit-test dimensions; normalize homogeneous height/volume scaling into SI; no airflow defaults invented',
            'extraction_date':DATE,'interpretation_note':'Actual host geometry, source exterior ACH50 and weather are separate operands; garage airflow does not reuse dwelling natural ACH. Duct imbalance remains systems scope.'}}
    validate(packet);return packet


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--recover',action='store_true');p.add_argument('--check',action='store_true');args=p.parse_args()
    if args.recover:dump_json(OUTPUT,recover())
    packet=load_json(OUTPUT)
    for path,h in packet['input_sha256'].items():
        if sha(ROOT/path)!=h:raise ValueError('Changed host-airflow recovery input: '+path)
    validate(packet);print('Verified host airflow for',len(packet['records']),'source fixtures')


if __name__=='__main__':main()
