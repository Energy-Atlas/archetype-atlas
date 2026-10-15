"""Guard-preserving numeric validation: unchanged truth table and bounded work."""
import sys
import unittest

from atlas_schedules import contract
from atlas_schedules.errors import GeneratorError
from tests import schedule_generator_validation_oracle as old


def outcome(module,value,schema=None):
    try:
        module._finite(value,'/samples')
        if schema is not None:module._check_schema(value,schema,schema,'/samples')
    except GeneratorError as error:return error.code,error.path,error.message
    return None


class NumericValidationTests(unittest.TestCase):
    def test_valid_hourly_numeric_array_does_not_recurse_for_every_scalar(self):
        values=[0.25,1,-0.0,1e300]*2190
        counts={contract._check_schema.__code__:0,contract._finite.__code__:0}
        def observe(frame,event,arg):
            if event=='call' and frame.f_code in counts:counts[frame.f_code]+=1
        previous=sys.getprofile()
        try:
            sys.setprofile(observe)
            self.assertIsNone(outcome(contract,values,{'type':'array','minItems':8760,'maxItems':8760,'items':{'type':'number'}}))
        finally:sys.setprofile(previous)
        self.assertEqual(counts[contract._check_schema.__code__],1)
        self.assertEqual(counts[contract._finite.__code__],1)

    def test_numeric_and_json_scalar_errors_match_original_checker(self):
        class FloatChild(float):pass
        class IntChild(int):pass
        class ListChild(list):pass
        items=[0,1,-1,0.0,-0.0,1e308,-1e308,10**5000,True,False,None,'1',{},[],
               float('nan'),float('inf'),-float('inf'),FloatChild(1),IntChild(1),ListChild([1]),object()]
        schema={'type':'array','minItems':3,'maxItems':3,'items':{'type':'number'}}
        for number,item in enumerate(items):
            for index in range(3):
                value=[0,1.0,2];value[index]=item
                with self.subTest(number=number,index=index):
                    self.assertEqual(outcome(contract,value,schema),outcome(old,value,schema))
        for value in ([],[1],[1,2,3,4],[[1]],{'nested':[1,float('nan')]},['bad',float('inf')],
                      [None,'bad'],[True,10**5000],[{1:'bad'},float('nan')]):
            self.assertEqual(outcome(contract,value,schema),outcome(old,value,schema))

    def test_error_paths_precedence_and_bool_rejection_remain_public(self):
        schema={'type':'array','items':{'type':'number'}}
        cases=[([1,True],('invalid_contract','/samples/1','Incorrect value type')),
               (['bad',float('nan')],('invalid_json','/samples/1','Nonfinite number')),
               ([10**5000],('invalid_contract','/samples/0','Incorrect value type')),
               ([{'x':float('inf')}],('invalid_json','/samples/0/x','Nonfinite number')),
               ([{1:'value'}],('invalid_json','/samples/0','JSON object keys must be strings'))]
        for value,expected in cases:self.assertEqual(outcome(contract,value,schema),expected)
        self.assertIsNone(outcome(contract,[None,True,False,'json',10**5000]))

    def test_enriched_item_schemas_and_array_guards_use_original_semantics(self):
        schemas=[{'type':'number','minimum':0,'maximum':1}, {'type':'number','const':1},
                 {'type':'number','enum':[0,1]}, {'oneOf':[{'type':'number'},{'type':'null'}]},
                 {'$ref':'#/$defs/value'}, {'type':['number','null']}, {'type':'integer'},
                 {'type':'number','unrecognized':True}]
        for number,item in enumerate(schemas):
            schema={'type':'array','minItems':2,'maxItems':3,'uniqueItems':True,'items':item,
                    '$defs':{'value':{'type':'number','minimum':1}}}
            for value in ([0,1],[0,0],[1,2],[1,None],[True,1],[-1,1],[1],[0,1,2,3]):
                with self.subTest(schema=number,value=value):
                    self.assertEqual(outcome(contract,value,schema),outcome(old,value,schema))

    def test_nested_json_shape_and_exact_types_preserve_original_errors(self):
        values=[{'a':[1,{'b':[True,None,'text',1.0]}]},[[1,2],[3,4]],
                [1,{'a':object()}],[1,{'a':[float('nan')]}],[1,{'a':(1,2)}]]
        for value in values:self.assertEqual(outcome(contract,value),outcome(old,value))


if __name__=='__main__':unittest.main()
