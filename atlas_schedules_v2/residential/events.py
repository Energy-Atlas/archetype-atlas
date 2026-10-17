"""Appliance and hot-water events on a minute grid (OpenStudio-HPXML `schedules.rb` 1076-1475).

Streams are shared as upstream does: `hygiene` draws sinks, baths and showers;
`dishwasher` and `clothes_washer` draw their water events then their power
events; the washer's power events also draw the dryer from `clothes_dryer`;
`cooking` is independent. Events are triggered by the residents' activity
states (1 shower, 2 laundry, 3 cooking, 4 dishwashing).

Minute series are plain lists because upstream `fill` may run a few minutes
past the year, which changes the later rotation.
"""
import math

from ..errors import GeneratorError
from .activity import AWAY, SLEEPING, STEPS_PER_YEAR, Activities
from .rng import weighted_choice

MINUTES = 365 * 1440


def _fill(values: list, start: int, length: int, value: float, add: bool = False) -> None:
    if length <= 0:
        return
    end = start + length
    if end > len(values):
        values.extend([0.0] * (end - len(values)))
    if add:
        for minute in range(start, end):
            values[minute] += value
    else:
        values[start:end] = [value] * length


class EventGenerator:
    def __init__(self, activities: Activities, streams: dict, tables, months: list):
        self.traces = activities.states
        self.count = self.traces.shape[0]
        self.streams = streams
        self.tables = tables
        self.constants = tables.constants
        self.months = months  # month index (0-11) of each 15-minute step's day
        self.consumption_row = {}
        self.duration_row = {}

    # draws ---------------------------------------------------------------
    def gaussian(self, stream: str, mean: float, std: float) -> float:
        rng = self.streams[stream]
        angle = 2 * math.pi * rng.random()
        radius = math.sqrt(-2 * math.log(1 - rng.random()))
        return max(0.1, mean + std * radius * math.cos(angle))

    def flow(self, stream: str, prefix: str) -> float:
        return self.gaussian(stream, self.constants[prefix + "FlowRateMean"], self.constants[prefix + "FlowRateStd"])

    def event_duration(self, stream: str, name: str) -> float:
        minutes, probabilities = self.tables.event_durations[name]
        return minutes[weighted_choice(self.streams[stream], probabilities)]

    def cluster_size(self, stream: str, name: str) -> int:
        return weighted_choice(self.streams[stream], self.tables.clusters[name]) + 1

    def appliance(self, stream: str, name: str) -> tuple[int, float]:
        """(duration in 15-minute steps, power) for one appliance event.

        Upstream picks one consumption row and one duration row per appliance on
        first use, then draws a duration from that row for every event."""
        rng = self.streams[stream]
        durations, powers = self.tables.power[name]
        if name not in self.consumption_row:
            self.consumption_row[name] = int(rng.random() * len(powers))
            self.duration_row[name] = int(rng.random() * len(durations))
        row = durations[self.duration_row[name]]
        return row[rng.randbelow(len(row))], powers[self.consumption_row[name]]

    def residents_in(self, state: int, step: int) -> int:
        return int((self.traces[:, step] == state).sum())

    # end uses ------------------------------------------------------------
    def sink(self) -> list:
        c = self.constants
        rng = self.streams["hygiene"]
        awake_home = ((self.traces != SLEEPING) & (self.traces != AWAY)).any(axis=0)
        probable = [int(v) for v in awake_home]
        values = [0.0] * MINUTES
        clusters_per_day = int(c["SinkAvgSinkClustersPerHH"] * (0.29 * self.count + 0.26) / 365)
        flow = self.flow("hygiene", "Sink")
        for day in range(365):
            probabilities = [probable[day * 96 + i] * c["SinkHourlyOnsetProb"][i // 4] for i in range(96)]
            total = math.fsum(probabilities)
            # With no awake-at-home step upstream divides by zero; every draw then
            # selects the last step and the 200-attempt cap ends the day.
            probabilities = [p / total for p in probabilities] if total else [math.nan] * 96
            generated = 0
            attempts = 0
            while generated < clusters_per_day and attempts < 200:
                start_step = weighted_choice(rng, probabilities)
                attempts += 1
                if probable[day * 96 + start_step] == 0:
                    continue
                probable[day * 96 + start_step] = 0
                generated += 1
                events = weighted_choice(rng, c["SinkEventsPerClusterProbs"]) + 1
                start = start_step * 15
                end = (start_step + 1) * 15
                for _ in range(events):
                    duration = min(weighted_choice(rng, c["SinkDurationProbability"]) + 1, end - start)
                    _fill(values, day * 1440 + start, duration, flow)
                    start += duration + int(c["SinkMinutesBetweenEventGap"])
                    if start >= end:
                        break
        return values

    def bath_and_shower(self) -> tuple[list, list]:
        c = self.constants
        rng = self.streams["hygiene"]
        bath_flow = self.flow("hygiene", "Bath")
        shower_flow = self.flow("hygiene", "Shower")
        bath = [0.0] * MINUTES
        shower = [0.0] * MINUTES
        step = 0
        while step < STEPS_PER_YEAR:
            start = step * 15
            jump = 1
            for _ in range(self.residents_in(1, step)):
                if rng.random() <= c["BathToShowerRatio"]:
                    duration = self.gaussian("hygiene", c["BathDurationMean"], c["BathDurationStd"])
                    length = math.ceil(duration)
                    m = min(length, MINUTES - start)
                    _fill(bath, start, m, bath_flow * duration / length, add=True)
                else:
                    m = 0
                    for _ in range(self.cluster_size("hygiene", "shower")):
                        duration = self.event_duration("hygiene", "shower")
                        length = math.ceil(duration)
                        filled = min(length, MINUTES - start - m)
                        _fill(shower, start + m, filled, shower_flow * duration / length, add=True)
                        m += filled
                        m += min(int(c["ShowerMinutesBetweenEventGap"]), MINUTES - start - m)
                        if start + m >= MINUTES:
                            break
                jump = max(jump, 1 + m // 15)
            step += jump
        return shower, bath

    def hot_water(self, name: str, stream: str, state: int, prefix: str) -> list:
        c = self.constants
        rng = self.streams[stream]
        values = [0.0] * MINUTES
        flow = self.flow(stream, prefix)
        gap = int(c[prefix + "MinutesBetweenEventGap"])
        washer = stream == "clothes_washer"
        step = 0
        while step < STEPS_PER_YEAR:
            jump = 1
            if self.residents_in(state, step):
                loads = weighted_choice(rng, c["HotWaterClothesWasherLoadSizeProbability"]) + 1 if washer else 1
                start = step * 15
                m = 0
                for _ in range(loads):
                    for _ in range(self.cluster_size(stream, name)):
                        duration = self.event_duration(stream, name)
                        length = math.ceil(duration)
                        # Upstream writes before its end-of-year check (at least one minute).
                        filled = max(1, min(length, MINUTES - start - m))
                        _fill(values, start + m, filled, flow * duration / length)
                        m += filled
                        if start + m >= MINUTES:
                            break
                        m += min(gap, MINUTES - start - m)
                        if start + m >= MINUTES:
                            break
                if washer and start + m >= MINUTES:
                    break
                jump = max(jump, 1 + m // 15)
            step += jump
        return values

    def power(self, name: str, stream: str, state: int, monthly: list, dryer_monthly: list | None = None):
        """Appliance power events; with `dryer_monthly`, each washer event is followed by a dryer event."""
        values = [0.0] * MINUTES
        dryer_values = [0.0] * MINUTES
        step = 0
        previous_active = 0
        while step < STEPS_PER_YEAR:
            active = min(1, self.residents_in(state, step))
            jump = 1
            if active and previous_active == 0:
                duration, power = self.appliance(stream, name)
                if duration <= 0:
                    raise GeneratorError("source_undefined", f"/events/{name}", "Non-positive event duration")
                if dryer_monthly is not None:
                    dryer_duration, dryer_power = self.appliance("clothes_dryer", "clothes_dryer")
                month = self.months[step]
                length = min(int(duration * 15 * monthly[month]), MINUTES - step * 15)
                _fill(values, step * 15, length, power)
                jump = duration
                if dryer_monthly is not None:
                    dryer_start = step * 15 + length
                    dryer_length = min(int(dryer_duration * 15 * dryer_monthly[month]), MINUTES - dryer_start)
                    _fill(dryer_values, dryer_start, dryer_length, dryer_power)
                    jump += dryer_duration
            previous_active = active
            step += jump
        return (values, dryer_values) if dryer_monthly is not None else values

    def generate(self, installed: dict) -> dict:
        """Minute series per event slot, in upstream order."""
        custom = self.tables.custom
        series = {"sink": self.sink()}
        series["shower"], series["bath"] = self.bath_and_shower()
        if installed["dishwasher"]:
            series["hot_water_dishwasher"] = self.hot_water("hot_water_dishwasher", "dishwasher", 4, "HotWaterDishwasher")
            series["dishwasher"] = self.power("dishwasher", "dishwasher", 4,
                                              custom["dishwasher", "HotWaterDishwasherMonthlyMultiplier"])
        if installed["clothes_washer"]:
            series["hot_water_clothes_washer"] = self.hot_water(
                "hot_water_clothes_washer", "clothes_washer", 2, "HotWaterClothesWasher")
            series["clothes_washer"], series["clothes_dryer"] = self.power(
                "clothes_washer", "clothes_washer", 2,
                custom["clothes_washer", "HotWaterClothesWasherMonthlyMultiplier"],
                dryer_monthly=custom["clothes_dryer", "ClothesDryerMonthlyMultiplier"])
        if installed["cooking_range"]:
            series["cooking_range"] = self.power("cooking", "cooking", 3,
                                                 custom["cooking_range", "CookingMonthlyMultiplier"])
        return series
