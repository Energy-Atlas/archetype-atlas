"""Bounded presentation packets from the frozen equivalent release; no fitting."""
import copy
import hashlib
from functools import lru_cache
from pathlib import Path

from scripts.common import load_json
from scripts.construction_equivalent_release import OUTPUT


def load_equivalents(directory=OUTPUT):
    directory=Path(directory)
    manifest=load_json(directory/'manifest.json')
    if manifest.get('kind')!='construction_equivalent_release' or manifest.get('release')!='1.1.0':
        raise ValueError('Unsupported frozen equivalent release')
    for name,row in manifest['files'].items():
        path=(directory/name).resolve()
        if not path.is_relative_to(directory.resolve()):raise ValueError('Equivalent file escapes release')
        data=path.read_bytes()
        if len(data)!=row['bytes'] or hashlib.sha256(data).hexdigest()!=row['sha256']:
            raise ValueError('Equivalent release checksum/size mismatch: '+name)
    return {name:load_json(directory/(name+'.json')) for name in ('catalogue','component_sets','assemblies')}


@lru_cache(maxsize=1)
def shared_mass_release():
    from scripts.construction_mass_release import load_release
    return load_release()


def mass_fields(context_ids):
    release=shared_mass_release()
    links={cid:release['contexts'][cid]['contract_id'] for cid in context_ids}
    return links,{mid:release['contracts'][mid] for mid in sorted(set(links.values()))}


def packet_for(tables,identity,context_ids):
    contexts={i:copy.deepcopy(tables['catalogue']['contexts'][i]) for i in sorted(context_ids)}
    links,contracts=mass_fields(context_ids)
    for cid,context in contexts.items():
        context.update(schema_version='1.2.0',mass_contract_id=links[cid])
    if identity not in tables['catalogue']['construction_sets']:
        raise ValueError('Unsupported equivalent construction set')
    source=tables['catalogue']['construction_sets'][identity]['source']
    if any(c['source']!=source or c['detailed_context_id']!=i for i,c in contexts.items()):
        raise ValueError('Equivalent context does not match construction set')
    sets={c['component_set_id']:tables['component_sets'][c['component_set_id']] for c in contexts.values()}
    ids={v['assembly_id'] for s in sets.values() for v in s['components'].values() if v['status']=='ready'}
    return {'schema_version':'1.1.0','kind':'construction_equivalent_site_packet',
            'mass_contracts':contracts,
            'construction_set_id':identity,'contexts':contexts,'component_sets':sets,
            'assemblies':{i:tables['assemblies'][i] for i in sorted(ids)}}
