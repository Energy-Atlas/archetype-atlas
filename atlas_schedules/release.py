"""Read an atlas release: program records, folder tables and generation blocks (ADR 0051).

The generator holds no copy of release values. It reads a release from one of:

- `set_releases(path)`, else the `ATLAS_RELEASES` environment variable: a folder of release
  folders side by side (`v2.0.0/`, `v2.1.0/`, `v2.2.0/`, as `data/atlas-releases` or the
  extracted data archive), one release folder, or a generator view (below);
- the source tree's `data/atlas-releases`, when the package runs from a checkout;
- the generator view the wheel bundles (`data/atlas-release/`, written by
  `scripts.build_generator_view`): per building folder, exactly the files the assembler reads,
  and the release's version and manifest hash, so a bundle is the same whichever is read.

A release is a whole snapshot (2.0.0) or a delta on a base (2.1.0 on 2.0.0, 2.2.0 on 2.1.0). A
delta's manifest names its base by release and manifest hash, lists its own files, and lists
the base files it removes. A path resolves to the delta's file, else the base's unless
removed. Each folder's `generation.json` holds its programs' generation blocks, its services'
blocks and its building configurations; a program record reads with its block as `generation`.
"""
from functools import cached_property, lru_cache
import hashlib
import json
import os
from pathlib import Path

from .errors import GeneratorError

READS = {"release": "2", "generation": "1"}   # major versions this generator reads
PACKAGE = Path(__file__).resolve().parent
SOURCE_TREE = PACKAGE.parents[0] / "data" / "atlas-releases"
VIEW = PACKAGE / "data" / "atlas-release"
VIEW_INDEX = "index.json"
_ROOT: Path | None = None


def set_releases(path) -> None:
    """Read releases from this folder from now on (a releases tree, one release or a generator view)."""
    global _ROOT
    _ROOT = Path(path) if path is not None else None
    current.cache_clear()


def releases_folder() -> Path | None:
    """Where releases are read from, in order: set_releases(), ATLAS_RELEASES, the source tree, the bundled view."""
    if _ROOT is not None:
        return _ROOT
    if os.environ.get("ATLAS_RELEASES"):
        return Path(os.environ["ATLAS_RELEASES"])
    if SOURCE_TREE.is_dir():
        return SOURCE_TREE
    if (VIEW / VIEW_INDEX).is_file():
        return VIEW
    return None


def read_bytes(path) -> bytes:
    """A file's bytes; on Windows, past MAX_PATH through the extended-length prefix."""
    if os.name == "nt":
        absolute = os.path.abspath(path)
        if len(absolute) >= 240 and not absolute.startswith("\\\\?\\"):
            path = "\\\\?\\" + absolute
    with open(path, "rb") as handle:
        return handle.read()


def _version(name: str) -> tuple:
    return tuple(int(part) for part in name.removeprefix("v").split("."))


class TreeStore:
    """One release folder in a releases tree, resolved over its base when it is a delta."""

    def __init__(self, folder):
        self.folder = Path(folder)
        raw = read_bytes(self.folder / "manifest.json")
        self.manifest = json.loads(raw)
        self.manifest_sha256 = hashlib.sha256(raw).hexdigest()
        self.version = self.manifest["release"]
        base = self.manifest.get("base_release")
        self.base = None
        if base:
            self.base = TreeStore(self.folder.parent / f"v{base['release']}")
            if self.base.manifest_sha256 != base["manifest_sha256"]:
                raise GeneratorError("release", "/base_release",
                                     f"Release {self.version} expects base {base['release']} with manifest "
                                     f"{base['manifest_sha256']}, found {self.base.manifest_sha256}")
        self.removed = set(self.manifest.get("removed", []))

    @property
    def generation_schema_version(self) -> str | None:
        return (self.manifest.get("generation") or {}).get("schema_version")

    @cached_property
    def paths(self) -> dict:
        """{release path: file path} of every file the resolved release holds."""
        out = {} if self.base is None else {p: f for p, f in self.base.paths.items() if p not in self.removed}
        out.update({p: self.folder / p for p in self.manifest["files"]})
        return out

    def json(self, path: str):
        return json.loads(read_bytes(self.paths[path]))

    def describe(self) -> str:
        return str(self.folder)


class ViewStore:
    """The generator view a wheel bundles: `index.json` and one JSON file per building folder, each
    holding {release path: document} for the files the assembler reads."""

    def __init__(self, folder):
        self.folder = Path(folder)
        self.manifest = json.loads(read_bytes(self.folder / VIEW_INDEX))
        if self.manifest.get("kind") != "atlas_release_generator_view":
            raise GeneratorError("release", "/", f"{self.folder} is not a generator view of an atlas release")
        self.version = self.manifest["release"]
        self.manifest_sha256 = self.manifest["manifest_sha256"]
        self.base = None
        self.removed = set()

    @property
    def generation_schema_version(self) -> str | None:
        return self.manifest["generation"]["schema_version"]

    @cached_property
    def paths(self) -> dict:
        """{release path: view file} of every release path the view carries."""
        out = {p: VIEW_INDEX for p in self.manifest["root"]}
        for name, listed in self.manifest["folders"].items():
            out.update({p: listed["file"] for p in listed["paths"]})
        return out

    @lru_cache(maxsize=None)
    def _file(self, name: str) -> dict:
        return json.loads(read_bytes(self.folder / name))

    def json(self, path: str):
        name = self.paths[path]
        if name == VIEW_INDEX:
            return self.manifest["root"][path]
        return self._file(name)[path]

    def describe(self) -> str:
        return f"{self.folder} (generator view)"


class Release:
    """A release read through a store, with the generation blocks laid over its programs."""

    def __init__(self, folder, generation: dict | None = None):
        self.store = folder if isinstance(folder, (TreeStore, ViewStore)) else open_store(folder)
        self._generation = generation   # {folder: generation.json document}, to check blocks before they are written

    @property
    def version(self) -> str:
        return self.store.version

    @property
    def manifest(self) -> dict:
        return self.store.manifest

    @property
    def manifest_sha256(self) -> str:
        return self.store.manifest_sha256

    @property
    def generation_schema_version(self) -> str | None:
        return self.store.generation_schema_version

    @cached_property
    def base(self):
        """The base release this one is a delta on, read the same way; None for a snapshot or a view."""
        return Release(self.store.base) if self.store.base is not None else None

    @property
    def removed(self) -> set:
        return self.store.removed

    @property
    def paths(self) -> dict:
        return self.store.paths

    def json(self, path: str):
        return self.store.json(path)

    def describe(self) -> str:
        return f"atlas release {self.version} from {self.store.describe()}"

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

    def provenance(self) -> dict:
        """What a bundle records of the release it was generated from."""
        return {"version": self.version, "manifest_sha256": self.manifest_sha256,
                "generation_schema_version": self.generation_schema_version}


def open_store(path):
    """A store for a release folder (manifest.json) or a generator view (index.json)."""
    path = Path(path)
    if (path / VIEW_INDEX).is_file():
        return ViewStore(path)
    if (path / "manifest.json").is_file():
        return TreeStore(path)
    raise GeneratorError("release", "/", f"{path} holds neither a release manifest nor a generator view index")


def definition_map(release: Release | None = None) -> dict:
    """The release's `definition-map.json`: definition program IDs to release program and view,
    definition service IDs to release services."""
    return (release or current()).json("definition-map.json")


def translate(document: dict, release: Release | None = None) -> dict:
    """A request with definition IDs (`program-…`, `service-…`) written as release IDs and views, and its
    schema version raised to the one this generator reads (request schema 4.0.0, ADR 0051)."""
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
    out = {**document, "instances": instances}
    if out.get("schema_version") == "3.0.0":
        out["schema_version"] = "4.0.0"
    return out


def releases(root: Path | None = None) -> list:
    """Release versions in a releases folder, oldest first."""
    root = releases_folder() if root is None else root
    if root is None or not root.is_dir():
        return []
    names = [p.name for p in root.iterdir() if p.is_dir() and (p / "manifest.json").is_file()]
    return sorted((n.removeprefix("v") for n in names if n.startswith("v")), key=_version)


def _reads(release: Release) -> bool:
    return (release.version.split(".")[0] == READS["release"]
            and (release.generation_schema_version or "").split(".")[0] == READS["generation"])


@lru_cache(maxsize=1)
def current() -> Release:
    """The release this generator reads: the one set or named, else the newest major-2 release with
    generation blocks in the releases folder."""
    root = releases_folder()
    if root is None:
        raise GeneratorError("release", "/", "No atlas release to read: the package bundles none and ATLAS_RELEASES is unset")
    if (root / VIEW_INDEX).is_file() or (root / "manifest.json").is_file():
        release = Release(root)
        if not _reads(release):
            raise GeneratorError("release", "/", f"Generator reads atlas release {READS['release']}.x with generation "
                                                 f"blocks {READS['generation']}.x; {release.describe()} is not one")
        return release
    for version in reversed(releases(root)):
        if version.split(".")[0] != READS["release"]:
            continue
        release = Release(root / f"v{version}")
        if _reads(release):
            return release
    raise GeneratorError("release", "/", f"No atlas release {READS['release']}.x with generation blocks in {root}; "
                                         "set ATLAS_RELEASES to the extracted data archive")
