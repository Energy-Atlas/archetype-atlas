"""Annual totals and amplitudes: the two bindings of a load to its schedule.

- Source magnitude (commercial and fixed programmes, shared water services; O15): the
  amplitude is the installed density or peak flow, and the annual total is
  `annual_target(magnitude, unit, generated shape)`, so it follows the draw, as in ComStock.
- Annual (ResStock dwellings and apartment units): the annual total is fixed first, and
  `fit_amplitude` gives the design level that makes the generated shape integrate to it, as
  OpenStudio-HPXML `calc_design_level_from_annual_kwh` does.
"""
import numpy as np

from .errors import GeneratorError

# magnitude unit -> (annual unit, seconds per hourly sample)
ANNUAL_UNITS = {
    "W": ("Wh", 1),
    "W/m2": ("Wh/m2", 1),
    "W/dwelling": ("Wh/dwelling", 1),
    "W/person": ("Wh/person", 1),
    "m3/s": ("m3", 3600),
    "m3/s/m2": ("m3/m2", 3600),
    "m3/s/dwelling": ("m3/dwelling", 3600),
    "m3/s/person": ("m3/person", 3600),
}


def annual_target(magnitude: float, magnitude_unit: str, reference_shape: np.ndarray) -> float:
    """Annual total = magnitude x sum of the hourly reference fractions x seconds per sample."""
    seconds = ANNUAL_UNITS[magnitude_unit][1]
    return float(magnitude * np.sum(reference_shape) * seconds)


def fit_amplitude(total: float, magnitude_unit: str, shape: np.ndarray) -> float:
    """Amplitude that makes `amplitude x shape` integrate to `total`."""
    integral = float(np.sum(shape))
    if integral == 0:
        if total > 0:
            raise GeneratorError("zero_generated_integral", "/values", "A positive target cannot bind a zero schedule")
        return 0.0
    seconds = ANNUAL_UNITS[magnitude_unit][1]
    return total / (integral * seconds)
