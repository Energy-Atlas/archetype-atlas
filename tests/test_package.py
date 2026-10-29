"""The atlas-schedules package: its version is the generator's, and it ships the data the generator reads (ADR 0049)."""
import re
import tomllib
import unittest
from pathlib import Path

import yaml

import atlas_schedules
from scripts.common import ROOT

RELEASE_VERSION = re.compile(r'^\d+\.\d+\.\d+$')


def pyproject():
    return tomllib.loads((ROOT/'pyproject.toml').read_text(encoding='utf-8'))


class PackageTests(unittest.TestCase):
    def test_package_version_is_the_generator_version(self):
        project = pyproject()
        self.assertEqual(project['project']['name'], 'atlas-schedules')
        self.assertIn('version', project['project']['dynamic'])
        self.assertEqual(project['tool']['setuptools']['dynamic']['version'], {'attr': 'atlas_schedules.__version__'})
        self.assertRegex(atlas_schedules.__version__, RELEASE_VERSION)  # a tagged release, not a dev build

    def test_bundles_name_the_package_version(self):
        from atlas_schedules.generator import generate
        request = {'schema_version': '3.0.0', 'seed': 1, 'instances': [
            {'key': 'office', 'program_id': 'program-0e670d8dc556f7f5bdd7f1a9', 'extent': {'floor_area': 100},
             'operating_group': 'building', 'service_links': {'service-7430007e80203f78a1297cc6': 'water'}},
            {'key': 'water', 'service_id': 'service-7430007e80203f78a1297cc6', 'physical_id': 'heater',
             'configuration_id': 'medium_office__90_1_2013__reviewed', 'extent': {'floor_area': 100}, 'operating_group': 'building'}]}
        self.assertEqual(generate(request)['generator_version'], atlas_schedules.__version__)

    def test_runtime_requirements_and_entry_points(self):
        project = pyproject()['project']
        self.assertEqual(project['requires-python'], '>=3.11')
        self.assertEqual(sorted(d.split('>=')[0] for d in project['dependencies']), ['jsonschema', 'numpy'])
        self.assertTrue(all('>=' in d for d in project['dependencies']))
        pinned = {line.split('==')[0] for line in (ROOT/'requirements.txt').read_text(encoding='utf-8').split()}
        self.assertTrue({'numpy', 'jsonschema'} <= pinned)
        self.assertEqual(project['scripts'], {'atlas-schedules': 'atlas_schedules.__main__:main'})
        self.assertEqual(project['license'], 'MIT')
        dev = (ROOT/'requirements-dev.txt').read_text(encoding='utf-8')
        self.assertRegex(dev, r'(?m)^build==')
        self.assertNotIn('build', (ROOT/'requirements.txt').read_text(encoding='utf-8'))

    def test_package_data_covers_every_file_the_generator_reads(self):
        patterns = pyproject()['tool']['setuptools']['package-data']['atlas_schedules']
        package = ROOT/'atlas_schedules'
        shipped = {p.relative_to(package).as_posix() for pattern in patterns for p in package.glob(pattern) if p.is_file()}
        present = {p.relative_to(package).as_posix() for folder in ('data', 'schemas') for p in (package/folder).rglob('*')
                   if p.is_file() and '__pycache__' not in p.parts}
        self.assertEqual(present - shipped, set())
        self.assertTrue(any(p.startswith('data/recipes/') for p in shipped))
        self.assertTrue(any(p.startswith('data/residential/characteristics/') and p.endswith('.gz') for p in shipped))
        self.assertIn('schemas/request-v3.schema.json', shipped)
        self.assertTrue(any(p.startswith('data/notices/') for p in shipped))

    def test_release_workflow_builds_the_wheel_for_a_matching_tag(self):
        workflow = yaml.load((ROOT/'.github/workflows/atlas-schedules-release.yml').read_text(encoding='utf-8'), Loader=yaml.BaseLoader)
        self.assertEqual(workflow['on']['push']['tags'], ['atlas-schedules-v*'])
        commands = '\n'.join(s.get('run', '') for j in workflow['jobs'].values() for s in j['steps'])
        for command in ('requirements-dev.txt', 'python -m build', 'atlas_schedules.__version__', 'gh release'):
            self.assertIn(command, commands)
        self.assertEqual(workflow['jobs']['wheel']['permissions'], {'contents': 'write'})


if __name__ == '__main__':
    unittest.main()
