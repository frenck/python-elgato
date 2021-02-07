"""Exceptions for Elgato Key Lights."""


class ElgatoError(Exception):
    """Generic Elgato Key Light exception."""


class ElgatoConnectionError(ElgatoError):
    """Elgato Key Light connection exception."""
