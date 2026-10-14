"""Standalone generator behavior from a checkout-independent directory."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from atlas_schedules import generate
from atlas_schedules.comparison import compare_bundles
from atlas_schedules.resources import strict_json

ROOT = Path(__file__).resolve().parents[1]
REQUEST = ROOT / 'docs/examples/schedule-generator-v1/medium-office-request.json'


class StandaloneCliTests(unittest.TestCase):
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
            script = ("import os,runpy,sys,sysconfig\n"
                      "z=sys.argv[1]; request=sys.argv[2]; output=sys.argv[3]\n"
                      "stdlib=os.path.realpath(sysconfig.get_paths()['stdlib'])\n"
                      "def audit(event,args):\n"
                      " if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.spawn','os.exec'):\n"
                      "  raise RuntimeError('forbidden runtime action: '+event)\n"
                      " if event=='import':\n"
                      "  for entry in sys.path:\n"
                      "   path=os.path.realpath(entry)\n"
                      "   external=any(part in path.lower() for part in ('site-packages','dist-packages'))\n"
                      "   allowed=not external and (path.startswith(stdlib) or path.startswith(os.path.realpath(sys.base_prefix+'/DLLs')) or path==os.path.realpath(sys.base_prefix) or path==os.path.realpath(z) or 'atlas-schedules-' in path or path.endswith('python314.zip'))\n"
                      "   if not allowed: raise RuntimeError('external import path: '+path)\n"
                      "  if len(args)>1 and args[1]:\n"
                      "   path=os.path.realpath(args[1]); name=args[0]\n"
                      "   allowed=path.startswith(stdlib) or path.startswith(os.path.realpath(sys.base_prefix+'/DLLs')) or (name.startswith('atlas_schedules') and 'atlas-schedules-' in path)\n"
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
