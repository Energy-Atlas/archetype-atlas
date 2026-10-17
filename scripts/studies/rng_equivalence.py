"""Are residential R1 (Ruby MT replay) and R2 (numpy PCG64) statistically equivalent?

Both modes run the same algorithm on different uniform streams, so R2 should
differ from R1 no more than R1 differs from itself under new seeds.

Criteria, fixed before any R1-versus-R2 comparison was run:

1. Stream primitives (10^6 draws per mode): `random()` vs U[0,1) (KS),
   `randbelow(97)` vs uniform integers (chi-square), and cross-correlation of a
   unit's end-use streams, each below its 99 % critical value.
2. Unit outputs, per configuration, with all appliances installed. For every
   statistic below, R2 is equivalent to R1 when
   (a) the standardised effect is at most 0.25 SD (mean statistics), and
   (b) a permutation test that swaps whole units finds the observed statistic
       within 4 null standard deviations (this also controls false alarms over
       the ~300 tests).
   Statistics: per channel, the daily-mean profile (24 hourly means; effect =
   the worst hour), the annual total and the daily-total distribution (KS);
   per end use, annual event count, event durations and start minutes (KS);
   per unit, occupant types and the unit offset (KS).

Why not fixed absolute margins (1 % of peak, KS 0.03): occupancy-driven shapes
vary ~0.15-0.28 of peak per hour between units because occupant types differ,
so a 1 % hourly margin needs 10,000-40,000 units per mode, and KS sampling noise
at 500 units is ~0.06. An R1-only variance pilot (100 units, three
configurations) sized the study without looking at R2.

Writes docs/validation/residential-rng-equivalence.json.
Usage: python -m scripts.studies.rng_equivalence [--seeds 500] [--main-seeds 1000] [--workers 4]
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import time

import numpy as np

from atlas_schedules_v2.residential.activity import simulate_activities
from atlas_schedules_v2.residential.events import EventGenerator
from atlas_schedules_v2.residential.generate import Dwelling, _step_months, dwelling_channels
from atlas_schedules_v2.residential.rng import END_USES, unit_streams
from atlas_schedules_v2.residential.tables import load_tables

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "docs/validation/residential-rng-equivalence.json"
INSTALLED = {k: True for k in ("dishwasher", "clothes_washer", "clothes_dryer", "cooking_range",
                               "plug_loads_other", "plug_loads_tv", "ceiling_fan", "garage")}
LOCATIONS = {
    "hickory_nc": ("NC", 35.741, -81.389, -5, "USA_NC_Hickory.Rgnl.AP.723145_TMY3"),
    "anchorage_ak": ("AK", 61.2169, -149.868, -9, "USA_AK_Anchorage-Merrill.Field.702735_TMY3"),
    "san_jose_ca": ("CA", 37.362, -121.929, -8, "USA_CA_San.Jose.Intl.AP.724945_TMY3"),
}
RESIDENTS = (1, 2, 4)
MAIN_CONFIGURATION = ("hickory_nc", 2)
EVENT_SERIES = ("sink", "shower", "bath", "hot_water_dishwasher", "hot_water_clothes_washer",
                "dishwasher", "clothes_washer", "clothes_dryer", "cooking_range")
EFFECT_MARGIN_SD = 0.25
NULL_Z_LIMIT = 4.0
PERMUTATIONS = 200
EVENTS_PER_UNIT = 40


# --------------------------------------------------------------------------- units
def _runs(series: list) -> tuple[np.ndarray, np.ndarray]:
    """(durations, start minute of day) of contiguous non-zero runs in a minute series."""
    on = np.asarray(series[:365 * 1440]) > 0
    edges = np.diff(np.concatenate(([0], on.astype(np.int8), [0])))
    starts = np.flatnonzero(edges == 1)
    ends = np.flatnonzero(edges == -1)
    return ends - starts, starts % 1440


def run_unit(task: tuple) -> dict:
    location, residents, mode, seed = task
    state, latitude, longitude, offset, weather = LOCATIONS[location]
    dwelling = Dwelling(residents, state, latitude, longitude, offset, weather, INSTALLED)
    tables = load_tables()
    streams = unit_streams(mode, seed)
    activities = simulate_activities(residents, streams["main"], tables)
    channels = dwelling_channels(dwelling, activities, streams)
    fresh = unit_streams(mode, seed)  # end-use streams as the events first saw them
    series = EventGenerator(activities, fresh, tables, _step_months(2007)).generate(INSTALLED)
    sampler = np.random.default_rng(seed)
    unit = {"types": np.asarray(activities.occupant_types), "offset": np.asarray([activities.offset_minutes]),
            "profile": {}, "annual": {}, "daily": {}, "count": {}, "durations": {}, "starts": {}}
    for name, values in channels.items():
        days = values.reshape(365, 24)
        unit["profile"][name] = days.mean(axis=0)
        unit["annual"][name] = float(values.sum())
        unit["daily"][name] = days.sum(axis=1)
    for name in EVENT_SERIES:
        durations, starts = _runs(series[name])
        keep = sampler.permutation(len(durations))[:EVENTS_PER_UNIT]
        unit["count"][name] = float(len(durations))
        unit["durations"][name] = durations[keep]
        unit["starts"][name] = starts[keep]
    return unit


# ---------------------------------------------------------------------- statistics
def ks_distance(a, b) -> float:
    a = np.sort(np.asarray(a, dtype=float))
    b = np.sort(np.asarray(b, dtype=float))
    grid = np.concatenate((a, b))
    return float(np.abs(np.searchsorted(a, grid, "right") / len(a) - np.searchsorted(b, grid, "right") / len(b)).max())


def effect(a: np.ndarray, b: np.ndarray) -> float:
    """Worst standardised mean difference over the trailing axes (0 when there is no spread)."""
    sd = np.sqrt((a.var(axis=0, ddof=1) + b.var(axis=0, ddof=1)) / 2)
    difference = np.abs(a.mean(axis=0) - b.mean(axis=0))
    with np.errstate(divide="ignore", invalid="ignore"):
        standardised = np.where(sd > 0, difference / sd, np.where(difference > 0, np.inf, 0.0))
    return float(np.max(standardised))


def _null_z(observed: float, statistic, units: list, n: int, rng) -> float:
    null = []
    for _ in range(PERMUTATIONS):
        order = rng.permutation(len(units))
        null.append(statistic([units[i] for i in order[:n]], [units[i] for i in order[n:]]))
    spread = float(np.std(null))
    return 0.0 if spread == 0 else (observed - float(np.mean(null))) / spread


def mean_check(per_unit_a: list, per_unit_b: list, rng) -> dict:
    a = np.stack(per_unit_a)
    b = np.stack(per_unit_b)
    observed = effect(a, b)
    z = _null_z(observed, lambda x, y: effect(np.stack(x), np.stack(y)), per_unit_a + per_unit_b, len(a), rng)
    relative = float(np.max(np.abs(a.mean(axis=0) - b.mean(axis=0)) / np.maximum(np.abs(a.mean(axis=0)), 1e-12)))
    return {"effect_sd": observed, "null_z": z, "worst_relative_difference": relative,
            "equivalent": bool(observed <= EFFECT_MARGIN_SD and z <= NULL_Z_LIMIT)}


def distribution_check(per_unit_a: list, per_unit_b: list, rng) -> dict:
    observed = ks_distance(np.concatenate(per_unit_a), np.concatenate(per_unit_b))
    z = _null_z(observed, lambda x, y: ks_distance(np.concatenate(x), np.concatenate(y)),
                per_unit_a + per_unit_b, len(per_unit_a), rng)
    return {"ks": observed, "null_z": z, "equivalent": bool(z <= NULL_Z_LIMIT)}


def compare(r1: list, r2: list, rng) -> dict:
    report = {}
    for name in r1[0]["profile"]:
        report[f"channel/{name}/profile"] = mean_check([u["profile"][name] for u in r1], [u["profile"][name] for u in r2], rng)
        report[f"channel/{name}/annual"] = mean_check([np.asarray([u["annual"][name]]) for u in r1],
                                                      [np.asarray([u["annual"][name]]) for u in r2], rng)
        report[f"channel/{name}/daily"] = distribution_check([u["daily"][name] for u in r1],
                                                             [u["daily"][name] for u in r2], rng)
    for name in EVENT_SERIES:
        report[f"event/{name}/count"] = mean_check([np.asarray([u["count"][name]]) for u in r1],
                                                   [np.asarray([u["count"][name]]) for u in r2], rng)
        report[f"event/{name}/duration"] = distribution_check([u["durations"][name] for u in r1],
                                                              [u["durations"][name] for u in r2], rng)
        report[f"event/{name}/start"] = distribution_check([u["starts"][name] for u in r1],
                                                           [u["starts"][name] for u in r2], rng)
    report["activity/occupant_type"] = distribution_check([u["types"] for u in r1], [u["types"] for u in r2], rng)
    report["activity/offset"] = distribution_check([u["offset"] for u in r1], [u["offset"] for u in r2], rng)
    return report


# ------------------------------------------------------------------- primitives
def primitive_checks(draws: int = 1_000_000) -> dict:
    results = {}
    for mode in ("ruby_mt", "pcg64"):
        streams = unit_streams(mode, 12345)
        values = np.sort([streams["main"].random() for _ in range(draws)])
        ks_uniform = float(np.abs(values - np.arange(1, draws + 1) / draws).max())
        counts = np.bincount([streams["hygiene"].randbelow(97) for _ in range(draws // 10)], minlength=97)
        expected = (draws // 10) / 97
        chi_square = float(((counts - expected) ** 2 / expected).sum())
        sample = np.stack([[streams[name].random() for _ in range(20000)] for name in END_USES])
        correlation = np.corrcoef(sample)
        cross = float(np.abs(correlation[~np.eye(len(END_USES), dtype=bool)]).max())
        limits = {"ks": 1.63 / np.sqrt(draws), "chi_square": 133.5, "correlation": 3.29 / np.sqrt(20000)}
        results[mode] = {"random_ks_vs_uniform": ks_uniform, "randbelow97_chi_square": chi_square,
                         "max_cross_stream_correlation": cross, "limits_99": limits,
                         "equivalent": bool(ks_uniform < limits["ks"] and chi_square < limits["chi_square"]
                                            and cross < limits["correlation"])}
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=500)
    parser.add_argument("--main-seeds", type=int, default=1000)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    started = time.time()
    rng = np.random.default_rng(20261017)
    results = {"method": __doc__, "criteria": {"effect_margin_sd": EFFECT_MARGIN_SD, "null_z_limit": NULL_Z_LIMIT,
                                               "permutations": PERMUTATIONS},
               "primitives": primitive_checks(), "configurations": {}}
    print("primitives", {m: r["equivalent"] for m, r in results["primitives"].items()}, flush=True)
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for location in LOCATIONS:
            for residents in RESIDENTS:
                seeds = args.main_seeds if (location, residents) == MAIN_CONFIGURATION else args.seeds
                runs = {mode: list(pool.map(run_unit, [(location, residents, mode, s) for s in range(1, seeds + 1)],
                                            chunksize=8))
                        for mode in ("ruby_mt", "pcg64")}
                report = compare(runs["ruby_mt"], runs["pcg64"], rng)
                failures = [k for k, v in report.items() if not v["equivalent"]]
                key = f"{location}__{residents}_residents"
                results["configurations"][key] = {"seeds": seeds, "report": report, "failures": failures}
                worst = max(report.values(), key=lambda v: v.get("null_z", 0))
                print(f"{key} ({seeds} seeds): failures {failures} worst z {worst['null_z']:.2f} "
                      f"({time.time() - started:.0f}s)", flush=True)
    failures = [f"{k}: {f}" for k, c in results["configurations"].items() for f in c["failures"]]
    failures += [f"primitives/{m}" for m, r in results["primitives"].items() if not r["equivalent"]]
    results["overall"] = {"equivalent": not failures, "failures": failures, "seconds": round(time.time() - started)}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(results, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print("overall equivalent:", results["overall"]["equivalent"], "failures:", failures)


if __name__ == "__main__":
    main()
