"""Readable ComStock/ResStock schedule generator (ADR 0035)."""

__version__ = "2.0.0.dev0"

from .generator import generate  # noqa: E402  (generator reads __version__)

__all__ = ["__version__", "generate"]
