"""Readable ComStock/ResStock schedule generator (ADR 0035).

`__version__` is the generator's version and the version of the `atlas-schedules`
package built from this tree (ADR 0049; `pyproject.toml` reads it). Generator 4.0.0
assembles its recipes from an atlas data release (ADR 0051): the generator view the
wheel bundles, or a release on disk named by `ATLAS_RELEASES` or `--release-dir`."""

__version__ = "4.0.0"
REQUEST_SCHEMA_VERSION = "4.0.0"   # the request and bundle contract (ADR 0051 section 4)

from .generator import generate  # noqa: E402  (generator reads __version__)

__all__ = ["__version__", "REQUEST_SCHEMA_VERSION", "generate"]
