"""Exceptions for Elgato Lights."""

from typing import Any


class ElgatoError(Exception):
    """Generic Elgato Light exception."""


class ElgatoConnectionError(ElgatoError):
    """Elgato Light connection exception."""


class ElgatoNoBatteryError(Exception):
    """Elgato light does not have a battery."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the ElgatoNoBatteryError."""
        if not args:  # pragma: no cover
            args = ("The Elgato light does not have a battery.",)
        super().__init__(*args, **kwargs)
