"""Bounded R70 transition rejects changed historical and current identities."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from atlas_schedules.errors import GeneratorError
from scripts import schedule_generator_runtime_cut as cut


class RuntimeCut(unittest.TestCase):
    def setUp(self):
        self.covering=cut._read(cut.ROOT,cut.CUT)
        self.lock=cut._read(cut.ROOT,cut.LOCK)
        self.retention=cut._read(cut.ROOT,cut.THEN+'retention.json')

    def check(self,**kwargs):return cut.verify_r70_transition(**kwargs)

    def test_complete_current_and_historical_cut(self):
        result=self.check()
        self.assertTrue(result['passed'])
        self.assertEqual(result['historical_code_count'],63)
        self.assertEqual(result['historical_evidence_count'],53)
        self.assertEqual(result['current_code_count'],67)

    def test_missing_duplicate_foreign_or_stale_current_dependency_rejected(self):
        for mutation in ('missing','duplicate','foreign','stale'):
            lock=copy.deepcopy(self.lock)
            if mutation=='missing':lock['current_dependencies'].pop()
            elif mutation=='duplicate':lock['current_dependencies'].append(copy.deepcopy(lock['current_dependencies'][0]))
            elif mutation=='foreign':lock['current_dependencies'][-1]['source_path']='tests/foreign.py'
            else:
                old=cut._read(cut.ROOT,cut.ANCHORS[0]['source_path'])
                row=next(r for r in old['current_dependencies'] if r['source_path']=='atlas_schedules/service_graph.py')
                index=next(i for i,r in enumerate(lock['current_dependencies']) if r['source_path']==row['source_path'])
                lock['current_dependencies'][index]=row
            with self.subTest(mutation=mutation),self.assertRaises(GeneratorError):self.check(lock=lock)

    def test_missing_duplicate_foreign_or_rebound_historical_edge_rejected(self):
        for mutation in ('missing','duplicate','foreign','rebound'):
            retained=copy.deepcopy(self.retention);edges=retained['historical_edges']
            if mutation=='missing':edges.pop()
            elif mutation=='duplicate':edges.append(copy.deepcopy(edges[0]))
            elif mutation=='foreign':edges[0]['original_path']='foreign.py'
            else:
                # A changed current file may never stand in for its old native or
                # code qualification, even when both declarations are rewritten.
                edge=next(r for r in edges if r['original_path']=='atlas_schedules/service_graph.py')
                new=next(r for r in self.lock['current_dependencies'] if r['source_path']==edge['original_path'])
                edge.update(sha256=new['sha256'],size_bytes=new['size_bytes'],resolved_path=new['source_path'])
            with self.subTest(mutation=mutation),self.assertRaises(GeneratorError):self.check(retention=retained)

    def test_changed_historical_bytes_rejected_with_real_local_file(self):
        # Copy the complete bounded closure into an isolated test directory;
        # mutate its actual historical file rather than mocking the hash checker.
        paths={a['source_path'] for a in cut.ANCHORS}
        paths.update(r['historical_path'] for k in ('current_then_code','current_then_evidence','snapshots') for r in self.retention[k])
        paths.update(r['source_path'] for r in self.retention['historical_documents'])
        paths.update(r['resolved_path'] for r in self.retention['historical_edges'] if r['resolved_path'])
        paths.add(cut.THEN+'retention.json')
        paths.add(self.retention['historical_unavailability']['source_path'])
        paths.update(cut.UNAVAILABLE_RECORD[k]['source_path'] for k in ('document','transition','amended_test'))
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for path in paths:
                destination=root/path;destination.parent.mkdir(parents=True,exist_ok=True)
                destination.write_bytes((cut.ROOT/path).read_bytes())
            cut.verify_r70_retention(root)
            path=root/(cut.BASE+'qualification-code/a5-r70-current-then/atlas_schedules/service_graph.py')
            path.write_bytes(path.read_bytes()+b'\n')
            with self.assertRaises(GeneratorError):cut.verify_r70_retention(root)

    def test_only_exact_unknown_test_edge_is_an_availability_limit(self):
        result=self.check()
        self.assertEqual((result['historical_edges_verified'],result['historical_edges_unavailable']),(1600,1))
        for field,value in (('locator','/current_dependencies/51'),('sha256','f'*64),
                            ('size_bytes',22942),('original_path','tests/other.py'),
                            ('resolved_path','tests/test_schedule_generator_apartment_family.py')):
            retained=copy.deepcopy(self.retention)
            edge=next(r for r in retained['historical_edges'] if r['resolved_path'] is None)
            edge[field]=value
            with self.subTest(field=field),self.assertRaises(GeneratorError):self.check(retention=retained)
        for category in ('atlas_schedules/','capture','sources/'):
            retained=copy.deepcopy(self.retention)
            edge=next(r for r in retained['historical_edges'] if category in r['original_path'] and r['resolved_path'])
            edge['resolved_path']=None
            with self.subTest(category=category),self.assertRaises(GeneratorError):self.check(retention=retained)

    def test_availability_record_metadata_status_and_transition_are_exact(self):
        # Supply decoded mutations at the read boundary: even with the actual
        # pinned file unchanged, the semantic guard must reject each exception.
        from unittest.mock import patch
        record_path=self.retention['historical_unavailability']['source_path']
        original_read=cut._read
        for field,value in (('status','verified'),('resolved_path','tests/current.py'),
                            ('reason','unavailable other test'),('schema_version','2.0.0')):
            record=copy.deepcopy(cut.UNAVAILABLE_RECORD);record[field]=value
            # The read boundary supplies only this decoded test mutation; every
            # source identity and all other actual files still use the real checker.
            def read(root,path):return record if path==record_path else original_read(root,path)
            with self.subTest(field=field),patch.object(cut,'_read',side_effect=read),self.assertRaises(GeneratorError):
                self.check()
        record=copy.deepcopy(cut.UNAVAILABLE_RECORD);record['transition']['sha256']='0'*64
        with patch.object(cut,'_read',side_effect=lambda root,path:record if path==record_path else original_read(root,path)):
            with self.assertRaises(GeneratorError):self.check()

    def test_unknown_edge_numeric_metadata_type_is_exact(self):
        retained=copy.deepcopy(self.retention)
        edge=next(r for r in retained['historical_edges'] if r['resolved_path'] is None)
        edge['size_bytes']=22941.0
        with self.assertRaises(GeneratorError):cut.verify_r70_retention(retention=retained)

    def test_changed_old_evidence_missing_covering_evidence_and_wrong_cut_rejected(self):
        covering=copy.deepcopy(self.covering);covering['required_evidence'].pop()
        with self.assertRaises(GeneratorError):self.check(cut=covering)
        covering=copy.deepcopy(self.covering);covering['runtime_changes'].pop()
        with self.assertRaises(GeneratorError):self.check(cut=covering)
        lock=copy.deepcopy(self.lock);lock['verification_evidence'][0]['sha256']='0'*64
        with self.assertRaises(GeneratorError):self.check(lock=lock)


if __name__=='__main__':unittest.main()
