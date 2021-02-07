"""Asynchronous Python client for Elgato Key Lights."""
from __future__ import annotations

import asyncio
import socket
from importlib import metadata
from typing import Any

import aiohttp
import async_timeout
from yarl import URL

from .exceptions import ElgatoConnectionError, ElgatoError
from .models import Info, State


class Elgato:
    """Main class for handling connections with an Elgato Key Light."""

    def __init__(
        self,
        host: str,
        port: int = 9123,
        request_timeout: int = 8,
        session: aiohttp.client.ClientSession = None,
    ) -> None:
        """Initialize connection with the Elgato Key Light.

        Constructor to set up the Elgato Key Light instance.

        Args:
            host: Hostname or IP address of the Elgato Key Light.
            port: The port number, in general this is 9123 (default).
            request_timeout: An integer with the request timeout in seconds.
            session: Optional, shared, aiohttp client session.
        """
        self._session = session
        self._close_session = False

        self.host = host
        self.port = port
        self.request_timeout = request_timeout

    async def _request(
        self,
        uri: str,
        data: dict | None = None,
    ) -> Any:
        """Handle a request to a Elgato Key Light device.

        A generic method for sending/handling HTTP requests done against
        the Elgato Key Light API.

        Args:
            uri: Request URI, without '/elgato/', for example, 'info'
            data: Dictionary of data to send to the Elgato Key Light.

        Returns:
            A Python dictionary (JSON decoded) with the response from
            the Elgato Key Light API.

        Raises:
            ElgatoConnectionError: An error occurred while communicating with
                the Elgato Key Light.
            ElgatoError: Received an unexpected response from the Elgato Key
                Light API.
        """
        version = metadata.version(__package__)
        method = "GET" if data is None else "PUT"
        url = URL.build(
            scheme="http", host=self.host, port=self.port, path="/elgato/"
        ).join(URL(uri))

        headers = {
            "User-Agent": f"PythonElgato/{version}",
            "Accept": "application/json, text/plain, */*",
        }

        if self._session is None:
            self._session = aiohttp.ClientSession()
            self._close_session = True

        try:
            with async_timeout.timeout(self.request_timeout):
                response = await self._session.request(
                    method,
                    url,
                    json=data,
                    headers=headers,
                )
                response.raise_for_status()
        except asyncio.TimeoutError as exception:
            raise ElgatoConnectionError(
                "Timeout occurred while connecting to Elgato Key Light device"
            ) from exception
        except (
            aiohttp.ClientError,
            aiohttp.ClientResponseError,
            socket.gaierror,
        ) as exception:
            raise ElgatoConnectionError(
                "Error occurred while communicating with Elgato Key Light device"
            ) from exception

        content_type = response.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            text = await response.text()
            raise ElgatoError(
                "Unexpected response from the Elgato Key Light device",
                {"Content-Type": content_type, "response": text},
            )

        return await response.json()

    async def state(self) -> State:
        """Get the current state of Elgato Key Light device.

        Returns:
            A State object, with the current Elgato Key Light state.
        """
        data = await self._request("lights")
        return State.from_dict(data)

    async def info(self) -> Info:
        """Get devices information from Elgato Key Light device.

        Returns:
            A Info object, with information about the Elgato Key Light device.
        """
        data = await self._request("accessory-info")
        return Info.from_dict(data)

    async def light(
        self,
        on: bool | None = None,
        brightness: int | None = None,
        temperature: int | None = None,
    ) -> None:
        """Change state of an Elgato Key Light device.

        Args:
            on: A boolean, true to turn the light on, false otherwise.
            brightness: The brightness of the light, between 0 and 255.
            temperature: The color temperature of the light, in mired.
        """
        state = {}

        if on is not None:
            state["on"] = int(on)

        if brightness is not None:
            state["brightness"] = brightness

        if temperature is not None:
            state["temperature"] = temperature

        await self._request("lights", data={"numberOfLights": 1, "lights": [state]})

    async def close(self) -> None:
        """Close open client session."""
        if self._session and self._close_session:
            await self._session.close()

    async def __aenter__(self) -> Elgato:
        """Async enter.

        Returns:
            The Elgato object.
        """
        return self

    async def __aexit__(self, *_exc_info) -> None:
        """Async exit.

        Args:
            _exc_info: Exec type.
        """
        await self.close()
