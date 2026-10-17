"""Programme recipes: load them and turn one programme instance into channels and bindings.

A recipe (data/recipes/<program_id>.json) lists the programme's slots (loads,
controls, resident counts), its demands (annual magnitude per basis unit), its
companions and, per kind, the kernel inputs:
- "commercial": ComStock transform (configuration, sampling building type,
  slot modes, People per space);
- "residential": ResStock dwelling (residents, location, weather, installed
  appliances, thermostat arguments);
- "fixed": source rule sets used as they are.

Annual targets come from the original source shape before any transform, so a
transform moves energy in time without changing the annual total.
"""
from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path

import numpy as np

from .budgets import ANNUAL_UNITS, annual_target, annual_unit, fit_amplitude
from .calendar import evaluate_rules
from .commercial.transform import Slot, transform
from .companions import companion_channels
from .errors import GeneratorError
from .residential.generate import Dwelling, generate_dwelling

DATA = Path(__file__).resolve().parent / "data"


@lru_cache(maxsize=1)
def schedules() -> dict:
    return json.loads((DATA / "schedules.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def load_recipe(program_id: str) -> dict:
    path = DATA / "recipes" / f"{program_id}.json"
    if not path.exists():
        raise GeneratorError("unsupported_binding", "/program_id", f"No recipe for {program_id!r}")
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass
class Binding:
    """One demand bound to its generated shape: amplitude x shape integrates to the target."""
    slot: str
    quantity: str
    unit: str            # magnitude unit, e.g. W/m2
    basis: str
    fuel: str
    host: str
    annual_total: float  # per basis unit, in annual_unit(unit)
    amplitude: float


def _reference_shapes(recipe: dict) -> dict:
    table = schedules()
    return {s["slot"]: evaluate_rules(table[s["schedule"]])[0] for s in recipe["slots"] if s["schedule"]}


def annual_targets(recipe: dict) -> list:
    """Annual total per demand, in demand order (a slot may carry two fuels),
    from direct evidence or magnitude x reference shape."""
    shapes = _reference_shapes(recipe)
    targets = []
    for demand in recipe["demands"]:
        if "annual_total" in demand:
            targets.append(demand["annual_total"])
        else:
            targets.append(annual_target(demand["value"], demand["unit"], shapes[demand["slot"]]))
    return targets


def _commercial_channels(recipe: dict, operating: dict) -> dict:
    table = schedules()
    spec = recipe["commercial"]
    slots = {s["slot"]: Slot(table[s["schedule"]], spec["modes"][s["slot"]])
             for s in recipe["slots"] if s["slot"] in spec["modes"]}
    people = [(schedule_id, table[schedule_id], count) for schedule_id, count in spec["people"]]
    return transform(slots, people, operating, invert_rule_days=spec.get("invert_rule_days", False))


def _residential_channels(recipe: dict, unit_seed: int, rng_mode: str) -> dict:
    d = recipe["dwelling"]
    dwelling = Dwelling(d["residents"], d["state"], d["latitude"], d["longitude"], d["utc_offset"],
                        d["weather_id"], d["installed"])
    return generate_dwelling(dwelling, unit_seed, rng_mode)


def _fixed_channels(recipe: dict) -> dict:
    return _reference_shapes(recipe)


def instance_channels(recipe: dict, *, operating: dict | None = None, unit_seed: int | None = None,
                      rng_mode: str = "pcg64") -> dict:
    """Hourly channels for every slot of the recipe."""
    kind = recipe["kind"]
    if kind == "commercial":
        channels = _commercial_channels(recipe, operating)
    elif kind == "residential":
        channels = _residential_channels(recipe, unit_seed, rng_mode)
    elif kind == "fixed":
        channels = _fixed_channels(recipe)
    else:
        raise GeneratorError("unsupported_binding", "/program_id", f"Recipe kind {kind!r} is generated elsewhere")
    channels.update(companion_channels(recipe["companions"], schedules(), recipe.get("thermostat")))
    selected = {}
    for slot in recipe["slots"]:
        name = slot["slot"]
        if name not in channels:
            raise GeneratorError("missing_channel", f"/slots/{name}", "The recipe selects a slot nothing generated")
        selected[name] = np.asarray(channels[name], dtype=float)
    for name in recipe["companions"]:
        if name not in selected and name in channels:
            selected[name] = np.asarray(channels[name], dtype=float)
    return selected


def bind_demands(recipe: dict, channels: dict, targets: list) -> list[Binding]:
    bindings = []
    for demand, total in zip(recipe["demands"], targets):
        slot = demand["slot"]
        amplitude = fit_amplitude(total, demand["unit"], channels[slot])
        bindings.append(Binding(slot, demand["quantity"], demand["unit"], demand["basis"], demand["fuel"],
                                demand["host"], total, amplitude))
    return bindings


__all__ = ["ANNUAL_UNITS", "Binding", "annual_targets", "annual_unit", "bind_demands", "instance_channels",
           "load_recipe", "schedules"]
