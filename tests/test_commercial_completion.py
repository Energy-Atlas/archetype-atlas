import copy
import unittest
from scripts.common import ROOT

class CommercialCompletionTests(unittest.TestCase):
    def module(self):
        from scripts import commercial_completion
        return commercial_completion

    def test_water_inventory_preserves_unallocated_services_and_source_order(self):
        packet=self.module().build()
        self.assertEqual(len(packet['draw_paths']),217)
        self.assertEqual(len(packet['schedules']),28)
        self.assertEqual(sum(p['allocation_status']=='building_service_unallocated' for p in packet['draw_paths']),59)
        gaps=packet['missing_program_evidence']
        self.assertEqual(sum(g['zero_schedule_eligible'] for g in gaps),206)
        self.assertEqual(sum(g['coverage_resolution_status']=='allocation_unknown' for g in gaps),279)
        self.assertTrue(all(not g['zero_schedule_eligible'] for g in gaps if g.get('building_service_paths')))
        for s in packet['schedules']:
            self.assertEqual(s['source_order'],sorted(s['source_order']))
            for original,normalized in zip(s['source_rows'],s['normalized_source_rows']):
                self.assertEqual({k:v for k,v in original.items() if k!='values'},{k:v for k,v in normalized.items() if k!='values'})
                for a,b in zip(original['values'],normalized['values']):self.assertAlmostEqual(a,b*s['peak_divisor'])

    def test_inactive_controls_require_all_generated_phases_and_no_shared_control(self):
        m=self.module();packet=m.build()
        self.assertEqual(len(packet['controls']),19)
        for c in packet['controls']:self.assertTrue(m.inactive_control(c))
        for key,value in [('heating_schedule','active'),('equipment',[['HVAC','x']]),('zone_spaces',['x','y']),('zone_mixing',['mix'])]:
            c=copy.deepcopy(packet['controls'][0]);c['runtime_evidence'][0][key]=value
            self.assertFalse(m.inactive_control(c))
        c=copy.deepcopy(packet['controls'][0]);c['runtime_phases'].remove('custom_hvac_tweaks')
        self.assertFalse(m.inactive_control(c))

    def test_duplicate_or_nonconserving_allocation_is_rejected(self):
        m=self.module();p=m.build();p['draw_paths'].append(copy.deepcopy(p['draw_paths'][0]))
        with self.assertRaisesRegex(ValueError,'Duplicate'):m.validate_packet(p)
        p=m.build();d=next(d for d in p['draw_paths'] if d['beneficiary_program_ids']);d['allocation_weights']={d['beneficiary_program_ids'][0]:2}
        with self.assertRaisesRegex(ValueError,'allocation'):m.validate_packet(p)

    def test_combined_overlay_closes_only_supported_coverage_gaps(self):
        from scripts.common import load_atlas,load_json
        from scripts.resolve import resolve_records
        from scripts.fixed_background import build as fixed
        from scripts.schedule_coverage import build as coverage
        data=load_atlas(ROOT/'data/releases/v0.2.0');policy=load_json(ROOT/'sources/resolution-policy.json')
        result=resolve_records(data,policy,load_json(ROOT/'data/resolution-releases/v0.3.0/profile-index.json'),fixed(names=policy['fixed_default_names']),self.module().build())
        report=coverage(data,result,supplement_version='v0.4.0')
        self.assertEqual(report['commercial']['missing_by_field'],{'service_water_heating_schedule_id':279})
        self.assertEqual(report['residential']['missing_profile_fields'],0)
        self.assertEqual(report['residential']['additional_end_uses']['missing_records'],[])

if __name__=='__main__':unittest.main()
