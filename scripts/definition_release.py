"""Freeze, verify and reproduce immutable definition releases."""
import argparse
import csv
import hashlib
import io
from pathlib import Path
from scripts.common import ROOT, load_json
from scripts.definition_contract import DefinitionBundle, DefinitionError, TABLES, ValidationReport, canonical
from scripts.definition_validate import validate


def read_bundle(path):
    path=Path(path);bundle=DefinitionBundle(**load_json(path/'metadata.json'))
    for table in TABLES:bundle[table]=load_json(path/(table+'.json'))
    return bundle


def freeze(bundle,target,version='0.1.1'):
    report=validate(bundle)
    if report.errors:raise DefinitionError('; '.join(report.errors[:10]))
    target=Path(target)
    files={table+'.json':canonical(bundle[table]) for table in TABLES}
    files['metadata.json']=canonical({k:v for k,v in bundle.items() if k not in TABLES})
    files['coverage-report.json']=canonical(report.__dict__)
    for relative in ('schemas/definitions.schema.json','schemas/query-v2.schema.json',
                     'sources/definition-evidence-lock.json','sources/definition-policy.json',
                     'sources/program-composition-policy.json','docs/reviews/source-default-lock.json'):
        if (ROOT/relative).is_file():files[relative]=(ROOT/relative).read_bytes()
    for path in (ROOT/'data/releases/v0.2.0/sources/licenses').glob('*.txt'):
        files['sources/licenses/'+path.name]=path.read_bytes()
    files['LICENSE']=(ROOT/'LICENSE').read_bytes()
    for table in ('programs','constructions','hvac_systems'):
        stream=io.StringIO(newline='');writer=csv.writer(stream,lineterminator='\n')
        writer.writerow(['id','name','building_type','template','source_family','evidence_view','derivation'])
        for row in bundle[table]:writer.writerow([row.get(k) for k in ('id','name','building_type','template','source_family','evidence_view','derivation')])
        files['inspection/'+table+'.csv']=stream.getvalue().encode()
    manifest={'release_version':version,'schema_version':'1.0.0','dependencies':bundle.get('dependencies',{}),
              'files':{name:{'sha256':hashlib.sha256(content).hexdigest(),'size_bytes':len(content)}
                       for name,content in sorted(files.items())}}
    files['manifest.json']=canonical(manifest)
    if target.exists() and any(target.iterdir()):
        if any(not (target/name).is_file() or (target/name).read_bytes()!=content for name,content in files.items()):
            raise DefinitionError('Immutable release differs; choose a new release version')
        if {p.relative_to(target).as_posix() for p in target.rglob('*') if p.is_file()} != set(files):
            raise DefinitionError('Unexpected files in immutable release')
        return manifest
    for name,content in files.items():
        path=target/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
    return manifest


def verify(target):
    from scripts.query_delivery import safe_path
    target=Path(target);report=ValidationReport()
    try:
        manifest=load_json(target/'manifest.json')
        for name,descriptor in manifest['files'].items():
            content=safe_path(target,name).read_bytes()
            if len(content)!=descriptor['size_bytes'] or hashlib.sha256(content).hexdigest()!=descriptor['sha256']:
                report.errors.append('Hash mismatch: '+name)
        expected=set(manifest['files'])|{'manifest.json'}
        if {p.relative_to(target).as_posix() for p in target.rglob('*') if p.is_file()}!=expected:
            report.errors.append('Release file inventory mismatch')
        if not report.errors:report=validate(read_bundle(target))
    except (OSError,ValueError,KeyError) as error:report.errors.append(str(error))
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,default=ROOT/'data/definition-releases/v0.1.1')
    p.add_argument('--input',type=Path);p.add_argument('--verify',action='store_true');p.add_argument('--reproduce',action='store_true');a=p.parse_args()
    if a.verify:
        report=verify(a.target)
        if report.errors:raise SystemExit('\n'.join(report.errors))
        print('Frozen definitions verified')
    elif a.reproduce:
        from scripts.definitions import build
        from scripts.definition_contract import load_context
        expected=read_bundle(a.target);actual=build(load_context(scope=expected['scope']))
        if canonical(expected)!=canonical(actual):raise SystemExit('Reproduction mismatch')
        print('Canonical definition bytes reproduced')
    else:
        if not a.input:p.error('--input required to freeze')
        freeze(read_bundle(a.input),a.target,version=a.target.name.removeprefix('v'));print('Definitions frozen at '+str(a.target))


if __name__=='__main__':main()
