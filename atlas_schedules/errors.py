"""Structured public validation failures."""


class GeneratorError(ValueError):
    def __init__(self, code: str, path: str, message: str):
        self.code, self.path, self.message = code, path, message
        super().__init__(f'{code} at {path}: {message}')
