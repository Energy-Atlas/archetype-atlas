"""ResStock housing characteristics for one apartment unit (plan section 8, B3; rulings 186-187).

Draws a unit's characteristics from the packaged ResStock tables
(scripts/build_resstock_characteristics.py), conditioned exactly on what the caller and the
programme fix:

- location: state, and the IECC 2004 climate zone if given (otherwise drawn within the state);
  county and PUMA are drawn as hidden variables, so they are summed out;
- building: `Geometry Building Type RECS`, the `Geometry Building Type Height` class for 5+ units,
  the allowed `Vintage` options (from the template), and the `Geometry Floor Area` bin of the unit;
- HVAC, fixed to the prototype: heating fuel, heating type, cooling type, shared system and zonal
  electric heating (all five or none);
- residents: an `Occupants` option, or none to draw them (vacancy included).

Conditioning is exact, not forward clamping. Every fixed characteristic downstream of a drawn one
(for example residents, which depend on income and tenure) reweights its ancestors: the posterior
over the county-and-PUMA cell, building size class and vintage is enumerated with the household
(vacancy, tenure, income, bedrooms) and HVAC likelihoods summed out; each hidden variable is then
drawn from its exact conditional. Characteristics with no fixed descendant are drawn forward in
topological order. Table rows are normalised to sum to one.

The draws use their own PCG64 stream (`SeedSequence([unit_seed, STREAM_TAG])`), so the schedule
streams of the same unit are unchanged.
"""
from dataclasses import dataclass
from functools import lru_cache
import gzip
import json
import math
from pathlib import Path

import numpy as np

from ..errors import GeneratorError
from .rng import Pcg64Stream, weighted_choice

DATA = Path(__file__).resolve().parents[1] / "data" / "residential" / "characteristics"
STREAM_TAG = 0x52455343  # "RESC"
FT2_PER_M2 = 1 / 0.09290304
FLOOR_AREA_BINS = ((0, 500, "0-499"), (500, 750, "500-749"), (750, 1000, "750-999"), (1000, 1500, "1000-1499"),
                   (1500, 2000, "1500-1999"), (2000, 2500, "2000-2499"), (2500, 3000, "2500-2999"),
                   (3000, 4000, "3000-3999"), (4000, math.inf, "4000+"))
HVAC = ("Heating Fuel", "HVAC Heating Type", "HVAC Cooling Type", "HVAC Has Shared System",
        "HVAC Has Zonal Electric Heating")
# Drawn by the exact posterior below; every other table is drawn forward.
POSTERIOR = {"ASHRAE IECC Climate Zone 2004", "County and PUMA", "County", "PUMA", "State", "Census Division",
             "Census Division RECS", "Custom State", "PUMA Metro Status", "Geometry Building Type ACS",
             "Geometry Building Type RECS", "Vintage", "Vintage ACS", "Vacancy Status", "Tenure", "Income",
             "Income RECS2015", "Income RECS2020", "Geometry Floor Area", "Geometry Floor Area Bin",
             "Geometry Stories", "Geometry Building Type Height", "Bedrooms", "Occupants", *HVAC,
             "HVAC Heating Efficiency"}


@dataclass(frozen=True)
class Conditions:
    state: str
    building_type: str
    floor_area: str
    vintages: tuple
    climate_zone: str | None = None
    height: str | None = None
    occupants: str | None = None
    hvac: tuple | None = None


def floor_area_option(area_m2: float) -> str:
    """The `Geometry Floor Area` bin holding a unit's conditioned floor area."""
    if not area_m2 > 0:
        raise GeneratorError("unsupported_input", "/extent/floor_area", "Floor area must be positive")
    area = area_m2 * FT2_PER_M2
    for low, high, label in FLOOR_AREA_BINS:
        if low <= area < high:
            return label
    raise GeneratorError("unsupported_input", "/extent/floor_area", "Floor area must be finite")


def occupants_option(residents: int) -> str:
    if residents < 0:
        raise GeneratorError("unsupported_input", "/residents", "Residents cannot be negative")
    return "10+" if residents >= 10 else str(residents)


class Table:
    def __init__(self, name: str, record: dict):
        self.name = name
        self.dependencies = record["dependencies"]
        self.options = record["options"]
        self.rows = record["rows"]
        self.index = {option: i for i, option in enumerate(self.options)}

    def distribution(self, values: dict) -> list:
        key = "|".join(values[d] for d in self.dependencies)
        try:
            row = self.rows[key]
        except KeyError:
            raise GeneratorError("source_undefined", f"/characteristics/{self.name}",
                                 f"No source row for {dict(zip(self.dependencies, key.split('|')))}") from None
        total = math.fsum(row)
        if total <= 0:
            raise GeneratorError("source_undefined", f"/characteristics/{self.name}", f"Empty source row {key}")
        return [p / total for p in row]

    def probability(self, option: str, values: dict) -> float:
        return self.distribution(values)[self.index[option]]

    def only(self, values: dict) -> str:
        """The option of a one-to-one mapping row."""
        row = self.distribution(values)
        winners = [i for i, p in enumerate(row) if p == 1.0]
        if len(winners) != 1:
            raise GeneratorError("source_undefined", f"/characteristics/{self.name}", "Mapping row is not one-to-one")
        return self.options[winners[0]]


@lru_cache(maxsize=8)
def _load(state: str) -> tuple:
    try:
        shard = json.loads(gzip.decompress((DATA / "states" / f"{state}.json.gz").read_bytes()))
    except FileNotFoundError:
        raise GeneratorError("unsupported_input", "/location/state", f"No ResStock tables for state {state!r}") from None
    national = _national()
    tables = {name: Table(name, record) for name, record in {**national["tables"], **shard["tables"]}.items()}
    return tables, shard["cells"]


@lru_cache(maxsize=1)
def _national() -> dict:
    return json.loads(gzip.decompress((DATA / "national.json.gz").read_bytes()))


def _forward_order(tables: dict) -> list:
    """Remaining tables in dependency order (ties by name)."""
    pending = {name: set(t.dependencies) for name, t in tables.items() if name not in POSTERIOR}
    done, order = set(POSTERIOR), []
    while pending:
        ready = sorted(name for name, deps in pending.items() if deps <= done)
        if not ready:
            raise GeneratorError("source_undefined", "/characteristics", f"Cyclic or missing dependencies: {sorted(pending)}")
        for name in ready:
            order.append(name)
            done.add(name)
            del pending[name]
    return order


class _Posterior:
    """Exact joint posterior over (climate zone, cell, ACS building type, vintage)."""

    def __init__(self, conditions: Conditions):
        self.c = conditions
        self.tables, cells = _load(conditions.state)
        t = self.tables
        if conditions.hvac is not None and len(conditions.hvac) != len(HVAC):
            raise GeneratorError("unsupported_input", "/hvac", "Give all five HVAC characteristics or none")
        state = {"State": conditions.state}
        self.base = {"State": conditions.state, "Census Division": t["Census Division"].only(state),
                     "Census Division RECS": t["Census Division RECS"].only(state),
                     "Custom State": t["Custom State"].only(state),
                     "Geometry Building Type RECS": conditions.building_type,
                     "Geometry Floor Area": conditions.floor_area}
        self.base["Geometry Floor Area Bin"] = t["Geometry Floor Area Bin"].only(self.base)
        zones = t["ASHRAE IECC Climate Zone 2004"].distribution({})
        zone_index = t["ASHRAE IECC Climate Zone 2004"].index
        acs = [a for a in t["Geometry Building Type RECS"].rows
               if t["Geometry Building Type RECS"].only({"Geometry Building Type ACS": a}) == conditions.building_type]
        self.candidates, weights = [], []
        household_cache, hvac_cache = {}, {}
        for cell in cells:
            puma = cell["puma"]
            local = dict(self.base, **{"County and PUMA": cell["id"], "County": cell["county"], "PUMA": puma})
            local["PUMA Metro Status"] = t["PUMA Metro Status"].only(local)
            for zone, p_cell in cell["probability_given_climate_zone"].items():
                if conditions.climate_zone is not None and zone != conditions.climate_zone:
                    continue
                p_zone = zones[zone_index[zone]] * p_cell
                if p_zone == 0:
                    continue
                for a in acs:
                    local_a = dict(local, **{"Geometry Building Type ACS": a})
                    p_acs = t["Geometry Building Type ACS"].probability(a, local_a)
                    if p_acs == 0:
                        continue
                    vintage_row = t["Vintage"].distribution(local_a)
                    for v in conditions.vintages:
                        p_v = vintage_row[t["Vintage"].index[v]]
                        if p_v == 0:
                            continue
                        values = dict(local_a, **{"ASHRAE IECC Climate Zone 2004": zone, "Vintage": v})
                        values["Vintage ACS"] = t["Vintage ACS"].only(values)
                        w = p_zone * p_acs * p_v * self._height(values)
                        if w == 0:
                            continue
                        key = (cell["id"], v)
                        if key not in hvac_cache:
                            hvac_cache[key] = self._hvac(values)
                        w *= hvac_cache[key]
                        if w == 0:
                            continue
                        key = (puma, values["Vintage ACS"])
                        if key not in household_cache:
                            household_cache[key] = self._household(values)
                        w *= household_cache[key]
                        if w > 0:
                            self.candidates.append(values)
                            weights.append(w)
        total = math.fsum(weights)
        if total <= 0:
            raise GeneratorError("source_undefined", "/characteristics",
                                 f"ResStock has no multifamily unit matching {conditions}")
        self.weights = [w / total for w in weights]

    # Likelihood factors -------------------------------------------------------------------------------
    def _height(self, values: dict) -> float:
        if self.c.height is None:
            return 1.0
        t = self.tables
        total = 0.0
        stories = t["Geometry Stories"].distribution(values)
        for option, p in zip(t["Geometry Stories"].options, stories):
            if p and t["Geometry Building Type Height"].only(dict(values, **{"Geometry Stories": option})) == self.c.height:
                total += p
        return total

    def _hvac(self, values: dict) -> float:
        if self.c.hvac is None:
            return 1.0
        t = self.tables
        v = dict(values, **dict(zip(HVAC[:4], self.c.hvac[:4])))
        p = 1.0
        for name in HVAC[:4]:
            p *= t[name].probability(v[name], v)
            if p == 0:
                return 0.0
        efficiencies = t["HVAC Heating Efficiency"].distribution(v)
        zonal = t["HVAC Has Zonal Electric Heating"]
        return p * math.fsum(q for option, q in zip(t["HVAC Heating Efficiency"].options, efficiencies)
                             if q and zonal.only({"HVAC Heating Efficiency": option}) == self.c.hvac[4])

    def _household_terms(self, values: dict):
        """Nested terms for (vacancy, tenure, income) with the floor-area and resident evidence summed in."""
        t = self.tables
        for vac, p_vac in zip(t["Vacancy Status"].options, t["Vacancy Status"].distribution(values)):
            if not p_vac:
                continue
            v1 = dict(values, **{"Vacancy Status": vac})
            for ten, p_ten in zip(t["Tenure"].options, t["Tenure"].distribution(v1)):
                if not p_ten:
                    continue
                v2 = dict(v1, Tenure=ten)
                for inc, p_inc in zip(t["Income"].options, t["Income"].distribution(v2)):
                    if not p_inc:
                        continue
                    v3 = dict(v2, Income=inc)
                    yield v3, p_vac * p_ten * p_inc * self._area(v3) * self._residents(v3)

    def _area(self, values: dict) -> float:
        t = self.tables
        total = 0.0
        for i20, p in zip(t["Income RECS2020"].options, t["Income RECS2020"].distribution(values)):
            if p:
                total += p * t["Geometry Floor Area"].probability(self.c.floor_area, dict(values, **{"Income RECS2020": i20}))
        return total

    def _residents(self, values: dict) -> float:
        if self.c.occupants is None:
            return 1.0
        t = self.tables
        total = 0.0
        bedrooms = t["Bedrooms"].distribution(values)
        for i15, p15 in zip(t["Income RECS2015"].options, t["Income RECS2015"].distribution(values)):
            if not p15:
                continue
            for bed, p_bed in zip(t["Bedrooms"].options, bedrooms):
                if p_bed:
                    v = dict(values, **{"Income RECS2015": i15, "Bedrooms": bed})
                    total += p15 * p_bed * t["Occupants"].probability(self.c.occupants, v)
        return total

    def _household(self, values: dict) -> float:
        return math.fsum(w for _, w in self._household_terms(values))

    # Drawing ------------------------------------------------------------------------------------------
    def draw(self, stream) -> dict:
        t = self.tables
        values = dict(self.candidates[weighted_choice(stream, self.weights)])
        if self.c.height is not None:
            stories = [(o, p) for o, p in zip(t["Geometry Stories"].options, t["Geometry Stories"].distribution(values))
                       if p and t["Geometry Building Type Height"].only(dict(values, **{"Geometry Stories": o})) == self.c.height]
            values["Geometry Stories"] = _pick(stream, stories)
        else:
            values["Geometry Stories"] = _pick_row(stream, t["Geometry Stories"], values)
        values["Geometry Building Type Height"] = t["Geometry Building Type Height"].only(values)
        terms = list(self._household_terms(values))
        values.update(_pick(stream, [(v, w) for v, w in terms if w > 0]))
        income_2020 = [(o, p * t["Geometry Floor Area"].probability(self.c.floor_area, dict(values, **{"Income RECS2020": o})))
                       for o, p in zip(t["Income RECS2020"].options, t["Income RECS2020"].distribution(values)) if p]
        values["Income RECS2020"] = _pick(stream, income_2020)
        if self.c.occupants is None:
            values["Income RECS2015"] = _pick_row(stream, t["Income RECS2015"], values)
            values["Bedrooms"] = _pick_row(stream, t["Bedrooms"], values)
            values["Occupants"] = _pick_row(stream, t["Occupants"], values)
        else:
            joint = []
            for i15, p15 in zip(t["Income RECS2015"].options, t["Income RECS2015"].distribution(values)):
                for bed, p_bed in zip(t["Bedrooms"].options, t["Bedrooms"].distribution(values)):
                    if p15 and p_bed:
                        v = dict(values, **{"Income RECS2015": i15, "Bedrooms": bed})
                        joint.append(((i15, bed), p15 * p_bed * t["Occupants"].probability(self.c.occupants, v)))
            values["Income RECS2015"], values["Bedrooms"] = _pick(stream, [(k, w) for k, w in joint if w > 0])
            values["Occupants"] = self.c.occupants
        if self.c.hvac is None:
            for name in HVAC[:4] + ("HVAC Heating Efficiency",):
                values[name] = _pick_row(stream, t[name], values)
        else:
            values.update(zip(HVAC[:4], self.c.hvac[:4]))
            zonal = t["HVAC Has Zonal Electric Heating"]
            efficiencies = [(o, p) for o, p in zip(t["HVAC Heating Efficiency"].options, t["HVAC Heating Efficiency"].distribution(values))
                            if p and zonal.only({"HVAC Heating Efficiency": o}) == self.c.hvac[4]]
            values["HVAC Heating Efficiency"] = _pick(stream, efficiencies)
        values["HVAC Has Zonal Electric Heating"] = t["HVAC Has Zonal Electric Heating"].only(values)
        return values


def _pick(stream, choices: list):
    total = math.fsum(w for _, w in choices)
    return choices[weighted_choice(stream, [w / total for _, w in choices])][0]


def _pick_row(stream, table: Table, values: dict) -> str:
    return table.options[weighted_choice(stream, table.distribution(values))]


@lru_cache(maxsize=64)
def _posterior(conditions: Conditions) -> _Posterior:
    return _Posterior(conditions)


def characteristics_stream(unit_seed: int) -> Pcg64Stream:
    return Pcg64Stream(np.random.SeedSequence([unit_seed, STREAM_TAG]))


def sample_characteristics(conditions: Conditions, unit_seed: int) -> dict:
    """{characteristic: option} for one unit; County and PUMA are drawn but not returned."""
    stream = characteristics_stream(unit_seed)
    posterior = _posterior(conditions)
    values = posterior.draw(stream)
    tables = posterior.tables
    for name in _forward_order(tables):
        values[name] = _pick_row(stream, tables[name], values)
    for hidden in ("County and PUMA", "County", "PUMA"):
        values.pop(hidden, None)
    return values
