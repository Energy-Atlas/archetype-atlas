"""The one error type the generator raises for bad requests or data."""


class GeneratorError(ValueError):
    """A structured failure: a short code, a JSON-pointer-like path and a message."""

    def __init__(self, code: str, path: str, message: str):
        self.code = code
        self.path = path
        self.message = message
        super().__init__(f"{code} at {path}: {message}")
