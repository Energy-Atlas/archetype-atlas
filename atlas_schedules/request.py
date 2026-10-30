"""Parse and validate a generator request (schema 4.0.0).

All validation happens here, once. Kernels and mixtures trust what this returns.
4.0.0 (ADR 0051) names programmes and shared services by atlas release ID, a programme with
its view (`values`: source or filled). The definition IDs of 3.0.0 requests (`program-…`,
`service-…`) are refused: `atlas-schedules translate` rewrites such a request through the
release's definition map. 3.0.0 kept, for ResStock apartment units, `residents: "resstock"`
and the location's `climate_zone` and `weather_id` (ADR 0047); those fields are unchanged.
"""
from dataclasses import dataclass, field
from functools import lru_cache
import json
import math
from pathlib import Path

import jsonschema

from . import REQUEST_SCHEMA_VERSION
from .commercial.base_peak import FLAT_DAY_MODES
from .errors import GeneratorError
from .residential.rng import MODES
from .seeds import check_master_seed

SCHEMAS = {REQUEST_SCHEMA_VERSION: Path(__file__).resolve().parent / "schemas" / "request-v4.schema.json"}
BASIS_UNITS = {"floor_area": "m2", "dwelling_unit": "dwelling", "person": "person", "absolute": "1"}
DEFINITION_PREFIXES = ("program-", "service-", "schedule-")
TRANSLATE = ("Definition IDs (program-..., service-...) are generator 3.0.0's; generator 4.0.0 takes atlas release IDs "
             "(ADR 0051). Rewrite the request with `atlas-schedules translate request.json` "
             "(atlas_schedules.release.translate).")


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
    values: str | None = None             # programme view: "source" or "filled" (ADR 0051); default per program
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
    schema_version: str = REQUEST_SCHEMA_VERSION


@lru_cache(maxsize=None)
def _validator(version: str):
    return jsonschema.Draft202012Validator(json.loads(SCHEMAS[version].read_text(encoding="utf-8")))


def _definition_ids(document: dict) -> None:
    """A 3.0.0 request's definition IDs get the translation message, not a pattern error."""
    for index, raw in enumerate(document.get("instances", []) if isinstance(document.get("instances"), list) else []):
        if not isinstance(raw, dict):
            continue
        for key in ("program_id", "service_id"):
            if isinstance(raw.get(key), str) and raw[key].startswith(DEFINITION_PREFIXES):
                raise GeneratorError("invalid_request", f"/instances/{index}/{key}", f"{raw[key]!r}: {TRANSLATE}")
        for linked in (raw.get("service_links") or {}) if isinstance(raw.get("service_links"), dict) else {}:
            if isinstance(linked, str) and linked.startswith(DEFINITION_PREFIXES):
                raise GeneratorError("invalid_request", f"/instances/{index}/service_links/{linked}", TRANSLATE)


def _schema_errors(document: dict) -> None:
    version = document.get("schema_version") if isinstance(document, dict) else None
    if version not in SCHEMAS:
        message = f"Supported versions are {sorted(SCHEMAS)}"
        if version == "3.0.0":
            message += ". " + TRANSLATE
        raise GeneratorError("invalid_request", "/schema_version", message)
    _definition_ids(document)
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
