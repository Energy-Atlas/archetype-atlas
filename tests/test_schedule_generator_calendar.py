"""Selected frozen source rule objects and independently captured OpenStudio values."""
import copy
import json
from pathlib import Path
import unittest
from atlas_schedules.errors import GeneratorError
try:
    from atlas_schedules.calendar import evaluate_rules
except ImportError:
    evaluate_rules = None

class CalendarTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(evaluate_rules, 'source calendar implementation is missing')
    def source(self,key='schedule-0527ef8d69f949a5b342669e'):
        return json.loads(Path('atlas_schedules/data/reference/'+key+'.json').read_bytes())['definition']

    def test_non_leap_hourly_calendar(self):
        source=self.source()
        self.assertEqual(evaluate_rules(source,2007,[])['values'],[0]*8760)
        for year in [2008,True,0,10000,'2007']:
            with self.subTest(year=year),self.assertRaises(GeneratorError):evaluate_rules(source,year,[])
        for dates in [['2008-01-01'],['2007-02-29'],['01-01'],[None],['2007-01-01','2007-01-01']]:
            with self.subTest(dates=dates),self.assertRaises(GeneratorError):evaluate_rules(source,2007,dates)

    def test_only_source_required_special_profiles(self):
        self.assertNotIn('special_profiles',evaluate_rules(self.source(),2007,[]))
        source=self.source('schedule-4082e09c5f9727640add')
        result=evaluate_rules(source,2007,[])
        self.assertEqual(set(result['special_profiles']),{'SmrDsn','WntrDsn'})
        self.assertNotIn('Hol',result['special_profiles'])
        self.assertNotEqual(result['values'][:24], result['special_profiles']['SmrDsn'])

    def test_selected_source_rule_vectors(self):
        fixture=json.loads(Path('data/schedule-generator/reference-vectors.json').read_bytes())
        for vector in fixture['rule_vectors']:
            with self.subTest(schedule=vector['schedule_id']):
                source=self.source(vector['schedule_id']);before=copy.deepcopy(source)
                result=evaluate_rules(source,vector['year'],vector['holidays'])
                for i,(a,b) in enumerate(zip(result['values'],vector['values'])):
                    self.assertAlmostEqual(a,b,delta=1e-8,msg=str(i))
                self.assertEqual(result.get('special_profiles',{}),vector['special_profiles'])
                if vector['holidays']:
                    self.assertEqual(result['values'][:24],vector['default_profile'])
                self.assertEqual(source,before)

    def test_source_order_and_dates(self):
        # An actual selected rule repeated with a shorter active period tests last-created precedence.
        source=self.source('schedule-db120b43964b8b666cd8')
        rule=copy.deepcopy(source['rules'][-2]);rule.update(start_date='2014-12-30',end_date='2014-01-02',values=[0.4]*24)
        source['rules'].append(rule)
        result=evaluate_rules(source,2007,[])
        self.assertEqual(result['values'][:48],[0.4]*48)
        self.assertEqual(result['values'][-24:],[0.4]*24)
        self.assertNotEqual(result['values'][48:72],[0.4]*24)

    def test_explicit_holidays_select_default_only_without_source_holiday_profile(self):
        source=self.source('schedule-db120b43964b8b666cd8')
        result=evaluate_rules(source,2007,['2007-01-01'])
        default=next(r['values'] for r in source['rules'] if r['day_types']=='Default')
        self.assertEqual(result['values'][:24],default)

    def test_unsupported_or_unknown_inputs_fail_closed(self):
        source=self.source()
        for updates in [{'time_resolution_minutes':30},{'rules':[]},{'interpolation':'Linear'},{'rules':[dict(source['rules'][0],day_types='Hol')]}]:
            with self.assertRaises(GeneratorError):evaluate_rules(dict(source,**updates),2007,[])
        for rule in [{'values':[None]},{'values':[float('nan')]},{'values':[0,1]},{'day_types':'MadeUp'},{'start_date':'garbage'}]:
            bad=copy.deepcopy(source);bad['rules'][0].update(rule)
            with self.subTest(rule=rule),self.assertRaises(GeneratorError):evaluate_rules(bad,2007,[])
