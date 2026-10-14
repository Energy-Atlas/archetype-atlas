"""Reproduce complete source-backed public API pilots with the current resources."""
import argparse
import copy
import gzip
import json
from pathlib import Path

from atlas_schedules import generate
from atlas_schedules.canonical import canonical
from atlas_schedules.resources import ResourceSet

ROOT=Path(__file__).resolve().parents[1]
OFFICE='program-0e670d8dc556f7f5bdd7f1a9'
OCCUPIED='program-03fe19ed8968e605f4be3b8d'
VACANT='program-e0993499165be6c7b5bf9efa'


def build_examples(destination: Path):
    manifest=json.loads((ROOT/'atlas_schedules/data/manifest.json').read_text())
    resources=ResourceSet.load(manifest['resource_set_id'])
    destination=Path(destination); destination.mkdir(parents=True,exist_ok=True)
    def instance(key,program,extent=None):
        inputs=copy.deepcopy(resources.get('program',program)['recipe']['bound_inputs'])
        return {'key':key,'program_id':program,'inputs':inputs,'basis_bindings':extent or {},
                'operating_group':None if 'residents' in inputs else 'medium-office-building'}
    def extent(basis,value,unit):
        return {'extents':{basis:{'value':value,'unit':unit,
                                  'evidence':{'caller':'Explicit pilot experiment extent; no inferred unit area'}}}}
    def mixture(instances,physical=False):
        result={'program_id':'pilot-mixture','composition_id':None,
                'members':[{'instance_key':i['key'],'weight':1/len(instances)} for i in instances]}
        if physical:
            result.update(result_basis='floor_area',denominator={'value':100,'unit':'m2',
                'evidence':{'caller':'Explicit experimental normalization area; not inferred building geometry'}})
        return result
    apartments=[instance('apartment-occupied',OCCUPIED),instance('apartment-vacant',VACANT)]
    mixed=[instance('office',OFFICE,extent('floor_area',100,'m2')),
           instance('apartment',OCCUPIED,extent('dwelling_unit',1,'dwelling'))]
    examples={'medium-office':([instance('office',OFFICE)],None),
              'two-apartments':(apartments,mixture(apartments)),
              'mixed-families':(mixed,mixture(mixed,True)),
              'all-declared-cases':([instance(c['case_id'],c['program_id'])
                                    for c in resources.get('reference','m1-scope')['cases']],None)}
    for name,(instances,mix) in examples.items():
        params={'resource_set_id':resources.resource_set_id,
                'calendar':{'year':2007,'clock':'local_standard_time','holidays':[]},'instances':instances}
        if mix is not None: params['mixture']=mix
        request={'schema_version':'1.0.0','params':params,'seed':42}
        (destination/(name+'-request.json')).write_text(json.dumps(request,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        bundle=generate(params,request['seed'])
        target=destination/(name+'-bundle.json.gz')
        content=canonical(bundle)
        target.write_bytes(gzip.compress(content,mtime=0))
        print(f'{name}: {len(bundle["schedules"])} channels, {len(bundle["constituents"])} owners, '+
              f'{len(content)} JSON bytes, {target.stat().st_size} compressed bytes')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination',type=Path,default=ROOT/'docs/examples/schedule-generator-v1')
    build_examples(parser.parse_args().destination)


if __name__=='__main__':main()
