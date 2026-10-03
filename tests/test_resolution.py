"""Evidence gates for selective resolutions; unknown values stay unknown."""
import copy
import importlib
import shutil
import tempfile
import unittest
from pathlib import Path
from scripts.common import ROOT, load_json, dump_json


class ResolutionTests(unittest.TestCase):
    def module(self):
        return importlib.import_module('scripts.resolve')

    def test_missing_or_positive_load_does_not_prove_zero(self):
        rule = self.module().source_zero
        for value in [None, 0.1, -1, False]:
            self.assertFalse(rule({'density':value,'schedule':None}, 'density','schedule'))
        self.assertTrue(rule({'density':0.0,'schedule':None},'density','schedule'))
        self.assertFalse(rule({'density':0,'schedule':'existing'},'density','schedule'))

    def electric_options(self):
        return {'Heating Fuel':'Electricity','HVAC Secondary Heating Fuel':'None',
                'Clothes Dryer':'Electric','Cooking Range':'Electric Resistance',
                'Water Heater Efficiency':'Electric Standard','Misc Gas Fireplace':'None',
                'Misc Gas Grill':'None','Misc Gas Lighting':'None',
                'Misc Pool Heater':'None','Misc Hot Tub Spa':'None'}

    def test_electric_hvac_alone_does_not_prove_all_electric(self):
        rule = self.module().all_electric
        options = self.electric_options()
        self.assertTrue(rule(options))
        for key,value in [('Cooking Range','Gas'),('Water Heater Efficiency','Other Fuel'),
                          ('Misc Gas Fireplace','Gas Fireplace'),('HVAC Secondary Heating Fuel','Natural Gas')]:
            other=options.copy();other[key]=value
            self.assertFalse(rule(other))
        del options['Clothes Dryer']
        self.assertFalse(rule(options))

    def test_conditioning_requires_reviewed_id_and_source_guards(self):
        rule = self.module().unconditioned
        row={'id':'p','source_space_type':'Plenum','heating_setpoint_schedule_id':None,
             'cooling_setpoint_schedule_id':None}
        mappings=[{'program_id':'p','system_id':None,'part_of_total_floor_area':['No']}]
        self.assertFalse(rule(row,mappings,[]))
        self.assertTrue(rule(row,mappings,['p']))
        other=copy.deepcopy(mappings);other[0]['system_id']='hvac'
        self.assertFalse(rule(row,other,['p']))
        row['heating_setpoint_schedule_id']='actual'
        self.assertFalse(rule(row,mappings,['p']))

    def test_policy_never_changes_frozen_source_rows(self):
        module=self.module()
        from scripts.common import load_atlas
        data=load_atlas(ROOT/'data/releases/v0.2.0'); original=copy.deepcopy(data)
        policy=load_json(ROOT/'sources/resolution-policy.json')
        result=module.resolve_records(data,policy,[])
        self.assertEqual(data,original)
        self.assertTrue(result['resolutions'])
        # Positive equipment in hotel electrical rooms must survive.
        rows={r['id']:r for r in data['programs']}
        for resolution in result['resolutions']:
            if resolution['record_table']=='programs' and resolution['field']=='electric_equipment_schedule_id':
                self.assertLessEqual(rows[resolution['record_id']]['electric_equipment_W_m2'] or 0,0)

    def test_positive_water_demand_blocks_reviewed_zero(self):
        from scripts.common import load_atlas
        module=self.module(); data=load_atlas(ROOT/'data/releases/v0.2.0')
        policy=load_json(ROOT/'sources/resolution-policy.json')
        row=next(r for r in data['programs'] if r['id'] in policy['no_hot_water_program_ids'])
        row['source_attributes']['service_water_heating_peak_flow_rate']=1
        result=module.resolve_records(data,policy,[])
        self.assertFalse(any(r['record_id']==row['id'] and r['rule']=='reviewed_no_hot_water' for r in result['resolutions']))

    def test_frozen_bundle_reproduces_rules_and_profiles(self):
        result=self.module().validate_bundle(ROOT/'data/resolution-releases/v0.1.0')
        self.assertEqual(result['summary']['by_rule']['reviewed_unconditioned'],24)

    def test_profile_paths_cannot_escape_output(self):
        rule=self.module().profile_name
        self.assertTrue(rule('residential_archetype-'+'a'*20+'.json'))
        for path in ['../outside.json','C:/outside.csv','profiles/x.json','wrong.json']:
            with self.assertRaises(ValueError):
                rule(path)

    def test_failed_latest_attempt_cannot_freeze_previous_success(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); previous=root/'output'
            bundle=ROOT/'data/resolution-releases/v0.1.0'
            shutil.copytree(bundle/'profiles',previous)
            shutil.copyfile(bundle/'profile-index.json',previous/'profile-index.json')
            dump_json(root/'latest-run.json',{'status':'failed','output':'output'})
            target=root/'new-release'
            with self.assertRaisesRegex(ValueError,'completed'):
                self.module().freeze(previous,target)
            self.assertFalse(target.exists())


if __name__ == '__main__':
    unittest.main()
