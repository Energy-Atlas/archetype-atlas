"""Real layout-2 extraction and strict release/reference failure boundaries."""
import copy
import gzip
import hashlib
import importlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
import warnings

from atlas_schedules.canonical import canonical

ROOT=Path(__file__).resolve().parents[1]
RUNNER=ROOT/'scripts/schedule_generator_release_reproduction.py'


def digest(blob):return {'sha256':hashlib.sha256(blob).hexdigest(),'size_bytes':len(blob)}


class ReleaseSidecarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory(prefix='a5-v2-small-')
        cls.root=Path(cls.temporary.name);cls.built=False

    @classmethod
    def tearDownClass(cls):cls.temporary.cleanup()

    def fixture(self):
        self.assertTrue(RUNNER.is_file(),'Required standalone v2 reproducer is absent')
        if not self.built:
            from scripts.schedule_generator_release import _archive,_execute_zip,BOOTSTRAP_V2
            from scripts.schedule_generator_apartment_certification import load_resources,apartment_request
            resources_root=ROOT/'build/task-10/apartment-a4/resources'
            if not (resources_root/'manifest.json').is_file():
                from scripts.schedule_generator_apartment_authority import build_apartment_resources
                build_apartment_resources(resources_root)
            resources=load_resources(resources_root)
            request=apartment_request(resources,include_previous=False)
            params=request['params']
            owner=next(i for i in params['instances'] if i['owner_kind']=='physical_service')
            realization=next(r for r in params['building_realizations'] if r['building_realization_id']==owner['building_realization_id'])
            realization['unit_inventory']['units']=[u for u in realization['unit_inventory']['units'] if u['unit_id']==owner['unit_id']]
            realization['unit_inventory_sha256']=digest(canonical(realization['unit_inventory']))['sha256']
            params['instances']=[owner];params['building_realizations']=[realization]
            files={'__main__.py':BOOTSTRAP_V2}
            for p in (ROOT/'atlas_schedules').rglob('*'):
                if p.is_file() and p.suffix in {'.py','.json'} and '__pycache__' not in p.parts and not p.is_relative_to(ROOT/'atlas_schedules/data'):
                    files[p.relative_to(ROOT).as_posix()]=p.read_bytes()
            for p in resources.root.rglob('*.json'):
                files['atlas_schedules/data/'+p.relative_to(resources.root).as_posix()]=p.read_bytes()
            scope=resources.get('reference','m1-scope')
            resource_manifest=json.loads(files['atlas_schedules/data/manifest.json'])
            resource_manifest.update(cases=scope['cases'],service_cases=scope.get('service_cases',[]))
            resource_manifest['resource_set_id']='resources-'+hashlib.sha256(canonical({k:v for k,v in resource_manifest.items() if k!='resource_set_id'})).hexdigest()
            files['atlas_schedules/data/manifest.json']=canonical(resource_manifest)
            request['params']['resource_set_id']=resource_manifest['resource_set_id']
            files['sources/schedule-generator-m1-scope.json']=canonical(scope)
            files['data/schedule-generator/comstock-sampling-audit.json']=(ROOT/'data/schedule-generator/comstock-sampling-audit.json').read_bytes()
            files['references/all-cases-request.json']=canonical(request)
            implementations={}
            for name in ('scripts/schedule_generator_release.py','scripts/schedule_generator_apartment_certification.py','scripts/schedule_generator_release_reproduction.py'):
                path='provenance/implementation/'+name;files[path]=(ROOT/name).read_bytes()
                implementations[name]={'location':'generator_zip_member','path':path,**digest(files[path])}
            archive=_archive(files)
            # Real unpatched CLI generation from the extracted independent ZIP.
            generated=_execute_zip(archive,request);bundle=json.loads(generated)
            release=self.root/'original';release.mkdir();(release/'references').mkdir()
            (release/'generator.zip').write_bytes(archive);(release/'reproduce.py').write_bytes(RUNNER.read_bytes())
            reference=gzip.compress(generated,mtime=0);(release/'references/all-cases-bundle.json.gz').write_bytes(reference)
            manifest={'schema_version':'2.0.0','release_version':'focused-small-unqualified-release',
                'reference_layout':'external_local_gzip_json_v1','bundle_schema_version':'1.2.0',
                'entrypoints':{'generation':{'kind':'zip_request_output','path':'generator.zip'},'reproduction':{'kind':'release_script','path':'reproduce.py'}},
                'scope':{'milestone_id':scope['milestone_id'],'scope_version':scope['scope_version'],
                    'case_count':len(scope['cases']),'case_ids':[c['case_id'] for c in scope['cases']],
                    'service_case_count':len(scope.get('service_cases',[])),'service_case_ids':[c['case_id'] for c in scope.get('service_cases',[])],
                    'sha256':digest(files['sources/schedule-generator-m1-scope.json'])['sha256']},
                'resource_set_id':resource_manifest['resource_set_id'],
                'source_manifest_sha256':digest(files['atlas_schedules/data/manifest.json'])['sha256'],
                'commercial_audit_sha256':digest(files['data/schedule-generator/comstock-sampling-audit.json'])['sha256'],
                'request':{'location':'generator_zip_member','path':'references/all-cases-request.json',**digest(canonical(request))},
                'reference':{'location':'release_file','path':'references/all-cases-bundle.json.gz','codec':'gzip-json-v1',**digest(reference),
                    'decoded_sha256':digest(generated)['sha256'],'decoded_size_bytes':len(generated)},
                'files':{'generator.zip':digest(archive),'reproduce.py':digest(RUNNER.read_bytes()),'references/all-cases-bundle.json.gz':digest(reference)},
                'members':{k:digest(v) for k,v in files.items()},'implementation_sources':implementations,
                'public_counts':{'requested_owners':1,'constituents':len(bundle['constituents']),'schedules':len(bundle['schedules']),'bindings':len(bundle['bindings'])}}
            (release/'manifest.json').write_bytes(canonical(manifest))
            cls=type(self);cls.release=release;cls.manifest=manifest;cls.generated=generated;cls.built=True
        target=Path(tempfile.mkdtemp(prefix='copy-',dir=self.root));shutil.copytree(self.release,target,dirs_exist_ok=True)
        return target

    def run_release(self,target):
        work=Path(tempfile.mkdtemp(prefix='work-',dir=self.root));receipt=work/'receipt.json'
        command=[sys.executable,'-I','-S',str(target/'reproduce.py'),'--release-root',str(target),'--receipt',str(receipt)]
        r=subprocess.run(command,cwd=work,capture_output=True,text=True,timeout=600)
        return r,json.loads(receipt.read_bytes()) if receipt.exists() else None

    def change_reference(self,target,mutate):
        bundle=json.loads(self.generated);mutate(bundle);raw=canonical(bundle);blob=gzip.compress(raw,mtime=0)
        (target/'references/all-cases-bundle.json.gz').write_bytes(blob)
        manifest=json.loads((target/'manifest.json').read_bytes());manifest['files']['references/all-cases-bundle.json.gz']=digest(blob)
        manifest['reference'].update(**digest(blob),decoded_sha256=digest(raw)['sha256'],decoded_size_bytes=len(raw))
        (target/'manifest.json').write_bytes(canonical(manifest))

    def test_real_v2_extraction_and_four_file_copy(self):
        target=self.fixture()
        self.assertEqual({p.relative_to(target).as_posix() for p in target.rglob('*') if p.is_file()},
                         {'manifest.json','generator.zip','reproduce.py','references/all-cases-bundle.json.gz'})
        r,receipt=self.run_release(target);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertTrue(receipt['passed']);self.assertEqual(receipt['comparison_difference_count'],0)
        self.assertEqual(receipt['actual_counts'],{'constituents':1,'schedules':4,'bindings':4})
        self.assertTrue(receipt['strict_actual_validated'] and receipt['strict_expected_validated'])
        for name,module in receipt['packaged_modules'].items():
            self.assertTrue(module['path'].startswith('atlas_schedules/'),name)
            self.assertEqual(module['sha256'],self.manifest['members'][module['path']]['sha256'])
        evidence=ROOT/'build/task-10/apartment-a5'
        evidence.mkdir(parents=True,exist_ok=True)
        retained=Path(tempfile.mkdtemp(prefix='r67-primary-python'+str(sys.version_info.major)+str(sys.version_info.minor)+'-',dir=evidence))
        shutil.copytree(target,retained/'release')
        shutil.copyfile(Path(r.args[-1]),retained/'successful-runner-receipt.json')
        (retained/'retention.json').write_bytes(canonical({'interpretation':'Actual passing small sourcequalified boundary fixture only; not a full A5 candidate or limit result',
            'runtime':sys.version,'files':{p.relative_to(retained/'release').as_posix():digest(p.read_bytes())
                for p in (retained/'release').rglob('*') if p.is_file()}}))

    def test_transport_manifest_and_gzip_negatives(self):
        from scripts.schedule_generator_release_reproduction import verify_v2_release
        target=self.fixture();original=(target/'manifest.json').read_bytes();sidecar=target/'references/all-cases-bundle.json.gz';compressed=sidecar.read_bytes()
        for mutate in [lambda m:m.update(schema_version='9'),lambda m:m.update(reference_layout='guess'),
                lambda m:m['reference'].update(codec='guess'),lambda m:m['request'].update(size_bytes=True),
                lambda m:m['reference'].update(decoded_size_bytes=True),lambda m:m['files']['reproduce.py'].update(sha256='0'*64),
                lambda m:m['request'].update(sha256='0'*64),lambda m:m.update(resource_set_id='resources-foreign'),
                lambda m:m['scope'].update(case_count=1),lambda m:m['files'].update({'../foreign':digest(b'x')})]:
            m=json.loads(original);mutate(m);(target/'manifest.json').write_bytes(canonical(m))
            with self.subTest(mutation=m),self.assertRaises(Exception):verify_v2_release(target)
        (target/'manifest.json').write_bytes(original)
        for blob in (compressed[:-2],compressed+b'trailing',compressed+compressed,compressed[:-8]+b'12345678'):
            m=json.loads(original);m['files']['references/all-cases-bundle.json.gz']=digest(blob);m['reference'].update(**digest(blob))
            sidecar.write_bytes(blob);(target/'manifest.json').write_bytes(canonical(m))
            with self.subTest(gzip_size=len(blob)),self.assertRaises(Exception):verify_v2_release(target)
        sidecar.write_bytes(compressed);(target/'manifest.json').write_bytes(original)
        extra=target/'extra';extra.write_bytes(b'extra')
        with self.assertRaises(Exception):verify_v2_release(target)
        extra.unlink();sidecar.unlink()
        with self.assertRaises(Exception):verify_v2_release(target)

    def test_explicit_inventory_member_paths_and_decode_bounds(self):
        from scripts.schedule_generator_release_reproduction import verify_v2_release
        target=self.fixture();manifest_path=target/'manifest.json';original=manifest_path.read_bytes()
        for field,value in [('decoded_size_bytes',1),('decoded_size_bytes',len(self.generated)+1),('decoded_sha256','0'*64)]:
            manifest=json.loads(original);manifest['reference'][field]=value;manifest_path.write_bytes(canonical(manifest))
            with self.subTest(field=field,value=value),self.assertRaisesRegex(ValueError,'Decoded reference'):
                verify_v2_release(target)
        manifest_path.write_bytes(original)
        for location in (target/'decoded.json',target.parent/'already.json'):
            if not location.is_relative_to(target):location.write_bytes(b'existing')
            with self.assertRaises(ValueError):verify_v2_release(target,decoded_reference=location)
        extra=target/'empty';extra.mkdir()
        with self.assertRaisesRegex(ValueError,'directory inventory'):verify_v2_release(target)
        extra.rmdir()
        for name,reason in [('foreign/../bad','Unsafe'),('ATLAS_SCHEDULES/foreign.py','Case-colliding'),
                            ('atlas_schedules/__main__.py','Duplicate'),('references/all-cases-bundle.json.gz','Ambiguous')]:
            changed=self.fixture();manifest=json.loads((changed/'manifest.json').read_bytes())
            with warnings.catch_warnings():
                warnings.simplefilter('ignore',UserWarning)
                with zipfile.ZipFile(changed/'generator.zip','a') as archive:archive.writestr(name,b'foreign')
            manifest['files']['generator.zip']=digest((changed/'generator.zip').read_bytes())
            if reason!='Duplicate':manifest['members'][name]=digest(b'foreign')
            (changed/'manifest.json').write_bytes(canonical(manifest))
            with self.subTest(name=name),self.assertRaisesRegex(ValueError,reason):verify_v2_release(changed)
        # Duplicate/nonfinite manifest JSON rejects before trusted discovery.
        manifest_path.write_bytes(original.replace(b'"schema_version":"2.0.0"',b'"schema_version":"2.0.0","schema_version":"2.0.0"'))
        with self.assertRaisesRegex(ValueError,'Duplicate'):verify_v2_release(target)
        manifest_path.write_bytes(original.replace(b'"requested_owners":1',b'"requested_owners":NaN'))
        with self.assertRaisesRegex(ValueError,'Nonfinite'):verify_v2_release(target)

    def test_strict_expected_proof_and_scientific_policy_reject_updated_hashes(self):
        from tests.test_schedule_generator_apartment_family import ApartmentFamily
        def unused_pool(bundle):
            realization=bundle['metadata']['building_realizations'][0]
            selected={pid for u in realization['unit_inventory']['units'] for pid in u['programme_ids']}
            pool=realization['method_qualification']['value']['qualifications']
            unused=next(q for q in pool if q['value']['programme_id'] not in selected)
            self.assertNotIn(unused['value']['programme_id'],selected)
            pool.remove(unused);ApartmentFamily.rehash(realization['method_qualification'])
        def proof(bundle):ApartmentFamily.erase_proof(bundle);ApartmentFamily.rehash(bundle)
        mutations=[('control',lambda b:b['constituents'][0]['binding_indices'].pop()),
                   ('policy',lambda b:b['metadata']['comparison_policy']['tolerances']['fraction'].update(abs_tol=1.0)),
                   ('science',lambda b:b['generation'].update(master_seed=51)),('unused_pool',unused_pool),('native_proof',proof)]
        for name,mutate in mutations:
            target=self.fixture();self.change_reference(target,mutate);r,receipt=self.run_release(target)
            self.assertNotEqual(r.returncode,0,r.stdout+r.stderr);self.assertFalse(receipt and receipt.get('passed'))
            if name=='science':self.assertIn('Scientific comparison failed',r.stderr)

    def test_both_actual_consumers_stage_complete_inputs(self):
        from scripts.schedule_generator_apartment_certification import _profile_copied_apartment_release
        target=self.fixture();outside=Path(tempfile.mkdtemp(dir=self.root))
        result=_profile_copied_apartment_release(target,outside)
        self.assertTrue(result['passed'],result)
        self.assertEqual(set(result['outside_input_inventory']),{'manifest.json','generator.zip','reproduce.py','references/all-cases-bundle.json.gz'})
        self.assertEqual(set(p.relative_to(outside/'release').as_posix() for p in (outside/'release').rglob('*') if p.is_file()),set(result['outside_input_inventory']))
        self.assertEqual(result['phases']['normal_generation']['timeout_seconds'],240)
        self.assertEqual(result['phases']['combined_reproduction']['timeout_seconds'],600)
        self.assertTrue(result['phases']['combined_reproduction']['scientific_receipt']['passed'])

    def test_missing_receipt_and_child_timeout_do_not_pass(self):
        from unittest.mock import patch
        from scripts import schedule_generator_apartment_certification as a5
        target=self.fixture();outside=Path(tempfile.mkdtemp(dir=self.root))
        # Boundary fault: an OS child exits0 but never writes its declared
        # receipt. Real copy/discovery/accounting must still fail closed.
        with patch.object(a5,'_run',return_value={'returncode':0,'timed_out':False,'elapsed_seconds':0,'stdout':'','stderr':''}):
            result=a5._profile_copied_apartment_release(target,outside)
        self.assertFalse(result['passed']);self.assertIn('receipt_error',result['phases']['combined_reproduction'])
        outcome=a5._run([sys.executable,'-I','-S','-c','import time;time.sleep(2)'],self.root,.01)
        self.assertTrue(outcome['timed_out']);self.assertIsNone(outcome['returncode'])

    def test_zip_only_reproduction_rejected_but_generation_works(self):
        target=self.fixture();work=Path(tempfile.mkdtemp(dir=self.root));archive=target/'generator.zip'
        r=subprocess.run([sys.executable,'-I','-S',str(archive),'--reproduce'],cwd=work,capture_output=True,text=True,timeout=30)
        self.assertEqual(r.returncode,2);self.assertIn('Release layout 2 reproduction requires manifest.json',r.stdout+r.stderr)
        with zipfile.ZipFile(archive) as z:request=z.read('references/all-cases-request.json')
        (work/'request.json').write_bytes(request)
        r=subprocess.run([sys.executable,'-I','-S',str(archive),'--request',str(work/'request.json'),'--output',str(work/'actual.json')],cwd=work,capture_output=True,text=True,timeout=240)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertTrue((work/'actual.json').is_file())

    def test_actual_release_consumer_and_shared_command(self):
        from scripts.schedule_generator_release import _release_reproduction_command,reproduce_generator,verify_generator
        target=self.fixture();command=_release_reproduction_command(target,self.root/'receipt.json')
        self.assertEqual(command[1:3],['-I','-S']);self.assertEqual(Path(command[3]),target/'reproduce.py')
        self.assertEqual(verify_generator(target),[]);self.assertEqual(reproduce_generator(target),[])

    def test_actual_legacy_embedded_and_mixed_reproduction(self):
        from scripts.schedule_generator_release import _archive,BOOTSTRAP,_release_reproduction_command,verify_generator,reproduce_generator
        target=self.fixture()
        with zipfile.ZipFile(target/'generator.zip') as archive:files={n:archive.read(n) for n in archive.namelist()}
        files['__main__.py']=BOOTSTRAP
        files['references/all-cases-bundle.json.gz']=gzip.compress(self.generated,mtime=0)
        files['references/mixed-family-request.json']=files['references/all-cases-request.json']
        files['references/mixed-family-bundle.json.gz']=files['references/all-cases-bundle.json.gz']
        archive=_archive(files);legacy=Path(tempfile.mkdtemp(prefix='legacy-',dir=self.root))
        (legacy/'generator.zip').write_bytes(archive)
        manifest={k:copy.deepcopy(self.manifest[k]) for k in ('release_version','scope','resource_set_id','source_manifest_sha256','commercial_audit_sha256')}
        manifest.update(schema_version='1.0.0',files={'generator.zip':digest(archive)},members={n:digest(v) for n,v in files.items()})
        (legacy/'manifest.json').write_bytes(canonical(manifest))
        self.assertEqual(_release_reproduction_command(legacy,self.root/'unused.json')[-1],'--reproduce')
        self.assertEqual(verify_generator(legacy),[]);self.assertEqual(reproduce_generator(legacy),[])

    def test_missing_copied_inputs_and_preloaded_modules_reject(self):
        from scripts.schedule_generator_release import reproduce_generator
        for name in ('manifest.json','reproduce.py','references/all-cases-bundle.json.gz'):
            target=self.fixture();(target/name).unlink()
            self.assertTrue(reproduce_generator(target),name)
        target=self.fixture();work=Path(tempfile.mkdtemp(dir=self.root))
        script="import runpy,sys,types;sys.modules['atlas_schedules']=types.ModuleType('atlas_schedules');sys.argv=[sys.argv[1],*sys.argv[2:]];runpy.run_path(sys.argv[0],run_name='__main__')"
        result=subprocess.run([sys.executable,'-I','-S','-c',script,str(target/'reproduce.py'),'--release-root',str(target),'--receipt',str(work/'receipt.json')],cwd=work,capture_output=True,text=True,timeout=30)
        self.assertNotEqual(result.returncode,0);self.assertIn('Preloaded atlas_schedules',result.stderr)

    def test_actual_and_expected_validation_deny_resource_reads(self):
        # Fault injection adds one read after the unchanged real validator.
        # Count1 is genuine CLI generation;2 actual incoming;3 expected incoming.
        # No source qualifier or scientific predicate is replaced.
        from scripts.schedule_generator_release import _archive
        for incoming_call in (2,3):
            target=self.fixture()
            with zipfile.ZipFile(target/'generator.zip') as archive:files={n:archive.read(n) for n in archive.namelist()}
            probe=("\n_sidecar_original_validate_bundle=validate_bundle\n_sidecar_validation_calls=0\n"
                   "def validate_bundle(bundle):\n global _sidecar_validation_calls\n _sidecar_validation_calls+=1\n"
                   " result=_sidecar_original_validate_bundle(bundle)\n"
                   f" if _sidecar_validation_calls=={incoming_call}: (Path(__file__).parent/'data/reference/m1-scope.json').read_bytes()\n"
                   " return result\n").encode()
            files['atlas_schedules/contract.py']+=probe;blob=_archive(files);(target/'generator.zip').write_bytes(blob)
            manifest=json.loads((target/'manifest.json').read_bytes());manifest['files']['generator.zip']=digest(blob)
            manifest['members']['atlas_schedules/contract.py']=digest(files['atlas_schedules/contract.py'])
            (target/'manifest.json').write_bytes(canonical(manifest))
            result,receipt=self.run_release(target)
            self.assertNotEqual(result.returncode,0);self.assertIn('Read outside verified execution inputs denied',result.stderr)
            self.assertFalse(receipt and receipt.get('passed'))

    def test_symlink_release_input_rejects(self):
        import os
        from scripts.schedule_generator_release_reproduction import verify_v2_release
        target=self.fixture();runner=target/'reproduce.py';real=target.parent/'original-runner.py';shutil.copyfile(runner,real);runner.unlink()
        try:os.symlink(real,runner)
        except OSError as error:self.skipTest('Host cannot create symlink: '+str(error))
        with self.assertRaisesRegex(ValueError,'Symlink/reparse'):verify_v2_release(target)

    def test_cold_guard_allows_runtime_code_and_schema_but_denies_source_python(self):
        # A retained producer .py is source evidence, not an imported runtime
        # module. Extension alone must not admit it during incoming validation.
        work=Path(tempfile.mkdtemp(dir=self.root));package=work/'package';release=work/'release';release.mkdir()
        paths=[('atlas_schedules/contract.py','atlas_schedules/contract.py'),
               ('atlas_schedules/schemas/schedule-generator-bundle-v1_2.schema.json','atlas_schedules/schemas/schedule-generator-bundle-v1_2.schema.json'),
               ('provenance/implementation/scripts/schedule_generator_release.py','scripts/schedule_generator_release.py')]
        for target,source in paths:
            path=package/target;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/source,path)
        script=("import importlib.util,pathlib,sys\n"
                "spec=importlib.util.spec_from_file_location('release_runner',sys.argv[1]);runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)\n"
                "work=pathlib.Path(sys.argv[2]);package=work/'package'\n"
                "runner._install_isolation(work/'release',work,package,{'phase':'validation'},work/'receipt.json')\n"
                "(package/'atlas_schedules/contract.py').read_bytes()\n"
                "(package/'atlas_schedules/schemas/schedule-generator-bundle-v1_2.schema.json').read_bytes()\n"
                "try:(package/'provenance/implementation/scripts/schedule_generator_release.py').read_bytes()\n"
                "except ValueError:raise SystemExit(0)\n"
                "raise SystemExit('Retained source Python was incorrectly admitted as runtime code')\n")
        result=subprocess.run([sys.executable,'-I','-S','-c',script,str(RUNNER),str(work)],cwd=work,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)


if __name__=='__main__':unittest.main()
