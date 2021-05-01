"""Exceptions for Elgato Lights."""


class ElgatoError(Exception):
    """Generic Elgato Light exception."""


class ElgatoConnectionError(ElgatoError):
    """Elgato Light connection exception."""
