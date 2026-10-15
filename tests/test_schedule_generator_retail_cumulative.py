"""Exact cumulative Retail append and predecessor operand/order invariance."""
import copy,json,tempfile,unittest,zipfile
from pathlib import Path
from atlas_schedules.resources import ResourceSet
ROOT=Path(__file__).resolve().parents[1]

class RetailCumulativeTests(unittest.TestCase):
 def test_append_preserves_all_prior_programme_service_operands_and_complete_request_prefix(self):
  from scripts.schedule_generator_retail import compile_cumulative_records,qualification_request
  from scripts.schedule_generator_restaurants import qualification_request as prior_request
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory)
   with zipfile.ZipFile(ROOT/'data/generator-releases/v0.6.0/generator.zip') as archive:
    for name in archive.namelist():
     if name.startswith('atlas_schedules/data/'):
      target=root/name.removeprefix('atlas_schedules/data/');target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(archive.read(name))
   manifest=json.loads((root/'manifest.json').read_text());previous=ResourceSet(root,manifest['resource_set_id'])
   before={(e['kind'],e['key']):previous.get(e['kind'],e['key']) for e in manifest['resources']}
   records=compile_cumulative_records(previous);scope=records['reference','m1-scope'];old=before['reference','m1-scope']
   self.assertEqual(scope['cases'][:165],old['cases']);self.assertEqual(len(scope['cases']),229)
   self.assertEqual(scope['service_cases'][:26],old['service_cases']);self.assertEqual(len(scope['service_cases']),32)
   compiled={c['id'] for c in records['reference','catalogue-index']['compositions'] if c['status']=='compiled'}
   self.assertEqual(len(compiled),30)
   self.assertTrue(all(records['program',c['program_id']]['recipe']['source_composition']['composition_id'] in compiled for c in scope['cases'][165:] if records['program',c['program_id']]['definition']['derivation']=='composed'))
   for case in old['cases']:self.assertEqual(records['program',case['program_id']],before['program',case['program_id']])
   for key,record in before.items():
    if key[0]=='reference' and (key[1].startswith('physical-service__') or key[1]=='restaurant-water-fixed-native-operands'):
     self.assertEqual(records[key],record)
   self.assertNotIn(('reference','family-certification'),records)
   request=qualification_request(records);old_request=prior_request(before)
   self.assertEqual(request['instances'][:191],old_request['instances'])
   self.assertEqual(len(request['instances']),261)
   self.assertEqual([i['key'] for i in request['instances']],scope['qualification_request_order'])
   self.assertEqual(len({i['key'] for i in request['instances']}),261)
   self.assertEqual([i['program_id'] for i in request['instances'][191:255]],
    [c['program_id'] for c in scope['cases'][165:]])
   self.assertTrue(all(i['owner_kind']=='physical_service' for i in request['instances'][255:]))
   changed={k for k,v in before.items() if records.get(k)!=v}
   self.assertEqual(changed,{('reference',k) for k in ('m1-scope','recipe-coverage','catalogue-index','family-certification','family-native-join')})

 def test_actual_cumulative_mix_adds_generated_retail_parent_and_whole_unallocated_main(self):
  import math
  from unittest.mock import patch
  from atlas_schedules import generate
  from atlas_schedules.contract import validate_bundle
  from atlas_schedules.resources import write_resources
  from scripts.schedule_generator_retail import compile_cumulative_records,mixed_qualification_request
  from scripts.schedule_generator_restaurants import mixed_qualification_request as previous_mix
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory)/'previous'
   with zipfile.ZipFile(ROOT/'data/generator-releases/v0.6.0/generator.zip') as archive:
    for name in archive.namelist():
     if name.startswith('atlas_schedules/data/'):
      target=root/name.removeprefix('atlas_schedules/data/');target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(archive.read(name))
   m=json.loads((root/'manifest.json').read_text());prior=ResourceSet(root,m['resource_set_id']);records=compile_cumulative_records(prior)
   old=previous_mix(records,'temporary-identity')['params'];request=mixed_qualification_request(records,'temporary-identity')
   self.assertEqual(request['params']['instances'][:9],old['instances'])
   self.assertEqual(len(request['params']['instances']),11)
   self.assertEqual([m['weight'] for m in request['params']['mixture']['members'][:6]],
    [m['weight']*.8 for m in old['mixture']['members']])
   target=Path(directory)/'candidate';manifest=write_resources(target,records,{'scope':'Retail-mixed-integration-not-certificate'})
   resources=ResourceSet(target,manifest['resource_set_id']);request['params']['resource_set_id']=resources.resource_set_id
   with patch.object(ResourceSet,'load',return_value=resources):bundle=generate(request['params'],request['seed'])
   validate_bundle(bundle)
   owners=bundle['constituents'];physical=[o for o in owners if o['owner_kind']=='physical_service']
   self.assertEqual(len(physical),4)
   self.assertEqual(sum(o['generation'].get('method')=='conserved_source_composition' for o in owners),2)
   retail=[o for o in owners if o['source'].get('building_type')=='RetailStandalone']
   self.assertEqual(len(retail),6)
   sid='service-18de06e6d287f5e459877967'
   main=next(o for o in physical if o['source_service_id']==sid)
   self.assertEqual(main['shared_services'][0]['extent']['value'],1)
   self.assertEqual(main['evidence'][0]['original_service']['beneficiary_program_ids'],[])
   result=owners[-1]
   self.assertEqual(result['generation']['method'],'conserved_constituent_mixture')
   self.assertTrue(all(o.get('required_service_links')==[] for o in retail if o['owner_kind']=='program'))
   for i in result['binding_indices']:
    b=bundle['bindings'][i]
    if b['kind']!='load':continue
    expected=math.fsum(c['factor']*bundle['bindings'][c['binding_index']]['reference_target']['total'] for c in b['reference_target']['evidence']['components'])
    self.assertAlmostEqual(b['reference_target']['total'],expected,delta=max(1e-8,abs(expected)*1e-12))
   (ROOT/'build/task-10/retail-cumulative-mixed-green-20261015-01.json').write_text(json.dumps({'requested_instances':11,'owners':len(owners),'schedules':len(bundle['schedules']),'bindings':len(bundle['bindings']),'physical_services':4,'source_parents':2,'source_target_conservation':True}))

if __name__=='__main__':unittest.main()
