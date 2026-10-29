"""Mix generated owners into one result (ADR 0023).

For each load group (quantity, carrier, fuel, host) the mixed annual target is
the sum of the members' targets times their factors, and the mixed shape is
the factor-and-amplitude weighted sum of member shapes:

    factor_i = weight_i x extent_i[basis] x multiplicity_i / denominator
    q[h]     = sum(factor_i x amplitude_i x shape_i[h])

A shared service counts once, whole: factor = its own extent / denominator,
whatever the programme weights. People heat is density x occupancy x activity
per member; heating and cooling setpoints are weight-averaged over the members
that have them.
"""
from dataclasses import dataclass, field
import math
from urllib.parse import quote

import numpy as np

from .budgets import fit_amplitude
from .errors import GeneratorError

SUFFIXES = {"floor_area": "/m2", "dwelling_unit": "/dwelling", "person": "/person", "absolute": ""}
SETPOINTS = ("heating_setpoint", "cooling_setpoint")


@dataclass
class Load:
    slot: str
    quantity: str
    unit: str
    basis: str
    fuel: str
    host: str
    annual_total: float
    amplitude: float
    heat_fractions: dict | None = None


@dataclass
class Owner:
    """One generated owner: a programme instance, a shared service, a caller water owner or a mixture."""
    key: str
    kind: str
    program_id: str | None = None
    service_id: str | None = None
    values: str | None = None                        # programme view: source or filled (ADR 0049)
    schedules: dict = field(default_factory=dict)   # slot -> (unit, 8760 values)
    loads: list = field(default_factory=list)
    controls: list = field(default_factory=list)    # dicts with slot, quantity, unit (and people)
    extent: dict = field(default_factory=dict)
    multiplicity: float = 1.0
    physical_identity: tuple | None = None           # set for whole shared services
    people_pairs: list | None = None                 # carried by mixed owners
    result_basis: str | None = None
    generation: dict = field(default_factory=dict)


def carrier_of(unit: str, basis: str) -> str:
    suffix = SUFFIXES[basis]
    carrier = unit[:len(unit) - len(suffix)] if suffix else unit
    if carrier not in ("W", "m3/s") or carrier + suffix != unit:
        raise GeneratorError("invalid_mixture", "/loads", f"Unit {unit!r} does not match basis {basis!r}")
    return carrier


def scale(owner: Owner, basis: str, denominator: float | None) -> float:
    if denominator is None:
        if owner.extent:
            raise GeneratorError("invalid_mixture", f"/instances/{owner.key}/extent",
                                 "Extents need a mixture denominator")
        return owner.multiplicity
    if basis not in owner.extent:
        raise GeneratorError("invalid_mixture", f"/instances/{owner.key}/extent", f"Missing {basis} extent")
    return owner.extent[basis] * owner.multiplicity / denominator


def default_basis(members: list) -> str:
    bases = {load.basis for owner, _ in members for load in owner.loads}
    for owner, _ in members:
        occupancy = _occupancy(owner)
        if occupancy is not None:
            bases.add(occupancy["people"]["basis"])
    if len(bases) > 1:
        raise GeneratorError("invalid_mixture", "/mixture/result_basis", f"Several bases {sorted(bases)}; choose one")
    return bases.pop() if bases else "absolute"


def _occupancy(owner: Owner):
    return next((c for c in owner.controls if c["quantity"] == "occupancy_fraction" and "people" in c), None)


def _activity(owner: Owner):
    return next((c for c in owner.controls if c["quantity"] == "activity"), None)


def _load_components(members, services, denominator):
    """{group key: [(factor, load, shape)]} in first-seen order."""
    groups = {}
    for owner, weight in members:
        for load in owner.loads:
            factor = weight * scale(owner, load.basis, denominator)
            key = (load.quantity, carrier_of(load.unit, load.basis), load.fuel, load.host)
            groups.setdefault(key, []).append((factor, load, owner.schedules[load.slot][1]))
    for owner in services:
        for load in owner.loads:
            extent = owner.extent[load.basis]
            key = (load.quantity, carrier_of(load.unit, load.basis), load.fuel, load.host)
            groups.setdefault(key, []).append((extent / denominator, load, owner.schedules[load.slot][1]))
    return groups


def _mixed_heat_fractions(components, target_total):
    active = [(f * load.annual_total, load) for f, load, _ in components if f * load.annual_total > 0]
    if not active or any(load.heat_fractions is None for _, load in active):
        return None
    names = set(active[0][1].heat_fractions)
    if any(set(load.heat_fractions) != names for _, load in active):
        raise GeneratorError("invalid_mixture", "/loads/heat_fractions", "Members report different heat fractions")
    return {n: math.fsum(e * load.heat_fractions[n] for e, load in active) / target_total for n in sorted(names)}


def _mix_loads(groups: dict, result_basis: str) -> tuple[dict, list]:
    schedules, loads = {}, []
    for (quantity, carrier, fuel, host), components in groups.items():
        target_total = math.fsum(f * load.annual_total for f, load, _ in components)
        if len(components) == 1:
            values = components[0][2]
        else:
            weights = [f * load.amplitude for f, load, _ in components]
            amplitude = math.fsum(weights)
            mixed = np.sum([w * shape for w, (_, _, shape) in zip(weights, components)], axis=0)
            values = mixed / amplitude if amplitude else np.zeros(8760)
        slot = "load/" + "/".join(quote(part, safe="") for part in (quantity, carrier, fuel, host))
        unit = carrier + SUFFIXES[result_basis]
        heat = _mixed_heat_fractions(components, target_total) if carrier == "W" else None
        schedules[slot] = ("fraction", values)
        loads.append(Load(slot, quantity, unit, result_basis, fuel, host, target_total,
                          fit_amplitude(target_total, unit, values), heat))
    return schedules, loads


def _people_heat(members, result_basis, denominator):
    pairs = []
    for owner, weight in members:
        if owner.people_pairs is not None:
            factor = weight * scale(owner, owner.result_basis, denominator)
            pairs.extend((density * factor, occupancy, activity) for density, occupancy, activity in owner.people_pairs)
            continue
        occupancy = _occupancy(owner)
        if occupancy is None:
            continue
        people = occupancy["people"]
        activity = _activity(owner)
        if activity is None:
            if people["density"] == 0:
                continue
            raise GeneratorError("invalid_mixture", f"/instances/{owner.key}", "Occupancy without activity")
        factor = weight * scale(owner, people["basis"], denominator)
        pairs.append((people["density"] * factor, owner.schedules[occupancy["slot"]][1],
                      owner.schedules[activity["slot"]][1]))
    return pairs


def _setpoints(members, setpoint_weights) -> dict:
    schedules = {}
    for slot in SETPOINTS:
        eligible = [(w, owner.schedules[slot][1]) for (owner, _), w in zip(members, setpoint_weights)
                    if w > 0 and slot in owner.schedules and owner.multiplicity > 0
                    and all(v > 0 for v in owner.extent.values())]
        total = math.fsum(w for w, _ in eligible)
        if total:
            schedules[slot] = ("C", np.sum([w * values for w, values in eligible], axis=0) / total)
    return schedules


def mix(key: str, program_id: str, members: list, services: list, result_basis: str | None,
        denominator: float | None, setpoint_weights: list | None = None, kind: str = "mixture") -> Owner:
    """Mixed owner from (owner, weight) members and whole shared-service owners."""
    unique_services = []
    seen = {}
    for owner in services:
        identity = owner.physical_identity
        if identity in seen:
            continue
        seen[identity] = owner
        unique_services.append(owner)
    basis = result_basis or default_basis(members)
    if denominator is not None and result_basis is None:
        raise GeneratorError("invalid_mixture", "/mixture", "A denominator needs a result basis")
    schedules, loads = _mix_loads(_load_components(members, unique_services, denominator), basis)
    pairs = _people_heat(members, basis, denominator)
    controls = []
    if pairs:
        values = np.sum([d * occupancy * activity for d, occupancy, activity in pairs], axis=0)
        schedules["people_heat"] = ("W" + SUFFIXES[basis], values)
        controls.append({"slot": "people_heat", "quantity": "people_heat", "unit": "W" + SUFFIXES[basis]})
    weights = setpoint_weights if setpoint_weights is not None else [w for _, w in members]
    for slot, schedule in _setpoints(members, weights).items():
        schedules[slot] = schedule
        controls.append({"slot": slot, "quantity": "temperature", "unit": "C"})
    extent = {basis: denominator} if denominator is not None else {}
    return Owner(key=key, kind=kind, program_id=program_id, schedules=schedules, loads=loads, controls=controls,
                 extent=extent, people_pairs=pairs, result_basis=basis,
                 generation={"result_basis": basis, "denominator": denominator,
                             "members": [[o.key, w] for o, w in members],
                             "services": [o.key for o in unique_services]})


__all__ = ["Load", "Owner", "SUFFIXES", "carrier_of", "mix", "scale"]
