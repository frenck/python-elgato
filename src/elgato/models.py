"""Asynchronous Python client for Elgato Key Lights."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class State:
    """Object holding the Elgato Key Light state.

    Represents a visible state of an Elgato Key Light.

    Attributes:
        on: A boolean indiciating the if the light if on or off.
        brightness: An integer between 0 and 255, representing the brightness.
        temperature: An integer representing the color temperature in mireds.
    """

    on: bool
    brightness: int
    temperature: int

    @staticmethod
    def from_dict(data: dict[str, Any]) -> State:
        """Return a State object from a Elgato Key Light API response.

        Converts a dictionary, obtained from an Elgato Key Light's API into
        a State object.

        Args:
            data: The state response from the Elgato Key Light's API.

        Returns:
            A state object.
        """
        return State(
            on=(data["lights"][0]["on"] == 1),
            brightness=data["lights"][0]["brightness"],
            temperature=data["lights"][0]["temperature"],
        )


@dataclass
class Info:
    """Object holding the Elgato Key Light device information.

    This object holds information about the Elgato Key Light.

    Attributes:
        product_name: The product name.
        hardware_board_type: An integer indicating the board revision.
        firmware_build_number: An integer with the build number of the firmware.
        firmware_version: String containing the firmware version.
        serial_number: Serial number of the Elgato Key Light.
        display_name: Configured display name of the Elgato Key Light.
    """

    product_name: str
    hardware_board_type: int
    firmware_build_number: int
    firmware_version: str
    serial_number: str
    display_name: str

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Info:
        """Return a Info object from a Elgato Key Light API response.

        Converts a dictionary, obtained from an Elgato Key Light's API into
        a Info object.

        Args:
            data: The info response from the Elgato Key Light's API.

        Returns:
            An info object.
        """
        return Info(
            product_name=data["productName"],
            hardware_board_type=data["hardwareBoardType"],
            firmware_build_number=data["firmwareBuildNumber"],
            firmware_version=data["firmwareVersion"],
            serial_number=data["serialNumber"],
            display_name=data["displayName"],
        )
