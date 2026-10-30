"""The CI gates: required check names, what they run, and no step reading a retired release (ADR 0046)."""
import re
import unittest

import yaml

from scripts import ci_tests, site_check, site_release, suite_site
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
        for command in ('scripts.ci_tests --shard', 'scripts.atlas_snapshot --verify', 'scripts.atlas_delta --check',
                        'scripts.atlas_exports --check-schemas', 'scripts.smoke_catalogue', 'scripts.audit'):
            self.assertIn(command, commands)

    def test_windows_check_runs_the_suite_on_python_3_14(self):
        jobs = workflow('validate.yml')['jobs']
        windows = job(REQUIRED[1])
        self.assertEqual(set(windows['needs']), {k for k, j in jobs.items() if j['runs-on'] == 'windows-latest'})
        self.assertEqual(windows['if'], 'always()')
        self.assertIn('needs.*.result', windows['steps'][0]['env']['RESULTS'])
        gated_jobs = gated(REQUIRED[1])
        self.assertIn('scripts.ci_tests --shard', runs(gated_jobs))
        versions = {s['with']['python-version'] for j in gated_jobs for s in j['steps'] if 'python-version' in s.get('with', {})}
        self.assertEqual(versions, {'3.14'})

    def test_unit_jobs_run_every_shard_on_both_platforms(self):
        jobs = workflow('validate.yml')['jobs']
        for name in ('unit-tests', 'windows-tests'):
            self.assertEqual(jobs[name]['strategy']['matrix']['shard'], list(ci_tests.SHARDS), name)
            self.assertIn('--shard ${{ matrix.shard }}', runs([jobs[name]]))

    def test_shards_partition_the_suite(self):
        shards = ci_tests.shards()
        everything = [t.id() for t in ci_tests.flatten(unittest.defaultTestLoader.discover(str(ROOT/'tests')))]
        ids = [t.id() for tests in shards.values() for t in tests]
        self.assertEqual(sorted(ids), sorted(everything))
        self.assertTrue(all(shards.values()))
        for name in ('schedules-commercial', 'schedules-rest'):
            self.assertTrue(all(type(t).__module__.startswith('schedules.') for t in shards[name]), name)
        self.assertEqual({type(t).__module__ for t in shards['schedules-commercial']}, set(ci_tests.COMMERCIAL))
        self.assertTrue(all(ci_tests.shard_of(t) == 'atlas' for t in shards['atlas']))
        self.assertTrue(all(not type(t).__module__.startswith('schedules.') for t in shards['atlas']))

    def test_only_a_main_push_skips_the_unit_shards_and_samples_nothing(self):
        site = workflow('catalogue-site.yml')
        self.assertEqual(site['jobs']['research']['with']['full'], "${{ github.event_name != 'push' }}")
        self.assertEqual(site['jobs']['research']['with']['full_catalogue'], "${{ github.event_name != 'pull_request' }}")
        self.assertIn('schedule', site['on'])
        jobs = workflow('validate.yml')['jobs']
        skipped = {name for name, j in jobs.items() if j.get('if') == 'inputs.full'}
        self.assertEqual(skipped, {'unit-tests', 'windows-tests'})
        self.assertEqual(jobs['schedules']['if'], 'inputs.full || inputs.full_catalogue')
        smoke = next(s for s in jobs['schedules']['steps'] if 'smoke_catalogue' in s.get('run', ''))
        self.assertEqual(smoke['env']['FULL_CATALOGUE'], '${{ inputs.full_catalogue }}')
        self.assertIn('if [ "$FULL_CATALOGUE" = true ]; then python -m scripts.smoke_catalogue; else python -m scripts.smoke_catalogue --sample 2; fi', smoke['run'])
        for name in ('release', 'package'):
            self.assertNotIn('if', jobs[name])
        for gate in REQUIRED:  # a skipped job passes a gate only when the run is not full
            step = job(gate)['steps'][0]
            self.assertEqual(step['env']['FULL'], '${{ inputs.full }}')
            self.assertIn('[ "$FULL" = false ] && [ "$result" = skipped ]', step['run'])

    def test_package_job_builds_installs_and_runs_the_wheel_outside_the_checkout(self):
        package = workflow('validate.yml')['jobs']['package']
        self.assertEqual(package['runs-on'], 'ubuntu-latest')
        commands = runs([package])
        for command in ('requirements-dev.txt', 'python -m build --wheel', 'python -m venv', 'pip install dist/*.whl', 'cd /tmp/quick-start',
                        'atlas-schedules office-and-retail.json', 'python -m atlas_schedules office-and-retail.json', "m.version('atlas-schedules')"):
            self.assertIn(command, commands)
        self.assertIn('package', job(REQUIRED[0])['needs'])

    def test_sampled_smoke_spreads_over_every_family(self):
        from scripts import smoke_catalogue
        sampled = smoke_catalogue.recipes(2)
        everything = smoke_catalogue.recipes(None)
        self.assertEqual({smoke_catalogue.family(r) for r in sampled}, {smoke_catalogue.family(r) for r in everything})
        self.assertLess(len(sampled), len(everything) / 4)
        self.assertEqual([r['program_id'] for r in sampled], [r['program_id'] for r in smoke_catalogue.recipes(2)])  # deterministic
        self.assertEqual(smoke_catalogue.spread(list(range(10)), 3), [0, 4, 8])
        self.assertEqual(smoke_catalogue.spread(list(range(3)), 3), [0, 1, 2])

    def test_site_cache_key_covers_what_the_site_reads(self):
        steps = workflow('catalogue-site.yml')['jobs']['build']['steps']
        cache = next(s for s in steps if s.get('id') == 'cache')
        self.assertIn('build/site-docs', cache['with']['path'])
        self.assertIn('build/site', cache['with']['path'].split())
        self.assertIn('steps.digest.outputs.value', cache['with']['key'])
        modules = suite_site.generator_modules()
        for module in ('scripts.suite_site', 'scripts.atlas_exports', 'scripts.lod_site', 'scripts.site_asset_versions'):  # the last via a hook
            self.assertIn(module, modules)
        self.assertNotIn('scripts.ci_tests', modules)
        self.assertIn('data/lod-recommendations', suite_site.DIGEST_INPUTS)  # the zoning pages' data drop (ADR 0050)

    def test_no_step_reads_a_retired_release(self):
        for name in ('validate.yml', 'catalogue-site.yml'):
            commands = runs(workflow(name)['jobs'].values())
            for retired in RETIRED:  # whole names: scripts.release_editor is not scripts.release
                self.assertIsNone(re.search(re.escape(retired)+r'(?![A-Za-z0-9_])' if retired[-1].isalnum() else re.escape(retired), commands),
                                  f'{name}: {retired}')

    def test_build_verifies_the_suite_site_before_upload(self):
        jobs = workflow('catalogue-site.yml')['jobs']
        commands = runs([jobs['build']])
        for command in ('scripts.suite_site', 'mkdocs build --strict', 'scripts.site_check', 'scripts.site_smoke', 'tests.test_suite_site'):
            self.assertIn(command, commands)
        self.assertEqual(jobs['deploy']['needs'], ['research', 'build'])
        self.assertIn("github.ref == 'refs/heads/main'", jobs['deploy']['if'])

    def test_a_pull_request_builds_a_sample_and_every_other_event_the_full_cached_published_site(self):
        jobs = workflow('catalogue-site.yml')['jobs']
        self.assertEqual(set(jobs), {'research', 'build', 'deploy'})  # the required check is named `build`
        build = jobs['build']
        self.assertEqual(build['env']['FULL_SITE'], "${{ github.event_name != 'pull_request' }}")
        steps = {s.get('id') or s.get('name') or s['uses']: s for s in build['steps']}
        for name in ('digest', 'cache', 'Upload verified Pages artifact'):  # no cache and no Pages artifact for a sample
            self.assertEqual(steps[name]['if'], "env.FULL_SITE == 'true'", name)
        generate = next(s for s in build['steps'] if 'scripts.suite_site' in s.get('run', '') and '--digest' not in s['run'])
        self.assertEqual(generate['if'], "steps.cache.outputs.cache-hit != 'true'")  # empty when the cache step is skipped
        self.assertIn('if [ "$FULL_SITE" = true ]; then python -m scripts.suite_site; else python -m scripts.suite_site --sample 1; fi', generate['run'])
        self.assertEqual(steps['Build']['if'], "steps.cache.outputs.cache-hit != 'true'")
        verify = next(s for s in build['steps'] if 'scripts.site_check' in s.get('run', ''))
        self.assertNotIn('if', verify)
        self.assertIn('if [ "$FULL_SITE" = true ]; then python -m scripts.site_check --require-complete; else python -m scripts.site_check; fi', verify['run'])
        self.assertIn('python -m scripts.site_smoke', verify['run'])
        self.assertEqual(jobs['deploy']['if'].split(), "github.ref == 'refs/heads/main' && (github.event_name == 'push' || "
                         "(github.event_name == 'workflow_dispatch' && inputs.deploy))".split())

    def test_sample_rule_prefers_every_mode_then_the_cheapest_folder_and_is_deterministic(self):
        release = FakeRelease({'commercial/90-1-2019/office/': (['source']*40+['general']*12, 126),
                               'commercial/90-1-2019/retail-standalone/': (['source']*5+['general', 'department'], 21),
                               'commercial/90-1-2019/hospital/': (['source']*20+['general']*3+['department']*3, 21),
                               'commercial/90-1-2019/small-office/': (['source']*2, 21),
                               'residential/iecc-2021/single-family/': (['dwelling']*2, 76),
                               'residential/iecc-2021/multifamily/': (['dwelling']*2, 72),
                               'residential/resstock-sdr/highrise-apartment/': (['dwelling'], 1)})
        self.assertEqual(suite_site.sample_folders(release, 1), ['commercial/90-1-2019/retail-standalone/', 'residential/iecc-2021/multifamily/',
                                                                  'residential/resstock-sdr/highrise-apartment/'])
        self.assertEqual(suite_site.sample_folders(release, 2)[:2], ['commercial/90-1-2019/hospital/', 'commercial/90-1-2019/retail-standalone/'])
        self.assertEqual(len(suite_site.sample_folders(release, 9)), 7)
        self.assertEqual(suite_site.sample_folders(release, 1), suite_site.sample_folders(release, 1))

    def test_sampled_site_covers_every_template_and_page_kind_of_the_release(self):
        """What the pull-request build (`--sample 1`) covers of the newest release, and what site_smoke picks from it."""
        release = site_release.SiteRelease()
        folders = suite_site.sample_folders(release, 1)
        self.assertEqual(folders, sorted(folders))
        templates = {(f.family, f.template) for f in release.folders.values()}
        self.assertEqual({(release.folders[f].family, release.folders[f].template) for f in folders}, templates)
        self.assertEqual(len(folders), len(templates))  # one each, so every template index and library trail resolves
        modes = {release.programs[p][1] for f in folders for p in release.folders[f].programs}
        self.assertEqual(modes, {release.programs[p][1] for p in release.programs})
        sets = {s: release.sets[s][1] for f in folders for s in release.folders[f].sets}
        self.assertTrue(any(s.startswith('90-1-2019.') and len(r.get('contexts', {})) > 3 for s, r in sets.items()))  # site_smoke's commercial set
        self.assertTrue(any(s.startswith('iecc-') and all('.' in k for k in r['contexts']) for s, r in sets.items()))  # its foundation axes
        programs = {p for f in folders for p in release.folders[f].programs}
        self.assertTrue(any(p.startswith('resstock-sdr.') for p in programs))  # its dwelling with annual schedules
        self.assertTrue(any(p.startswith('iecc-') for p in programs))  # its source-only program
        cost = sum(suite_site.folder_cost(release, release.folders[f]) for f in folders)
        self.assertLess(cost, sum(suite_site.folder_cost(release, f) for f in release.folders.values()) / 5)

    def test_sampled_check_excuses_only_links_into_folders_the_sample_left_out(self):
        unbuilt = site_check.unbuilt_folder({'sample': {'folders_per_template': 1, 'folders': ['commercial/90-1-2019/retail-standalone/']}})
        self.assertTrue(unbuilt('catalogue/commercial/90-1-2019/office/'))
        self.assertTrue(unbuilt('catalogue/commercial/90-1-2019/office/programs/source/x/'))
        self.assertFalse(unbuilt('catalogue/commercial/90-1-2019/retail-standalone/programs/source/x/'))
        self.assertFalse(unbuilt('catalogue/commercial/90-1-2019/'))
        self.assertFalse(unbuilt(f'catalogue/commercial/90-1-2019/{suite_site.LIBRARY}/'))
        self.assertFalse(unbuilt('zoning/office/'))
        self.assertFalse(site_check.unbuilt_folder({'partial': True})('catalogue/commercial/90-1-2019/office/'))


class FakeRelease:
    """A release index of folders with the given program modes and construction contexts (site_release.SiteRelease's shape)."""

    def __init__(self, folders):
        self.folders, self.programs, self.sets = {}, {}, {}
        for path, (modes, contexts) in folders.items():
            folder = site_release.Folder(path)
            for i, mode in enumerate(modes):
                self.programs[f'{path}p{i}'] = (path, mode, {})
                folder.programs.append(f'{path}p{i}')
            self.sets[path+'s'] = (path, {'contexts': {str(c): {} for c in range(contexts)}})
            folder.sets.append(path+'s')
            self.folders[path] = folder


if __name__ == '__main__':
    unittest.main()
