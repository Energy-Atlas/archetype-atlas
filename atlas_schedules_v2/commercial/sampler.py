"""Sample the ten ComStock operating parameters for one operating group.

ComStock draws these from conditional probability tables (TSV v33). Each
parameter takes one uniform draw, in a fixed order, and selects the first
option whose cumulative probability is strictly greater than the draw. Later
tables may be conditioned on options chosen earlier. A draw beyond a table's
cumulative total is an error (no tail filling).
"""
from functools import lru_cache
import json
from pathlib import Path
import random

from ..errors import GeneratorError

TABLES = Path(__file__).resolve().parents[1] / "data/commercial/sampling"

DRAW_ORDER = (
    "weekday_start_time", "weekend_start_time", "weekday_duration", "weekend_duration",
    "plugload_sch_base_peak_ratio_type", "plugload_sch_weekday_base_peak_ratio",
    "plugload_sch_weekend_base_peak_ratio",
    "ltg_sch_base_peak_ratio_type", "ltg_sch_weekday_base_peak_ratio", "ltg_sch_weekend_base_peak_ratio",
)


@lru_cache(maxsize=None)
def load_tables(building_type: str) -> dict:
    """The ten conditional tables (ComStock tsvs-v33) for one building type."""
    path = TABLES / f"{building_type}.json"
    if not path.exists():
        raise GeneratorError("unsupported_binding", "/commercial/building_type",
                             f"No sampling tables for building type {building_type!r}")
    return json.loads(path.read_text(encoding="utf-8"))


def select_option(table: dict, selectors: dict, uniform: float) -> int:
    """Index of the option selected by `uniform` in the row matching `selectors`."""
    rows = [row for row in table["rows"]
            if all(row["selectors"].get(d) == selectors[d] for d in table["dependencies"])]
    if len(rows) != 1:
        raise GeneratorError("source_selection", "/commercial/selectors",
                             f"Selectors {selectors} must match exactly one row")
    cumulative = 0.0
    for index, probability in enumerate(rows[0]["probabilities"]):
        cumulative += probability
        if cumulative > uniform:
            return index
    raise GeneratorError("source_selection", "/commercial/uniform",
                         f"Draw {uniform} lies beyond the table total {cumulative}")


def sample_operating_parameters(tables: dict, building_type: str, group_seed: int) -> dict:
    """Return {parameter: {"option", "value", "unit", "modify"}} for the ten parameters."""
    rng = random.Random(group_seed)
    selectors = {"building_type": building_type}
    sampled = {}
    for parameter in DRAW_ORDER:
        table = tables[parameter]
        uniform = rng.random()
        index = select_option(table, selectors, uniform)
        option = table["options"][index]
        values = table.get("option_values")
        sampled[parameter] = {
            "option": option,
            "value": values[index] if values else option,
            "unit": table.get("option_unit"),
            "modify": option != "NA",
        }
        selectors[parameter] = option
    return sampled
