"""ResStock 15-minute occupant states, preserving source main-stream draw order.

Port of dd25369 schedules.rb:simulate_occupant_activities (207-245).
Use original numeric table cells: normalized SI durations are evidence, whereas
the upstream transition algorithm consumes integer 15-minute intervals.
"""
import calendar
from datetime import date, timedelta
import math

from ..errors import GeneratorError
from ..seeds import source_streams


def dates(year):
    if isinstance(year, bool) or not isinstance(year, int) or not 1 <= year <= 9999:
        raise GeneratorError('invalid_calendar', '/inputs/year', 'Gregorian year required')
    if calendar.isleap(year):
        raise GeneratorError('leap_year', '/inputs/year', 'Non-leap Gregorian year required')
    return [date(year, 1, 1) + timedelta(days=i) for i in range(365)]


def required(inputs, key):
    if key not in inputs:
        raise GeneratorError('missing_input', '/inputs/'+key, 'Explicit source input required')
    return inputs[key]


def rows(resources, key):
    return resources.get('residential', key)['original_values']


def weighted(rng, probabilities):
    draw = rng.random()
    cumulative = 0.0
    for index, probability in enumerate(probabilities):
        cumulative += probability
        if cumulative >= draw:
            return index
    return len(probabilities)-1


def simulate_activities(inputs: dict, unit_seed: int, resources) -> dict:
    if isinstance(unit_seed,bool) or not isinstance(unit_seed,int) or unit_seed<0:
        raise GeneratorError('invalid_seed','/unit_seed','Nonnegative source unit seed required')
    days = dates(required(inputs, 'year'))
    residents = required(inputs, 'residents')
    if isinstance(residents, bool) or not isinstance(residents, (int, float)) or not math.isfinite(residents) or residents < 0:
        raise GeneratorError('invalid_input', '/inputs/residents', 'Finite nonnegative source resident count required')
    count = int(residents)  # source args[:geometry_num_occupants].to_i
    if residents != 0 and count == 0:
        raise GeneratorError('unsupported_input', '/inputs/residents', 'Positive count truncating to zero is undefined upstream')
    common = {'schema_version':'1.0.0', 'year':inputs['year'], 'residents_input':residents,
              'simulated_residents':count, 'unit_seed':unit_seed, 'resident_states':[],
              'occupant_types':[], 'decisions':[], 'unit_offset_minutes':None,
              'main_state':None, 'enduse_seeds':{}, 'enduse_states':{},
              'resource_set_id':resources.resource_set_id}
    if count == 0:
        # BuildResidentialScheduleFile.run skips before initializing any stream.
        return dict(common, status='upstream_zero_residents_skip')
    streams = source_streams(unit_seed)
    main = streams['main']
    probabilities = resources.get('residential', 'constants_rb')['text'].split("OccupancyTypesProbabilities = '",1)[1].split("'",1)[0]
    types_probabilities = [float(p) for p in probabilities.split(',')]
    initial = {}; transitions = {}; durations = {}
    names = {1:'shower', 2:'laundry', 3:'cooking', 4:'dishwashing'}
    for daytype in ('weekday','weekend'):
        initial_rows = rows(resources, daytype+'__mkv_chain_initial_prob_csv')
        transition_rows = rows(resources, daytype+'__mkv_chain_transition_prob_csv')
        for occupant_type in range(4):
            initial[occupant_type,daytype] = [float(r[1]) for r in initial_rows if int(r[0]) == occupant_type]
            transitions[occupant_type,daytype] = [[float(v) for v in r[1:]] for r in transition_rows if int(r[0]) == occupant_type]
        for state, name in names.items():
            for time in ('morning','midday','evening'):
                table = rows(resources, daytype+'__duration_probability__'+name+'_'+time+'_duration_probability_csv')
                for occupant_type in range(4):
                    selected = [r for r in table if int(r[0]) == occupant_type]
                    durations[occupant_type,daytype,state,time] = ([int(r[1]) for r in selected], [float(r[2]) for r in selected])
    for _ in range(count):
        occupant_type = weighted(main, types_probabilities)
        common['occupant_types'].append(occupant_type)
        trace = []
        for today in days:
            daytype = 'weekend' if today.weekday() >= 5 else 'weekday'
            probability = initial[occupant_type,daytype]
            j = 0
            while j < 96:
                state = weighted(main, probability)
                duration = 1
                if state in names:
                    hour = j//4
                    time = 'morning' if hour < 8 else 'midday' if hour < 16 else 'evening'
                    values, weights = durations[occupant_type,daytype,state,time]
                    duration = values[weighted(main, weights)]
                common['decisions'].append([state,duration])
                filled = min(duration,96-j)
                trace.extend([state]*filled)
                j += filled
                if j < 96:
                    probability = transitions[occupant_type,daytype][(j-1)*7+state]
        common['resident_states'].append(trace[-16:]+trace[:-16])
    common['unit_offset_minutes'] = int(main.random()*2*30)-30
    common['main_state'] = main.getstate()
    common['enduse_states'] = {k:rng.getstate() for k,rng in streams.items() if k != 'main'}
    common['enduse_seeds'] = {k:state['seed'] for k,state in common['enduse_states'].items()}
    return dict(common, status='simulated_source_activities')
