"""Asynchronous Python client for Elgato Lights."""
from __future__ import annotations

import asyncio
import socket
from dataclasses import dataclass
from importlib import metadata
from typing import TYPE_CHECKING, Any, Concatenate, ParamSpec, TypedDict, TypeVar, cast

import async_timeout
from aiohttp.client import ClientError, ClientSession
from aiohttp.hdrs import METH_GET, METH_POST, METH_PUT
from yarl import URL

from .exceptions import ElgatoConnectionError, ElgatoError, ElgatoNoBatteryError
from .models import BatteryInfo, BatterySettings, Info, PowerOnBehavior, Settings, State

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

_ElgatoT = TypeVar("_ElgatoT", bound="Elgato")
_R = TypeVar("_R")
_P = ParamSpec("_P")


def requires_battery(
    func: Callable[Concatenate[_ElgatoT, _P], Coroutine[Any, Any, _R]],
) -> Callable[Concatenate[_ElgatoT, _P], Coroutine[Any, Any, _R]]:
    """Decorate Elgato calls that require a device with a battery installed.

    A decorator that wraps and guards the passed in function, and checks if
    the device has a battery installed and only than calls the function.
    """

    async def handler(self: _ElgatoT, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        """Handle calls to devices that require a battery."""
        if await self.has_battery() is False:
            raise ElgatoNoBatteryError
        return await func(self, *args, **kwargs)

    return handler


@dataclass
class Elgato:
    """Main class for handling connections with an Elgato Light."""

    host: str
    port: int = 9123
    request_timeout: int = 8
    session: ClientSession | None = None

    _close_session: bool = False
    _has_battery: bool | None = None

    async def _request(
        self,
        uri: str,
        *,
        method: str = METH_GET,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Handle a request to a Elgato Light device.

        A generic method for sending/handling HTTP requests done against
        the Elgato Light API.

        Args
        ----
            uri: Request URI, without '/elgato/', for example, 'info'
            method: HTTP Method to use.
            data: Dictionary of data to send to the Elgato Light.

        Returns
        -------
            A Python dictionary (JSON decoded) with the response from
            the Elgato Light API.

        Raises
        ------
            ElgatoConnectionError: An error occurred while communicating with
                the Elgato Light.
            ElgatoError: Received an unexpected response from the Elgato Light
                API.
        """
        version = metadata.version(__package__)
        url = URL.build(
            scheme="http",
            host=self.host,
            port=self.port,
            path="/elgato/",
        ).join(URL(uri))

        headers = {
            "User-Agent": f"PythonElgato/{version}",
            "Accept": "application/json, text/plain, */*",
        }

        if self.session is None:
            self.session = ClientSession()
            self._close_session = True

        try:
            async with async_timeout.timeout(self.request_timeout):
                response = await self.session.request(
                    method,
                    url,
                    json=data,
                    headers=headers,
                )
                response.raise_for_status()
        except asyncio.TimeoutError as exception:
            msg = "Timeout occurred while connecting to Elgato Light device"
            raise ElgatoConnectionError(msg) from exception
        except (
            ClientError,
            socket.gaierror,
        ) as exception:
            msg = "Error occurred while communicating with Elgato Light device"
            raise ElgatoConnectionError(msg) from exception

        content_type = response.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            text = await response.text()
            msg = "Unexpected response from the Elgato Light device"
            raise ElgatoError(msg, {"Content-Type": content_type, "response": text})

        return cast(dict[str, Any], await response.json())

    async def has_battery(self) -> bool:
        """Check if the Elgato Light device has a battery.

        Returns
        -------
            A boolean indicating if the Elgato Light device has a battery.
        """
        if self._has_battery is None:
            settings = await self.settings()
            self._has_battery = settings.battery is not None
        return self._has_battery

    @requires_battery
    async def battery(self) -> BatteryInfo:
        """Get battery information from Elgato Light device.

        Returns
        -------
            A BatteryInfo object, with information on the current battery state
            of the Elgato light.
        """
        data = await self._request("battery-info")
        return BatteryInfo.parse_obj(data)

    @requires_battery
    async def battery_bypass(self, *, on: bool) -> None:
        """Change the bypass mode of the Elgato Light device.

        In the app this is also called "Studio mode". When the bypass mode is
        the battery isn't used and would only work when the device is plugged
        into mains.

        There is an odd bug in current versions of the Elgato Light Mini
        firmware, that turns the light on when the bypass mode is turned off;
        the device will still think it is turned off, but the light will be on.

        Args:
        ----
            on: A boolean, true to turn on bypass, false otherwise.
        """
        await self._request(
            "/elgato/lights/settings",
            method=METH_PUT,
            data={"battery": {"bypass": int(on)}},
        )

    async def battery_settings(self) -> BatterySettings:
        """Get device battery settings from Elgato Light device.

        Guarded version of `settings().battery`.

        Returns
        -------
            A Battery settings object, with information about the Elgato Light device.
        """
        settings = await self.settings()
        if settings.battery is None:
            raise ElgatoNoBatteryError
        return settings.battery

    @requires_battery
    async def energy_saving(
        self,
        *,
        adjust_brightness: bool | None = None,
        brightness: int | None = None,
        disable_wifi: bool | None = None,
        minimum_battery_level: int | None = None,
        on: bool | None = None,
    ) -> None:
        """Change the energy saving mode of the Elgato Light device.

        Args:
        ----
            adjust_brightness: Adjust the brightness of the light when it drops
                below the minimum battery level threshold. True to turn it on,
                false otherwise.
            brightness: The brightness to set the light to when energy savings
                kicks in. This is only used when adjust_brightness is True.
            disable_wifi: Disable the WiFi of the Elgato Light device when
                energy savings kicks in. True to turn it on, false otherwise.
            minimum_battery_level: The minimum battery level threshold to
                trigger energy savings.
            on: A boolean, true to turn on energy saving, false otherwise.
        """
        current_settings = await self.battery_settings()
        data = current_settings.energy_saving.dict(by_alias=True)

        if on is not None:
            data["enable"] = int(on)
        if minimum_battery_level is not None:
            data["minimumBatteryLevel"] = minimum_battery_level
        if disable_wifi is not None:
            data["disableWifi"] = int(disable_wifi)
        if adjust_brightness is not None:
            data["adjustBrightness"]["enable"] = int(adjust_brightness)
        if brightness is not None:
            data["adjustBrightness"]["brightness"] = brightness

        await self._request(
            "/elgato/lights/settings",
            method=METH_PUT,
            data={"battery": {"energySaving": data}},
        )

    async def info(self) -> Info:
        """Get devices information from Elgato Light device.

        Returns
        -------
            A Info object, with information about the Elgato Light device.
        """
        data = await self._request("accessory-info")
        return Info.parse_obj(data)

    async def settings(self) -> Settings:
        """Get device settings from Elgato Light device.

        Returns
        -------
            A Settings object, with information about the Elgato Light device.
        """
        data = await self._request("lights/settings")
        return Settings.parse_obj(data)

    async def state(self) -> State:
        """Get the current state of Elgato Light device.

        Returns
        -------
            A State object, with the current Elgato Light state.
        """
        data = await self._request("lights")
        return State.parse_obj(data["lights"][0])

    async def identify(self) -> None:
        """Identify this Elgato Light device by making it blink."""
        await self._request("identify", method=METH_POST)

    async def restart(self) -> None:
        """Restart the Elgato Light device."""
        await self._request("restart", method=METH_POST)

    async def display_name(self, name: str) -> None:
        """Change the display name of an Elgato Light device.

        Args:
        ----
            name: The name to give the Elgato Light device.
        """
        await self._request(
            "/elgato/accessory-info",
            method=METH_PUT,
            data={"displayName": name},
        )

    async def light(
        self,
        *,
        on: bool | None = None,
        brightness: int | None = None,
        hue: float | None = None,
        saturation: float | None = None,
        temperature: int | None = None,
    ) -> None:
        """Change state of an Elgato Light device.

        Args:
            on: A boolean, true to turn the light on, false otherwise.
            brightness: The brightness of the light, between 0 and 255.
            hue: The hue range as a float from 0 to 360 degrees.
            saturation: The color saturation as a float from 0 to 100.
            temperature: The color temperature of the light, in mired.

        Raises
        ------
            ElgatoError: The provided values are invalid.
        """
        if temperature and (hue or saturation):
            msg = "Cannot set temperature together with hue or saturation"
            raise ElgatoError(msg)

        class LightState(TypedDict, total=False):
            """Describe state dictionary that can be set on a light."""

            brightness: int
            hue: float
            on: int
            saturation: float
            temperature: int

        state: LightState = {}

        if on is not None:
            state["on"] = int(on)

        if brightness is not None:
            if not 0 <= brightness <= 100:
                msg = "Brightness not between 0 and 100"
                raise ElgatoError(msg)
            state["brightness"] = brightness

        if hue is not None:
            if not 0 <= hue <= 360:
                msg = "Hue not between 0 and 360"
                raise ElgatoError(msg)
            state["hue"] = hue

        if saturation is not None:
            if not 0 <= saturation <= 100:
                msg = "Saturation not between 0 and 100"
                raise ElgatoError(msg)
            state["saturation"] = saturation

        if temperature is not None:
            if not 143 <= temperature <= 344:
                msg = "Color temperature out of range"
                raise ElgatoError(msg)
            state["temperature"] = temperature

        if not state:
            msg = "No parameters to set, light not adjusted"
            raise ElgatoError(msg)

        await self._request(
            "lights",
            method=METH_PUT,
            data={"numberOfLights": 1, "lights": [state]},
        )

    async def power_on_behavior(
        self,
        *,
        behavior: PowerOnBehavior | None = None,
        brightness: int | None = None,
        hue: float | None = None,
        temperature: int | None = None,
    ) -> None:
        """Change the power on behavior of the Elgato Light device.

        Args:
        ----
            behavior: The power on behavior to set.
            brightness: The power on brightness of the light, between 0 and 255.
            hue: The power on hue range as a float from 0 to 360 degrees.
            temperature: The power on color temperature of the light, in mired.
        """
        current_settings = await self.settings()
        if behavior is not None:
            current_settings.power_on_behavior = behavior
        if brightness is not None:
            current_settings.power_on_brightness = brightness
        if hue is not None:
            current_settings.power_on_hue = hue
        if temperature is not None:
            current_settings.power_on_temperature = temperature

        # Unset battery if present, needs special handling
        if current_settings.battery:
            current_settings.battery = None

        await self._request(
            "/elgato/lights/settings",
            method=METH_PUT,
            data=current_settings.dict(by_alias=True, exclude_none=True),
        )

    async def close(self) -> None:
        """Close open client session."""
        if self.session and self._close_session:
            await self.session.close()

    async def __aenter__(self) -> Elgato:
        """Async enter.

        Returns
        -------
            The Elgato object.
        """
        return self

    async def __aexit__(self, *_exc_info: Any) -> None:
        """Async exit.

        Args:
        ----
            _exc_info: Exec type.
        """
        await self.close()
