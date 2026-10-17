"""Generate a schedule bundle from a request (schema 2.0.0).

Steps:
1. parse and validate the request;
2. expand composition parents into their member programmes, and give every
   apartment unit with a floor area its caller-unit water owner;
3. derive seeds: one cumulative chain over residential units (stock dwellings
   and apartment units, including empty ones), one SHA-256 seed per commercial
   operating group;
4. build every owner (channels, annual targets, fitted amplitudes);
5. combine composition members into their parents, then apply the request mixture;
6. assemble the bundle.
"""
from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
from urllib.parse import quote

import numpy as np

from . import __version__
from .budgets import annual_target, fit_amplitude
from .calendar import evaluate_rules
from .commercial.sampler import load_tables, sample_operating_parameters
from .commercial.transform import Slot, transform
from .companions import companion_channels
from .errors import GeneratorError
from .mixtures import Load, Owner, mix, scale
from .programmes import (annual_targets, configuration_people, instance_channels, load_configuration,
                         load_recipe, schedules)
from .request import Instance, Request, parse_request
from .residential.generate import Dwelling, generate_occupancy_and_lighting
from .seeds import commercial_group_seed

DATA = Path(__file__).resolve().parent / "data"


@lru_cache(maxsize=None)
def load_service(service_id: str) -> dict:
    path = DATA / "services" / f"{service_id}.json"
    if not path.exists():
        raise GeneratorError("unsupported_binding", "/service_id", f"No shared service {service_id!r}")
    return json.loads(path.read_text(encoding="utf-8"))


def schedule_id(key: str, slot: str) -> str:
    return "schedule:" + quote(key, safe="") + ":" + quote(slot, safe="")


# ----------------------------------------------------------------- expansion
@dataclass
class Planned:
    instance: Instance
    recipe: dict | None = None
    service: dict | None = None
    caller_water_of: str | None = None   # apartment unit key this water owner belongs to
    parent: str | None = None            # composition parent key


def _expand(request: Request) -> tuple[list, dict]:
    """Planned owners in generation order, and composition parents {key: (instance, recipe, children)}."""
    planned, parents = [], {}
    for instance in request.instances:
        if instance.service_id:
            planned.append(Planned(instance, service=load_service(instance.service_id)))
            continue
        recipe = load_recipe(instance.program_id)
        if recipe["kind"] == "composition":
            children = _composition_children(instance, recipe)
            parents[instance.key] = (instance, recipe, children)
            planned.extend(Planned(child, recipe=load_recipe(child.program_id), parent=instance.key) for child, _ in children)
            continue
        planned.append(Planned(instance, recipe=recipe))
        if recipe["kind"] == "apartment_unit" and "floor_area" in instance.extent:
            water = Instance(key=instance.key + "/water", extent={"floor_area": instance.extent["floor_area"]},
                             physical_id=instance.key)
            planned.append(Planned(water, recipe=recipe, caller_water_of=instance.key))
    return planned, parents


def _composition_children(parent: Instance, recipe: dict) -> list:
    """(child instance, setpoint weight E_i / D) for each member, areas A_i, f_i = A_i / sum A."""
    members = recipe["composition"]["members"]
    total = float(np.sum([area for _, area in members]))
    mode = parent.composition_basis or "reference_area"
    if mode == "caller_area":
        if "floor_area" not in parent.extent or parent.extent["floor_area"] <= 0:
            raise GeneratorError("invalid_request", f"/instances/{parent.key}/extent",
                                 "caller_area needs the parent floor area")
        denominator = parent.extent["floor_area"]
    else:
        if parent.extent:
            raise GeneratorError("invalid_request", f"/instances/{parent.key}/extent",
                                 "reference_area parents take no caller extent")
        denominator = total
    children = []
    for index, (program_id, area) in enumerate(members):
        extent = area if mode == "reference_area" else denominator * area / total
        key = f"source-member/{quote(parent.key, safe='')}/{index}/{program_id}"
        child = Instance(key=key, program_id=program_id, extent={"floor_area": extent}, operating_group=parent.group)
        children.append((child, extent / denominator))
    return children


# ---------------------------------------------------------------------- seeds
def _unit_seeds(master: int, planned: list) -> dict:
    """Cumulative chain over residential actors in order (BuildResidentialScheduleFile measure.rb:162)."""
    seeds = {}
    seed = master
    position = 0
    for item in planned:
        recipe = item.recipe
        if item.caller_water_of or recipe is None or recipe["kind"] not in ("residential", "apartment_unit"):
            continue
        position += 1
        seed *= position
        seeds[item.instance.key] = seed
    return seeds


def _group_operating(master: int, planned: list) -> dict:
    """Sampled operating parameters per commercial operating group."""
    building_types = {}
    for item in planned:
        if item.service:
            configuration = item.service["configurations"][item.instance.configuration_id]
            building_types.setdefault(item.instance.group, load_configuration(item.instance.configuration_id)["building_type"])
        elif item.recipe and item.recipe["kind"] == "commercial" and not item.caller_water_of:
            building_type = load_configuration(item.recipe["commercial"]["configuration_id"])["building_type"]
            if building_types.setdefault(item.instance.group, building_type) != building_type:
                raise GeneratorError("operating_group_conflict", f"/instances/{item.instance.key}/operating_group",
                                     "One operating group cannot mix sampling building types")
    return {group: sample_operating_parameters(load_tables(bt), bt, commercial_group_seed(master, group))
            for group, bt in building_types.items()}


# --------------------------------------------------------------------- owners
def _loads(recipe_demands: list, channels: dict, targets: list) -> list:
    loads = []
    for demand, total in zip(recipe_demands, targets):
        slot = demand["slot"]
        loads.append(Load(slot, demand["quantity"], demand["unit"], demand["basis"], demand["fuel"], demand["host"],
                          total, fit_amplitude(total, demand["unit"], channels[slot]), demand.get("heat_fractions")))
    return loads


def _slot_units(recipe: dict) -> dict:
    return {s["slot"]: s["unit"] for s in recipe["slots"]}


def _programme_owner(item: Planned, request: Request, seeds: dict, operating: dict) -> Owner:
    instance, recipe = item.instance, item.recipe
    kind = recipe["kind"]
    targets = annual_targets(recipe)
    generation = {}
    if kind == "apartment_unit":
        channels = _apartment_channels(instance, recipe, seeds.get(instance.key), request.residential_rng)
        generation["unit_seed"] = seeds.get(instance.key)
    else:
        group_operating = operating.get(instance.group) if kind == "commercial" else None
        channels = instance_channels(recipe, operating=group_operating, unit_seed=seeds.get(instance.key),
                                     rng_mode=request.residential_rng)
        if kind == "commercial":
            generation["operating_group"] = instance.group
        if kind == "residential":
            generation["unit_seed"] = seeds.get(instance.key)
    units = _slot_units(recipe)
    schedules_out = {slot: (units.get(slot, "C"), values) for slot, values in channels.items()}
    return Owner(key=instance.key, kind="program", program_id=instance.program_id, schedules=schedules_out,
                 loads=_loads(recipe["demands"], channels, targets), controls=recipe["controls"],
                 extent=instance.extent, multiplicity=instance.multiplicity, generation=generation)


def _apartment_channels(instance: Instance, recipe: dict, unit_seed: int | None, rng_mode: str) -> dict:
    table = schedules()
    channels = {s["slot"]: evaluate_rules(table[s["schedule"]])[0] for s in recipe["slots"] if s["schedule"]}
    if instance.residents is None:
        raise GeneratorError("missing_input", f"/instances/{instance.key}/residents", "Apartment units need residents")
    if instance.residents > 0:
        if instance.location is None:
            raise GeneratorError("missing_input", f"/instances/{instance.key}/location",
                                 "Occupied apartment units need a location")
        where = instance.location
        dwelling = Dwelling(instance.residents, where.state, where.latitude, where.longitude, where.utc_offset)
        timing = generate_occupancy_and_lighting(dwelling, unit_seed, rng_mode)
        for slot, kernel_channel in recipe["unit_timing"].items():
            channels[slot] = timing[kernel_channel]
    channels.update(companion_channels(recipe["companions"], table, None))
    return channels


def _caller_water_owner(item: Planned) -> Owner:
    """Fixed apartment hot water: source density x the unit's own floor area, no transform."""
    water = item.recipe["caller_water"]
    shape = evaluate_rules(schedules()[water["schedule"]])[0]
    total = annual_target(water["density"], water["density_unit"], shape)
    load = Load("hot_water_volume", "hot_water_volume", water["density_unit"], "floor_area", "water",
                "building_service", total, fit_amplitude(total, water["density_unit"], shape))
    schedules_out = {"hot_water_volume": ("fraction", shape)}
    controls = []
    for slot, (quantity, unit, value) in water["controls"].items():
        schedules_out[slot] = (unit, np.full(8760, value))
        controls.append({"slot": slot, "quantity": quantity, "unit": unit})
    return Owner(key=item.instance.key, kind="caller_water", service_id=water["service_id"], schedules=schedules_out,
                 loads=[load], controls=controls, extent=item.instance.extent,
                 physical_identity=("caller_water", item.caller_water_of),
                 generation={"unit": item.caller_water_of})


def _service_owner(item: Planned, operating: dict) -> Owner:
    instance, service = item.instance, item.service
    configuration = service["configurations"].get(instance.configuration_id)
    if configuration is None:
        raise GeneratorError("unsupported_binding", f"/instances/{instance.key}/configuration_id",
                             f"Service {instance.service_id} has no variant for {instance.configuration_id}")
    table = schedules()
    demand = service["demand"]
    reference = evaluate_rules(table[configuration["schedule"]])[0]
    total = annual_target(demand["value"], demand["unit"], reference)
    building = load_configuration(instance.configuration_id)
    channels = transform({"hot_water_volume": Slot(table[configuration["schedule"]], "hours")},
                         configuration_people(building), operating[instance.group],
                         invert_rule_days=building["invert_rule_days"])
    channels.update(companion_channels(configuration["companions"], table, None))
    if demand["basis"] not in instance.extent:
        raise GeneratorError("invalid_request", f"/instances/{instance.key}/extent", f"Needs a {demand['basis']} extent")
    load = Load("hot_water_volume", demand["quantity"], demand["unit"], demand["basis"], demand["fuel"],
                demand["host"], total, fit_amplitude(total, demand["unit"], channels["hot_water_volume"]))
    units = {c["slot"]: c["unit"] for c in service["controls"]}
    schedules_out = {slot: (units.get(slot, "fraction"), values) for slot, values in channels.items()}
    return Owner(key=instance.key, kind="physical_service", service_id=instance.service_id, schedules=schedules_out,
                 loads=[load], controls=service["controls"], extent=instance.extent,
                 physical_identity=("physical_service", instance.physical_id),
                 generation={"operating_group": instance.group, "configuration_id": instance.configuration_id})


# ---------------------------------------------------------------------- mixing
def _linked_services(member: Owner, instances: dict, owners: dict) -> list:
    instance = instances.get(member.key)
    if instance is None:
        return []
    return [owners[key] for key in instance.service_links.values()]


def _request_mixture(request: Request, owners: dict, instances: dict, water_by_unit: dict) -> Owner:
    spec = request.mixture
    if spec.members and abs(sum(m.weight for m in spec.members) - 1) > 1e-12:
        raise GeneratorError("invalid_mixture", "/mixture/members", "Member weights must sum to one")
    members = [(owners[m.instance], m.weight) for m in spec.members]
    services = [owners[key] for key in spec.services]
    for owner, weight in members:
        if weight > 0:
            services.extend(_linked_services(owner, instances, owners))
            if owner.key in water_by_unit:
                services.append(water_by_unit[owner.key])
    return mix("mixture/" + spec.program_id, spec.program_id, members, services, spec.result_basis, spec.denominator)


def _parent_owner(parent: Instance, recipe: dict, children: list, owners: dict) -> Owner:
    denominator = parent.extent.get("floor_area") if parent.composition_basis == "caller_area" else \
        float(np.sum([area for _, area in recipe["composition"]["members"]]))
    members = [(owners[child.key], 1.0) for child, _ in children]
    owner = mix(parent.key, parent.program_id, members, [], "floor_area", denominator,
                setpoint_weights=[weight for _, weight in children], kind="program")
    owner.extent = parent.extent
    owner.multiplicity = parent.multiplicity
    return owner


# --------------------------------------------------------------------- bundle
def _owner_record(owner: Owner) -> dict:
    return {
        "key": owner.key, "kind": owner.kind, "program_id": owner.program_id, "service_id": owner.service_id,
        "extent": owner.extent, "multiplicity": owner.multiplicity,
        "schedules": {slot: schedule_id(owner.key, slot) for slot in owner.schedules},
        "loads": [{"slot": l.slot, "quantity": l.quantity, "unit": l.unit, "basis": l.basis, "fuel": l.fuel,
                   "host": l.host, "annual_total": l.annual_total, "amplitude": l.amplitude,
                   "heat_fractions": l.heat_fractions} for l in owner.loads],
        "controls": [{k: c[k] for k in ("slot", "quantity", "unit")} for c in owner.controls if c["slot"] in owner.schedules],
        "generation": owner.generation,
    }


def generate(document: dict) -> dict:
    request = parse_request(document)
    planned, parents = _expand(request)
    seeds = _unit_seeds(request.seed, planned)
    operating = _group_operating(request.seed, planned)
    owners = {}
    water_by_unit = {}
    for item in planned:
        if item.service:
            owner = _service_owner(item, operating)
        elif item.caller_water_of:
            owner = _caller_water_owner(item)
            water_by_unit[item.caller_water_of] = owner
        else:
            owner = _programme_owner(item, request, seeds, operating)
        owners[owner.key] = owner
    for key, (parent, recipe, children) in parents.items():
        owners[key] = _parent_owner(parent, recipe, children, owners)
    instances = {i.key: i for i in request.instances}
    mixed = _request_mixture(request, owners, instances, water_by_unit) if request.mixture else None
    every = list(owners.values()) + ([mixed] if mixed else [])
    bundle_schedules = {}
    for owner in every:
        for slot, (unit, values) in owner.schedules.items():
            bundle_schedules[schedule_id(owner.key, slot)] = {"unit": unit, "values": np.asarray(values).tolist()}
    return {
        "schema_version": "2.0.0",
        "generator_version": __version__,
        "seed": request.seed,
        "residential_rng": request.residential_rng,
        "calendar": {"year": 2007, "clock": "local_standard_time", "timestep_minutes": 60},
        "schedules": bundle_schedules,
        "owners": [_owner_record(o) for o in owners.values()],
        "mixture": _owner_record(mixed) if mixed else None,
        "operating_groups": operating,
        "unit_seeds": seeds,
    }
