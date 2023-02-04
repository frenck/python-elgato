"""Tests for identifying the Elgato Light device."""

import pytest
from aiohttp import ClientSession
from aresponses import ResponsesMockServer

from elgato import Elgato


@pytest.mark.asyncio
async def test_identify(aresponses: ResponsesMockServer) -> None:
    """Test identifying the Elgato Light."""
    aresponses.add(
        "example.com:9123",
        "/elgato/identify",
        "POST",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text="",
        ),
    )

    async with ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        await elgato.identify()
