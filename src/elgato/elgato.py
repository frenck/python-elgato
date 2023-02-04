"""Asynchronous Python client for Elgato Lights."""
from __future__ import annotations

import asyncio
import socket
from dataclasses import dataclass
from importlib import metadata
from typing import Any, TypedDict, cast

import async_timeout
from aiohttp.client import ClientError, ClientSession
from aiohttp.hdrs import METH_GET, METH_POST, METH_PUT
from yarl import URL

from .exceptions import ElgatoConnectionError, ElgatoError
from .models import Info, Settings, State


@dataclass
class Elgato:
    """Main class for handling connections with an Elgato Light."""

    host: str
    port: int = 9123
    request_timeout: int = 8
    session: ClientSession | None = None

    _close_session: bool = False

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

        class LightState(TypedDict, total=False):  # lgtm [py/unused-local-variable]
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
