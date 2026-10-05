import tempfile
import unittest
from pathlib import Path

from scripts.common import ROOT, load_atlas, load_json


class WaterReportingSiteTests(unittest.TestCase):
    def test_program_view_exposes_assumptions_and_shared_relationships(self):
        from scripts import site_water_reporting
        packet=load_json(ROOT/'data/water-reporting-releases/v0.1.0/water-reporting.json')
        row=next(p for p in packet['programs'] if p['building_type']=='Hospital')
        current='releases/v0.2.0/programs/'+row['program_id']+'.md'
        page=site_water_reporting.program_html(current,row,packet)
        self.assertIn('shared',page.lower())
        self.assertIn('source_local_assignment_unknown',page)
        self.assertIn('water-reporting',page)
        self.assertIn('not place',page)

    def test_generated_bundle_and_shapes_are_linked_without_copying_source_nulls(self):
        from scripts import site_water_reporting
        from scripts.water_reporting import DEFAULT
        packet=load_json(DEFAULT/'water-reporting.json');data=load_atlas(ROOT/'data/releases/v0.2.0')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            site_water_reporting.generate(root,packet,DEFAULT,data,pilot=True)
            overview=(root/'water-reporting/index.md').read_text()
            self.assertIn('734',overview);self.assertIn('279',overview)
            self.assertTrue((root/'water-reporting/v0.1.0/snapshot.zip').exists())
            row=next(r for r in packet['programs'] if (r['building_type'],r['template'])==('MediumOffice','90.1-2013'))
            sid=row['reporting_schedule_id']
            shape=load_json(root/f'releases/v0.2.0/records/{sid}.json')['record']
            self.assertEqual(shape,next(s for s in packet['schedules'] if s['id']==sid))


if __name__=='__main__':unittest.main()
