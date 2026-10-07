import unittest
from scripts.definition_contract import load_context
from scripts.definitions import build
from scripts.definition_validate import validate


class FullDefinitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context=load_context(scope='full');cls.bundle=build(cls.context)

    def test_all_source_rows_have_explicit_coverage(self):
        covered={r['source_id'] for r in self.bundle['coverage']}
        for table in ('programs','systems','envelope_components'):
            self.assertTrue({r['id'] for r in self.context.atlas[table]}<=covered)
        self.assertFalse(any(r['status']=='unsupported' for r in self.bundle['coverage']))

    def test_hospital_air_and_hotel_ptac_are_retained(self):
        hospital=[r for r in self.bundle['constructions'] if r['building_type']=='Hospital']
        self.assertTrue(any(a['category']=='total_supply' for r in hospital for a in r.get('air_exchange',[])))
        outpatient=[r for r in self.bundle['constructions'] if r['building_type']=='Outpatient']
        self.assertTrue(any(a['category']=='total_supply' and a['value'] and a['value']>0
                            for r in outpatient for a in r.get('air_exchange',[])))
        self.assertTrue(any(r['system_type']=='PTAC' and r['building_type']=='SmallHotel' for r in self.bundle['hvac_systems']))
        self.assertFalse(any(r.get('representation')=='ancillary_equipment' for r in self.bundle['hvac_systems']))

    def test_source_flags_do_not_move_hospital_and_hotel_to_residential(self):
        for row in self.bundle['programs']:
            if row['building_type'] in {'Hospital','SmallHotel','LargeHotel'}:
                self.assertEqual(row['gate'],['nonresidential'])
        self.assertTrue(any(r['gate']==['residential'] and r['building_type']=='MidriseApartment' for r in self.bundle['programs']))

    def test_full_graph_validates(self):
        self.assertEqual(validate(self.bundle).errors,[])


if __name__=='__main__':unittest.main()
