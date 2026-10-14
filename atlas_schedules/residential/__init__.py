"""Source-native residential shapes; definition-derived annual budgets bind later."""
from .activity import simulate_activities
from .events import generate_events
from .shapes import occupancy_shapes


def generate_residential(inputs: dict, unit_seed: int, resources) -> dict:
    activities = simulate_activities(inputs, unit_seed, resources)
    shapes = occupancy_shapes(activities, inputs, resources)
    events = generate_events(activities, inputs, resources)
    return {'channels': {**shapes['channels'], **events['channels']},
            'source_context': {'activity': {key: activities[key] for key in
                               ('status', 'year', 'residents_input', 'simulated_residents', 'unit_seed', 'occupant_types',
                                'unit_offset_minutes', 'enduse_seeds', 'resource_set_id',
                                'resident_states', 'decisions', 'main_state')},
                               'shapes': shapes['source_context'], 'events': events['source_context'],
                               'export_precision': 'raw_source_float'}}


__all__ = ['generate_residential', 'generate_events', 'simulate_activities', 'occupancy_shapes']
