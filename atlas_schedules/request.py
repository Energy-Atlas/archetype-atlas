"""Parse and validate a generator request (schema 3.0.0).

All validation happens here, once. Kernels and mixtures trust what this returns.
3.0.0 adds, for ResStock apartment units, `residents: "resstock"` and the location's
`climate_zone` and `weather_id`; 2.0.0 requests are no longer accepted (ADR 0047). Programs and
services are named by atlas release ID, a program with its view (`values`, ADR 0049).
"""
from dataclasses import dataclass, field
from functools import lru_cache
import json
import math
from pathlib import Path

import jsonschema

from .commercial.base_peak import FLAT_DAY_MODES
from .errors import GeneratorError
from .residential.rng import MODES
from .seeds import check_master_seed

SCHEMAS = {"3.0.0": Path(__file__).resolve().parent / "schemas" / "request-v3.schema.json"}
BASIS_UNITS = {"floor_area": "m2", "dwelling_unit": "dwelling", "person": "person", "absolute": "1"}


@dataclass
class Location:
    state: str
    latitude: float
    longitude: float
    utc_offset: float
    climate_zone: str | None = None
    weather_id: str | None = None


@dataclass
class Instance:
    key: str
    program_id: str | None = None
    values: str | None = None             # programme view: "source" or "filled" (ADR 0049); default per program
    service_id: str | None = None
    configuration_id: str | None = None
    physical_id: str | None = None
    extent: dict = field(default_factory=dict)
    multiplicity: float = 1.0
    operating_group: str | None = None
    residents: int | str | None = None   # "resstock": ResStock draws them (3.0.0)
    location: Location | None = None
    service_links: dict = field(default_factory=dict)
    composition_basis: str | None = None
    reference_location: str | None = None

    @property
    def group(self) -> str:
        """Effective operating group: the declared group or the instance's own key."""
        return self.operating_group or self.key


@dataclass
class Member:
    instance: str
    weight: float


@dataclass
class Mixture:
    program_id: str
    members: list
    services: list
    result_basis: str | None
    denominator: float | None


@dataclass
class Request:
    seed: int
    residential_rng: str
    flat_days: str
    instances: list
    mixture: Mixture | None
    occupancy: tuple = ("state", "2003-2019")   # (mix, ATUS window), residential/occupancy.py
    schema_version: str = "3.0.0"


@lru_cache(maxsize=None)
def _validator(version: str):
    return jsonschema.Draft202012Validator(json.loads(SCHEMAS[version].read_text(encoding="utf-8")))


def _schema_errors(document: dict) -> None:
    version = document.get("schema_version") if isinstance(document, dict) else None
    if version not in SCHEMAS:
        raise GeneratorError("invalid_request", "/schema_version", f"Supported versions are {sorted(SCHEMAS)}")
    errors = sorted(_validator(version).iter_errors(document), key=lambda e: list(e.path))
    if errors:
        first = errors[0]
        path = "/" + "/".join(str(p) for p in first.path)
        raise GeneratorError("invalid_request", path, first.message)


def _finite(document) -> None:
    if isinstance(document, float) and not math.isfinite(document):
        raise GeneratorError("invalid_request", "/", "Numbers must be finite")
    if isinstance(document, dict):
        for value in document.values():
            _finite(value)
    elif isinstance(document, list):
        for value in document:
            _finite(value)


def parse_request(document: dict, residential_rng: str = "pcg64", flat_days: str = "documented") -> Request:
    if residential_rng not in MODES:
        raise GeneratorError("invalid_request", "/residential_rng", f"Unknown stream mode {residential_rng!r}")
    if flat_days not in FLAT_DAY_MODES:
        raise GeneratorError("invalid_request", "/flat_days", f"Unknown flat-day mode {flat_days!r}")
    _finite(document)
    _schema_errors(document)
    check_master_seed(document["seed"])  # JSON Schema accepts 42.0 as an integer
    instances = []
    for raw in document["instances"]:
        location = Location(**raw["location"]) if "location" in raw else None
        instances.append(Instance(
            key=raw["key"], program_id=raw.get("program_id"), values=raw.get("values"), service_id=raw.get("service_id"),
            configuration_id=raw.get("configuration_id"), physical_id=raw.get("physical_id"),
            extent=dict(raw.get("extent", {})), multiplicity=float(raw.get("multiplicity", 1)),
            operating_group=raw.get("operating_group"), residents=raw.get("residents"), location=location,
            service_links=dict(raw.get("service_links", {})), composition_basis=raw.get("composition_basis"),
            reference_location=raw.get("reference_location")))
    for instance in instances:
        if instance.values and not instance.program_id:
            raise GeneratorError("invalid_request", f"/instances/{instance.key}/values", "Only programmes take values")
    keys = [i.key for i in instances]
    if len(set(keys)) != len(keys):
        raise GeneratorError("duplicate_instance", "/instances", "Instance keys must be unique")
    services = {i.key: i for i in instances if i.service_id}
    for instance in instances:
        for service_id, target in instance.service_links.items():
            if target not in services or services[target].service_id != service_id:
                raise GeneratorError("invalid_request", f"/instances/{instance.key}/service_links/{service_id}",
                                     f"{target!r} is not a shared-service instance of {service_id}")
    mixture = None
    if "mixture" in document:
        raw = document["mixture"]
        mixture = Mixture(raw["program_id"], [Member(m["instance"], float(m["weight"])) for m in raw["members"]],
                          list(raw.get("services", [])), raw.get("result_basis"), raw.get("denominator"))
        _check_mixture(mixture, set(keys), set(services))
    occupancy = document.get("occupancy", {})
    return Request(document["seed"], residential_rng, flat_days, instances, mixture,
                   (occupancy.get("mix", "state"), occupancy.get("window", "2003-2019")), document["schema_version"])


def _check_mixture(mixture: Mixture, keys: set, service_keys: set) -> None:
    for member in mixture.members:
        if member.instance not in keys:
            raise GeneratorError("invalid_request", "/mixture/members", f"Unknown instance {member.instance!r}")
    for service in mixture.services:
        if service not in service_keys:
            raise GeneratorError("invalid_request", "/mixture/services", f"{service!r} is not a shared-service instance")
    if (mixture.result_basis is None) != (mixture.denominator is None):
        raise GeneratorError("invalid_request", "/mixture", "result_basis and denominator go together")
    if mixture.services and mixture.denominator is None:
        raise GeneratorError("invalid_request", "/mixture/services", "Shared services need a result basis and denominator")
