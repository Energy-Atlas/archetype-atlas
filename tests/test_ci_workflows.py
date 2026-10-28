"""The CI gates: required check names, what they run, and no step reading a retired release (ADR 0046)."""
import unittest

import yaml

from scripts.common import ROOT

REQUIRED = ('atlas (ubuntu-latest, 3.11)', 'atlas (windows-latest, 3.14)')
RETIRED = ('atlas_release', 'atlas_delta_release', 'atlas_minor_release', 'definition_release', 'program_completeness',
           'schedule_coverage', 'construction_', 'resolve', 'scripts.release', 'water_reporting', 'water_equivalent',
           'commercial_completion', 'data/releases', 'definition-releases', 'resolution-releases', 'atlas-releases/v1.')


def workflow(name):
    return yaml.load((ROOT/'.github/workflows'/name).read_text(encoding='utf-8'), Loader=yaml.BaseLoader)


def job(name):
    """The gate job behind a required check name such as 'atlas (windows-latest, 3.14)'."""
    return next(j for j in workflow('validate.yml')['jobs'].values() if j.get('name') == name)


def gated(name):
    """The jobs a required check passes on: its gate's needs."""
    jobs = workflow('validate.yml')['jobs']
    return [jobs[n] for n in job(name)['needs']]


def runs(jobs):
    return '\n'.join(s.get('run', '') for j in jobs for s in j.get('steps', []))


class WorkflowTests(unittest.TestCase):
    def test_linux_check_passes_only_when_every_linux_job_passes(self):
        jobs = workflow('validate.yml')['jobs']
        linux = job(REQUIRED[0])
        self.assertEqual(set(linux['needs']), {k for k, j in jobs.items() if j['runs-on'] == 'ubuntu-latest' and j.get('name') not in REQUIRED})
        self.assertEqual(linux['if'], 'always()')
        self.assertIn('needs.*.result', linux['steps'][0]['env']['RESULTS'])
        commands = runs(gated(REQUIRED[0]))
        for command in ('unittest discover -s tests', 'scripts.atlas_snapshot --verify', 'scripts.atlas_exports --check-schemas',
                        'scripts.smoke_catalogue', 'scripts.audit'):
            self.assertIn(command, commands)

    def test_windows_check_runs_the_suite_on_python_3_14(self):
        jobs = workflow('validate.yml')['jobs']
        windows = job(REQUIRED[1])
        self.assertEqual(set(windows['needs']), {k for k, j in jobs.items() if j['runs-on'] == 'windows-latest'})
        self.assertEqual(windows['if'], 'always()')
        self.assertIn('needs.*.result', windows['steps'][0]['env']['RESULTS'])
        gated_jobs = gated(REQUIRED[1])
        self.assertIn('unittest discover -s tests', runs(gated_jobs))
        versions = {s['with']['python-version'] for j in gated_jobs for s in j['steps'] if 'python-version' in s.get('with', {})}
        self.assertEqual(versions, {'3.14'})

    def test_no_step_reads_a_retired_release(self):
        for name in ('validate.yml', 'catalogue-site.yml'):
            commands = runs(workflow(name)['jobs'].values())
            for retired in RETIRED:
                self.assertNotIn(retired, commands, f'{name}: {retired}')

    def test_build_verifies_the_suite_site_before_upload(self):
        jobs = workflow('catalogue-site.yml')['jobs']
        commands = runs([jobs['build']])
        for command in ('scripts.suite_site', 'mkdocs build --strict', 'scripts.site_check', 'scripts.site_smoke', 'tests.test_suite_site'):
            self.assertIn(command, commands)
        self.assertEqual(jobs['deploy']['needs'], ['research', 'build'])
        self.assertIn("github.ref == 'refs/heads/main'", jobs['deploy']['if'])


if __name__ == '__main__':
    unittest.main()
