"""Standalone layout-2 local release verifier and isolated scientific reproducer.

This exact stdlib source is shipped as reproduce.py. Transport integrity is
administrative; only the extracted unchanged generator and validators qualify
and compare scientific bundles. No checkout import or nested process is used.
"""
import argparse
import hashlib
import importlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import sysconfig
import tempfile
import time
import zipfile
import zlib

FILES={'generator.zip','reproduce.py','references/all-cases-bundle.json.gz'}
REQUEST='references/all-cases-request.json'
REFERENCE='references/all-cases-bundle.json.gz'
PRODUCERS={'scripts/schedule_generator_release.py','scripts/schedule_generator_apartment_certification.py',
           'scripts/schedule_generator_release_reproduction.py'}
CAP=104857600


def _require(condition,message):
    if not condition:raise ValueError(message)


def _canonical(value):
    return (json.dumps(value,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':'))+'\n').encode()


def _json(blob):
    def pairs(items):
        result={}
        for key,value in items:
            _require(key not in result,'Duplicate JSON key');result[key]=value
        return result
    def number(token):
        value=float(token);_require(math.isfinite(value),'Nonfinite JSON number');return value
    return json.loads(blob,object_pairs_hook=pairs,parse_float=number,
                      parse_constant=lambda x:(_ for _ in ()).throw(ValueError('Nonfinite JSON constant')))


def _digest(blob):return {'sha256':hashlib.sha256(blob).hexdigest(),'size_bytes':len(blob)}


def _path(name):
    _require(isinstance(name,str) and name and '\\' not in name and ':' not in name,'Unsafe path')
    p=PurePosixPath(name);reserved={'CON','PRN','AUX','NUL'}|{f'{a}{i}' for a in ('COM','LPT') for i in range(1,10)}
    _require(not p.is_absolute() and all(x not in {'','.','..'} and not x.endswith(('.',' '))
             and x.split('.')[0].upper() not in reserved for x in name.split('/')),'Unsafe path')
    return p


def _unique_paths(names):
    prefixes={}
    _require(len(names)==len(set(names)),'Duplicate path')
    for name in names:
        parts=_path(name).parts
        for i in range(1,len(parts)+1):
            prefix='/'.join(parts[:i]);key=prefix.casefold()
            _require(key not in prefixes or prefixes[key]==prefix,'Case-colliding path');prefixes[key]=prefix


def _identity(entry,*,positive=True):
    _require(isinstance(entry,dict) and set(entry)=={'sha256','size_bytes'},'Invalid identity fields')
    _require(isinstance(entry['sha256'],str) and re.fullmatch('[0-9a-f]{64}',entry['sha256']) is not None,'Invalid SHA256')
    _require(type(entry['size_bytes']) is int and entry['size_bytes']>=(1 if positive else 0),'Invalid byte size')


def _regular(path):
    info=path.lstat()
    _require(not path.is_symlink() and not getattr(info,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',1024),'Symlink/reparse input rejected')
    _require(stat.S_ISREG(info.st_mode),'Input is not a regular file')


def _inventory(root):
    _require(root.is_dir() and not root.is_symlink(),'Release root must be a regular directory')
    _require(not getattr(root.lstat(),'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',1024),'Reparse release root rejected')
    root=root.resolve();found=[];directories=[]
    for directory,dirs,files in os.walk(root,followlinks=False):
        for name in dirs+files:
            path=Path(directory)/name;info=path.lstat()
            _require(not path.is_symlink() and not getattr(info,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',1024),'Symlink/reparse input rejected')
            _require(path.resolve().is_relative_to(root),'Input escapes release root')
            if name in files:_regular(path);found.append(path.relative_to(root).as_posix())
            else:
                _require(stat.S_ISDIR(info.st_mode),'Foreign directory type');directories.append(path.relative_to(root).as_posix())
    _unique_paths(found)
    _require(set(found)==FILES|{'manifest.json'},'Release file inventory differs')
    _require(set(directories)=={'references'},'Release directory inventory differs')


def _manifest(manifest):
    required={'schema_version','release_version','scope','resource_set_id','source_manifest_sha256',
              'commercial_audit_sha256','files','members','public_counts','reference_layout','bundle_schema_version',
              'entrypoints','request','reference','implementation_sources'}
    _require(isinstance(manifest,dict) and set(manifest)==required,'Invalid layout-2 manifest fields')
    _require(manifest['schema_version']=='2.0.0' and manifest['reference_layout']=='external_local_gzip_json_v1'
             and manifest['bundle_schema_version']=='1.2.0','Unsupported release layout/version')
    _require(isinstance(manifest['release_version'],str) and manifest['release_version'],'Invalid release version')
    _require(isinstance(manifest['resource_set_id'],str) and re.fullmatch('resources-[0-9a-f]{64}',manifest['resource_set_id']) is not None,'Invalid resource identity')
    for field in ('source_manifest_sha256','commercial_audit_sha256'):_identity({'sha256':manifest[field],'size_bytes':1})
    _require(manifest['entrypoints']=={'generation':{'kind':'zip_request_output','path':'generator.zip'},
             'reproduction':{'kind':'release_script','path':'reproduce.py'}},'Unsupported entrypoints')
    _require(isinstance(manifest['files'],dict) and set(manifest['files'])==FILES,'Invalid file inventory')
    for entry in manifest['files'].values():_identity(entry);_require(entry['size_bytes']<=CAP,'Transported file exceeds104857600')
    _require(isinstance(manifest['members'],dict) and manifest['members'],'Invalid member inventory')
    _unique_paths(list(manifest['members']))
    for entry in manifest['members'].values():_identity(entry,positive=False);_require(entry['size_bytes']<=CAP,'Tracked member exceeds104857600')
    request=manifest['request'];reference=manifest['reference']
    _require(isinstance(request,dict) and set(request)=={'location','path','sha256','size_bytes'}
             and request['location']=='generator_zip_member' and request['path']==REQUEST,'Invalid request descriptor')
    _identity({k:request[k] for k in ('sha256','size_bytes')})
    _require(isinstance(reference,dict) and set(reference)=={'location','path','codec','sha256','size_bytes','decoded_sha256','decoded_size_bytes'}
             and reference['location']=='release_file' and reference['path']==REFERENCE and reference['codec']=='gzip-json-v1','Invalid reference descriptor')
    _identity({k:reference[k] for k in ('sha256','size_bytes')})
    _identity({'sha256':reference['decoded_sha256'],'size_bytes':reference['decoded_size_bytes']})
    _require(manifest['files'][REFERENCE]=={k:reference[k] for k in ('sha256','size_bytes')},'Reference file identity differs')
    _require(manifest['members'].get(REQUEST)=={k:request[k] for k in ('sha256','size_bytes')},'Request member identity differs')
    _require(REFERENCE not in manifest['members'],'Ambiguous inline/external reference')
    scope=manifest['scope']
    _require(isinstance(scope,dict) and {'milestone_id','scope_version','case_ids','case_count','sha256'}<=set(scope),'Invalid scope')
    for field in ('milestone_id','scope_version'):_require(isinstance(scope[field],str) and scope[field],'Invalid scope label')
    _identity({'sha256':scope['sha256'],'size_bytes':1})
    for prefix in ('case','service_case'):
        if prefix=='service_case':_require((prefix+'_ids' in scope)==(prefix+'_count' in scope),'Incomplete service scope inventory')
        if prefix=='case' or prefix+'_ids' in scope:
            ids=scope[prefix+'_ids'];count=scope[prefix+'_count']
            _require(isinstance(ids,list) and all(isinstance(x,str) and x for x in ids) and len(ids)==len(set(ids))
                     and type(count) is int and count==len(ids),'Invalid scope case inventory')
    for name in ('source_service_definition_count','declared_owned_slot_count','required_programme_service_link_count'):
        if name in scope:_require(type(scope[name]) is int and scope[name]>=0,'Invalid scope count')
    counts=manifest['public_counts'];_require(isinstance(counts,dict) and set(counts)=={'requested_owners','constituents','schedules','bindings'},'Invalid public counts')
    _require(all(type(v) is int and v>=0 for v in counts.values()),'Invalid public count')
    implementations=manifest['implementation_sources']
    _require(isinstance(implementations,dict) and set(implementations)==PRODUCERS,'Missing explicit runner/producer provenance')
    for name,entry in implementations.items():
        _require(isinstance(entry,dict) and set(entry)=={'location','path','sha256','size_bytes'} and entry['location']=='generator_zip_member'
                 and entry['path']=='provenance/implementation/'+name,'Invalid implementation provenance path')
        identity={k:entry[k] for k in ('sha256','size_bytes')};_identity(identity)
        _require(manifest['members'].get(entry['path'])==identity,'Implementation member identity differs')
    runner=implementations['scripts/schedule_generator_release_reproduction.py']
    _require(manifest['files']['reproduce.py']=={k:runner[k] for k in ('sha256','size_bytes')},'Shipped runner differs from producer provenance')


def _stream_gzip(path,reference,output):
    decoder=zlib.decompressobj(16+zlib.MAX_WBITS);count=0;digest=hashlib.sha256();limit=reference['decoded_size_bytes']
    with path.open('rb') as stream:
        while chunk:=stream.read(65536):
            _require(not decoder.eof,'Trailing/concatenated gzip data')
            while chunk:
                try:decoded=decoder.decompress(chunk,min(1048576,limit-count+1))
                except zlib.error as error:raise ValueError('Invalid gzip stream: '+str(error)) from error
                chunk=decoder.unconsumed_tail
                count+=len(decoded);_require(count<=limit,'Decoded reference exceeds declared size')
                digest.update(decoded)
                if output is not None:output.write(decoded)
                _require(not decoder.unused_data,'Trailing/concatenated gzip data')
    _require(decoder.eof,'Truncated gzip stream')
    _require(count==limit and digest.hexdigest()==reference['decoded_sha256'],'Decoded reference identity differs')


def verify_v2_release(release_root: Path, *, decoded_reference: Path | None=None) -> dict:
    """Verify actual local inputs; return transport data, never proof authority."""
    incoming=Path(release_root)
    _require(not incoming.is_symlink() and not getattr(incoming.lstat(),'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',1024),'Symlink/reparse release root rejected')
    root=incoming.resolve()
    _inventory(root);manifest_bytes=(root/'manifest.json').read_bytes();manifest=_json(manifest_bytes);_manifest(manifest)
    identities={'manifest.json':_digest(manifest_bytes)}
    for name,expected in manifest['files'].items():
        _require((root/name).stat().st_size==expected['size_bytes'],'Release file size differs: '+name)
        digest=hashlib.sha256();count=0
        with (root/name).open('rb') as stream:
            while chunk:=stream.read(1048576):count+=len(chunk);digest.update(chunk)
        identities[name]={'sha256':digest.hexdigest(),'size_bytes':count}
        _require(identities[name]==expected,'Release file hash/size differs: '+name)
    with zipfile.ZipFile(root/'generator.zip') as archive:
        names=archive.namelist();_unique_paths(names);_require(set(names)==set(manifest['members']),'ZIP member inventory differs')
        for info in archive.infolist():
            _require(not info.is_dir() and not info.flag_bits&1 and stat.S_IFMT(info.external_attr>>16) in (0,stat.S_IFREG),'Unsafe ZIP member type')
            _require(info.file_size==manifest['members'][info.filename]['size_bytes'],'ZIP member declared size differs')
            digest=hashlib.sha256();count=0
            with archive.open(info) as stream:
                while chunk:=stream.read(1048576):
                    count+=len(chunk);_require(count<=info.file_size,'ZIP member size overflow');digest.update(chunk)
            _require({'sha256':digest.hexdigest(),'size_bytes':count}==manifest['members'][info.filename],'ZIP member identity differs: '+info.filename)
        read=lambda name:_json(archive.read(name))
        scope=read('sources/schedule-generator-m1-scope.json');resources=read('atlas_schedules/data/manifest.json')
        _require(_digest(archive.read('sources/schedule-generator-m1-scope.json'))['sha256']==manifest['scope']['sha256'],'Source scope hash differs')
        _require([c['case_id'] for c in scope['cases']]==manifest['scope']['case_ids'] and len(scope['cases'])==manifest['scope']['case_count'],'Scope case inventory differs')
        for field in ('milestone_id','scope_version'):_require(scope[field]==manifest['scope'][field],'Scope label differs')
        _require(resources.get('schema_version')=='1.0.0','Resource manifest schema differs')
        rid='resources-'+hashlib.sha256(_canonical({k:v for k,v in resources.items() if k!='resource_set_id'})).hexdigest()
        _require(resources['resource_set_id']==rid==manifest['resource_set_id'],'Resource identity differs')
        _require(_digest(archive.read('atlas_schedules/data/manifest.json'))['sha256']==manifest['source_manifest_sha256'],'Resource manifest hash differs')
        _require(_digest(archive.read('data/schedule-generator/comstock-sampling-audit.json'))['sha256']==manifest['commercial_audit_sha256'],'Commercial audit hash differs')
        _require(read('atlas_schedules/data/reference/m1-scope.json')==scope,'Runtime/source scope differs')
        if 'service_cases' in scope:
            _require(manifest['scope'].get('service_case_ids')==[c['case_id'] for c in scope['service_cases']]
                     and manifest['scope'].get('service_case_count')==len(scope['service_cases'])
                     and resources.get('service_cases')==scope['service_cases'],'Physical service/configuration inventory differs')
        resource_paths=[];resource_keys=[]
        for entry in resources['resources']:
            name='atlas_schedules/data/'+str(_path(entry['path']));resource_paths.append(name);resource_keys.append((entry['kind'],entry['key']))
            _identity({k:entry[k] for k in ('sha256','size_bytes')},positive=False)
            _require(manifest['members'].get(name)=={k:entry[k] for k in ('sha256','size_bytes')},'Resource member checksum differs')
        _unique_paths(resource_paths);_require(len(resource_keys)==len(set(resource_keys)),'Duplicate resource identity')
        _require(set(n for n in names if n.startswith('atlas_schedules/data/'))==set(resource_paths)|{'atlas_schedules/data/manifest.json'},'Resource inventory differs')
        policy=[e for e in resources['resources'] if (e['kind'],e['key'])==('reference','comparison-policy')]
        _require(len(policy)==1,'Exact packaged comparison policy required');policy_name='atlas_schedules/data/'+policy[0]['path']
        request=archive.read(REQUEST);wrapper=_json(request)
        _require(isinstance(wrapper,dict) and set(wrapper)=={'schema_version','params','seed'} and wrapper['schema_version']=='1.2.0'
                 and isinstance(wrapper['params'],dict) and wrapper['params'].get('schema_version')=='1.2.0'
                 and wrapper['params'].get('resource_set_id')==rid and type(wrapper['seed']) is int and 0<=wrapper['seed']<2**64,'Invalid packaged request wrapper/version/identity')
        _require(len(wrapper['params']['instances'])==manifest['public_counts']['requested_owners'],'Requested owner count differs')
        for name in ('__main__.py','atlas_schedules/__main__.py','atlas_schedules/contract.py','atlas_schedules/comparison.py','atlas_schedules/resources.py'):
            _require(name in manifest['members'],'Missing packaged entry/validator: '+name)
    if decoded_reference is not None:_require(not Path(decoded_reference).is_symlink(),'Symlink decoded output rejected')
    output_path=Path(decoded_reference).resolve() if decoded_reference is not None else None
    if output_path is not None:
        _require(not output_path.is_relative_to(root) and not output_path.exists(),'Decoded output must be new and outside release')
        with output_path.open('xb') as output:_stream_gzip(root/REFERENCE,manifest['reference'],output)
    else:_stream_gzip(root/REFERENCE,manifest['reference'],None)
    return {'manifest':manifest,'request_bytes':request,'release_root':root,'input_paths':{n:root/n for n in FILES|{'manifest.json'}},
            'input_identities':identities,'policy_member':policy_name,'decoded_reference':output_path}


def _install_isolation(root,work,extraction,state,receipt):
    stdlib=Path(sysconfig.get_path('stdlib')).resolve();base=Path(sys.base_prefix).resolve()
    def audit(event,args):
        if event.startswith(('socket.','subprocess.')) or event in {'os.system','os.posix_spawn','os.spawn'}:raise RuntimeError('Network/subprocess denied: '+event)
        if event!='open' or isinstance(args[0],int):return
        path=Path(os.fsdecode(args[0])).resolve();mode=args[1] or '';flags=args[2]
        writing=any(c in mode for c in 'wax+') or flags& (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC)
        if writing:
            _require(path.is_relative_to(work) or (state['phase']=='receipt' and path==receipt),'Write outside owned work denied');return
        _require(not any(p in {'site-packages','dist-packages'} for p in path.parts),'Ambient package denied')
        phase=state['phase']
        if phase=='validation':
            allowed=(path.is_relative_to(extraction/'atlas_schedules') and
                     not path.is_relative_to(extraction/'atlas_schedules/data') and path.suffix in {'.py','.pyc'}) or (
                     path.is_relative_to(extraction/'atlas_schedules/schemas'))
        elif phase=='generation':
            allowed=path.is_relative_to(extraction/'atlas_schedules') or path==work/'request.json'
        else:allowed=path.is_relative_to(work) or path.is_relative_to(root)
        allowed=allowed or path.is_relative_to(stdlib) or (path.is_relative_to(base) and path.suffix in {'.zip','.pyd','.dll'})
        _require(allowed,'Read outside verified execution inputs denied')
    sys.addaudithook(audit)


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False);parser.add_argument('--release-root',required=True,type=Path);parser.add_argument('--receipt',required=True,type=Path)
    args=parser.parse_args(argv);root=args.release_root.resolve();receipt=args.receipt.resolve()
    _require(not args.receipt.is_symlink(),'Symlink receipt rejected')
    _require(not receipt.is_relative_to(root) and not receipt.exists(),'Receipt must be new and outside release')
    _require(not any(n=='atlas_schedules' or n.startswith('atlas_schedules.') for n in sys.modules),'Preloaded atlas_schedules modules rejected')
    started=time.perf_counter()
    with tempfile.TemporaryDirectory(prefix='atlas-v2-repro-') as directory:
        work=Path(directory).resolve();extraction=work/'package';extraction.mkdir()
        verified=verify_v2_release(args.release_root,decoded_reference=work/'expected.json')
        _require(_digest(Path(__file__).read_bytes())==verified['manifest']['files']['reproduce.py'],'Executing runner differs from verified runner')
        with zipfile.ZipFile(root/'generator.zip') as archive:archive.extractall(extraction)
        state={'phase':'import'};_install_isolation(root,work,extraction,state,receipt)
        sys.path.insert(0,str(extraction))
        modules={name:importlib.import_module('atlas_schedules.'+name) for name in ('__main__','contract','comparison','resources','canonical')}
        module_identities={}
        for name,module in list(sys.modules.items()):
            if name=='atlas_schedules' or name.startswith('atlas_schedules.'):
                path=Path(module.__file__).resolve();_require(path.is_relative_to(extraction),'Foreign packaged module origin')
                module_identities[name]={'path':path.relative_to(extraction).as_posix(),**_digest(path.read_bytes())}
        (work/'request.json').write_bytes(verified['request_bytes']);state['phase']='generation'
        _require(modules['__main__'].main(['--request',str(work/'request.json'),'--output',str(work/'actual.json')])==0,'Packaged CLI generation failed')
        state['phase']='parse'
        actual=modules['resources'].strict_json((work/'actual.json').read_bytes(),'actual.json')
        expected=modules['resources'].strict_json((work/'expected.json').read_bytes(),'expected.json')
        _require(actual.get('schema_version')==expected.get('schema_version')=='1.2.0','Bundle schema differs from release')
        state['phase']='validation';modules['contract'].validate_bundle(actual);modules['contract'].validate_bundle(expected)
        state['phase']='policy';policy=modules['resources'].strict_json((extraction/verified['policy_member']).read_bytes(),'packaged comparison policy')
        _require(modules['canonical'].canonical(policy)==modules['canonical'].canonical(actual['metadata']['comparison_policy'])
                 ==modules['canonical'].canonical(expected['metadata']['comparison_policy']),'Bundle policy differs from exact packaged policy')
        state['phase']='comparison';differences=modules['comparison'].compare_bundles(actual,expected,policy)
        _require(not differences,'Scientific comparison failed: '+str(differences[:30]))
        counts={'constituents':len(actual['constituents']),'schedules':len(actual['schedules']),'bindings':len(actual['bindings'])}
        _require(all(counts[k]==verified['manifest']['public_counts'][k] for k in counts),'Actual output counts differ')
        # Include modules imported lazily by generation as well as entry modules.
        for name,module in list(sys.modules.items()):
            if name=='atlas_schedules' or name.startswith('atlas_schedules.'):
                path=Path(module.__file__).resolve();_require(path.is_relative_to(extraction),'Foreign lazy module origin')
                module_identities[name]={'path':path.relative_to(extraction).as_posix(),**_digest(path.read_bytes())}
        platform_facts={'sys_platform':sys.platform,'machine':sysconfig.get_platform()}
        if hasattr(sys,'getwindowsversion'):
            version=sys.getwindowsversion();platform_facts['os_version']={'major':version.major,'minor':version.minor,'build':version.build}
        elif hasattr(os,'uname'):
            version=os.uname();platform_facts['os_version']={'sysname':version.sysname,'release':version.release,'version':version.version,'machine':version.machine}
        result={'schema_version':'1.0.0','passed':True,'runtime':sys.version,'platform':platform_facts,
                'elapsed_seconds':time.perf_counter()-started,'input_identities':verified['input_identities'],
                'request_identity':{k:verified['manifest']['request'][k] for k in ('sha256','size_bytes')},
                'reference':verified['manifest']['reference'],'packaged_modules':module_identities,
                'requested_owners':verified['manifest']['public_counts']['requested_owners'],'actual_counts':counts,
                'policy_identity':verified['manifest']['members'][verified['policy_member']],
                'strict_actual_validated':True,'strict_expected_validated':True,'comparison_difference_count':0}
        # Receipt is deliberately outside immutable inputs and outside any proof.
        content=_canonical(result);state['phase']='receipt'
        with receipt.open('xb') as output:output.write(content)
        print('Source/discrete and numerical reproduction passed: '+str(counts))
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as error:
        print(type(error).__name__+': '+str(error),file=sys.stderr);raise SystemExit(1)
