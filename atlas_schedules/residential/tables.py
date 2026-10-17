"""Source tables for the residential generator, loaded once.

The files under data/residential are OpenStudio-HPXML `BuildResidentialScheduleFile`
resources (ResStock revision dd25369), kept with their original cell values and
provenance. Durations stay in upstream integer 15-minute steps.
"""
from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
ACTIVITIES = {1: "shower", 2: "laundry", 3: "cooking", 4: "dishwashing"}
TIMES_OF_DAY = ("morning", "midday", "evening")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "July", "Aug", "Sep", "Oct", "Nov", "Dec")


def _resource(name: str) -> dict:
    return json.loads((DATA / "residential" / f"{name}.json").read_text(encoding="utf-8"))


def _rows(name: str) -> list:
    return _resource(name)["original_values"]


def _schedule_rows(name: str) -> dict:
    """CSV of (schedule name, element, comma-separated values) -> {(name, element): floats}."""
    return {(r[0], r[1]): [float(v) for v in r[2].split(",")] for r in _rows(name)[1:]}


@dataclass(frozen=True)
class Tables:
    occupant_type_probabilities: list
    initial: dict          # (occupant type, daytype) -> 7 probabilities
    transitions: dict      # (occupant type, daytype) -> rows of 7 probabilities
    durations: dict        # (type, daytype, state, time of day) -> (steps, probabilities)
    custom: dict           # schedules.csv
    defaults: dict         # HPXML default_schedules.csv
    shifts: dict           # (daytype, state) -> {month: lead minutes}
    constants: dict        # event constants
    clusters: dict         # water event cluster size probabilities
    event_durations: dict  # water event (minutes, probabilities)
    power: dict            # appliance (duration rows, consumption values)


def _occupant_type_probabilities() -> list:
    text = _resource("constants_rb")["text"]
    values = text.split("OccupancyTypesProbabilities = '", 1)[1].split("'", 1)[0]
    return [float(p) for p in values.split(",")]


def _markov():
    initial, transitions, durations = {}, {}, {}
    for daytype in ("weekday", "weekend"):
        initial_rows = _rows(f"{daytype}__mkv_chain_initial_prob_csv")
        transition_rows = _rows(f"{daytype}__mkv_chain_transition_prob_csv")
        for occupant_type in range(4):
            initial[occupant_type, daytype] = [float(r[1]) for r in initial_rows if int(r[0]) == occupant_type]
            transitions[occupant_type, daytype] = [[float(v) for v in r[1:]]
                                                   for r in transition_rows if int(r[0]) == occupant_type]
        for state, name in ACTIVITIES.items():
            for time in TIMES_OF_DAY:
                table = _rows(f"{daytype}__duration_probability__{name}_{time}_duration_probability_csv")
                for occupant_type in range(4):
                    selected = [r for r in table if int(r[0]) == occupant_type]
                    durations[occupant_type, daytype, state, time] = (
                        [int(r[1]) for r in selected], [float(r[2]) for r in selected])
    return initial, transitions, durations


def _shifts() -> dict:
    shifts = {}
    for daytype in ("weekday", "weekend"):
        table = _rows(f"{daytype}__state_and_monthly_schedule_shift_csv")
        header = table[0]
        state, month, lead = header.index("State"), header.index("Month"), header.index("Lead")
        for row in table[1:]:
            shifts.setdefault((daytype, row[state]), {})[row[month]] = int(row[lead])
    return shifts


def _events():
    clusters, event_durations, power = {}, {}, {}
    for name in ("shower", "hot_water_dishwasher", "hot_water_clothes_washer"):
        clusters[name] = [float(r[0]) for r in _rows(f"{name}_cluster_size_probability_csv")]
        table = _rows(f"{name}_event_duration_probability_csv")
        event_durations[name] = ([float(r[0]) / 60 for r in table], [float(r[1]) for r in table])
    for name in ("dishwasher", "clothes_washer", "clothes_dryer", "cooking"):
        power[name] = ([[int(v) for v in row] for row in _rows(f"{name}_duration_dist_csv")],
                       [float(row[0]) for row in _rows(f"{name}_consumption_dist_csv")])
    return clusters, event_durations, power


@lru_cache(maxsize=1)
def load_tables() -> Tables:
    initial, transitions, durations = _markov()
    clusters, event_durations, power = _events()
    constants = {k: f["value"] for k, f in _resource("event-constants")["fields"].items()}
    return Tables(
        occupant_type_probabilities=_occupant_type_probabilities(),
        initial=initial, transitions=transitions, durations=durations,
        custom=_schedule_rows("schedules_csv"),
        defaults=_schedule_rows("resources__hpxml-measures__HPXMLtoOpenStudio__resources__data__default_schedules_csv"),
        shifts=_shifts(), constants=constants,
        clusters=clusters, event_durations=event_durations, power=power,
    )


@lru_cache(maxsize=None)
def load_drybulb(weather_id: str) -> tuple:
    """Hourly dry-bulb temperatures (degC) of a packaged TMY3 station."""
    record = json.loads((DATA / "weather" / f"{weather_id}.json").read_text(encoding="utf-8"))
    return tuple(record["drybulb_C"])
