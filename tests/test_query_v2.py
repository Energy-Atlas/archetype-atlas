import tempfile
import unittest
from pathlib import Path
from scripts.definition_contract import DefinitionBundle, parameter, record
from scripts.query_v2 import QueryClient, generate_delivery


class QueryTests(unittest.TestCase):
    def test_construction_only_update_reuses_program_and_supporting_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'delivery';bundle=DefinitionBundle()
            source={'building_type':'MediumOffice','template':'90.1-2019'}
            program=record('program',dict(source,id='p'),'Office');program['air_exchange']={'unchanged':True}
            old=record('construction',dict(source,id='old'),'Partial room');old['scope']='space_type'
            bundle['programs']=[program];bundle['constructions']=[old]
            before=generate_delivery(bundle,path);before_bytes={f.relative_to(path).as_posix():f.read_bytes() for f in path.rglob('*') if f.is_file()}
            revised=record('construction',dict(source,id='new'),'Whole building');revised['scope']='building'
            bundle['constructions']=[revised]
            after=generate_delivery(bundle,path,only_kind='construction')
            self.assertEqual(before['record_types']['program'],after['record_types']['program'])
            self.assertEqual(before['record_types']['hvac_system'],after['record_types']['hvac_system'])
            self.assertEqual(before['supporting_tables'],after['supporting_tables'])
            for name,data in before_bytes.items():
                if name!='latest.json':self.assertEqual((path/name).read_bytes(),data)
            client=QueryClient(path)
            self.assertEqual([x['id'] for x in client.query('construction',{},['name'])['records']],[revised['id']])
            self.assertEqual(client.query('program',{},['name'])['match_count'],1)

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
