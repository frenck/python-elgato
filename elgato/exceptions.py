"""Exceptions for Elgato Key Lights."""


class ElgatoError(Exception):
    """Generic Elgato Key Light exception."""

    pass


class ElgatoConnectionError(ElgatoError):
    """Elgato Key Light connection exception."""

    pass
