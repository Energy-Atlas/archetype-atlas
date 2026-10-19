"""Southern-hemisphere season alignment (atlas deviation from upstream; plan section 7, O13).

Upstream OpenStudio-HPXML models the United States only. Its empirical monthly
terms are indexed by northern calendar months: the lighting, plug-load,
appliance and fixed-background monthly multipliers, the lighting equation's
extra hour in April-October and the month term of the evening-peak width.
For a negative latitude these terms take the values of the month six months
away (January uses July's), so seasons line up. Astronomical sunset is
computed from the real latitude and needs no shift. Non-negative latitudes
are unchanged, so every upstream result is reproduced as before.
"""
from dataclasses import replace


def season_month(month: int, latitude: float | None) -> int:
    """The northern-calendar month (1-12) whose empirical values apply to `month`."""
    if latitude is None or latitude >= 0:
        return month
    return (month + 5) % 12 + 1


def seasonal(values, latitude: float | None) -> list:
    """Twelve monthly values re-indexed for the hemisphere."""
    return [values[season_month(month, latitude) - 1] for month in range(1, 13)]


def for_hemisphere(tables, latitude: float | None):
    """Tables whose monthly multipliers follow the hemisphere's seasons."""
    if latitude is None or latitude >= 0:
        return tables
    custom = {key: seasonal(values, latitude) if "Monthly" in key[1] else values
              for key, values in tables.custom.items()}
    return replace(tables, custom=custom)
