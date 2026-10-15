"""Exact apartment shipment scope and unchanged release policy."""
import copy
import unittest
from scripts import schedule_generator_apartment_certification as certification

class ApartmentCertificationTests(unittest.TestCase):
    def test_partial_sidecar_receipt_does_not_qualify_profile(self):
        import tempfile,json
        from pathlib import Path
        from scripts.schedule_generator_release import _v2_reproduction_receipt
        with tempfile.TemporaryDirectory() as directory:
            receipt=Path(directory)/'receipt.json';receipt.write_text(json.dumps({'passed':True}))
            manifest={'public_counts':{'requested_owners':1,'constituents':1,'schedules':4,'bindings':4},'files':{}}
            with self.assertRaises(ValueError):_v2_reproduction_receipt(receipt,manifest,{'sha256':'0'*64,'size_bytes':1})
            receipt.write_text(json.dumps({'passed':True,'strict_actual_validated':True,'strict_expected_validated':True,
                'comparison_difference_count':0,'actual_counts':{'constituents':1,'schedules':4,'bindings':4},
                'requested_owners':1,'input_identities':[]}))
            with self.assertRaises(ValueError):_v2_reproduction_receipt(receipt,manifest,{'sha256':'0'*64,'size_bytes':1})

    def test_grouping_preserves_all_owners_and_real_graph(self):
        from unittest.mock import patch
        from atlas_schedules import generate
        from atlas_schedules.contract import validate_bundle
        root=certification.ROOT/'build/task-10/apartment-a5/resources'
        if not (root/'manifest.json').is_file():
            from scripts.schedule_generator_apartment_authority import build_apartment_resources
            build_apartment_resources(root)
        resources=certification.load_resources(root)
        before=certification.apartment_request(resources,group_contexts=False)
        after=certification.apartment_request(resources)
        old=before['params'];new=after['params']
        self.assertEqual((len(old['instances']),len(new['instances'])),(385,385))
        self.assertEqual([i['key'] for i in old['instances']],[i['key'] for i in new['instances']])
        self.assertEqual((len(old['building_realizations']),len(new['building_realizations'])),(40,8))
        def scientific_instances(params):
            instances=copy.deepcopy(params['instances'])
            for i in instances:
                i.pop('building_realization_id',None)
                if i.get('unit_id') is not None:i['basis_bindings']['extents']['floor_area'].pop('evidence')
            return instances
        self.assertEqual(scientific_instances(old),scientific_instances(new))
        fields=('unit_id','physical_id','source_service_id','source_beneficiary_id','programme_ids',
                'water_authority_programme_id','floor_area_m2','multiplicity')
        units=lambda p:{u['unit_id']:{k:u[k] for k in fields} for r in p['building_realizations']
                         for u in r['unit_inventory']['units']}
        self.assertEqual(units(old),units(new));self.assertEqual(len(units(new)),40)
        self.assertEqual(len({(r['building_type'],r['template']) for r in new['building_realizations']}),8)
        # Every actual unit owner and every native CONTROL is exercised. Source
        # qualification is real; only the loader routes to this isolated set.
        params=copy.deepcopy(new)
        params['instances']=[i for i in params['instances'] if i.get('physical_binding_kind')==
                             'caller_unit_prototype_density_fixed_dhw']
        with patch('atlas_schedules.generator.ResourceSet.load',return_value=resources):
            bundle=generate(params,42)
        validate_bundle(bundle)
        self.assertEqual((len(bundle['constituents']),len(bundle['bindings']),len(bundle['schedules'])),(40,160,160))
        self.assertEqual(bundle['generation']['physical_unit_seed_sequence'],[])
        for owner in bundle['constituents']:
            selected=[bundle['bindings'][i] for i in owner['binding_indices']]
            self.assertEqual(sum(b['kind']=='load' for b in selected),1)
            self.assertEqual(sum(b['kind']=='control' for b in selected),3)
            controls={b['slot']:set(bundle['schedules'][b['schedule_id']]['values']) for b in selected if b['kind']=='control'}
            self.assertEqual(controls,{'water_target_temperature':{60.0},'water_sensible_fraction':{.2},'water_latent_fraction':{.05}})
            service=owner['shared_services'][0]
            area=owner['basis_bindings']['extents']['floor_area']['value']
            self.assertAlmostEqual(service['whole_input_target']['total'],service['source_basis_target']['total']*area)

    def test_exact_apartment_codec_identity(self):
        import hashlib
        from atlas_schedules.canonical import canonical
        from scripts.schedule_generator_native_codec import decode_native_component
        lock=certification._read('sources/schedule-generator-apartment-fixed-reference-lock.json')
        component={'reference_resource_key':'apartment-fixed-native-lock','lock':lock,
                   'reference_resource_sha256':hashlib.sha256(canonical(lock)).hexdigest()}
        for field in ('inputs','vectors'):
            blob=(certification.ROOT/lock[field]['source_path']).read_bytes()
            self.assertEqual(len(decode_native_component(blob,component,field)),lock[field]['payload_size_bytes'])
            for mutation in ('key','lock','path','format','compressed','raw'):
                bad=copy.deepcopy(component);content=blob
                if mutation=='key':bad['reference_resource_key']+='-foreign'
                elif mutation=='lock':bad['lock']['schema_version']='foreign'
                elif mutation=='path':bad['lock'][field]['source_path']='data/foreign.json.gz'
                elif mutation=='format':bad['lock'][field]['format']='gzip-json'
                elif mutation=='compressed':content=blob[:-1]+bytes([blob[-1]^1])
                else:bad['lock'][field]['payload_sha256']='0'*64
                bad['reference_resource_sha256']=hashlib.sha256(canonical(bad['lock'])).hexdigest()
                with self.subTest(field=field,mutation=mutation),self.assertRaises(Exception):
                    decode_native_component(content,bad,field)
    def test_apartment_standalone_and_scope_exhaustion(self):
        scope=certification.apartment_scope()
        self.assertEqual(len(scope['cases']),313)
        finite=scope['apartment_finite_configurations']
        self.assertEqual(len(finite),1564)
        self.assertEqual(sum(x['branch']=='positive_N' for x in finite),1480)
        self.assertEqual(sum(x['branch']=='skip_N0' for x in finite),40)
        self.assertEqual(sum(x['branch']=='fixed' for x in finite),44)
        self.assertEqual(len(scope['apartment_location_tuples']),37)
        self.assertEqual(scope['variable_domains']['N'],{'type':'integer','minimum':0,'maximum':None})
        certification.validate_scope(scope)
        for field in ('cases','apartment_finite_configurations','apartment_location_tuples'):
            bad=copy.deepcopy(scope);bad[field].pop()
            with self.subTest(field=field),self.assertRaises(ValueError):certification.validate_scope(bad)
        bad=copy.deepcopy(scope);bad['apartment_finite_configurations'].reverse()
        with self.assertRaises(ValueError):certification.validate_scope(bad)

    def test_apartment_release_limits_are_preserved(self):
        from scripts.schedule_generator_release import COMPLETE_REPRODUCTION_TIMEOUT_SECONDS
        from scripts.schedule_generator_native_codec import decode_native_component
        self.assertEqual(COMPLETE_REPRODUCTION_TIMEOUT_SECONDS,600)
        self.assertEqual(certification.NORMAL_TIMEOUT_SECONDS,240)
        self.assertEqual(certification.MAX_TRACKED_BLOB_BYTES,104857600)
        with self.assertRaises(Exception):decode_native_component(b'foreign',{'reference_resource_key':'apartment-anything'})
        with self.assertRaises(ValueError):certification.validate_transport_inventory([{'path':'oversized','size_bytes':104857601}])
