"""ComStock base-to-peak ratio adjustment (measures `set_interior_lighting_bpr`
and `set_electric_equipment_bpr`, method `set_sch_bpr`).

The day's minimum is raised or lowered towards `ratio x peak` while the peak
stays fixed. Weekend days may not go above the lowest weekday base.

Flat days (every value equal, any number of points) have no base-to-peak
ratio. The measure leaves one-value days unaltered, and the reference
documentation keeps data-centre IT equipment constant (section 4.6.3), so the
documented behaviour leaves every flat day unchanged. Native ComStock instead
clears multi-point flat days, which the hours transform creates from constant
days: the scale is 0/0, OpenStudio rejects the NaN values, and the day reads
[[24, 0]]. That zeroes data-centre plug loads all year and flat weekend days in
plain-template offices and schools (ADR 0035 outcome; plan section 7, O2).
"native" reproduces it for validation against the answer keys only.
"""
from .profiles import stored_value

FLAT_DAY_MODES = ("documented", "native")


def adjust_day(points, ratio: float, weekday_base: float | None = None, flat_days: str = "documented"):
    """Return (adjusted points, resulting base) for one day profile."""
    peak = max(v for _, v in points)
    base = min(v for _, v in points)
    if len(points) == 1 or (peak == base and flat_days == "documented"):
        # No base-to-peak ratio exists; ComStock returns a sentinel base of 1.
        return list(points), 1.0
    if peak == base:
        return [(24.0, 0.0)], 0.0
    new_base = ratio * peak
    if weekday_base is not None and weekday_base < new_base:
        new_base = weekday_base
    scale = (new_base - base) / (peak - base)
    adjusted = [(t, stored_value(max(0.0, (peak - v) * scale + v))) for t, v in points]
    return adjusted, min(v for _, v in adjusted)
