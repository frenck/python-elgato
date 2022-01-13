"""Asynchronous Python client for Elgato Lights."""
from enum import IntEnum
from typing import Optional

from pydantic import BaseModel, Field


class Info(BaseModel):
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

    display_name: str = Field("Elgato Light", alias="displayName")
    firmware_build_number: int = Field(..., alias="firmwareBuildNumber")
    firmware_version: str = Field(..., alias="firmwareVersion")
    hardware_board_type: int = Field(..., alias="hardwareBoardType")
    product_name: str = Field(..., alias="productName")
    serial_number: str = Field(..., alias="serialNumber")
    features: list[str] = Field(...)


class PowerOnBehavior(IntEnum):
    """Enum for the power on behavior of the Elgato Light."""

    UNKNOWN = 0
    RESTORE_LAST = 1
    USE_DEFAULTS = 2


class Settings(BaseModel):
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

    color_change_duration: int = Field(..., alias="colorChangeDurationMs")
    power_on_behavior: PowerOnBehavior = Field(..., alias="powerOnBehavior")
    power_on_brightness: int = Field(..., alias="powerOnBrightness")
    power_on_hue: Optional[float] = Field(None, alias="powerOnHue")
    power_on_saturation: Optional[float] = Field(None, alias="powerOnSaturation")
    power_on_temperature: Optional[int] = Field(None, alias="powerOnTemperature")
    switch_off_duration: int = Field(..., alias="switchOffDurationMs")
    switch_on_duration: int = Field(..., alias="switchOnDurationMs")


class State(BaseModel):
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
    hue: Optional[float]
    saturation: Optional[float]
    temperature: Optional[int]
