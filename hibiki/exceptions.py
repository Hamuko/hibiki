"""
Provides exceptions for the rest of the module.
"""


class HibikiException(Exception):
    """Base exception class for Hibiki exceptions."""
    def __init__(self, message=None):
        super().__init__(message)


class BadDestinationError(HibikiException):
    """Raised if HibikiConfig receives a non-valid destination."""
    def __init__(self, message=None):
        super().__init__(message)


class InvalidConfigError(HibikiException):
    """Raised if configuration file for HibikiConfig is invalid."""
    def __init__(self, message=None):
        super().__init__(message)
