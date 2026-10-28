"""ResStock measure arguments of a unit's sampled characteristics (plan section 8, B4).

1. options_lookup: each sampled characteristic option gives its ResStockArguments arguments (strings);
2. ResStockArguments.run: no pool when `misc_has_pool` is false;
3. BuildResidentialHPXML `get_option_properties`: every argument that names an option table adds that
   option's properties as `<table>_<property>`, typed as `get_csv_data_for_tsv_file` types them
   (packaged by scripts/build_resstock_characteristics.py).

Characteristics without options_lookup arguments (geography, income, tenure and the like) add none.
"""
from functools import lru_cache
import gzip
import json

from ..errors import GeneratorError
from .characteristics import DATA


@lru_cache(maxsize=1)
def _arguments() -> dict:
    return json.loads(gzip.decompress((DATA / "arguments.json.gz").read_bytes()))


def lookup_arguments(characteristics: dict) -> dict:
    """Steps 1 and 2: {argument: value} before option properties."""
    lookup = _arguments()["lookup"]
    arguments = {}
    for name, option in characteristics.items():
        options = lookup.get(name)
        if options is None:
            continue
        if option not in options:
            raise GeneratorError("source_undefined", f"/characteristics/{name}",
                                 f"options_lookup has no row for {name}={option}")
        for key, value in options[option].items():
            if key in arguments and arguments[key] != value:
                raise GeneratorError("source_undefined", f"/arguments/{key}", f"Conflicting values from {name}")
            arguments[key] = value
    if arguments.get("misc_has_pool") == "false":
        arguments["misc_pool"] = "None"  # ResStockArguments.run
    return arguments


def expand_properties(arguments: dict) -> dict:
    """Step 3: a copy with the option properties of every argument that names an option table."""
    expanded = dict(arguments)
    for table, record in _arguments()["properties"].items():
        option = arguments.get(table)
        if option is None:
            continue
        if option not in record["rows"]:
            raise GeneratorError("source_undefined", f"/arguments/{table}", f"No option {option!r} in {table}.tsv")
        for key, value in zip(record["keys"], record["rows"][option]):
            if expanded.get(key) is not None:
                raise GeneratorError("source_undefined", f"/arguments/{key}", "Duplicate option property")
            expanded[key] = value
    return expanded


def unit_arguments(characteristics: dict) -> dict:
    """{argument: value} for one unit's {characteristic: option}."""
    return expand_properties(lookup_arguments(characteristics))
