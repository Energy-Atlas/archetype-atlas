import copy
import tempfile
import unittest
from pathlib import Path

from scripts.common import ROOT, load_atlas, load_json


class WaterReportingTests(unittest.TestCase):
    def module(self):
        from scripts import water_reporting
        return water_reporting

    def test_reference_floor_vertices_include_y_z_and_multiplier_once(self):
        text = '''OS:Surface,
 {floor}, !- Handle
 Test floor, !- Name
 Floor, !- Surface Type
 , !- Construction Name
 {space}, !- Space Name
 , !- Outside Boundary Condition
 , !- Outside Boundary Condition Object
 , !- Sun Exposure
 , !- Wind Exposure
 , !- View Factor to Ground
 , !- Number of Vertices
 0,0,3, !- X,Y,Z Vertex 1 {m}
 4,0,3, !- X,Y,Z Vertex 2 {m}
 4,5,3, !- X,Y,Z Vertex 3 {m}
 0,5,3; !- X,Y,Z Vertex 4 {m}
'''
        areas = self.module().floor_areas(text)
        self.assertEqual(areas, {'{space}': 20.0})

    def test_complete_variant_keeps_source_unknowns_and_shared_services(self):
        m=self.module();p=m.build()
        self.assertEqual(len(p['programs']),734)
        self.assertEqual(len(p['services']),217)
        self.assertEqual(p['summary']['source_only_water_gaps'],279)
        self.assertEqual(p['summary']['operational_water_gaps'],0)
        self.assertTrue(any(s['allocation_status']=='retained_shared_service' for s in p['services']))
        self.assertTrue(any(s['allocation_status']=='derived_design_occupant_allocation' for s in p['services']))
        self.assertTrue(any(s['allocation_status']=='derived_dedicated_kitchen_process' for s in p['services']))
        self.assertTrue(all(r['reporting_schedule_id'] for r in p['programs']))
        hospital=[s for s in p['services'] if s['building_type']=='Hospital' and s['end_use']=='main']
        self.assertTrue(all(not s['allocation_weights'] and s['allocation_status']=='retained_shared_service' for s in hospital))
        dining=next(r for r in p['programs'] if r['building_type']=='FullServiceRestaurant' and r['template']=='90.1-2013' and r['source_space_type']=='Dining')
        self.assertEqual(dining['local_draw_status'],'source_no_local_draw')
        self.assertEqual(dining['reporting_status'],'zero_local_draw')
        self.assertTrue(dining['building_service_path_ids'])

    def test_operational_coverage_is_reported_separately_from_source_gaps(self):
        from scripts.schedule_coverage import build as coverage
        p=self.module().build();report=coverage(water_reporting=p)
        self.assertEqual(report['commercial']['missing_schedule_fields'],279)
        self.assertEqual(report['water_reporting_variant']['remaining_schedule_gaps'],0)
        self.assertEqual(report['water_reporting_variant']['supplied_schedule_fields'],5138)
        self.assertFalse(report['water_reporting_variant']['full_simulation_readiness'])

    def test_nonconserving_weight_and_orphan_program_are_rejected(self):
        m=self.module();p=m.build();data=load_atlas(m.BASE);completion=load_json(m.COMPLETION/'commercial-completion.json')
        q=copy.deepcopy(p);s=next(s for s in q['services'] if s['allocation_weights']);key=next(iter(s['allocation_weights']));s['allocation_weights'][key]=2
        with self.assertRaisesRegex(ValueError,'allocation'):m.validate_packet(q,data,completion)
        q=copy.deepcopy(p);q['programs'].pop()
        with self.assertRaisesRegex(ValueError,'inventory'):m.validate_packet(q,data,completion)

    def test_each_program_peak_is_checked_even_when_shapes_are_shared(self):
        m=self.module();p=m.build();data=load_atlas(m.BASE);completion=load_json(m.COMPLETION/'commercial-completion.json')
        positive=[r for r in p['programs'] if r['reference_reporting_peak_flow_m3_s']>0]
        seen=set();row=None
        for r in positive:
            if r['reporting_schedule_id'] in seen:row=r;break
            seen.add(r['reporting_schedule_id'])
        self.assertIsNotNone(row)
        row['reference_reporting_peak_flow_m3_s']*=2
        with self.assertRaisesRegex(ValueError,'conservation'):m.validate_packet(p,data,completion)

    def test_reference_weights_deduplicate_spaces_and_hvac_services(self):
        m=self.module();data=load_atlas(m.BASE);refs=m.reference_context(data)
        office=next(p for p in data['programs'] if (p['building_type'],p['template'],p['source_space_type'])==('Warehouse','90.1-2013','Office'))
        self.assertAlmostEqual(refs[office['id']]['represented_area_m2'],236.8796,places=3)
        self.assertAlmostEqual(refs[office['id']]['design_occupants'],4.9975,places=3)
        duplicate=copy.deepcopy(data);duplicate['mappings']+=copy.deepcopy(data['mappings'])
        self.assertEqual(m.reference_context(duplicate),refs)

    def test_null_density_keeps_main_service_shared_instead_of_zero_weights(self):
        m=self.module();data=load_atlas(m.BASE);references=m.reference_context(data)
        candidates=[p for p in data['programs'] if (p['building_type'],p['template'])==('Warehouse','90.1-2013') and p['source_space_type']!='Attic']
        office=next(p for p in candidates if p['source_space_type']=='Office');references[office['id']]['design_occupants']=None
        draw=next(d for d in load_json(m.COMPLETION/'commercial-completion.json')['draw_paths'] if d['path_id']=='Warehouse|90.1-2013|main')
        status,weights=m.allocation(draw,candidates,references)
        self.assertEqual(status,'retained_shared_service');self.assertEqual(weights,{})

    def test_derived_support_zero_does_not_claim_a_retained_shared_service(self):
        p=self.module().build()
        fine=next(r for r in p['programs'] if (r['building_type'],r['template'],r['source_space_type'])==('Warehouse','90.1-2019','Fine'))
        self.assertEqual(fine['reporting_status'],'zero_attribution_only')
        self.assertEqual(fine['local_draw_status'],'source_local_assignment_unknown')

    def test_source_fields_relationships_and_summary_cannot_be_fabricated(self):
        m=self.module();p=m.build();data=load_atlas(m.BASE);completion=load_json(m.COMPLETION/'commercial-completion.json')
        for field,value in [('source_schedule_id','fabricated'),('target_temperature_degC',999),('end_use','laundry')]:
            q=copy.deepcopy(p);q['services'][0][field]=value
            with self.assertRaisesRegex(ValueError,'Source'):m.validate_packet(q,data,completion)
        q=copy.deepcopy(p);q['programs'][0]['building_service_path_ids']=['does-not-exist']
        with self.assertRaisesRegex(ValueError,'relationship'):m.validate_packet(q,data,completion)
        q=copy.deepcopy(p);q['summary']['operational_water_gaps']=999
        with self.assertRaisesRegex(ValueError,'summary'):m.validate_packet(q,data,completion)

    def test_freeze_is_immutable_and_reproduces_with_pinned_dependencies(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'v0.1.0';p=m.freeze(target)
            self.assertEqual(m.validate_bundle(target),p)
            with self.assertRaisesRegex(ValueError,'overwrite'):m.freeze(target)
            (target/'water-reporting.json').write_text('{}',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'checksum'):m.validate_bundle(target)


if __name__=='__main__':unittest.main()
