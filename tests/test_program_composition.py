import unittest
from scripts.program_composition import mix_schedule, represented_weights, recipe_groups
from scripts.semantics import profile


def schedule(value):
    return {'id':str(value),'schedule_type':'fraction','units':'1','rules':[
        {'day_types':'Default','start_date':'2000-01-01','end_date':'2000-12-31','values':[value]}]}


class CompositionTests(unittest.TestCase):
    def test_complete_matrix_build_retains_recipe_provenance_and_stripmall_weights(self):
        from scripts.definition_contract import load_context
        from scripts.program_definitions import build_programs
        from scripts.program_composition import extract_areas, compose
        context=load_context(scope='full')
        areas=extract_areas(context)
        self.assertEqual(len(areas),83)
        bundle=compose(context,build_programs(context))
        recipes=[r for r in bundle['compositions'] if r['building_type']=='RetailStripmall' and r['template']=='90.1-2019']
        self.assertTrue(recipes)
        self.assertEqual(sorted(round(m['weight'],8) for m in recipes[0]['members']),[.25,.25,.5])
        self.assertTrue(all('basement' not in r['name'].lower() and 'attic' not in r['name'].lower() for r in bundle['compositions']))

    def test_load_trajectory_is_not_independently_averaged(self):
        mixed=mix_schedule([schedule(.2),schedule(.8)],[.25,.75],[10,20],17.5)
        self.assertAlmostEqual(profile(mixed['rules'],'Mon','02-29')[0]*17.5,12.5)

    def test_design_day_and_rule_override_are_preserved(self):
        a=schedule(.2);a['rules'].append({'day_types':'SmrDsn','start_date':'2000-01-01','end_date':'2000-12-31','values':[1]})
        mixed=mix_schedule([a,schedule(.4)],[.5,.5])
        self.assertAlmostEqual(profile(mixed['rules'],'SmrDsn','07-01')[0],.7)
        self.assertAlmostEqual(profile(mixed['rules'],'Mon','07-01')[0],.3)

    def test_individual_weekday_wins_after_seasonal_aggregate(self):
        a=schedule(.2)
        a['rules'] += [
            {'day_types':'Wkdy','start_date':'2000-11-01','end_date':'2000-03-01','values':[.6]},
            {'day_types':'Mon','start_date':'2000-01-01','end_date':'2000-12-31','values':[1]}]
        mixed=mix_schedule([a,schedule(.4)],[.5,.5])
        for date in ('01-15','02-29','07-01','12-01'):
            for day in ('Mon','Tue','Sat','SmrDsn'):
                self.assertAlmostEqual(profile(mixed['rules'],day,date)[0],
                    .5*profile(a['rules'],day,date)[0]+.2)

    def test_required_unknown_cannot_be_averaged_away(self):
        self.assertIsNone(mix_schedule([schedule(.2),None],[.5,.5]))

    def test_excluded_attic_basement_do_not_enter_denominator(self):
        rows=[{'program_id':'a','source_space_type':'Office','represented_area_m2':25,'area_status':'derived'},
              {'program_id':'b','source_space_type':'WholeBuilding - Lg Office-basement','represented_area_m2':75,'area_status':'derived'}]
        self.assertEqual(represented_weights(rows),{'a':1})

    def test_approved_special_groups(self):
        groups=recipe_groups('SecondarySchool',['ComputerRoom','Gym','Library','Auditorium','Gym - audience'])
        self.assertIn('Auditorium',groups['departments']['Activity_Mixed_SecondarySchool'])
        self.assertFalse(recipe_groups('FullServiceRestaurant',['Dining','Kitchen'])['departments'])


if __name__=='__main__':unittest.main()
