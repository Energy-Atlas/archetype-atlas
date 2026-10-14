"""Native ResStock appliance/water event shapes, schedules.rb:1076-1564.

Resume Task 4 checkpoints; calibration power/flow samples are never annual
budgets or installed ratings. Source revision/line receipts live in ResourceSet.
"""
import math

from ..errors import GeneratorError
from ..ruby_random import SourceRandom
from .activity import dates, required, rows, weighted
from .shapes import MONTHS, PRESENCE_KEYS, _schedules, normalize, shift_and_normalize

MINUTES = 365 * 1440
STEPS = 365 * 96
EVENT_SLOTS = ('hot_water_fixtures', 'hot_water_dishwasher', 'dishwasher',
               'hot_water_clothes_washer', 'clothes_washer', 'clothes_dryer', 'cooking_range')
STREAMS = ('main', 'hygiene', 'dishwasher', 'clothes_washer', 'clothes_dryer', 'ev', 'cooking')


class _DrawStream:
    def __init__(self, key, checkpoint, draws):
        self.key = key
        self.rng = SourceRandom(0)
        self.rng.setstate(checkpoint)
        self.draws = draws

    def random(self):
        value = self.rng.random()
        self.draws.append([self.key, None, value])
        return value

    def randbelow(self, limit):
        value = self.rng.randbelow(limit)
        self.draws.append([self.key, limit, value])
        return value


def _segments(values):
    runs = []
    for index, value in enumerate(values):
        if value == 0:
            continue
        if runs and runs[-1][0] + runs[-1][1] == index and runs[-1][2] == value:
            runs[-1][1] += 1
        else:
            runs.append([index, 1, value])
    return runs


def _fill(values, start, length, value, add=False):
    # Ruby fill can extend an array; washer's outer load loop can reach this.
    if length <= 0:
        return
    end = start + length
    if end > len(values):
        values.extend([0.0] * (end-len(values)))
    if add:
        for minute in range(start, end):
            values[minute] += value
    else:
        values[start:end] = [value] * length


class _EventRun:
    """One source execution, including calibrated minute arrays and draw receipts."""
    def __init__(self, activities, inputs, resources):
        self.days = dates(required(inputs, 'year'))
        residents = required(inputs, 'residents')
        if (isinstance(residents, bool) or not isinstance(residents, (int,float))
                or not math.isfinite(residents) or residents <= 0):
            raise GeneratorError('invalid_input', '/inputs/residents', 'Positive finite native resident count required')
        if (activities['year'] != inputs['year'] or activities['resource_set_id'] != resources.resource_set_id
                or activities['residents_input'] != residents or activities['status'] != 'simulated_source_activities'):
            raise GeneratorError('activity_context', '/activities', 'Activity source/calendar/resident context differs')
        self.traces = activities['resident_states']
        self.count = activities['simulated_residents']
        if (type(self.count) is not int or self.count != int(residents) or self.count <= 0 or len(self.traces) != self.count
                or any(len(t) != STEPS or any(type(s) is not int or not 0 <= s < 7 for s in t) for t in self.traces)):
            raise GeneratorError('activity_context', '/activities/resident_states', 'Complete native resident state traces required')
        self.installed = required(inputs, 'installed')
        if (not isinstance(self.installed, dict) or set(self.installed) != set(PRESENCE_KEYS)
                or any(type(v) is not bool for v in self.installed.values())):
            raise GeneratorError('invalid_input', '/inputs/installed', 'Exact source presence booleans required')
        self.offset = activities['unit_offset_minutes']
        if type(self.offset) is not int or not -30 <= self.offset < 30:
            raise GeneratorError('activity_context', '/activities/unit_offset_minutes', 'Native minute offset required')
        state = required(inputs, 'state')
        self.shifts = {}
        for daytype in ('weekday', 'weekend'):
            table = rows(resources, daytype+'__state_and_monthly_schedule_shift_csv')
            header = table[0]
            self.shifts[daytype] = {r[header.index('Month')]: int(r[header.index('Lead')]) for r in table[1:]
                                    if r[header.index('State')] == state}
            if set(self.shifts[daytype]) != set(MONTHS):
                raise GeneratorError('unsupported_input', '/inputs/state', 'Source state/month shifts required')
        checkpoints = dict(activities['enduse_states'], main=activities['main_state'])
        if set(checkpoints) != set(STREAMS):
            raise GeneratorError('activity_context', '/activities/enduse_states', 'All native streams including EV required')
        seeds = activities['enduse_seeds']
        if (set(seeds) != set(STREAMS)-{'main'} or checkpoints['main']['seed'] != activities['unit_seed']
                or any(checkpoints[key]['seed'] != seeds[key] for key in seeds)):
            raise GeneratorError('activity_context', '/activities/enduse_seeds', 'Native seed receipts differ from resumed checkpoints')
        self.draws = []
        self.streams = {key: _DrawStream(key, checkpoints[key], self.draws) for key in STREAMS}
        self.constants = {key: field['value'] for key, field in resources.get('residential', 'event-constants')['fields'].items()}
        self.schedules = _schedules(resources, 'schedules_csv')
        self.clusters = {}; self.durations = {}; self.power = {}
        for name in ('shower', 'hot_water_dishwasher', 'hot_water_clothes_washer'):
            self.clusters[name] = [float(r[0]) for r in rows(resources, name+'_cluster_size_probability_csv')]
            table = rows(resources, name+'_event_duration_probability_csv')
            self.durations[name] = ([float(r[0])/60 for r in table], [float(r[1]) for r in table])
        for name in ('dishwasher', 'clothes_washer', 'clothes_dryer', 'cooking'):
            self.power[name] = ([[int(v) for v in row] for row in rows(resources, name+'_duration_dist_csv')],
                                [float(row[0]) for row in rows(resources, name+'_consumption_dist_csv')])
        self.consumption_rows = {}; self.duration_rows = {}

    def gaussian(self, stream, mean, std):
        rng = self.streams[stream]
        angle = 2 * math.pi * rng.random()
        radius = math.sqrt(-2 * math.log(1-rng.random()))
        return max(0.1, mean + std * radius * math.cos(angle))

    def flow(self, stream, name):
        return self.gaussian(stream, self.constants[name+'FlowRateMean'], self.constants[name+'FlowRateStd'])

    def duration(self, stream, name):
        durations, probabilities = self.durations[name]
        return durations[weighted(self.streams[stream], probabilities)]

    def cluster(self, stream, name):
        return weighted(self.streams[stream], self.clusters[name]) + 1

    def appliance(self, stream, name):
        rng = self.streams[stream]
        durations, powers = self.power[name]
        if name not in self.consumption_rows:
            self.consumption_rows[name] = int(rng.random() * len(powers))
            self.duration_rows[name] = int(rng.random() * len(durations))
        selected = durations[self.duration_rows[name]]
        return selected[rng.randbelow(len(selected))], powers[self.consumption_rows[name]]

    def states(self, state, step):
        return sum(trace[step] == state for trace in self.traces)

    def sink(self):
        c = self.constants; rng = self.streams['hygiene']
        probable = [int(any(trace[step] not in (0, 5) for trace in self.traces)) for step in range(STEPS)]
        values = [0.0] * MINUTES
        clusters_per_day = int(c['SinkAvgSinkClustersPerHH'] * (0.29*self.count+0.26) / 365)
        flow = self.flow('hygiene', 'Sink')
        for day in range(365):
            probabilities = [probable[day*96+i] * c['SinkHourlyOnsetProb'][i//4] for i in range(96)]
            total = math.fsum(probabilities)
            # Native zero-onset probabilities become NaN; its bsearch selects the last
            # step and reaches the 200-attempt cap without emitting a cluster.
            probabilities = [p/total for p in probabilities] if total else [math.nan]*96
            generated = 0; attempts = 0
            while generated < clusters_per_day and attempts < 200:
                start_step = weighted(rng, probabilities); attempts += 1
                if probable[day*96+start_step] == 0:
                    continue
                probable[day*96+start_step] = 0; generated += 1
                events = weighted(rng, c['SinkEventsPerClusterProbs']) + 1
                start = start_step*15; end = (start_step+1)*15
                for _ in range(events):
                    duration = min(weighted(rng, c['SinkDurationProbability'])+1, end-start)
                    _fill(values, day*1440+start, duration, flow)
                    start += duration + int(c['SinkMinutesBetweenEventGap'])
                    if start >= end:
                        break
        return values

    def bath_shower(self):
        c = self.constants; rng = self.streams['hygiene']
        bath_flow = self.flow('hygiene', 'Bath'); shower_flow = self.flow('hygiene', 'Shower')
        bath = [0.0]*MINUTES; shower = [0.0]*MINUTES; step = 0
        while step < STEPS:
            start = step*15; jump = 1
            for _ in range(self.states(1, step)):
                if rng.random() <= c['BathToShowerRatio']:
                    duration = self.gaussian('hygiene', c['BathDurationMean'], c['BathDurationStd'])
                    length = math.ceil(duration); flow = bath_flow*duration/length
                    m = min(length, MINUTES-start)
                    _fill(bath, start, m, flow, add=True)
                else:
                    events = self.cluster('hygiene', 'shower'); m = 0
                    for _ in range(events):
                        duration = self.duration('hygiene', 'shower'); length = math.ceil(duration)
                        flow = shower_flow*duration/length
                        filled = min(length, MINUTES-start-m)
                        _fill(shower, start+m, filled, flow, add=True); m += filled
                        m += min(int(c['ShowerMinutesBetweenEventGap']), MINUTES-start-m)
                        if start+m >= MINUTES:
                            break
                jump = max(jump, 1+m//15)
            step += jump
        return shower, bath

    def water(self, name, stream, state, prefix):
        c = self.constants; rng = self.streams[stream]
        values = [0.0]*MINUTES; flow = self.flow(stream, prefix); step = 0
        gap = int(c[prefix+'MinutesBetweenEventGap'])
        while step < STEPS:
            jump = 1
            if self.states(state, step):
                loads = weighted(rng, c['HotWaterClothesWasherLoadSizeProbability'])+1 if stream == 'clothes_washer' else 1
                start = step*15; m = 0
                for _ in range(loads):
                    clusters = self.cluster(stream, name)
                    for _ in range(clusters):
                        duration = self.duration(stream, name); length = math.ceil(duration)
                        event_flow = flow*duration/length
                        # Source assigns before its annual-end check, including outer
                        # washer loads that continue after the preceding load reaches end.
                        filled = max(1, min(length, MINUTES-start-m))
                        _fill(values, start+m, filled, event_flow); m += filled
                        if start+m >= MINUTES:
                            break
                        m += min(gap, MINUTES-start-m)
                        if start+m >= MINUTES:
                            break
                if stream == 'clothes_washer' and start+m >= MINUTES:
                    break
                jump = max(jump, 1+m//15)
            step += jump
        return values

    def power_schedule(self, name, stream, state, multiplier_key, dryer=False):
        values = [0.0]*MINUTES; dryer_values = [0.0]*MINUTES
        monthly = self.schedules[(stream if dryer else ('cooking_range' if name == 'cooking' else stream)), multiplier_key]
        dryer_monthly = self.schedules['clothes_dryer', 'ClothesDryerMonthlyMultiplier'] if dryer else None
        step = 0; last = 0
        while step < STEPS:
            active = min(1, self.states(state, step)); jump = 1
            if active and last == 0:
                duration, power = self.appliance(stream, name)
                if duration <= 0:
                    raise GeneratorError('source_undefined', '/events/'+name, 'Nonpositive native event step jump')
                if dryer:
                    dryer_duration, dryer_power = self.appliance('clothes_dryer', 'clothes_dryer')
                month = self.days[step//96].month-1
                length = min(int(duration*15*monthly[month]), MINUTES-step*15)
                _fill(values, step*15, length, power); jump = duration
                if dryer:
                    dryer_start = step*15+length
                    dryer_length = min(int(dryer_duration*15*dryer_monthly[month]), MINUTES-dryer_start)
                    _fill(dryer_values, dryer_start, dryer_length, dryer_power)
                    jump += dryer_duration
            last = active; step += jump
        return (values, dryer_values) if dryer else values

    def generate_minutes(self):
        arrays = {'sink': self.sink()}
        arrays['shower'], arrays['bath'] = self.bath_shower()
        if self.installed['dishwasher']:
            arrays['hot_water_dishwasher'] = self.water('hot_water_dishwasher', 'dishwasher', 4, 'HotWaterDishwasher')
            arrays['dishwasher'] = self.power_schedule('dishwasher', 'dishwasher', 4, 'HotWaterDishwasherMonthlyMultiplier')
        if self.installed['clothes_washer']:
            arrays['hot_water_clothes_washer'] = self.water('hot_water_clothes_washer', 'clothes_washer', 2, 'HotWaterClothesWasher')
            arrays['clothes_washer'], arrays['clothes_dryer'] = self.power_schedule(
                'clothes_washer', 'clothes_washer', 2, 'HotWaterClothesWasherMonthlyMultiplier', dryer=True)
        if self.installed['cooking_range']:
            arrays['cooking_range'] = self.power_schedule('cooking', 'cooking', 3, 'CookingMonthlyMultiplier')
        return arrays


def generate_events(activities: dict, inputs: dict, resources) -> dict:
    """Return applicable hourly event fractions and explicit source/absence receipts."""
    if activities['status'] == 'upstream_zero_residents_skip':
        dates(required(inputs, 'year'))
        if (isinstance(required(inputs, 'residents'), bool) or activities['residents_input'] != inputs['residents'] or inputs['residents'] != 0
                or activities['year'] != inputs['year'] or activities['resource_set_id'] != resources.resource_set_id):
            raise GeneratorError('activity_context', '/activities', 'Zero-skip context differs')
        return {'channels': {}, 'source_context': {'activity_status': activities['status'], 'rng_consumed': False,
                'absence_receipts': {slot: 'upstream_zero_residents_skip' for slot in EVENT_SLOTS},
                'excluded': {'ev': 'excluded_output; zero-resident skip allocates no streams'},
                'resource_set_id': resources.resource_set_id, 'export_precision': 'raw_source_float'}}
    run = _EventRun(activities, inputs, resources)
    minutes = run.generate_minutes()
    absence = {}; channels = {}; components = {}
    for slot, appliance in [('hot_water_dishwasher','dishwasher'), ('dishwasher','dishwasher'),
                            ('hot_water_clothes_washer','clothes_washer'), ('clothes_washer','clothes_washer'),
                            ('clothes_dryer','clothes_dryer'), ('cooking_range','cooking_range')]:
        reason = ('source_washer_branch_absent' if slot == 'clothes_dryer' and not run.installed['clothes_washer']
                  else 'source_appliance_absent' if not run.installed[appliance] else None)
        if reason:
            absence[slot] = reason
            continue
        if max(minutes[slot]) <= 0:
            raise GeneratorError('zero_generated_integral', '/channels/'+slot, 'Native realization has no events; no retry or new seed')
        channels[slot] = shift_and_normalize(minutes[slot], run.offset, run.days, run.shifts)
    for slot in ('shower', 'sink', 'bath'):
        if max(minutes[slot]) <= 0:
            raise GeneratorError('zero_generated_integral', '/channels/hot_water_fixtures/'+slot,
                                 'Native fixture component normalization has no events; no retry or new seed')
        components[slot] = shift_and_normalize(minutes[slot], run.offset, run.days, run.shifts)
    channels['hot_water_fixtures'] = normalize([math.fsum(values) for values in zip(components['shower'], components['sink'], components['bath'])])
    context = {'activity_status': activities['status'], 'resource_set_id': resources.resource_set_id,
               'export_precision': 'raw_source_float', 'rng_consumed': bool(run.draws),
               'enduse_seeds': dict(activities['enduse_seeds']), 'unit_offset_minutes': run.offset,
               'monthly_shifts': run.shifts, 'installed': dict(run.installed), 'absence_receipts': absence,
               'calendar_variant': 'controlled_no_DST_local_standard_calendar',
               'source_month_lookup': 'elapsed local-standard calendar; native reference child TZ=UTC; physical lighting/weather timezone unchanged',
               'excluded': {'ev': 'excluded_output; native allocator seed slot retained'},
               'event_draws': run.draws, 'event_segments': {slot: _segments(values) for slot, values in minutes.items()},
               'minute_lengths': {slot: len(values) for slot, values in minutes.items()},
               'power_rows': {'consumption': run.consumption_rows or None, 'duration': run.duration_rows or None},
               'final_rng_states': {key: stream.rng.getstate() for key, stream in run.streams.items()},
               'fixture_component_integrals': {slot: math.fsum(values) for slot, values in components.items()},
               'shift_order': ['annual_unit_minute_rotation', 'daily_state_month_rotation', 'hourly_sum',
                               'individual_component_normalization', 'fixture_sum_then_max_normalization']}
    return {'channels': channels, 'source_context': context}
