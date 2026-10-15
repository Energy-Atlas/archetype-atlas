"""Pure native-getter memo ownership and unchanged real public transforms."""
import copy
from fractions import Fraction
import math
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from atlas_schedules.commercial import parametric as kernel
from atlas_schedules.canonical import canonical
from atlas_schedules.errors import GeneratorError
from scripts.schedule_generator_reference import load_commercial_reference


class CommercialNativeCache(unittest.TestCase):
    def test_complete_numeric_key_retains_order_type_bits_and_steps(self):
        key=kernel._native_getter_key
        base=key([[1.0,0.0],[24.0,1.0]],6)
        for points,steps in (([[1.0,-0.0],[24.0,1.0]],6),([[1,0.0],[24.0,1.0]],6),
                             ([[24.0,1.0],[1.0,0.0]],6),([[1.0,0.0],[24.0,1.0]],6.0),
                             ([[1.0,0.0],[24.0,1.0]],True),([[1.0,0.0],[24.0,1.0]],4)):
            self.assertNotEqual(base,key(points,steps))
        nan1=struct.unpack('>d',bytes.fromhex('7ff8000000000001'))[0]
        nan2=struct.unpack('>d',bytes.fromhex('7ff8000000000002'))[0]
        self.assertNotEqual(key([[24.,nan1]],6),key([[24.,nan2]],6))
        with self.assertRaises(TypeError):key([[24.,Fraction(1,2)]],6)

    def test_only_successes_cache_and_unsupported_types_use_original_getter(self):
        cache={};original=kernel._hourly
        for points in ([[0.,0.],[24.,1.]],[[float('nan'),1.]],[[float('inf'),1.]],[[24.,float('inf')]]):
            def outcome(fn):
                try:return ('ok',fn())
                except Exception as e:return (type(e).__name__,str(e))
            want=outcome(lambda:original(points,6))
            self.assertNotEqual(want[0],'ok')
            for _ in range(2):self.assertEqual(outcome(lambda:kernel._memo_native_day(points,6,cache)),want)
            self.assertEqual(cache,{})
        class FloatSubclass(float):pass
        with patch.object(kernel,'_hourly',wraps=original) as count:
            for _ in range(2):self.assertEqual(kernel._memo_native_day([[24.,FloatSubclass(.5)]],6,cache),original([[24.,.5]],6))
            self.assertEqual(count.call_count,2);self.assertEqual(cache,{})
        points=[[24.,.5]]
        with patch.object(kernel,'_hourly',wraps=original) as count:
            self.assertEqual(kernel._memo_native_day(points,6,cache),original(points,6))
            kernel._memo_native_day(points,6,cache)
            self.assertEqual(count.call_count,1);self.assertEqual(len(cache),1)

    def test_direct_supported_getter_edge_math_is_unchanged(self):
        cases=[([[24.,.5]],6),([[float(i+1),i/24] for i in range(24)],6),
               ([[7.,0.],[18.,1.],[24.,0.]],6),([[7.13,.123456789],[18.2,1.],[24.,0.]],6),
               ([[.1166666666667,.2],[24.,.8]],6),([[24.,kernel._stored(.231*.123456789)]],6),
               ([[24.,-0.]],6),([[24,1]],6),([[24.,1.]],4)]
        for points,steps in cases:
            with self.subTest(points=points,steps=steps):
                self.assertEqual(kernel._memo_native_day(points,steps,{}),kernel._hourly(points,steps))

    def test_all365_points_in_source_order_per_slot_and_independent_flat_outputs(self):
        raw=[.5]*8760;original_points=kernel._points;original_hourly=kernel._hourly
        with (patch.object(kernel,'_points',wraps=original_points) as points,
              patch.object(kernel,'_hourly',wraps=original_hourly) as hourly):
            first=kernel._native_original(raw);second=kernel._native_original(raw)
            self.assertEqual(points.call_count,730);self.assertEqual(hourly.call_count,2)
        self.assertEqual(first,[.5]*8760);self.assertEqual(second,first)
        second[0]=.75;self.assertEqual(first[0],.5)
        varying=[float(day) for day in range(365) for _ in range(24)]
        with patch.object(kernel,'_points',wraps=original_points) as points:
            kernel._native_original(varying)
            self.assertEqual([call.args[0][0] for call in points.call_args_list],list(map(float,range(365))))

    def test_first_invalid_day_stops_before_later_points(self):
        raw=[.5]*8760;raw[24]=float('nan')
        with patch.object(kernel,'_points',wraps=kernel._points) as points:
            with self.assertRaises((GeneratorError,ValueError,OverflowError)):kernel._native_original(raw)
            self.assertEqual(points.call_count,2)


class RealCommercialNativeParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases=load_commercial_reference()['cases']
        # Raw retained preimage is an independently checked historical method,
        # never a new native/source qualification or a generated SHA oracle.
        path=Path(__file__).resolve().parents[1]/'data/schedule-generator/apartment/qualification-code/a5-r70-current-then/atlas_schedules/commercial/parametric.py'
        ns=dict(kernel.__dict__)
        exec(compile(path.read_bytes(),str(path),'exec'),ns)
        cls.original=staticmethod(ns['transform_commercial'])

    def test_real_supported_sources_public_outputs_contexts_and_nonalias(self):
        for case in self.cases:
            with self.subTest(case=case['case_id']):
                context=dict(case['source_context'],slot_sources=case['schedules'])
                channels=copy.deepcopy(case['original_channels']);operating=copy.deepcopy(case['operating'])
                before=canonical([channels,operating,context])
                original=self.original(channels,operating,context)
                actual=kernel.transform_commercial(channels,operating,context)
                self.assertEqual(canonical(actual),canonical(original))
                self.assertEqual(canonical([channels,operating,context]),before)
                slot=next(iter(actual['channels']))
                self.assertIsNot(actual['channels'][slot],original['channels'][slot])
                actual['channels'][slot][0]+=.01
                actual['source_context']['transforms'][slot]['daily_profiles'][0][0][1]+=.01
                self.assertEqual(canonical(original),canonical(self.original(channels,operating,context)))

    def test_public_all8760_finite_checks_length_and_first_error_order(self):
        case=self.cases[0];context=dict(case['source_context'],slot_sources=case['schedules'])
        slot=next(iter(context['slot_sources']))
        for index,value in ((0,-99.),(8759,-99.),(0,float('nan'))):
            channels=copy.deepcopy(case['original_channels']);channels[slot][index]=value
            outcomes=[]
            for fn in (self.original,kernel.transform_commercial):
                with self.assertRaises(GeneratorError) as caught:fn(channels,case['operating'],context)
                e=caught.exception;outcomes.append((type(e),e.code,e.path,e.message))
            self.assertEqual(*outcomes)
        for invalid in ('length','timestep'):
            channels=copy.deepcopy(case['original_channels']);ctx=copy.deepcopy(context)
            if invalid=='length':channels[slot].pop()
            else:ctx['steps_per_hour']=True
            outcomes=[]
            for fn in (self.original,kernel.transform_commercial):
                with self.assertRaises(GeneratorError) as caught:fn(channels,case['operating'],ctx)
                e=caught.exception;outcomes.append((type(e),e.code,e.path,e.message))
            self.assertEqual(*outcomes)


if __name__=='__main__':unittest.main()
