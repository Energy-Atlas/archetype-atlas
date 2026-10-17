"""Read spaces, floor areas, zone multipliers and standards space types from an OpenStudio .osm file.

An .osm file is a sequence of objects separated by blank lines; each field line
carries a `!- Field Name` comment, which this reader uses to find fields by name.
A space's floor area is the sum of the areas of its Floor surfaces (Newell's
method), as OpenStudio `Space.floorArea` computes it; translation and rotation
of the space do not change it.
"""
from dataclasses import dataclass
import math
from pathlib import Path


@dataclass(frozen=True)
class Space:
    name: str
    space_type: str | None
    standards_building_type: str | None
    standards_space_type: str | None
    floor_area_m2: float
    multiplier: int
    part_of_total_floor_area: bool


def _objects(text: str):
    for block in text.replace("\r\n", "\n").split("\n\n"):
        lines = [line for line in block.strip().splitlines() if line.strip()]
        if not lines:
            continue
        kind = lines[0].strip().rstrip(",;")
        fields = {}
        vertices = []
        for line in lines[1:]:
            value, _, comment = line.partition("!-")
            value = value.strip().rstrip(",;").strip()
            name = comment.strip()
            if name.startswith("X,Y,Z Vertex"):
                vertices.append(tuple(float(v) for v in value.split(",")))
            else:
                fields[name] = value
        yield kind, fields, vertices


def polygon_area(vertices) -> float:
    """Area of a planar 3D polygon (Newell's method)."""
    nx = ny = nz = 0.0
    count = len(vertices)
    for i in range(count):
        x1, y1, z1 = vertices[i]
        x2, y2, z2 = vertices[(i + 1) % count]
        nx += (y1 - y2) * (z1 + z2)
        ny += (z1 - z2) * (x1 + x2)
        nz += (x1 - x2) * (y1 + y2)
    return 0.5 * math.sqrt(nx * nx + ny * ny + nz * nz)


def read_spaces(path: Path) -> list[Space]:
    """Spaces in file order with floor area, zone multiplier and standards space type.

    Object references in .osm files are handles; names are resolved here.
    """
    spaces, space_types, zones = {}, {}, {}
    floor_area = {}
    order = []
    for kind, fields, vertices in _objects(Path(path).read_text(encoding="utf-8")):
        handle = fields.get("Handle")
        if kind == "OS:Space":
            spaces[handle] = fields
            order.append(handle)
        elif kind == "OS:SpaceType":
            space_types[handle] = fields
        elif kind == "OS:ThermalZone":
            zones[handle] = fields
        elif kind == "OS:Surface" and fields.get("Surface Type", "").lower() == "floor":
            owner = fields["Space Name"]
            floor_area[owner] = floor_area.get(owner, 0.0) + polygon_area(vertices)
    result = []
    for handle in order:
        fields = spaces[handle]
        space_type = space_types.get(fields.get("Space Type Name"), {})
        zone = zones.get(fields.get("Thermal Zone Name"), {})
        multiplier = zone.get("Multiplier") or "1"
        result.append(Space(
            name=fields["Name"], space_type=space_type.get("Name"),
            standards_building_type=space_type.get("Standards Building Type") or None,
            standards_space_type=space_type.get("Standards Space Type") or None,
            floor_area_m2=floor_area.get(handle, 0.0),
            multiplier=int(float(multiplier)),
            part_of_total_floor_area=(fields.get("Part of Total Floor Area", "Yes").lower() != "no")))
    return result
