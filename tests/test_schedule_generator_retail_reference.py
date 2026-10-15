"""Actual source/native container and fixed-operand pointer closure."""
import copy,unittest
from atlas_schedules.errors import GeneratorError

class RetailReferenceTests(unittest.TestCase):
 def test_native_people_topology_geometry_and_schedules_are_independent_guards(self):
  from scripts.schedule_generator_retail import validate_programme_observation
  people=[{'space_name':'one','nominal_people':2,'native_people_object_handle':'original-shared'},
          {'space_name':'two','nominal_people':3,'native_people_object_handle':'original-shared'}]
  given={'case_id':'captured-excerpt','operating':{'source_uniform':.25},'schedules':{'occupancy':{'source':'literal'}},
   'geometry_receipt':{'sha256':'source-geometry'},'source_context':{'occupancy_aggregation':{'source_model_scope':{
    'original_people_inventory':people,'native_people_object_count':1,'native_sorted_space_order':['one','two']}}}}
  observed={'case_id':given['case_id'],'source_context':copy.deepcopy(given['source_context']),
   'operating':copy.deepcopy(given['operating']),'schedules':copy.deepcopy(given['schedules']),
   'source_reference_geometry':copy.deepcopy(given['geometry_receipt']),'native_people_object_count':1,
   'source_space_order':['one','two'],'actual_people':copy.deepcopy(people)}
  for item in observed['actual_people']:item['native_people_object_handle']='new-native-shared'
  validate_programme_observation(given,observed)
  for mutation in ('density','sharing','count','order','geometry','schedule','operating'):
   changed=copy.deepcopy(observed)
   if mutation=='density':changed['actual_people'][0]['nominal_people']+=1
   elif mutation=='sharing':changed['actual_people'][1]['native_people_object_handle']='separate-object'
   elif mutation=='count':changed['native_people_object_count']=2
   elif mutation=='order':changed['source_space_order'].reverse()
   elif mutation=='geometry':changed['source_reference_geometry']['sha256']='foreign'
   elif mutation=='schedule':changed['schedules']['occupancy']['source']='foreign'
   else:changed['operating']['source_uniform']=.5
   with self.subTest(mutation=mutation),self.assertRaises(GeneratorError):validate_programme_observation(given,changed)

 def test_actual_336_programme_member_observations_keep_raw_bytes_and_topology(self):
  from scripts.schedule_generator_retail import load_programme_reference
  capture=load_programme_reference();lock=capture['lock'];given=capture['inputs'];native=capture['vectors']
  self.assertEqual((len(given),len(native['cases'])),(336,336))
  self.assertEqual({lock[k]['format'] for k in ('inputs','vectors')},{'xz-json'})
  self.assertEqual(lock['vectors']['payload_sha256'],'68e1a129c138c512b5d8153d2ec523f3eda07d4851a1936823e6b3b7178cb3ac')
  self.assertEqual(len({i['source_case']['program_id'] for i in given}),64)
  self.assertEqual(sum('activity' in c['channels'] and c['channels']['activity']==c['original_channels']['activity'] for c in native['cases']),294)
  self.assertEqual(sum(bool(i['source_member_receipt']) for i in given),116)
 def test_fixed_projection_missing_mispointed_altered_operand_and_native_control_fail(self):
  from scripts.schedule_generator_retail import load_context_reference,fixed_native_operands,validate_fixed_native_operands
  captured=load_context_reference();original=fixed_native_operands(captured);validate_fixed_native_operands(original,captured)
  for mutation in ('missing','pointer','value','case','native_body'):
   projection=copy.deepcopy(original);native=copy.deepcopy(captured)
   if mutation=='missing':projection['cases'].pop()
   elif mutation=='pointer':projection['cases'][0]['controls']['target_temperature']['source_native_pointer']='/cases/0/controls/target_temperature'
   elif mutation=='value':projection['cases'][0]['controls']['target_temperature']['hourly_value']+=1
   elif mutation=='case':projection['cases'][0]['case_id']='foreign-capture'
   else:next(c for c in native['vectors']['cases'] if c['source_service_id'])['controls']['target_temperature']['values'][0]+=1
   self.assertTrue(projection!=original or mutation=='native_body')
   with self.subTest(mutation=mutation),self.assertRaises(GeneratorError):validate_fixed_native_operands(projection,native)

if __name__=='__main__':unittest.main()
