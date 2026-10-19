"""Derive the occupant-type mix tables (plan section 7, O14) from pinned ATUS and ACS inputs.

The ResStock chains, durations and events stay national. Only the share of the
four occupant types (mostly home, early regular worker, mostly away, regular
worker) becomes local, through composition:

1. ATUS diaries (non-holiday weekdays; 96 fifteen-minute slots from 4 am, each
   taking the state with the most minutes) are scored under each type's
   weekday chain, as the generator draws them: initial and time-inhomogeneous
   transition probabilities, and runs of shower, laundry, cooking or
   dishwashing scored once with their duration tables. The posterior uses
   ResStock's national shares as the prior.
2. Cell probabilities: weighted mean posterior per cell of age band
   (15-24, 25-44, 45-64, 65+) x employed x enrolled in school, shrunk toward
   age x employed, then age, then all (pseudo-count 30 effective
   respondents). One table per ATUS window.
3. State compositions: ACS PUMS household-population persons per state. Each
   person aged 15+ falls in a cell; the share under 15 is kept separately
   (ATUS has no diaries for them, so they keep ResStock's national shares).

A dwelling's type probabilities are then sum(cell share x cell probabilities)
+ child share x national shares (atlas_schedules/residential/occupancy.py).

Inputs: sources/occupancy-mix-lock.json (`python -m scripts.fetch --lock ...`).
Usage: python -m scripts.derive_occupancy_mix          (write the tables)
       python -m scripts.derive_occupancy_mix --check  (rebuild and compare)
"""
import csv
import io
import json
import math
from pathlib import Path
import sys
import zipfile

import numpy as np

from atlas_schedules.residential.tables import load_tables

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
LOCK = ROOT / "sources/occupancy-mix-lock.json"
TARGET = ROOT / "atlas_schedules/data/residential/occupancy-mix.json"
WINDOWS = {"2003-2019": (2003, 2019), "2022-2024": (2022, 2024)}
AGE_BANDS = ((15, 24, "15-24"), (25, 44, "25-44"), (45, 64, "45-64"), (65, 200, "65+"))
PSEUDO_COUNT = 30.0
FLOOR = 1e-6
FIPS = {"01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO", "09": "CT", "10": "DE", "11": "DC",
        "12": "FL", "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN", "19": "IA", "20": "KS", "21": "KY",
        "22": "LA", "23": "ME", "24": "MD", "25": "MA", "26": "MI", "27": "MN", "28": "MS", "29": "MO", "30": "MT",
        "31": "NE", "32": "NV", "33": "NH", "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND", "39": "OH",
        "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD", "47": "TN", "48": "TX", "49": "UT",
        "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI", "56": "WY"}


def cell_key(age: int, employed: bool, enrolled: bool) -> str:
    band = next(label for low, high, label in AGE_BANDS if low <= age <= high)
    return f"{band}|{'employed' if employed else 'not_employed'}|{'enrolled' if enrolled else 'not_enrolled'}"


CELLS = [cell_key(low, e, s) for low, _, _ in AGE_BANDS for e in (True, False) for s in (True, False)]


def _rows(zip_name: str, member_suffix: str, columns: tuple):
    archive = zipfile.ZipFile(RAW / zip_name)
    member = next(n for n in archive.namelist() if n.endswith(member_suffix))
    with archive.open(member) as handle:
        reader = csv.reader(io.TextIOWrapper(handle, encoding="ascii"))
        header = next(reader)
        index = [header.index(c) for c in columns]
        for row in reader:
            yield [row[i] for i in index]


# ------------------------------------------------------------------ ATUS diaries
def _state(code: int, where: int) -> int:
    """ATUS activity code and location -> generator state (0 sleep ... 6 idle)."""
    if where > 1:
        return 5
    if code in (10101, 10102):
        return 0
    if code == 10201:
        return 1
    if code == 20102:
        return 2
    if code in (20201, 20202):
        return 3
    if code == 20203:
        return 4
    return 6


def load_respondents() -> dict:
    respondents = {}
    for case, year, day, holiday, weight, enrolled, labour in _rows(
            "atus/atusresp-0324.zip", ".dat",
            ("TUCASEID", "TUYEAR", "TUDIARYDAY", "TRHOLIDAY", "TUFNWGTP", "TESCHENR", "TELFS")):
        if holiday != "0" or day in ("1", "7"):
            continue  # weekday, non-holiday diaries only
        respondents[case] = {"year": int(year), "weight": float(weight), "enrolled": enrolled == "1",
                             "employed": labour in ("1", "2")}
    for case, line, age in _rows("atus/atusrost-0324.zip", ".dat", ("TUCASEID", "TULINENO", "TEAGE")):
        if line == "1" and case in respondents:
            respondents[case]["age"] = int(age)
    return respondents


def load_diaries(cases: set) -> dict:
    """{case: 96 states}; diaries whose durations do not sum to 1,440 minutes are dropped."""
    segments = {}
    for case, order, duration, code, where in _rows("atus/atusact-0324.zip", ".dat",
                                                     ("TUCASEID", "TUACTIVITY_N", "TUACTDUR24", "TRCODEP", "TEWHERE")):
        if case in cases:
            segments.setdefault(case, []).append((int(order), _state(int(code), int(where)), int(duration)))
    diaries = {}
    for case, rows in segments.items():
        rows.sort()
        lengths = [d for _, _, d in rows]
        if sum(lengths) != 1440:
            continue
        slots = np.repeat(np.array([s for _, s, _ in rows], dtype=np.int8), lengths).reshape(96, 15)
        counts = np.stack([(slots == s).sum(1) for s in range(7)], axis=1)
        diaries[case] = counts.argmax(1).astype(np.int8)
    return diaries


# ------------------------------------------------------------------ chain scores
def _time_of_day(step: int) -> int:
    hour = step // 4
    return 0 if hour < 8 else (1 if hour < 16 else 2)


def weekday_log_likelihoods(states: np.ndarray, tables) -> np.ndarray:
    """(n, 4) log-likelihood of each 96-slot diary under each type's weekday chain."""
    n = len(states)
    run = np.ones((n, 96), dtype=int)
    for step in range(94, -1, -1):
        run[:, step] = np.where(states[:, step] == states[:, step + 1], run[:, step + 1] + 1, 1)
    previous = np.concatenate([np.full((n, 1), -1), states[:, :-1]], axis=1)
    held = (previous >= 1) & (previous <= 4) & (states == previous)
    drawn = ~held
    times = ("morning", "midday", "evening")
    result = np.zeros((n, 4))
    for occupant_type in range(4):
        initial = np.log(np.maximum(np.asarray(tables.initial[occupant_type, "weekday"]), FLOOR))
        transitions = np.log(np.maximum(np.asarray(tables.transitions[occupant_type, "weekday"]), FLOOR)).reshape(95, 7, 7)
        total = initial[states[:, 0]]
        for step in range(1, 96):
            total = total + np.where(drawn[:, step], transitions[step - 1][previous[:, step], states[:, step]], 0.0)
        for step in range(96):
            for state in (1, 2, 3, 4):
                mask = drawn[:, step] & (states[:, step] == state)
                if not mask.any():
                    continue
                steps, weights = tables.durations[occupant_type, "weekday", state, times[_time_of_day(step)]]
                pmf = np.zeros(98)
                for length, weight in zip(steps, np.asarray(weights) / np.sum(weights)):
                    pmf[min(length, 97)] += weight
                tail = np.cumsum(pmf[::-1])[::-1]
                length = run[:, step]
                ends_day = step + length == 96
                p = np.where(ends_day, tail[np.minimum(96 - step, 97)], pmf[np.minimum(length, 97)])
                total = total + np.where(mask, np.log(np.maximum(p, FLOOR)), 0.0)
        result[:, occupant_type] = total
    return result


def posteriors(log_likelihoods: np.ndarray, prior) -> np.ndarray:
    a = log_likelihoods + np.log(np.asarray(prior))
    a -= a.max(axis=1, keepdims=True)
    p = np.exp(a)
    return p / p.sum(axis=1, keepdims=True)


# ------------------------------------------------------------------ cell table
def _weighted(posterior: np.ndarray, weights: np.ndarray) -> tuple:
    total = weights.sum()
    return (posterior * weights[:, None]).sum(0) / total, total ** 2 / (weights ** 2).sum()


def cell_probabilities(posterior: np.ndarray, weights: np.ndarray, keys: list) -> dict:
    """Shrunk weighted mean posterior per cell (age x employed x enrolled).

    From all respondents down to age, age x employed and the cell, each level's
    weighted mean is pulled toward the level above with PSEUDO_COUNT effective
    respondents; an empty level keeps the level above.
    """
    parts = np.array([k.split("|") for k in keys])
    estimate_all, _ = _weighted(posterior, weights)
    cells = {}
    for cell in CELLS:
        target = cell.split("|")
        estimate, effective = estimate_all, 0.0
        for depth in (1, 2, 3):
            mask = np.all(parts[:, :depth] == target[:depth], axis=1)
            if not mask.any():
                effective = 0.0
                continue
            mean, effective = _weighted(posterior[mask], weights[mask])
            estimate = (effective * mean + PSEUDO_COUNT * estimate) / (effective + PSEUDO_COUNT)
        respondents = int(np.all(parts == target, axis=1).sum())
        cells[cell] = {"probabilities": [round(float(v), 6) for v in estimate / estimate.sum()],
                       "respondents": respondents,
                       "effective_respondents": round(float(effective), 1) if respondents else 0.0}
    return cells


def atus_tables() -> dict:
    tables = load_tables()
    prior = tables.occupant_type_probabilities
    respondents = load_respondents()
    diaries = load_diaries(set(respondents))
    cases = [c for c in diaries if "age" in respondents[c] and respondents[c]["age"] >= 15]
    states = np.stack([diaries[c] for c in cases])
    posterior = posteriors(weekday_log_likelihoods(states, tables), prior)
    years = np.array([respondents[c]["year"] for c in cases])
    weights = np.array([respondents[c]["weight"] for c in cases])
    keys = [cell_key(respondents[c]["age"], respondents[c]["employed"], respondents[c]["enrolled"]) for c in cases]
    windows = {}
    for name, (first, last) in WINDOWS.items():
        mask = (years >= first) & (years <= last)
        shares, _ = _weighted(posterior[mask], weights[mask])
        windows[name] = {
            "years": [first, last], "weekday_diaries": int(mask.sum()),
            "national_shares": [round(float(v), 6) for v in shares],
            "mean_abs_difference_from_resstock": round(float(np.abs(shares - np.asarray(prior)).mean()), 6),
            "mean_top_probability": round(float((posterior[mask].max(1) * weights[mask]).sum() / weights[mask].sum()), 4),
            "cells": cell_probabilities(posterior[mask], weights[mask], [k for k, m in zip(keys, mask) if m]),
        }
    return windows


# ------------------------------------------------------------------ ACS composition
def state_compositions() -> dict:
    totals = {}
    for member in ("psam_pusa.csv", "psam_pusb.csv"):
        for serial, state, age, employment, school, weight in _rows(
                "acs/csv_pus-2024-1yr.zip", member, ("SERIALNO", "STATE", "AGEP", "ESR", "SCH", "PWGTP")):
            if "GQ" in serial or state not in FIPS:
                continue  # household population of the 50 states and DC
            entry = totals.setdefault(FIPS[state], {"under_15": 0.0, **{c: 0.0 for c in CELLS}})
            age = int(age)
            if age < 15:
                entry["under_15"] += float(weight)
            else:
                entry[cell_key(age, employment in ("1", "2", "4", "5"), school in ("2", "3"))] += float(weight)
    compositions = {}
    for state, entry in sorted(totals.items()):
        population = math.fsum(entry.values())
        compositions[state] = {key: round(value / population, 6) for key, value in entry.items()}
    return compositions


def build() -> dict:
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    return {
        "schema_version": "1.0.0",
        "description": "Occupant-type probabilities per cell (ATUS) and state compositions (ACS PUMS) for the "
                       "residential generator; see scripts/derive_occupancy_mix.py.",
        "types": ["mostly_home", "early_regular_worker", "mostly_away", "regular_worker"],
        "cells": CELLS,
        "method": {"classifier": "chain likelihood under ResStock weekday chains, ResStock national prior",
                   "slot_rule": "state with the most minutes in each 15-minute slot, 4 am to 4 am",
                   "diaries": "non-holiday weekdays, respondents aged 15+",
                   "shrinkage": f"toward age x employed, age, all; pseudo-count {PSEUDO_COUNT:g} effective respondents",
                   "children": "persons under 15 keep ResStock's national shares (no ATUS diaries)",
                   "acs_population": "household population (group quarters excluded), persons weighted by PWGTP"},
        "windows": atus_tables(),
        "states": state_compositions(),
        "provenance": {"lock": str(LOCK.relative_to(ROOT)),
                       "inputs": {f["source_id"] + "/" + f["path"]: f["sha256"] for f in lock["files"]}},
    }


def main() -> None:
    payload = build()
    text = json.dumps(payload, indent=1, sort_keys=True) + "\n"
    if sys.argv[1:] == ["--check"]:
        same = TARGET.exists() and TARGET.read_text(encoding="utf-8") == text
        print("identical" if same else "DIFFERENT")
        raise SystemExit(0 if same else 1)
    TARGET.write_text(text, encoding="utf-8", newline="\n")
    for name, window in payload["windows"].items():
        print(name, window["weekday_diaries"], "diaries; national", window["national_shares"],
              "diff", window["mean_abs_difference_from_resstock"], "top", window["mean_top_probability"])
    print(len(payload["states"]), "states;", TARGET.relative_to(ROOT))


if __name__ == "__main__":
    main()
