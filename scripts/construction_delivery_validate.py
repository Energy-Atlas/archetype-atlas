"""Validate every frozen consumer pair without regenerating fitted recipe IDs.

Exact producer reproduction remains a separate mandatory Windows/CPython check.
This command checks frozen bytes, provenance inputs, schemas, references,
source equality and physical/mass conservation on each consumer platform.
"""
import argparse
import json

from scripts.common import ROOT,load_json
from scripts.construction_distribution import load_current_release
from scripts.construction_equivalent_release import validate_document,OUTPUT as EQUIVALENT
from scripts.construction_mass_release import load_release,unified_index,export_pair,sha
from scripts.construction_mass_accounting import BatchMassValidationCache
from scripts.construction_weighting import load_profiles


def validate_context(cid,source,mass,index,profiles,cache):
    detailed,unified=export_pair(cid,source,mass,index=index,cache=cache)
    header=index['catalogue']['contexts'][cid]
    body=index['components'][header['component_set_id']]
    legacy={**unified,'schema_version':'1.1.0','mass_accounting':body['mass_accounting']}
    validate_document(legacy,source,profiles)
    if unified['status']!='ready':raise ValueError('Blocked construction context: '+cid)
    if detailed['mass_accounting']!=unified['mass_accounting']:
        raise ValueError('Detailed/unified mass ledgers disagree: '+cid)
    return detailed['schema_version'],unified['schema_version']


def validate_delivery(*,quiet=False):
    source=load_current_release();mass=load_release();index=unified_index();profiles=load_profiles()
    manifest=load_json(EQUIVALENT/'manifest.json')
    for path,digest in manifest['input_sha256'].items():
        if sha(ROOT/path)!=digest:raise ValueError('Changed unified provenance input: '+path)
    ids=set(source['contexts'])
    if ids!=set(mass['contexts']) or ids!=set(index['catalogue']['contexts']):
        raise ValueError('Detailed/unified/shared-mass context census mismatch')
    if set(source['construction_sets'])!=set(index['catalogue']['construction_sets']):
        raise ValueError('Detailed/unified construction-set census mismatch')
    cache=BatchMassValidationCache()
    for n,cid in enumerate(sorted(ids),1):
        versions=validate_context(cid,source,mass,index,profiles,cache)
        if versions!=('2.1.0','1.2.0'):raise ValueError('Unexpected consumer schema versions')
        if not quiet and n%400==0:print(f'Validated frozen consumer pairs: {n}/{len(ids)}',flush=True)
    return {'construction_sets':len(source['construction_sets']),'contexts':len(ids),
            'consumer_documents':2*len(ids),'blocked_contexts':0,
            'checks':'Frozen checksums and provenance inputs; all detailed/unified schemas, source references, materials, conservation and shared mass ledgers'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--quiet',action='store_true')
    args=parser.parse_args();print(json.dumps(validate_delivery(quiet=args.quiet),indent=2))


if __name__=='__main__':main()
