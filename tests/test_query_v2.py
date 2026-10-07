import tempfile
import unittest
from pathlib import Path
from scripts.definition_contract import DefinitionBundle, parameter
from scripts.query_v2 import QueryClient, generate_delivery


class QueryTests(unittest.TestCase):
    def test_projection_filter_lazy_fetch_and_checksum(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'delivery'
            bundle=DefinitionBundle(schema_version='1.0.0')
            bundle['programs']=[{'id':'p','kind':'program','name':'Office','template':'90.1-2019',
                'building_type':'MediumOffice','source_family':'code_prototype_rules',
                'gate':['nonresidential'],'evidence_view':'source','derivation':'normalized',
                'detail':'SourcePrograms','available_details':['SourcePrograms','GeneralMix'],
                'parameters':{},'loads':[],'evidence_ids':['e'],'required_inputs':[]}]
            bundle['provenance']=[{'id':'e','locator':'source'}]
            generate_delivery(bundle,path)
            client=QueryClient(path)
            result=client.query('program',{'building_type':'MediumOffice'},['name'])
            self.assertEqual(result['records'][0]['fields'],{'name':'Office'})
            self.assertEqual(client.query('program',{'detail':'GeneralMix'},['name'])['match_count'],1)
            self.assertEqual(client.query('program',{'template':'not-present'},['name'])['records'],[])
            with self.assertRaises(ValueError):client.query('program',{'madeup':1},['name'])
            with self.assertRaises(ValueError):client.query('program',{},['madeup'])
            self.assertEqual(client.resource('e')['record']['locator'],'source')
            latest=path/'latest.json'; import json
            manifest=json.loads(latest.read_text())['manifest']; (path/manifest['href']).write_bytes(b'bad')
            with self.assertRaises(ValueError):QueryClient(path)


if __name__=='__main__': unittest.main()
