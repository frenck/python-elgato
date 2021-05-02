"""Tests for identifying the Elgato Light device."""
import aiohttp
import pytest

from elgato import Elgato


@pytest.mark.asyncio
async def test_identify(aresponses):
    """Test identifying the Elgato Light."""
    aresponses.add(
        "example.com:9123",
        "/elgato/identify",
        "POST",
        aresponses.Response(
            status=200, headers={"Content-Type": "application/json"}, text=""
        ),
    )

    async with aiohttp.ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        await elgato.identify()
