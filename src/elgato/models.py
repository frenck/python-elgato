"""Asynchronous Python client for Elgato Lights."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Info:
    """Object holding the Elgato Light device information.

    This object holds information about the Elgato Light.

    Attributes:
        display_name: Configured display name of the Elgato Light.
        features: List of features this devices exposes.
        firmware_build_number: An integer with the build number of the firmware.
        firmware_version: String containing the firmware version.
        hardware_board_type: An integer indicating the board revision.
        product_name: The product name.
        serial_number: Serial number of the Elgato Light.
    """

    display_name: str
    features: list[str]
    firmware_build_number: int
    firmware_version: str
    hardware_board_type: int
    product_name: str
    serial_number: str

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Info:
        """Return a Info object from a Elgato Light API response.

        Converts a dictionary, obtained from an Elgato Light's API into
        a Info object.

        Args:
            data: The info response from the Elgato Light's API.

        Returns:
            An info object.
        """
        return Info(
            display_name=data["displayName"],
            features=data["features"],
            firmware_build_number=data["firmwareBuildNumber"],
            firmware_version=data["firmwareVersion"],
            hardware_board_type=data["hardwareBoardType"],
            product_name=data["productName"],
            serial_number=data["serialNumber"],
        )


@dataclass
class Settings:
    """Object holding the Elgato Light device settings.

    This object holds information about the Elgato Light settings.

    Attributes:
        color_change_duration: Transition time of color changes in milliseconds.
        power_on_behavior: 1 = Restore last, 2 = Use defaults.
        power_on_brightness: The brightness used as default.
        power_on_hue: The hue value used as default.
        power_on_saturation: The saturation level used as default.
        power_on_temperature: The temperature level used as default.
        switch_off_duration: Turn off transition time in milliseconds.
        switch_on_duration: Turn on transition time in milliseconds.
    """

    color_change_duration: int
    power_on_behavior: bool
    power_on_brightness: int
    power_on_hue: float | None
    power_on_saturation: float | None
    power_on_temperature: int | None
    switch_off_duration: int
    switch_on_duration: int

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Settings:
        """Return a Settings object from a Elgato Light API response.

        Converts a dictionary, obtained from an Elgato Light's API into
        a Settings object.

        Args:
            data: The setting response from the Elgato Light's API.

        Returns:
            An settings object.
        """
        return Settings(
            color_change_duration=data["colorChangeDurationMs"],
            power_on_behavior=data["powerOnBehavior"],
            power_on_brightness=data["powerOnBrightness"],
            power_on_hue=data.get("powerOnHue"),
            power_on_saturation=data.get("powerOnSaturation"),
            power_on_temperature=data.get("powerOnTemperature"),
            switch_off_duration=data["switchOffDurationMs"],
            switch_on_duration=data["switchOnDurationMs"],
        )


@dataclass
class State:
    """Object holding the Elgato Light state.

    Represents a visible state of an Elgato Light.

    Attributes:
        on: A boolean indicating the if the light if on or off.
        brightness: An integer between 0 and 255, representing the brightness.
        hue:
        saturation:
        temperature: An integer representing the color temperature in mireds.
    """

    on: bool
    brightness: int
    hue: float | None
    saturation: float | None
    temperature: int | None

    @staticmethod
    def from_dict(data: dict[str, Any]) -> State:
        """Return a State object from a Elgato Light API response.

        Converts a dictionary, obtained from an Elgato Light's API into
        a State object.

        Args:
            data: The state response from the Elgato Light's API.

        Returns:
            A state object.
        """
        state = data["lights"][0]
        return State(
            on=(state["on"] == 1),
            brightness=state["brightness"],
            hue=state.get("hue"),
            saturation=state.get("saturation"),
            temperature=state.get("temperature"),
        )
