"""Atlas card icons, extending the EnergyAtlas Wiki editorial family.

Render them (from the skill folder):

    python <editorial-icons>/scripts/ink_icons.py design/icons/atlas_cards.py \
        --out build/card-icons

The cards use regular weight at 40 px and in their hover backdrops. Bold is
available for smaller displays. See README.md for the subjects and motion contract.
"""

from ink_icons import Pen, arc_points, rotate, rounded_polyline

TITLE = "Energy Archetype Atlas card icons"
INK = "#3b3631"       # warm charcoal; the site replaces it with currentColor
ACCENT = "#125dae"    # the light theme's accent blue; the site replaces it with its --ui-accent token
WEIGHTS = {"regular": 1.3, "bold": 1.85}


def house(pen: Pen) -> None:
    """One open-bottom stroke joins the two walls and pitched roof."""
    pen.stroke(rounded_polyline([(4.8, 20.2), (4.8, 10.0), (12.0, 3.6),
                                 (19.2, 10.0), (19.2, 20.2)], r=0.4))
    pen.blob(pen.rounded_rect(10.2, 13.8, 13.8, 20.1, 0.35, jitter=0.05), accent=True)


def program(pen: Pen) -> None:
    """A plan divided into program zones, with one zone highlighted."""
    pen.stroke(pen.rounded_rect(3.6, 4.4, 20.4, 20.0, 0.65), closed=True, overshoot=0.8)
    pen.stroke([(10.9, 4.7), (10.9, 19.7)], weight=0.9)
    pen.stroke([(11.2, 12.6), (20.0, 12.6)], weight=0.9)
    pen.blob(pen.rounded_rect(13.7, 7.1, 17.8, 10.0, 0.3, jitter=0.05), accent=True)


def select_copy(pen: Pen) -> None:
    """Overlapping copy sheets with an accent selection check."""
    pen.stroke(rounded_polyline([(4.0, 15.0), (4.0, 3.6), (14.4, 3.6), (14.4, 6.0)], r=0.5))
    pen.stroke(pen.rounded_rect(7.7, 7.6, 20.0, 20.4, 0.6), closed=True, overshoot=0.8)
    pen.stroke(rounded_polyline([(10.4, 14.1), (13.0, 16.5), (17.4, 11.4)], r=0.3), accent=True)


def schedule(pen: Pen) -> None:
    """A calendar containing a stepped daily schedule."""
    pen.stroke(pen.rounded_rect(3.6, 6.0, 20.4, 20.4, 0.65), closed=True, overshoot=0.8)
    pen.stroke([(3.9, 10.1), (20.1, 10.1)], weight=0.85)
    pen.stroke([(8.0, 3.5), (8.0, 7.7)])
    pen.stroke([(16.0, 3.5), (16.0, 7.7)])
    pen.stroke(rounded_polyline([(5.7, 17.7), (9.1, 17.7), (9.1, 13.9),
                                 (14.1, 13.9), (14.1, 16.2), (18.3, 16.2)], r=0.25),
               weight=0.95, accent=True)


def json_document(pen: Pen) -> None:
    """A document with JSON braces and one blue folded corner."""
    pen.stroke(rounded_polyline([(5.0, 11.0), (5.0, 3.6), (14.0, 3.6),
                                 (19.0, 8.6), (19.0, 20.4), (5.0, 20.4),
                                 (5.0, 10.2)], r=0.4))
    pen.stroke(rounded_polyline([(14.0, 3.9), (14.0, 8.6), (18.7, 8.6)], r=0.3), accent=True)
    brace = [(10.2, 11.4), (8.9, 11.9), (9.0, 13.7), (7.8, 14.7),
             (9.0, 15.6), (8.9, 17.5), (10.2, 18.0)]
    pen.stroke(brace, weight=0.8)
    pen.stroke([(24.0 - x, y) for x, y in brace], weight=0.8)


def definitions(pen: Pen) -> None:
    """An open reference book with a blue index ribbon."""
    pen.stroke(rounded_polyline([(12.0, 6.5), (8.1, 4.9), (3.7, 5.7),
                                 (3.7, 18.4), (8.1, 17.6), (12.0, 19.2)], r=0.45))
    pen.stroke(rounded_polyline([(12.0, 6.5), (15.9, 4.9), (20.3, 5.7),
                                 (20.3, 18.4), (15.9, 17.6), (12.0, 19.2)], r=0.45))
    pen.stroke([(12.0, 7.2), (12.0, 18.4)], weight=0.85)
    pen.blob([(15.1, 5.4), (17.0, 5.4), (17.0, 12.0), (16.0, 10.9), (15.1, 12.0)], accent=True)


def office(pen: Pen) -> None:
    """An office tower: four windows and one blue ground-floor entrance."""
    pen.stroke(pen.rounded_rect(6.0, 3.5, 18.0, 20.4, 0.6), closed=True, overshoot=0.8)
    for x in (9.3, 14.7):
        for y in (7.0, 11.7):
            pen.stroke([(x, y), (x, y + 1.7)], weight=0.95, taper=(0.9, 0.9), spline=False)
    pen.blob(pen.rounded_rect(10.3, 16.7, 13.7, 20.2, 0.35, jitter=0.05), accent=True)


def layers(pen: Pen) -> None:
    """Three separated construction layers; the bottom layer is the accent."""
    # Start along an edge, rounding the four corners before the pen samples
    # the centreline. A sparse, unsampled polyline loses its closing edge.
    pen.stroke(rounded_polyline([(16.25, 5.8), (20.5, 8.1), (12.0, 12.7),
                                 (3.5, 8.1), (12.0, 3.5)], r=0.45),
               closed=True, overshoot=0.7)
    pen.stroke(rounded_polyline([(3.5, 12.0), (12.0, 16.6), (20.5, 12.0)], r=0.35))
    pen.stroke(rounded_polyline([(3.5, 16.0), (12.0, 20.6), (20.5, 16.0)], r=0.35), accent=True)


def fan(pen: Pen) -> None:
    """A circular fan with three swept blades and a blue hub."""
    pen.stroke(arc_points(12.0, 12.0, 8.7, -90, 278, n=28), weight=0.95)
    blade = [(10.6, 10.1), (8.3, 6.2), (9.6, 4.9), (12.8, 4.6),
             (14.5, 6.0), (14.2, 8.3), (12.9, 10.0)]
    for angle in (0, 120, 240):
        pen.blob(rotate(blade, (12.0, 12.0), angle))
    pen.dot(12.0, 12.0, 1.45, accent=True)


ICONS = {
    "house": (house, 31),
    "office": (office, 37),
    "layers": (layers, 41),
    "fan": (fan, 43),
    "program": (program, 47),
    "select-copy": (select_copy, 53),
    "schedule": (schedule, 59),
    "json-document": (json_document, 61),
    "definitions": (definitions, 67),
}
