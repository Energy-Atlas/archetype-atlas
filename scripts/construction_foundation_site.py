"""Bounded ground dependency packets from the immutable combined freeze."""
import copy
from functools import lru_cache
from scripts.construction_foundation_release import load_release


@lru_cache(maxsize=1)
def release():return load_release()


def packet_for(context_ids):
    r=release();contexts={i:r['contexts'][i]['extension_id'] for i in sorted(context_ids)}
    extensions={eid:r['extensions'][eid] for eid in sorted(set(contexts.values()))}
    result={'contexts':contexts,'extensions':extensions}
    for table in ('assemblies','unified_assemblies','materials','evidence'):
        ids={i for e in extensions.values() for i in e[table]}
        result[table]={i:r[table][i] for i in sorted(ids)}
    return copy.deepcopy(result)
