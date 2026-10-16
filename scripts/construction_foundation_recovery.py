"""Internal ground census and pinned native-recovery adapter; never a public suite.

python -m scripts.construction_foundation_recovery [--check]
No source execution, site/program generation or historical release mutation.
"""
import argparse
import hashlib
from collections import Counter
from pathlib import Path

from scripts.common import ROOT, load_json, dump_json
from scripts.construction_distribution import load_current_release
from scripts.construction_export import climate_matches

DATE = '2026-10-16'
OUTPUT = ROOT/'data/construction-inputs/foundation-source-v1.json'
DEFINITIONS = ROOT/'data/definition-releases/v0.1.1/constructions.json'
GEOMETRY = ROOT/'data/construction-inputs/geometry-v1.json'
RESIDENTIAL = ROOT/'data/construction-inputs/residential-assemblies-v1.json'
SELECTION = ROOT/'data/construction-releases/v2.2.0/selection.json'
NO_CONTACT = {'Above Apartment', 'Ambient'}
ROLES = {'GroundFloor':'ground_contact_floor', 'FoundationWall':'ground_contact_wall'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inventory_foundation_sources(definitions, contexts, geometry, residential):
    """Select table candidates, never infer a final native method from a label."""
    definitions = {d['id']:d for d in definitions}
    res_geometry = {r['id']:r for r in geometry['residential']}
    suites = {}
    configurations = Counter()
    deferred = Counter()
    for identity, suite in sorted(contexts['construction_sets'].items()):
        source = suite['source']
        record = {'id':identity, 'scope':suite['scope'],
                  'building_type':source['building_type'], 'template':source['template'],
                  'source_fixture_id':source['source_fixture_id']}
        if suite['scope']=='whole_dwelling':
            fid = source['source_fixture_id']
            effective = res_geometry[fid]['source_context']['foundation_adjacency']
            pending = residential['records'][fid]['deferred_elements']
            if effective in NO_CONTACT and pending:
                raise ValueError('Source no-contact absence contradicts deferred physics: '+fid)
            if effective not in NO_CONTACT and not pending:
                raise ValueError('Missing residential foundation dependencies: '+fid)
            record.update(effective_configuration=effective,
                          deferred_elements=pending,
                          disposition='source_supported_no_contact' if effective in NO_CONTACT else 'missing_executable_physics')
            configurations[effective]+=1
            deferred.update(p['role'] for p in pending)
        else:
            definition=definitions[identity]
            for role,slot in ROLES.items():
                ids=definition['elements'].get(slot,[])
                if role=='GroundFloor' and not ids:
                    raise ValueError('Missing ground floor source dependency: '+identity)
                if any(k not in definitions for k in ids):
                    raise ValueError('Orphan ground source dependency: '+identity)
                record[slot]=list(ids)
            record['effective_configuration']=None
            record['disposition']='missing_executable_physics'
        suites[identity]=record
    selected={}
    for identity,c in sorted(contexts['contexts'].items()):
        suite=suites[c['construction_set_id']]
        candidates={}
        if suite['scope']=='building':
            for role,slot in ROLES.items():
                candidates[role]=[k for k in suite[slot] if climate_matches(definitions[k]['climate'],c['climate_zone'])]
                if role=='GroundFloor' and len(candidates[role])!=1:
                    raise ValueError('Missing/ambiguous GroundFloor climate candidate: '+identity)
                if role=='FoundationWall' and len(candidates[role])>1:
                    raise ValueError('Ambiguous FoundationWall climate candidate: '+identity)
        selected[identity]={'id':identity,'suite_id':suite['id'],
            'climate_zone':c['climate_zone'],'reference_id':c['reference_id'],
            'candidate_elements':candidates,'disposition':suite['disposition'],
            'native_execution_recovered':False}
    counts=Counter(c['disposition'] for c in selected.values())
    coverage={'suites':len(suites),'contexts':len(selected),
        'commercial_floor_suites':sum(bool(s.get('ground_contact_floor')) for s in suites.values()),
        'commercial_wall_suites':sum(bool(s.get('ground_contact_wall')) for s in suites.values()),
        'context_dispositions':{k:counts[k] for k in ('executable_contact','source_supported_no_contact','missing_executable_physics')},
        'residential_effective_configurations':dict(sorted(configurations.items())),
        'deferred_residential_objects':dict(sorted(deferred.items()))}
    return {'schema_version':'1.0.0','kind':'internal_foundation_source_census',
        'extraction_date':DATE,'consumer_selectable':False,
        'suites':suites,'contexts':selected,'coverage':coverage}


def build_census():
    packet=inventory_foundation_sources(load_json(DEFINITIONS),load_current_release(),load_json(GEOMETRY),load_json(RESIDENTIAL))
    selection=load_json(SELECTION)
    packet['source_evidence_context_ids']=selection['source_evidence_context_ids']
    packet['coverage']['source_evidence_contexts']=len(packet['source_evidence_context_ids'])
    # No raw dependencies are fetched here. Existing receipts pin all inherited inputs.
    paths=[DEFINITIONS,GEOMETRY,RESIDENTIAL,SELECTION,
           ROOT/'scripts/construction_foundation_recovery.py',
           ROOT/'sources/runtime-lock.json',ROOT/'sources/commercial-runtime-lock.json']
    packet['input_sha256']={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    packet['provenance']={'source_locator':{
        'commercial':'data/definition-releases/v0.1.1/constructions.json#/id={suite_id}/elements/ground_contact_*',
        'residential':'data/construction-inputs/geometry-v1.json#/residential/id={source_fixture_id}/source_context/foundation_adjacency',
        'deferred_objects':'data/construction-inputs/residential-assemblies-v1.json#/records/{source_fixture_id}/deferred_elements'},
        'original_unit':'categorical source identities and source climate labels',
        'transformation':'Existing suite selection and exact source climate matching; effective HPXML foundation after unit-position processing; no physical inference',
        'interpretation_note':'Candidate inventory only. Missing executable physics remains blocked, including finite-R recipes named Adiabatic. Full extraction receipts remain in the locked input files.',
        'extraction_date':DATE}
    return packet


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    packet=build_census()
    if args.check:
        if load_json(OUTPUT)!=packet:raise ValueError('Foundation census reproducibility mismatch')
    else:dump_json(OUTPUT,packet)
    print(packet['coverage'])


if __name__=='__main__':main()
