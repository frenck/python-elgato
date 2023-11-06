"""Asynchronous Python client for Elgato Lights."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

from mashumaro import field_options
from mashumaro.config import BaseConfig
from mashumaro.mixins.orjson import DataClassORJSONMixin
from mashumaro.types import SerializationStrategy


class IntegerIsBoolean(SerializationStrategy):
    """Boolean serialization strategy for integers."""

    def serialize(self, value: bool) -> int:  # noqa: FBT001
        """Serialize a boolean to an integer."""
        return int(value)

    def deserialize(self, value: int) -> bool:
        """Deserialize an integer to a boolean."""
        return bool(value)


class BaseModel(DataClassORJSONMixin):
    """Base model for all Elgato models."""

    # pylint: disable-next=too-few-public-methods
    class Config(BaseConfig):
        """Mashumaro configuration."""

        omit_none = True
        serialization_strategy = {bool: IntegerIsBoolean()}  # noqa: RUF012
        serialize_by_alias = True


@dataclass
class EnergySavingAdjustBrightnessSettings(BaseModel):
    """Object holding the Elgato Light battery energy saving settings for brightness.

    This object holds information about the Elgato Light energy saving settings
    for saving battery when using the light regarding brightness limits.

    Only applies to Elgato devices with a battery of course,
    like the Key Light Mini.

    Attributes
    ----------
        brightness: Adjusted brightness when energy saving is active.
        enabled: boolean
    """

    brightness: int
    enabled: bool = field(metadata=field_options(alias="enable"))


@dataclass
class EnergySavingSettings(BaseModel):
    """Object holding the Elgato Light battery energy saving settings.

    This object holds information about the Elgato Light energy saving settings
    for saving battery when using the light.

    Only applies to Elgato devices with a battery of course,
    like the Key Light Mini.

    Attributes
    ----------
        adjust_brightness: Adjust brightness when energy saving is active.
        disable_wifi: Disable Wi-Fi when energy saving is active.
        enabled: boolean
        minimum_battery_level: Use energy saving when battery level is below this value.
    """

    adjust_brightness: EnergySavingAdjustBrightnessSettings = field(
        metadata=field_options(alias="adjustBrightness")
    )
    disable_wifi: bool = field(metadata=field_options(alias="disableWifi"))
    enabled: bool = field(metadata=field_options(alias="enable"))
    minimum_battery_level: int = field(
        metadata=field_options(alias="minimumBatteryLevel")
    )


@dataclass
class BatterySettings(BaseModel):
    """Object holding the Elgato Light battery information.

    This object holds information about the Elgato Light battery.

    Only applies to Elgato devices with a battery of course,
    like the Key Light Mini.

    Attributes
    ----------
        energy_saving: Energy saving settings.
        bypass: If the battery is bypassed (studio mode).
    """

    energy_saving: EnergySavingSettings = field(
        metadata=field_options(alias="energySaving")
    )
    bypass: bool


@dataclass
class Wifi(BaseModel):
    """Object holding the Elgato device Wi-Fi information.

    This object holds wireles information about the Elgato device.

    Attributes
    ----------
        frequency: The frequency in MHz of the Wi-Fi network connected.
        rssi: The signal strength in dBm of the Wi-Fi network connected.
        ssid: The SSID of the Wi-Fi network the device is connected to.
    """

    frequency: int = field(metadata=field_options(alias="frequencyMHz"))
    rssi: int
    ssid: str


class PowerSource(IntEnum):
    """Enum for the power source of the Elgato Light."""

    UNKNOWN = 0
    MAINS = 1
    BATTERY = 2


class BatteryStatus(IntEnum):
    """Enum for the battery status of the Elgato Light.

    Value "1" seems to be unused. I could not get it to show up, no
    matter if the device was charging or not, in saving mode or even bypass.
    """

    DRAINING = 0
    CHARGING = 2
    CHARGED = 3


@dataclass
class BatteryInfo(BaseModel):
    """Object holding the Elgato Light device information.

    This object holds information about the Elgato Light.

    Attributes
    ----------
        charge_current: The charge current in A.
        charge_power: The charge power in W.
        charge_voltage: The charge voltage in V.
        input_charge_current: The charge current in mA.
        input_charge_voltage: The charge voltage in mV.
        input_charge_voltage: The charge voltage in mV.
        level: The battery level of the device in %.
        power_source: The power source of the device.
        status: The battery status.
        voltage: The current battery voltage in mV.
    """

    power_source: PowerSource = field(metadata=field_options(alias="powerSource"))
    level: float
    status: BatteryStatus
    voltage: int = field(metadata=field_options(alias="currentBatteryVoltage"))
    input_charge_voltage: int = field(
        metadata=field_options(alias="inputChargeVoltage")
    )
    input_charge_current: int = field(
        metadata=field_options(alias="inputChargeCurrent")
    )

    @property
    def input_charge_power(self) -> int:
        """Return the input charge power in mW."""
        return round(self.input_charge_voltage * self.input_charge_current / 1_000)

    @property
    def charge_current(self) -> float:
        """Return the charge current in A."""
        return round(self.input_charge_current / 1_000, 2)

    @property
    def charge_power(self) -> float:
        """Return the charge power in W."""
        return round(self.input_charge_power / 1_000, 2)

    @property
    def charge_voltage(self) -> float:
        """Return the charge voltage in V."""
        return round(self.input_charge_voltage / 1_000, 2)


@dataclass
# pylint: disable-next=too-many-instance-attributes
class Info(BaseModel):
    """Object holding the Elgato Light device information.

    This object holds information about the Elgato Light.

    Attributes
    ----------
        display_name: Configured display name of the Elgato Light.
        features: List of features this devices exposes.
        firmware_build_number: An integer with the build number of the firmware.
        firmware_version: String containing the firmware version.
        hardware_board_type: An integer indicating the board revision.
        product_name: The product name.
        serial_number: Serial number of the Elgato Light.
    """

    features: list[str]
    firmware_build_number: int = field(
        metadata=field_options(alias="firmwareBuildNumber")
    )
    firmware_version: str = field(metadata=field_options(alias="firmwareVersion"))
    hardware_board_type: int = field(metadata=field_options(alias="hardwareBoardType"))
    product_name: str = field(metadata=field_options(alias="productName"))
    serial_number: str = field(metadata=field_options(alias="serialNumber"))
    display_name: str = field(
        default="Elgato Light", metadata=field_options(alias="displayName")
    )
    mac_address: str | None = field(
        default=None, metadata=field_options(alias="macAddress")
    )
    wifi: Wifi | None = field(default=None, metadata=field_options(alias="wifi-info"))


class PowerOnBehavior(IntEnum):
    """Enum for the power on behavior of the Elgato Light."""

    UNKNOWN = 0
    RESTORE_LAST = 1
    USE_DEFAULTS = 2


@dataclass
# pylint: disable-next=too-many-instance-attributes
class Settings(BaseModel):
    """Object holding the Elgato Light device settings.

    This object holds information about the Elgato Light settings.

    Attributes
    ----------
        battery: Battery settings, if the device has a battery.
        color_change_duration: Transition time of color changes in milliseconds.
        power_on_behavior: 1 = Restore last, 2 = Use defaults.
        power_on_brightness: The brightness used as default.
        power_on_hue: The hue value used as default.
        power_on_saturation: The saturation level used as default.
        power_on_temperature: The temperature level used as default.
        switch_off_duration: Turn off transition time in milliseconds.
        switch_on_duration: Turn on transition time in milliseconds.
    """

    color_change_duration: int = field(
        metadata=field_options(alias="colorChangeDurationMs")
    )
    power_on_behavior: PowerOnBehavior = field(
        metadata=field_options(alias="powerOnBehavior")
    )
    power_on_brightness: int = field(metadata=field_options(alias="powerOnBrightness"))
    switch_off_duration: int = field(
        metadata=field_options(alias="switchOffDurationMs")
    )
    switch_on_duration: int = field(metadata=field_options(alias="switchOnDurationMs"))
    battery: BatterySettings | None = None
    power_on_hue: float | None = field(
        default=None, metadata=field_options(alias="powerOnHue")
    )
    power_on_saturation: float | None = field(
        default=None, metadata=field_options(alias="powerOnSaturation")
    )
    power_on_temperature: int | None = field(
        default=None, metadata=field_options(alias="powerOnTemperature")
    )


@dataclass
class State(BaseModel):
    """Object holding the Elgato Light state.

    Represents a visible state of an Elgato Light.

    Attributes
    ----------
        on: A boolean indicating the if the light if on or off.
        brightness: An integer between 0 and 255, representing the brightness.
        hue:
        saturation:
        temperature: An integer representing the color temperature in mireds.
    """

    on: bool
    brightness: int
    hue: float | None = field(default=None)
    saturation: float | None = field(default=None)
    temperature: int | None = field(default=None)
