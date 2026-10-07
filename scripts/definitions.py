"""Build locked deterministic definitions; validate the pilot before expansion."""
import argparse
from pathlib import Path
from scripts.common import ROOT, load_json, dump_json
from scripts.definition_contract import DefinitionBundle, TABLES, load_context, stable_id
from scripts.program_definitions import build_programs
from scripts.construction_definitions import build_constructions
from scripts.hvac_definitions import build_hvac


def build(context):
    programs=build_programs(context)
    bundle=DefinitionBundle(schema_version='1.0.0',scope=context.scope,
                            extraction_date=context.extraction_date,dependencies=context.dependencies)
    bundle.merge(programs).merge(build_constructions(context,programs)).merge(build_hvac(context))
    if context.scope=='full':
        from scripts.program_composition import compose
        from scripts.residential_definitions import build_residential
        bundle.merge(compose(context,bundle)).merge(build_residential(context))
    lock=load_json(context.root/'sources/definition-evidence-lock.json')
    bundle['source_files']=list(context.atlas['source_files'])+[
        dict(entry,id=stable_id('sourcefile',{'path':entry['path']})) for entry in lock['files']]
    for source in context.atlas['provenance']:
        if source['id'] in {r.get('provenance_id') for r in bundle['schedules']}:
            bundle['provenance'].append({'id':source['id'],'source_file_id':source['source_file_id'],
                'locator':source['locator'],'original_value':source['fields'],'original_unit':'mixed source fields',
                'transformation':'retained schedule provenance; field-specific conversions preserved',
                'extraction_date':source['extraction_date'],'interpretation':source['notes']})
    bundle['policies']=[{'id':'definition-policy-v1',**context.policy}]
    if context.scope=='full':
        for table,source_table in [('programs','programs'),('constructions','envelope_components'),('hvac_systems','systems')]:
            represented={r.get('source_id') for r in bundle[table]}
            ancillary={r['source_id'] for r in bundle['coverage']}
            for source in context.atlas[source_table]:
                if source['id'] not in ancillary:
                    bundle['coverage'].append({'id':'coverage-'+source['id'],'source_id':source['id'],
                        'source_table':source_table,'status':'represented' if source['id'] in represented else 'unsupported',
                        'reason':'Normalized source definition; individual unknowns retained' if source['id'] in represented else 'No supported normalized definition'})
    return DefinitionBundle(**{k:v for k,v in bundle.items() if k not in TABLES}).merge(bundle)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--scope',choices=['pilot','full'],default='pilot')
    p.add_argument('--output',type=Path,default=ROOT/'build/definitions-pilot');args=p.parse_args()
    if args.scope=='full' and not (ROOT/'build/definitions-pilot/pilot-report.json').is_file():
        raise SystemExit('Validate the Medium Office pilot first')
    from scripts.definition_validate import validate
    context=load_context(scope=args.scope);bundle=build(context);report=validate(bundle)
    if report.errors:raise SystemExit('\n'.join(report.errors[:20]))
    args.output.mkdir(parents=True,exist_ok=True)
    for table in TABLES:dump_json(args.output/(table+'.json'),bundle[table])
    dump_json(args.output/'metadata.json',{k:v for k,v in bundle.items() if k not in TABLES})
    dump_json(args.output/('pilot-report.json' if args.scope=='pilot' else 'validation-report.json'),report.__dict__)
    print('Definitions built and validated: '+str(report.coverage))


if __name__=='__main__':main()
