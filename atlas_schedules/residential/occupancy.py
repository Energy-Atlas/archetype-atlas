"""Local occupant-type mix by composition (plan section 7, O14).

ResStock draws every resident's occupant type (mostly home, early regular
worker, mostly away, regular worker) from one national share vector. Here the
shares follow the dwelling's state: each ATUS cell (age band x employed x
enrolled) has its own type probabilities, and the state's household population
(ACS PUMS) weights the cells. Residents under 15, who have no ATUS diaries,
keep the national shares. Chains, durations and events are unchanged.

Tables: data/residential/occupancy-mix.json, built by scripts/derive_occupancy_mix.py.
"""
from functools import lru_cache
import json
import math
from pathlib import Path

from ..errors import GeneratorError

DATA = Path(__file__).resolve().parents[1] / "data" / "residential" / "occupancy-mix.json"
MIXES = ("state", "national")
DEFAULT_WINDOW = "2003-2019"


@lru_cache(maxsize=1)
def load_mix() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def windows() -> tuple:
    return tuple(load_mix()["windows"])


def type_probabilities(state: str, window: str, national) -> list:
    """Type probabilities for a dwelling in `state` under one ATUS window."""
    mix = load_mix()
    if state not in mix["states"]:
        raise GeneratorError("unsupported_input", "/inputs/state", f"No household composition for state {state!r}")
    composition = mix["states"][state]
    cells = mix["windows"][window]["cells"]
    totals = [composition["under_15"] * p for p in national]
    for cell in mix["cells"]:
        share = composition[cell]
        totals = [t + share * p for t, p in zip(totals, cells[cell]["probabilities"])]
    total = math.fsum(totals)
    return [t / total for t in totals]
