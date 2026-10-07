import unittest
from scripts.definition_contract import load_context
from scripts.residential_definitions import build_residential


class ResidentialDefinitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context=load_context(scope='full');cls.bundle=build_residential(cls.context)

    def test_whole_dwelling_requires_no_room_area_mixture(self):
        self.assertEqual(len(self.bundle['programs']),41)
        for row in self.bundle['programs']:
            self.assertEqual(row['gate'],['residential'])
            self.assertEqual(row['scope'],'whole_dwelling')
            occupancy=next(l for l in row['loads'] if l['quantity']=='occupancy')
            self.assertEqual(occupancy['basis'],'dwelling_unit')
            self.assertEqual(occupancy['required_inputs'],['dwelling_unit_count'])
            self.assertIsNotNone(occupancy['value'])
            self.assertTrue(any(l['value'] is None for l in row['loads']))
            if occupancy['value']>0:
                self.assertTrue(any(l['value'] is None and l['schedule_id'] for l in row['loads']))

    def test_profiles_are_existing_determined_realizations(self):
        for schedule in self.bundle['schedules']:
            self.assertEqual(len(schedule['annual_values']),8760)
            self.assertEqual(schedule['calendar']['year'],2007)
            self.assertIn('seed',schedule['calendar'])
            self.assertNotIn('generator_arguments',schedule)
        self.assertTrue(all(r['unresolved_options'] for r in self.bundle['programs']))

    def test_pressure_test_and_ratings_remain_distinct(self):
        row=self.bundle['constructions'][0]
        self.assertEqual(row['air_exchange']['pressure_test']['reference_pressure']['value'],50)
        self.assertIsNone(row['air_exchange']['infiltration']['value'])
        self.assertEqual(row['layers'],[])
        metrics={m['metric'] for c in self.bundle['components'] for m in c.get('ratings',[])}
        self.assertIn('AFUE',metrics);self.assertIn('SEER2',metrics)
        self.assertNotIn('COP',metrics)

    def test_evidence_and_schedule_references_are_closed(self):
        evidence={e['id'] for e in self.bundle['provenance']}
        schedules={s['id'] for s in self.bundle['schedules']}
        for row in self.bundle['programs']:
            for load in row['loads']:
                self.assertIn(load['evidence_id'],evidence)
                if load['schedule_id']:self.assertIn(load['schedule_id'],schedules)


if __name__=='__main__':unittest.main()
