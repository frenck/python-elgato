"""Asynchronous Python client for Elgato Key Lights."""
import asyncio
import socket
from typing import Any, Optional

import aiohttp
import async_timeout
from yarl import URL

from .__version__ import __version__
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
        """Initialize connection with the Elgato Key Light."""
        self._session = session
        self._close_session = False

        self.host = host
        self.port = port
        self.request_timeout = request_timeout

    async def _request(self, uri: str, data: Optional[dict] = None,) -> Any:
        """Handle a request to a Elgato Key Light device."""
        method = "GET" if data is None else "PUT"
        url = URL.build(
            scheme="http", host=self.host, port=self.port, path="/elgato/"
        ).join(URL(uri))

        headers = {
            "User-Agent": f"PythonElgato/{__version__}",
            "Accept": "application/json, text/plain, */*",
        }

        if self._session is None:
            self._session = aiohttp.ClientSession()
            self._close_session = True

        try:
            with async_timeout.timeout(self.request_timeout):
                response = await self._session.request(
                    method, url, json=data, headers=headers,
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

    async def state(self):
        """Get the current state of Elgato Key Light device."""
        data = await self._request("lights")
        return State.from_dict(data)

    async def info(self) -> Info:
        """Get devices information from Elgato Key Light device."""
        data = await self._request("accessory-info")
        return Info.from_dict(data)

    async def light(
        self,
        on: Optional[bool] = None,
        brightness: Optional[int] = None,
        temperature: Optional[int] = None,
    ) -> None:
        """Change state of an Elgato Key Light device."""
        state = {}

        if on is not None:
            state["on"] = 1 if on else 0

        if brightness is not None:
            state["brightness"] = brightness

        if temperature is not None:
            state["temperature"] = temperature

        await self._request("lights", data={"numberOfLights": 1, "lights": [state]})

    async def close(self) -> None:
        """Close open client session."""
        if self._session and self._close_session:
            await self._session.close()

    async def __aenter__(self) -> "Elgato":
        """Async enter."""
        return self

    async def __aexit__(self, *exc_info) -> None:
        """Async exit."""
        await self.close()
