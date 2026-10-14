"""Source-native residential allocation and the audited commercial seed adapter."""
import hashlib
from .canonical import canonical
from .errors import GeneratorError
from .ruby_random import SourceRandom

ENDUSE_ORDER = ('hygiene','dishwasher','clothes_washer','clothes_dryer','ev','cooking')

def _master(master):
    if isinstance(master,bool) or not isinstance(master,int) or not 0 <= master < 2**64:
        raise GeneratorError('invalid_seed','/seed','Explicit unsigned 64-bit integer required')

def assign_unit_seeds(master: int, ordered_keys: list[str]) -> dict[str,int]:
    """BuildResidentialScheduleFile/measure.rb:162; order is scientifically significant."""
    _master(master)
    if not isinstance(ordered_keys,list) or any(not isinstance(k,str) or not k for k in ordered_keys):
        raise GeneratorError('invalid_reference','/instances','Ordered nonempty instance keys required')
    if len(set(ordered_keys)) != len(ordered_keys):
        raise GeneratorError('duplicate_instance','/instances','Instance keys must be unique')
    result={};seed=master
    for position,key in enumerate(ordered_keys,1):
        seed *= position
        result[key]=seed
    return result

def source_streams(unit_seed: int) -> dict[str,SourceRandom]:
    """schedules.rb:127-133: retain EV allocation and source end-use coupling."""
    allocator=SourceRandom(unit_seed)
    streams={'main':SourceRandom(unit_seed)}
    for enduse in ENDUSE_ORDER:
        streams[enduse]=SourceRandom(allocator.randbelow(2**32))
    return streams

def commercial_group_seed(master: int, operating_group: str) -> int:
    """atlas_conditional_seeded_v1; consumer receives this full digest exactly once."""
    _master(master)
    if not isinstance(operating_group,str) or not operating_group:
        raise GeneratorError('invalid_reference','/operating_group','Nonempty operating group required')
    return int.from_bytes(hashlib.sha256(canonical(['atlas_conditional_seeded_v1',master,operating_group])).digest(),'big')
