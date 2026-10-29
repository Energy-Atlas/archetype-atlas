"""Generate a schedule bundle from a request (schema 3.0.0).

Steps:
1. parse and validate the request;
2. expand composition parents into their member programmes, and give every
   apartment unit (a ResStock multifamily unit: residential/apartment.py) its water owner;
3. derive seeds: one cumulative chain over residential units (stock dwellings
   and apartment units, including empty ones), one SHA-256 seed per commercial
   operating group;
4. build every owner (channels, and each load bound by its source magnitude or, for
   ResStock units, its annual total; budgets.py);
5. combine composition members into their parents, then apply the request mixture;
6. assemble the bundle.
"""
from dataclasses import dataclass
import math
from urllib.parse import quote

import numpy as np

from . import __version__
from .budgets import annual_target, fit_amplitude
from .commercial.sampler import load_tables, sample_operating_parameters
from .commercial.transform import Slot, transform
from .companions import companion_channels
from .errors import GeneratorError
from .mixtures import Load, Owner, mix
from .programmes import (annual_targets, configuration_people, dwelling_for, instance_channels, load_configuration,
                         load_recipe, load_service, occupant_type_probabilities, reference_locations, required_services,
                         schedules)
from .release import current
from .request import Instance, Location, Request, parse_request
from .residential.apartment import resstock_unit
from .seeds import commercial_group_seed


def schedule_id(key: str, slot: str) -> str:
    # Mixed load slots are already quoted part by part ("load/<quantity>/m3%2Fs/...").
    return "schedule:" + quote(key, safe="") + ":" + quote(slot, safe="/%")


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
        recipe = load_recipe(instance.program_id, instance.values)
        _check_links(instance, recipe)
        if recipe["kind"] == "composition":
            children = _composition_children(instance, recipe)
            parents[instance.key] = (instance, recipe, children)
            planned.extend(Planned(child, recipe=load_recipe(child.program_id, child.values), parent=instance.key)
                           for child, _ in children)
            continue
        planned.append(Planned(instance, recipe=recipe))
        if recipe["kind"] == "apartment_unit" and "floor_area" in instance.extent:
            water = Instance(key=instance.key + "/water", extent={"floor_area": instance.extent["floor_area"]},
                             physical_id=instance.key)
            planned.append(Planned(water, recipe=recipe, caller_water_of=instance.key))
    return planned, parents


def _check_links(instance: Instance, recipe: dict) -> None:
    """Every required shared service is linked, and nothing else is."""
    required = required_services(recipe)
    missing = [s for s in required if s not in instance.service_links]
    extra = [s for s in instance.service_links if s not in required]
    if missing or extra:
        raise GeneratorError("service_links", f"/instances/{instance.key}/service_links",
                             f"Link exactly the required shared services {required}; missing {missing}, "
                             f"not required {extra}")


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
    for index, ((program_id, area), values) in enumerate(zip(members, recipe["composition"]["member_values"])):
        extent = area if mode == "reference_area" else denominator * area / total
        key = f"source-member/{quote(parent.key, safe='')}/{index}/{program_id}"
        child = Instance(key=key, program_id=program_id, values=values, extent={"floor_area": extent},
                         operating_group=parent.group)
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
            configuration_id = item.instance.configuration_id
        elif item.recipe and item.recipe["kind"] == "commercial" and not item.caller_water_of:
            configuration_id = item.recipe["commercial"]["configuration_id"]
        else:
            continue
        building_type = load_configuration(configuration_id)["building_type"]
        if building_types.setdefault(item.instance.group, building_type) != building_type:
            raise GeneratorError("operating_group_conflict", f"/instances/{item.instance.key}/operating_group",
                                 "One operating group cannot mix sampling building types")
    return {group: sample_operating_parameters(load_tables(bt), bt, commercial_group_seed(master, group))
            for group, bt in building_types.items()}


# --------------------------------------------------------------------- owners
def _loads(recipe: dict, channels: dict) -> list:
    """ResStock dwellings hold each annual total and fit the design level (OpenStudio-HPXML);
    commercial and fixed programmes bind the source magnitude to the generated schedule, as
    ComStock does, so the annual total follows the draw (O15)."""
    loads = []
    annual = recipe["kind"] == "residential"
    for demand, target in zip(recipe["demands"], annual_targets(recipe) if annual else [None] * len(recipe["demands"])):
        slot, unit = demand["slot"], demand["unit"]
        if annual:
            total, amplitude = target, fit_amplitude(target, unit, channels[slot])
        else:
            total, amplitude = annual_target(demand["value"], unit, channels[slot]), demand["value"]
        loads.append(Load(slot, demand["quantity"], unit, demand["basis"], demand["fuel"], demand["host"],
                          total, amplitude, demand.get("heat_fractions")))
    return loads


def _slot_units(recipe: dict) -> dict:
    return {s["slot"]: s["unit"] for s in recipe["slots"]}


def _unit_location(instance: Instance) -> Location:
    if instance.reference_location:
        row = reference_locations()[instance.reference_location]
        return Location(row["state"], row["latitude"], row["longitude"], row["utc_offset"], weather_id=row["weather_id"])
    if instance.location is None:
        raise GeneratorError("missing_input", f"/instances/{instance.key}/location",
                             "Apartment units need a location or reference_location")
    return instance.location


def _resstock_unit_owner(item: Planned, request: Request, seeds: dict, units: dict) -> Owner:
    """A ResStock apartment unit (residential/apartment.py); its draw is kept for the unit's water owner."""
    instance, recipe = item.instance, item.recipe
    if instance.residents is None:
        raise GeneratorError("missing_input", f"/instances/{instance.key}/residents", "Apartment units need residents")
    if instance.extent.get("floor_area", 0) <= 0:
        raise GeneratorError("missing_input", f"/instances/{instance.key}/extent",
                             "ResStock apartment units need their floor area")
    location = _unit_location(instance)
    shares = occupant_type_probabilities(location.state, request.occupancy)
    unit = resstock_unit(recipe["resstock_unit"], location, instance.extent["floor_area"], instance.residents,
                         seeds[instance.key], request.residential_rng, shares)
    units[instance.key] = unit
    schedule_units = {"activity": "W/person", "heating_setpoint": "C", "cooling_setpoint": "C"}
    schedules_out = {slot: (schedule_units.get(slot, "fraction"), values) for slot, values in unit.channels.items()}
    generation = {"unit_seed": seeds[instance.key], "occupant_type_probabilities": shares, **unit.generation}
    return Owner(key=instance.key, kind="program", program_id=instance.program_id, values=recipe["values"],
                 schedules=schedules_out, loads=unit.loads, controls=unit.controls,
                 extent={**instance.extent, "dwelling_unit": 1.0}, multiplicity=instance.multiplicity, generation=generation)


def _resstock_water_owner(item: Planned, units: dict) -> Owner:
    """Ruling 185 (P2): prototype volume per design person x residents, timed by the unit's fixture events."""
    water = item.recipe["caller_water"]
    total, shape = units[item.caller_water_of].water
    load = Load("hot_water_volume", "hot_water_volume", "m3/s/dwelling", "dwelling_unit", "water", "building_service",
                total, fit_amplitude(total, "m3/s/dwelling", shape))
    schedules_out = {"hot_water_volume": ("fraction", shape)}
    controls = []
    for slot, (quantity, unit, value) in water["controls"].items():
        schedules_out[slot] = (unit, np.full(8760, value))
        controls.append({"slot": slot, "quantity": quantity, "unit": unit})
    return Owner(key=item.instance.key, kind="caller_water", service_id=water["service_id"], schedules=schedules_out,
                 loads=[load], controls=controls, extent={**item.instance.extent, "dwelling_unit": 1.0},
                 physical_identity=("caller_water", item.caller_water_of),
                 generation={"unit": item.caller_water_of, "basis": "residents x prototype volume per design person"})


def _programme_owner(item: Planned, request: Request, seeds: dict, operating: dict) -> Owner:
    instance, recipe = item.instance, item.recipe
    kind = recipe["kind"]
    generation = {}
    group_operating = operating.get(instance.group) if kind == "commercial" else None
    channels = instance_channels(recipe, operating=group_operating, unit_seed=seeds.get(instance.key),
                                 rng_mode=request.residential_rng, reference_location=instance.reference_location,
                                 flat_days=request.flat_days, occupancy=request.occupancy)
    if kind == "commercial":
        generation["operating_group"] = instance.group
    if kind == "residential":
        generation["unit_seed"] = seeds.get(instance.key)
        shares = occupant_type_probabilities(dwelling_for(recipe, instance.reference_location).state, request.occupancy)
        generation["occupant_type_probabilities"] = shares
    units = _slot_units(recipe)
    schedules_out = {slot: (units.get(slot, "C"), values) for slot, values in channels.items()}
    return Owner(key=instance.key, kind="program", program_id=instance.program_id, values=recipe["values"],
                 schedules=schedules_out, loads=_loads(recipe, channels), controls=recipe["controls"],
                 extent=instance.extent, multiplicity=instance.multiplicity, generation=generation)


def _service_owner(item: Planned, operating: dict) -> Owner:
    instance, service = item.instance, item.service
    configuration = service["configurations"].get(instance.configuration_id)
    if configuration is None:
        raise GeneratorError("unsupported_binding", f"/instances/{instance.key}/configuration_id",
                             f"Service {instance.service_id} has no variant for {instance.configuration_id}")
    table = schedules()
    demand = service["demand"]
    building = load_configuration(instance.configuration_id)
    channels = transform({"hot_water_volume": Slot(table[configuration["schedule"]], "hours")},
                         configuration_people(building), operating[instance.group],
                         invert_rule_days=building["invert_rule_days"])
    channels.update(companion_channels(configuration["companions"], table, None))
    if demand["basis"] not in instance.extent:
        raise GeneratorError("invalid_request", f"/instances/{instance.key}/extent", f"Needs a {demand['basis']} extent")
    # The source peak flow binds the sampled schedule; the annual volume follows the draw (O15).
    total = annual_target(demand["value"], demand["unit"], channels["hot_water_volume"])
    load = Load("hot_water_volume", demand["quantity"], demand["unit"], demand["basis"], demand["fuel"],
                demand["host"], total, demand["value"])
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
    # ADR 0023: with a denominator, weights are participation multipliers on
    # explicit extents; without one, they are normalised shares.
    if spec.denominator is None and spec.members and abs(math.fsum(m.weight for m in spec.members) - 1) > 1e-12:
        raise GeneratorError("invalid_mixture", "/mixture/members",
                             "Without a denominator, member weights are shares and must sum to one")
    for member in spec.members:
        instance = instances[member.instance]
        if (spec.denominator is not None and instance.program_id
                and load_recipe(instance.program_id, instance.values)["kind"] == "composition"
                and (instance.composition_basis or "reference_area") == "reference_area"):
            raise GeneratorError("invalid_mixture", f"/instances/{instance.key}/composition_basis",
                                 "A reference_area parent has no caller extent; "
                                 "use caller_area to mix it with a denominator")
    members = [(owners[m.instance], m.weight) for m in spec.members]
    services = [owners[key] for key in spec.services]
    for owner, weight in members:
        if weight > 0:
            services.extend(_linked_services(owner, instances, owners))
            if owner.key in water_by_unit:
                services.append(water_by_unit[owner.key])
    if services and spec.denominator is None:
        raise GeneratorError("invalid_mixture", "/mixture",
                             "Shared services (listed, linked or apartment water) need a result basis and denominator")
    return mix("mixture/" + spec.program_id, spec.program_id, members, services, spec.result_basis, spec.denominator)


def _parent_owner(parent: Instance, recipe: dict, children: list, owners: dict) -> Owner:
    denominator = parent.extent.get("floor_area") if parent.composition_basis == "caller_area" else \
        float(np.sum([area for _, area in recipe["composition"]["members"]]))
    members = [(owners[child.key], 1.0) for child, _ in children]
    owner = mix(parent.key, parent.program_id, members, [], "floor_area", denominator,
                setpoint_weights=[weight for _, weight in children], kind="program")
    owner.values = recipe["values"]
    owner.extent = parent.extent
    owner.multiplicity = parent.multiplicity
    return owner


# --------------------------------------------------------------------- bundle
def _owner_record(owner: Owner) -> dict:
    return {
        "key": owner.key, "kind": owner.kind, "program_id": owner.program_id, "values": owner.values,
        "service_id": owner.service_id, "extent": owner.extent, "multiplicity": owner.multiplicity,
        "schedules": {slot: schedule_id(owner.key, slot) for slot in owner.schedules},
        "loads": [{"slot": l.slot, "quantity": l.quantity, "unit": l.unit, "basis": l.basis, "fuel": l.fuel,
                   "host": l.host, "annual_total": l.annual_total, "amplitude": l.amplitude,
                   "heat_fractions": l.heat_fractions} for l in owner.loads],
        "controls": [{k: c[k] for k in ("slot", "quantity", "unit")} for c in owner.controls if c["slot"] in owner.schedules],
        "generation": owner.generation,
    }


def generate(document: dict, *, residential_rng: str = "pcg64", flat_days: str = "documented") -> dict:
    """Generate the bundle for a request document.

    The keyword arguments are validation-only; requests cannot choose them.
    residential_rng "ruby_mt" (R1) replays Ruby streams, so native ResStock
    captures and the legacy generator can be checked draw for draw. Requests
    always use "pcg64" (R2); see docs/validation/residential-rng-equivalence.md.
    flat_days "native" reproduces ComStock clearing flat days in base-to-peak,
    for the native answer keys. Requests always use "documented"; see
    commercial/base_peak.py.
    """
    request = parse_request(document, residential_rng, flat_days)
    planned, parents = _expand(request)
    seeds = _unit_seeds(request.seed, planned)
    operating = _group_operating(request.seed, planned)
    owners = {}
    water_by_unit = {}
    units = {}
    for item in planned:
        if item.service:
            owner = _service_owner(item, operating)
        elif item.caller_water_of:
            owner = _resstock_water_owner(item, units)
            water_by_unit[item.caller_water_of] = owner
        elif item.recipe["kind"] == "apartment_unit":
            owner = _resstock_unit_owner(item, request, seeds, units)
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
    release = current()
    return {
        "schema_version": "3.0.0",
        "generator_version": __version__,
        "release": {"version": release.version, "manifest_sha256": release.manifest_sha256,
                    "generation_schema_version": release.manifest["generation"]["schema_version"]},
        "seed": request.seed,
        "residential_rng": request.residential_rng,
        "flat_days": request.flat_days,
        "occupancy": {"mix": request.occupancy[0], "window": request.occupancy[1]},
        "calendar": {"year": 2007, "clock": "local_standard_time", "timestep_minutes": 60},
        "schedules": bundle_schedules,
        "owners": [_owner_record(o) for o in owners.values()],
        "mixture": _owner_record(mixed) if mixed else None,
        "operating_groups": operating,
        "unit_seeds": seeds,
    }
