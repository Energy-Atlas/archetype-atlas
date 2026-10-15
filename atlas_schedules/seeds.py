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


_ACTOR_FIELDS = {'actor_kind', 'instance_key', 'building_realization_id',
                 'unit_id', 'stochastic_action'}


def assign_physical_unit_sequence(master: int, actors: list[dict]) -> list[dict]:
    """One cumulative seed chain across every selected physical unit, including N0."""
    _master(master)
    if not isinstance(actors, list):
        raise GeneratorError('invalid_reference', '/physical_unit_seed_sequence',
                             'Ordered physical actors required')
    seen_keys = set()
    seen_units = set()
    sequence = []
    seed = master
    for position, actor in enumerate(actors):
        path = f'/physical_unit_seed_sequence/{position}'
        if not isinstance(actor, dict) or set(actor) != _ACTOR_FIELDS:
            raise GeneratorError('invalid_reference', path, 'Exact physical actor fields required')
        kind = actor['actor_kind']
        key = actor['instance_key']
        building = actor['building_realization_id']
        unit = actor['unit_id']
        action = actor['stochastic_action']
        if not isinstance(key, str) or not key or key in seen_keys:
            raise GeneratorError('duplicate_instance', path+'/instance_key',
                                 'Physical actor needs a unique instance key')
        seen_keys.add(key)
        if kind == 'stock':
            if building is not None or unit is not None or action != 'generate':
                raise GeneratorError('invalid_reference', path,
                                     'Stock actor has no caller unit and always generates')
        elif kind == 'apartment_adapter':
            if (not isinstance(building, str) or not building or
                    not isinstance(unit, str) or not unit or
                    action not in {'generate', 'skip_n0'}):
                raise GeneratorError('invalid_reference', path,
                                     'Apartment actor needs actual unit identity and action')
            identity = (building, unit)
            if identity in seen_units:
                raise GeneratorError('shared_service_conflict', path+'/unit_id',
                                     'Duplicate selected apartment actor for one physical unit')
            seen_units.add(identity)
        else:
            raise GeneratorError('invalid_reference', path+'/actor_kind',
                                 'Unknown physical actor kind')
        seed *= position + 1
        sequence.append(dict(actor, position=position, unit_seed=seed))
    return sequence


def validate_physical_unit_sequence(bundle: dict) -> None:
    """Validate retained 1.2 seed math and compatibility projection, offline.

    Task 6 additionally reconstructs the actors from retained source/method records;
    this helper does not treat a seed receipt as its own source qualification.
    """
    if not isinstance(bundle, dict) or bundle.get('schema_version') != '1.2.0':
        raise GeneratorError('invalid_contract', '/schema_version', 'Physical sequence requires 1.2.0')
    generation = bundle.get('generation')
    if not isinstance(generation, dict):
        raise GeneratorError('invalid_contract', '/generation', 'Generation receipt required')
    receipts = generation.get('physical_unit_seed_sequence')
    if not isinstance(receipts, list):
        raise GeneratorError('invalid_contract', '/generation/physical_unit_seed_sequence',
                             'Physical sequence required')
    actors = []
    for position, receipt in enumerate(receipts):
        path = f'/generation/physical_unit_seed_sequence/{position}'
        if not isinstance(receipt, dict) or set(receipt) != _ACTOR_FIELDS | {'position', 'unit_seed'}:
            raise GeneratorError('invalid_contract', path, 'Exact physical unit receipt required')
        if type(receipt['position']) is not int or type(receipt['unit_seed']) is not int:
            raise GeneratorError('invalid_contract', path, 'Integer position and seed required')
        actors.append({field: receipt[field] for field in _ACTOR_FIELDS})
    expected = assign_physical_unit_sequence(generation.get('master_seed'), actors)
    for position, (actual, calculated) in enumerate(zip(receipts, expected)):
        if actual != calculated:
            raise GeneratorError('invalid_reference',
                                 f'/generation/physical_unit_seed_sequence/{position}',
                                 'Physical unit position or cumulative seed differs')
    keys = [actor['instance_key'] for actor in expected]
    seeds = {actor['instance_key']: actor['unit_seed'] for actor in expected}
    retained_seeds = generation.get('unit_seeds')
    if (generation.get('residential_unit_order') != keys or
            not isinstance(retained_seeds, dict) or
            set(retained_seeds) != set(seeds) or
            any(type(retained_seeds[key]) is not int or retained_seeds[key] != value
                for key, value in seeds.items())):
        raise GeneratorError('invalid_reference', '/generation/residential_unit_order',
                             'Compatibility order and seeds differ from physical actors')

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
