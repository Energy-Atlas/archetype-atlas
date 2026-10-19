"""Occupant activity states on a 15-minute grid (ResStock Markov chain).

Port of OpenStudio-HPXML `schedules.rb` `simulate_occupant_activities`
(lines 207-245). Each resident gets an occupant type, then for every day a
chain over 96 steps of seven states:
0 sleeping, 1 shower, 2 laundry, 3 cooking, 4 dishwashing, 5 away, 6 idle.
States 1-4 last a sampled number of steps. The day's trace starts at 4 am, so
the year is rotated by 16 steps to start at midnight.
"""
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np

from .rng import weighted_choice
from .tables import ACTIVITIES, Tables

STEPS_PER_DAY = 96
STEPS_PER_YEAR = 365 * STEPS_PER_DAY
SLEEPING, AWAY = 0, 5


@dataclass
class Activities:
    states: np.ndarray       # residents x 35040 state codes
    occupant_types: list
    offset_minutes: int      # unit-level random shift, -30..29


def _time_of_day(step: int) -> str:
    hour = step // 4
    if hour < 8:
        return "morning"
    return "midday" if hour < 16 else "evening"


def _resident_trace(stream, tables: Tables, occupant_type: int, year: int) -> list:
    trace = []
    for index in range(365):
        day = date(year, 1, 1) + timedelta(days=index)
        daytype = "weekend" if day.weekday() >= 5 else "weekday"
        probabilities = tables.initial[occupant_type, daytype]
        step = 0
        while step < STEPS_PER_DAY:
            state = weighted_choice(stream, probabilities)
            duration = 1
            if state in ACTIVITIES:
                steps, weights = tables.durations[occupant_type, daytype, state, _time_of_day(step)]
                duration = steps[weighted_choice(stream, weights)]
            filled = min(duration, STEPS_PER_DAY - step)
            trace.extend([state] * filled)
            step += filled
            if step < STEPS_PER_DAY:
                probabilities = tables.transitions[occupant_type, daytype][(step - 1) * 7 + state]
    return trace[-16:] + trace[:-16]


def simulate_activities(residents: int, main_stream, tables: Tables, year: int = 2007,
                        type_probabilities=None) -> Activities:
    """Activity traces for `residents` people (residents >= 1) from the main stream.

    type_probabilities: the occupant-type shares to draw from (residential/occupancy.py);
    None uses ResStock's national shares.
    """
    shares = tables.occupant_type_probabilities if type_probabilities is None else type_probabilities
    types = []
    traces = []
    for _ in range(residents):
        occupant_type = weighted_choice(main_stream, shares)
        types.append(occupant_type)
        traces.append(_resident_trace(main_stream, tables, occupant_type, year))
    offset = int(main_stream.random() * 2 * 30) - 30
    return Activities(np.asarray(traces, dtype=np.int8), types, offset)
