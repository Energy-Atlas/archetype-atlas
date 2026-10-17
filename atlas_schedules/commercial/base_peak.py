"""ComStock base-to-peak ratio adjustment (measures `set_interior_lighting_bpr`
and `set_electric_equipment_bpr`, method `set_sch_bpr`).

The day's minimum is raised or lowered towards `ratio x peak` while the peak
stays fixed. Weekend days may not go above the lowest weekday base.
"""
from .profiles import stored_value


def adjust_day(points, ratio: float, weekday_base: float | None = None):
    """Return (adjusted points, resulting base) for one day profile."""
    if len(points) == 1:
        # Constant profiles are left alone; ComStock returns a sentinel base of 1.
        return list(points), 1.0
    peak = max(v for _, v in points)
    base = min(v for _, v in points)
    if peak == base:
        # The scale is 0/0, so every new value is NaN; OpenStudio rejects NaN
        # values and the cleared day reads as [[24, 0]]. Required by
        # answer_keys/commercial (287 family checks fail without it).
        return [(24.0, 0.0)], 0.0
    new_base = ratio * peak
    if weekday_base is not None and weekday_base < new_base:
        new_base = weekday_base
    scale = (new_base - base) / (peak - base)
    adjusted = [(t, stored_value(max(0.0, (peak - v) * scale + v))) for t, v in points]
    return adjusted, min(v for _, v in adjusted)
