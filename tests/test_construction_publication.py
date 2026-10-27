"""Foundation publication gates must verify current exports without native recovery."""
import unittest
import yaml
from scripts.common import ROOT


def workflow(name):
    return yaml.load((ROOT/'.github/workflows'/name).read_text(encoding='utf-8'),Loader=yaml.BaseLoader)


def job(name):
    """The research job behind a required check name such as 'atlas (windows-latest, 3.14)'."""
    return next(j for j in workflow('validate.yml')['jobs'].values() if j.get('name')==name)


REQUIRED=('atlas (ubuntu-latest, 3.11)','atlas (windows-latest, 3.14)')


def gated(name):
    """The jobs a required check passes on: its gate's needs."""
    jobs=workflow('validate.yml')['jobs']
    return [jobs[n] for n in job(name)['needs']]


class FoundationPublicationTests(unittest.TestCase):
    def test_exact_combined_reproduction_stays_on_pinned_windows_producer(self):
        windows=gated('atlas (windows-latest, 3.14)')
        self.assertEqual({j['runs-on'] for j in windows},{'windows-latest'})
        selected=[(j,s) for j in windows for s in j['steps'] if 'scripts.construction_foundation_release --check --examples' in s.get('run','')]
        self.assertEqual(len(selected),1,'Combined release must have an exact producer reproduction gate')
        steps=selected[0][0]['steps'];before=steps[:steps.index(selected[0][1])]
        versions=[s['with']['python-version'] for s in before if 'python-version' in s.get('with',{})]
        self.assertEqual(versions,['3.14.7'])

    def test_both_platforms_validate_combined_pairs_and_frozen_recovery_receipts(self):
        jobs=workflow('validate.yml')['jobs'];linux=job('atlas (ubuntu-latest, 3.11)')
        platforms={'windows':[s for j in gated('atlas (windows-latest, 3.14)') for s in j['steps']],
                   'linux':[s for name in linux['needs'] for s in jobs[name]['steps']]}
        for command in ('scripts.validate_construction_foundation --all','scripts.recover_construction_foundations --check',
                        'scripts.construction_foundation_airflow --check','scripts.construction_foundation_smoke',
                        'scripts.construction_delivery_validate'):
            for platform,steps in platforms.items():
                selected=[s for s in steps if 'python -m '+command in s.get('run','')]
                self.assertEqual(len(selected),1,command+' on '+platform)
        runs='\n'.join(s.get('run','') for steps in platforms.values() for s in steps)
        self.assertNotIn('--recover',runs)
        self.assertNotIn('scripts.construction_foundation_smoke --run',runs)
        self.assertNotIn('--fetch-runtime',runs)

    def test_linux_check_passes_only_when_every_linux_job_passes(self):
        jobs=workflow('validate.yml')['jobs'];linux=job('atlas (ubuntu-latest, 3.11)')
        self.assertEqual(set(linux['needs']),{k for k,j in jobs.items() if j['runs-on']=='ubuntu-latest' and j.get('name') not in REQUIRED})
        self.assertEqual(linux['if'],'always()')
        self.assertIn('needs.*.result',linux['steps'][0]['env']['RESULTS'])
        runs='\n'.join(s.get('run','') for j in jobs.values() for s in j['steps'])
        for command in ('unittest discover -s tests','scripts.program_completeness --check','scripts.smoke_catalogue',
                        'scripts.construction_base_reproduce','scripts.definition_release --reproduce','scripts.audit'):
            self.assertIn(command,runs)

    def test_windows_check_passes_only_when_every_windows_job_passes(self):
        jobs=workflow('validate.yml')['jobs'];windows=job('atlas (windows-latest, 3.14)')
        self.assertEqual(set(windows['needs']),{k for k,j in jobs.items() if j['runs-on']=='windows-latest'})
        self.assertEqual(windows['if'],'always()')
        self.assertIn('needs.*.result',windows['steps'][0]['env']['RESULTS'])

    def test_build_verifies_combined_closure_and_presentation_before_upload(self):
        jobs=workflow('catalogue-site.yml')['jobs'];steps=jobs['build']['steps']
        runs='\n'.join(s.get('run','') for s in steps)
        self.assertIn('scripts.construction_foundation_release import load_release',runs)
        self.assertIn('tests.test_construction_foundation_site',runs)
        self.assertIn('tests.test_construction_publication',runs)
        self.assertIn('scripts.construction_site_smoke',runs)
        self.assertEqual(jobs['deploy']['needs'],['research','build'])
        self.assertIn("github.ref == 'refs/heads/main'",jobs['deploy']['if'])


class ConstructionSmokeCasesTests(unittest.TestCase):
    def test_smoke_cases_use_current_versions_and_cover_native_methods_and_absence(self):
        from scripts import construction_site_smoke as smoke
        self.assertTrue(hasattr(smoke,'smoke_cases'),'Browser expectations must come from the combined frozen delivery')
        cases=smoke.smoke_cases();methods=set();absence=False
        self.assertGreaterEqual(len(cases),5)
        for case in cases:
            d,u=case['detailed'],case['unified']
            self.assertEqual((d['schema_version'],u['schema_version']),('3.0.0','2.0.0'))
            self.assertEqual(d['foundation_ground'],u['foundation_ground'])
            self.assertEqual(d['id'],case['context']['id'])
            methods.update(m['model'] for m in d['foundation_ground']['methods'].values())
            absence|=d['foundation_ground']['configuration']['type']=='no_direct_ground_contact'
        self.assertEqual(methods,{'FFactor','CFactor','Kiva','LayeredGround'})
        self.assertTrue(absence)


if __name__=='__main__':unittest.main()
