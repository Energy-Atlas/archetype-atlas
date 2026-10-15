"""Standalone generator behavior from a checkout-independent directory."""
from pathlib import Path
import contextlib
import io
import inspect
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from atlas_schedules import generate
from atlas_schedules.comparison import compare_bundles
from atlas_schedules.resources import strict_json

ROOT = Path(__file__).resolve().parents[1]
REQUEST = ROOT / 'docs/examples/schedule-generator-v1/medium-office-request.json'


def _audit_path_allowed(candidate, stdlib, extension_roots, stdlib_archive, extraction_root):
    path = os.path.normcase(os.path.realpath(candidate))
    if any(part in {'site-packages', 'dist-packages'} for part in Path(path).parts):
        return False

    def within(root):
        root = os.path.normcase(os.path.realpath(root))
        try:
            return os.path.commonpath((path, root)) == root
        except ValueError:
            return False

    return (path == os.path.normcase(os.path.realpath(stdlib_archive)) or
            within(stdlib) or any(within(root) for root in extension_roots) or
            bool(extraction_root and within(extraction_root)))


class StandaloneCliTests(unittest.TestCase):
    def test_resource_build_cli_summarizes_case_and_inventory_manifests(self):
        from scripts import schedule_generator_build as builder
        # Exercise real CLI parsing/summary with complete returned manifest shapes;
        # source compilation is outside this return-contract regression.
        from atlas_schedules.resources import write_resources
        with tempfile.TemporaryDirectory() as directory:
            apartment=write_resources(Path(directory),{
                ('reference','first'):{'label':'contract_structure_only'},
                ('reference','second'):{'label':'contract_structure_only'}},
                {'scope':'apartments','scope_version':'1.0.0','interpretation':'CLI return-contract fixture'})
        legacy={'resource_set_id':'resources-legacy','resources':[{},{}],'cases':[{}, {}, {}]}
        for scope,manifest,expected in (
                ('pilot',legacy,'Verified 2 dependencies for 3 cases: resources-legacy'),
                ('apartments',apartment,f"Verified 2 dependencies: {apartment['resource_set_id']}")):
            output=io.StringIO()
            with (self.subTest(scope=scope),patch.object(builder,'build_resources',return_value=manifest),
                  patch.object(sys,'argv',['schedule_generator_build','--scope',scope,'--destination','isolated-output']),
                  contextlib.redirect_stdout(output)):
                self.assertIsNone(builder.main())
            self.assertEqual(output.getvalue().strip(),expected)
        self.assertNotIn('cases',apartment)

    def test_isolation_path_predicate_is_version_aware_and_bounded(self):
        stdlib = '/opt/hostedtoolcache/Python/3.11.14/x64/lib/python3.11'
        archive = '/opt/hostedtoolcache/Python/3.11.14/x64/lib/python311.zip'
        extension = stdlib + '/lib-dynload'
        extracted = '/tmp/atlas-schedules-actual'
        self.assertTrue(_audit_path_allowed(archive, stdlib, (extension,), archive, extracted))
        self.assertTrue(_audit_path_allowed(extension + '/_bz2.so', stdlib,
                                            (extension,), archive, extracted))
        self.assertTrue(_audit_path_allowed(extracted + '/atlas_schedules', stdlib,
                                            (extension,), archive, extracted))
        for untrusted in (stdlib + '-lookalike', extracted + '-lookalike',
                          '/tmp/untrusted-atlas-schedules-probe',
                          '/opt/hostedtoolcache/Python/3.11.14/x64/lib/python312.zip'):
            self.assertFalse(_audit_path_allowed(untrusted, stdlib, (extension,),
                                                 archive, extracted), untrusted)

    def test_api_cli_numerical_equivalence(self):
        from atlas_schedules.__main__ import main
        request = strict_json(REQUEST.read_bytes(), str(REQUEST))
        expected = generate(request['params'], request['seed'])
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'bundle.json'
            self.assertEqual(main(['--request', str(REQUEST), '--output', str(output)]), 0)
            actual = strict_json(output.read_bytes(), str(output))
        self.assertEqual(compare_bundles(actual, expected, expected['metadata']['comparison_policy']), [])

    def test_tampered_resource_and_duplicate_json_rejected(self):
        from atlas_schedules.__main__ import main
        with tempfile.TemporaryDirectory() as directory:
            request = Path(directory) / 'request.json'
            output = Path(directory) / 'bundle.json'
            request.write_text('{"schema_version":"1.0.0","schema_version":"1.0.0"}', encoding='utf-8')
            with self.assertRaises(ValueError):
                main(['--request', str(request), '--output', str(output)])
            self.assertFalse(output.exists())
            package = Path(directory) / 'atlas_schedules'
            shutil.copytree(ROOT / 'atlas_schedules', package,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            resource = package / 'data/reference/m1-scope.json'
            resource.write_bytes(resource.read_bytes() + b' ')
            request.write_bytes(REQUEST.read_bytes())
            script = ("import runpy,sys\n"
                      "sys.path.insert(0,sys.argv[1])\n"
                      "sys.argv=['atlas_schedules','--request',sys.argv[2],'--output',sys.argv[3]]\n"
                      "runpy.run_module('atlas_schedules.__main__',run_name='__main__')\n")
            result = subprocess.run([sys.executable, '-I', '-S', '-c', script, directory,
                                     str(request), str(output)], cwd=directory,
                                    capture_output=True, text=True, timeout=30)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('resource_integrity', result.stderr)
            self.assertFalse(output.exists())

    def test_unsupported_family_fails_clearly(self):
        from atlas_schedules.errors import GeneratorError
        request = strict_json(REQUEST.read_bytes(), str(REQUEST))
        request['params']['instances'][0]['program_id'] = 'program-0020ff2d980d748dbab37775'
        with self.assertRaises(GeneratorError) as caught:
            generate(request['params'], request['seed'])
        self.assertEqual(caught.exception.code, 'unsupported_binding')

    def test_standalone_zip_generates_offline(self):
        from scripts.schedule_generator_release import freeze_generator
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release = root / 'release'
            freeze_generator(release, '0.1.0')
            request = root / 'request.json'
            request.write_bytes(REQUEST.read_bytes())
            (root / 'external_probe.py').write_text('VALUE = 1\n', encoding='utf-8')
            output = root / 'bundle.json'
            # The child runs in an empty cwd with -I -S; an audit hook raises on
            # network/subprocess use and on any import outside stdlib or this ZIP.
            script = ("import os,runpy,sys,sysconfig,tempfile\nfrom pathlib import Path\n" +
                      inspect.getsource(_audit_path_allowed) +
                      "z=sys.argv[1]; request=sys.argv[2]; output=sys.argv[3]\n"
                      "stdlib=os.path.realpath(sysconfig.get_paths()['stdlib'])\n"
                      "stdlib_archive=os.path.realpath(os.path.join(os.path.dirname(stdlib),'python'+str(sys.version_info.major)+str(sys.version_info.minor)+'.zip'))\n"
                      "extensions=[os.path.join(stdlib,'lib-dynload')]\n"
                      "if os.name=='nt': extensions.append(os.path.join(sys.base_prefix,'DLLs'))\n"
                      "sys.path[:]=[entry for entry in sys.path if os.path.normcase(os.path.realpath(entry))!=os.path.normcase(os.path.realpath(sys.base_prefix))]\n"
                      "extraction={'root':None}\n"
                      "original_tempdir=tempfile.TemporaryDirectory\n"
                      "class CapturedTempdir(original_tempdir):\n"
                      " def __enter__(self):\n"
                      "  directory=super().__enter__()\n"
                      "  extraction['root']=os.path.realpath(directory)\n"
                      "  return directory\n"
                      "tempfile.TemporaryDirectory=CapturedTempdir\n"
                      "def audit(event,args):\n"
                      " if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.spawn','os.exec'):\n"
                      "  raise RuntimeError('forbidden runtime action: '+event)\n"
                      " if event=='import':\n"
                      "  for entry in sys.path:\n"
                      "   path=os.path.realpath(entry)\n"
                      "   allowed=(os.path.normcase(path)==os.path.normcase(os.path.realpath(z)) or\n"
                      "            (extraction['root'] and os.path.normcase(path)==os.path.normcase(extraction['root'])) or\n"
                      "            _audit_path_allowed(path,stdlib,extensions,stdlib_archive,None))\n"
                      "   if not allowed: raise RuntimeError('external import path: '+path)\n"
                      "  if len(args)>1 and args[1]:\n"
                      "   path=os.path.realpath(args[1]); name=args[0]\n"
                      "   package_root=os.path.join(extraction['root'],'atlas_schedules') if extraction['root'] else None\n"
                      "   allowed=(_audit_path_allowed(path,stdlib,extensions,stdlib_archive,None) or\n"
                      "            (package_root and name.split('.')[0]=='atlas_schedules' and\n"
                      "             _audit_path_allowed(path,package_root,(),stdlib_archive,None)))\n"
                      "   if not allowed: raise RuntimeError('external import: '+path)\n"
                      "sys.addaudithook(audit)\n"
                      "sys.path.insert(0,os.getcwd())\n"
                      "try: import external_probe\n"
                      "except RuntimeError: pass\n"
                      "else: raise AssertionError('external import was allowed')\n"
                      "sys.path.pop(0)\n"
                      "for forbidden in ('socket.connect','subprocess.Popen'):\n"
                      " try: sys.audit(forbidden)\n"
                      " except RuntimeError: pass\n"
                      " else: raise AssertionError('forbidden action was allowed')\n"
                      "sys.argv=[z,'--request',request,'--output',output]\n"
                      "runpy.run_path(z,run_name='__main__')\n")
            result = subprocess.run([sys.executable, '-I', '-S', '-c', script,
                                     str(release / 'generator.zip'), str(request), str(output)],
                                    cwd=root, capture_output=True, text=True, timeout=180)
            self.assertEqual(result.returncode, 0, result.stderr)
            bundle = strict_json(output.read_bytes(), str(output))
            self.assertEqual(len(bundle['schedules']), 8)
            self.assertTrue(all(len(s['values']) == 8760 for s in bundle['schedules'].values()))


if __name__ == '__main__':
    unittest.main()
