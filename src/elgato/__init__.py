"""Asynchronous Python client for Elgato Lights."""

from .catalog import FirmwareCatalog
from .elgato import Elgato
from .exceptions import (
    ElgatoConnectionError,
    ElgatoError,
    ElgatoFirmwareError,
    ElgatoNoBatteryError,
)
from .firmware import BOARD_TYPES, FirmwareImage, FirmwareVersion
from .models import (
    BatteryInfo,
    BatterySettings,
    BatteryStatus,
    EnergySavingAdjustBrightnessSettings,
    EnergySavingSettings,
    Info,
    PowerOnBehavior,
    PowerSource,
    Settings,
    State,
    Wifi,
)

__all__ = [
    "BOARD_TYPES",
    "BatteryInfo",
    "BatterySettings",
    "BatteryStatus",
    "Elgato",
    "ElgatoConnectionError",
    "ElgatoError",
    "ElgatoFirmwareError",
    "ElgatoNoBatteryError",
    "EnergySavingAdjustBrightnessSettings",
    "EnergySavingSettings",
    "FirmwareCatalog",
    "FirmwareImage",
    "FirmwareVersion",
    "Info",
    "PowerOnBehavior",
    "PowerSource",
    "Settings",
    "State",
    "Wifi",
]
