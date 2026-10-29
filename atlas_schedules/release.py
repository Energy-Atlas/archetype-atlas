"""Read an atlas release: program records, folder tables and generation blocks (ADR 0049).

The generator holds no copy of release values. It reads them from a releases folder that
holds the release folders side by side (`v2.0.0/`, `v2.1.0/`): the source tree's
`data/atlas-releases`, or the extracted `v2.1.0` data archive. The folder is
`set_releases()`, else the `ATLAS_RELEASES` environment variable, else the source tree's.

A release is a whole snapshot (2.0.0) or a delta on a base (2.1.0). A delta's manifest
names its base by release and manifest hash, lists its own files, and lists the base files
it retires. A path resolves to the delta's file, else the base's unless retired. Each
folder's `generation.json` holds its programs' generation blocks, its services' blocks and
its building configurations; a program record reads with its block as `generation`.
"""
from functools import cached_property, lru_cache
import hashlib
import json
import os
from pathlib import Path

from .errors import GeneratorError

READS = {"release": "2", "generation": "1"}   # major versions this generator reads
SOURCE_TREE = Path(__file__).resolve().parents[1] / "data" / "atlas-releases"
_ROOT: Path | None = None


def set_releases(path) -> None:
    """Read releases from this folder from now on."""
    global _ROOT
    _ROOT = Path(path)
    current.cache_clear()


def releases_folder() -> Path:
    if _ROOT is not None:
        return _ROOT
    if os.environ.get("ATLAS_RELEASES"):
        return Path(os.environ["ATLAS_RELEASES"])
    return SOURCE_TREE


def read_bytes(path: Path) -> bytes:
    """A file's bytes; on Windows, past MAX_PATH through the extended-length prefix."""
    if os.name == "nt":
        absolute = os.path.abspath(path)
        if len(absolute) >= 240 and not absolute.startswith("\\\\?\\"):
            path = "\\\\?\\" + absolute
    with open(path, "rb") as handle:
        return handle.read()


def _version(name: str) -> tuple:
    return tuple(int(part) for part in name.removeprefix("v").split("."))


class Release:
    """One release folder, resolved over its base when it is a delta."""

    def __init__(self, folder: Path, generation: dict | None = None):
        self.folder = Path(folder)
        raw = read_bytes(self.folder / "manifest.json")
        self.manifest = json.loads(raw)
        self.manifest_sha256 = hashlib.sha256(raw).hexdigest()
        self.version = self.manifest["release"]
        base = self.manifest.get("base_release")
        self.base = None
        if base:
            self.base = Release(self.folder.parent / f"v{base['release']}")
            if self.base.manifest_sha256 != base["manifest_sha256"]:
                raise GeneratorError("release", "/base_release",
                                     f"Release {self.version} expects base {base['release']} with manifest "
                                     f"{base['manifest_sha256']}, found {self.base.manifest_sha256}")
        self.retired = set(self.manifest.get("retired", []))
        self._generation = generation   # {folder: generation.json document}, to check blocks before they are written

    @cached_property
    def paths(self) -> dict:
        """{release path: file path} of every file the resolved release holds."""
        out = {} if self.base is None else {p: f for p, f in self.base.paths.items() if p not in self.retired}
        out.update({p: self.folder / p for p in self.manifest["files"]})
        return out

    def json(self, path: str):
        return json.loads(read_bytes(self.paths[path]))

    @cached_property
    def program_paths(self) -> dict:
        return {p.rsplit("/", 1)[1][:-5]: p for p in self.paths if "/programs/" in p and p.endswith(".json")}

    @cached_property
    def folders(self) -> dict:
        """{(template, building type) as ID prefix: folder} of every building folder."""
        out = {}
        for path in self.paths:
            parts = path.split("/")
            if len(parts) > 3 and parts[0] in ("commercial", "residential") and parts[2] != "library":
                out[(parts[1], parts[2])] = "/".join(parts[:3])
        return out

    def folder_of(self, record_id: str) -> str:
        template, building_type = record_id.split(".")[:2]
        folder = self.folders.get((template, building_type))
        if folder is None:
            raise GeneratorError("unsupported_binding", "/program_id", f"No release folder for {record_id!r}")
        return folder

    @lru_cache(maxsize=None)
    def generation(self, folder: str) -> dict:
        if self._generation is not None:
            return self._generation.get(folder, {})
        path = f"{folder}/generation.json"
        return self.json(path) if path in self.paths else {}

    def generation_folders(self) -> list:
        if self._generation is not None:
            return sorted(self._generation)
        return sorted(p.rsplit("/", 1)[0] for p in self.paths if p.endswith("/generation.json"))

    @lru_cache(maxsize=None)
    def program(self, program_id: str) -> tuple:
        """(folder, record): the program record, with its generation block as `generation` when it has one."""
        path = self.program_paths.get(program_id)
        if path is None:
            raise GeneratorError("unsupported_binding", "/program_id", f"Release {self.version} has no program {program_id!r}")
        folder = path.split("/programs/")[0]
        record = self.json(path)
        block = self.generation(folder).get("programs", {}).get(program_id)
        return folder, ({**record, "generation": block} if block else record)

    @lru_cache(maxsize=None)
    def schedules(self, folder: str) -> dict:
        """{schedule ID: {"rules": [...]}} of a commercial folder, days expanded into each rule's values."""
        if f"{folder}/schedules.json" not in self.paths:
            return {}
        table = self.json(f"{folder}/schedules.json")
        return {sid: {"rules": [{"day_types": r["day_types"], "start_date": r["start_date"], "end_date": r["end_date"],
                                 "values": table["days"][r["day"]]} for r in schedule["rules"]]}
                for sid, schedule in table["schedules"].items()}

    @lru_cache(maxsize=None)
    def services(self, folder: str) -> dict:
        path = f"{folder}/services.json"
        return self.json(path) if path in self.paths else {}

    @cached_property
    def configurations(self) -> dict:
        """{configuration ID: (folder, configuration)} over every folder's generation.json."""
        out = {}
        for folder in self.generation_folders():
            for cid, configuration in self.generation(folder).get("configurations", {}).items():
                out[cid] = (folder, configuration)
        return out


def definition_map(release: Release | None = None) -> dict:
    """Release 2.1.0's `definition-map.json`: definition program IDs to release program and view,
    definition service IDs to release services."""
    return (release or current()).json("definition-map.json")


def translate(document: dict, release: Release | None = None) -> dict:
    """A request with definition IDs (`program-…`, `service-…`) written as release IDs and views."""
    mapped = definition_map(release)
    programs, services = mapped["programs"], mapped["services"]
    instances = []
    for raw in document.get("instances", []):
        raw = dict(raw)
        if raw.get("program_id") in programs:
            entry = programs[raw["program_id"]]
            raw["program_id"] = entry["program_id"]
            raw.setdefault("values", entry["values"])
        if raw.get("service_id") in services:
            raw["service_id"] = services[raw["service_id"]]
        if raw.get("service_links"):
            raw["service_links"] = {services.get(k, k): v for k, v in raw["service_links"].items()}
        instances.append(raw)
    return {**document, "instances": instances}


def releases() -> list:
    """Release versions in the releases folder, oldest first."""
    root = releases_folder()
    if not root.is_dir():
        return []
    names = [p.name for p in root.iterdir() if p.is_dir() and (p / "manifest.json").is_file()]
    return sorted((n.removeprefix("v") for n in names if n.startswith("v")), key=_version)


@lru_cache(maxsize=1)
def current() -> Release:
    """The newest release this generator reads: major 2, with generation blocks."""
    root = releases_folder()
    for version in reversed(releases()):
        if version.split(".")[0] != READS["release"]:
            continue
        release = Release(root / f"v{version}")
        if release.manifest.get("generation", {}).get("schema_version", "").split(".")[0] == READS["generation"]:
            return release
    raise GeneratorError("release", "/", f"No atlas release {READS['release']}.x with generation blocks in {root}; "
                                         "set ATLAS_RELEASES to the extracted data archive")
