"""Freeze/export shared mass quantities over immutable construction releases."""
import argparse
import copy
import hashlib
from pathlib import Path

from scripts.common import ROOT, load_json
from scripts.definition_contract import stable_id
from scripts.construction_distribution import load_current_release
from scripts.construction_set_release import hydrate_context
from scripts.construction_set_export import encoded
from scripts.construction_weighting import load_profiles
from scripts.construction_mass_accounting import (
    build_mass_contract, validate_mass_contract, upgrade_detailed, upgrade_unified, SCHEMAS,
    BatchMassValidationCache,
)

OUTPUT = ROOT/'data/construction-mass-releases/v1.0.0'
EQUIVALENT = ROOT/'data/construction-equivalent-releases/v1.1.0'
EXAMPLES = ROOT/'docs/examples/construction-mass-v1'
PILOTS = {
    'medium-office-2019-3B': 'construction-set-beb5e983644344ce44d4a299',
    'warehouse-2019-3B': 'construction-set-8d06e1ae4ed4c1c397f4ae12',
    'residential-5A': 'construction-set-0bcf3780911011575e748fea',
    'residential-multistorey-garage-4A': 'construction-set-e51353d35198be0acedd3c80',
    'residential-raised-exposed-floor-1A': 'construction-set-2c99b4d871abe60b1c76cb96',
    'midrise-apartment-2019-3B': 'construction-set-a34854999c89132b1734e4dc',
    'residential-apartment-unit-1990s-4A': 'construction-set-7a0bd4bfc6d28bbf5ea09c0f',
}
README = '''# Shared construction mass release 1.0.0

Detailed construction JSON 2.1.0 and unified JSON 1.2.0 embed the same source
mass-accounting contract 1.0.0. Original detailed 2.0.0 / distribution v2.2.0
and equivalent 1.1.0 releases and APIs remain immutable. No thermal refitting,
new ground/system models, program or schedule generation, or BEMGen code.

contexts.json maps source context IDs to deduplicated contracts.json entries.
Each standalone export embeds the selected contract, including original added
mass recipes, quantities, scopes, physical budgets and source provenance.
All three schemas are included. Source assemblies, assignments, infiltration
and equivalent recipes remain unchanged. Legacy InteriorPartition is retained
as material evidence; additional mass is instantiated from the new inventory
once, independently of residual restoration. Known zero is explicit; unknown
quantities/materials fail export instead of becoming zero.

Normalize budgets by actual counted floor area. Count physical paired faces
once using the frozen source area policy, and retain residential inferred
adiabatic object conventions. Restore max(0, reference minus represented)
capacity by category; preserve signed residual/excess diagnostics. Allocation
to geometry and simulation remain BEMGen responsibilities.

python -m scripts.construction_mass_release --check verifies exact reproduction.
Add --validate-all to validate both representations of every supported context.
Use --context-id ID --representation detailed|unified --output PATH for one
standalone export. --examples creates the seven paired review examples under
docs/examples/construction-mass-v1; --examples --check verifies them.

Frozen profiles contain the needed geometry/mass operands; no native runtime
or annual simulation is needed. Preserve original Atlas and upstream notices
from the detailed/equivalent source releases. Atlas original work remains
unlicensed; no publication or BEMGen fixture-transfer permission is implied.
'''


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def artifacts(source=None, profiles=None, context_ids=None):
    source = source if source is not None else load_current_release()
    profiles = profiles if profiles is not None else load_profiles()
    ids = sorted(context_ids if context_ids is not None else source['contexts'])
    contexts, contracts, cache = {}, {}, {}
    for cid in ids:
        c = source['contexts'][cid]
        cfg = source['component_configurations'][c['configuration_id']]['components']
        key = (c['reference_id'], stable_id('mass-selection', {k:cfg[k] for k in ('InteriorWall','InteriorFloor','InteriorPartition')}))
        if key not in cache:
            contract = build_mass_contract(source, cid, profiles)
            identity = stable_id('construction-mass-contract', contract)
            contracts[identity] = contract
            cache[key] = identity
        contexts[cid] = {'contract_id': cache[key]}
    files = {'contexts.json': encoded(contexts), 'contracts.json': encoded(dict(sorted(contracts.items()))),
             'README.md': README.encode('utf-8')}
    for path in SCHEMAS.values():
        files['schemas/'+path.name] = path.read_bytes()
    inputs = [ROOT/'scripts/construction_mass_accounting.py', Path(__file__), *SCHEMAS.values(),
              ROOT/'data/construction-releases/v2.2.0/manifest.json', EQUIVALENT/'manifest.json',
              ROOT/'data/program-support/construction-weighting-v1.1.0/manifest.json',
              ROOT/'data/construction-inputs/residential-assemblies-v1.json',
              ROOT/'data/program-support/construction-weighting-v1.1.0/profiles.json']
    manifest = {'schema_version':'1.0.0', 'kind':'construction_shared_mass_release', 'release':'1.0.0',
                'detailed_consumer_schema':'2.1.0', 'unified_consumer_schema':'1.2.0',
                'base_detailed_distribution':'v2.2.0', 'base_unified_release':'1.1.0',
                'input_sha256': {p.relative_to(ROOT).as_posix():sha(p) for p in inputs},
                'coverage': {'contexts':len(contexts), 'contracts':len(contracts),
                    'construction_sets':len({source['contexts'][i]['construction_set_id'] for i in ids}),
                    'ready_contexts':len(contexts), 'blocked_contexts':0},
                'files': {name:{'sha256':hashlib.sha256(data).hexdigest(), 'bytes':len(data)} for name,data in sorted(files.items())}}
    files['manifest.json'] = encoded(manifest)
    return files


def load_release(directory=OUTPUT):
    directory = Path(directory)
    manifest = load_json(directory/'manifest.json')
    if manifest.get('kind') != 'construction_shared_mass_release' or manifest.get('release') != '1.0.0':
        raise ValueError('Invalid shared construction mass release')
    expected = {'contexts.json','contracts.json','README.md'} | {'schemas/'+p.name for p in SCHEMAS.values()}
    if set(manifest['files']) != expected:
        raise ValueError('Invalid shared mass file census')
    for name,row in manifest['files'].items():
        path = directory/name
        if sha(path) != row['sha256'] or path.stat().st_size != row['bytes']:
            raise ValueError('Shared mass checksum mismatch: '+name)
    for name,digest in manifest['input_sha256'].items():
        if sha(ROOT/name) != digest:
            raise ValueError('Shared mass input checksum mismatch: '+name)
    contracts,contexts = load_json(directory/'contracts.json'),load_json(directory/'contexts.json')
    for identity,mass in contracts.items():
        if identity != stable_id('construction-mass-contract', mass):
            raise ValueError('Invalid shared mass contract identity')
        validate_mass_contract(mass)
    used = {c['contract_id'] for c in contexts.values()}
    if used != set(contracts):
        raise ValueError('Orphan shared mass context/contract')
    return {'manifest':manifest, 'contexts':contexts, 'contracts':contracts}


def unified_index():
    manifest = load_json(EQUIVALENT/'manifest.json')
    for name,row in manifest['files'].items():
        if sha(EQUIVALENT/name) != row['sha256']:
            raise ValueError('Frozen unified checksum mismatch: '+name)
    return {k:load_json(EQUIVALENT/v) for k,v in [
        ('catalogue','catalogue.json'),('components','component_sets.json'),('assemblies','assemblies.json')]}


def export_pair(context_id, source=None, mass_release=None, *, index=None, cache=None):
    source = source if source is not None else load_current_release()
    mass_release = mass_release if mass_release is not None else load_release()
    mass = mass_release['contracts'][mass_release['contexts'][context_id]['contract_id']]
    d = upgrade_detailed(hydrate_context(source, context_id, cache=cache.legacy if cache else None), mass, cache=cache)
    index = index if index is not None else unified_index()
    u = copy.deepcopy(index['catalogue']['contexts'][context_id])
    body = index['components'][u.pop('component_set_id')]
    u.update(copy.deepcopy(body))
    aids = {v['assembly_id'] for v in u['components'].values() if v['status']=='ready'}
    u['assemblies'] = {aid:copy.deepcopy(index['assemblies'][aid]) for aid in sorted(aids)}
    return d, upgrade_unified(u, mass, cache=cache)


def example_artifacts(source=None, mass_release=None):
    source = source if source is not None else load_current_release()
    mass_release = mass_release if mass_release is not None else load_release()
    index = unified_index()
    files = {}
    for name,cid in PILOTS.items():
        pair = export_pair(cid, source, mass_release, index=index)
        for representation,document in zip(('detailed','unified'), pair):
            files[name+'.'+representation+'.json'] = encoded(document)
    files['manifest.json'] = encoded({'kind':'shared_mass_examples', 'release':'1.0.0',
        'source_release_manifest_sha256':sha(OUTPUT/'manifest.json'),
        'contexts':PILOTS,
        'files':{name:{'sha256':hashlib.sha256(data).hexdigest(), 'bytes':len(data)} for name,data in sorted(files.items())}})
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--examples', action='store_true')
    parser.add_argument('--validate-all', action='store_true')
    parser.add_argument('--context-id')
    parser.add_argument('--representation', choices=['detailed','unified'], default='detailed')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    source = load_current_release()
    if args.context_id:
        if args.output is None:
            parser.error('--context-id requires --output')
        doc = export_pair(args.context_id, source)[args.representation=='unified']
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(encoded(doc))
        return
    for name,data in artifacts(source).items():
        path = OUTPUT/name
        if args.check:
            if path.read_bytes() != data:
                raise ValueError('Shared mass release reproduction mismatch: '+name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    release = load_release()
    if args.examples:
        for name,data in example_artifacts(source, release).items():
            path = EXAMPLES/name
            if args.check:
                if path.read_bytes() != data:
                    raise ValueError('Shared mass example reproduction mismatch: '+name)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
    if args.validate_all:
        index = unified_index()
        cache = BatchMassValidationCache()
        for i,cid in enumerate(sorted(source['contexts']),1):
            export_pair(cid, source, release, index=index, cache=cache)
            if i % 200 == 0:
                print(f'Validated {i}/{len(source["contexts"])} detailed/unified pairs', flush=True)
    print('Shared mass release:', release['manifest']['coverage'], flush=True)


if __name__ == '__main__':
    main()
