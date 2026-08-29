"""Asynchronous Python client for Elgato Lights."""

from __future__ import annotations

import asyncio
import socket
from dataclasses import dataclass
from http import HTTPStatus
from typing import (
    TYPE_CHECKING,
    Any,
    Concatenate,
    ParamSpec,
    Self,
    TypedDict,
    TypeVar,
)

import orjson
from aiohttp.client import ClientError, ClientSession
from aiohttp.hdrs import METH_GET, METH_POST, METH_PUT
from yarl import URL

from .exceptions import (
    ElgatoConnectionError,
    ElgatoError,
    ElgatoFirmwareError,
    ElgatoNoBatteryError,
)
from .models import (
    BatteryInfo,
    BatterySettings,
    Info,
    PowerOnBehavior,
    PowerSource,
    Settings,
    State,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from .firmware import FirmwareImage

_ElgatoT = TypeVar("_ElgatoT", bound="Elgato")
_R = TypeVar("_R")
_P = ParamSpec("_P")

# The chunk size Elgato Control Center uses over HTTP.
FIRMWARE_CHUNK_SIZE = 4096
FIRMWARE_UPLOAD_RETRIES = 3
FIRMWARE_RETRY_DELAY = 0.2

# Preparing erases a flash slot and rebooting takes the device offline for a
# while; both need considerably more patience than a normal call.
FIRMWARE_SLOW_TIMEOUT = 60

# Not a threshold Elgato publishes, but an interrupted update on a light that
# runs out of power halfway is a bad trade for a firmware nobody asked for.
FIRMWARE_MINIMUM_BATTERY_LEVEL = 20


def _firmware_error(status: int, response: str) -> str:
    """Turn a device error response into something worth reading.

    Args:
    ----
        status: The HTTP status the device answered with.
        response: The raw response body.

    Returns:
    -------
        The messages the device gave, or the status code when it gave none.

    """
    try:
        # pylint: disable-next=no-member
        errors = orjson.loads(response)["errors"]
        messages = "; ".join(str(error["message"]) for error in errors)
    # pylint: disable-next=no-member
    except (orjson.JSONDecodeError, KeyError, TypeError):
        messages = ""

    return messages or f"Elgato Light device returned HTTP {status}"


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
    ) -> str:
        """Handle a request to an Elgato Light device.

        A generic method for sending/handling HTTP requests done against
        the Elgato Light API.

        Args:
        ----
            uri: Request URI, without '/elgato/', for example, 'info'
            method: HTTP Method to use.
            data: Dictionary of data to send to the Elgato Light.

        Returns:
        -------
            A Python string (JSON) with the response from the Elgato Light API.

        Raises:
        ------
            ElgatoConnectionError: An error occurred while communicating with
                the Elgato Light.
            ElgatoError: Received an unexpected response from the Elgato Light
                API.

        """
        status, response = await self._raw_request(uri, method=method, data=data)

        if status >= HTTPStatus.BAD_REQUEST:
            msg = f"Elgato Light device returned HTTP {status}: {response}"
            raise ElgatoError(msg)

        return response

    # pylint: disable-next=too-many-arguments
    async def _raw_request(
        self,
        uri: str,
        *,
        method: str = METH_GET,
        data: dict[str, Any] | None = None,
        content: bytes | None = None,
        request_timeout: int | None = None,
    ) -> tuple[int, str]:
        """Handle a request to an Elgato Light device, status and all.

        The firmware update API says what it means with its status codes: it
        acknowledges a chunk with 202 and reports trouble in the body of a
        400. Both are things a caller may want to act on rather than treat as
        a failed connection.

        Args:
        ----
            uri: Request URI, without '/elgato/', for example, 'info'
            method: HTTP Method to use.
            data: Dictionary of data to send as JSON.
            content: Raw bytes to send instead of JSON.
            request_timeout: Seconds to wait, overriding the configured one.

        Returns:
        -------
            The HTTP status and the response body.

        Raises:
        ------
            ElgatoConnectionError: An error occurred while communicating with
                the Elgato Light.

        """
        url = URL.build(
            scheme="http",
            host=self.host,
            port=self.port,
            path="/elgato/",
        ).join(URL(uri))

        headers = {
            "User-Agent": "PythonElgato",
            "Accept": "application/json, text/plain, */*",
        }
        if content is not None:
            headers["Content-Type"] = "application/octet-stream"

        if self.session is None:
            self.session = ClientSession()
            self._close_session = True

        try:
            async with asyncio.timeout(request_timeout or self.request_timeout):
                response = await self.session.request(
                    method,
                    url,
                    data=content,
                    json=data if content is None else None,
                    headers=headers,
                )
                return response.status, await response.text()
        except TimeoutError as exception:
            msg = "Timeout occurred while connecting to Elgato Light device"
            raise ElgatoConnectionError(msg) from exception
        except (
            ClientError,
            socket.gaierror,
        ) as exception:
            msg = "Error occurred while communicating with Elgato Light device"
            raise ElgatoConnectionError(msg) from exception

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
        return BatteryInfo.from_json(data)

    @requires_battery
    async def battery_bypass(self, *, on: bool) -> None:
        """Change the bypass mode of the Elgato Light device.

        In the app this is also called "Studio mode". When the bypass mode is on,
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
            "lights/settings",
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
    # pylint: disable-next=too-many-arguments
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
        data = current_settings.energy_saving.to_dict()

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
            "lights/settings",
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
        return Info.from_json(data)

    async def settings(self) -> Settings:
        """Get device settings from Elgato Light device.

        Returns
        -------
            A Settings object, with information about the Elgato Light device.

        """
        data = await self._request("lights/settings")
        return Settings.from_json(data)

    async def state(self) -> State:
        """Get the current state of Elgato Light device.

        Returns
        -------
            A State object, with the current Elgato Light state.

        """
        data = await self._request("lights")
        # pylint: disable-next=no-member
        lights = orjson.loads(data)["lights"]
        return State.from_dict(lights[0])

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
            "accessory-info",
            method=METH_PUT,
            data={"displayName": name},
        )

    # pylint: disable-next=too-many-arguments
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
        ----
            on: A boolean, true to turn the light on, false otherwise.
            brightness: The brightness of the light, between 0 and 100.
            hue: The hue range as a float from 0 to 360 degrees.
            saturation: The color saturation as a float from 0 to 100.
            temperature: The color temperature of the light, in mired.

        Raises:
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
            brightness: The power on brightness of the light, between 0 and 100.
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
            "lights/settings",
            method=METH_PUT,
            data=current_settings.to_dict(),
        )

    async def update_firmware(
        self,
        image: FirmwareImage,
        *,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> None:
        """Install a firmware image on the Elgato Light device.

        The device keeps two firmware slots and runs the old one until the
        very last step, so an upload that fails partway leaves a working
        light. That last step reboots the device, which takes about a minute.
        This method returns as soon as the device accepts the reboot, it does
        not wait for the device to come back.

        Args:
        ----
            image: The firmware image to install.
            on_progress: Called with the bytes sent so far and the total,
                after every chunk the device accepts.

        Raises:
        ------
            ElgatoFirmwareError: The image is not for this device, the battery
                is too low, or the device refused the update.

        """
        info = await self.info()
        if info.hardware_board_type != image.board_type:
            msg = (
                f"Firmware is for the {image.board_name}, "
                f"but this device is board type {info.hardware_board_type}"
            )
            raise ElgatoFirmwareError(msg)

        await self._firmware_battery_check()
        await self._firmware_prepare(len(image.data))
        await self._firmware_upload(image.data, on_progress)
        await self._firmware_execute()

    async def _firmware_battery_check(self) -> None:
        """Keep a light that is about to die out of a firmware update."""
        if not await self.has_battery():
            return

        battery = await self.battery()
        if (
            battery.power_source is PowerSource.BATTERY
            and battery.level < FIRMWARE_MINIMUM_BATTERY_LEVEL
        ):
            msg = (
                f"Battery is at {battery.level:.0f}%, connect the device to"
                " power before updating its firmware"
            )
            raise ElgatoFirmwareError(msg)

    async def _firmware_prepare(self, size: int) -> None:
        """Ask the Elgato Light device to make room for a firmware image.

        The device erases its spare flash slot here, and answers nothing else
        while it does. Nothing may talk to the device until this returns.

        Args:
        ----
            size: The size of the complete firmware image, in bytes.

        """
        status, response = await self._raw_request(
            "firmware-update/prepare",
            method=METH_PUT,
            data={"size": size},
            request_timeout=FIRMWARE_SLOW_TIMEOUT,
        )

        if status != HTTPStatus.OK:
            msg = f"Device refused the firmware: {_firmware_error(status, response)}"
            raise ElgatoFirmwareError(msg)

    async def _firmware_upload(
        self,
        data: bytes,
        on_progress: Callable[[int, int], None] | None,
    ) -> None:
        """Send a firmware image to the Elgato Light device, chunk by chunk.

        Args:
        ----
            data: The complete firmware image, header included.
            on_progress: Called with the bytes sent so far and the total.

        """
        total = len(data)
        offset = 0

        while offset < total:
            chunk = data[offset : offset + FIRMWARE_CHUNK_SIZE]
            await self._firmware_chunk(chunk, offset)
            offset += len(chunk)

            if on_progress is not None:
                on_progress(offset, total)

    async def _firmware_chunk(self, chunk: bytes, offset: int) -> None:
        """Send a single chunk of firmware, retrying the ones that stumble.

        The device answers 202 for as long as it wants more, and 200 once the
        last chunk passed verification. It asks for a retry with 400 or 408,
        but it also uses those to reject an image outright. Retrying costs
        little, and a rejected image fails on the last attempt all the same.

        Args:
        ----
            chunk: The bytes to send.
            offset: Where these bytes belong in the image.

        """
        attempt = 0
        while True:
            status, response = await self._raw_request(
                f"firmware-update/data?offset={offset}",
                method=METH_PUT,
                content=chunk,
                request_timeout=FIRMWARE_SLOW_TIMEOUT,
            )

            if status in (HTTPStatus.OK, HTTPStatus.ACCEPTED):
                return

            attempt += 1
            retryable = status in (
                HTTPStatus.BAD_REQUEST,
                HTTPStatus.REQUEST_TIMEOUT,
            )
            if not retryable or attempt == FIRMWARE_UPLOAD_RETRIES:
                msg = (
                    f"Device rejected the firmware at offset {offset}: "
                    f"{_firmware_error(status, response)}"
                )
                raise ElgatoFirmwareError(msg)

            await asyncio.sleep(FIRMWARE_RETRY_DELAY)

    async def _firmware_execute(self) -> None:
        """Tell the Elgato Light device to boot the firmware it just took."""
        status, response = await self._raw_request(
            "firmware-update/execute",
            method=METH_POST,
            request_timeout=FIRMWARE_SLOW_TIMEOUT,
        )

        if status != HTTPStatus.OK:
            msg = (
                "Device refused to install the firmware: "
                f"{_firmware_error(status, response)}"
            )
            raise ElgatoFirmwareError(msg)

    async def close(self) -> None:
        """Close open client session."""
        if self.session and self._close_session:
            await self.session.close()

    async def __aenter__(self) -> Self:
        """Async enter.

        Returns
        -------
            The Elgato object.

        """
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        """Async exit.

        Args:
        ----
            _exc_info: Exec type.

        """
        await self.close()
