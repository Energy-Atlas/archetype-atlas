"""Build-only R70 predecessor/transition verification, never qualification.

This checker is deliberately specific to the reviewed R64 -> R70 transition.
It does not confer authority on later runtime edits or update any lock.
"""
import hashlib
import json
from pathlib import Path

from atlas_schedules.canonical import canonical
from atlas_schedules.errors import GeneratorError
from atlas_schedules.resources import safe_path
from scripts.common import ROOT

BASE='data/schedule-generator/apartment/'
THEN=BASE+'evidence/a5-r70-current-then/'
CUT=BASE+'evidence/a5-r70/code-cut.json'
LOCK='sources/schedule-generator-apartment-authority-lock.json'
# The R70-activated lock, retained when the Retail/Office S1 transition moved the
# live lock on. Every check of a file changed after R70 reads its retained copy.
R70_LOCK=BASE+'evidence/ro-s1-current-then/authority-lock.json'
LATER_RETAINED={p:BASE+'qualification-code/ro-s1-current-then/'+p for p in (
    'atlas_schedules/commercial/parametric.py','atlas_schedules/commercial/source_models.py',
    'scripts/schedule_generator_runtime_cut.py','tests/test_schedule_generator_runtime_cut.py')}
# Historical edges R70 resolved to live files that later commits moved on
# (coverage drafts settled in 8d5619a; v0.8.0 release docs); their exact
# R70-era bytes are retained here and still checked by hash.
LATER_RETAINED.update({
    'scripts/schedule_generator_coverage.py':BASE+'qualification-code/a5-r67-current-then/scripts/schedule_generator_coverage.py',
    'docs/schedule-generator.md':BASE+'qualification-code/ro-s1-current-then/docs/schedule-generator.md'})
CHANGED={'atlas_schedules/service_graph.py','atlas_schedules/commercial/parametric.py'}
ADDED={'scripts/schedule_generator_runtime_cut.py',
       'tests/test_schedule_generator_runtime_workspaces.py',
       'tests/test_schedule_generator_commercial_native_cache.py',
       'tests/test_schedule_generator_runtime_cut.py'}
ANCHORS=[
    {'source_path':THEN+'authority-lock.json','sha256':'2c9eda30fcbea0f49c004cd7e8b3dced51b2deded893bf05fe2ea716b0c90be5','size_bytes':24989},
    {'source_path':THEN+'code-cut.json','sha256':'2dfe52e1a2e96dc3be1838a7f0decad58b80b2643e90739d97879c86d67b2bfb','size_bytes':9711},
    {'source_path':THEN+'r67-external-code-cut.json','sha256':'26b6fb168e51a62ffa72f29238db4675120239c766df74feadf3d037de546ae2','size_bytes':4504}]
HISTORICAL_EXTRA=[{'sha256': '6165bfbfbec59caa59d09e2c754c3d7a7e29e305f7053331165cc32c5bd51f87', 'size_bytes': 10108, 'source_path': 'data/schedule-generator/apartment/evidence/a3-reviewed-lock.json'}, {'sha256': '2c9eda30fcbea0f49c004cd7e8b3dced51b2deded893bf05fe2ea716b0c90be5', 'size_bytes': 24989, 'source_path': 'data/schedule-generator/apartment/evidence/a5-r67-current-then/authority-lock.json'}, {'sha256': '2dfe52e1a2e96dc3be1838a7f0decad58b80b2643e90739d97879c86d67b2bfb', 'size_bytes': 9711, 'source_path': 'data/schedule-generator/apartment/evidence/a5-r67-current-then/code-cut.json'}, {'sha256': '9ec2fc891c55c0592458215e4c1eb6530d4f3464a8d10667df0ee442827e83b3', 'size_bytes': 27372, 'source_path': 'data/schedule-generator/apartment/evidence/a5-r67-current-then/retention.json'}, {'sha256': '26b6fb168e51a62ffa72f29238db4675120239c766df74feadf3d037de546ae2', 'size_bytes': 4504, 'source_path': 'data/schedule-generator/apartment/evidence/a5-r67/code-cut.json'}, {'sha256': '98a558d3c35b73b986fe9901dd9c3e699cca24a42fe24fa7106e2b746287de1a', 'size_bytes': 15688, 'source_path': 'data/schedule-generator/apartment/evidence/authority-retention.json'}, {'sha256': '6165bfbfbec59caa59d09e2c754c3d7a7e29e305f7053331165cc32c5bd51f87', 'size_bytes': 10108, 'source_path': 'sources/schedule-generator-apartment-fixed-reference-lock.json'}]
EVIDENCE_NAMES={'method-parity.json','focused-results.json','compatibility-results.json','historical-unavailability.json'}
UNAVAILABLE_EDGE={
    'document':BASE+'evidence/a4-current/covering-code-cut.json',
    'locator':'/current_dependencies/52',
    'original_path':'tests/test_schedule_generator_apartment_family.py',
    'resolved_path':None,
    'sha256':'8c8af9a1245cc6d6cb0c2d4338e3d4218de346e7ec59433e95edb8fe16b829be',
    'size_bytes':22941}
UNAVAILABLE_RECORD={
    'schema_version':'1.0.0','status':'unknown','resolved_path':None,
    'edge':UNAVAILABLE_EDGE,
    'document':{'source_path':UNAVAILABLE_EDGE['document'],
                'sha256':'3c60b021e431640a5ce18cf725a2326e6a533648f9b163d86a3b6b0e5f5d5fcd','size_bytes':9396},
    'transition':{'source_path':BASE+'evidence/a4-current/test-coverage-transition.json',
                  'sha256':'49943fceee6fd3c3406c68fe0223a6bdfbe3e66e5cecab24e5349695dc3b456f','size_bytes':770},
    'amended_test':{'source_path':BASE+'qualification-code/a4-e160/tests/test_schedule_generator_apartment_family.py',
                    'sha256':'86c0846cdd8b64e420954fa47f8213f2c270a8168d5b0aedfb99f86dd5053b20','size_bytes':25051},
    'reason':'Original intermediate test-only bytes unavailable after bounded filesystem/Git/retained-diff search; later amended coverage does not recreate or certify the missing old test body.',
    'interpretation':'R71 archival availability limit only. Exactly 1600 historical edges verified and one unavailable; no full old 95-test-source reproducibility or whole historical closure claim. All current, scientific, runtime, native and other historical edges remain mandatory.'}


def _fail(path,message):raise GeneratorError('source_integrity',path,message)


def _read(root,path):return json.loads((root/str(safe_path(path))).read_bytes())


def _check(root,row,path_key='source_path'):
    path=str(safe_path(row[path_key]))
    blob=(root/LATER_RETAINED.get(path,path)).read_bytes()
    if hashlib.sha256(blob).hexdigest()!=row['sha256'] or len(blob)!=row['size_bytes']:
        _fail(path,'Exact R70 current or historical bytes differ')


def _rows(rows):
    result={}
    for row in rows:
        if set(row)!={'source_path','sha256','size_bytes'}:_fail('/cut','Unexpected identity fields')
        path=str(safe_path(row['source_path']))
        if path in result:_fail(path,'Duplicate cut path')
        result[path]=row
    return result


def _edges(value,document,locator=''):
    result=[]
    if isinstance(value,dict):
        if isinstance(value.get('sha256'),str) and len(value['sha256'])==64 and type(value.get('size_bytes')) is int:
            original=next((value[k] for k in ('retained_path','source_path','path') if isinstance(value.get(k),str)),None)
            if original:
                result.append(dict(document=document,locator=locator,original_path=original,
                                   sha256=value['sha256'],size_bytes=value['size_bytes']))
        for k,v in value.items():result.extend(_edges(v,document,locator+'/'+str(k)))
    elif isinstance(value,list):
        for i,v in enumerate(value):result.extend(_edges(v,document,locator+'/'+str(i)))
    return result


def verify_r70_retention(root=ROOT,retention=None):
    root=Path(root)
    for anchor in ANCHORS:_check(root,anchor)
    old=_read(root,ANCHORS[0]['source_path'])
    old_cut=_read(root,ANCHORS[1]['source_path'])
    if old_cut!={k:old[k] for k in ('current_dependencies','current_producer')}:
        _fail('/predecessor','Original R64 code cut does not equal original authority rows')
    retained=_read(root,THEN+'retention.json') if retention is None else retention
    expected_code=[]
    for row in [old['current_producer'],*old['current_dependencies']]:
        path=row['source_path']
        historical=BASE+'qualification-code/a5-r70-current-then/'+path if path in CHANGED else path
        expected_code.append(dict(current_path=path,historical_path=historical,sha256=row['sha256'],size_bytes=row['size_bytes']))
    expected_evidence=[dict(current_path=r['source_path'],historical_path=r['source_path'],sha256=r['sha256'],size_bytes=r['size_bytes']) for r in old['verification_evidence']]
    expected_snapshots=[dict(current_path=p,historical_path=a['source_path'],sha256=a['sha256'],size_bytes=a['size_bytes']) for p,a in zip((LOCK,BASE+'evidence/a5-r64/code-cut.json',BASE+'evidence/a5-r67/code-cut.json'),ANCHORS)]
    if retained['current_then_code']!=expected_code or retained['current_then_evidence']!=expected_evidence or retained['snapshots']!=expected_snapshots:
        _fail('/retention','Complete unchanged old 63-code/53-evidence/preimage table required')
    for row in expected_code+expected_evidence+expected_snapshots:_check(root,row,'historical_path')
    names={'authority-lock.json','code-cut.json','retention.json','covering-code-cut.json','final-code-cut.json','pre-json-LF-code-cut.json'}
    documents=[r for r in old['verification_evidence'] if Path(r['source_path']).name in names]
    documents=sorted(documents+HISTORICAL_EXTRA,key=lambda r:r['source_path'])
    if retained['historical_documents']!=documents:_fail('/retention/documents','Complete original historical document inventory required')
    expected=[]
    for row in documents:
        _check(root,row);expected.extend(_edges(_read(root,row['source_path']),row['source_path']))
    actual=retained['historical_edges']
    if canonical([{k:v for k,v in r.items() if k!='resolved_path'} for r in actual])!=canonical(expected):
        _fail('/retention/edges','Omitted, foreign, duplicated or rebound historical edge')
    unavailability=retained['historical_unavailability']
    if unavailability['source_path']!=BASE+'evidence/a5-r70/historical-unavailability.json':
        _fail('/retention/unavailable','Foreign archival availability record')
    _check(root,unavailability)
    record=_read(root,unavailability['source_path'])
    if canonical(record)!=canonical(UNAVAILABLE_RECORD):_fail('/retention/unavailable','Exact R71 unknown/null historical test edge required')
    for key in ('document','transition','amended_test'):_check(root,record[key])
    unavailable=0
    for row in actual:
        if canonical(row)==canonical(UNAVAILABLE_EDGE):
            unavailable+=1
        else:
            if row['resolved_path'] is None:_fail('/retention/edges','Additional unavailable historical edge')
            _check(root,row,'resolved_path')
    if unavailable!=1 or retained['historical_edge_availability']!={'verified':1600,'unavailable':1}:
        _fail('/retention/edges','Exact separately reported R71 availability counts required')
    for field,paths in (('runtime_edge_relocations',CHANGED),('authority_edge_relocations',{LOCK})):
        targets={r['historical_path']:r['current_path'] for r in expected_code+expected_snapshots if r['current_path'] in paths}
        expected_moves=[dict(document=r['document'],locator=r['locator'],
                             previous_resolved_path=targets[r['resolved_path']],resolved_path=r['resolved_path'],
                             sha256=r['sha256'],size_bytes=r['size_bytes'])
                        for r in actual if r['resolved_path'] in targets]
        if retained[field]!=expected_moves:_fail('/retention/'+field,'Complete explicit historical edge relocation table differs')
    return old,retained


def verify_r70_transition(root=ROOT,cut=None,lock=None,retention=None):
    root=Path(root);old,retained=verify_r70_retention(root,retention)
    current=_read(root,R70_LOCK) if lock is None else lock
    covering=_read(root,CUT) if cut is None else cut
    if covering['predecessors']!=ANCHORS:_fail('/cut/predecessors','Original predecessor anchors required')
    current_rows=_rows([current['current_producer'],*current['current_dependencies']])
    old_rows=_rows([old['current_producer'],*old['current_dependencies']])
    if set(current_rows)!=set(old_rows)|ADDED:_fail('/cut/current','Missing or foreign current code path')
    if current['current_producer']!=old['current_producer']:_fail('/cut/producer','Pinned producer changed')
    for path,row in current_rows.items():
        _check(root,row)
        if path in old_rows and path not in CHANGED and row!=old_rows[path]:_fail(path,'Unapproved current dependency change')
        if path in CHANGED and row==old_rows[path]:_fail(path,'Stale approved runtime delta')
    if covering['current_dependencies']!=current['current_dependencies'] or covering['current_producer']!=current['current_producer']:
        _fail('/cut/current','Covering cut differs from activated authority')
    wanted_changes=[dict(original=old_rows[p],current=current_rows[p],historical_path=BASE+'qualification-code/a5-r70-current-then/'+p) for p in sorted(CHANGED)]
    if covering['runtime_changes']!=wanted_changes:_fail('/cut/changes','Exact two reviewed runtime transitions required')
    expected_paths={r['source_path'] for r in old['verification_evidence']}|{THEN+'retention.json'}|{BASE+'evidence/a5-r70/'+n for n in EVIDENCE_NAMES}
    evidence=_rows(covering['required_evidence'])
    if set(evidence)!=expected_paths:_fail('/cut/evidence','Missing or foreign required evidence')
    for row in old['verification_evidence']:
        if evidence[row['source_path']]!=row:_fail(row['source_path'],'Old evidence rebound')
    for row in evidence.values():_check(root,row)
    activated=_rows(current['verification_evidence'])
    if set(activated)!=set(evidence)|{CUT}:_fail('/authority/evidence','Missing or foreign activated evidence')
    for path,row in evidence.items():
        if activated[path]!=row:_fail(path,'Activated evidence differs from covering cut')
    _check(root,activated[CUT])
    for field in ('historical_fixed_lock','historical_dependency_relocations','timing_evidence','schema_version'):
        if current[field]!=old[field]:_fail('/authority/'+field,'Original scientific/historical authority changed')
    return {'schema_version':'1.0.0','passed':True,'current_code_count':len(current_rows),
            'historical_code_count':63,'historical_evidence_count':53,
            'historical_edge_count':len(retained['historical_edges']),
            'historical_edges_verified':1600,'historical_edges_unavailable':1,
            'scope':'R70 bounded transition integrity only; no source/native/runtime release qualification'}


if __name__=='__main__':print(json.dumps(verify_r70_transition(),sort_keys=True))
