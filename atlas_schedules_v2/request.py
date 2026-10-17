"""Parse and validate a generator request (schema 2.0.0).

All validation happens here, once. Kernels and mixtures trust what this returns.
"""
from dataclasses import dataclass, field
from functools import lru_cache
import json
import math
from pathlib import Path

import jsonschema

from .errors import GeneratorError

SCHEMA = Path(__file__).resolve().parent / "schemas" / "request-v2.schema.json"
BASIS_UNITS = {"floor_area": "m2", "dwelling_unit": "dwelling", "person": "person", "absolute": "1"}


@dataclass
class Location:
    state: str
    latitude: float
    longitude: float
    utc_offset: float


@dataclass
class Instance:
    key: str
    program_id: str | None = None
    service_id: str | None = None
    configuration_id: str | None = None
    physical_id: str | None = None
    extent: dict = field(default_factory=dict)
    multiplicity: float = 1.0
    operating_group: str | None = None
    residents: int | None = None
    location: Location | None = None
    service_links: dict = field(default_factory=dict)
    composition_basis: str | None = None

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
    instances: list
    mixture: Mixture | None


@lru_cache(maxsize=1)
def _validator():
    return jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))


def _schema_errors(document: dict) -> None:
    errors = sorted(_validator().iter_errors(document), key=lambda e: list(e.path))
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


def parse_request(document: dict) -> Request:
    _finite(document)
    _schema_errors(document)
    instances = []
    for raw in document["instances"]:
        location = Location(**raw["location"]) if "location" in raw else None
        instances.append(Instance(
            key=raw["key"], program_id=raw.get("program_id"), service_id=raw.get("service_id"),
            configuration_id=raw.get("configuration_id"), physical_id=raw.get("physical_id"),
            extent=dict(raw.get("extent", {})), multiplicity=float(raw.get("multiplicity", 1)),
            operating_group=raw.get("operating_group"), residents=raw.get("residents"), location=location,
            service_links=dict(raw.get("service_links", {})), composition_basis=raw.get("composition_basis")))
    keys = [i.key for i in instances]
    if len(set(keys)) != len(keys):
        raise GeneratorError("duplicate_instance", "/instances", "Instance keys must be unique")
    mixture = None
    if "mixture" in document:
        raw = document["mixture"]
        mixture = Mixture(raw["program_id"], [Member(m["instance"], float(m["weight"])) for m in raw["members"]],
                          list(raw.get("services", [])), raw.get("result_basis"), raw.get("denominator"))
        _check_mixture(mixture, set(keys))
    return Request(document["seed"], document.get("residential_rng", "pcg64"), instances, mixture)


def _check_mixture(mixture: Mixture, keys: set) -> None:
    for member in mixture.members:
        if member.instance not in keys:
            raise GeneratorError("invalid_request", "/mixture/members", f"Unknown instance {member.instance!r}")
    for service in mixture.services:
        if service not in keys:
            raise GeneratorError("invalid_request", "/mixture/services", f"Unknown instance {service!r}")
    if (mixture.result_basis is None) != (mixture.denominator is None):
        raise GeneratorError("invalid_request", "/mixture", "result_basis and denominator go together")
    if mixture.services and mixture.denominator is None:
        raise GeneratorError("invalid_request", "/mixture/services", "Shared services need a result basis and denominator")
