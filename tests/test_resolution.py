"""Evidence gates for selective resolutions; unknown values stay unknown."""
import copy
import importlib
import shutil
import tempfile
import unittest
from pathlib import Path
from scripts.common import ROOT, load_json, dump_json


class ResolutionTests(unittest.TestCase):
    def test_reviewed_gas_absence_cannot_override_positive_or_unreviewed_loads(self):
        from scripts.common import load_atlas
        data=load_atlas(ROOT/'data/releases/v0.2.0')
        policy=load_json(ROOT/'sources/resolution-policy.json')
        def gas(rows):
            return [r for r in self.module().resolve_records(rows,policy,[])['resolutions']
                    if r['rule']=='reviewed_no_gas_equipment']
        resolved=gas(data)
        self.assertEqual(len(resolved),1426)  # 713 schedules and matching densities
        row=next(r for r in data['programs'] if r['id']==resolved[0]['record_id'])
        for field,value in [('gas_equipment_W_m2',1),('gas_equipment_schedule_id','existing')]:
            altered=copy.deepcopy(data)
            next(r for r in altered['programs'] if r['id']==row['id'])[field]=value
            self.assertFalse(any(r['record_id']==row['id'] for r in gas(altered)))
        for field,value in [('gas_equipment_per_area',1),('additional_gas_equipment_schedule','existing')]:
            altered=copy.deepcopy(data)
            next(r for r in altered['programs'] if r['id']==row['id'])['source_attributes'][field]=value
            self.assertFalse(any(r['record_id']==row['id'] for r in gas(altered)))
        altered=copy.deepcopy(data)
        next(r for r in altered['programs'] if r['id']==row['id'])['id']='program-unreviewed'
        self.assertFalse(any(r['record_id']=='program-unreviewed' for r in gas(altered)))

    def test_background_defaults_have_no_weather_dependency_and_preserve_seasonality(self):
        from scripts.fixed_background import build, annual_series
        packet=build()
        self.assertEqual(set(packet['schedules']),{'refrigerator','freezer'})
        for schedule in packet['schedules'].values():
            annual=annual_series(schedule,2007)
            self.assertEqual(len(annual),8760)
            self.assertEqual(max(annual),1)
            self.assertGreater(min(annual),0)
            self.assertLess(annual[17],annual[24*181+17])
            self.assertEqual(len(schedule['evidence']),3)
            self.assertFalse(schedule['temperature_dependent'])
        from scripts.common import load_atlas
        result=self.module().resolve_records(load_atlas(ROOT/'data/releases/v0.2.0'),
                  load_json(ROOT/'sources/resolution-policy.json'),[],packet)
        defaults=[r for r in result['resolutions'] if r['rule']=='fixed_background_default']
        self.assertEqual(len(defaults),5)
        self.assertEqual(len({r['record_id'] for r in defaults}),3)

    def test_approved_plenum_lighting_and_data_center_occupancy(self):
        from scripts.common import load_atlas
        data=load_atlas(ROOT/'data/releases/v0.2.0')
        policy=load_json(ROOT/'sources/resolution-policy.json')
        result=self.module().resolve_records(data,policy,[])
        lights=[r for r in result['resolutions'] if r['rule']=='reviewed_no_lighting']
        self.assertEqual(len(lights),10)
        rows={r['id']:r for r in data['programs']}
        for r in lights:
            self.assertEqual(rows[r['record_id']]['source_space_type'],'Plenum')
            self.assertEqual(r['resolved_value']['constant_value'],0)
        centers=[r for r in result['resolutions'] if r['rule']=='reviewed_no_occupancy'
                 and 'Data Center' in rows[r['record_id']]['source_space_type']]
        self.assertEqual(len(centers),6)
        for r in centers:
            row=rows[r['record_id']]
            self.assertIsNotNone(row['lighting_schedule_id'])
            self.assertGreater(row['electric_equipment_W_m2'],0)
            self.assertIn('data-centre',r['note'])
        self.assertEqual(result['schema_version'],'0.3.0')

    def test_approved_zeros_reject_contradictory_loads_and_unreviewed_rooms(self):
        from scripts.common import load_atlas
        data=load_atlas(ROOT/'data/releases/v0.2.0')
        policy=load_json(ROOT/'sources/resolution-policy.json')
        lights=next(r for r in data['programs'] if r['source_space_type']=='Plenum'
                    and r['lighting_schedule_id'] is None)
        center=next(r for r in data['programs'] if 'Data Center' in r['source_space_type'])
        for field,value in [('lighting_W_m2',1),('lighting_schedule_id','actual')]:
            altered=copy.deepcopy(data)
            next(r for r in altered['programs'] if r['id']==lights['id'])[field]=value
            resolutions=self.module().resolve_records(altered,policy,[])['resolutions']
            self.assertFalse(any(r['record_id']==lights['id'] and r['rule']=='reviewed_no_lighting' for r in resolutions))
        center['people_per_m2']=0.01
        resolutions=self.module().resolve_records(data,policy,[])['resolutions']
        self.assertFalse(any(r['record_id']==center['id'] and r['rule']=='reviewed_no_occupancy' for r in resolutions))
        altered=copy.deepcopy(data)
        next(r for r in altered['programs'] if r['id']==lights['id'])['id']='program-unreviewed'
        resolutions=self.module().resolve_records(altered,policy,[])['resolutions']
        self.assertFalse(any(r['record_id']=='program-unreviewed' and r['rule']=='reviewed_no_lighting' for r in resolutions))

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
        latest=self.module().validate_bundle(ROOT/'data/resolution-releases/v0.2.0')
        self.assertEqual(latest['summary']['resolution_rows'],693)
        self.assertEqual(latest['summary']['by_rule']['reviewed_no_lighting'],10)
        self.assertEqual(latest['summary']['by_rule']['reviewed_no_occupancy'],30)

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
