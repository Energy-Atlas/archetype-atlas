"""Explicit new native XZ container, exact historical gzip identity scope."""
import copy,gzip,hashlib,json,lzma,unittest
from pathlib import Path
from atlas_schedules.canonical import canonical
from atlas_schedules.errors import GeneratorError
ROOT=Path(__file__).resolve().parents[1]

class NativeCodecTests(unittest.TestCase):
 def component(self,codec='xz-json'):
  raw=canonical({'cases':[{'case_id':'source-observation'}]});blob=lzma.compress(raw) if codec=='xz-json' else gzip.compress(raw,mtime=0)
  entry={'source_path':'data/schedule-generator/reference/retail-programme-native.json.'+('xz' if codec=='xz-json' else 'gz'),
   'format':codec,'sha256':hashlib.sha256(blob).hexdigest(),'size_bytes':len(blob),'payload_sha256':hashlib.sha256(raw).hexdigest(),'payload_size_bytes':len(raw)}
  lock={'vectors':entry};component={'reference_resource_key':'retail-programme-native-lock','lock':lock,'reference_resource_sha256':hashlib.sha256(canonical(lock)).hexdigest()}
  return raw,blob,component
 def test_new_xz_declared_compressed_and_raw_hashes_decode_exact_source_bytes(self):
  from scripts.schedule_generator_native_codec import decode_native_component
  raw,blob,component=self.component();self.assertEqual(decode_native_component(blob,component),raw)
 def test_new_missing_unknown_extension_body_raw_or_component_identity_fail(self):
  from scripts.schedule_generator_native_codec import decode_native_component
  for mutation in ('missing_format','unknown_format','gzip_new','extension','missing_path','body','raw_sha','raw_size','missing_raw_size','component_hash'):
   raw,blob,component=self.component();entry=component['lock']['vectors']
   if mutation=='missing_format':entry.pop('format')
   elif mutation=='unknown_format':entry['format']='zstd-json'
   elif mutation=='gzip_new':raw,blob,component=self.component('gzip-json');entry=component['lock']['vectors']
   elif mutation=='extension':entry['source_path']=entry['source_path'].replace('.xz','.gz')
   elif mutation=='missing_path':entry.pop('source_path')
   elif mutation=='body':blob=blob[:-1]+bytes([blob[-1]^1]);entry.update(sha256=hashlib.sha256(blob).hexdigest())
   elif mutation=='raw_sha':entry['payload_sha256']='0'*64
   elif mutation=='raw_size':entry['payload_size_bytes']+=1
   elif mutation=='missing_raw_size':entry.pop('payload_size_bytes')
   component['reference_resource_sha256']=hashlib.sha256(canonical(component['lock'])).hexdigest() if mutation!='component_hash' else '0'*64
   with self.subTest(mutation=mutation),self.assertRaises(GeneratorError):decode_native_component(blob,component)
 def test_exact_legacy_water_label_lock_path_and_absent_legacy_gzip_remain_valid(self):
  from scripts.schedule_generator_native_codec import decode_native_component
  old=json.loads((ROOT/'sources/schedule-generator-restaurant-water-reference-lock.json').read_text())
  component={'reference_resource_key':'restaurant-water-native-lock','reference_resource_sha256':hashlib.sha256(canonical(old)).hexdigest(),'lock':old}
  entry=old['vectors'];blob=(ROOT/entry['source_path']).read_bytes()
  self.assertEqual(decode_native_component(blob,component),gzip.decompress(blob))
  for mutation in ('path','identity','foreign_component','unknown_label'):
   changed=copy.deepcopy(component)
   if mutation=='path':changed['lock']['vectors']['source_path']='foreign.json.gz'
   elif mutation=='identity':changed['lock']['interpretation']='Coherent but foreign lock identity'
   elif mutation=='foreign_component':changed['reference_resource_key']='commercial-native-lock'
   else:changed['lock']['vectors']['format']='gzip JSON unknown'
   changed['reference_resource_sha256']=hashlib.sha256(canonical(changed['lock'])).hexdigest()
   with self.subTest(mutation=mutation),self.assertRaises(GeneratorError):decode_native_component(blob,changed)
  raw=canonical({'cases':[]});blob=gzip.compress(raw,mtime=0)
  lock={'vectors':{'source_path':'legacy.json.gz','sha256':hashlib.sha256(blob).hexdigest(),'size_bytes':len(blob),'payload_sha256':hashlib.sha256(raw).hexdigest(),'payload_size_bytes':len(raw)}}
  component={'reference_resource_key':'commercial-native-lock','reference_resource_sha256':hashlib.sha256(canonical(lock)).hexdigest(),'lock':lock}
  self.assertEqual(decode_native_component(blob,component),raw)

 def test_packaged_new_xz_inputs_and_vectors_close_raw_hashes(self):
  from scripts.schedule_generator_release import validate_packaged_native_components
  raw,blob,component=self.component();lock=component['lock']
  raw_input=canonical([{'case_id':'source-observation'}]);input_blob=lzma.compress(raw_input)
  lock['inputs']={'source_path':'data/schedule-generator/reference/retail-programme-inputs.json.xz',
   'format':'xz-json','sha256':hashlib.sha256(input_blob).hexdigest(),'size_bytes':len(input_blob),
   'payload_sha256':hashlib.sha256(raw_input).hexdigest(),'payload_size_bytes':len(raw_input)}
  component['reference_resource_sha256']=hashlib.sha256(canonical(lock)).hexdigest()
  join={'components':[component],'fixture_bindings':[],'service_bindings':[]}
  records={'family-native-join':join,'retail-programme-native-lock':lock}
  class Resources:
   def get(self,kind,key):return copy.deepcopy(records[key])
  files={lock['vectors']['source_path']:blob,lock['inputs']['source_path']:input_blob}
  validate_packaged_native_components(Resources(),files)
  lock['inputs']['payload_sha256']='0'*64
  component['reference_resource_sha256']=hashlib.sha256(canonical(lock)).hexdigest()
  with self.assertRaisesRegex((ValueError,GeneratorError),'[Rr]aw|payload'):
   validate_packaged_native_components(Resources(),files)

if __name__=='__main__':unittest.main()
