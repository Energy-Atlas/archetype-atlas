"""Readable ComStock/ResStock schedule generator (ADR 0035).

`__version__` is the generator's version and the version of the `atlas-schedules`
package built from this tree (ADR 0049; `pyproject.toml` reads it)."""

__version__ = "3.0.0"

from .generator import generate  # noqa: E402  (generator reads __version__)

__all__ = ["__version__", "generate"]
