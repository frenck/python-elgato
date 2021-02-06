"""Asynchronous Python client for Elgato Key Lights."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class State:
    """Object holding the Elgato Key Light state."""

    on: bool
    brightness: int
    temperature: int

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> State:
        """Return a State object from a Elgato Key Light API response."""
        return State(
            on=(data["lights"][0]["on"] == 1),
            brightness=data["lights"][0]["brightness"],
            temperature=data["lights"][0]["temperature"],
        )


@dataclass
class Info:
    """Object holding the Elgato Key Light device information."""

    product_name: str
    hardware_board_type: int
    firmware_build_number: int
    firmware_version: str
    serial_number: str
    display_name: str

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> Info:
        """Return a Info object from a Elgato Key Light API response."""
        return Info(
            product_name=data["productName"],
            hardware_board_type=data["hardwareBoardType"],
            firmware_build_number=data["firmwareBuildNumber"],
            firmware_version=data["firmwareVersion"],
            serial_number=data["serialNumber"],
            display_name=data["displayName"],
        )
